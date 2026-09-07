from django.urls import path
from . import views

app_name = "appointments"

urlpatterns = [
    path("", views.appointments, name="appointments"),
    path("book/", views.book_appointment, name="book_appointment"),
    path("reschedule/<int:pk>/", views.reschedule_appointment, name="reschedule_appointment"),
    path("detail/<int:pk>/", views.appointment_detail, name="appointment_detail"),
    path("cancel/<int:pk>/", views.cancel_appointment, name="cancel_appointment"),
]
