from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


class TokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()
    refresh_token_expires = serializers.DateTimeField()
    access_token = serializers.CharField()
    access_token_expires = serializers.DateTimeField()


    @classmethod
    def for_user(cls, user):
        refresh_token = RefreshToken.for_user(user)
        access = refresh_token.access_token

        access_token_expires = datetime.now() + settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
        refresh_token_expires = datetime.now() + settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']

        return cls({
            'refresh_token': str(refresh_token),
            'refresh_token_expires': access_token_expires.isoformat() + 'Z',
            'access_token': str(access),
            'access_token_expires': refresh_token_expires.isoformat() + 'Z',
            
        })

class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.DictField()
    @classmethod
    def from_serializer_errors(cls, serializer):
        return cls({
            'error': serializer.errors,  
        })
    
    @classmethod
    def from_dict(cls, dict):
        return cls({
            'error': dict,  
        })
        
    @classmethod
    def from_params(cls, type, message):
        return cls({
            'error': {type:message},  
        })
        
class SuccessResponseSerializer(serializers.Serializer):
    message = serializers.CharField(
        required=True,
        max_length=255,
    )
    
    @classmethod
    def from_string(cls, string):
        return cls({
            'message': string,  
        })

class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(
        max_length=255,
        required=True,
        error_messages={
            'required': 'Please provide your email address.',
            'blank': 'Please provide your email address.',
            'invalid': 'Please enter a valid email address.',
            'max_length': 'The email address is too long.'
        }
    )
    password = serializers.CharField(
        required=True,
        max_length=255,
        error_messages={
            'required': 'Please provide your password.',
            'blank': 'Please provide your password.',
            'max_length': 'The password is too long.'
        }
    )

class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(
        max_length=255,
        required=True,
        error_messages={
            'required': 'Please provide your refresh token address.',
            'blank': 'Please provide your refresh token address.',
            'invalid': 'Please provide your refresh token address.',
            'max_length': 'The refresh token is too long.'
        }
    )
    
class ResetSerializer(serializers.Serializer):
    email = serializers.CharField(
        max_length=255,
        required=True,
        error_messages={
            'required': 'Please provide your email address.',
            'blank': 'Please provide your email address.',
            'invalid': 'Please enter a valid email address.',
            'max_length': 'The email address is too long.'
        }
    )