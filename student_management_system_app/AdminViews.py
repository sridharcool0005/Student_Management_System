import csv
import json
import os
import requests

from datetime import datetime

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, UpdateView, DeleteView

from django.templatetags.static import static

from student_management_system_app.forms import StudentCreationForm, StudentEditForm, StudentBulkUploadForm, \
    StudentBlukUploadForm
from student_management_system_app.models import CustomUser, Course, Subject, Staff, Student, SessionYear, \
    StudentBulkUpload, FeedBackStudent, FeedBackStaff, LeaveReportStudent, LeaveReportStaff, Attendance, \
    AttendanceReport, NotificationStudent, NotificationStaff


class DateInput(forms.DateInput):
    input_type = 'date'


@login_required
def admin_home(request):
    total_students = Student.objects.all().count()
    total_staffs = Staff.objects.all().count()
    total_subjects = Subject.objects.all().count()
    total_courses = Course.objects.all().count()

    courses = Course.objects.all()
    course_name_list = []
    subject_count_list = []
    student_course_name_list = []
    student_count_list = []    
    for course in courses:
        # To fetch Course's Subject Data
        subject_count = Subject.objects.filter(course_id=course.id).count()
        if subject_count > 0:
            course_name_list.append(course.course_name)
            subject_count_list.append(subject_count)

        # To fetch Student's Course Data
        student_count = Student.objects.filter(course_id=course.id).count()
        if student_count > 0:
            student_course_name_list.append(course.course_name)
            student_count_list.append(student_count)

    # To fetch Subject Data
    student_subject_name_list = []
    student_count_list_in_subject = []
    subjects = Subject.objects.all()
    for subject in subjects:
        student_count_in_subject = Student.objects.filter(course_id=subject.course_id).count()
        if student_count_in_subject > 0:
            student_subject_name_list.append(subject.subject_name)
            student_count_list_in_subject.append(student_count_in_subject)

    # To fetch Staff Data Attendance VS Leaves
    staff_attendance_list = []
    staff_leaves_list = []
    staff_names_list = []

    staffs = Staff.objects.all()
    for staff in staffs:
        subjects = Subject.objects.filter(staff_id=staff.admin.id)
        total_attendance = Attendance.objects.filter(subject_id__in=subjects).count()
        total_leaves = LeaveReportStaff.objects.filter(staff_id=staff.id, leave_status=True).count()
        staff_names_list.append(staff.admin.get_full_name())
        staff_attendance_list.append(total_attendance)
        staff_leaves_list.append(total_leaves)

    # To fetch Attendance Data by Student
    students = Student.objects.all()
    student_list = []
    present_attendance_by_student_count_list = []
    absent_attendance_by_student_count_list = []
    for student in students:
        attendancereport_present_count = AttendanceReport.objects.filter(student_id=student.id, status=True).count()
        attendancereport_absent_count = AttendanceReport.objects.filter(student_id=student.id, status=False).count()
        if attendancereport_present_count > 0 or attendancereport_absent_count > 0:
            student_list.append(student.admin.get_full_name())
            present_attendance_by_student_count_list.append(attendancereport_present_count)
            absent_attendance_by_student_count_list.append(attendancereport_absent_count)
      
    context = {
        'total_students': total_students,
        'total_staffs': total_staffs,
        'total_subjects': total_subjects,
        'total_courses': total_courses,
        'course_name_list': course_name_list,
        'subject_count_list': subject_count_list,
        'student_course_name_list': student_course_name_list,
        'student_count_list': student_count_list,
        'student_subject_name_list': student_subject_name_list,
        'student_count_list_in_subject': student_count_list_in_subject,
        'staff_names_list': staff_names_list,
        'staff_attendance_list': staff_attendance_list,
        'staff_leaves_list': staff_leaves_list,
        'student_list': student_list,
        'present_attendance_by_student_count_list': present_attendance_by_student_count_list,
        'absent_attendance_by_student_count_list': absent_attendance_by_student_count_list       
    }
    return render(request, 'student_management_system_app/admin_template/admin_home.html', context)


@login_required
def admin_profile(request):
    context = {
        'user': CustomUser.objects.get(id=request.user.id)
    }
    return render(request, 'student_management_system_app/admin_template/admin_profile.html', context)


