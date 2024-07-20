

from rest_framework import serializers
from apps.calendar_app.models import CalendarEntry

class CalendarEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEntry
        fields = '__all__'


class CalendarEntryPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEntry
        fields = '__all__'
        read_only_fields = ['user']


from django.db import models


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