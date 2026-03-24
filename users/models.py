from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    # Staff field
    designation = models.CharField(max_length=50, blank=True, null=True)

    # Student fields
    department = models.CharField(max_length=10, blank=True, null=True)
    year = models.CharField(max_length=1, blank=True, null=True)
    section = models.CharField(max_length=1, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"