from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


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
        'subject_holder_class_count',
        'is_staff',
    )
    list_filter = (
        'role',
        'designation',
        'department',
        'section',
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
        'subject_holder_department',
        'faculty_fa_section',
        'subject_holder_section',
    )
    ordering = ('username',)
