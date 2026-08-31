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
        "edit/<int:pk>/",
        views.edit_produce,
        name="edit_produce",
    ),

    path(
        "delete/<int:pk>/",
        views.delete_produce,
        name="delete_produce",
    ),
]