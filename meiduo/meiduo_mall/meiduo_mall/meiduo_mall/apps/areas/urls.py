from django.urls import path
from . import views
urlpatterns =[
    #省区市三级联动
    path('areas/', views.AreaView.as_view()),
]