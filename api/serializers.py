from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.models import Profile
from produce.models import Produce


class RegistrationSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(
        choices=["FARMER", "OFFICER"],
        write_only=True,
    )

    class Meta:
        model = User
        fields = ["username", "email", "role", "password1", "password2"]

    def validate(self, attrs):
        if attrs["password1"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password2": "The passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        role = validated_data.pop("role")
        password = validated_data.pop("password1")
        validated_data.pop("password2")
        user = User.objects.create_user(password=password, **validated_data)
        profile = user.profile
        profile.role = role
        profile.is_approved = role == "FARMER"
        profile.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs["username"],
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError("Invalid username or password.")

        profile = getattr(user, "profile", None)
        if profile is None:
            raise serializers.ValidationError("User profile is not available.")
        if not profile.is_approved:
            raise serializers.ValidationError(
                {"approval": "Your account is waiting for approval."}
            )

        attrs["user"] = user
        return attrs


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Profile
        fields = [
            "username",
            "email",
            "role",
            "farmer_id",
            "is_approved",
            "phone",
            "village",
            "district",
            "preferred_language",
        ]
        read_only_fields = ["role", "farmer_id", "is_approved"]


class ProduceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Produce
        fields = [
            "id",
            "crop_name",
            "quantity",
            "unit",
            "harvest_date",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "created_at",
            "updated_at",
        ]
