from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import now, make_aware, get_current_timezone
from django.db import models
from django.utils.dateparse import parse_datetime
from django.db.models import Count
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

from .models import Assignment, Attendance, Submission, Timetable, Notification, FeedbackForm, FeedbackResponse, Complaint

User = get_user_model()


def is_staff_user(user):
    return getattr(user, 'role', None) in ['staff', 'admin'] or getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)


# ✅ Attendance
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_attendance(request):
    data = Attendance.objects.all().values()
    return Response(data)


# ✅ Timetable
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_timetable(request):
    data = Timetable.objects.all().values()
    return Response(data)


# ✅ Assignments
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_assignments(request):
    data = Assignment.objects.all().values()
    return Response(data)


# ✅ Submit Assignment
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_assignment(request):
    student = request.user
    assignment_id = request.data.get('assignment_id')
    file = request.FILES.get('file')

    if not assignment_id:
        return Response({"error": "assignment_id required"}, status=400)

    try:
        assignment = Assignment.objects.get(id=assignment_id)
    except Assignment.DoesNotExist:
        return Response({"error": "Invalid assignment"}, status=400)

    if assignment.deadline < now().date():
        return Response({"error": "Deadline passed"}, status=400)

    if Submission.objects.filter(student=student, assignment=assignment).exists():
        return Response({"error": "Already submitted"}, status=400)

    Submission.objects.create(
        student=student,
        assignment=assignment,
        file=file
    )

    return Response({"message": "Submitted successfully"})


# ✅ Student Submissions
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_submissions(request):
    submissions = Submission.objects.filter(student=request.user)

    data = []
    for s in submissions:
        data.append({
            "assignment_id": s.assignment.id,
            "marks": s.marks,
            "feedback": s.feedback,
        })

    return Response(data)


# ✅ Staff View Submissions
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_submissions(request):
    submissions = Submission.objects.select_related('student', 'assignment')

    data = []
    for s in submissions:
        data.append({
            "id": s.id,
            "student_name": s.student.username,
            "subject": s.assignment.subject,
            "file": s.file.url,
            "submitted_at": s.submitted_at,
            "marks": s.marks,
            "feedback": s.feedback,
        })

    return Response(data)


# ✅ Grade Submission
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def grade_submission(request):
    submission_id = request.data.get("submission_id")
    marks = request.data.get("marks")
    feedback = request.data.get("feedback")

    if not submission_id or not marks:
        return Response({"error": "Missing data"}, status=400)

    try:
        submission = Submission.objects.get(id=submission_id)
    except Submission.DoesNotExist:
        return Response({"error": "Invalid submission"}, status=400)

    submission.marks = marks
    submission.feedback = feedback
    submission.save()

    return Response({"message": "Graded successfully"})


# ✅ GET NOTIFICATIONS
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    now_time = now()
    Notification.objects.filter(scheduled_time__lt=now_time).delete()

    notifications = Notification.objects.filter(
        models.Q(scheduled_time__isnull=True) | models.Q(scheduled_time__gte=now_time)
    )

    if request.user.role not in ['staff', 'admin']:
        notifications = notifications.filter(student=request.user)

    data = []
    for n in notifications:
        data.append({
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "file": n.file.url if n.file else None,
            "scheduled_time": n.scheduled_time,
        })

    return Response(data)


# ✅ CREATE NOTIFICATION
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_notification(request):
    title = request.data.get("title")
    message = request.data.get("message")

    department = request.data.get("department")
    year = request.data.get("year")
    section = request.data.get("section")

    scheduled_time_raw = request.data.get("scheduled_time")
    scheduled_time = None
    if scheduled_time_raw:
        parsed_scheduled_time = parse_datetime(scheduled_time_raw)
        if parsed_scheduled_time is not None:
            if parsed_scheduled_time.tzinfo is None:
                scheduled_time = make_aware(parsed_scheduled_time, get_current_timezone())
            else:
                scheduled_time = parsed_scheduled_time

    file = request.FILES.get("file")

    users = User.objects.filter(is_active=True)
    if department and department != 'all':
        users = users.filter(department=department)
    if year and year != 'all':
        users = users.filter(year=year)
    if section and section != 'all':
        users = users.filter(section=section)

    file_name = None
    file_content = None
    if file:
        file_name = file.name
        file_content = file.read()

    for user in users:
        notification = Notification(
            title=title,
            message=message,
            department=department,
            year=year,
            section=section,
            scheduled_time=scheduled_time,
            created_by=request.user,
            student=user 
        )
        if file and file_content is not None:
            notification.file.save(file_name, ContentFile(file_content), save=False)
        notification.save()

    return Response({"message": "Notification created"})


