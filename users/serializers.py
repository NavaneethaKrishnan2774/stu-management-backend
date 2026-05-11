from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    designation = serializers.CharField(required=False, allow_blank=True, allow_null=True, default='')

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            raise serializers.ValidationError("Username and password are required")

        # Try to find the user
        user = None

        # First try direct username
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Try register_number
            try:
                user = User.objects.get(register_number=username)
            except User.DoesNotExist:
                # Try email
                if '@' in username:
                    try:
                        user = User.objects.get(email=username)
                    except User.DoesNotExist:
                        pass

        if not user:
            raise serializers.ValidationError("Invalid credentials")

        # Check if user is active
        if not user.is_active:
            raise serializers.ValidationError("Account is disabled")

        # Check password manually
        from django.contrib.auth.hashers import check_password
        if not check_password(password, user.password):
            raise serializers.ValidationError("Invalid credentials")

        return {
            'user': user
        }