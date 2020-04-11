from django.urls import path
from . import views
urlpatterns =[
    #获取QQ登陆连接
    path('qq/authorization/', views.OAuthURLView.as_view()),
    path('oauth_callback/', views.QQAuthUserViwe.as_view()),
]