from django.urls import path
from . import views  
from .views import delete_notification # ✅ THIS LINE IS IMPORTANT

urlpatterns = [
    path('attendance/', views.get_attendance),
    path('timetable/', views.get_timetable),
    path('timetables/', views.get_timetable),
    path('create-timetable/', views.create_timetable),
    path('delete-timetable/<int:id>/', views.delete_timetable),
    path('assignments/', views.get_assignments),
    path('submit/', views.submit_assignment),
    path('my-submissions/', views.my_submissions), 
    path('submissions/', views.get_submissions),
    path('grade/', views.grade_submission),
    path('notifications/', views.get_notifications),
    path('create-notification/', views.create_notification),
    path('notification-count/', views.notification_count),
    path('mark-read/', views.mark_as_read),
    path('delete-notification/<int:id>/', views.delete_notification),
    path('feedback-forms/', views.get_feedback_forms),
    path('create-feedback-form/', views.create_feedback_form),
    path('delete-feedback-form/<int:form_id>/', views.delete_feedback_form),
    path('submit-feedback/', views.submit_feedback),
    path('submit-complaint/', views.submit_complaint),
    path('available-faculties/', views.get_available_faculties),
    path('attendance-percentage/', views.get_attendance_percentage),
    path('check-attendance/', views.check_low_attendance),
]