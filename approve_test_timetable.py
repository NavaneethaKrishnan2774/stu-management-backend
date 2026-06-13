#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms_backend.settings')
django.setup()

from students.models import Timetable
from users.models import User
from django.utils.timezone import now

# Get a timetable for CSE Year 3 Section A
tt = Timetable.objects.filter(department='CSE', year='3', section='A').first()
if tt:
    hod = User.objects.filter(role='hod').first()
    print(f'Timetable ID: {tt.id}')
    print(f'Status: {tt.approval_status}')
    print(f'Dept: {tt.department}, Year: {tt.year}, Section: {tt.section}')
    print(f'Subject: {tt.subject}')
    print(f'HOD: {hod.username if hod else "None"}')
    
    # Approve it
    tt.approval_status = 'approved'
    tt.is_approved = True
    tt.approved_by = hod
    tt.approved_at = now()
    tt.save()
    print(f'\n✅ Updated! New status: {tt.approval_status}')
    print(f'Approved by: {tt.approved_by.username}')
    print(f'Approved at: {tt.approved_at}')
else:
    print('❌ No timetable found for CSE 3 A')
    # List what exists
    all_tt = Timetable.objects.all()
    print(f'\nAvailable timetables:')
    for t in all_tt:
        print(f'  - ID: {t.id}, Dept: {t.department}, Year: {t.year}, Section: {t.section}')