# ✅ CREATE TIMETABLE
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_timetable(request):
    if not is_staff_user(request.user):
        return Response({"error": "Permission denied"}, status=403)

    department = request.data.get("department")
    year = request.data.get("year")
    section = request.data.get("section")
    semester = request.data.get("semester")
    day = request.data.get("day")
    period = request.data.get("period")
    faculty_id = request.data.get("faculty_id")
    subject_code = request.data.get("subject_code")
    subject_name = request.data.get("subject_name")
    credits = request.data.get("credits")

    if not all([department, year, section, semester, day, period, faculty_id, subject_name, credits]):
        return Response({"error": "Missing required fields"}, status=400)

    try:
        faculty = User.objects.get(id=faculty_id, role='staff')
    except User.DoesNotExist:
        return Response({"error": "Invalid faculty"}, status=400)

    try:
        credits_value = int(credits)
    except (TypeError, ValueError):
        return Response({"error": "Invalid credits"}, status=400)

    period_to_time = {
        '1': '9:00-9:50',
        '2': '9:50-10:40',
        '4': '11:00-11:50',
        '5': '11:50-12:40',
        '7': '1:25-2:15',
        '8': '2:15-3:05',
        '10': '3:20-4:10',
        '11': '4:10-5:00',
    }
    time_value = period_to_time.get(str(period))
    if not time_value:
        return Response({"error": "Invalid period"}, status=400)

    Timetable.objects.create(
        department=department,
        year=year,
        section=section,
        semester=semester,
        subject_code=subject_code,
        subject=subject_name,
        faculty=faculty.get_full_name() or faculty.username,
        day=day,
        time=time_value,
        period=str(period),
        credits=credits_value,
    )

    return Response({"message": "Timetable entry created"})


# ✅ DELETE TIMETABLE
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_timetable(request, id):
    if not is_staff_user(request.user):
        return Response({"error": "Permission denied"}, status=403)

    try:
        timetable = Timetable.objects.get(id=id)
    except Timetable.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    timetable.delete()
    return Response({"message": "Deleted"})


# ✅ COUNT
# ✅ COUNT
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_count(request):
    now_time = now()
    Notification.objects.filter(scheduled_time__lt=now_time).delete()

    count = Notification.objects.filter(
        student=request.user,
        read=False
    ).filter(
        models.Q(scheduled_time__isnull=True) | models.Q(scheduled_time__gte=now_time)
    ).count()

    return Response({"count": count})


# ✅ MARK AS READ
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_as_read(request):
    now_time = now()
    Notification.objects.filter(scheduled_time__lt=now_time).delete()
    Notification.objects.filter(student=request.user).update(read=True)
    return Response({"message": "Done"})


# ✅ DELETE (FIXED SECURITY)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_notification(request, id):
    try:
        notification = Notification.objects.get(
            id=id,
            student=request.user   # ✅ FIX
        )
        notification.delete()
        return Response({"message": "Deleted"})
    except Notification.DoesNotExist:
        return Response({"error": "Not found"}, status=404)


# ✅ ATTENDANCE CALCULATION (FIXED)
def calculate_attendance_percentage(user):
    total = Attendance.objects.filter(student=user).count()

    present = Attendance.objects.filter(
        student=user,
        status='present'   # ✅ FIX
    ).count()

    if total == 0:
        return 0

    return (present / total) * 100


# ✅ ATTENDANCE API
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_attendance_percentage(request):
    percentage = calculate_attendance_percentage(request.user)
    return Response({"percentage": round(percentage, 2)})


# ✅ LOW ATTENDANCE CHECK (FIXED)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_low_attendance(request):

    users = User.objects.all()

    for user in users:
        records = Attendance.objects.filter(student=user)

        total = records.count()
        present = records.filter(status='present').count()

        if total == 0:
            continue

        percentage = (present / total) * 100

        if percentage < 75:
            exists = Notification.objects.filter(
                title="Low Attendance Warning",
                student=user
            ).exists()

            if not exists:
                Notification.objects.create(
                    title="Low Attendance Warning",
                    message=f"Your attendance is {percentage:.2f}%. Improve immediately.",
                    student=user,
                    created_by=request.user
                )

    return Response({"message": "Attendance checked"})


