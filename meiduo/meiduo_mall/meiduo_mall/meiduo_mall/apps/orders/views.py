from django import http
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View
from django_redis import get_redis_connection
from django.utils import timezone
from django.db import transaction

import json
import logging

from decimal import Decimal
from meiduo_mall.utils.views import LoginRequired
from users.models import Address
from goods.models import SKU
from .models import OrderInfo, OrderGoods
from meiduo_mall.utils.response_code import RETCODE

logger = logging.getLogger('django')


class OrderSettlementView(LoginRequiredMixin, View):
    """结算"""
    def get(self, request):
        user = request.user
        #查出当前登陆用户所有未被逻辑删除的收获地址
        addresses = Address.objects.filter(user=user, is_deleted=False)
        # addresses = user.addresses.filter(is_deleted=False)
        #创建redis连接对象
        redis_conn = get_redis_connection("carts")
        #获取hash数据 hash 存放了sku count数量
        redis_carts = redis_conn.hgetall("carts_%s" % user.id)
        #获取set 数据   set存放了sku商品的勾选状态 勾选的存放set
        selected_ids = redis_conn.smembers("selected_%s" % user.id)
        cart_dict = {}
        #对hash数据进行过滤只要勾选那些商品的id和count
        for sku_id_bytes in selected_ids:
            cart_dict[int(sku_id_bytes)] = int(redis_carts[sku_id_bytes])

        #通过sku_id 查询所有sku模型
        skus = SKU.objects.filter(id__in=cart_dict.keys())
        #定义两个两边接收商品总数量，一个总价
        total_count = 0
        total_amount = 0
        #遍历sku查询 模型给每个sku模型多定义一个count和amount属性
        for sku in skus:
            sku.count = cart_dict[sku.id]
            sku.amount = sku.price * sku.count

            total_count += sku.count
            total_amount += sku.amount
        freight = Decimal('10.00')#运费
        context = {
            'addresses': addresses,  # 收货地址
            'skus': skus,  # 所有勾选的商品
            'total_count': total_count,  # 商品总数量
            'total_amount': total_amount,  # 商品总价
            'freight': freight,  # 运费
            'payment_amount': total_amount + freight,  # 实付总金额
        }
        return render(request, 'place_order.html', context)


class OrderCommitView(LoginRequired):
    """提交订单"""
    def post(self, request):
        #1接收请求体数据
        json_dict = json.loads(request.body.decode())
        address_id = json_dict.get('address_id')
        pay_method = json_dict.get('pay_method')
        user = request.user
        #校验
        if all([address_id, pay_method]) is False:
            return http.HttpResponseForbidden("缺少必传参数")

        try:
            address = Address.objects.get(id=address_id, user=user, is_deleted=False)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden("address_id无效")

        if pay_method not in [OrderInfo.PAY_METHODS_ENUM["CASH"], OrderInfo.PAY_METHODS_ENUM["ALIPAY"]]:
            return http.HttpResponseForbidden("参数有误")
        #生成订单编号
        order_id = timezone.now().strftime("%Y%m%d%H%M%S") + '%09d' % user.id
        #判断订单状态
        status = (OrderInfo.ORDER_STATUS_ENUM['UNPAID']
                if (pay_method == OrderInfo.PAY_METHODS_ENUM['ALIPAY'])
                else OrderInfo.ORDER_STATUS_ENUM['UNSEND'])

        #手动开启事务
        with transaction.atomic():
            save_point1 = transaction.savepoint()
            try:
                #订单信息
                order = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=0,
                    total_amount=Decimal("0.00"),
                    freight=Decimal("10.00"),
                    pay_method=pay_method,
                    status=status
                )

                #连接redis数据库
                redis_conn = get_redis_connection("carts")
                #获取hash数据
                redis_carts = redis_conn.hgetall("carts_%s" % user.id)
                #获取set数据
                selected_ids = redis_conn.smembers("selected_%s" % user.id)
                #定义字典用来装所有购买商品和count
                cart_dict = {}
                #对redis中hash购物车数据进行过滤，只要勾选的数据
                for sku_id_bytes in selected_ids:#遍历出set勾选的所有数据的key
                    #添加到cart_dict字典中
                    cart_dict[int(sku_id_bytes)] = int(redis_carts[sku_id_bytes])
                #遍历出所有要购买的商品数量
                for sku_id in cart_dict:
                    while True:
                    #查询sku模型
                        sku = SKU.objects.get(id=sku_id)
                        #获取要购买的商品数量
                        buy_count = cart_dict[sku_id]
                        #获取当前商品的库存
                        origin_stock = sku.stock
                        #获取当前商品的销量
                        origin_sales = sku.sales
                        #判断库存 当前购买商品数量是否大于当前商品的库存量
                        if buy_count > origin_stock:
                            # #回滚到初始
                            # transaction.rollback()
                            #如果库存不足对事务的操作进行回滚
                            transaction.savepoint_rollback(save_point1)
                            return http.JsonResponse({'code':RETCODE.STOCKERR,'errmsg':'库存量不足'})
                        #修改SKU的库存和销量
                        #计算当前的库存：当前商品库存量-购买商品的数量
                        new_stock = origin_stock- buy_count
                        #计算新的销量:当前商品的购买量+本次商品的购买量
                        new_sales = origin_sales + buy_count
                        # sku.stock = new_stock #修改SKU的库存数量
                        # sku.sales = new_sales #修改sku的销售数量
                        # sku.save()#保存


                        result = SKU.objects.filter(id=sku.id,stock=origin_stock).update(stock=new_sales,sales=new_sales)
                        if result == 0: #说明本次修改失败
                            continue
                         # 修改SPU销量
                        spu = sku.spu #获取当前的spu商品
                        spu.sales += buy_count #spu的销售量+本次spu的购买数量
                        spu.save()#保存
                        #新增订单中n个商品记录
                        OrderGoods.objects.create(
                                order=order,
                                sku=sku,
                                count=buy_count,
                                price=sku.price)
                        #累加订单中商品总数量
                        order.total_count += buy_count#商品总数初始值为0 加上本次商品的购买数量
                            #商品总金额 = 本次购买的商品价格乘于本次商品的购买量
                        order.total_amount += (sku.price*buy_count)
                        break
                    #累加运费一定要写在for循环外面 不然会累加运费 运费只需要酸一次就可以
                    order.total_amount += order.freight
                    order.save()#保存本次操作
            except Exception as e:
            #try里面出现任务问题，进行暴力回滚
                logger.error(e)
                transaction.get_connection(save_point1)
                return http.JsonResponse({'code': RETCODE.STOCKERR, 'errmsg': '提交订单失败'})
            else:
                #提交事务
                transaction.savepoint_commit(save_point1)

        #清楚购物车中已经购买过的商品
        pl = redis_conn.pipeline()#创建管道
        pl.hdel('carts_%s' % user.id, *cart_dict.keys())#删除hash中已经购买的所有key
        pl.delete("selected_%s" % user.id)#删除set集合中的勾选状态
        pl.execute()#执行管道
        #响应
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'order_id': order_id})




class OrderSuccessView(LoginRequired):

    def get(self, request):
        payment_amount = request.GET.get("payment_amount")
        order_id = request.GET.get('order_id')
        pay_method = request.GET.get('pay_method')
        try:
            OrderInfo.objects.get(order_id=order_id, pay_method=pay_method, total_amount=payment_amount, user=request.user)
        except OrderInfo.DoesNotExist:
            http.HttpResponseForbidden("订单信息错误")

        context={
            "payment_amount": payment_amount,
            "order_id": order_id,
            "pay_method ": pay_method
        }

        return render(request, "order_success.html", context)



