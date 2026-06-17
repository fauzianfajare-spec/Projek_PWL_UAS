from functools import wraps
from django.shortcuts import redirect

def firebase_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Mengecek apakah UID dari Firebase terdaftar di session browser
        if 'firebase_user_uid' not in request.session:
            return redirect('users:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view