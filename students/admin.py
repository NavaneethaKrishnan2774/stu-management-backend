from django.contrib import admin
from .models import Timetable, Attendance,Assignment,Submission

@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ('department', 'year', 'section', 'subject', 'faculty', 'day', 'time')
    list_filter = ('department', 'year', 'section', 'day')


admin.site.register(Attendance)
admin.site.register(Assignment)
admin.site.register(Submission)