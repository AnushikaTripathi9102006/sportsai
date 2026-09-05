from django.urls import path
from . import views


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('farmer/', views.farmer_dashboard, name='farmer_dashboard'),
    path('officer/', views.officer_dashboard, name='officer_dashboard'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
]