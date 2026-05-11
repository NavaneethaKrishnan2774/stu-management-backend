from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import now, make_aware, get_current_timezone
from django.db import models
from django.utils.dateparse import parse_datetime
from django.db.models import Count
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

from .models import Assignment, Attendance, StaffAttendance, Submission, Timetable, Notification, FeedbackForm, FeedbackResponse, Complaint, PlacementDrive, PlacementOffer, PlacementMessage, PlacementStudentRound

User = get_user_model()


def is_staff_user(user):
    return getattr(user, 'role', None) in ['staff', 'admin'] or getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)


def is_placement_officer(user):
    return getattr(user, 'role', None) == 'staff' and (
        getattr(user, 'is_placement_officer', False) or getattr(user, 'designation', None) == 'placement_officer'
    )


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


# ✅ PROFILE API
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def get_profile(request):
    user = request.user
    
    if request.method == 'PUT':
        # Handle profile update
        data = request.data
        
        # Update basic user fields
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'email' in data:
            user.email = data['email']
        
        # Update student-specific fields
        if 'register_number' in data:
            user.register_number = data['register_number']
        if 'department' in data:
            user.department = data['department']
        if 'year' in data:
            user.year = data['year']
        if 'section' in data:
            user.section = data['section']
        if 'semester' in data:
            user.semester = data['semester']
        if 'mobile' in data:
            user.mobile = data['mobile']
        if 'date_of_birth' in data:
            user.date_of_birth = data['date_of_birth']
        if 'age' in data:
            user.age = data['age']
        if 'parent_mobile' in data:
            user.parent_mobile = data['parent_mobile']
        if 'year_of_joining' in data:
            user.year_of_joining = data['year_of_joining']
        if 'blood_group' in data:
            user.blood_group = data['blood_group']
        if 'advisor_faculty_id' in data:
            user.advisor_faculty_id = data['advisor_faculty_id']
        if 'emergency_contact' in data:
            user.emergency_contact = data['emergency_contact']
        if 'residential_address' in data:
            user.residential_address = data['residential_address']
        
        # Handle profile photo upload
        if 'profile_photo' in request.FILES:
            user.profile_photo = request.FILES['profile_photo']
        
        user.save()
        
        # Return updated profile record so frontend can refresh immediately
        profile_data = {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "register_number": getattr(user, 'register_number', None),
            "department": getattr(user, 'department', None),
            "year": getattr(user, 'year', None),
            "section": getattr(user, 'section', None),
            "semester": getattr(user, 'semester', None),
            "phone": getattr(user, 'mobile', None),
            "date_of_birth": getattr(user, 'date_of_birth', None),
            "age": getattr(user, 'age', None),
            "parent_mobile": getattr(user, 'parent_mobile', None),
            "year_of_joining": getattr(user, 'year_of_joining', None),
            "blood_group": getattr(user, 'blood_group', None),
            "advisor_faculty_id": getattr(user, 'advisor_faculty_id', None),
            "emergency_contact": getattr(user, 'emergency_contact', None),
            "residential_address": getattr(user, 'residential_address', None),
            "profile_photo": user.profile_photo.url if user.profile_photo else None,
            "current_semester": getattr(user, 'current_semester', None),
            "cgpa": getattr(user, 'cgpa', None),
            "placed": getattr(user, 'placed', False),
            "is_active": user.is_active,
            "attendance_percentage": round(calculate_attendance_percentage(user), 2),
        }
        return Response(profile_data)
    
    # GET request - return profile data
    profile_data = {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "register_number": getattr(user, 'register_number', None),
        "department": getattr(user, 'department', None),
        "year": getattr(user, 'year', None),
        "section": getattr(user, 'section', None),
        "semester": getattr(user, 'semester', None),
        "phone": getattr(user, 'mobile', None),
        "date_of_birth": getattr(user, 'date_of_birth', None),
        "age": getattr(user, 'age', None),
        "parent_mobile": getattr(user, 'parent_mobile', None),
        "year_of_joining": getattr(user, 'year_of_joining', None),
        "blood_group": getattr(user, 'blood_group', None),
        "advisor_faculty_id": getattr(user, 'advisor_faculty_id', None),
        "emergency_contact": getattr(user, 'emergency_contact', None),
        "residential_address": getattr(user, 'residential_address', None),
        "profile_photo": user.profile_photo.url if user.profile_photo else None,
        "current_semester": getattr(user, 'current_semester', None),
        "cgpa": getattr(user, 'cgpa', None),
        "placed": getattr(user, 'placed', False),
        "is_active": user.is_active,
        "attendance_percentage": round(calculate_attendance_percentage(user), 2),
    }
    return Response(profile_data)


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

    # Get placement drives for this department
    placement_drives = PlacementDrive.objects.filter(department=department)
    active_drives_count = placement_drives.filter(drive_date__gte=now().date()).count()
    
    # Count shortlisted students (students with placement offers)
    shortlisted_students_count = PlacementOffer.objects.filter(
        drive__department=department,
        status__in=['applied', 'shortlisted', 'placed']
    ).values('student').distinct().count()

    return Response({
        "student_count": students.count(),
        "staff_count": staff.count(),
        "low_attendance_students_count": low_students_count,
        "low_attendance_staff_count": low_staff_count,
        "placement_drives_count": active_drives_count,
        "shortlisted_students_count": shortlisted_students_count,
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


# PLACEMENT VIEWS

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def placement_departments(request):
    if not is_placement_officer(request.user):
        return Response({"error": "Permission denied"}, status=403)
    
    departments = [
        {'code': 'CSE', 'name': 'Computer Science Engineering'},
        {'code': 'ECE', 'name': 'Electronics and Communication Engineering'},
        {'code': 'EEE', 'name': 'Electrical and Electronics Engineering'},
        {'code': 'MECH', 'name': 'Mechanical Engineering'},
        {'code': 'CIVIL', 'name': 'Civil Engineering'},
    ]
    return Response(departments)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def placement_students(request, department):
    if not is_placement_officer(request.user):
        return Response({"error": "Permission denied"}, status=403)
    
    students = User.objects.filter(role='student', department=department).order_by('first_name', 'last_name')
    
    # Get attendance percentages, placement status and completed assessment markers
    student_data = []
    for student in students:
        attendance_percentage = _attendance_percentage_for_student(student)
        placed_offers = PlacementOffer.objects.filter(student=student, status='placed').count()
        assessment_completed = Submission.objects.filter(student=student, marks__isnull=False).exists()
        
        student_data.append({
            'id': student.id,
            'register_number': student.username,
            'name': f"{student.first_name} {student.last_name}".strip(),
            'class': f"{student.year} {student.section}",
            'year': student.year,
            'section': student.section,
            'cgpa': float(student.cgpa) if student.cgpa else None,
            'current_arrears': student.current_arrears,
            'arrears_history': student.arrears_history,
            'resume': student.resume.url if student.resume else None,
            'job_offers': student.job_offers_count,
            'email': student.email,
            'mobile': student.mobile,
            'attendance_percentage': attendance_percentage,
            'placed': placed_offers > 0,
            'assessment_completed': assessment_completed,
        })
    
    # Keep only students who have completed an assessment submission
    completed_students = [s for s in student_data if s['assessment_completed']]
    
    placed_students = [s for s in completed_students if s['placed']]
    unplaced_students = [s for s in completed_students if not s['placed']]
    
    if placed_students:
        placed_students.sort(key=lambda x: x['name'])
        unplaced_students.sort(key=lambda x: (-(x['attendance_percentage'] or 0), x['name']))
    else:
        unplaced_students.sort(key=lambda x: x['name'])
    
    result = placed_students + unplaced_students
    return Response({
        'total_count': len(result),
        'placed_count': len(placed_students),
        'students': result,
    })


# ✅ GET FILTERED STUDENTS FOR PLACEMENT DRIVE
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_placement_students_filtered(request):
    """Get students filtered by department, year, and placement status"""
    if not is_placement_officer(request.user):
        return Response({"error": "Permission denied"}, status=403)
    
    department = request.GET.get('department')
    year = request.GET.get('year')
    filter_type = request.GET.get('filter', 'all')  # all, placed, offers_2, offers_3, offers_4, offers_5
    round_filter = request.GET.get('round')  # first, second, third, final
    
    # Base queryset
    students = User.objects.filter(role='student', department=department)
    
    if year:
        students = students.filter(year=year)
    
    students = students.order_by('first_name', 'last_name')
    
    student_data = []
    for student in students:
        # Get placement offers count and status
        offers = PlacementOffer.objects.filter(student=student)
        placed_count = offers.filter(placed=True).count()
        total_offers = offers.count()
        
        # Get round clearances
        rounds_cleared = PlacementStudentRound.objects.filter(
            student=student,
            cleared=True
        ).values_list('round_number', flat=True).distinct()
        
        placed_drives = PlacementOffer.objects.filter(student=student, placed=True).select_related('drive')
        company_names = [offer.drive.company_name for offer in placed_drives]
        student_info = {
            'id': student.id,
            'register_number': student.username,
            'name': f"{student.first_name} {student.last_name}".strip(),
            'department': student.department,
            'class': f"{student.year} {student.section}",
            'year': student.year,
            'section': student.section,
            'cgpa': float(student.cgpa) if student.cgpa else 0.0,
            'current_arrears': student.current_arrears,
            'arrears_history': student.arrears_history or 'None',
            'resume': student.resume.url if student.resume else None,
            'job_offers': student.job_offers_count,
            'email': student.email,
            'mobile': student.mobile or 'N/A',
            'placed': placed_count > 0,
            'placed_company': ", ".join(company_names) if company_names else None,
            'total_offers': total_offers,
            'rounds_cleared': list(rounds_cleared),
        }
        student_data.append(student_info)
    
    # Apply filters
    filtered_data = student_data
    
    if filter_type == 'placed':
        filtered_data = [s for s in filtered_data if s['placed']]
    elif filter_type.startswith('offers_'):
        try:
            offer_count = int(filter_type.split('_')[1])
            filtered_data = [s for s in filtered_data if s['total_offers'] >= offer_count]
        except:
            pass
    
    if round_filter and round_filter != 'all':
        filtered_data = [s for s in filtered_data if round_filter in s['rounds_cleared']]
    
    # Sort: placed first, then by name
    placed = [s for s in filtered_data if s['placed']]
    not_placed = [s for s in filtered_data if not s['placed']]
    placed.sort(key=lambda x: x['name'])
    not_placed.sort(key=lambda x: x['name'])
    
    final_list = placed + not_placed
    
    return Response({
        'total_students': len(student_data),
        'filtered_students': len(final_list),
        'placed_count': len(placed),
        'students': final_list,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_placement_drive(request):
    if not is_placement_officer(request.user):
        return Response({"error": "Permission denied"}, status=403)
    
    import json

    def _parse_json_list(value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else [parsed]
            except Exception:
                return [item.strip() for item in value.split(',') if item.strip()]
        return [value]

    def _get_list_field(name):
        if hasattr(request.data, 'getlist'):
            values = request.data.getlist(name)
            if values:
                return values
        return _parse_json_list(request.data.get(name))

    company_name = request.data.get('company_name')
    company_history = request.data.get('company_history')
    company_location = request.data.get('company_location')
    expected_skills = _get_list_field('expected_skills')
    job_role = request.data.get('job_role')
    package = request.data.get('package')
    vacancies = request.data.get('vacancies')
    location = request.data.get('location')
    drive_date = request.data.get('drive_date')
    last_date_to_apply = request.data.get('last_date_to_apply')
    eligible_batches = _get_list_field('eligible_batches')
    eligible_departments = _get_list_field('eligible_departments')
    contact_person_name = request.data.get('contact_person_name')
    contact_person_designation = request.data.get('contact_person_designation')
    contact_person_email = request.data.get('contact_person_email')
    contact_person_phone = request.data.get('contact_person_phone')
    bond_period = request.data.get('bond_period')
    bond_amount = request.data.get('bond_amount')
    min_cgpa = request.data.get('min_cgpa')
    min_10th_percentage = request.data.get('min_10th_percentage')
    min_12th_percentage = request.data.get('min_12th_percentage')
    arrears_allowed = request.data.get('arrears_allowed')
    shortlist_limit = request.data.get('shortlist_limit')
    perks = _get_list_field('perks')
    additional_questions = _get_list_field('additional_questions')
    notification_preference = request.data.get('notification_preference')
    rounds = _get_list_field('rounds')
    jd_file = request.FILES.get('jd_file')
    company_document = request.FILES.get('company_document')
    
    if not all([company_name, job_role, drive_date]):
        return Response({"error": "Missing required fields: company_name, job_role, drive_date"}, status=400)

    if not eligible_departments:
        return Response({"error": "Please select at least one eligible department."}, status=400)
    
    drive_department = eligible_departments[0]
    
    try:
        criteria = json.dumps({
            'job_role': job_role,
            'package': package,
            'vacancies': vacancies,
            'location': location,
            'last_date_to_apply': last_date_to_apply,
            'company_history': company_history,
            'company_location': company_location,
            'expected_skills': expected_skills,
            'min_cgpa': float(min_cgpa) if min_cgpa not in (None, "", "null") else None,
            'min_10th_percentage': float(min_10th_percentage) if min_10th_percentage not in (None, "", "null") else None,
            'min_12th_percentage': float(min_12th_percentage) if min_12th_percentage not in (None, "", "null") else None,
            'arrears_allowed': arrears_allowed,
            'shortlist_limit': int(shortlist_limit) if shortlist_limit not in (None, "", "") else None,
            'eligible_departments': eligible_departments,
            'eligible_batches': eligible_batches,
            'notification_preference': notification_preference,
            'contact_person': {
                'name': contact_person_name,
                'designation': contact_person_designation,
                'email': contact_person_email,
                'phone': contact_person_phone,
            },
            'bond': {
                'period': bond_period,
                'amount': bond_amount,
            },
            'perks': perks,
            'rounds': rounds,
        })
    except Exception:
        criteria = ""
    
    drive = PlacementDrive.objects.create(
        company_name=company_name,
        drive_date=drive_date,
        department=drive_department,
        criteria=criteria,
        document=jd_file,
        created_by=request.user,
    )
    
    eligible_students = _get_eligible_students(drive)
    eligible_students_list = []
    for student in eligible_students:
        eligible_students_list.append({
            'id': student.id,
            'username': student.username,
            'full_name': student.get_full_name() or student.username,
            'email': student.email,
            'department': student.department,
            'year': student.year,
            'cgpa': float(student.cgpa) if student.cgpa is not None else None,
            'current_arrears': student.current_arrears,
        })
    
    return Response({
        "message": f"Drive created successfully. {len(eligible_students_list)} students are eligible.",
        "drive_id": drive.id,
        "eligible_students": eligible_students_list
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_drive_to_students(request):
    if not is_placement_officer(request.user):
        return Response({"error": "Permission denied"}, status=403)
    
    drive_id = request.data.get('drive_id')
    student_ids = request.data.get('student_ids', [])
    
    if not drive_id:
        return Response({"error": "Drive ID required"}, status=400)
    
    if not student_ids:
        return Response({"error": "Student IDs required"}, status=400)
    
    try:
        drive = PlacementDrive.objects.get(id=drive_id, created_by=request.user)
    except PlacementDrive.DoesNotExist:
        return Response({"error": "Drive not found"}, status=404)
    
    # Get the specified students
    eligible_students = User.objects.filter(id__in=student_ids, role='student')
    
    if not eligible_students.exists():
        return Response({"error": "No valid students found"}, status=400)
    
    # Create placement offers for eligible students
    for student in eligible_students:
        PlacementOffer.objects.get_or_create(
            student=student,
            drive=drive,
            defaults={'status': 'applied'}
        )
    
    # Send drive details to eligible students
    message_text = f"New placement drive: {drive.company_name} on {drive.drive_date}. Please check your dashboard for details."
    placement_message = PlacementMessage.objects.create(
        sender=request.user,
        subject=f"Placement Drive: {drive.company_name}",
        message=message_text,
        drive=drive,
    )
    placement_message.recipients.set(eligible_students)
    
    # Create notifications for eligible students
    notification_title = f"New Placement Drive: {drive.company_name}"
    notification_message = f"A new placement drive for {drive.company_name} has been scheduled on {drive.drive_date}. Check the Development module for details and eligibility criteria."
    
    for student in eligible_students:
        Notification.objects.create(
            title=notification_title,
            message=notification_message,
            department=getattr(drive, 'department', student.department),  # Use drive department or student's department
            created_by=request.user,
            student=student,
        )
    
    # Create notification for HOD of the department
    try:
        # Get departments from the drive or from students
        departments = set()
        if hasattr(drive, 'eligible_departments') and drive.eligible_departments:
            departments.update(drive.eligible_departments)
        else:
            departments.update(eligible_students.values_list('department', flat=True))
        
        for dept in departments:
            hod_user = User.objects.filter(
                role__in=['hod', 'staff'],
                department=dept,
                designation__in=['hod', 'HOD']
            ).first()
            
            if hod_user:
                hod_notification_title = f"Placement Drive Sent: {drive.company_name}"
                hod_notification_message = f"The placement drive for {drive.company_name} has been sent to {eligible_students.count()} eligible students in {dept} department."
                
                Notification.objects.create(
                    title=hod_notification_title,
                    message=hod_notification_message,
                    department=dept,
                    created_by=request.user,
                    student=hod_user,
                )
    except Exception as e:
        print(f"Error creating HOD notification: {e}")
    
    return Response({"message": f"Drive sent to {eligible_students.count()} students"})


def _get_eligible_students(drive):
    """Filter students based on company criteria"""
    import json

    students = User.objects.filter(role='student')
    try:
        criteria = json.loads(drive.criteria) if drive.criteria else {}
    except Exception:
        criteria = {}

    eligible_departments = criteria.get('eligible_departments', [])
    if eligible_departments:
        students = students.filter(department__in=eligible_departments)
    elif getattr(drive, 'department', None):
        students = students.filter(department=drive.department)

    if 'min_cgpa' in criteria and criteria['min_cgpa'] is not None:
        try:
            students = students.filter(cgpa__gte=float(criteria['min_cgpa']))
        except Exception:
            pass

    arrears_allowed = criteria.get('arrears_allowed')
    if arrears_allowed == 'Not Allowed':
        students = students.filter(current_arrears=0)
    elif arrears_allowed == 'Allowed (up to 2)':
        students = students.filter(current_arrears__lte=2)

    return students


def _parse_criteria(criterion):
    """Parse criteria like '>=8.0' into ('>=', '8.0')"""
    import re
    match = re.match(r'([<>=!]+)(.+)', criterion.strip())
    if match:
        return match.group(1), match.group(2).strip()
    return '==', criterion.strip()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_placement_message(request):
    if not is_placement_officer(request.user):
        return Response({"error": "Permission denied"}, status=403)
    
    subject = request.data.get('subject')
    message = request.data.get('message')
    student_ids = request.data.get('student_ids', [])
    drive_id = request.data.get('drive_id')
    
    if not subject or not message:
        return Response({"error": "Subject and message required"}, status=400)
    
    if isinstance(student_ids, str):
        student_ids = [int(x.strip()) for x in student_ids.split(',') if x.strip()]
    
    students = User.objects.filter(id__in=student_ids, role='student')
    
    placement_message = PlacementMessage.objects.create(
        sender=request.user,
        subject=subject,
        message=message,
        drive_id=drive_id,
    )
    
    placement_message.recipients.set(students)
    
    return Response({"message": f"Message sent to {students.count()} students"})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def placement_drives(request):
    if not is_placement_officer(request.user):
        return Response({"error": "Permission denied"}, status=403)
    
    drives = PlacementDrive.objects.filter(created_by=request.user).order_by('-created_at')
    data = []
    for drive in drives:
        offers = PlacementOffer.objects.filter(drive=drive)
        placed_count = offers.filter(status='placed').count()
        applied_count = offers.filter(status='applied').count()
        
        data.append({
            'id': drive.id,
            'company_name': drive.company_name,
            'drive_date': drive.drive_date,
            'department': drive.department,
            'criteria': drive.criteria,
            'document': drive.document.url if drive.document else None,
            'applied_count': applied_count,
            'placed_count': placed_count,
        })
    
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_placement_drives(request):
    permission_denied = _hod_permissions(request)
    if permission_denied:
        return permission_denied

    department = request.user.department
    drives = PlacementDrive.objects.filter(department=department).order_by('-drive_date')

    data = []
    for drive in drives:
        # Get placement offers for this drive
        offers = PlacementOffer.objects.filter(drive=drive).select_related('student')
        
        shortlisted_students = []
        placed_count = 0
        
        for offer in offers:
            if offer.status in ['applied', 'shortlisted', 'placed']:
                shortlisted_students.append({
                    'id': offer.student.id,
                    'name': offer.student.get_full_name() or offer.student.username,
                    'register_number': offer.student.register_number,
                    'cgpa': float(offer.student.cgpa) if offer.student.cgpa else None,
                    'status': offer.status,
                })
                if offer.status == 'placed':
                    placed_count += 1

        data.append({
            'id': drive.id,
            'company_name': drive.company_name,
            'drive_date': drive.drive_date,
            'department': drive.department,
            'criteria': drive.criteria,
            'document': drive.document.url if drive.document else None,
            'shortlisted_count': len(shortlisted_students),
            'placed_count': placed_count,
            'shortlisted_students': shortlisted_students,
        })

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_placement_drives(request):
    if request.user.role != 'student':
        return Response({"error": "Permission denied"}, status=403)

    import json

    student_department = request.user.department
    student_cgpa = float(request.user.cgpa) if request.user.cgpa is not None else None
    student_arrears = getattr(request.user, 'current_arrears', None)

    drives = PlacementDrive.objects.order_by('-drive_date')

    data = []
    for drive in drives:
        try:
            criteria = json.loads(drive.criteria) if drive.criteria else {}
        except Exception:
            criteria = {}

        eligible_departments = criteria.get('eligible_departments', [])
        if eligible_departments:
            if student_department not in eligible_departments:
                continue
        elif drive.department and student_department != drive.department:
            continue

        min_cgpa = criteria.get('min_cgpa')
        if min_cgpa is not None:
            try:
                if student_cgpa is None or student_cgpa < float(min_cgpa):
                    continue
            except Exception:
                pass

        arrears_allowed = criteria.get('arrears_allowed')
        if arrears_allowed == 'Not Allowed' and student_arrears is not None and student_arrears > 0:
            continue
        if arrears_allowed == 'Allowed (up to 2)' and student_arrears is not None and student_arrears > 2:
            continue

        # Get all placement offers for this drive
        offers = PlacementOffer.objects.filter(drive=drive).select_related('student')
        
        # Find current student's offer
        my_offer = offers.filter(student=request.user).first()
        my_status = my_offer.status if my_offer else 'not_applied'
        
        # Get attendee information (applied, shortlisted, placed students)
        attendees = []
        total_applied = 0
        total_shortlisted = 0
        total_placed = 0
        
        for offer in offers:
            if offer.status in ['applied', 'shortlisted', 'placed']:
                attendees.append({
                    'id': offer.student.id,
                    'name': offer.student.get_full_name() or offer.student.username,
                    'register_number': getattr(offer.student, 'register_number', None) or offer.student.username,
                    'status': offer.status,
                })
                
                if offer.status == 'applied':
                    total_applied += 1
                elif offer.status == 'shortlisted':
                    total_shortlisted += 1
                elif offer.status == 'placed':
                    total_placed += 1

        data.append({
            'id': drive.id,
            'company_name': drive.company_name,
            'drive_date': drive.drive_date,
            'department': drive.department,
            'criteria': drive.criteria,
            'document': drive.document.url if drive.document else None,
            'my_status': my_status,
            'total_applied': total_applied,
            'total_shortlisted': total_shortlisted,
            'total_placed': total_placed,
            'attendees': attendees,
        })

    return Response(data)