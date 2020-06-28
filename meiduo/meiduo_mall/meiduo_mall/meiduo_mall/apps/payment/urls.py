from django.urls import path
from . import views
urlpatterns=[
    path('payment/<int:order_id>/', views.PaymentView.as_view()),
    path('payment/status/', views.PaymentStausView.as_view()),#验证支付结果
]