# ✅ FEEDBACK FORMS
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_feedback_forms(request):
    now_time = now()
    FeedbackForm.objects.filter(is_active=True, available_until__lt=now_time).update(is_active=False)

    user_role = getattr(request.user, 'role', None)
    if user_role == 'student':
        forms = FeedbackForm.objects.filter(is_active=True).filter(
            models.Q(department=request.user.department) | models.Q(department='all'),
            models.Q(year=request.user.year) | models.Q(year='all'),
            models.Q(section=request.user.section) | models.Q(section='all')
        )
        semester = request.query_params.get('semester')
        if semester:
            forms = forms.filter(semester=semester)
    else:
        forms = FeedbackForm.objects.all()

    data = []
    for form in forms:
        data.append({
            "id": form.id,
            "title": form.title,
            "description": form.description,
            "form_type": form.form_type,
            "department": form.department,
            "year": form.year,
            "section": form.section,
            "semester": form.semester,
            "subject_code": form.subject_code,
            "subject": form.subject,
            "faculty": form.faculty.username,
            "faculty_name": form.faculty.get_full_name(),
            "created_by": form.created_by.username,
            "available_until": form.available_until,
            "is_active": form.is_active,
        })

    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_feedback_form(request):
    if not is_staff_user(request.user):
        return Response({"error": "Permission denied"}, status=403)

    title = request.data.get("title")
    description = request.data.get("description")
    form_type = request.data.get("form_type", "semester")
    department = request.data.get("department")
    year = request.data.get("year")
    section = request.data.get("section")
    semester = request.data.get("semester")
    subject = request.data.get("subject")
    available_until_raw = request.data.get("available_until")

    if form_type == "course":
        form_type = "semester"

    if not all([title, department, year, section, semester, subject]):
        return Response({"error": "Missing required fields"}, status=400)

    available_until = None
    if available_until_raw:
        parsed_available_until = parse_datetime(available_until_raw)
        if parsed_available_until is not None:
            if parsed_available_until.tzinfo is None:
                available_until = make_aware(parsed_available_until, get_current_timezone())
            else:
                available_until = parsed_available_until

    form = FeedbackForm.objects.create(
        title=title,
        description=description,
        form_type=form_type,
        department=department,
        year=year,
        section=section,
        semester=semester,
        subject=subject,
        faculty=request.user,
        created_by=request.user,
        available_until=available_until,
    )

    return Response({"message": "Feedback form created", "id": form.id})
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_feedback_form(request, form_id):
    try:
        form = FeedbackForm.objects.get(id=form_id)
    except FeedbackForm.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    if not is_staff_user(request.user) and form.created_by != request.user:
        return Response({"error": "Permission denied"}, status=403)

    form.delete()
    return Response({"message": "Deleted"})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_feedback(request):
    if request.user.role != 'student':
        return Response({"error": "Only students can submit feedback"}, status=403)

    form_id = request.data.get("form_id")
    response_text = request.data.get("response_text")

    if not form_id or not response_text:
        return Response({"error": "Missing data"}, status=400)

    try:
        form = FeedbackForm.objects.get(id=form_id, is_active=True)
    except FeedbackForm.DoesNotExist:
        return Response({"error": "Invalid feedback form"}, status=400)

    FeedbackResponse.objects.create(
        form=form,
        student=request.user,
        response_text=response_text,
    )

    return Response({"message": "Feedback submitted"})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_complaint(request):
    if request.user.role != 'student':
        return Response({"error": "Only students can submit complaints"}, status=403)

    faculty_username = request.data.get("faculty_username")
    subject = request.data.get("subject")
    subject_code = request.data.get("subject_code")
    issue_type = request.data.get("issue_type")
    description = request.data.get("description")
    department = request.data.get("department")
    year = request.data.get("year")
    section = request.data.get("section")
    semester = request.data.get("semester")

    if not all([faculty_username, subject, issue_type, description, department, year, section, semester]):
        return Response({"error": "Missing complaint fields"}, status=400)

    try:
        faculty = User.objects.get(username=faculty_username, role='staff')
    except User.DoesNotExist:
        return Response({"error": "Invalid faculty"}, status=400)

    Complaint.objects.create(
        faculty_username=faculty.username,
        faculty_name=faculty.get_full_name(),
        department=department,
        year=year,
        section=section,
        semester=semester,
        subject_code=subject_code,
        subject=subject,
        issue_type=issue_type,
        description=description,
        student=request.user,
    )

    return Response({"message": "Complaint submitted"})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_faculties(request):
    faculties = User.objects.filter(role='staff').order_by('username')
    data = []
    for faculty in faculties:
        data.append({
            "id": faculty.id,
            "username": faculty.username,
            "full_name": faculty.get_full_name(),
            "department": faculty.department,
            "designation": faculty.designation,
            "role": faculty.role,
        })
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_feedback_results(request):
    # Only staff/admin can view results
    if not is_staff_user(request.user):
        return Response({"error": "Permission denied"}, status=403)

    forms = FeedbackForm.objects.all()

    data = []
    for form in forms:
        responses = FeedbackResponse.objects.filter(form=form)

        data.append({
            "form_id": form.id,
            "title": form.title,
            "subject": form.subject,
            "faculty": form.faculty.get_full_name() if form.faculty else None,
            "total_responses": responses.count(),
            "responses": [
                {
                    "student": r.student.username,
                    "response": r.response_text,
                }
                for r in responses
            ]
        })

    return Response(data)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_feedback_summary(request, form_id):
    try:
        form = FeedbackForm.objects.get(id=form_id)
    except FeedbackForm.DoesNotExist:
        return Response({"error": "Form not found"}, status=404)

    # Only staff/admin or creator can delete
    if not is_staff_user(request.user) and form.created_by != request.user:
        return Response({"error": "Permission denied"}, status=403)

    # Delete all responses linked to this form
    deleted_count, _ = FeedbackResponse.objects.filter(form=form).delete()

    return Response({
        "message": f"{deleted_count} feedback responses deleted successfully"
    })