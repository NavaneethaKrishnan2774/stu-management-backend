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
        ('faculty_fa', 'Faculty (FA)'),
        ('faculty_subject', 'Faculty (Subject Holder)'),
        ('librarian', 'Librarian'),
        ('placement_officer', 'Placement Officer'),
        ('association_advisor', 'Association Advisor'),
        ('hostel_warden', 'Hostel Warden'),
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
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

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

    is_placement_officer = models.BooleanField(
        default=False,
        verbose_name='Placement Officer',
        help_text='Mark this user as Placement Officer',
    )

    # Student fields
    department = models.CharField(max_length=15, choices=DEPARTMENT_CHOICES, blank=True, null=True)
    year = models.CharField(max_length=10, choices=YEAR_CHOICES, blank=True, null=True)
    section = models.CharField(max_length=1, choices=SECTION_CHOICES, blank=True, null=True)
    semester = models.CharField(max_length=1, choices=[
        ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'), ('8', '8')
    ], blank=True, null=True)
    cgpa = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    current_arrears = models.PositiveIntegerField(default=0)
    arrears_history = models.TextField(blank=True, null=True)  # JSON or text description
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    job_offers_count = models.PositiveIntegerField(default=0)
    mobile = models.CharField(max_length=15, blank=True, null=True)
    
    # Additional student profile fields
    date_of_birth = models.DateField(blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)  # Auto-calculated from DOB
    parent_mobile = models.CharField(max_length=15, blank=True, null=True)
    register_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    year_of_joining = models.CharField(max_length=4, blank=True, null=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    residential_address = models.TextField(blank=True, null=True)
    blood_group = models.CharField(max_length=5, choices=[
        ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'), 
        ('AB+', 'AB+'), ('AB-', 'AB-'), ('O+', 'O+'), ('O-', 'O-')
    ], blank=True, null=True)
    advisor_faculty_id = models.CharField(max_length=20, blank=True, null=True)
    emergency_contact = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


class StaffRegistration(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    # Personal Information
    name = models.CharField(max_length=100)
    dob = models.DateField()
    age = models.CharField(max_length=3)
    mobile = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(unique=True)
    address = models.TextField(blank=True, null=True)
    blood_group = models.CharField(max_length=5, blank=True, null=True)

    # Professional Information
    department = models.CharField(max_length=15, choices=User.DEPARTMENT_CHOICES)
    designation = models.CharField(max_length=50, choices=User.DESIGNATION_CHOICES)
    id_number = models.CharField(max_length=20, unique=True)
    joining_year = models.CharField(max_length=4)
    subjects = models.TextField(blank=True, null=True)
    subjects_handled = models.TextField(blank=True, null=True)
    semester_handling = models.CharField(max_length=100, blank=True, null=True)
    class_incharge_details = models.CharField(max_length=255, blank=True, null=True)
    experience = models.CharField(max_length=50, blank=True, null=True)
    room_number = models.CharField(max_length=20, blank=True, null=True)
    qualification = models.CharField(max_length=100, blank=True, null=True)
    department_managed = models.CharField(max_length=100, blank=True, null=True)
    hostel_name = models.CharField(max_length=100, blank=True, null=True)
    block_assigned = models.CharField(max_length=100, blank=True, null=True)
    floor_assigned = models.CharField(max_length=100, blank=True, null=True)
    hostel_type = models.CharField(max_length=50, blank=True, null=True)
    duty_timing = models.CharField(max_length=100, blank=True, null=True)
    official_whatsapp = models.CharField(max_length=50, blank=True, null=True)
    industry_experience = models.CharField(max_length=100, blank=True, null=True)
    companies_coordinated = models.TextField(blank=True, null=True)
    library_id = models.CharField(max_length=50, blank=True, null=True)
    section_managed = models.CharField(max_length=100, blank=True, null=True)
    shift_timing = models.CharField(max_length=100, blank=True, null=True)
    association_name = models.CharField(max_length=100, blank=True, null=True)
    certifications = models.TextField(blank=True, null=True)
    account_approval_status = models.CharField(max_length=50, blank=True, null=True)
    username = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True)
    emergency_contact = models.CharField(max_length=15, blank=True, null=True)

    # File uploads
    profile_photo = models.FileField(upload_to='staff_registration/profile_photos/', blank=True, null=True)
    id_card = models.FileField(upload_to='staff_registration/id_cards/', blank=True, null=True)
    qualification_certificates = models.FileField(upload_to='staff_registration/qualification_certificates/', blank=True, null=True)
    resume = models.FileField(upload_to='staff_registration/resumes/', blank=True, null=True)
    appointment_order = models.FileField(upload_to='staff_registration/appointment_orders/', blank=True, null=True)
    photo_filename = models.CharField(max_length=255, blank=True, null=True)

    # Status
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    password = models.CharField(max_length=128)  # Will be hashed when creating user

    # Admin approval fields
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_registrations')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.designation} ({self.status})"

    class Meta:
        ordering = ['-created_at']