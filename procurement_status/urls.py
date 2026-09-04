from django.urls import path

from . import views

app_name = "procurement_status"

urlpatterns = [
    path("", views.procurement_status, name="status"),
    path("detail/", views.procurement_detail, name="detail"),
]
