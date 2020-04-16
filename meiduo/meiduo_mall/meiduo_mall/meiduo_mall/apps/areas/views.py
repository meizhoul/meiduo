from django.shortcuts import render
from django.views import View
from django import http
from django.core.cache import cache

from .models import Area
from meiduo_mall.utils.response_code import RETCODE


class AreaView(View):
    """省市区数据查询"""
    def get(self,request):
        """获取查询参数area_id"""
        area_id = request.GET.get("area_id")
        #判断area_id是否有值
        if area_id is None:
            #先尝试去redis获取所有省的缓存
            province_list = cache.get("province_list")
            #如果缓存中没有取到所有省数据，就去mysql查询
            if province_list is None:
                province_qs = Area.objects.filter(parent=None)
                province_list = []#用来装所有省的数据字典
                for province_model in province_qs:
                    #遍历查询集，将里面的每一个模型转换成字典
                    province_list.append({
                        "id":province_model.id,
                        "name":province_model.name

                    })
                    cache.set("province_list",province_list,3600)
                return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'ok', 'province_list': province_list})


        #如果area_id为None 说明查询的是所有省

        else:
            #先去缓存读写数据，如果缓存中没有在去mysql
            data_dict = cache.get("sub_area"+area_id)
            if data_dict is None:
                #如果area_id有值，代表查询指定area_id的下级所有行政区
                province_model = Area.objects.get(id=area_id)#获取当前指定行政区
                sub_qs = province_model.subs.all()#获取指定行政区的所有下级行政区
                sub_list = []#包装所有下级行政区
                for sub_model in sub_qs:
                    sub_list.append({
                        "id": sub_model.id,
                        "name": sub_model.name
                    })

                #包装要响应的数据
                data_dict= {
                    'id': province_model.id,
                    'name': province_model.name,
                    'subs': sub_list
                }
                #设置缓存
                cache.set("sub_area"+area_id, data_dict, 3600)
            return http.JsonResponse({"code": RETCODE.OK, 'errmsg': 'ok', 'sub_data': data_dict})
