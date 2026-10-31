from django.shortcuts import render, redirect, get_object_or_404
from lms_app.models import *
from lms_app.forms import *
from lms_app.decorators import *
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.db.models import Q, Count
from django.db import transaction


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_view')
    form_data= AuthenticationForm()
    if request.method=='POST':
        form_data= AuthenticationForm(request, data= request.POST)
        if form_data.is_valid():
            login(request, form_data.get_user())
            messages.success(request, 'Logged in successfully.')
            return redirect('dashboard_view')
    context={
        'form_title': 'User Login Page',
        'form_btn': 'Login',
        'title': 'Login',
        'form_data': form_data,
        'alt_text': "Don't have an account?",
        'alt_link_text': 'Register here',
        'alt_url': 'register_view',
    }
    return render(request, 'master/base_form.html', context)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_view')
    form_data= RegistrationForm()
    if request.method=='POST':
        form_data= RegistrationForm(request.POST)
        if form_data.is_valid():
            form_data.save()
            messages.success(request, 'Registration successful. Please login.')
            return redirect('login_view')
    context={
        'form_title': 'User Registration Page',
        'form_btn': 'Register',
        'title': 'Register',
        'form_data': form_data,
        'alt_text': 'Already have an account?',
        'alt_link_text': 'Login here',
        'alt_url': 'login_view',
    }
    return render(request, 'master/base_form.html', context)


@login_required
def dashboard_view(request):
    if request.user.is_superuser:
        context={
            'title': 'Dashboard',
            'role': 'Admin',
            'total_students': UserProfileModel.objects.filter(role='Student', user__is_superuser=False).count(),
            'total_instructors': UserProfileModel.objects.filter(role='Instructor', user__is_superuser=False).count(),
            'total_courses': CourseModel.objects.count(),
            'total_enrollments': EnrollmentModel.objects.count(),
            'pending_count': CourseModel.objects.filter(approval_status='Pending').count(),
            'pending_courses': CourseModel.objects.filter(approval_status='Pending').select_related('instructor', 'category'),
            'popular_courses': CourseModel.objects.filter(approval_status='Approved').annotate(student_count=Count('enrollments')).order_by('-student_count')[:5],
        }
        return render(request, 'dashboard.html', context)
    try:
        profile= request.user.user_profile
    except ObjectDoesNotExist:
        messages.warning(request, 'Please update your profile first.')
        return redirect('profile_update_view')

    if profile.role == 'Instructor':
        courses= CourseModel.objects.filter(instructor=request.user)
        enrollments= EnrollmentModel.objects.filter(course__instructor=request.user)
        context={
            'title': 'Dashboard',
            'role': 'Instructor',
            'courses': courses,
            'total_courses': courses.count(),
            'approved_count': courses.filter(approval_status='Approved').count(),
            'pending_count': courses.filter(approval_status='Pending').count(),
            'total_students': enrollments.values('student').distinct().count(),
            'recent_enrollments': enrollments.select_related('student', 'course')[:5],
        }
    else:
        context={
            'title': 'Dashboard',
            'role': 'Student',
            'enrollments': EnrollmentModel.objects.filter(student=request.user).select_related('course'),
        }
    return render(request, 'dashboard.html', context)


@login_required
def profile_page(request):
    try:
        profile= request.user.user_profile
    except ObjectDoesNotExist:
        profile= None
    context={
        'title': 'Profile',
        'profile': profile,
    }
    return render(request, 'profile.html', context)

@login_required
def profile_update_view(request):
    try:
        profile_data= request.user.user_profile
    except ObjectDoesNotExist:
        profile_data= None
    form_data= UpdateProfileForm(instance=profile_data, initial={'email': request.user.email})
    if request.method=='POST':
        form_data= UpdateProfileForm(request.POST, request.FILES, instance=profile_data)
        if form_data.is_valid():
            request.user.email= form_data.cleaned_data['email']
            request.user.save()
            profile= form_data.save(commit=False)
            profile.user= request.user
            profile.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile_page')
    context={
        'form_title': 'User Profile Update Page',
        'form_btn': 'Update',
        'title': 'Update Profile',
        'form_data': form_data,
    }
    return render(request, 'master/base_form.html', context)


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('login_view')

