from django.shortcuts import render

# Create your views here.
import json
from django.contrib.auth import authenticate, login
from django.db.models import Q
from django.core.paginator import Paginator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from datetime import datetime,timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.views import TokenRefreshView
from apps.api.serializers import TokenSerializer,ErrorResponseSerializer,LoginSerializer,ResetSerializer,LogoutSerializer,SuccessResponseSerializer,PaginationMetadataSerializer,ListResponseSerializer
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from apps.api.constants import ERROR_TYPES,RESPONSE_CODES

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi



class CustomPagination(PageNumberPagination):
    page_size = 5  # Default page size
    page_size_query_param = 'page_size'
    max_page_size = 100  # Maximum page size

###
#
#   User App
#
##

import logging

logger = logging.getLogger('api')



