from django.shortcuts import render, redirect, get_object_or_404
from datetime import datetime, timedelta
from django.contrib.auth import authenticate, login
from .models import Staff, Attendance, User
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
import base64
from django.utils.timezone import localtime, now
from .forms import AttendanceForm, LoginForm
from django.db.models import Count
from django import template
from django.contrib.auth.decorators import login_required
from .decorators import master_required
from django.contrib.auth.models import Group
from django.utils import timezone
from datetime import datetime
import subprocess
from django.shortcuts import redirect, render
from django.contrib import messages
from myApp.models import Staff, Attendance
from myApp.forms import AttendanceForm  # Assuming you have a form for attendance

#_________________________BACK_UP_DATABASE_Drive_________________________________________

from django.shortcuts import render, redirect
from django.http import HttpResponse
from .forms import BackupForm
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload
import pickle
from datetime import datetime

import os
import shutil
from datetime import datetime
from django.http import HttpResponse
from django.shortcuts import redirect

def backup_success(request):
    return render(request, 'myApp/backup_success.html')

import os
import shutil
import pickle
from datetime import datetime
from django.http import HttpResponse
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from django.shortcuts import render
from .forms import BackupForm

# Google API Scopes
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Paths to credentials and token files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
credentials_path = os.path.join(BASE_DIR, 'credentials.json')
token_path = os.path.join(BASE_DIR, 'token.pickle')

def run_backup_script(request):
    """Run the database backup script."""
    db_path = r'C:\Sk_Enterprises\Sk_Enterprises\myproject\db.sqlite3'  
    backup_path = r'C:\Sk_Enterprises\Sk_Enterprises\myproject\backups' 
    try:
        # Ensure the backup directory exists
        if not os.path.exists(backup_path):
            os.makedirs(backup_path)

        # Generate backup file with timestamp
        timestamp = datetime.now().strftime('%Y%m%d')
        backup_filename = f'database_backup_{timestamp}.db'
        backup_full_path = os.path.join(backup_path, backup_filename)

        # Copy the database file
        shutil.copy(db_path, backup_full_path)

        # Confirm the file was created
        if os.path.exists(backup_full_path):
            message = f"Backup successful! Backup created at: {backup_full_path}"
        else:
            message = "Error: Backup file creation failed."

    except Exception as e:
        message = f"Error running backup script: {str(e)}"

    # Return response or redirect
    return HttpResponse(message)

def authenticate_google_drive():
    """Authenticate and return a Google Drive API service."""
    creds = None

    # Check for existing token.pickle for saved credentials
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, log in and save the token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save refreshed token
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
            except RefreshError:
                # If token refresh fails, prompt user to reauthenticate
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
        else:
            # Request new credentials if no valid or refreshable token exists
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

    # Build and return the Google Drive API service
    service = build('drive', 'v3', credentials=creds)
    return service

def upload_file_to_drive(service, file_name, file_path):
    """Upload the file to Google Drive."""
    file_metadata = {'name': file_name}
    media = MediaFileUpload(file_path, mimetype='application/octet-stream')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

def delete_old_backups(service, max_backups=3):
    """Delete old backups if there are more than the specified max."""
    results = service.files().list(q="name contains 'database_backup'", spaces='drive').execute()
    items = results.get('files', [])

    if len(items) > max_backups:
        if items and 'createdTime' in items[0]:
            items.sort(key=lambda x: x['createdTime'])
        else:
            items.sort(key=lambda x: x['name'])  # Fallback to sorting by name if 'createdTime' is not available

        for item in items[:-max_backups]:
            file_id = item['id']
            service.files().delete(fileId=file_id).execute()
            print(f"Deleted old backup: {item['name']} (ID: {file_id})")

def update_backup(request):
    """Update the database backup and upload it to Google Drive."""
    initial_data = {
        'db_path': r'C:\Sk_Enterprises\Sk_Enterprises\myproject\db.sqlite3',  # Set default database path
        'backup_path': r'C:\Sk_Enterprises\Sk_Enterprises\myproject\backups'  # Set default backup directory
    }
    
    if request.method == 'POST':
        form = BackupForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            db_path = form.cleaned_data['db_path']
            backup_path = form.cleaned_data['backup_path']
            max_backups = form.cleaned_data['max_backups']

            # Run the backup script first
            run_backup_script(request)

            # Generate a unique backup file name with a timestamp
            timestamp = datetime.now().strftime('%Y%m%d')
            backup_filename = f'database_backup_{timestamp}.db'                                 
            backup_full_path = os.path.join(backup_path, backup_filename)

            # Copy the database file to create a backup
            shutil.copy(db_path, backup_full_path)

            # Authenticate with Google Drive (this automatically handles token refresh)
            service = authenticate_google_drive()

            # Delete old backups if there are more than the allowed number (max_backups)
            delete_old_backups(service, max_backups)

            # Upload the new backup to Google Drive
            file_id = upload_file_to_drive(service, backup_filename, backup_full_path)

            return render(request, 'myApp/backup_sucess.html', {'file_id': file_id})
    else:
        form = BackupForm()

    return render(request, 'myApp/backup_form.html', {'form': form})

#_____________________________________________Backup_googlesheets_________________________________
def run_script(request):
    try:
        # Run the script using subprocess
        subprocess.run(['python', r'C:\Sk_Enterprises\Sk_Enterprises\myproject\myApp\google_sheet.py'], check=True)
        return render(request, 'myApp/backup_sucess.html')
    except subprocess.CalledProcessError:
        return render(request, 'myApp/backup_error.html')
#___________________________________________________________________________________


