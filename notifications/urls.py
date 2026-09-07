from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notifications, name="notifications"),
    path("<int:pk>/read/", views.mark_as_read, name="mark_as_read"),
    path("read-all/", views.mark_all_as_read, name="mark_all_as_read"),
    path("api/unread-count/", views.unread_count_api, name="unread_count_api"),
]