@login_required
def course_list(request):
    courses= CourseModel.objects.select_related('category', 'instructor')
    if not request.user.is_superuser:
        courses= courses.filter(approval_status='Approved')
    categories= CategoryModel.objects.all()
    search= request.GET.get('q', '')
    category_id= request.GET.get('category', '')
    if search:
        courses= courses.filter(Q(title__icontains=search) | Q(description__icontains=search))
    if category_id.isdigit():
        courses= courses.filter(category_id=category_id)
    context={
        'title': 'Courses',
        'courses': courses,
        'categories': categories,
        'search': search,
        'category_id': category_id,
    }
    return render(request, 'course_list.html', context)


@login_required
def course_detail(request, id):
    course= get_object_or_404(CourseModel, id=id)
    is_owner= course.instructor == request.user
    if course.approval_status != 'Approved' and not (is_owner or request.user.is_superuser):
        messages.error(request, 'This course is not available.')
        return redirect('course_list')
    is_enrolled= EnrollmentModel.objects.filter(student=request.user, course=course).exists()
    context={
        'title': course.title,
        'course': course,
        'lessons': course.lessons.all(),
        'is_owner': is_owner,
        'is_enrolled': is_enrolled,
        'can_view_lessons': is_owner or is_enrolled or request.user.is_superuser,
        'quizzes': course.quizzes.all()
    }
    return render(request, 'course_detail.html', context)


@login_required
@instructor_required
def my_courses(request):
    courses= CourseModel.objects.filter(instructor=request.user)
    context={
        'title': 'My Courses',
        'courses': courses,
    }
    return render(request, 'my_courses.html', context)


@login_required
@instructor_required
def add_course(request):
    form_data= CourseForm()
    if request.method=='POST':
        form_data= CourseForm(request.POST, request.FILES)
        if form_data.is_valid():
            form_data= form_data.save(commit=False)
            form_data.instructor= request.user
            form_data.save()
            messages.success(request, 'Course submitted. It will be visible after admin approval.')
            return redirect('my_courses')
    context={
        'form_title': 'Add Course',
        'form_btn': 'Add Course',
        'title': 'Add Course',
        'form_data': form_data,
    }
    return render(request, 'master/base_form.html', context)


@login_required
@instructor_required
def update_course(request, id):
    data= get_object_or_404(CourseModel, id=id, instructor=request.user)
    form_data= CourseForm(instance=data)
    if request.method=='POST':
        form_data= CourseForm(request.POST, request.FILES, instance=data)
        if form_data.is_valid():
            course= form_data.save(commit=False)
            if course.approval_status == 'Rejected':
                course.approval_status= 'Pending'
                messages.info(request, 'Your course was sent back for admin approval.')
            course.save()
            messages.success(request, 'Course updated successfully.')
            return redirect('my_courses')
    context={
        'form_title': 'Update Course',
        'form_btn': 'Update Course',
        'title': 'Update Course',
        'form_data': form_data,
    }
    return render(request, 'master/base_form.html', context)


@login_required
@instructor_required
def delete_course(request, id):
    data= get_object_or_404(CourseModel, id=id, instructor=request.user)
    if request.method=='POST':
        data.delete()
        messages.success(request, 'Course deleted successfully.')
        return redirect('my_courses')
    context={
        'title': 'Delete Course',
        'object_name': data.title,
        'cancel_url': 'my_courses',
    }
    return render(request, 'confirm_delete.html', context)

@login_required
@instructor_required
def add_lesson(request, course_id):
    course= get_object_or_404(CourseModel, id=course_id, instructor=request.user)
    form_data= LessonForm()
    if request.method=='POST':
        form_data= LessonForm(request.POST, request.FILES)
        if form_data.is_valid():
            form_data= form_data.save(commit=False)
            form_data.course= course
            form_data.save()
            messages.success(request, 'Lesson added successfully.')
            return redirect('course_detail', id=course.id)
    context={
        'form_title': f'Add Lesson to {course.title}',
        'form_btn': 'Add Lesson',
        'title': 'Add Lesson',
        'form_data': form_data,
    }
    return render(request, 'master/base_form.html', context)


@login_required
@instructor_required
def update_lesson(request, id):
    data= get_object_or_404(LessonModel, id=id, course__instructor=request.user)
    form_data= LessonForm(instance=data)
    if request.method=='POST':
        form_data= LessonForm(request.POST, request.FILES, instance=data)
        if form_data.is_valid():
            form_data.save()
            messages.success(request, 'Lesson updated successfully.')
            return redirect('course_detail', id=data.course.id)
    context={
        'form_title': 'Update Lesson',
        'form_btn': 'Update Lesson',
        'title': 'Update Lesson',
        'form_data': form_data,
    }
    return render(request, 'master/base_form.html', context)