@login_required
@master_required  # Ensure only master users can access this view
def add_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        group_name = request.POST.get('group')

        # Create the new user
        user = User.objects.create_user(username=username, password=password)
        
        # Assign user to the appropriate group (master or user)
        group, created = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
        
        messages.success(request, f'{group_name.capitalize()} user added successfully.')
        return redirect('add_user')  # Redirect back to the add user page or wherever you prefer

    return render(request, 'myApp/home.html')  # Form template for adding users




@login_required
def master_view(request):
    return render(request, 'myApp/master.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home/')
        else:
            if not User.objects.filter(username=username).exists():
                messages.error(request, 'Username not found')
            else:
                messages.error(request, 'Invalid username or password')

    return render(request, 'myApp/login.html')

# _____________________________________________HOMEPAGE_________________________________________________
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from .models import Attendance

@login_required
def home(request):
    # Double-check user authentication (optional, for debugging purposes)
    if not request.user.is_authenticated:
        return redirect('login')  # Ensure redirect to login if not authenticated

    # Get today's date
    today = localtime(now()).date()

    # Dictionary to store attendance counts per employee
    attendance_count = {}
    attendance_records = Attendance.objects.filter(attendance_date=today)

    # Process attendance records to count attendance types per employee
    for record in attendance_records:
        staff_id = record.staff.id_no  # Assuming staff.id_no uniquely identifies each employee
        attendance_type = record.attendance_type

        # Initialize the employee's attendance counts if not already done
        if staff_id not in attendance_count:
            attendance_count[staff_id] = {
                'name': record.staff.name,  # Store employee name
                'Onsite': 0,
                'Offsite': 0,
                'WFH': 0,
                'Leave': 0,
                'Travel': 0,
                'Others': 0,
                'Paid_leave': 0,
            }
        # Increment the count based on attendance type
        if attendance_type in attendance_count[staff_id]:
            attendance_count[staff_id][attendance_type] += 1

    # Aggregate the total counts for the day
    total_count = {
        'Onsite': sum(employee['Onsite'] for employee in attendance_count.values()),
        'Offsite': sum(employee['Offsite'] for employee in attendance_count.values()),
        'WFH': sum(employee['WFH'] for employee in attendance_count.values()),
        'Leave': sum(employee['Leave'] for employee in attendance_count.values()),
        'Travel': sum(employee['Travel'] for employee in attendance_count.values()),
        'Others': sum(employee['Others'] for employee in attendance_count.values()),
        'Paid_leave': sum(employee['Paid_leave'] for employee in attendance_count.values()),
    }

    context = {
        'total_count': total_count,  # Pass the total count to the template
    }

    return render(request, 'myApp/home.html',context)   

def daily_attendance(request):
    today = localtime(now()).date()
    attendance_count = {}
    attendance_records = Attendance.objects.filter(attendance_date=today)

    # Process attendance records
    for record in attendance_records:
        staff_id = record.staff.id_no
        attendance_type = record.attendance_type
        
        # Initialize the employee's attendance counts if not already done
        if staff_id not in attendance_count:
            attendance_count[staff_id] = {
                'name': record.staff.name,
                'Onsite': 0,
                'Offsite': 0,
                'WFH': 0,
                'Leave': 0,
                'Travel': 0,
                'Others': 0,
                'Paid_leave': 0,
            }

        # Increment the count based on attendance type
        attendance_count[staff_id][attendance_type] += 1

    # Aggregate total counts
    total_count = {
        'Onsite': sum(employee['Onsite'] for employee in attendance_count.values()),
        'Offsite': sum(employee['Offsite'] for employee in attendance_count.values()),
        'WFH': sum(employee['WFH'] for employee in attendance_count.values()),
        'Leave': sum(employee['Leave'] for employee in attendance_count.values()),
        'Travel': sum(employee['Travel'] for employee in attendance_count.values()),
        'Others': sum(employee['Others'] for employee in attendance_count.values()),\
        'Paid_leave': sum(employee['Paid_leave'] for employee in attendance_count.values()),
    }

    context = {
        'attendance_count': attendance_count,
        'total_count': total_count,
        'attendance_records': attendance_records,
    }

    return render(request, 'myApp/home.html', context)

#------------------------------------graphs--------------------------------------------
def chart_view(request):
    return render(request, 'attendance_chart.html')

def chart_data(request):
    # Get the current year
    current_year = timezone.now().year

    # Fetch attendance data for the current year and return JSON
    attendance_data = Attendance.objects.filter(attendance_date__year=current_year).values('attendance_type').annotate(count=Count('attendance_type'))
    labels = []
    data = []
    for entry in attendance_data:
        labels.append(entry['attendance_type'])
        data.append(entry['count'])
    return JsonResponse({'labels': labels, 'data': data})


def chart_data_month(request):
        # Get the current month and year
        current_date = timezone.now()
        current_year = current_date.year
        current_month = current_date.month

        # Fetch attendance data for the current month and return JSON
        attendance_data = Attendance.objects.filter(attendance_date__year=current_year, attendance_date__month=current_month).values('attendance_type').annotate(count=Count('attendance_type'))
        labels = []
        data = []
        for entry in attendance_data:
            labels.append(entry['attendance_type'])
            data.append(entry['count'])
        return JsonResponse({'labels': labels, 'data': data})

def work_mode_chart_data(request):
    # Get today's date and the date 30 days ago
    today = localtime(now()).date()
    last_30_days = today - timedelta(days=30)

    # Query the attendance for the last 30 days, grouped by attendance_type
    attendance_data = Attendance.objects.filter(attendance_date__gte=last_30_days).values('attendance_type').annotate(
        count=Count('staff', distinct=True)
    )

    # Prepare data for Chart.js
    labels = []  # Work modes like 'Onsite', 'Offsite', etc.
    data = []    # Corresponding counts of employees

    for entry in attendance_data:
        labels.append(entry['attendance_type'])
        data.append(entry['count'])

    return JsonResponse({'labels': labels, 'data': data})

