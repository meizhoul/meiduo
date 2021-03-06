from django.shortcuts import render

from django.shortcuts import render, redirect
from django.db import DatabaseError
from django.urls import reverse
from django.contrib.auth import authenticate
from django.contrib.auth import login, logout
from django.views import View
from django import http
from django.contrib.auth import mixins
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import DatabaseError
from django_redis import get_redis_connection

from .models import User, Address

import re
import json
import logging

from meiduo_mall.utils.response_code import RETCODE
from meiduo_mall.utils.views import LoginRequired
from celery_tasks.email.tasks import send_verify_email
from .utils import generate_verify_email_url,check_verify_email
from goods.models import SKU
from carts.utils import merge_cart_cookie_to_redis

logger = logging.getLogger("django")

class RegisterView(View):
    """用户注册"""

    def get(self, request):
        """
        提供注册界面
        :param request: 请求对象
        :return: 注册界面
        """
        return render(request, 'register.html')

    def post(self, request):
        """
        实现用户注册
        :param request: 请求对象
        :return: 注册结果
        """
        # 1.接收参数
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        sms_code_client = request.POST.get('sms_code')
        allow = request.POST.get('allow')

        # 2.校验参数
        # 2.1 判断参数是否齐全
        if not all([username, password, password2, mobile, sms_code_client, allow]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 2.2 判断用户名是否是5-20个字符
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入5-20个字符的用户名')
        # 2.3 判断密码是否是8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')
        # 2.4 判断两次密码是否一致
        if password != password2:
            return http.HttpResponseForbidden('两次输入的密码不一致')
        # 2.5 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号码')


        if allow != 'on':
            return http.HttpResponseForbidden('请勾选用户协议')

        # 3. 保存注册数据
        try:
            user = User.objects.create_user(username=username, password=password, mobile=mobile)
        except DatabaseError:
            return render(request, 'register.html', {'register_errmsg': '注册失败'})

        # 4. 登入用户，实现状态保持
        login(request, user)

        # 5. 响应注册结果
        response = redirect(reverse('contents:index'))

        return response


class UsernameCountView(View):
    """判断用户名是否重复"""
    def get(self, request, username):

        # 查询user表, 查询username的数量
        count = User.objects.filter(username=username).count()

        # 包装响应数据
        data = {
            'count': count,
            'code': RETCODE.OK,  # 自定义状态码
            'errmsg': 'OK'
        }
        # 响应
        return http.JsonResponse(data)


class MobileCountView(View):
    """判断手机号是否重复"""
    def get(self, request, mobile):

        # 查询user表, 查询mobile的数量
        count = User.objects.filter(mobile=mobile).count()

        # 包装响应数据
        data = {
            'count': count,
            'code': RETCODE.OK,  # 自定义状态码
            'errmsg': 'OK'
        }
        # 响应
        return http.JsonResponse(data)

class LoginView(View):
    """用户登陆 """

    def get(self,request):
        """www.baidu.com"
        提供登陆界面
        :param request: 请求对象
        :return: 登陆界面
        """
        return render(request,"login.html")

    def post(self,request):
        """
        登陆逻辑
        :param request:
        :return:
        """
        #接受请求参数
        username = request.POST.get("username")
        password = request.POST.get("password")
        remembered = request.POST.get("remembered")
        #校验参数
        #2.1判断参数是否齐全
        if not all([username,password]):
            return http.HttpResponseForbidden("缺少必传参数")
        #2.2判断用户名是否5-20个字符
        if not re.match(r'^[a-zA-z0-9_-]{5,20}$',username):
            return http.HttpResponseForbidden("请输入正确的用户名或手机号")
        #2.3判断秘密是否8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$',password):
            return http.HttpResponseForbidden("密码最少8位，最长20位")

        # 认证成功
        """authentica封装好了一系列的用户验证 查询数据库，所以直接调用就可以"""
        user = authenticate(username=username,password=password)
        if user is None:
            return render(request,"login.html",{"accouny_errmsg":"用户名或密码错误"})

        # 保持登陆状态
        login(request,user)

        #设置状态保持的周期
        if remembered != 'on':
            #没有记住用户：浏览器会话结束就过期
            request.session.set_expiry(0)
        #获取用户界面来源
        next = request.GET.get("next")
        response = redirect(next or '/')
        # response = redirect((reverse('contents:index')))#创建重定向响应对象
        response.set_cookie('username', user.username, max_age=remembered and settings.SESSION_COOKIE_AGE)
        #购物车合并
        merge_cart_cookie_to_redis(request,response)
        return response


class LogoutView(View):
    """退出登录"""

    def get(self,request):
        """退出登陆逻辑"""
        #清除session
        logout(request)
        #退出登陆重定向到登陆页
        response = redirect('/login/')#重定向到login
        # response = redirect(reverse('users:login'))#报错
        # response = redirect(reverse('contents:index'))#不报错重定向到index首页
        # response = redirect('/')#不报错重定向到index首页
        #推出登陆时清楚cookie中的username
        response.delete_cookie("username")
        return response

class UserInfoView(mixins.LoginRequiredMixin,View):
    """用户中心"""

    def get(self,request):
        '''提供邮箱验证信息'''

        return render(request, "user_center_info.html")


class EmailView(LoginRequired):
    """设置用户邮箱"""

    def put(self,request):
        #接受数据
        json_dict = json.loads(request.body.decode())
        email = json_dict.get("email")
        #校验
        if email is None:
            return http.HttpResponseForbidden("缺少必传参数")
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return http.HttpResponseForbidden("邮箱格式不正确")
        #业务处理
        user = request.user
        User.objects.filter(id=user.id, email="").update(email=email)
        # #生成激活url
        # verify_url = generate_verify_email_url(user)
        # #异步发送邮件
        # send_verify_email.delay(email, verify_url)
        # #响应
        # return http.JsonResponse({"code":RETCODE.OK,"errmsg":"OK"})
        verify_url = generate_verify_email_url(user)
        # celery异步发邮件
        send_verify_email.delay(email, verify_url)
        # 响应
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


class VerifyEmaiView(View):
    """激活用户邮箱"""
    def get(self,request):
        #获取查询参数中的token
        token = request.GET.get("token")
        #校验
        if token is None:
            return http.HttpResponseForbidden("缺少token")
        #解密
        user = check_verify_email(token)
        if user is None:
            return http.HttpResponseForbidden("token无效")
        #修改字段
        user.email_active = True
        user.save()
        #响应
        return redirect("/info/")


class AddressViwe(LoginRequired):
    """用户收货地址"""

    def get(self, request):
        user = request.user #获取当前用户
        address_qs = Address.objects.filter(user=user,is_deleted=False)
        address_list = []#用来装用户所有收获地址
        for address in address_qs:
            address_dict = {
                'id': address.id,
                'title': address.title,
                'receiver': address.receiver,
                'province_id': address.province_id,
                'province': address.province.name,
                'city_id': address.city_id,
                'city': address.city.name,
                'district_id': address.district_id,
                'district': address.district.name,
                'place': address.place,
                'mobile': address.mobile,
                'tel': address.tel,
                'email': address.email,
            }
            address_list.append(address_dict)
        context ={
                "addresses": address_list,
                "default_address_id":user.default_address_id
            }
        return render(request, 'user_center_site.html', context)





class CreateAddressView(LoginRequiredMixin,View):
    """新增地址"""
    def post(self,request):
        #判断用户收获地址不超过20个
        user = request.user
        #查询当前登陆用户未被逻辑删除的收获地址
        count = Address.objects.filter(user=user, is_deleted=False).count()

        if count >= 20:
            return http.JsonResponse({'code':RETCODE.MAXNUM, 'errmsg': '收获地址超限'})

        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        #校验
        if all([receiver,province_id,city_id,district_id,place,mobile]) is False:
            return http.HttpResponseForbidden("缺少必传参数")

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')

        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')

        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')
        #新增
        try:
            address = Address.objects.create(
                user=user,
                title=title,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )

        except DatabaseError as e:
            logger.error(e)
            return http.HttpResponseForbidden("添加收获地址失败")


        if user.default_address is None:
            user.default_address = address
            user.save()

        adderss_dict={
            'id': address.id,
            'title': address.title,
            'receiver': address.receiver,
            'province_id': address.province_id,
            'province': address.province.name,
            'city_id': address.city_id,
            'city': address.city.name,
            'district_id': address.district_id,
            'district': address.district.name,
            'place': address.place,
            'mobile': address.mobile,
            'tel': address.tel,
            'email': address.email,
        }

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '添加收货地址成功', 'address': adderss_dict})


