from django.urls import path
from . import views

urlpatterns=[
    path('hot/<int:category_id>/', views.HotGoodsView.as_view()),
    path('list/<int:category_id>/<int:page_num>/', views.ListView.as_view()),
    path('detail/<int:sku_id>/', views.DetailView.as_view()),
    path('detail/visit/<int:category_id>/', views.DetailVisitView.as_view()),

]