def individual_work_mode_data(request, work_mode):
    today = localtime(now()).date()
    start_of_month = today.replace(day=1)

    # Filter attendance for the current month for the specific work mode
    attendance_data = Attendance.objects.filter(
        attendance_type=work_mode, attendance_date__gte=start_of_month
    ).values('staff__name').annotate(count=Count('staff')).order_by('staff__name')

    labels = []
    data = []

    for entry in attendance_data:
        labels.append(entry['staff__name'])  # Staff names
        data.append(entry['count'])          # Count of how many times they were in the specific work mode

    return JsonResponse({'labels': labels, 'data': data})

def staff_workmode_data(request):
    today = localtime(now()).date()
    start_of_month = today.replace(day=1)
    staff_data = []

    # Fetch all staff members
    staff_members = Staff.objects.all()
    
    for staff in staff_members:
        work_modes = Attendance.objects.filter(staff=staff, attendance_date__gte=start_of_month)
        
        work_mode_counts = {
            'Onsite': work_modes.filter(attendance_type='Onsite').count(),
            'Offsite': work_modes.filter(attendance_type='Offsite').count(),
            'WFH': work_modes.filter(attendance_type='WFH').count(),
            'Leave': work_modes.filter(attendance_type='Leave').count(),
            'Travel': work_modes.filter(attendance_type='Travel').count(),
            'Others': work_modes.filter(attendance_type='Others').count(),
            'Paid_leave': work_modes.filter(attendance_type='Paid_leave').count(),
        }

        staff_data.append({
            'staff_name': staff.name,
            'work_modes': work_mode_counts
        })
        #print("Returning data:", staff_data)

    return JsonResponse(staff_data, safe=False)

from datetime import timedelta
from django.utils.timezone import localtime
from django.utils.timezone import now
from django.http import JsonResponse
from .models import Staff, Attendance

def staff_workmode_data_week(request):
    today = localtime(now()).date()
    start_of_week = today - timedelta(days=today.weekday())  # Get the start of the week (Monday)
    
    staff_data = []

    # Fetch all staff members
    staff_members = Staff.objects.all()
    
    for staff in staff_members:
        # Filter attendance data for the last 7 days
        work_modes = Attendance.objects.filter(staff=staff, attendance_date__gte=start_of_week)

        work_mode_counts = {
            'Onsite': work_modes.filter(attendance_type='Onsite').count(),
            'Offsite': work_modes.filter(attendance_type='Offsite').count(),
            'WFH': work_modes.filter(attendance_type='WFH').count(),
            'Leave': work_modes.filter(attendance_type='Leave').count(),
            'Travel': work_modes.filter(attendance_type='Travel').count(),
            'Others': work_modes.filter(attendance_type='Others').count(),
            'Paid_leave': work_modes.filter(attendance_type='Paid_leave').count(),
        }

        staff_data.append({
            'staff_name': staff.name,
            'work_modes': work_mode_counts
        })

    return JsonResponse(staff_data, safe=False)










# _____________________________________________MANAGE_STAFF___________________________________________
def manage_staff(request):
    staff_list = Staff.objects.all()
    return render(request, 'myApp/managestaff.html', {'staff_list': staff_list})

def add_staff(request):
    if request.method == 'POST':
        staff = Staff(
            name=request.POST['name'],
            designation=request.POST['designation'],
            qualification=request.POST.get('qualification', ''),
            joining_date=request.POST.get('joining_date', None),
            dob=request.POST['dob'],
            blood_group=request.POST.get('blood_group', ''),
            id_no=request.POST['id_no'],
            aadhar=request.POST['aadhar'],
            pan=request.POST.get('pan', ''),
            email=request.POST['email'],
            mobile=request.POST['mobile'],
            emergency_contact=request.POST.get('emergency_contact', ''),
            address=request.POST.get('address', ''),
            insurance_policy_no=request.POST.get('insurance_policy_no', ''),
            insurance_expiry=request.POST.get('insurance_expiry', None),
            basic_salary=request.POST['basic_salary'],
            hra=request.POST['hra'],
            conveyance=request.POST['conveyance'],
            spl_allowance=request.POST['spl_allowance'],
            photo=request.FILES.get('photo', None), 
            totalleaves=request.POST.get('totalleaves', '0.0'),
        )
        staff.save()
        messages.success(request, 'Staff member added successfully!')
        return redirect('myApp:staff_success')
    return render(request, 'myApp/add_staff.html')

def edit_staff(request, id_no):
    staff = get_object_or_404(Staff, id_no=id_no)
    if request.method == 'POST':
        staff.name = request.POST['name']
        staff.designation = request.POST['designation']
        staff.qualification = request.POST.get('qualification', '')
        staff.joining_date = request.POST.get('joining_date', None)
        staff.dob = request.POST['dob']
        staff.blood_group = request.POST.get('blood_group', '')
        staff.aadhar = request.POST['aadhar']
        staff.pan = request.POST.get('pan', '')
        staff.email = request.POST['email']
        staff.mobile = request.POST['mobile']
        staff.emergency_contact = request.POST.get('emergency_contact', '')
        staff.address = request.POST.get('address', '')
        staff.insurance_policy_no = request.POST.get('insurance_policy_no', '')
        staff.insurance_expiry = request.POST.get('insurance_expiry', None)
        staff.photo=request.POST.get('photo','')
        if request.user.is_superuser:
            staff.basic_salary = request.POST['basic_salary']
            staff.hra = request.POST['hra']
            staff.conveyance = request.POST['conveyance']
            staff.spl_allowance = request.POST['spl_allowance']
            staff.totalleaves = request.POST['totalleaves']
        else:
            messages.error(request, 'You do not have permission to edit this information.')
            return redirect('myApp:manage_staff')
        if request.FILES.get('photo'):
            staff.photo = request.FILES['photo']
        staff.save()
        messages.success(request, 'Staff member updated successfully!')
        return redirect('myApp:manage_staff')
    return render(request, 'myApp/edit_staff.html', {'staff': staff})

