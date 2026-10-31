from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist


def role_required(role):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login_view')
            if request.user.is_superuser:
                messages.error(request, f'Only {role.lower()}s can access that page.')
                return redirect('dashboard_view')
            try:
                user_role= request.user.user_profile.role
            except ObjectDoesNotExist:
                messages.warning(request, 'Please update your profile first.')
                return redirect('profile_update_view')
            if user_role != role:
                messages.error(request, f'Only {role.lower()}s can access that page.')
                return redirect('dashboard_view')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


student_required= role_required('Student')
instructor_required= role_required('Instructor')


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_view')
        if not request.user.is_superuser:
            messages.error(request, 'Only admin can access that page.')
            return redirect('dashboard_view')
        return view_func(request, *args, **kwargs)
    return wrapper