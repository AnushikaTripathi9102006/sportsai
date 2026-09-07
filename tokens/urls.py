from django.urls import path
from . import views

app_name = "tokens"

urlpatterns = [
    path("", views.token_queue, name="token_queue"),
    path("call-next/", views.call_next_token_view, name="call_next_token"),
    path("verify/<uuid:qr_uuid>/", views.verify_token_view, name="verify_token"),
]