from datetime import datetime

def edit_staff_view(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)
    
    # Format the dates
    staff.joining_date = staff.joining_date.strftime('%Y-%m-%d') if staff.joining_date else ''
    staff.dob = staff.dob.strftime('%Y-%m-%d') if staff.dob else ''
    staff.insurance_expiry = staff.insurance_expiry.strftime('%Y-%m-%d') if staff.insurance_expiry else ''
    
    if request.method == 'POST':
        # Handle form submission
        pass
    
    return render(request, 'myApp/edit_staff.html', {'staff': staff})

register = template.Library()

@register.filter(name='b64encode')

def b64encode(value):

    return base64.b64encode(value).decode('utf-8')

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Staff, Attendance

def delete_staff(request):
    if request.method == 'POST':
        try:
            # Retrieve id_no from query parameters
            id_no = request.GET.get('id_no')
            print(f"Received id_no exactly as passed: '{id_no}'")  # Debug log
            staff_member = get_object_or_404(Staff, id_no=id_no)

            # Delete all related attendance records
            deleted_count = Attendance.objects.filter(staff=staff_member).delete()
            print(f"Deleted {deleted_count} related attendance records")

            # Delete the staff member
            staff_member.delete()
            print(f"Deleted staff member with id_no: {id_no}")

            messages.success(request, 'Staff member and related data deleted successfully!')
            return redirect('myApp:manage_staff')
        except Staff.DoesNotExist:
            messages.error(request, 'Staff member not found.')
            return redirect('myApp:manage_staff')
        except Exception as e:
            print(f"Error occurred: {e}")
            messages.error(request, f'Error: {str(e)}')
            return redirect('myApp:manage_staff')
    else:
        messages.error(request, 'Invalid request method.')
        return redirect('myApp:manage_staff')

def manage_staff_view(request):
    Staff_list = Staff.objects.all()
    Staff_list = Staff.objects.values('id_no', 'name', 'designation', 'mobile')
    return render(request,'myApp/manage_staff.html',{'Staff_list':Staff_list})

def staff_detail(request, staff_id):
    staff = Staff.objects.get(id=staff_id)  # Fetch the staff member by ID
    return render(request, 'myApp/staff_detail.html', {'staff': staff})

def staff_success(request):
    return render(request, 'myApp/staff_success.html')

def leave_limit(request):
    staff_list = Staff.objects.values('id_no', 'name', 'designation', 'mobile', 'totalleaves')
    current_year = timezone.now().year

    # Count the leave for every staff member
    leave_counts = Attendance.objects.filter(attendance_type='Leave', attendance_date__year=current_year).values('staff__id_no').annotate(total_leaves=Count('attendance_type'))

    # Calculate the number of Paid_leave days for each staff member
    paid_leave_counts = Attendance.objects.filter(attendance_type='Paid_leave', attendance_date__year=current_year).values('staff__id_no').annotate(total_paid_leaves=Count('attendance_type'))

    # Create a dictionary to map staff id_no to their paid leave count
    paid_leave_count_dict = {item['staff__id_no']: item['total_paid_leaves'] for item in paid_leave_counts}

    # Create a dictionary to map staff id_no to their leave count
    leave_count_dict = {item['staff__id_no']: item['total_leaves'] for item in leave_counts}

    # Add leave count and remaining leaves to each staff member in the staff_list
    for staff in staff_list:
        leave_count = leave_count_dict.get(staff['id_no'], 0)
        paid_leave_count = paid_leave_count_dict.get(staff['id_no'], 0)
        staff['leave_count'] = leave_count
        staff['paid_leave'] = paid_leave_count
        staff['remainingleaves'] = staff['totalleaves'] - leave_count - paid_leave_count

    return render(request, 'myApp/leave_limit.html', {'staff_list': staff_list})

#_____________________________________________ATTENDANCE_________________________________________________
from django import forms

def attendance(request):
    staff_list = Staff.objects.all()
    return render(request, 'myApp/attendance.html', {'staff_list': staff_list})

def error(request):
    return render(request, 'myApp/error.html')

def view_attendance(request):
     if request.method == 'GET':
        attendance_date = request.GET.get('view_attendance_date')
        attendance_records = Attendance.objects.filter(attendance_date=attendance_date)
        return render(request, 'myApp/view_attendance.html', {'attendance_records': attendance_records, 'attendance_date': attendance_date})
     return render(request, 'myApp/view_attendance.html')

def attendance_staff_detail(request, staff_id):
    staff = get_object_or_404(Staff, id_no=staff_id)
    return render(request, 'myApp/attendance_staff_detail.html', {'staff': staff})

def attendance_success(request):
    return render(request, 'myApp/attendance_success.html')