@login_required
def admin_profile_save(request):
    if request.method != 'POST':
        return redirect(reverse('student_management_system_app:admin_profile'))
    else:
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        try:
            user = CustomUser.objects.get(id=request.user.id)
            user.first_name = first_name
            user.last_name = last_name
            if password is not None and password != "":
                user.set_password(password)
            user.save()
            messages.success(request, "Successfully updated your profile.")
            return redirect(reverse('student_management_system_app:admin_profile'))
        except Exception as e:
            messages.error(request, "Failed To Update your profile Errors: {}".format(e))
            return redirect(reverse('student_management_system_app:admin_profile'))


@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def check_email_exist(request):
    email = request.POST.get('email')
    user = CustomUser.objects.filter(email=email).exists()
    if user:
        return HttpResponse(True)
    else:
        return HttpResponse(False)


@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def check_username_exist(request):
    username = request.POST.get('username')
    user = CustomUser.objects.filter(username=username).exists()
    if user:
        return HttpResponse(True)
    else:
        return HttpResponse(False)
        

@login_required
def add_staff(request):
    return render(request, 'student_management_system_app/admin_template/add_staff.html')


@login_required
def add_staff_save(request):
    if request.method != "POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        address = request.POST.get("address")
        try:
            user = CustomUser.objects.create_user(username=username, password=password, email=email,
                                                first_name=first_name, last_name=last_name, user_type=2)
            user.staff.address = address
            user.save()
            messages.success(request, "Successfully Added Staff")
            return redirect('student_management_system_app:add_staff')
        except:
            messages.error(request, "Failed to Add Staff")
            return redirect('student_management_system_app:add_staff')


@login_required
def manage_staffs(request):
    staffs = Staff.objects.all()
    return render(request, 'student_management_system_app/admin_template/manage_staffs.html', {"staffs":staffs})


@login_required
def edit_staff(request, staff_id):
    staff = Staff.objects.get(admin=staff_id)
    return render(request, 'student_management_system_app/admin_template/edit_staff.html', {"staff":staff,"id":staff_id})


@login_required
def edit_staff_save(request):
    if request.method != "POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        staff_id = request.POST.get("staff_id")
        if staff_id == None:
            return redirect("student_management_system_app:manage_staffs")

        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        address = request.POST.get("address")
        try:
            user = CustomUser.objects.get(id=staff_id, username=username)
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.save()

            staff_model = Staff.objects.get(admin=staff_id)
            staff_model.address = address
            staff_model.save()
            messages.success(request, "Successfully Edited Staff")
            return redirect('student_management_system_app:edit_staff', staff_id)
        except Exception as e:
            messages.error(request, "Failed to Edit Staff {}".format(e))
            return redirect('student_management_system_app:edit_staff', staff_id)


@login_required
def manage_session_years(request):
    session_years = SessionYear.objects.all()
    return render(request, 'student_management_system_app/admin_template/manage_session_years.html', {"session_years":session_years})


########## Using Custom Form for adding - need save function separately to do creation ##########
# @login_required()
# def add_session_year(request):
#     form = SessionYearForm()
#     return render(request, 'student_management_system_app/admin_template/add_session_year.html', {
#         'form': form
#     })


########## Using Custom Form for adding ##########
# class SessionYearCreateView(LoginRequiredMixin, View):
#     def get(self, request):
#         form = SessionYearForm()
#         return render(request, 'student_management_system_app/admin_template/add_session_year.html', {
#             'form': form
#         })


#     def post(self, request):
#         form = SessionYearForm(request.POST)
#         if form.is_valid():
#             session_start=form.cleaned_data['session_start']
#             session_end=form.cleaned_data['session_end']

#             try:
#                 session_year=SessionYear(session_start=session_start, session_end=session_end)
#                 session_year.save()

#                 messages.success(request,"Successfully Added Session Year")
#                 return redirect(reverse('student_management_system_app:add_session_year'))
#             except Exception as e:
#                 messages.error(request, "Failed To Add Session Year Errors: {}".format(e))
#                 return redirect(reverse('student_management_system_app:add_session_year'))

