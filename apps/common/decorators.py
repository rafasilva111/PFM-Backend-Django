from rest_framework.response import Response
from functools import wraps
from datetime import datetime
from apps.common.apps import firebase
from rest_framework import status


from firebase_admin import auth

def firebase_session_required(func):
    @wraps(func)
    def _wrapped_view(self,request, *args, **kwargs):
    
        try:
            teste = request.headers.get('Authorization', '').split('Bearer ')[-1].strip()
            decoded_token = auth.verify_id_token(request.headers.get('Authorization', '').split('Bearer ')[-1].strip())
           
            request.user_id = decoded_token
        except auth.ExpiredIdTokenError as e:
            return Response({'error': 'Expired token'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)

        return func(self,request, *args, **kwargs)

    return _wrapped_view