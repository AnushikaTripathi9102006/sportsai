from django.contrib.auth.models import User
from rest_framework import generics, permissions, status, views, viewsets
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from produce.models import Produce

from .permissions import ApprovedFarmerPermission
from .serializers import (
    LoginSerializer,
    ProduceSerializer,
    ProfileSerializer,
    RegistrationSerializer,
)


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegistrationSerializer

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        resp_data = response.data or {}
        user = User.objects.get(username=resp_data["username"])
        profile = user.profile
        response.data = {
            "message": "Registration successful.",
            "username": user.username,
            "role": profile.role,
            "is_approved": profile.is_approved,
            "farmer_id": profile.farmer_id,
        }
        return response


class LoginView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        val_data = serializer.validated_data or {}
        user = val_data["user"]
        refresh = RefreshToken.for_user(user)
        profile = user.profile
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": profile.role,
                "farmer_id": profile.farmer_id,
                "is_approved": profile.is_approved,
            },
        })


class LogoutView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "A refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh_token).blacklist()
        except Exception:
            return Response(
                {"detail": "Invalid refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user.profile


class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user.profile


class DashboardView(views.APIView):
    permission_classes = [ApprovedFarmerPermission]

    def get(self, request):
        profile = request.user.profile
        return Response({
            "username": request.user.username,
            "full_name": request.user.get_full_name(),
            "farmer_id": profile.farmer_id,
            "produce_count": Produce.objects.filter(
                farmer=request.user
            ).count(),
        })


class ProduceViewSet(viewsets.ModelViewSet):
    serializer_class = ProduceSerializer
    permission_classes = [ApprovedFarmerPermission]

    def get_queryset(self):
        return Produce.objects.filter(
            farmer=self.request.user
        ).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(farmer=self.request.user)

    def perform_update(self, serializer):
        if self.get_object().status != "AVAILABLE":
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                "Only available produce can be edited."
            )
        serializer.save()

    def perform_destroy(self, instance):
        if instance.status != "AVAILABLE":
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                "Only available produce can be deleted."
            )
        instance.delete()
