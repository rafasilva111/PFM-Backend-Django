from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import datetime
from pytz import  timezone as pytz_timezone,utc
from .models import User,FollowRequest,Goal
from apps.user_app.serializers import UserSerializer,UserSimpleSerializer
from .constants import USER_MAX_WEIGHT,USER_MIN_WEIGHT,USER_MIN_HEIGHT,USER_MAX_HEIGHT,STRING_USER_BIRTHDATE_PAST_ERROR,STRING_USER_BIRTHDATE_YOUNG_ERROR
from django.conf import settings

class GoalSerializer(UserSerializer):
    
    user = UserSimpleSerializer(required = False)
    
    class Meta:
        model = Goal
        fields = '__all__'
        read_only_fields = ['user']
    
    def create(self, validated_data):
        if 'user' in self.context:
            user = self.context['user']
            goal = Goal.objects.create(user=user, **validated_data)
            return goal
        
        goal = Goal.objects.create(**validated_data)
        return goal

class IdealWeightSerializer(serializers.Serializer):
    ideial_weigh_lower_limit = serializers.FloatField(required = True)
    ideial_weigh_upper_limit = serializers.FloatField(required = True)
    bmi = serializers.FloatField(required = True)
    
    
    @classmethod
    def from_params(cls, ideial_weigh_lower_limit, ideial_weigh_upper_limit,bmi):
        return cls({
            'ideial_weigh_lower_limit':ideial_weigh_lower_limit,
            'ideial_weigh_upper_limit':ideial_weigh_upper_limit,
            'bmi': bmi
        })