########## Using Django's in-built Model CreateView - so less code to write all managed by Django ##########
class SessionYearCreateView(LoginRequiredMixin, CreateView):
    model = SessionYear
    template_name ='student_management_system_app/admin_template/add_session_year.html'
    fields = ['session_start', 'session_end']
    # success_url = '/'

    def get_form(self, form_class=None):
        form = super(SessionYearCreateView, self).get_form(form_class)
        form.fields['session_start'].widget = DateInput()
        form.fields['session_end'].widget = DateInput()
        return form

    def form_valid(self, form):
        form.save(commit=True)
        messages.success(self.request, "Successfully Added Session Year")
        return redirect('student_management_system_app:add_session_year')


class SessionYearUpdateView(LoginRequiredMixin, UpdateView):
    model = SessionYear
    template_name ='student_management_system_app/admin_template/edit_session_year.html'
    fields = ['session_start', 'session_end']
    # success_url = '/'

    def get_form(self, form_class=None):
        form = super(SessionYearUpdateView, self).get_form(form_class)
        form.fields['session_start'].widget = DateInput()
        form.fields['session_end'].widget = DateInput()
        return form

    def form_valid(self, form):
        instance = form.save()
        messages.success(self.request, "Successfully Edited Session Year")
        # return redirect('student_management_system_app:manage_session_years')
        return redirect('student_management_system_app:edit_session_year', instance.pk)


class SessionYearDeleteView(LoginRequiredMixin, DeleteView):
    model = SessionYear
    template_name = 'student_management_system_app/admin_template/delete_session_year.html'
    success_url = reverse_lazy('student_management_system_app:manage_session_years')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Successfully Deleted Session Year")
        return super().delete(self, request, *args, **kwargs)


@login_required
def add_course(request):
    return render(request, 'student_management_system_app/admin_template/add_course.html')


@login_required
def add_course_save(request):
    if request.method != "POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        course = request.POST.get("course")
        try:            
            course_model = Course(course_name=course)
            course_model.save()
            messages.success(request, "Successfully Added Course")
            return redirect('student_management_system_app:add_course')
        except:
            messages.error(request, "Failed To Add Course")
            return redirect('student_management_system_app:add_course')


@login_required
def manage_courses(request):
    courses = Course.objects.all()
    return render(request, 'student_management_system_app/admin_template/manage_courses.html', {"courses":courses})


@login_required
def edit_course(request, course_id):    
    course = get_object_or_404(Course, id=course_id)
    return render(request, 'student_management_system_app/admin_template/edit_course.html', {"course":course,"id":course_id})


@login_required
def edit_course_save(request):
    if request.method!="POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        course_id = request.POST.get("course_id")
        if course_id is None:
            return redirect("student_management_system_app:manage_courses")

        course = request.POST.get("course")
        try:
            course_model = Course.objects.get(id=course_id)
            course_model.course_name=course
            course_model.save()
            messages.success(request, "Successfully Edited Course")
            return redirect('student_management_system_app:edit_course', course_id)
        except Exception as e:
            messages.error(request, "Failed To Edit Course Errors: {}".format(e))
            # return redirect(reverse('student_management_system_app:edit_course', kwargs={'course_id':course_id}))
            return redirect('student_management_system_app:edit_course', course_id)


@login_required
def add_subject(request):
    courses=Course.objects.all()
    staffs=CustomUser.objects.filter(user_type=2)
    return render(request,"student_management_system_app/admin_template/add_subject.html",{"staffs":staffs,"courses":courses})


@login_required
def add_subject_save(request):
    if request.method!="POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        subject_name=request.POST.get("subject_name")
        course_id=request.POST.get("course")
        course=Course.objects.get(id=course_id)
        staff_id=request.POST.get("staff")
        staff=CustomUser.objects.get(id=staff_id)

        try:
            subject=Subject(subject_name=subject_name,course_id=course,staff_id=staff)
            subject.save()
            messages.success(request,"Successfully Added Subject")
            return redirect("student_management_system_app:add_subject")
        except:
            messages.error(request,"Failed to Add Subject")
            return redirect("student_management_system_app:add_subject")


@login_required
def manage_subjects(request):
    subjects = Subject.objects.all()
    return render(request, 'student_management_system_app/admin_template/manage_subjects.html', {"subjects":subjects})


