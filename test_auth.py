import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms_backend.settings')
django.setup()

from users.models import User
from django.contrib.auth import authenticate

# Get a staff user
staff_user = User.objects.filter(role='staff').first()
if staff_user:
    print(f"User: {staff_user.username}")
    print(f"Password hash: {staff_user.password}")
    print(f"Is active: {staff_user.is_active}")

    # Try to authenticate
    auth_result = authenticate(username=staff_user.username, password='password')
    print(f"Authenticate result: {auth_result}")

    # Try manual password check
    from django.contrib.auth.hashers import check_password
    manual_check = check_password('password', staff_user.password)
    print(f"Manual password check: {manual_check}")
else:
    print("No staff user found")