def attendance_view(request):
    if request.method == 'POST':
        attendance_date = request.POST.get('attendance_date', timezone.now().date())
        today = localtime(now()).date()

        # Convert attendance_date to a date object
        attendance_date_obj = datetime.strptime(attendance_date, '%Y-%m-%d').date()

        # Prevent updating future attendance
        if attendance_date_obj > today:
            messages.error(request, 'Cannot record attendance for future dates.')
            return redirect('myApp:error')

        # Process attendance for each staff member
        staff_list = Staff.objects.all()  # Fetch all staff members
        for staff in staff_list:
            attendance_type = request.POST.get(f'attendance_type_{staff.id_no}')
            location = request.POST.get(f'location_{staff.id_no}')  # Get location from the form
            if attendance_type:
                attendance, created = Attendance.objects.get_or_create(
                    staff=staff,
                    attendance_date=attendance_date,
                    defaults={'attendance_type': attendance_type, 'location': location}
                )
                if not created:
                    attendance.attendance_type = attendance_type
                    attendance.location = location  # Update location if attendance already exists
                    attendance.save()

        messages.success(request, 'Attendance recorded successfully!')
        return redirect('myApp:attendance_success')

    else:
        # For GET request, fetch existing attendance records for the given date
        attendance_date = request.GET.get('attendance_date', timezone.now().date())
        attendance_date_obj = datetime.strptime(str(attendance_date), '%Y-%m-%d').date()

        # Fetch existing attendance records
        attendance_records = Attendance.objects.filter(attendance_date=attendance_date_obj)

        # Create an initial data dictionary to prefill the form
        initial_data = {}
        for record in attendance_records:
            initial_data[f'attendance_type_{record.staff.id_no}'] = record.attendance_type

        # Pass initial data to the form
        form = AttendanceForm(initial=initial_data)

        # Render the form and existing attendance records
        return render(request, 'myApp/attendance.html', {
            'form': form,
            'attendance_date': attendance_date,
            'attendance_records': attendance_records
        })

def attendance_menu(request):
    return render(request, 'myApp/attendance_menu.html')

def weekly_attendance(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    attendance_records = Attendance.objects.filter(attendance_date__range=[start_date, end_date])
    
    # Initialize a dictionary to hold attendance counts for each employee
    attendance_count = {}

    for record in attendance_records:
        staff_id = record.staff.id_no  # Assuming staff.id_no uniquely identifies each employee
        if staff_id not in attendance_count:
            attendance_count[staff_id] = {
                'name': record.staff.name,  # Store employee name
                'Onsite': 0,
                'Offsite': 0,
                'WFH': 0,
                'Leave': 0,
                'Travel': 0,
                'Others': 0,
                'Paid_leave': 0,
            }
        
        # Increment the count based on attendance type
        attendance_count[staff_id][record.attendance_type] += 1

    context = {
        'attendance_records': attendance_records,
        'attendance_count': attendance_count,
    }
    
    return render(request, 'myApp/weekly_attendance.html', context)

class MonthYearForm(forms.Form):
    month = forms.ChoiceField(choices=[(str(i), str(i)) for i in range(1, 13)], label="Month")
    year = forms.ChoiceField(choices=[(str(i), str(i)) for i in range(2020, datetime.now().year + 1)], label="year")
    years = [str(i) for i in range(2020, datetime.now().year + 1)]
    label = "years"

def monthly_attendance(request):
    years = [str(i) for i in range(2020, datetime.now().year + 1)]
    year = datetime.now().year  # Initialize year with the current year
    if request.method == 'POST':
        form = MonthYearForm(request.POST)
        if form.is_valid():
            month = form.cleaned_data['month']
            year = form.cleaned_data['year']
            attendance_count = {}
            attendance_records = []

            # Convert year to integer
            year = int(year)

            # Get the start and end date for the specified month
            start_date = datetime(year, int(month), 1)
            end_date = datetime(year, int(month) + 1, 1) if month != '12' else datetime(year + 1, 1, 1)

            # Fetch attendance records for the specified month
            attendance_records = Attendance.objects.filter(attendance_date__range=[start_date, end_date])

            # Process attendance records to count attendance types per employee
            for record in attendance_records:
                staff_id = record.staff.id_no
                attendance_type = record.attendance_type

                if staff_id not in attendance_count:
                    attendance_count[staff_id] = {
                        'name': record.staff.name,
                        'Onsite': 0,
                        'Offsite': 0,
                        'WFH': 0,
                        'Leave': 0,
                        'Travel': 0,
                        'Others': 0,
                        'Paid_leave': 0,
                    }

                if attendance_type in attendance_count[staff_id]:
                    attendance_count[staff_id][attendance_type] += 1

            context = {
                'attendance_count': attendance_count,
                'attendance_records': attendance_records,
                'selected_year': year,
                'selected_month': month,
            }
            return render(request, 'myApp/month.html', context)
    else:
        form = MonthYearForm()

    context = {
        'form': form,
        'year': year,
        'years':years,
    }

    return render(request, 'myApp/month.html', context)

def staff_attendance_view(request):
    staff_list = Staff.objects.all()
    attendance_data = []
    context = {'staff_list': staff_list}

    if request.method == 'POST':
        # Get form inputs
        staff_id = request.POST.get('staff_id')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        # Validate inputs
        if not (staff_id and start_date and end_date):
            context['error_message'] = 'Please provide all required fields.'
            return render(request, 'staff_attendance.html', context)

        try:
            # Convert start_date and end_date strings to datetime.date objects
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            context['error_message'] = 'Invalid date format. Use YYYY-MM-DD.'
            return render(request, 'staff_attendance.html', context)

        if start_date > end_date:
            context['error_message'] = 'Start date cannot be after the end date.'
            return render(request, 'staff_attendance.html', context)

        # Fetch the selected staff member
        staff = get_object_or_404(Staff, id_no=staff_id)

        # Fetch attendance records for the specified date range
        attendance_records = Attendance.objects.filter(
            staff=staff,
            attendance_date__range=[start_date, end_date]
        )

        # Prepare attendance data
        attendance_data = [
            {'date': record.attendance_date, 'work_mode': record.attendance_type,'location':record.location}
            for record in attendance_records
        ]

        # Add fetched data to the context
        context.update({
            'staff': staff,
            'attendance_data': attendance_data,
            'start_date': start_date,
            'end_date': end_date,
        })

    return render(request, 'myApp/staff_list.html', context)

# _____________________________________________STAFF_PROFILES_________________________________________

def staff_profiles(request):
    staff_members = Staff.objects.all()
    context = {'staff_members': staff_members}
    return render(request, 'myApp/staff_profiles.html', context)

def view_bio(request, id_no):
    staff = get_object_or_404(Staff, id_no=id_no)
    return render(request, 'view_bio.html', {'staff': staff})

# _____________________________________________PAY_SLIP___________________________________________
def pay_slip(request):
    return render(request, 'myApp/pay_slip.html')

def pay_slip(request):
    staff_members = Staff.objects.all()  # Fetch all staff members
    context = {
        'staff_members': staff_members
    }
    return render(request, 'myApp/pay_slip.html', context)

from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from .models import Staff
from num2words import num2words

def generate_pay_slip(request, id_no):
    # Fetch the staff member based on the id_no
    staff_member = Staff.objects.get(id_no=id_no)

    # Create a PDF response
    response = HttpResponse(content_type='application/pdf')
    current_month = date.today().strftime('%B_%Y')
    response['Content-Disposition'] = f'attachment; filename="pay_slip_{staff_member.name}_{current_month}.pdf"'

    # Create the PDF using ReportLab
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    # Add the company logo
    logo_path = finders.find('myproject/images/logo.png')  # Ensure the logo is in the 'static/images' folder
    if logo_path:  # Check if logo is found
        p.drawImage(logo_path, 50, height - 100, width=120, height=50)

    # Title and Company Information
    p.setFont("Helvetica", 12)
    p.drawString(450, height - 60, "Pay Slip For the Month")
    
    # Fetch the present month
    p.setFont("Helvetica-Bold", 14)
    current_month = date.today().strftime('%B %Y')
    p.drawString(465, height - 80, f"{current_month}")

    # Employee Summary Section
    p.setFont("Helvetica-Bold", 9)
    p.setFillColor(colors.grey)
    p.drawString(65, height - 160, "EMPLOYEE SUMMARY")
    p.setFillColor(colors.black)  # Reset to black for subsequent text


    p.setFont("Helvetica", 10)
    p.setFillColor(colors.grey)
    p.drawString(65, height - 180, "Employee ID           :")
    p.setFillColor(colors.black)
    p.setFont("Helvetica", 10)
    p.drawString(160, height - 180, f"{staff_member.id_no}")


    p.setFont("Helvetica", 10)
    p.setFillColor(colors.grey)
    p.drawString(65, height - 200, f"Employee Name     :")
    p.setFillColor(colors.black)
    p.setFont("Helvetica", 10)
    p.drawString(160, height - 200, f"{staff_member.name}")

    p.setFont("Helvetica", 10)
    p.setFillColor(colors.grey)
    p.drawString(65, height - 220, f"Designation            :")
    p.setFillColor(colors.black)
    p.setFont("Helvetica", 10)
    p.drawString(160, height - 220, f"{staff_member.designation}")

    p.setFont("Helvetica", 10)
    p.setFillColor(colors.grey)
    p.drawString(65, height - 240, f"Pay Date                 :")
    p.setFillColor(colors.black)
    p.setFont("Helvetica", 10)
    p.drawString(160, height - 240, f"{date.today().strftime('%d/%m/%Y')}")

    p.setFont("Helvetica", 10)
    p.setFillColor(colors.grey)
    p.drawString(65, height - 260, f"Pay Period              :") 
    p.setFillColor(colors.black)
    p.setFont("Helvetica", 10)
    p.drawString(160, height - 260, f"{current_month}")

     # Calculate the total salary
    # Calculate the number of days the staff member was in Onsite mode in the current month
    year = date.today().year
    month = date.today().month
    onsite_days = Attendance.objects.filter(
        staff=staff_member,
        attendance_type='Onsite',
        attendance_date__year=year,
        attendance_date__month=month
    ).count()

    paid_leave_days = Attendance.objects.filter(
        staff=staff_member,
        attendance_type='Paid_Leave',
        attendance_date__year=year,
        attendance_date__month=month
    ).count()


    # Calculate the total incentive based on the number of Onsite days
    total_incentive = staff_member.incentive * onsite_days
    
    # Calculate the total salary

    paid_leave_days = Attendance.objects.filter(
        staff=staff_member,
        attendance_type='Paid_leave',
        attendance_date__year=year,
        attendance_date__month=month
    ).count()

#***********************calculate the total salary********************************
    salary = int((staff_member.basic_salary + staff_member.hra + staff_member.conveyance + staff_member.spl_allowance + total_incentive))

    total_deductions = int(staff_member.leave_deduction * paid_leave_days)+int(staff_member.income_tax + staff_member.pf)+int(staff_member.advance_amount)

    leave_deduction = int(staff_member.leave_deduction * paid_leave_days)

    total_salary = int((staff_member.basic_salary + staff_member.hra + staff_member.conveyance + staff_member.spl_allowance + total_incentive) - total_deductions)
    
#**********************************************************************************
    # Draw a dotted box around the salary information
    p.setStrokeColor(colors.black)
    p.setLineWidth(0.5)
    p.setFillColor(colors.lightgreen)
    p.setFillAlpha(0.5)  # Set opacity to 50%
    p.roundRect(340, height - 210, 220, 75, 10, stroke=1, fill=1)
    p.setFillAlpha(0.5)  # Reset opacity to 100%
    p.setFillColor(colors.black)
    p.setLineWidth(1)
    p.roundRect(340, height - 260, 220, 125, 10) #black border
    p.setFont("Helvetica-Bold", 25)
    p.drawString(350, height - 175, f"{total_salary:,.2f}")
    p.setFont("Helvetica", 10)
    p.drawString(350, height - 190, "Employee Net Pay")
    
    # Calculate the number of leave days in the current month for the staff member
    year = date.today().year
    month = date.today().month
    leave_days = Attendance.objects.filter(
        staff=staff_member,
        attendance_type='Leave',
        attendance_date__year=year,
        attendance_date__month=month
    ).count()
    p.drawString(350, height - 250, f"Leaves: {paid_leave_days + leave_days}")

    # Calculate the number of days in the current month
    num_days_in_month = monthrange(year, month)[1]
    paid_days = num_days_in_month - leave_days
    p.drawString(350, height - 230, f"Paid Days: {paid_days -(paid_leave_days+leave_days)}")

    # Earnings and Deductions Table Headers
    # Draw a box around the Earnings and Deductions headers
    p.setStrokeColor(colors.black)
    p.setLineWidth(1)
    p.roundRect(50, height - 460, 500, 150, 10)

    p.setFont("Times-Roman", 12)
    p.drawString(60, height - 330, "EARNINGS")
    p.drawString(210, height - 330, "AMOUNT")
    p.drawString(310, height - 330, "DEDUCTIONS")
    p.drawString(460, height - 330, "AMOUNT")

    # Draw a dotted line between the earning amount and basic
    p.setDash(1, 2)  # Set the dash pattern: 1 point on, 2 points off
    p.line(60, height - 340, 260, height - 340)  # Draw the line
    p.setDash()  # Reset to solid line

    p.setDash(1, 2)  # Set the dash pattern: 1 point on, 2 points off
    p.line(310, height - 340, 510, height - 340)  # Draw the line
    p.setDash()  # Reset to solid line
    # Earnings Details
    p.setFont("Helvetica", 10)
    p.drawString(60, height - 360, "Basic Salary ")
    p.setFont("Helvetica-Bold", 10)
    p.drawString(210, height - 360, f"{staff_member.basic_salary:,.0f}")
    p.setFont("Helvetica", 10)
    p.drawString(60, height - 380, "House Rent Allowance ")
    p.setFont("Helvetica-Bold", 10)
    p.drawString(210, height - 380, f"{staff_member.hra:,.0f}")
    p.setFont("Helvetica", 10)
    p.drawString(60, height - 400, "Conveyance")
    p.setFont("Helvetica-Bold", 10)
    p.drawString(210, height - 400, f"{staff_member.conveyance:,.0f}")
    p.setFont("Helvetica", 10)
    p.drawString(60, height - 420, "Special Allowance")
    p.setFont("Helvetica-Bold", 10)
    p.drawString(210, height - 420, f"{staff_member.spl_allowance:,.0f}")
    p.setFont("Helvetica", 10)
    p.drawString(60, height - 440, "Total Incentive")
    p.setFont("Helvetica-Bold", 10)
    p.drawString(210, height - 440, f"{total_incentive:,.0f}")
    p.drawString(60,height-470, "Gross Earnings")
    p.setFont("Helvetica-Bold", 10)
    p.drawString(210, height - 470, f"{salary:,.0f}")



    # Deductions Details
    p.setFont("Helvetica", 10)
    p.drawString(310, height - 360, "Income Tax")
    p.setFont("Helvetica-Bold", 10)
    p.drawString(460, height - 360, f"{staff_member.income_tax:,.0f}")
    p.setFont("Helvetica", 10)
    p.drawString(310, height - 380, "Provident Fund")
    p.setFont("Helvetica-Bold", 10)
    p.drawString(460, height - 380, f"{staff_member.pf:,.0f}")
    p.setFont("Helvetica", 10)
    p.drawString(310, height - 400, "Leave deduction")
    p.setFont("Helvetica-Bold", 10)
    p.drawString(460, height - 400, f"{leave_deduction:,.0f}")
    p.setFont("Helvetica", 10)
    p.drawString(310, height - 420, "Advance Amount")
    p.setFont("Helvetica-Bold", 10)
    p.drawString(460, height - 420, f"{staff_member.advance_amount:,.0f}")


    p.drawString(310, height - 470  , "Total Deductions")
    p.drawString(460, height - 470, f"{total_deductions:.0f}")
        

    # Net Payable
    p.setFont("Helvetica-Bold", 12)
    p.drawString(60, height - 530, "TOTAL NET PAYABLE")
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(60, height - 550, f"Amount:{num2words(total_salary, to='cardinal', lang='en').capitalize()} Rupees only")

    
    
    # Set background color for the amount only
    amount_x = 440
    amount_y = height - 560  # Moved downward
    amount_width = 110  # Extended right side
    amount_height = 50  # top and bottom
    
    p.setFillColor(colors.lightgreen)
    p.setFillAlpha(0.5)  # Set opacity to 50%
    p.roundRect(amount_x, amount_y, amount_width, amount_height, 10, stroke=0, fill=1)
    
    # Reset fill color to black for text
    p.setFillAlpha(1)  # Reset opacity to 100%
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(470, height - 540, f"{total_salary:,.2f}")

    # Draw a box around the Net Payable section
    p.setStrokeColor(colors.black)
    p.setLineWidth(1)
    p.roundRect(50, height - 560, 500, 50, 10)

    p.showPage()
    p.save()
    # Reset the advance amount after generating the pay slip
    staff_member.advance_amount = 0
    staff_member.save()
    return response

from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from datetime import date
from calendar import monthrange
from .models import Staff, Attendance  # Adjust as needed based on your models
from django.contrib.staticfiles import finders
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from urllib.parse import unquote
from django.conf import settings

def view_pay_slip(request, id_no):
    # Fetch the staff member based on the id_no
    staff_member = Staff.objects.get(id_no=id_no)

    # Calculate the total salary
    # Calculate the number of days the staff member was in Onsite mode in the current month
    year = date.today().year
    month = date.today().month
    onsite_days = Attendance.objects.filter(
        staff=staff_member,
        attendance_type='Onsite',
        attendance_date__year=year,
        attendance_date__month=month
    ).count()

    # Calculate the total incentive based on the number of Onsite days
    total_incentive = staff_member.incentive * onsite_days

    leave_days = Attendance.objects.filter(
        staff=staff_member,
        attendance_type='Leave',
        attendance_date__year=year,
        attendance_date__month=month
    ).count()

    paid_leave_days = Attendance.objects.filter(
        staff=staff_member,
        attendance_type='Paid_leave',
        attendance_date__year=year,
        attendance_date__month=month
    ).count()


    deductions = (int(staff_member.leave_deduction * paid_leave_days) )

    # Calculate the total salary
    total_salary = (staff_member.basic_salary + staff_member.hra + staff_member.conveyance + staff_member.spl_allowance + total_incentive) 

    total_deductions = (staff_member.income_tax + staff_member.pf + deductions + staff_member.advance_amount)+deductions

    pay_amount  = total_salary - total_deductions
    

    

    # Calculate the number of leave days in the current month for the staff member
    year = date.today().year
    month = date.today().month
    leave_days = Attendance.objects.filter(
        staff=staff_member,
        attendance_type='Leave',
        attendance_date__year=year,
        attendance_date__month=month
    ).count()

    year = date.today().year
    month = date.today().month
    paid_leave_days = Attendance.objects.filter(
        staff=staff_member,
        attendance_type='Paid_leave',
        attendance_date__year=year,
        attendance_date__month=month
    ).count()

    # Calculate the number of days in the current month
    num_days_in_month = monthrange(year, month)[1]
    paid_days = num_days_in_month - (leave_days + paid_leave_days)

    # Prepare context for the template
    context = {
        'staff_member': staff_member,
        'total_salary': total_salary,
        'leave_days': leave_days,
        'paid_days': paid_days,
        'pay_amount': pay_amount,
        'total_incentive': total_incentive,
        'total_deductions': total_deductions,
        'paid_leave_days': paid_leave_days,
        'current_month': date.today().strftime('%B %Y'),
        'pay_date': date.today().strftime('%d/%m/%Y'),
        'deductions':deductions,
    }

    return render(request, 'myApp/payslip_view.html', context)

def edit_earnings(request, id_no):
    staff = get_object_or_404(Staff, id_no=id_no)
        
    if request.method == 'POST':
        staff.basic_salary = request.POST['basic_salary']
        staff.hra = request.POST['hra']
        staff.conveyance = request.POST['conveyance']
        staff.spl_allowance = request.POST['spl_allowance']
        staff.incentive = request.POST['incentive']
        staff.leave_deduction = request.POST['leave_deduction']
        staff.income_tax = request.POST['income_tax']
        staff.pf = request.POST['pf']
        staff.advance_amount = request.POST['advance_amount']
        
        staff.save()
        messages.success(request, 'Data updated successfully!')
        return redirect('myApp:pay_slip')
        
    return render(request, 'myApp/edit_earnings.html', {'staff': staff})

def mail_success(request):
    return render(request, 'myApp/mail_success.html')



def send_pay_slip(request, id_no):
        staff_member = get_object_or_404(Staff, id_no=id_no)
        
        # Generate the PDF
        response = generate_pay_slip(request, id_no)
        pdf_content = response.content

        # Create the email
        subject = 'Pay Slip Generated '
        html_message = render_to_string('myApp/email.html', {'staff_member': staff_member})
        plain_message = strip_tags(html_message)
        email = EmailMessage(subject, plain_message, to=[staff_member.email])
        email.attach(f'pay_slip_{staff_member.name}_{date.today().strftime("%B_%Y")}.pdf', pdf_content, 'application/pdf')

        # Send the email
        email.send()

        messages.success(request, 'Pay slip sent successfully!')
        return redirect('myApp:mail_success')


from datetime import datetime
from django.shortcuts import render, get_object_or_404
from .models import Staff, Attendance

def fetch_attendance_view(request, id_no):
    # Fetch the staff member based on the id_no
    staff_member = get_object_or_404(Staff, id_no=id_no)
    
    # Initialize context
    context = {'staff_member': staff_member}

    # Fetch attendance records for the staff member (without any date range initially)
    attendance_data = Attendance.objects.filter(staff=staff_member)

    # Add attendance data to context
    context['attendance_data'] = [
        {'date': record.attendance_date, 'work_mode': record.attendance_type, 'location': record.location}
        for record in attendance_data
    ]

    if request.method == 'POST':
        # Get form inputs for date range
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        # Validate inputs
        if not (start_date and end_date):
            context['error_message'] = 'Please provide both start and end dates.'
            return render(request, 'myApp/attendance_view.html', context)

        try:
            # Convert start_date and end_date to datetime.date objects
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            context['error_message'] = 'Invalid date format. Use YYYY-MM-DD.'
            return render(request, 'myApp/attendance_view.html', context)

        if start_date > end_date:
            context['error_message'] = 'Start date cannot be after the end date.'
            return render(request, 'myApp/attendance_view.html', context)

        # Fetch filtered attendance records for the specified date range
        attendance_data = Attendance.objects.filter(
            staff=staff_member,
            attendance_date__range=[start_date, end_date]
        )

        # Add the filtered attendance data to context
        context['attendance_data'] = [
            {'date': record.attendance_date, 'work_mode': record.attendance_type, 'location': record.location}
            for record in attendance_data
        ]
        context['start_date'] = start_date
        context['end_date'] = end_date

    return render(request, 'myApp/attendance_view.html', context)




# _____________________________________________settings_____________________________________________
def settings(request):
    return render(request, 'myApp/settings.html')