@login_required
def edit_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    courses=Course.objects.all()
    staffs=CustomUser.objects.filter(user_type=2)
    context = {
                'subject': subject,
                'courses': courses,
                'staffs': staffs,                
                'id': subject_id
    }
    return render(request, 'student_management_system_app/admin_template/edit_subject.html', context)


@login_required
def edit_subject_save(request):
    if request.method!="POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        subject_id = request.POST.get("subject_id")
        if subject_id is None:
            return redirect("student_management_system_app:manage_subjects")

        subject_name=request.POST.get("subject_name")
        staff_id=request.POST.get("staff")
        course_id=request.POST.get("course")

        try:
            subject=Subject.objects.get(id=subject_id)
            subject.subject_name=subject_name
            staff=CustomUser.objects.get(id=staff_id)
            subject.staff_id=staff
            course=Course.objects.get(id=course_id)
            subject.course_id=course
            subject.save()

            messages.success(request,"Successfully Edited Subject")
            return redirect('student_management_system_app:edit_subject', subject_id)
        except Exception as e:
            messages.error(request, "Failed To Edit Subject Errors: {}".format(e))
            return redirect('student_management_system_app:edit_subject', subject_id)

    
@login_required
def add_student(request):
    form = StudentCreationForm()
    return render(request, 'student_management_system_app/admin_template/add_student.html', {"form": form})


@login_required
def add_student_save(request):
    if request.method != "POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        form = StudentCreationForm(request.POST, request.FILES)        
        if form.is_valid():
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            address = form.cleaned_data["address"]

            session_year_id = form.cleaned_data["session_year"].id

            course_id = form.cleaned_data["course"].id
            gender = form.cleaned_data["gender"]

            profile_pic = request.FILES['profile_pic']

            # FileSystemStorage fallbacks to MEDIA_ROOT when location
            # is empty, so we restore the empty value.
            # FileSystemStorage(location='/uploads') # i.e. /media/uploads/<filename>
            fs = FileSystemStorage()
            filename = fs.save(profile_pic.name, profile_pic)
            # profile_pic_url = fs.url(filename)

            try:
                user = CustomUser.objects.create_user(username=username, password=password, email=email,
                                                    first_name=first_name, last_name=last_name, user_type=3)
                user.student.address = address
                course = Course.objects.get(id=course_id)
                user.student.course_id = course

                session_year = SessionYear.objects.get(id=session_year_id)
                user.student.session_year_id = session_year

                user.student.gender = gender
                user.student.profile_pic = filename
                user.save()
                messages.success(request, "Successfully Added Student")
                return redirect("student_management_system_app:add_student")
            except Exception as e:
                messages.error(request, "Failed to Add Student Errors: {}".format(e))
                # messages.error(request, "Failed to Add Student")
                return redirect("student_management_system_app:add_student")
        else:
            form = StudentCreationForm(request.POST)
            return render(request, 'student_management_system_app/admin_template/add_student.html', {"form": form})


@login_required
def manage_students(request):
    students = Student.objects.all()
    return render(request, 'student_management_system_app/admin_template/manage_students.html', {"students":students})


@login_required
def edit_student(request, student_id):
    # request.session['student_id']=student_id
    student = get_object_or_404(Student, admin=student_id)
    # student=Student.objects.get(admin=student_id)

    form=StudentEditForm(initial={'student_id': student_id})
    form.fields['email'].initial=student.admin.email
    form.fields['first_name'].initial=student.admin.first_name
    form.fields['last_name'].initial=student.admin.last_name
    form.fields['username'].initial=student.admin.username
    form.fields['address'].initial=student.address
    form.fields['course'].initial=student.course_id
    form.fields['gender'].initial=student.gender

    form.fields['session_year'].initial=student.session_year_id

    context = {
        'form': form,
        'id': student_id,
        'username': student.admin.username
    }
    
    return render(request,"student_management_system_app/admin_template/edit_student.html", context)


