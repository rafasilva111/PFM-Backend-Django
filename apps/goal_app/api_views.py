###
#       Default imports
##


##
#   Default
#

from django.utils import timezone
from django.contrib.auth import login, logout, authenticate
from django.conf import settings
from django.db.models import Case, When, Value, BooleanField,Q

##
#   Django Rest Framework
#

from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView


##
#   Api Swagger
#

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema



##
#   Extras
#

from django.core.paginator import Paginator




###
#       App specific imports
##


##
#   Models
#

from apps.goal_app.models import Goal
from apps.goal_app.serializers import GoalSerializer,IdealWeightSerializer
from apps.goal_app.functions import calculate_bmi


##
#   Serializers
#

from apps.goal_app.serializers import GoalSerializer, IdealWeightSerializer
from apps.api.serializers import ErrorResponseSerializer,ListResponseSerializer,IdResponseSerializer


##
#   Functions
#


##
#   Contants
#


from apps.api.constants import ERROR_TYPES,RESPONSE_CODES




###
#
#   User App
#
##

###
#   Auth
##



###
#   Goals
##

class IdealWeightView(APIView):
    
    permission_classes = [IsAuthenticated]
    def get(self,request):
        # Standart BMI 
        
        # Get user authed
        user = request.user
        
        # Validate args
        if user.weight == -1 or user.height == -1:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.LOGICAL.value,message="User does not have setted weight neither height...").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate BMI
        
        bmi, ideial_weigh_lower_limit,ideial_weigh_upper_limit  = calculate_bmi(user.weight,user.height)
        

        return Response(IdealWeightSerializer.from_params(ideial_weigh_lower_limit,ideial_weigh_upper_limit,bmi).data,status=status.HTTP_200_OK)
        
        
       
class GoalsView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self,request):
        
        # Get user authed
        user = request.user

        # Get user goal
        
        try:
            goal = user.goals.get(deleted_at = None)
            
        except Goal.DoesNotExist:
            
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.MISSING_MODEL.value,message="User does't have a goal.").data,status=status.HTTP_400_BAD_REQUEST)
            # if user hasnt ever create a goal this would trow and exception

        
        return Response(GoalSerializer(goal).data, status=status.HTTP_200_OK)
    
    def post(self,request):
        
        # Get user authed
        user = request.user
        
        # Validate serializer
        serializer = GoalSerializer(data=request.data, context={'user': user})
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)

        serializer.user = user
        
        # Soft delete previous goal (user can only have one current goal)

        try:
            previous_goal = user.goals.get(deleted_at = None)
            previous_goal.delete()
        except Goal.DoesNotExist:
            # if user hasnt ever create a goal this would trow and exception
            pass
        
    
        # save goal
        serializer.save()

        return Response(status=status.HTTP_201_CREATED)
        
        
    def delete(self,request):
        
        # Get user auth id
        user = request.user
        
        
        # Get user goal
        
        try:
            goal = user.goals.get(deleted_at = None)
            
        except Goal.DoesNotExist:
            
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.MISSING_MODEL.value,message="User does not have a goal to delete.").data,status=status.HTTP_400_BAD_REQUEST)
            # if user hasnt ever create a goal this would trow and exception
            pass
        
        # delete        
        goal.delete()
        
        
        return Response(status=status.HTTP_200_OK)
   