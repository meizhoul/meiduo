from django.urls import path, re_path
from . import views



urlpatterns =[
    path("image_codes/<uuid>/",views.ImageCodeView.as_view()) ,#图像验证码
  # re_path(r'^image_codes/(?P<uuid>[\w-]+)/$', views.ImageCodeView.as_view()),
    path("sms_codes/<mobile>",views.SMSCodeView.as_view())#手机验证码

]