@login_required
def edit_student_save(request):
    if request.method!="POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        # student_id=request.session.get("student_id")
        student_id = request.POST.get("student_id")
        if student_id == None:
            return redirect("student_management_system_app:manage_students")

        form=StudentEditForm(request.POST, request.FILES)
        if form.is_valid():
            student_id=form.cleaned_data["student_id"]
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            address = form.cleaned_data["address"]
            session_year_id = form.cleaned_data["session_year"].id
            course_id = form.cleaned_data["course"].id
            gender = form.cleaned_data["gender"]

            if request.FILES.get('profile_pic', False):
                profile_pic=request.FILES['profile_pic']
                fs=FileSystemStorage()
                profile_pic_url = fs.save(profile_pic.name, profile_pic)
                # filename = fs.save(profile_pic.name, profile_pic)
                # profile_pic_url = fs.url(filename)
            else:
                profile_pic_url=None

            try:
                user=CustomUser.objects.get(id=student_id)
                user.first_name=first_name
                user.last_name=last_name
                user.username=username
                user.email=email
                user.save()

                student=Student.objects.get(admin=student_id)
                student.address=address
                
                session_year = SessionYear.objects.get(id=session_year_id)
                user.student.session_year_id = session_year

                student.gender=gender

                course=Course.objects.get(id=course_id)
                student.course_id=course
                if profile_pic_url is not None:
                    student.profile_pic=profile_pic_url
                student.save()
                # del request.session['student_id']
                messages.success(request,"Successfully Edited Student")
                return redirect("student_management_system_app:edit_student", student_id=student_id)
            except Exception as e:
                messages.error(request,"Failed to Edit Student! Errors: {}".format(e))
                return redirect("student_management_system_app:edit_student", student_id=student_id)
        else:
            form=StudentEditForm(request.POST, initial={'student_id': student_id})
            # student=Students.objects.get(admin=student_id)
            student = get_object_or_404(Student, admin=student_id)

            context = {
                'form': form,
                'id': student_id,
                'username': student.admin.username
            }
            
            return render(request,"student_management_system_app/admin_template/edit_student.html", context)


