from functools import wraps
from django.http import HttpResponse

def permission_required(perm):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.has_perm(perm):
                return HttpResponse("Unauthorized", status=403)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator