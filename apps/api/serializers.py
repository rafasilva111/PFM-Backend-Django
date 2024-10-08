from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from apps.api.functions import build_paginated_url

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

        access_token_expires = timezone.now() + settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
        refresh_token_expires = timezone.now() + settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']

        return cls({
            'refresh_token': str(refresh_token),
            'refresh_token_expires': refresh_token_expires.isoformat() + 'Z',
            'access_token': str(access),
            'access_token_expires': access_token_expires.isoformat() + 'Z',
            
        })
    @classmethod
    def from_refresh_token(cls, refresh_token_):
        

    
        try:
            refresh_token = RefreshToken(refresh_token_)
        except TokenError as e:
            raise serializers.ValidationError({'refresh': str(e)})
        
        access = refresh_token.access_token

        access_token_expires = timezone.now() + settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
        refresh_token_expires = timezone.now() + settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']

        return cls({
            'refresh_token': str(refresh_token),
            'refresh_token_expires': refresh_token_expires.isoformat() + 'Z',
            'access_token': str(access),
            'access_token_expires': access_token_expires.isoformat() + 'Z',
            
        })
    

class ErrorResponseSerializer(serializers.Serializer):
    errors = serializers.DictField()
    @classmethod
    def from_serializer_errors(cls, serializer):
        return cls({
            'errors': serializer.errors,  
        })
    
    @classmethod
    def from_dict(cls, dict):
        return cls({
            'errors': dict,  
        })
        
    @classmethod
    def from_params(cls, type, message):
        return cls({
            'errors': {type:[message]},  
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
    refresh = serializers.CharField(
        max_length=255,
        required=True,
        error_messages={
            'required': 'Please provide your refresh token address.',
            'blank': 'Please provide your refresh token address.',
            'invalid': 'Please provide your refresh token address.',
            'max_length': 'The refresh token is too long.'
        }
    )

class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        max_length=255,
        required=True,
        error_messages={
            'required': 'Please provide your refresh token.',
            'blank': 'Please provide your refresh token.',
            'invalid': 'Please enter a valid refresh token.',
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
    
class PaginationMetadataSerializer(serializers.Serializer):

    current_page = serializers.IntegerField()
    items_per_page = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    total_items = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)

    @staticmethod
    def build_metadata(page, page_size, total_pages, total_items, endpoint_name, **kwargs):
        metadata = {
            'current_page': page,
            'items_per_page': page_size,
            'total_pages': total_pages,
            'total_items': total_items,
            'next': None,
            'previous': None,
        }

        endpoint_url = reverse(endpoint_name)

        if page < total_pages:
            next_link = page + 1
            metadata['next'] = f"{endpoint_url}?page={next_link}&page_size={page_size}"
        if page > 1:
            previous_link = page - 1
            metadata['previous'] = f"{endpoint_url}?page={previous_link}&page_size={page_size}"
        
        metadata.update(kwargs)
        return metadata

class IdResponseSerializer(serializers.Serializer):

    id = serializers.IntegerField()
    
    @classmethod
    def build_(cls, id):

        
        return cls({
            'id': id,
            })

class IdListInputSerializer(serializers.Serializer):

    ids = serializers.ListField(child=serializers.IntegerField())



from rest_framework import serializers
from rest_framework.reverse import reverse

class ListResponseSerializer(serializers.Serializer):
    _metadata = serializers.DictField(
        child=serializers.JSONField(),
        help_text="Pagination metadata including page, page_size, total_pages, total_items, next_page, and previous_page."
    )
    result = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of results from the specified serializer."
    )

    @classmethod
    def build_(cls, request, page, paginator, serializer, endpoint_name):
        """
        Build the response data including metadata and result.

        :param request: DRF request object.
        :param page: Current page number.
        :param paginator: Paginator instance.
        :param serializer: Serializer instance for result data.
        :param endpoint_name: Name of the endpoint for metadata purposes.
        :return: A ListResponseSerializer instance with populated data.
        """

        total_items = paginator.count
        total_pages = paginator.num_pages
        page_size = paginator.per_page

        current_page = request.build_absolute_uri(reverse(endpoint_name) + f'?page={page}&page_size={page_size}')
        
        next_page = None
        if page < total_pages:
            next_page = request.build_absolute_uri(reverse(endpoint_name) + f'?page={page + 1}')

        previous_page = None
        if page > 1:
            previous_page = request.build_absolute_uri(reverse(endpoint_name) + f'?page={page - 1}')

        metadata = {
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "total_items": total_items,
            "current_page": current_page,
            "next_page": next_page,
            "previous_page": previous_page
        }

        result = serializer.data

        response_data = {
            "_metadata": metadata,
            "result": result
        }

        return cls(response_data)

    
    # Use this one
    @classmethod
    def build__(cls, request, page, paginator, serializer):
        """
        Build the response data including metadata and result.

        :param request: DRF request object.
        :param page: Current page number.
        :param paginator: Paginator instance.
        :param serializer: Serializer instance for result data.
        :return: A ListResponseSerializer instance with populated data.
        """

        total_items = paginator.count
        total_pages = paginator.num_pages
        page_size = paginator.per_page
        
        current_page = request.get_full_path()
        
        next_page = build_paginated_url(request, page + 1) if page < total_pages else None
        previous_page = build_paginated_url(request, page - 1) if page > 1 else None

        metadata = {
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "total_items": total_items,
            "current_page": current_page,
            "next_page": next_page,
            "previous_page": previous_page
        }

        result = serializer.data

        response_data = {
            "_metadata": metadata,
            "result": result
        }

        return cls(response_data)