@login_required
def add_students_bulk(request):   
    if request.method == 'POST':
        form = StudentBulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:                
                csv_file = request.FILES['csv_file']
                if not csv_file.name.endswith('.csv'):
                    messages.error(request,'File is not CSV type')
                    return redirect(reverse('student_management_system_app:add_students_bulk'))
                #if file is too large, return
                if csv_file.multiple_chunks():
                    messages.error(request,'Uploaded file is too big (%.2f MB).' % (csv_file.size/(1000*1000),))
                    return redirect(reverse('student_management_system_app:add_students_bulk'))

                # Upload the file
                fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'bulk_uploads'))
                filename = fs.save(csv_file.name, csv_file)
                # uploaded_file_url = fs.url(filename)

                DATETIME_INPUT_FORMATS = [
                    '%Y-%m-%d %H:%M:%S',     # '2006-10-25 14:30:59'
                    '%Y-%m-%d %H:%M:%S.%f',  # '2006-10-25 14:30:59.000200'
                    '%Y-%m-%d %H:%M',        # '2006-10-25 14:30'
                    '%Y-%m-%d',              # '2006-10-25'
                    '%m/%d/%Y %H:%M:%S',     # '10/25/2006 14:30:59'
                    '%m/%d/%Y %H:%M:%S.%f',  # '10/25/2006 14:30:59.000200'
                    '%m/%d/%Y %H:%M',        # '10/25/2006 14:30'
                    '%m/%d/%Y',              # '10/25/2006'
                    '%m/%d/%y %H:%M:%S',     # '10/25/06 14:30:59'
                    '%m/%d/%y %H:%M:%S.%f',  # '10/25/06 14:30:59.000200'
                    '%m/%d/%y %H:%M',        # '10/25/06 14:30'
                    '%m/%d/%y',              # '10/25/06'
                ]

                DATETIME_INPUT_FORMAT = '%m/%d/%Y'

                expected_headers = ['email', 'password', 'first_name', 'last_name', 'username', 'address', 'course_name', 'gender', 'session_start', 'session_end', 'profile_pic']
              
                with open(os.path.join(settings.MEDIA_ROOT, 'bulk_uploads', filename)) as csvfile:
                    reader = csv.reader(csvfile)

                    headers = next(reader, None) # Reading Header Row

                    if str(headers) != str(expected_headers):
                        messages.error(request, "The expected headers are %s. Please supply precisely these headers" % str(expected_headers))
                        return redirect(reverse('student_management_system_app:add_students_bulk'))

                    header_map = {}
                    for i in range(len(headers)):
                        header_map[headers[i]] = i

                    update_count = 0
                    new_count = 0

                    with transaction.atomic():
                        for line in reader:
                            blanked_line = list(map(lambda x: x or None, line)) #Turns '' into None

                            # Saving Course
                            course_name=blanked_line[header_map['course_name']]
                            if Course.objects.filter(course_name=course_name).count():
                                # Course already exists - updating it
                                course = Course.objects.get(course_name=course_name)
                            else:
                                course = Course(course_name=course_name)
                            course.save()
                            
                            # Saving Session Year
                            if blanked_line[header_map['session_start']]:#is not None
                                #Note this is technically not necessary, because date is a required (not null) field
                                #However, should this change in the future, we don't want to cause a hard to find bug
                                session_start = datetime.strptime(blanked_line[header_map['session_start']], DATETIME_INPUT_FORMAT)
                            else:
                                session_start = None
                            if blanked_line[header_map['session_end']]:#is not None
                                #Note this is technically not necessary, because date is a required (not null) field
                                #However, should this change in the future, we don't want to cause a hard to find bug
                                session_end = datetime.strptime(blanked_line[header_map['session_end']], DATETIME_INPUT_FORMAT)
                            else:
                                session_end = None
                            
                            if SessionYear.objects.filter(session_start=session_start, session_end=session_end).count():
                                # Session Year already exists - updating it
                                session_year = SessionYear.objects.get(session_start=session_start, session_end=session_end)
                            else:
                                session_year = SessionYear(session_start=session_start, session_end=session_end)
                            session_year.save()
                            
                            email = blanked_line[header_map['email']]
                            password = blanked_line[header_map['password']]
                            first_name = blanked_line[header_map['first_name']]
                            last_name = blanked_line[header_map['last_name']]
                            username = blanked_line[header_map['username']]

                            address = blanked_line[header_map['address']]
                            gender = blanked_line[header_map['gender']]
                            profile_pic = blanked_line[header_map['profile_pic']]

                            data_dict = { 'email': email, 'password': password, 'first_name': first_name,
                                 'last_name': last_name, 'username': username, 'address': address,
                                 'course': course, 'gender': gender, 'session_year': session_year, 
                                 'profile_pic': profile_pic }
                            
                            form_student = StudentBlukUploadForm(data_dict)
                            
                            if form_student.is_valid():
                                # Saving Student
                                username = form_student.cleaned_data["username"]
                                email = form_student.cleaned_data["email"]
                                if CustomUser.objects.filter(username=username, email=email).count():
                                    # User already exists - updating it
                                    user = CustomUser.objects.get(username=username, email=email)
                                    update_count += 1
                                else:
                                    user = CustomUser()
                                    user.username = username
                                    user.email = email
                                    new_count += 1
                          
                                first_name = form_student.cleaned_data["first_name"]                                
                                last_name = form_student.cleaned_data["last_name"]

                                user.first_name = first_name
                                user.last_name = last_name
                                user.set_password(password)
                                # For Student User Type = 3 
                                user.user_type=3
                                user.save()                              

                                address = form_student.cleaned_data["address"]                              
                                # session_year_id = form_student.cleaned_data["session_year"].id
                                # course_id = form_student.cleaned_data["course"].id
                                gender = form_student.cleaned_data["gender"]                                

                                user.student.address = address
                                user.student.session_year_id = session_year
                                user.student.course_id = course
                                user.student.gender = gender
                                user.student.profile_pic = profile_pic
                                user.student.save()
                                
                            else:
                                messages.error(request, form_student.errors.as_json())
                                return redirect(reverse('student_management_system_app:add_students_bulk'))

                    messages.success(request, "%s new rows. %s rows updated." % (new_count, update_count))

                form = StudentBulkUploadForm()
            except Exception as e:
                messages.error(request, 'Unable to upload file. ' + repr(e))
                return redirect(reverse('student_management_system_app:add_students_bulk'))
        else:
            messages.error(request, form.errors.as_json())
            return redirect(reverse('student_management_system_app:add_students_bulk'))
    else:
        form = StudentBulkUploadForm()

    context = {
        'form': form
    }
    return render(request, 'student_management_system_app/admin_template/add_students_bulk.html', context)


