from django.urls import path
from . import views
urlpatterns=[
    path('carts/', views.CartsView.as_view()),#购物车增删改
    path('carts/selection/', views.CartsSelectedAllView.as_view()),
    path('carts/simple/', views.CartsSimpleView.as_view()),#简单版购物车
]