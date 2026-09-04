from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("", views.payments, name="payments"),
    path("detail/<int:payment_id>/", views.payment_detail, name="detail"),
]
