from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    DashboardView,
    LoginView,
    LogoutView,
    MeView,
    ProduceViewSet,
    ProfileView,
    RegisterView,
)

router = DefaultRouter()
router.register("produce", ProduceViewSet, basename="produce")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="api-register"),
    path("auth/login/", LoginView.as_view(), name="api-login"),
    path("auth/logout/", LogoutView.as_view(), name="api-logout"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/me/", MeView.as_view(), name="api-me"),
    path("profile/", ProfileView.as_view(), name="api-profile"),
    path("dashboard/", DashboardView.as_view(), name="api-dashboard"),
    path("", include(router.urls)),
]