class UpdateDestroyAddressView(LoginRequired):
    """修改删除收货地址"""
    def put(self,request,address_id):
        """修改收获地址逻辑"""
        #对assress_id进行校验
        try:
             #校验address_id校验当前登陆用户未必逻辑删除的收获地址
            address = Address.objects.get(id=address_id, user=request.user, is_deleted=False)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden("修改收获地址失败")

        #接受请求体
        json_dict = json.loads(request.body.decode())
        title = json_dict.get("title")
        receiver = json_dict.get("receiver")
        province_id = json_dict.get("province_id")
        city_id = json_dict.get("city_id")
        district_id = json_dict.get("district_id")
        place = json_dict.get("place")
        mobile = json_dict.get("mobile")
        tel = json_dict.get("tel")
        email = json_dict.get("email")

        #校验
        if all([title,receiver,province_id,city_id,district_id,place,mobile]) is False:
            return http.HttpResponseForbidden("缺少必传参数")

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')



        #修改
        try:
            address.title = title
            address.receiver = receiver
            address.province_id = province_id
            address.city_id = city_id
            address.district_id = district_id
            address.place = place
            address.mobile = mobile
            address.tel = tel
            address.email = email
            address.save()
        except DatabaseError as e:
            logger.error(e)
            return http.HttpResponseForbidden('修改收货地址失败')

        #把新增的address模型对象转换成字典,并响应给前端
        address_dict = {
            'id': address.id,
            'title': address.title,
            'receiver': address.receiver,
            'province_id': address.province_id,
            'province': address.province.name,
            'city_id': address.city_id,
            'city': address.city.name,
            'district_id': address.district_id,
            'district': address.district.name,
            'place': address.place,
            'mobile': address.mobile,
            'tel': address.tel,
            'email': address.email,
        }
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '修改收货地址成功', 'address': address_dict})


    def delete(self,request,address_id):
        """收获地址删除"""
        try:
            address=Address.objects.get(id=address_id,user=request.user,is_deleted=False)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden('删除收货地址失败')

        address.is_deleted= True#逻辑删除
        address.save()

        #address.delete()#物理删除

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


