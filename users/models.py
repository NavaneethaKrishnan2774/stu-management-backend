from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    SALUTATION_CHOICES = (
        ('mr', 'Mr'),
        ('ms', 'Ms'),
        ('mrs', 'Mrs'),
    )

    ROLE_CHOICES = (
        ('student', 'Student'),
        ('staff', 'Staff'),
        ('hod', 'HOD'),
        ('admin', 'Admin'),
    )

    DESIGNATION_CHOICES = (
        ('assistant_professor', 'Assistant Professor'),
        ('associate_professor', 'Associate Professor'),
        ('professor', 'Professor'),
        ('hod', 'HOD'),
        ('other', 'Other'),
    )

    DEPARTMENT_CHOICES = (
        ('CSE', 'CSE'),
        ('ECE', 'ECE'),
        ('MECH', 'MECH'),
        ('CIVIL', 'CIVIL'),
        ('EEE', 'EEE'),
        ('MECHANICAL', 'MECHANICAL'),
    )

    YEAR_CHOICES = (
        ('FY', 'First Year'),
        ('SY', 'Second Year'),
        ('TY', 'Third Year'),
        ('Final', 'Final Year'),
    )

    SECTION_CHOICES = (
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
    )

    salutation = models.CharField(max_length=10, choices=SALUTATION_CHOICES, blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    # Staff field
    designation = models.CharField(max_length=50, choices=DESIGNATION_CHOICES, blank=True, null=True)
    is_faculty_fa = models.BooleanField(
        default=False,
        verbose_name='Faculty (FA)',
        help_text='Mark this user as Faculty (FA) advisor',
    )
    faculty_advisor_class = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Faculty (FA) Advisor Class',
        help_text='Class or section managed by the Faculty (FA)',
    )
    faculty_fa_department = models.CharField(
        max_length=15,
        choices=DEPARTMENT_CHOICES,
        blank=True,
        null=True,
        verbose_name='Faculty (FA) Department',
    )
    faculty_fa_year = models.CharField(
        max_length=10,
        choices=YEAR_CHOICES,
        blank=True,
        null=True,
        verbose_name='Faculty (FA) Year',
    )
    faculty_fa_section = models.CharField(
        max_length=1,
        choices=SECTION_CHOICES,
        blank=True,
        null=True,
        verbose_name='Faculty (FA) Section',
    )
    faculty_fa_from_date = models.DateField(blank=True, null=True, verbose_name='Faculty (FA) From Date')
    faculty_fa_to_date = models.DateField(blank=True, null=True, verbose_name='Faculty (FA) To Date')

    is_subject_holder = models.BooleanField(
        default=False,
        verbose_name='Faculty (Subject Holder)',
        help_text='Mark this user as Faculty (Subject Holder)',
    )
    subject_holder_class_count = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Subject Holder Class Count',
        help_text='Number of classes handled as a subject holder',
    )
    subject_holder_department = models.CharField(
        max_length=15,
        choices=DEPARTMENT_CHOICES,
        blank=True,
        null=True,
        verbose_name='Subject Holder Department',
    )
    subject_holder_year = models.CharField(
        max_length=10,
        choices=YEAR_CHOICES,
        blank=True,
        null=True,
        verbose_name='Subject Holder Year',
    )
    subject_holder_section = models.CharField(
        max_length=1,
        choices=SECTION_CHOICES,
        blank=True,
        null=True,
        verbose_name='Subject Holder Section',
    )

    # Student fields
    department = models.CharField(max_length=15, choices=DEPARTMENT_CHOICES, blank=True, null=True)
    year = models.CharField(max_length=10, choices=YEAR_CHOICES, blank=True, null=True)
    section = models.CharField(max_length=1, choices=SECTION_CHOICES, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"