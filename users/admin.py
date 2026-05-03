from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from .models import StaffRegistration, User


@admin.register(StaffRegistration)
class StaffRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'email',
        'id_number',
        'department',
        'designation',
        'status',
        'created_at',
        'approved_by',
    )
    list_filter = ('status', 'department', 'designation', 'created_at')
    search_fields = ('name', 'email', 'id_number', 'department', 'designation')
    readonly_fields = (
        'status',
        'approved_by',
        'approved_at',
        'created_at',
        'updated_at',
        'password',
    )

    fieldsets = (
        ('Personal Information', {
            'fields': (
                'name',
                'dob',
                'age',
                'mobile',
                'email',
                'blood_group',
                'address',
            )
        }),
        ('Professional Information', {
            'fields': (
                'id_number',
                'department',
                'designation',
                'joining_year',
                'qualification',
                'experience',
                'room_number',
                'subjects',
            )
        }),
        ('Files', {
            'fields': ('photo_filename',)
        }),
        ('Authentication', {
            'fields': ('password',)
        }),
        ('Approval Status', {
            'fields': (
                'status',
                'approved_by',
                'approved_at',
                'rejection_reason',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_registrations', 'reject_registrations']

    def approve_registrations(self, request, queryset):
        approved_count = 0
        for registration in queryset.filter(status='pending'):
            try:
                # Create user account using create_user to properly hash password
                user = User.objects.create_user(
                    username=registration.id_number,
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

                # Set additional flags based on designation
                if registration.designation == 'hod':
                    user.role = 'hod'
                elif registration.designation == 'faculty_fa':
                    user.is_faculty_fa = True
                elif registration.designation == 'faculty_subject':
                    user.is_subject_holder = True
                elif registration.designation == 'placement_officer':
                    user.is_placement_officer = True

                user.save()

                # Update registration status
                registration.status = 'approved'
                registration.approved_by = request.user
                registration.approved_at = timezone.now()
                registration.save()
                
                approved_count += 1

            except Exception as e:
                self.message_user(request, f"Error approving {registration.name}: {str(e)}", level='error')

        if approved_count > 0:
            self.message_user(request, f"Successfully approved {approved_count} registrations.")

    approve_registrations.short_description = "✓ Approve selected registrations"

    def reject_registrations(self, request, queryset):
        pending_regs = queryset.filter(status='pending')

        if not pending_regs:
            self.message_user(request, "No pending registrations to reject.", level='warning')
            return

        rejection_reason = "Rejected by admin"
        for registration in pending_regs:
            registration.status = 'rejected'
            registration.approved_by = request.user
            registration.approved_at = timezone.now()
            registration.rejection_reason = rejection_reason
            registration.save()

        self.message_user(request, f"Rejected {pending_regs.count()} registrations.")

    reject_registrations.short_description = "✗ Reject selected registrations"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {
            'fields': (
                'first_name',
                'last_name',
                'email',
                'salutation',
                'department',
                'section',
            )
        }),
        (_('Role info'), {'fields': ('role', 'designation')}),
        (_('Faculty (FA) info'), {
            'fields': (
                'is_faculty_fa',
                'faculty_advisor_class',
                'faculty_fa_department',
                'faculty_fa_year',
                'faculty_fa_section',
                'faculty_fa_from_date',
                'faculty_fa_to_date',
            )
        }),
        (_('Subject Holder info'), {
            'fields': (
                'is_subject_holder',
                'subject_holder_class_count',
                'subject_holder_department',
                'subject_holder_year',
                'subject_holder_section',
            )
        }),
        (_('Permissions'), {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            )
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'role',
                'designation',
                'salutation',
                'department',
                'section',
                'is_faculty_fa',
                'faculty_advisor_class',
                'faculty_fa_department',
                'faculty_fa_year',
                'faculty_fa_section',
                'faculty_fa_from_date',
                'faculty_fa_to_date',
                'is_subject_holder',
                'subject_holder_class_count',
                'subject_holder_department',
                'subject_holder_year',
                'subject_holder_section',
                'password1',
                'password2',
            ),
        }),
    )
    list_display = (
        'username',
        'email',
        'role',
        'designation',
        'is_faculty_fa',
        'is_subject_holder',
        'department',
        'section',
        'salutation',
        'faculty_advisor_class',
        'faculty_fa_department',
        'faculty_fa_year',
        'faculty_fa_section',
        'subject_holder_class_count',
        'is_staff',
    )
    list_filter = (
        'role',
        'designation',
        'department',
        'section',
        'faculty_fa_department',
        'faculty_fa_year',
        'faculty_fa_section',
        'salutation',
        'is_faculty_fa',
        'is_subject_holder',
    )
    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
        'designation',
        'department',
        'section',
        'faculty_advisor_class',
        'faculty_fa_department',
        'faculty_fa_year',
        'subject_holder_department',
        'faculty_fa_section',
        'subject_holder_section',
    )
    ordering = ('username',)