@login_required
@instructor_required
def delete_lesson(request, id):
    data= get_object_or_404(LessonModel, id=id, course__instructor=request.user)
    course_id= data.course.id
    if request.method=='POST':
        data.delete()
        messages.success(request, 'Lesson deleted successfully.')
        return redirect('course_detail', id=course_id)
    context={
        'title': 'Delete Lesson',
        'object_name': data.title,
        'cancel_url': 'course_detail',
        'cancel_id': course_id,
    }
    return render(request, 'confirm_delete.html', context)


@login_required
def lesson_detail(request, id):
    lesson= get_object_or_404(LessonModel, id=id)
    course= lesson.course
    is_owner= course.instructor == request.user
    is_enrolled= EnrollmentModel.objects.filter(student=request.user, course=course).exists()
    if not (is_owner or is_enrolled or request.user.is_superuser):
        messages.error(request, 'Please enroll in this course to view its lessons.')
        return redirect('course_detail', id=course.id)
    completed_ids= set(LessonProgressModel.objects.filter(
        student=request.user, lesson__course=course
    ).values_list('lesson_id', flat=True))
    context={
        'title': lesson.title,
        'lesson': lesson,
        'course': course,
        'lessons': course.lessons.all(),
        'completed_ids': completed_ids,
        'is_completed': lesson.id in completed_ids,
        'is_enrolled': is_enrolled,
    }
    return render(request, 'lesson_detail.html', context)


@login_required
@student_required
def enroll_course(request, id):
    course= get_object_or_404(CourseModel, id=id, approval_status='Approved')
    if request.method=='POST':
        enrollment, created= EnrollmentModel.objects.get_or_create(student=request.user, course=course)
        if created:
            messages.success(request, f'You are now enrolled in {course.title}.')
        else:
            messages.info(request, 'You are already enrolled in this course.')
    return redirect('course_detail', id=course.id)


@login_required
@student_required
def complete_lesson(request, id):
    lesson= get_object_or_404(LessonModel, id=id)
    if not EnrollmentModel.objects.filter(student=request.user, course=lesson.course).exists():
        messages.error(request, 'Please enroll in this course first.')
        return redirect('course_detail', id=lesson.course.id)
    if request.method=='POST':
        LessonProgressModel.objects.get_or_create(student=request.user, lesson=lesson)
        messages.success(request, 'Lesson marked as completed.')
    return redirect('lesson_detail', id=lesson.id)


@login_required
@student_required
def my_enrollments(request):
    enrollments= EnrollmentModel.objects.filter(student=request.user).select_related('course')
    context={
        'title': 'My Learning',
        'enrollments': enrollments,
    }
    return render(request, 'my_enrollments.html', context)

@login_required
@instructor_required
def add_quiz(request, course_id):
    course= get_object_or_404(CourseModel, id=course_id, instructor=request.user)
    form_data= QuizForm()
    if request.method=='POST':
        form_data= QuizForm(request.POST)
        if form_data.is_valid():
            form_data= form_data.save(commit=False)
            form_data.course= course
            form_data.save()
            messages.success(request, 'Quiz created. Now add some questions.')
            return redirect('manage_quiz', id=form_data.id)
    context={
        'form_title': f'Add Quiz to {course.title}',
        'form_btn': 'Add Quiz',
        'title': 'Add Quiz',
        'form_data': form_data,
    }
    return render(request, 'master/base_form.html', context)


@login_required
@instructor_required
def manage_quiz(request, id):
    quiz= get_object_or_404(QuizModel, id=id, course__instructor=request.user)
    context={
        'title': 'Manage Quiz',
        'quiz': quiz,
        'questions': quiz.questions.prefetch_related('choices'),
    }
    return render(request, 'manage_quiz.html', context)


@login_required
@instructor_required
def delete_quiz(request, id):
    quiz= get_object_or_404(QuizModel, id=id, course__instructor=request.user)
    course_id= quiz.course.id
    if request.method=='POST':
        quiz.delete()
        messages.success(request, 'Quiz deleted successfully.')
        return redirect('course_detail', id=course_id)
    context={
        'title': 'Delete Quiz',
        'object_name': quiz.title,
        'cancel_url': 'manage_quiz',
        'cancel_id': quiz.id,
    }
    return render(request, 'confirm_delete.html', context)


