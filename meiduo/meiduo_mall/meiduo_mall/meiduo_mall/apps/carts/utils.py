import pickle, base64
from django_redis import get_redis_connection

def merge_cart_cookie_to_redis(request,response):
    """登陆时合并购物车数据"""
    #获取cookie中购物车的数据
    cart_str = request.COOKIES.get("carts")
    #判断是否有cookie购物车数据
    if cart_str is None:
        #如果没有，提前结束函数运行
        return
    #将字符串转字典
    cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
    #创建redis连接对象
    redis_conn = get_redis_connection("carts")
    user = request.user
    pl = redis_conn.pipeline()
    #遍历从cookie购物车数据字典
    for sku_id in cart_dict:
        #sku_id和count向redis的Hash添加
            pl.hset("carts_%s" % user.id, sku_id,cart_dict[sku_id]['count'])
        #判断cookie中当前商品是勾选还是不勾选
            if cart_dict[sku_id]['selected']:
                #勾选就将sku_id向redis的set添加
                pl.sadd('selectde_%s' % user.id, sku_id)
            else:
                #不勾选就将sku_id从redis的set中删除
                pl.srem('selectde_%s' % user.id, sku_id)
    pl.execute()
    #将cookie购物车数据删除
    response.delete_cookie("carts")