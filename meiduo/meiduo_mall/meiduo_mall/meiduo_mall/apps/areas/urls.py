from django.urls import path
from . import views
urlpatterns =[
    #获取QQ登陆连接
    path('areas/', views.AreaView.as_view()),
]