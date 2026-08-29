from django.urls import path
from . import views


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('farmer/', views.farmer_dashboard, name='farmer_dashboard'),
   
]