class StudentBulkUploadView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = StudentBulkUpload
    template_name = 'student_management_system_app/admin_template/add_students_bulk.html'
    fields = ['csv_file']
    success_url = 'student_management_system_app:manage_students'
    success_message = 'Successfully uploaded students'
    

@login_required   
def download_student_csv_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_template.csv"'

    writer = csv.writer(response)

    writer.writerow(['first_name', 'last_name', 'email', 'gender', 'profile_pic', 'address', 'course_name', 'session_start', 'session_end'])

    return response


@login_required
def staff_feedback_message(request):
    feedbacks = FeedBackStaff.objects.all()
    return render(request, 'student_management_system_app/admin_template/staff_feedback_message.html', { 'feedbacks' : feedbacks })



@csrf_exempt
def staff_feedback_message_replied(request):
    feedback_id = request.POST.get("id")
    feedback_message = request.POST.get("message")

    try:
        feedback = FeedBackStaff.objects.get(id=feedback_id)
        feedback.feedback_reply = feedback_message
        feedback.save()
        return HttpResponse("True")
    except:
        return HttpResponse("False")


@login_required
def student_feedback_message(request):
    feedbacks = FeedBackStudent.objects.all()
    return render(request, 'student_management_system_app/admin_template/student_feedback_message.html', { 'feedbacks' : feedbacks })


@csrf_exempt
def student_feedback_message_replied(request):
    feedback_id = request.POST.get("id")
    feedback_message = request.POST.get("message")

    try:
        feedback = FeedBackStudent.objects.get(id=feedback_id)        
        feedback.feedback_reply = feedback_message
        feedback.save()
        return HttpResponse("True")
    except:
        return HttpResponse("False")


@login_required
def staff_leave_view(request):
    leaves = LeaveReportStaff.objects.all()
    return render(request, 'student_management_system_app/admin_template/staff_leave_view.html', { 'leaves': leaves })


@login_required
def staff_leave_approve(request, pk):
    try:
        leave = get_object_or_404(LeaveReportStaff, pk=pk)
        leave.leave_status = 1
        leave.save()
        messages.success(request,"Successfully Approved Staff Leave Request")
        return redirect(reverse('student_management_system_app:staff_leave_view')) 
    except Exception as e:
        messages.error(request, "Failed To Approve Staff Leave Request Errors: {}".format(e))
        return redirect(reverse('student_management_system_app:staff_leave_view'))


@login_required
def staff_leave_disapprove(request, pk):
    try:
        leave = get_object_or_404(LeaveReportStaff, pk=pk)
        leave.leave_status = 2
        leave.save()
        messages.error(request,"Successfully Disapproved Staff Leave Request")
        return redirect(reverse('student_management_system_app:staff_leave_view')) 
    except Exception as e:
        messages.error(request, "Failed To Disapprove Staff Leave Request Errors: {}".format(e))
        return redirect(reverse('student_management_system_app:staff_leave_view'))


@login_required
def student_leave_view(request):
    leaves = LeaveReportStudent.objects.all()
    return render(request, 'student_management_system_app/admin_template/student_leave_view.html', { 'leaves': leaves })


@login_required
def student_leave_approve(request, pk):
    try:
        leave = get_object_or_404(LeaveReportStudent, pk=pk)
        leave.leave_status = 1
        leave.save()
        messages.success(request,"Successfully Approved Student Leave Request")
        return redirect(reverse('student_management_system_app:student_leave_view')) 
    except Exception as e:
        messages.error(request, "Failed To Approve Student Leave Request Errors: {}".format(e))
        return redirect(reverse('student_management_system_app:student_leave_view'))


@login_required
def student_leave_disapprove(request, pk):
    try:
        leave = get_object_or_404(LeaveReportStudent, pk=pk)
        leave.leave_status = 2
        leave.save()
        messages.error(request,"Successfully Disapproved Student Leave Request")
        return redirect(reverse('student_management_system_app:student_leave_view')) 
    except Exception as e:
        messages.error(request, "Failed To Disapprove Student Leave Request Errors: {}".format(e))
        return redirect(reverse('student_management_system_app:student_leave_view'))


