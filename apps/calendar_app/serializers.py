

from rest_framework import serializers
from apps.calendar_app.models import CalendarEntry
from apps.recipe_app.serializers import RecipeSerializer

class CalendarEntrySerializer(serializers.ModelSerializer):
    
    recipe = RecipeSerializer()
    class Meta:
        model = CalendarEntry
        fields = '__all__'
        



class CalendarEntryPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEntry
        fields = '__all__'
        read_only_fields = ['id','user']
        
        

    def update(self, instance, validated_data):
        
        # Extract nested data
        user = self.context.pop('user', None)
        
        # Update the main instance
        instance = super().update(instance, validated_data)
        
        # Validate context instances       
        if not user:
            raise serializers.ValidationError("User in context is required.")
        
        if self.instance.user.id != user.id:
            raise serializers.ValidationError("You do not own this Calendar entry.")

                
        return instance




class CalendarEntryListUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating multiple calendar entries at once.
    """
    checked_done = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,  # Makes this field optional
        allow_empty=True,  # Allows the list to be empty
        default = []
    )
    
    checked_removed= serializers.ListField(
        child=serializers.IntegerField(),
        required=False,  # Makes this field optional
        allow_empty=True,  # Allows the list to be empty
        default = []
    )