class DefultAddressView(LoginRequired):
    """设置默认地址"""
    def put(self,request,address_id):

       try:
            address= Address.objects.get(id=address_id,user=request.user,is_deleted=False)

       except Address.DoesNotExist:
           return http.HttpResponseForbidden("设置默认收货地址失败")

       request.user.default_address = address #给用户默认收获地址设置新值
       request.user.save()

       return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


class UpdateTiteAddressView(LoginRequired):
    """修改用户收获地址标题"""
    def put(self,request,address_id):

        try:
            address = Address.objects.get(id=address_id,users=request.user, is_deleted=False)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden("设置用户收获地址标题失败")

        json_dict = json.loads(request.body.decode())
        title = json_dict.get("title")

        if title is None:
            return http.HttpResponseForbidden("缺少必传参数")

        address.title = title
        address.save()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


class ChangePasswordView(LoginRequired):
    """修改密码"""

    def get(self,request):
        return render(request,"user_center_pass.html")


    def post(self,request):
        #接受表单
        old_pwd = request.POST.get("old_pwd")
        new_pwd = request.POST.get("new_pwd")
        new_cpwd = request.POST.get("new_cpwd")
        #校验
        if all([old_pwd,new_pwd,new_cpwd]) is False:
            return http.HttpResponseForbidden("缺少必传参数'")
        #修改密码
        if request.user.check_password(old_pwd) is False:
            return render(request,'user_center_pass.html',{"origin_pwd_errmsg":"原始密码不正确"})

        if not re.match('^[0-9A-Za-z]{8,20}$', new_pwd):
            return http.HttpResponseForbidden("请输入8-20位长度的密码")

        if new_pwd != new_cpwd:
            return http.HttpResponseForbidden("两次密码输入的不一致")

        request.user.set_password(new_pwd)
        request.user.save()

        #重定向login
        return redirect('/logout')
        #响应


class HisoryGoodsView(View):
    """商品浏览记录"""

    def post(self,request):
        """保存商品浏览记录"""
        #判断用户是是否登陆
        if not request.user.is_authenticated:
            return http.JsonResponse({"code": RETCODE.SESSIONERR,"errmsg": "用户未登录"})

        #获取请求体中的sku_id
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')

        #校验
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden("sku_id无效")

        #创建redis连接对象
        redis_conn = get_redis_connection("history")

        #创建管道
        pl = redis_conn.pipeline()
        #存储每个用户的redis的唯一key

        key = "history_%s" % request.user.id
        #先去重
        pl.lrem(key, 0, sku_id)
        #添加到列表的开头
        pl.lpush(key,sku_id)
        #保留列表中的前5个元素
        pl.ltrim(key, 0, 4)
        #执行管道
        pl.execute()
        #响应
        return http.JsonResponse({'code':RETCODE.OK,'errmsg': 'OK'})

    def get(self,request):
        #判断用户是否登陆
        if not request.user.is_authenticated:
            return http.JsonResponse({"code": RETCODE.SESSIONERR,"errmsg": "用户未登录"})

        #创建redis连接对象
        redis_conn = get_redis_connection("history")
        #存储每个用户redis的唯一key
        key = "history_%s" % request.user.id
        #获取当前用户的浏览记录数据
        sku_id_list = redis_conn.lrange(key, 0, -1)
        #定义一个列表,用来装sku字典数据
        sku_list =[]
        #遍历sku_id列表，有顺序的一个一个去获取SKU模型并转换成字典
        for sku_id in sku_id_list:
            sku = SKU.objects.get(id=sku_id)
            sku_list.append({
                "id": sku.id,
                "name":sku.name,
                "price":sku.price,
                "default_image_url":sku.default_image.url
            })
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'skus': sku_list})

