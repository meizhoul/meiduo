from django.urls import path
from . import views

urlpatterns =[
    #注册
    path("register/",views.RegisterView.as_view(),name="register"),
    # path("register/",views.RegisterView.as_view()),

    # 用户名是否重复注册
    # url(r'^usernames/(?P<username>[a-zA-Z0-9_-]{5,20})/count/$', views.UsernameCountView.as_view()),
    # 用户名是否重复注册
    path("usernames/<str:username>/count/", views.UsernameCountView.as_view()),
    #手机号是否重复注册
    path("mobiles/<mobile:mobile>/count/", views.MobileCountView.as_view()),
    #登陆界面
    path("login/",views.LoginView.as_view()),
    #退出登陆
    path("logout/",views.LogoutView.as_view()),
    #用户中心
    path("info/",views.UserInfoView.as_view()),
    #邮箱设置
    path("emails/", views.EmailView.as_view()),
    #激活用户邮箱
    path("emails/verification/", views.VerifyEmaiView.as_view()),
    #收获地址
    path("addresses/", views.AddressViwe.as_view()),
    #用户新增地址
    path("addresses/create/",views.CreateAddressView.as_view()),
    #用户修改删除地址
    path("addresses/<int:address_id>/",views.UpdateDestroyAddressView.as_view()),
    #设置默认收获地址
    path("addresses/<int:address_id>/default/",views.DefultAddressView.as_view()),
    #修改用户收获地址标题
    path("addresses/<int:address_id>/title/",views.UpdateTiteAddressView.as_view()),
    #修改密码
    path("password/",views.ChangePasswordView.as_view()),
]
