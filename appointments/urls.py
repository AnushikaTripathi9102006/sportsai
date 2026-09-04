from django.urls import path

from . import views


app_name = "appointments"

urlpatterns = [
    path("", views.appointments, name="appointments"),
    path("detail/", views.appointment_detail, name="appointment_detail"),
    path("book/", views.book_appointment, name="book_appointment"),
]
