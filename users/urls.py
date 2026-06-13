from django.urls import path
from .views import (
    LoginView,
    StudentRegistrationView,
    StaffRegistrationView,
    StaffRegistrationStatusView,
    AdminStaffRegistrationsView,
    AdminApproveStaffRegistrationView,
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/student/', StudentRegistrationView.as_view(), name='student_registration'),
    path('register/staff/', StaffRegistrationView.as_view(), name='staff_registration'),
    path('register/staff-status/', StaffRegistrationStatusView.as_view(), name='staff_registration_status'),
    path('admin/staff-registrations/', AdminStaffRegistrationsView.as_view(), name='admin_staff_registrations'),
    path('admin/approve-staff/<int:registration_id>/', AdminApproveStaffRegistrationView.as_view(), name='admin_approve_staff'),
]
