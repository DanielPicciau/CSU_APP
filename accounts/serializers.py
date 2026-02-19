"""
Serializers for the accounts app.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Profile

User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile."""

    class Meta:
        model = Profile
        fields = ["date_format", "default_timezone", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data."""

    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "profile", "date_joined"]
        read_only_fields = ["id", "date_joined"]


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = ["email", "password", "password_confirm", "first_name", "last_name"]
        extra_kwargs = {
            "first_name": {"required": False},
            "last_name": {"required": False},
        }

    def validate(self, attrs):
        """Validate that passwords match."""
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        """Create a new user."""
        validated_data.pop("password_confirm")
        user = User.objects.create_user(**validated_data)
        return user


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change."""

    old_password = serializers.CharField(
        required=True,
        style={"input_type": "password"},
    )
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        """Validate passwords."""
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )
        return attrs

    def validate_old_password(self, value):
        """Validate current password."""
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating profile."""

    class Meta:
        model = Profile
        fields = ["date_format", "default_timezone"]


class RecordInjectionSerializer(serializers.Serializer):
    """Serializer for recording an injection date on a biologic medication."""

    medication_id = serializers.IntegerField()
    injection_date = serializers.DateField()

    def validate_medication_id(self, value):
        from .models import UserMedication

        user = self.context["request"].user
        try:
            med = UserMedication.objects.get(pk=value, user=user)
        except UserMedication.DoesNotExist:
            raise serializers.ValidationError("Medication not found.")
        if med.medication_type != "biologic":
            raise serializers.ValidationError("Only biologic medications support injection tracking.")
        self._medication = med
        return value

    def validate_injection_date(self, value):
        # Future injection dates are allowed (scheduled injections)
        return value

    def save(self):
        med = self._medication
        med.last_injection_date = self.validated_data["injection_date"]
        med.save(update_fields=["last_injection_date", "updated_at"])
        return med
