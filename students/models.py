from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

DAY_CHOICES = [
    ('Monday', 'Monday'),
    ('Tuesday', 'Tuesday'),
    ('Wednesday', 'Wednesday'),
    ('Thursday', 'Thursday'),
    ('Friday', 'Friday'),
    ('Saturday', 'Saturday'),
]

TIME_CHOICES = [
    ('9:00-9:50', '9:00-9:50'),
    ('9:50-10:40', '9:50-10:40'),
    ('11:00-11:50', '11:00-11:50'),
    ('11:50-12:40', '11:50-12:40'),
    ('1:25-2:15', '1:25-2:15'),
    ('2:15-3:05', '2:15-3:05'),
    ('3:20-4:10', '3:20-4:10'),
    ('4:10-5:00', '4:10-5:00'),
]

DEPARTMENT_CHOICES = [
    ('CSE', 'CSE'),
    ('ECE', 'ECE'),
    ('EEE', 'EEE'),
    ('MECH', 'MECH'),
    ('CIVIL', 'CIVIL'),
]

YEAR_CHOICES = [
    ('1', '1st Year'),
    ('2', '2nd Year'),
    ('3', '3rd Year'),
    ('4', '4th Year'),
]

SECTION_CHOICES = [
    ('A', 'A'),
    ('B', 'B'),
    ('C', 'C'),
]

SEMESTER_CHOICES = [
    ('1', 'Semester 1'),
    ('2', 'Semester 2'),
    ('3', 'Semester 3'),
    ('4', 'Semester 4'),
    ('5', 'Semester 5'),
    ('6', 'Semester 6'),
    ('7', 'Semester 7'),
    ('8', 'Semester 8'),
]

PERIOD_CHOICES = [
    ('P1', 'Period 1'),
    ('P2', 'Period 2'),
    ('P3', 'Period 3'),
    ('P4', 'Period 4'),
    ('P5', 'Period 5'),
    ('P6', 'Period 6'),
    ('P7', 'Period 7'),
    ('P8', 'Period 8'),
]


class Timetable(models.Model):
    department = models.CharField(max_length=10, choices=DEPARTMENT_CHOICES, default="CSE")
    year = models.CharField(max_length=1, choices=YEAR_CHOICES)
    section = models.CharField(max_length=1, choices=SECTION_CHOICES)
    semester = models.CharField(max_length=1, choices=SEMESTER_CHOICES, default="1")
    subject_code = models.CharField(max_length=20, blank=True, null=True)

    subject = models.CharField(max_length=100)
    faculty = models.CharField(max_length=100)

    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    time = models.CharField(max_length=20, choices=TIME_CHOICES)
    period = models.CharField(max_length=3, choices=PERIOD_CHOICES, default="P1")
    credits = models.PositiveIntegerField(default=0)


STATUS_CHOICES = (
    ('present', 'Present'),
    ('absent', 'Absent'),
)


class Attendance(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)


class Assignment(models.Model):
    department = models.CharField(max_length=10)
    year = models.CharField(max_length=1)
    section = models.CharField(max_length=1)

    subject = models.CharField(max_length=100)
    description = models.TextField()

    file = models.FileField(upload_to='assignments/')
    deadline = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)


class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    marks = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)

    file = models.FileField(upload_to='submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)


# ✅ FIXED NOTIFICATION MODEL
class Notification(models.Model):
    title = models.CharField(max_length=255)
    message = models.TextField()

    department = models.CharField(max_length=50)
    year = models.CharField(max_length=10)
    section = models.CharField(max_length=10)

    scheduled_time = models.DateTimeField(null=True, blank=True)

    file = models.FileField(upload_to="notifications/", null=True, blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications_created"
    )

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        related_name="notifications_received"
    )

    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class FeedbackForm(models.Model):
    FORM_CHOICES = [
        ('semester', 'Semester Feedback'),
        ('event', 'Event Feedback'),
        ('course', 'Course Feedback'),
        ('faculty', 'Faculty Feedback'),
        ('general', 'General Feedback'),
        ('complaint', 'Complaint'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    form_type = models.CharField(max_length=20, choices=FORM_CHOICES, default='semester')
    department = models.CharField(max_length=10, choices=DEPARTMENT_CHOICES)
    year = models.CharField(max_length=1, choices=YEAR_CHOICES)
    section = models.CharField(max_length=1, choices=SECTION_CHOICES)
    semester = models.CharField(max_length=1, choices=SEMESTER_CHOICES, default='1')
    subject_code = models.CharField(max_length=20, blank=True, null=True)
    subject = models.CharField(max_length=100)
    faculty = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='feedback_forms'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_feedback_forms'
    )
    available_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)


class FeedbackResponse(models.Model):
    form = models.ForeignKey(
        FeedbackForm,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='feedback_responses'
    )
    response_text = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)


class Complaint(models.Model):
    faculty_username = models.CharField(max_length=100)
    faculty_name = models.CharField(max_length=150, blank=True, null=True)
    department = models.CharField(max_length=10, choices=DEPARTMENT_CHOICES)
    year = models.CharField(max_length=1, choices=YEAR_CHOICES)
    section = models.CharField(max_length=1, choices=SECTION_CHOICES)
    semester = models.CharField(max_length=1, choices=SEMESTER_CHOICES, default='1')
    subject_code = models.CharField(max_length=20, blank=True, null=True)
    subject = models.CharField(max_length=100)
    issue_type = models.CharField(
        max_length=20,
        choices=[
            ('understanding', 'Lack of Understanding'),
            ('teaching', 'Teaching Methodology'),
            ('faculty', 'Faculty Behavior'),
            ('other', 'Other Academic Issue'),
        ],
        default='understanding'
    )
    description = models.TextField()
    status = models.CharField(max_length=20, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='complaints'
    )
