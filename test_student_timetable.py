#!/usr/bin/env python
import requests
import json

# Login as student
r = requests.post('http://127.0.0.1:8000/api/login/', json={'username': 'navaneethakrishnan', 'password': 'test123'})
data = r.json()
token = data.get('access')

print(f'Login Status: {r.status_code}')
print(f'Token: {token[:50] if token else "None"}...\n')

# Get timetables
r2 = requests.get('http://127.0.0.1:8000/api/students/timetables/', headers={'Authorization': f'Bearer {token}'})
print(f'Timetables Endpoint Status: {r2.status_code}')

timetables = r2.json()
print(f'Total timetables: {len(timetables) if isinstance(timetables, list) else 0}')

if isinstance(timetables, list):
    print('\nApproved Timetables:')
    for t in timetables:
        print(f'  - Subject: {t.get("subject")}')
        print(f'    Status: {t.get("approval_status")}')
        print(f'    Day: {t.get("day")}, Time: {t.get("time")}')
        print(f'    Faculty: {t.get("faculty")}')
        print()
else:
    print(f'Response: {json.dumps(timetables, indent=2)}')
