from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    designation = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        username = data['username']
        password = data['password']
        user = authenticate(
            username=username,
            password=password
        )

        if not user:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                user = None

            if user and user.password and '$' not in user.password and user.password == password:
                user.set_password(password)
                user.save()
                user = authenticate(username=username, password=password)

        if not user:
            raise serializers.ValidationError("Invalid credentials")

        designation = data.get('designation')
        if designation:
            if designation != user.role:
                if user.role == 'staff':
                    normalized_designation = str(user.designation or '').strip().lower()
                    if designation == 'staff':
                        pass
                    elif designation == user.designation:
                        pass
                    elif designation == 'faculty_fa' and (
                        getattr(user, 'is_faculty_fa', False)
                        or normalized_designation in ('faculty (fa)', 'faculty_fa', 'faculty fa')
                    ):
                        pass
                    elif designation == 'faculty_subject' and (
                        getattr(user, 'is_subject_holder', False)
                        or 'subject' in normalized_designation
                    ):
                        pass
                    else:
                        raise serializers.ValidationError("Designation does not match the user role")
                else:
                    raise serializers.ValidationError("Designation does not match the user role")

        return {
            'user': user
        }