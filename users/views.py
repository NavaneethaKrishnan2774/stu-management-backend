from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializer
from .models import StaffRegistration, User
from django.utils import timezone

class LoginView(APIView):

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data['user']

            refresh = RefreshToken.for_user(user)

            return Response({
                "access": str(refresh.access_token),
                "role": user.role,
                "designation": user.designation,
                "department": user.department,
                "year": user.year,
                "section": user.section,
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StaffRegistrationView(APIView):
    def post(self, request):
        data = request.data

        # Check if email or id_number already exists
        if User.objects.filter(email=data.get('email')).exists():
            return Response({"error": "Email already registered"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=data.get('id_number')).exists():
            return Response({"error": "ID Number already exists"}, status=status.HTTP_400_BAD_REQUEST)

        if data.get('username'):
            if User.objects.filter(username=data.get('username')).exists():
                return Response({"error": "Username already registered"}, status=status.HTTP_400_BAD_REQUEST)
            if StaffRegistration.objects.filter(username=data.get('username')).exists():
                return Response({"error": "Registration already pending for this username"}, status=status.HTTP_400_BAD_REQUEST)

        if StaffRegistration.objects.filter(email=data.get('email')).exists():
            return Response({"error": "Registration already pending for this email"}, status=status.HTTP_400_BAD_REQUEST)

        if StaffRegistration.objects.filter(id_number=data.get('id_number')).exists():
            return Response({"error": "Registration already pending for this ID Number"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            registration = StaffRegistration.objects.create(
                name=data['name'],
                username=data.get('username') or data['id_number'],
                dob=data['dob'],
                age=data['age'],
                gender=data.get('gender'),
                department=data.get('department'),
                designation=data['designation'],
                mobile=data.get('mobile'),
                emergency_contact=data.get('emergency_contact'),
                id_number=data['id_number'],
                joining_year=data['joining_year'],
                address=data.get('address'),
                blood_group=data.get('blood_group'),
                department_managed=data.get('department_managed'),
                subjects=data.get('subjects'),
                subjects_handled=data.get('subjects_handled'),
                semester_handling=data.get('semester_handling'),
                class_incharge_details=data.get('class_incharge_details'),
                experience=data.get('experience'),
                room_number=data.get('room_number'),
                qualification=data.get('qualification'),
                hostel_name=data.get('hostel_name'),
                block_assigned=data.get('block_assigned'),
                floor_assigned=data.get('floor_assigned'),
                hostel_type=data.get('hostel_type'),
                duty_timing=data.get('duty_timing'),
                official_whatsapp=data.get('official_whatsapp'),
                industry_experience=data.get('industry_experience'),
                companies_coordinated=data.get('companies_coordinated'),
                library_id=data.get('library_id'),
                section_managed=data.get('section_managed'),
                shift_timing=data.get('shift_timing'),
                association_name=data.get('association_name'),
                certifications=data.get('certifications'),
                account_approval_status=data.get('account_approval_status', 'pending'),
                email=data['email'],
                password=data['password'],  # Will be hashed when creating user
                profile_photo=request.FILES.get('profile_photo'),
                id_card=request.FILES.get('id_card'),
                qualification_certificates=request.FILES.get('qualification_certificates'),
                resume=request.FILES.get('resume'),
                appointment_order=request.FILES.get('appointment_order'),
            )

            return Response({
                "success": True,
                "message": "Registration submitted for admin approval",
                "id": registration.id
            })

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminStaffRegistrationsView(APIView):
    def get(self, request):
        if request.user.role != 'admin':
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        registrations = StaffRegistration.objects.all().order_by('-created_at')
        data = []

        for reg in registrations:
            data.append({
                "id": reg.id,
                "name": reg.name,
                "email": reg.email,
                "department": reg.department,
                "designation": reg.designation,
                "id_number": reg.id_number,
                "status": reg.status,
                "created_at": reg.created_at,
                "approved_by": reg.approved_by.username if reg.approved_by else None,
                "approved_at": reg.approved_at,
                "rejection_reason": reg.rejection_reason,
            })

        return Response(data)


class AdminApproveStaffRegistrationView(APIView):
    def post(self, request, registration_id):
        if request.user.role != 'admin':
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        try:
            registration = StaffRegistration.objects.get(id=registration_id)
        except StaffRegistration.DoesNotExist:
            return Response({"error": "Registration not found"}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action')  # 'approve' or 'reject'

        if action == 'approve':
            # Create the user account using create_user to properly hash password
            user = User.objects.create_user(
                username=registration.username or registration.id_number,
                email=registration.email,
                password=registration.password,  # create_user hashes this automatically
                first_name=registration.name.split()[0] if registration.name else '',
                last_name=' '.join(registration.name.split()[1:]) if len(registration.name.split()) > 1 else '',
                role='staff',
                designation=registration.designation,
                department=registration.department,
                mobile=registration.mobile,
                is_active=True,
            )

            # Set HOD as a dedicated role, other staff stay as staff with role-specific flags
            if registration.designation == 'hod':
                user.role = 'hod'
            elif registration.designation == 'faculty_fa':
                user.is_faculty_fa = True
            elif registration.designation == 'faculty_subject':
                user.is_subject_holder = True
            elif registration.designation == 'placement_officer':
                user.is_placement_officer = True

            user.save()

            registration.status = 'approved'
            registration.approved_by = request.user
            registration.approved_at = timezone.now()
            registration.save()

            return Response({"message": f"Staff registration approved. User {user.username} can now login."})

        elif action == 'reject':
            rejection_reason = request.data.get('rejection_reason', '')
            registration.status = 'rejected'
            registration.approved_by = request.user
            registration.approved_at = timezone.now()
            registration.rejection_reason = rejection_reason
            registration.save()

            return Response({"message": "Staff registration rejected."})

        else:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)


class StaffRegistrationStatusView(APIView):
    def get(self, request):
        email = request.query_params.get('email')
        id_number = request.query_params.get('id_number')

        if not email and not id_number:
            return Response({"error": "email or id_number parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if email:
                registration = StaffRegistration.objects.get(email=email)
            else:
                registration = StaffRegistration.objects.get(id_number=id_number)
        except StaffRegistration.DoesNotExist:
            return Response({"error": "Registration not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "id": registration.id,
            "name": registration.name,
            "email": registration.email,
            "department": registration.department,
            "role": registration.designation,
            "status": registration.status,
            "rejection_reason": registration.rejection_reason,
            "approved_by": registration.approved_by.username if registration.approved_by else None,
            "approved_at": registration.approved_at,
            "created_at": registration.created_at,
        })