@login_required
@instructor_required
def add_question(request, quiz_id):
    quiz= get_object_or_404(QuizModel, id=quiz_id, course__instructor=request.user)
    form_data= QuestionForm()
    if request.method=='POST':
        form_data= QuestionForm(request.POST)
        if form_data.is_valid():
            cd= form_data.cleaned_data
            with transaction.atomic():
                question= QuestionModel.objects.create(quiz=quiz, text=cd['text'])
                for number in ['1', '2', '3', '4']:
                    choice_text= cd.get(f'choice_{number}')
                    if choice_text:
                        ChoiceModel.objects.create(
                            question=question,
                            text=choice_text,
                            is_correct=(cd['correct'] == number),
                        )
            messages.success(request, 'Question added successfully.')
            return redirect('manage_quiz', id=quiz.id)
    context={
        'form_title': f'Add Question to {quiz.title}',
        'form_btn': 'Add Question',
        'title': 'Add Question',
        'form_data': form_data,
    }
    return render(request, 'master/base_form.html', context)


@login_required
@instructor_required
def delete_question(request, id):
    question= get_object_or_404(QuestionModel, id=id, quiz__course__instructor=request.user)
    quiz_id= question.quiz.id
    if request.method=='POST':
        question.delete()
        messages.success(request, 'Question deleted successfully.')
        return redirect('manage_quiz', id=quiz_id)
    context={
        'title': 'Delete Question',
        'object_name': question.text,
        'cancel_url': 'manage_quiz',
        'cancel_id': quiz_id,
    }
    return render(request, 'confirm_delete.html', context)


@login_required
@student_required
def take_quiz(request, id):
    quiz= get_object_or_404(QuizModel, id=id)
    if not EnrollmentModel.objects.filter(student=request.user, course=quiz.course).exists():
        messages.error(request, 'Please enroll in this course to take its quiz.')
        return redirect('course_detail', id=quiz.course.id)
    questions= quiz.questions.prefetch_related('choices')
    if not questions.exists():
        messages.warning(request, 'This quiz has no questions yet.')
        return redirect('course_detail', id=quiz.course.id)
    if request.method=='POST':
        score= 0
        for question in questions:
            choice_id= request.POST.get(f'question_{question.id}')
            if choice_id and choice_id.isdigit():
                if ChoiceModel.objects.filter(id=choice_id, question=question, is_correct=True).exists():
                    score += 1
        attempt= QuizAttemptModel(student=request.user, quiz=quiz, score=score, total=questions.count())
        attempt.save()
        return redirect('quiz_result', id=attempt.id)
    context={
        'title': quiz.title,
        'quiz': quiz,
        'questions': questions,
        'attempts': QuizAttemptModel.objects.filter(student=request.user, quiz=quiz),
    }
    return render(request, 'take_quiz.html', context)


@login_required
@student_required
def quiz_result(request, id):
    attempt= get_object_or_404(QuizAttemptModel, id=id, student=request.user)
    context={
        'title': 'Quiz Result',
        'attempt': attempt,
    }
    return render(request, 'quiz_result.html', context)

@login_required
@admin_required
def approve_course(request, id):
    course= get_object_or_404(CourseModel, id=id)
    if request.method=='POST':
        course.approval_status= 'Approved'
        course.save()
        messages.success(request, f'{course.title} has been approved.')
    return redirect('dashboard_view')


@login_required
@admin_required
def reject_course(request, id):
    course= get_object_or_404(CourseModel, id=id)
    if request.method=='POST':
        course.approval_status= 'Rejected'
        course.save()
        messages.warning(request, f'{course.title} has been rejected.')
    return redirect('dashboard_view')

@login_required
@admin_required
def student_list(request):
    students= User.objects.filter(user_profile__role='Student', is_superuser=False).select_related('user_profile').annotate(course_count=Count('student_enrollments'))
    search= request.GET.get('q', '')
    if search:
        students= students.filter(
            Q(username__icontains=search) | Q(email__icontains=search) | Q(user_profile__name__icontains=search)
        )
    context={
        'title': 'Students',
        'students': students,
        'search': search,
    }
    return render(request, 'student_list.html', context)

@login_required
@admin_required
def instructor_list(request):
    instructors= User.objects.filter(user_profile__role='Instructor', is_superuser=False).select_related('user_profile').annotate(course_count=Count('instructor_courses'))
    search= request.GET.get('q', '')
    if search:
        instructors= instructors.filter(
            Q(username__icontains=search) | Q(email__icontains=search) | Q(user_profile__name__icontains=search)
        )
    context={
        'title': 'Instructors',
        'instructors': instructors,
        'search': search,
    }
    return render(request, 'instructor_list.html', context)