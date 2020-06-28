"""meiduo_mall URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include,register_converter,re_path

from meiduo_mall.apps.verifications.rewrite_urls import MobileConverter

register_converter(MobileConverter, 'mobile')


urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include(("users.urls","users"),namespace="users")),
    path("", include(("contents.urls","contents"), namespace="contents")),

    path("", include("verifications.urls")),
    path("", include("oauth.urls")),
    path("",include("areas.urls")),
    path("", include(('goods.urls', 'goods'), namespace="goods")),
    path("", include(('carts.urls', 'carts'), namespace="carts")),
    path("", include(("orders.urls", 'orders'), namespace="orders")),
    path('search/', include('haystack.urls')),#全文检索
    path("", include(("payment.urls", 'payment'), namespace="payment"))#支付宝
    # re_path(r'^', include('verifications.urls')),
]
