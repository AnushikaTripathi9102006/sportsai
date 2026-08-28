from django.urls import path
from . import views
from .views import pending_approval

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path(
    'pending-approval/',
    pending_approval,
    name='pending_approval'
),
]