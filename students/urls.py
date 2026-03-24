from django.urls import path
from .views import get_assignments, get_attendance, get_timetable, submit_assignment

urlpatterns = [
    path('attendance/', get_attendance),
    path('timetable/', get_timetable),
    path('assignments/', get_assignments),
    path('submit/', submit_assignment),
]