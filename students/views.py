from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Assignment, Attendance, Submission, Timetable

@api_view(['GET'])
def get_attendance(request):
    data = Attendance.objects.all().values()
    return Response(data)


@api_view(['GET'])
def get_timetable(request):
    data = Timetable.objects.all().values()
    return Response(data)

@api_view(['GET'])
def get_assignments(request):
    data = Assignment.objects.all().values()
    return Response(data)

@api_view(['POST'])
def submit_assignment(request):
    assignment_id = request.data.get('assignment')
    student_id = request.data.get('student')
    file = request.FILES.get('file')

    Submission.objects.create(
        assignment_id=assignment_id,
        student_id=student_id,
        file=file
    )

    return Response({"message": "Submitted successfully"})