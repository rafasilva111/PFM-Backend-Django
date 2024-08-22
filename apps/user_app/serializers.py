from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import datetime
from pytz import  timezone as pytz_timezone,utc
from .models import User,FollowRequest,Goal
from .constants import USER_MAX_WEIGHT,USER_MIN_WEIGHT,USER_MIN_HEIGHT,USER_MAX_HEIGHT,STRING_USER_BIRTHDATE_PAST_ERROR,STRING_USER_BIRTHDATE_YOUNG_ERROR
from django.conf import settings
class CustomDateFormatField(serializers.DateField):
    def to_internal_value(self, value):
        try:
            # Parse the input value using the custom format
            date_obj = datetime.strptime(value, '%d/%m/%Y')
            return date_obj
        except ValueError:
            raise serializers.ValidationError("Invalid date format. Please use the format 'DD/MM/YYYY'.")


class UserSerializer(serializers.ModelSerializer):
        
    class Meta:
        model = User
        fields = [
            'id', 'name', 'username', 'description', 'birth_date', 'img_source', 'email',
            'user_portion', 'created_at', 'fmc_token', 'activity_level', 'height', 'weight',
            'age', 'profile_type', 'user_type', 'sex','verified','password','follows_c','followers_c'
        ]
       
        
        read_only_fields = ['id', 'verified', 'user_type', 'age', 'created_date']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def get_age(self, obj):
        if obj.birth_date:
            today = timezone.now().date()
            age = today.year - obj.birth_date.year - ((today.month, today.day) < (obj.birth_date.month, obj.birth_date.day))
            return age
        else:
            return 0

    def validate_weight(self, value):
        if value and not USER_MAX_WEIGHT >= value >= USER_MIN_WEIGHT:
            raise serializers.ValidationError(f"User weight must be between {USER_MIN_WEIGHT} kg and {USER_MAX_WEIGHT} kg.")
        return value

    def validate_height(self, value):
        if value and not USER_MAX_HEIGHT >= value >= USER_MIN_HEIGHT:
            raise serializers.ValidationError(f"User height must be between {USER_MIN_HEIGHT} cm and {USER_MAX_HEIGHT} cm.")
        return value

    def validate_birth_date(self, value):
        
        # Define the Portugal timezone
        portugal_tz = pytz_timezone('Europe/Lisbon')
        
        # Convert the naive datetime to Portugal timezone if it's naive
        if value.tzinfo is None:
            value = portugal_tz.localize(value)
        
        # Convert to UTC for comparison
        value_utc = value.astimezone(utc)
        
        # Get the current time in UTC
        now_utc = timezone.now().astimezone(utc)    
        
        if value_utc > now_utc:
            raise serializers.ValidationError(STRING_USER_BIRTHDATE_PAST_ERROR)

        if not (now_utc - value).days // 365.25 >= 12:
            raise serializers.ValidationError(STRING_USER_BIRTHDATE_YOUNG_ERROR)

        return value

    def create(self, validated_data):
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
            
        return User.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('password', None)
        return super().update(instance, validated_data)
    
    

class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id','name','username','description','img_source','profile_type','user_type','follows_c','followers_c']

class UserProfileSerializer(serializers.ModelSerializer):
    
    recipes_created = serializers.SerializerMethodField()
     
    class Meta:
        model = User
        fields = ['id','name','username','description','img_source','profile_type','user_type','follows_c','followers_c','recipes_created']   
        
        
    def get_recipes_created(self, obj):

        return obj.created_recipes.count()    

class UserPatchSerializer(UserSerializer):
    old_password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = [
            'name', 'username', 'description', 'img_source','old_password','password' ,'age','birth_date',
            'user_portion', 'fmc_token', 'activity_level', 'height', 'weight', 'profile_type', 'user_type', 'sex'
        ]
        read_only_fields = ['age', 'birth_date']
    
    def validate(self, data):

        #                   incoming_fields - expected_fields
        unknown_keys = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown_keys:
            raise serializers.ValidationError(unknown_keys)
        
        if 'password' in self.initial_data and not 'old_password':
            raise serializers.ValidationError("Missing old_password, to update current password.")
        
        return data
    
    
class UserToFollowSerializer(serializers.Serializer):
    follower = serializers.BooleanField(default = False)
    request_sent = serializers.BooleanField(default = False)
    user = UserSimpleSerializer(required = True)
    
    def to_representation(self, instance):
        # Assume `instance` is the item object
        # Extract required fields
        print(instance)
        representation = super().to_representation({
            'user': instance,  
            'request_sent': instance.request_sent,
            'follower': instance.follower
        })
        return representation
    
class FollowRequestSerializer(UserSerializer):
    follower = UserSimpleSerializer(required= True)
    followed = UserSimpleSerializer(required = True)
    is_follow = serializers.BooleanField(default = False)
    request_sent = serializers.BooleanField(default = False)
    
    class Meta:
        model = FollowRequest
        fields = '__all__'
        
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