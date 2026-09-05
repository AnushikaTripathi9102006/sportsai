from django.urls import path

from . import views


app_name = "produce"

urlpatterns = [
    path("", views.my_produce, name="my_produce"),
  
     path(
        "add/",
        views.add_produce,
        name="add_produce",
    ),

    path(
        "detail/<int:pk>/",
        views.produce_detail,
        name="produce_detail",
    ),

    path(
        "edit/<int:pk>/",
        views.edit_produce,
        name="edit_produce",
    ),

    path(
        "delete/<int:pk>/",
        views.delete_produce,
        name="delete_produce",
    ),

    path(
        "request/<int:pk>/",
        views.request_procurement,
        name="request_procurement",
    ),
]