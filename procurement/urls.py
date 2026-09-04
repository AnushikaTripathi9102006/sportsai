from django.urls import path

from . import views

app_name = "procurement"

urlpatterns = [
    path("centers/", views.centers, name="centers"),
    path("centers/details/", views.center_detail, name="center_detail"),
    path("centers/confirm/", views.confirm_center, name="confirm_center"),
    path("status/", views.status, name="status"),
    path("status/detail/", views.status_detail, name="status_detail"),
]