@login_required
def admin_view_attendance_reports(request):
    context = {
        'subjects' : Subject.objects.all(),
        'session_years' : SessionYear.objects.all()
    }
    return render(request, 'student_management_system_app/admin_template/admin_view_attendance_reports.html', context)


@csrf_exempt
def admin_get_attendance_dates(request):
    subject_id = request.POST.get("subject")
    session_year_id = request.POST.get("session_year")
    subject = get_object_or_404(Subject, pk=subject_id)
    session_year = get_object_or_404(SessionYear, pk=session_year_id)

    attendances = Attendance.objects.filter(subject_id=subject, session_year_id=session_year)

    list_data = []
    for attendance in attendances:
        data_small = { "id":attendance.id, "session_year_id": attendance.session_year_id.id, "attendance_date": str(attendance.attendance_date) }
        list_data.append(data_small)
    return JsonResponse(json.dumps(list_data), content_type="application/json", safe=False)


@csrf_exempt
def admin_get_attendance_students(request):
    attendance_date = request.POST.get('attendance_date')
    attendance = Attendance.objects.get(id=attendance_date)

    attendancereports = AttendanceReport.objects.filter(attendance_id=attendance)

    list_data = []
    for attendancereport in attendancereports:
        data_small = { "id":attendancereport.student_id.admin.id, "name": attendancereport.student_id.admin.get_full_name(), "status": attendancereport.status }
        list_data.append(data_small)
    return JsonResponse(json.dumps(list_data), content_type="application/json", safe=False)


def admin_send_notification_to_staff(request):
    context = {
        'staffs': Staff.objects.all()
    }
    return render(request, 'student_management_system_app/admin_template/staff_notification.html', context)


def admin_send_notification_to_student(request):
    context = {
        'students': Student.objects.all()
    }
    return render(request, 'student_management_system_app/admin_template/student_notification.html', context)

@csrf_exempt
def send_staff_notification(request):
    staff_id = request.POST.get('staff_id')
    message = request.POST.get('message')
    staff = Staff.objects.get(admin=staff_id)
    token = staff.fcm_token
    url = 'https://fcm.googleapis.com/fcm/send'
    body = {
        'notification':{
            'title': 'Message from Student Management System',
            'body': message,
            'click_action': reverse('student_management_system_app:staff_all_notifications'),
            'icon': static('logo.png')
        },
        'to': token
    }
    headers = {
        'Content-Type':'application/json',
        'Authorization': 'key=AAAA1Su7yow:APA91bElVNCshX1xLGnUzo28dr5F8XDo8QLzl0Z0tiCRmyAFsZCIzWgnKlRjndOnrFCXfLtPeOn3LkSwOaW9FY2VNE7u563YQWRlXWaEr3uQO8fqMNkjjPoTzBSRCRwNhEjP_wGVVooI'
    }
    response = requests.post(url, data=json.dumps(body), headers=headers)
    print(response.text)
    notification = NotificationStaff(staff_id=staff, message=message)
    notification.save()
    return HttpResponse("True")

@csrf_exempt
def send_student_notification(request):
    student_id = request.POST.get('student_id')
    message = request.POST.get('message')
    student = Student.objects.get(admin=student_id)
    token = student.fcm_token
    url = 'https://fcm.googleapis.com/fcm/send'
    body = {
        'notification':{
            'title': 'Message from Student Management System',
            'body': message,
            'click_action': reverse('student_management_system_app:student_all_notifications'),
            'icon': static('logo.png')
        },
        'to': token
    }
    headers = {
        'Content-Type':'application/json',
        'Authorization': 'key=AAAA1Su7yow:APA91bElVNCshX1xLGnUzo28dr5F8XDo8QLzl0Z0tiCRmyAFsZCIzWgnKlRjndOnrFCXfLtPeOn3LkSwOaW9FY2VNE7u563YQWRlXWaEr3uQO8fqMNkjjPoTzBSRCRwNhEjP_wGVVooI'
    }
    response = requests.post(url, data=json.dumps(body), headers=headers)
    print(response.text)
    notification = NotificationStudent(student_id=student, message=message)
    notification.save()
    return HttpResponse("True")