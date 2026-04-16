from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import now, make_aware, get_current_timezone
from django.db import models
from django.utils.dateparse import parse_datetime
from django.db.models import Count
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

from .models import Assignment, Attendance, StaffAttendance, Submission, Timetable, Notification, FeedbackForm, FeedbackResponse, Complaint

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
    role = getattr(request.user, 'role', None)
    department = request.GET.get('department')
    year = request.GET.get('year')
    section = request.GET.get('section')
    semester = request.GET.get('semester')

    if role == 'student':
        department = request.user.department
        year = request.user.year
        section = request.user.section
        entries = Timetable.objects.filter(
            approval_status='approved',
            department=department,
            year=year,
            section=section,
        )
        if semester:
            entries = entries.filter(semester=semester)
    elif _is_hod_user(request.user):
        department = request.user.department
        entries = Timetable.objects.filter(department=department).exclude(approval_status='draft')
        if year:
            entries = entries.filter(year=year)
        if section:
            entries = entries.filter(section=section)
        if semester:
            entries = entries.filter(semester=semester)
    else:
        entries = Timetable.objects.filter(created_by=request.user)
        if _is_faculty_fa_user(request.user):
            assignment = _get_faculty_fa_assignment(request.user)
            if assignment:
                assigned_department, assigned_year, assigned_section = assignment
                entries = entries | Timetable.objects.filter(
                    department=assigned_department,
                    year=assigned_year,
                    section=assigned_section
                )
        if department:
            entries = entries.filter(department=department)
        if year:
            entries = entries.filter(year=year)
        if section:
            entries = entries.filter(section=section)
        if semester:
            entries = entries.filter(semester=semester)

    entries = entries.distinct()

    data = []
    for item in entries:
        data.append({
            "id": item.id,
            "department": item.department,
            "year": item.year,
            "section": item.section,
            "semester": item.semester,
            "subject_code": item.subject_code,
            "subject": item.subject,
            "faculty": item.faculty,
            "faculty_id": item.faculty_user.id if item.faculty_user else None,
            "created_by": item.created_by.username if item.created_by else None,
            "approved_by": item.approved_by.username if item.approved_by else None,
            "approved_at": item.approved_at,
            "is_approved": item.is_approved,
            "approval_status": item.approval_status,
            "hod_comment": item.hod_comment,
            "day": item.day,
            "time": item.time,
            "period": item.period,
            "credits": item.credits,
        })
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
    if _is_faculty_fa_user(request.user):
        assignment = _get_faculty_fa_assignment(request.user)
        if assignment:
            department, year, section = assignment
            submissions = Submission.objects.select_related('student', 'assignment').filter(
                student__department=department,
                student__year=year,
                student__section=section,
            )
        else:
            submissions = Submission.objects.none()
    else:
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

    if _is_faculty_fa_user(request.user):
        assignment = _get_faculty_fa_assignment(request.user)
        if assignment and not (
            submission.student.department == assignment[0] and
            submission.student.year == assignment[1] and
            submission.student.section == assignment[2]
        ):
            return Response({"error": "Permission denied: cannot grade this submission"}, status=403)

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

    if request.user.role != 'admin':
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

    department = request.data.get("department", "all")
    year = request.data.get("year", "all")
    section = request.data.get("section", "all")
    target = request.data.get("target", "all").lower()

    if _is_hod_user(request.user) and getattr(request.user, 'department', None):
        department = request.user.department

    if _is_faculty_fa_user(request.user):
        if target != 'students':
            return Response({"error": "Permission denied: FA can only send student notifications"}, status=403)
        permission_denied = _faculty_fa_class_permission(request, department, year, section, allow_all=False)
        if permission_denied:
            return permission_denied

    scheduled_time_raw = request.data.get("scheduled_time")
    scheduled_time = None
    if scheduled_time_raw:
        parsed_scheduled_time = parse_datetime(scheduled_time_raw)
        if parsed_scheduled_time is not None:
            if parsed_scheduled_time.tzinfo is None:
                scheduled_time = make_aware(parsed_scheduled_time, get_current_timezone())
            else:
                scheduled_time = parsed_scheduled_time

    staff_ids = []
    if hasattr(request.data, 'getlist'):
        staff_ids = request.data.getlist('staff_ids')
    else:
        staff_ids = request.data.get('staff_ids') or []

    if isinstance(staff_ids, str):
        staff_ids = [value.strip() for value in staff_ids.split(',') if value.strip()]
    staff_ids = [int(value) for value in staff_ids if str(value).isdigit()]

    if not title or not title.strip() or not message or not message.strip():
        return Response({"error": "Title and message are required."}, status=400)

    users = User.objects.filter(is_active=True)
    if target == "students":
        users = users.filter(role='student')
        if year not in [None, '', 'all']:
            users = users.filter(year=year)
        if section not in [None, '', 'all']:
            users = users.filter(section=section)
    elif target == "staff":
        users = users.filter(role='staff')
        if staff_ids:
            users = users.filter(id__in=staff_ids)
    elif target == "all":
        pass
    else:
        return Response({"error": "Invalid target selection."}, status=400)

    if department and department != 'all':
        users = users.filter(department=department)
    if year and year != 'all':
        users = users.filter(year=year)
    if section and section != 'all':
        users = users.filter(section=section)

    if target == 'staff' and staff_ids and users.count() == 0:
        return Response({"error": "No staff members found for the selected staff IDs."}, status=400)
    if target == 'students' and users.count() == 0:
        return Response({"error": "No student recipients found for the selected year/section."}, status=400)
    if target == 'all' and users.count() == 0:
        return Response({"error": "No recipients found."}, status=400)

    file = request.FILES.get("file")
    file_name = None
    file_content = None
    if file:
        file_name = file.name
        file_content = file.read()

    for user in users:
        notification = Notification(
            title=title.strip(),
            message=message.strip(),
            department=department,
            year=year,
            section=section,
            scheduled_time=scheduled_time,
            created_by=request.user,
            student=user,
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

    if _is_faculty_fa_user(request.user):
        permission_denied = _faculty_fa_class_permission(request, department, year, section, allow_all=False)
        if permission_denied:
            return permission_denied

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

    entry = Timetable.objects.create(
        department=department,
        year=year,
        section=section,
        semester=semester,
        subject_code=subject_code,
        subject=subject_name,
        faculty=faculty.get_full_name() or faculty.username,
        faculty_user=faculty,
        created_by=request.user,
        is_approved=getattr(request.user, 'role', None) in ['hod', 'admin'],
        approval_status='approved' if getattr(request.user, 'role', None) in ['hod', 'admin'] else 'draft',
        approved_by=request.user if getattr(request.user, 'role', None) in ['hod', 'admin'] else None,
        approved_at=now() if getattr(request.user, 'role', None) in ['hod', 'admin'] else None,
        day=day,
        time=time_value,
        period=str(period),
        credits=credits_value,
    )

    return Response({"message": "Timetable entry created", "id": entry.id})


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

    if _is_faculty_fa_user(request.user):
        assignment = _get_faculty_fa_assignment(request.user)
        if assignment and not (
            timetable.department == assignment[0] and
            timetable.year == assignment[1] and
            timetable.section == assignment[2]
        ):
            return Response({"error": "Permission denied: cannot delete timetable for other class"}, status=403)

    if timetable.approval_status == 'approved':
        return Response({"error": "Cannot delete approved timetable entry"}, status=403)

    timetable.delete()
    return Response({"message": "Deleted"})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_sent_notifications(request):
    permission_denied = _hod_permissions(request)
    if permission_denied:
        return permission_denied

    notifications = Notification.objects.filter(created_by=request.user).order_by('-id')
    data = []
    for n in notifications:
        data.append({
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "department": n.department,
            "year": n.year,
            "section": n.section,
            "scheduled_time": n.scheduled_time,
            "file": n.file.url if n.file else None,
            "recipient_role": n.student.role if n.student else None,
            "recipient_username": n.student.username if n.student else None,
            "recipient_id": n.student.id if n.student else None,
        })

    return Response(data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def hod_edit_notification(request, id):
    if not _is_hod_user(request.user):
        return Response({"error": "Permission denied"}, status=403)

    try:
        notification = Notification.objects.get(id=id, created_by=request.user)
    except Notification.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    notification.title = request.data.get("title", notification.title)
    notification.message = request.data.get("message", notification.message)
    notification.year = request.data.get("year", notification.year)
    notification.section = request.data.get("section", notification.section)
    if getattr(request.user, 'department', None):
        notification.department = request.user.department

    scheduled_time_raw = request.data.get("scheduled_time")
    if scheduled_time_raw:
        parsed_scheduled_time = parse_datetime(scheduled_time_raw)
        if parsed_scheduled_time is not None:
            if parsed_scheduled_time.tzinfo is None:
                notification.scheduled_time = make_aware(parsed_scheduled_time, get_current_timezone())
            else:
                notification.scheduled_time = parsed_scheduled_time

    file = request.FILES.get("file")
    if file:
        notification.file.save(file.name, ContentFile(file.read()), save=False)

    notification.save()
    return Response({"message": "Notification updated"})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def hod_delete_notification(request, id):
    if not _is_hod_user(request.user):
        return Response({"error": "Permission denied"}, status=403)

    try:
        notification = Notification.objects.get(id=id, created_by=request.user)
    except Notification.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    notification.delete()
    return Response({"message": "Deleted"})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_results_summary(request):
    if not _is_hod_user(request.user):
        return Response({"error": "Permission denied"}, status=403)

    department = request.user.department
    students = User.objects.filter(role='student', department=department)
    summaries = []

    for student in students:
        scores = Submission.objects.filter(student=student, marks__isnull=False).values_list('marks', flat=True)
        if scores:
            summaries.append(sum(scores) / len(scores))

    if not summaries:
        return Response({
            "pass_ratio": 0,
            "fail_ratio": 0,
            "top_performers_ratio": 0,
            "low_performers_ratio": 0,
            "student_count": students.count(),
        })

    threshold = 40
    sorted_scores = sorted(summaries, reverse=True)
    pass_count = len([s for s in sorted_scores if s >= threshold])
    fail_count = len([s for s in sorted_scores if s < threshold])
    student_count = len(sorted_scores)
    top_count = max(1, round(student_count * 0.1))
    low_count = max(1, round(student_count * 0.1))

    return Response({
        "pass_ratio": round((pass_count / student_count) * 100, 2),
        "fail_ratio": round((fail_count / student_count) * 100, 2),
        "top_performers_ratio": round((top_count / student_count) * 100, 2),
        "low_performers_ratio": round((low_count / student_count) * 100, 2),
        "student_count": student_count,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_subject_performance(request):
    if not _is_hod_user(request.user):
        return Response({"error": "Permission denied"}, status=403)

    department = request.user.department
    subject_data = Submission.objects.filter(
        student__role='student',
        student__department=department,
        marks__isnull=False
    ).values(
        subject=models.F('assignment__subject')
    ).annotate(
        average=models.Avg('marks'),
        count=models.Count('id')
    ).order_by('-average')

    weak_subjects = [s['subject'] for s in subject_data if s['average'] is not None and s['average'] < 50]

    return Response({
        "subjects": [
            {
                "subject": s['subject'],
                "average": round(s['average'] or 0, 2),
                "count": s['count'],
            } for s in subject_data
        ],
        "weak_subjects": weak_subjects,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_staff_performance(request):
    if not _is_hod_user(request.user):
        return Response({"error": "Permission denied"}, status=403)

    department = request.user.department
    staff_members = User.objects.filter(role='staff', department=department)
    result = []

    for member in staff_members:
        subjects = list(Timetable.objects.filter(faculty_user=member).values_list('subject', flat=True).distinct())
        scores = Submission.objects.filter(
            assignment__subject__in=subjects,
            marks__isnull=False
        ).values_list('marks', flat=True)
        feedback_count = FeedbackResponse.objects.filter(form__faculty=member).count()

        result.append({
            "id": member.id,
            "username": member.username,
            "name": f"{member.first_name} {member.last_name}".strip(),
            "designation": member.designation,
            "subjects_handled": subjects,
            "average_marks": round(sum(scores) / len(scores), 2) if scores else None,
            "feedback_count": feedback_count,
        })

    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_feedback_summary(request):
    if not _is_hod_user(request.user):
        return Response({"error": "Permission denied"}, status=403)

    department = request.user.department
    staff_members = User.objects.filter(role='staff', department=department)
    summary = []

    for member in staff_members:
        feedback_forms = FeedbackForm.objects.filter(faculty=member)
        response_count = FeedbackResponse.objects.filter(form__faculty=member).count()
        summary.append({
            "id": member.id,
            "username": member.username,
            "name": f"{member.first_name} {member.last_name}".strip(),
            "designation": member.designation,
            "feedback_form_count": feedback_forms.count(),
            "feedback_response_count": response_count,
        })

    return Response(summary)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_timetables(request):
    if not _is_hod_user(request.user):
        return Response({"error": "Permission denied"}, status=403)

    department = request.user.department
    entries = Timetable.objects.filter(department=department).exclude(approval_status='draft')
    data = []
    for item in entries:
        data.append({
            "id": item.id,
            "department": item.department,
            "year": item.year,
            "section": item.section,
            "semester": item.semester,
            "subject_code": item.subject_code,
            "subject": item.subject,
            "faculty": item.faculty,
            "faculty_id": item.faculty_user.id if item.faculty_user else None,
            "created_by": item.created_by.username if item.created_by else None,
            "approved_by": item.approved_by.username if item.approved_by else None,
            "approved_at": item.approved_at,
            "is_approved": item.is_approved,
            "approval_status": item.approval_status,
            "hod_comment": item.hod_comment,
            "day": item.day,
            "time": item.time,
            "period": item.period,
            "credits": item.credits,
        })

    clashes = []
    seen = {}
    for item in entries:
        key = (item.department, item.year, item.section, item.day, item.time)
        if key in seen:
            clashes.append(item.id)
            clashes.append(seen[key])
        else:
            seen[key] = item.id

    return Response({"timetables": data, "clash_ids": list(set(clashes))})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def hod_approve_timetable(request, id):
    if not _is_hod_user(request.user):
        return Response({"error": "Permission denied"}, status=403)

    try:
        item = Timetable.objects.get(id=id)
    except Timetable.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    item.is_approved = True
    item.approval_status = 'approved'
    item.approved_by = request.user
    item.approved_at = now()
    item.save()

    if item.faculty_user:
        title = "Timetable Approved"
        message = _format_hod_timetable_message(item, 'approved')
        _create_notification_for_user(item.faculty_user, title, message, item.department, item.year, item.section, request.user)

    return Response({"message": "Timetable approved"})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_timetable(request, id):
    if not is_staff_user(request.user):
        return Response({"error": "Permission denied"}, status=403)

    try:
        item = Timetable.objects.get(id=id)
    except Timetable.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    permission_denied = _staff_timetable_edit_permission(request, item)
    if permission_denied:
        return permission_denied

    if item.approval_status not in ['draft', 'pending', 'rejected', 'rework_assigned']:
        return Response({"error": "Only draft, pending, rejected or rework-assigned timetables can be submitted"}, status=400)

    item.approval_status = 'submitted'
    item.is_approved = False
    item.approved_by = None
    item.approved_at = None
    item.save()
    return Response({"message": "Timetable submitted for HOD review"})


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_timetable(request, id):
    if not is_staff_user(request.user):
        return Response({"error": "Permission denied"}, status=403)

    try:
        item = Timetable.objects.get(id=id)
    except Timetable.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    permission_denied = _staff_timetable_edit_permission(request, item)
    if permission_denied:
        return permission_denied

    department = request.data.get("department", item.department)
    year = request.data.get("year", item.year)
    section = request.data.get("section", item.section)

    if _is_faculty_fa_user(request.user):
        permission_denied = _faculty_fa_class_permission(request, department, year, section, allow_all=False)
        if permission_denied:
            return permission_denied

    item.department = department
    item.year = year
    item.section = section
    item.subject_code = request.data.get("subject_code", item.subject_code)
    item.subject = request.data.get("subject", request.data.get("subject_name", item.subject))
    item.day = request.data.get("day", item.day)
    item.time = request.data.get("time", item.time)
    item.period = request.data.get("period", item.period)
    item.semester = request.data.get("semester", item.semester)
    item.credits = request.data.get("credits", item.credits)

    faculty_id = request.data.get("faculty_id")
    if faculty_id:
        try:
            faculty = User.objects.get(id=faculty_id, role='staff')
            item.faculty_user = faculty
            item.faculty = faculty.get_full_name() or faculty.username
        except User.DoesNotExist:
            return Response({"error": "Invalid faculty"}, status=400)
    elif request.data.get("faculty"):
        item.faculty = request.data.get("faculty")

    submit_request = str(request.data.get("submit", "false")).lower() in ["true", "1", "yes"]
    approval_status = request.data.get("approval_status")
    if approval_status is not None:
        approval_status = str(approval_status).lower()
        if approval_status not in ['draft', 'submitted', 'pending', 'rejected', 'rework_assigned', 'under_review']:
            return Response({"error": "Invalid approval status"}, status=400)
        item.approval_status = approval_status
    elif submit_request:
        item.approval_status = 'submitted'

    if item.approval_status == 'submitted':
        item.is_approved = False
        item.approved_by = None
        item.approved_at = None

    item.save()
    return Response({"message": "Timetable updated"})


@api_view(['POST', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def hod_update_timetable(request, id):
    if not _is_hod_user(request.user):
        return Response({"error": "Permission denied"}, status=403)

    try:
        item = Timetable.objects.get(id=id)
    except Timetable.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    old_faculty_user = item.faculty_user

    department = request.data.get("department", item.department)
    year = request.data.get("year", item.year)
    section = request.data.get("section", item.section)

    item.department = department
    item.year = year
    item.section = section
    item.subject_code = request.data.get("subject_code", item.subject_code)
    item.subject = request.data.get("subject", request.data.get("subject_name", item.subject))
    item.day = request.data.get("day", item.day)
    item.time = request.data.get("time", item.time)
    item.period = request.data.get("period", item.period)
    item.semester = request.data.get("semester", item.semester)

    faculty_id = request.data.get("faculty_id")
    if faculty_id:
        try:
            faculty = User.objects.get(id=faculty_id, role='staff')
            item.faculty_user = faculty
            item.faculty = faculty.get_full_name() or faculty.username
        except User.DoesNotExist:
            return Response({"error": "Invalid faculty"}, status=400)
    elif request.data.get("faculty"):
        item.faculty = request.data.get("faculty")

    approval_status = request.data.get("approval_status")
    if approval_status is not None:
        approval_status = str(approval_status).lower()
        if approval_status not in ['pending', 'under_review', 'approved', 'rejected', 'rework_assigned']:
            return Response({"error": "Invalid approval status"}, status=400)
        item.approval_status = approval_status
        if approval_status == 'approved':
            item.is_approved = True
            item.approved_by = request.user
            item.approved_at = now()
        else:
            item.is_approved = False
            item.approved_by = None
            item.approved_at = None
    elif item.approval_status in ['submitted', 'pending', 'rework_assigned']:
        item.approval_status = 'under_review'
        item.is_approved = False
        item.approved_by = None
        item.approved_at = None

    item.hod_comment = request.data.get("hod_comment", item.hod_comment)
    item.save()

    notification_recipients = []
    if old_faculty_user and old_faculty_user != item.faculty_user:
        notification_recipients.append(old_faculty_user)
    if item.faculty_user:
        notification_recipients.append(item.faculty_user)

    notification_recipients = list({user.id: user for user in notification_recipients}.values())
    comment_text = item.hod_comment or None

    if item.approval_status == 'approved':
        title = "Timetable Approved"
        message = _format_hod_timetable_message(item, 'approved', comment_text)
    elif item.approval_status == 'rejected':
        title = "Timetable Rejected"
        message = _format_hod_timetable_message(item, 'rejected', comment_text)
    elif item.approval_status == 'rework_assigned':
        title = "Timetable Rework Requested"
        message = _format_hod_timetable_message(item, 'sent back for rework', comment_text)
    else:
        title = "Timetable Updated"
        message = _format_hod_timetable_message(item, 'updated', comment_text)

    for recipient in notification_recipients:
        _create_notification_for_user(recipient, title, message, item.department, item.year, item.section, request.user)

    return Response({"message": "Timetable updated"})


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


def _attendance_percentage_for_student(student):
    total = Attendance.objects.filter(student=student).count()
    if total == 0:
        return None
    present = Attendance.objects.filter(student=student, status='present').count()
    return round((present / total) * 100, 2)


def _attendance_percentage_for_staff(staff_member):
    total = StaffAttendance.objects.filter(staff=staff_member).count()
    if total == 0:
        return None
    present = StaffAttendance.objects.filter(staff=staff_member, status='present').count()
    return round((present / total) * 100, 2)


def _is_hod_user(user):
    role = str(getattr(user, 'role', '') or '').strip().lower()
    designation = str(getattr(user, 'designation', '') or '').strip().lower()
    return role == 'hod' or designation == 'hod' or (role == 'staff' and designation == 'hod')


def _is_faculty_fa_user(user):
    return bool(getattr(user, 'is_faculty_fa', False))


def _get_faculty_fa_assignment(user):
    if not _is_faculty_fa_user(user):
        return None
    department = getattr(user, 'faculty_fa_department', None)
    year = getattr(user, 'faculty_fa_year', None)
    section = getattr(user, 'faculty_fa_section', None)
    if department and year and section:
        return (department, year, section)
    return None


def _matches_faculty_fa_class(assignment, department, year, section, allow_all=False):
    if not assignment:
        return True
    assigned_department, assigned_year, assigned_section = assignment
    if department != assigned_department:
        return False
    if allow_all:
        if year not in [assigned_year, 'all', None, '']:
            return False
        if section not in [assigned_section, 'all', None, '']:
            return False
    else:
        if year != assigned_year:
            return False
        if section != assigned_section:
            return False
    return True


def _faculty_fa_class_permission(request, department, year, section, allow_all=False):
    assignment = _get_faculty_fa_assignment(request.user)
    if not assignment:
        return None
    if not _matches_faculty_fa_class(assignment, department, year, section, allow_all=allow_all):
        return Response({"error": "Permission denied: FA can only access assigned class"}, status=403)
    return None


def _staff_timetable_edit_permission(request, timetable):
    if timetable.approval_status == 'approved':
        return Response({"error": "Cannot edit approved timetable entry"}, status=403)

    if timetable.created_by == request.user:
        return None

    if _is_faculty_fa_user(request.user):
        assignment = _get_faculty_fa_assignment(request.user)
        if assignment and timetable.department == assignment[0] and timetable.year == assignment[1] and timetable.section == assignment[2]:
            return None

    return Response({"error": "Permission denied"}, status=403)


def _format_hod_timetable_message(item, action, comment=None):
    subject_desc = item.subject_code or item.subject or "the subject"
    class_desc = f"{item.department} {item.year}{item.section}"
    comment_text = f" Comment: {comment}" if comment else ""
    return (
        f"Timetable entry for {class_desc} ({item.semester} sem, {item.day} {item.time}) - "
        f"{subject_desc} has been {action}.{comment_text}"
    )


def _create_notification_for_user(user, title, message, department, year, section, created_by):
    if not user:
        return None
    Notification.objects.create(
        title=title,
        message=message,
        department=department or "all",
        year=year or "all",
        section=section or "all",
        created_by=created_by,
        student=user,
    )


def _hod_permissions(request):
    if not _is_hod_user(request.user):
        return Response({"error": "Permission denied"}, status=403)
    return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_overview(request):
    permission_denied = _hod_permissions(request)
    if permission_denied:
        return permission_denied

    department = request.user.department
    students = User.objects.filter(role='student', department=department)
    staff = User.objects.filter(role='staff', department=department)

    low_students_count = 0
    for student in students:
        percentage = _attendance_percentage_for_student(student)
        if percentage is not None and percentage < 75:
            low_students_count += 1

    low_staff_count = 0
    for member in staff:
        percentage = _attendance_percentage_for_staff(member)
        if percentage is not None and percentage < 75:
            low_staff_count += 1

    return Response({
        "student_count": students.count(),
        "staff_count": staff.count(),
        "low_attendance_students_count": low_students_count,
        "low_attendance_staff_count": low_staff_count,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_students(request):
    permission_denied = _hod_permissions(request)
    if permission_denied:
        return permission_denied

    department = request.user.department
    students = User.objects.filter(role='student', department=department)

    data = []
    for student in students:
        data.append({
            "id": student.id,
            "username": student.username,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "salutation": student.salutation,
            "email": student.email,
            "department": student.department,
            "year": student.year,
            "section": student.section,
            "attendance_percentage": _attendance_percentage_for_student(student),
        })

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_staff(request):
    permission_denied = _hod_permissions(request)
    if permission_denied:
        return permission_denied

    department = request.user.department
    staff = User.objects.filter(role='staff', department=department)

    data = []
    for member in staff:
        data.append({
            "id": member.id,
            "username": member.username,
            "first_name": member.first_name,
            "last_name": member.last_name,
            "salutation": member.salutation,
            "email": member.email,
            "designation": member.designation,
            "is_faculty_fa": member.is_faculty_fa,
            "is_subject_holder": member.is_subject_holder,
            "department": member.department,
            "section": member.section,
        })

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_low_students(request):
    permission_denied = _hod_permissions(request)
    if permission_denied:
        return permission_denied

    department = request.user.department
    students = User.objects.filter(role='student', department=department)

    low_students = []
    for student in students:
        percentage = _attendance_percentage_for_student(student)
        if percentage is not None and percentage < 75:
            low_students.append({
                "id": student.id,
                "username": student.username,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "salutation": student.salutation,
                "email": student.email,
                "department": student.department,
                "year": student.year,
                "section": student.section,
                "attendance_percentage": percentage,
            })

    return Response(low_students)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_low_staff(request):
    permission_denied = _hod_permissions(request)
    if permission_denied:
        return permission_denied

    department = request.user.department
    staff_members = User.objects.filter(role='staff', department=department)

    low_staff = []
    for member in staff_members:
        percentage = _attendance_percentage_for_staff(member)
        if percentage is not None and percentage < 75:
            low_staff.append({
                "id": member.id,
                "username": member.username,
                "first_name": member.first_name,
                "last_name": member.last_name,
                "salutation": member.salutation,
                "email": member.email,
                "designation": member.designation,
                "is_faculty_fa": member.is_faculty_fa,
                "is_subject_holder": member.is_subject_holder,
                "department": member.department,
                "section": member.section,
                "attendance_percentage": percentage,
            })

    return Response(low_staff)


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
        if _is_faculty_fa_user(request.user):
            assignment = _get_faculty_fa_assignment(request.user)
            if assignment:
                department, year, section = assignment
                forms = FeedbackForm.objects.filter(
                    department=department,
                    year__in=[year, 'all'],
                    section__in=[section, 'all']
                )
            else:
                forms = FeedbackForm.objects.none()
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

    if _is_faculty_fa_user(request.user):
        permission_denied = _faculty_fa_class_permission(request, department, year, section, allow_all=False)
        if permission_denied:
            return permission_denied

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
    if _is_hod_user(request.user) and getattr(request.user, 'department', None):
        faculties = faculties.filter(department=request.user.department)
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

    if _is_faculty_fa_user(request.user):
        assignment = _get_faculty_fa_assignment(request.user)
        if assignment:
            department, year, section = assignment
            forms = FeedbackForm.objects.filter(
                department=department,
                year__in=[year, 'all'],
                section__in=[section, 'all']
            )
        else:
            forms = FeedbackForm.objects.none()
    else:
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