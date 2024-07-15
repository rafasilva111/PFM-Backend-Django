from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from datetime import datetime
from pytz import timezone, utc
from .models import Notification
from apps.user_app.serializers import SimpleUserSerializer
from apps.recipe_app.serializers import SimpleRecipeSerializer, CommentSerializer

class NotificationSerializer(serializers.ModelSerializer):
    
    from_user = SimpleUserSerializer(required = False)
    recipe = SimpleRecipeSerializer(required = False)
    comment = CommentSerializer(required = False)
    
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['id','to_user','from_user','recipe','comment','type','created_at','updated_at']
        
    def create(self, validated_data):
        
        # Create the Recipe instance
        instance = Notification.objects.create(
            to_user = self.context['to_user'],
            from_user = self.context['from_user'],
            **validated_data
            )

        return instance

class NotificationPatchSerializer(NotificationSerializer):
    
    class Meta:
        model = Notification
        fields = '__all__'
        
        extra_kwargs = {
            'title': {'required': False},
            'message': {'required': False},
            'seen': {'required': False}
        }