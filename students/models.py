from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL
DAY_CHOICES = [
    ('Monday', 'Monday'),
    ('Tuesday', 'Tuesday'),
    ('Wednesday', 'Wednesday'),
    ('Thursday', 'Thursday'),
    ('Friday', 'Friday'),
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


class Timetable(models.Model):
    department = models.CharField(max_length=10, choices=DEPARTMENT_CHOICES,default="CSE")
    year = models.CharField(max_length=1, choices=YEAR_CHOICES)
    section = models.CharField(max_length=1, choices=SECTION_CHOICES)

    subject = models.CharField(max_length=100)
    faculty = models.CharField(max_length=100)

    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    time = models.CharField(max_length=20, choices=TIME_CHOICES)


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

    file = models.FileField(upload_to='submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)