###
#       Default imports
##


##
#   Default
#
from datetime import datetime, timedelta
from django.utils import timezone

##
#   Django Rest Framework
#

from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response


##
#   Api Swagger
#
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from django.core.paginator import Paginator

##
#   Extras
#

import math
from collections import defaultdict



###
#       App specific imports
##


##
#   Models
#

from apps.calendar_app.models import CalendarEntry
from apps.recipe_app.models import Recipe, RecipeIngredientQuantity
from apps.user_app.models import User

##
#   Serializers
#

from apps.calendar_app.serializers import CalendarEntrySerializer,CalendarEntryPatchSerializer,CalendarEntryListUpdateSerializer
from apps.api.serializers import SuccessResponseSerializer,ErrorResponseSerializer,ListResponseSerializer
from apps.shopping_app.serializers import ShoppingListSerializer,ShoppingIngredientSerializer


##
#   Functions
#

from apps.api.functions import add_days,parse_date


##
#   Contants
#

from apps.api.constants import ERROR_TYPES,RESPONSE_CODES

###
#
#   Calendar App
#
##

###
#   Calendar
##

class CalendarListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CalendarEntrySerializer

    @swagger_auto_schema(
        tags=['Calendar'],
        operation_summary="List all calendar entries",
        operation_description="List all calendar entries for the authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                name='page',
                in_=openapi.IN_QUERY,
                description="The page number to retrieve. Defaults to 1.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                name='page_size',
                in_=openapi.IN_QUERY,
                description="The number of items per page. Defaults to 5.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                name='id',
                in_=openapi.IN_QUERY,
                description="Filter by calendar entry ID.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                name='date',
                in_=openapi.IN_QUERY,
                description="Filter by date in the format DD/MM/YYYYThh:mm:ss.",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                name='from_date',
                in_=openapi.IN_QUERY,
                description="Filter by date after this in the format DD/MM/YYYYThh:mm:ss.",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                name='to_date',
                in_=openapi.IN_QUERY,
                description="Filter by date before this in the format DD/MM/YYYYThh:mm:ss.",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                name='user_id',
                in_=openapi.IN_QUERY,
                description="Filter by user ID.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                name='recipe_id',
                in_=openapi.IN_QUERY,
                description="Filter by recipe ID.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description='A paginated list of calendar entries.',
                schema=ListResponseSerializer(many=True),
            ),
            400: openapi.Response(
                description='Bad request. The provided parameters are not valid, or other parameter issues.',
                schema=ErrorResponseSerializer,
            ),
        }
    )
    def get(self, request):
        """
        List all calendar entries.
        """
        # Get user auth 
        user = request.user

        # Get args
        page = request.GET.get('page', 1)
        page_size = request.GET.get('page_size', 5)
        date = parse_date(request.GET.get('date')) if 'date' in request.query_params else None
        from_date = parse_date(request.GET.get('from_date')) if 'from_date' in request.GET else None
        to_date = parse_date(request.GET.get('to_date')) if 'to_date' in request.GET else None
        recipe_id = request.GET.get('recipe_id', None)

        # Validate args
        if from_date and to_date and from_date > to_date:
            return Response(ErrorResponseSerializer.from_dict({"invalid":"from_date cannot be greater than to_date"}).data, status=status.HTTP_400_BAD_REQUEST)

        # Query building
        base_query = CalendarEntry.objects.filter(user=user)

        if date:
            next_day = add_days(date, 1)
            base_query = base_query.filter(realization_date__gte=date, realization_date__lt=next_day)

        elif from_date and to_date:
            base_query = base_query.filter(realization_date__gte=from_date, realization_date__lte=to_date).order_by('realization_date')

            response_holder = {}

            # Group entries by date
            date_to_entries = defaultdict(list)

            for item in base_query:
                date_string = item.realization_date.strftime("%d/%m/%Y")
                date_to_entries[date_string].append(CalendarEntrySerializer(item).data)

            # Create a date range and initialize result dictionary with empty arrays
            date_range = [from_date + timedelta(days=i) for i in range((to_date - from_date).days + 1)]
            response_holder["result"] = {date.strftime("%d/%m/%Y"): [] for date in date_range}

            # Fill the result dictionary with grouped entries
            for date_string, entries in date_to_entries.items():
                response_holder["result"][date_string] = entries

            return Response(data=response_holder, status=status.HTTP_200_OK)

        # Paginate the results
        paginator = Paginator(base_query, page_size)

        # Get the requested page
        try:
            records_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_dict({"exception":"Page does not exist."}).data, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ListResponseSerializer.build_(page, paginator, serializer=CalendarEntrySerializer(records_page, many=True), endpoint_name="calendar_list").data,
            status=status.HTTP_200_OK
        )

class CalendarView(APIView):
    
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Calendar'],
        operation_summary="Get a calendar entry by ID",
        operation_description="Get a calendar entry by ID for the authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_QUERY,
                description="The ID of the calendar entry to retrieve.",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description='The calendar entry data.',
                schema=CalendarEntrySerializer
            ),
            400: openapi.Response(
                description='Bad request. The provided ID is not valid or other parameter issues.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def get(self, request):
        """
        Get a calendar entry by ID.
        
        Args:
            id (int): Calendar entry ID.
        
        Returns:
            Response: Response containing the calendar entry data.
        
        Raises:
            CalendarEntry.DoesNotExist: If the calendar entry does not exist.
        """
        
        # Get args
        
        entry_id = request.query_params.get('id')
        
        # Validate args
          
        if not entry_id:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.ARGS,message= "Calendar Entry ID not provided.").data, status=status.HTTP_400_BAD_REQUEST)

        # Query building
        
        try:
            calendar_entry = CalendarEntry.objects.get(id=entry_id, user=request.user)
            
        except CalendarEntry.DoesNotExist:
           return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL,message="Calendar Entry couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)

        return Response(CalendarEntrySerializer(calendar_entry).data, status=status.HTTP_200_OK)
    
    

    
    @swagger_auto_schema(
        tags=['Calendar'],
        operation_summary="Create a new calendar entry.",
        operation_description="Create a new calendar entry with the provided data.",
        request_body=CalendarEntryPatchSerializer,
        responses={
            201: openapi.Response(
                description='Successfully created a new calendar entry.',
                schema=CalendarEntrySerializer
            ),
            400: openapi.Response(
                description='Bad request. Invalid data provided.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def post(self, request):
        """
        Create a new calendar entry.
        
        Args:
            request (Request): The HTTP request object.
        
        Returns:
            JsonResponse: The response containing the calendar entry data.
        
        Raises:
            ValidationError: If the data is invalid.
        """
        
        # Serialize       
        serializer = CalendarEntryPatchSerializer(data=request.data)
        
        # Validate Serializer
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)
            
            
        # Update instance  
        calendar_entry = serializer.save(user=request.user)
        
        return Response(CalendarEntrySerializer(calendar_entry).data, status=status.HTTP_201_CREATED)

            

    @swagger_auto_schema(
        tags=['Calendar'],
        operation_summary="Update a calendar entry by ID",
        operation_description="Update a calendar entry by ID for the authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_QUERY,
                description="The ID of the calendar entry to update.",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        request_body=CalendarEntryPatchSerializer,
        responses={
            200: openapi.Response(
                description='The updated calendar entry data.',
                schema=CalendarEntrySerializer
            ),
            400: openapi.Response(
                description='Bad request. The provided ID is not valid, or other parameter issues.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def patch(self, request):
        """
        Update a calendar entry by ID.
        """
        
        # Get query parameters
        entry_id = request.query_params.get('id')
        
        # Validate args
        if not entry_id:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.ARGS,message= "Calendar Entry ID not provided.").data, status=status.HTTP_400_BAD_REQUEST)

        
        # Serialize    
        serializer = CalendarEntryPatchSerializer(data=request.data, partial=True)
        
        # Validate Serializer
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)

        
        # Get Instance
        try:
            calendar_entry = CalendarEntry.objects.get(id=entry_id, user=request.user)
        except CalendarEntry.DoesNotExist:
            return Response({"error": "Calendar entry does not exist."}, status=status.HTTP_400_BAD_REQUEST)

        # Update instance
        try:

            for key, value in serializer.validated_data.items():
                setattr(calendar_entry, key, value)

            calendar_entry.save()
            
        except Exception as e:
            return Response(ErrorResponseSerializer.from_dict({"exception":f"Error updating user: {e}"}).data, status=status.HTTP_400_BAD_REQUEST)
        

        return Response(CalendarEntrySerializer(calendar_entry).data, status=status.HTTP_200_OK)
    @swagger_auto_schema(
        tags=['Calendar'],
        operation_summary="Delete a calendar entry by ID",
        operation_description="Delete a calendar entry by ID for the authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_QUERY,
                description="The ID of the calendar entry to delete.",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description='The calendar entry has been deleted.'
            ),
            400: openapi.Response(
                description='Bad request. The provided ID is not valid, or other parameter issues.',
                schema=ErrorResponseSerializer
            ),
            404: openapi.Response(
                description='Calendar entry not found.'
            ),
        }
    )
    def delete(self, request):
        """
        Delete a calendar entry by ID.
        """

        # Get query parameters
        entry_id = request.query_params.get('id')
        
        # Validate args
        if not entry_id:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.ARGS,message= "Calendar Entry ID not provided.").data, status=status.HTTP_400_BAD_REQUEST)

        # Get Instance  
        try:
            calendar_entry = CalendarEntry.objects.get(id=entry_id, user=request.user)
            calendar_entry.delete()
        except CalendarEntry.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL,message= ERROR_TYPES.MISSING_MODEL.data).data, status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_200_OK)


class CalendarEntryListCheckView(APIView):
    
    @swagger_auto_schema(
        tags=['Calendar'],
        operation_summary="Check a list of calendar entries by ID",
        operation_description="Check a list of calendar entries by ID for the authenticated user.",
        request_body=CalendarEntryListUpdateSerializer,
        responses={
            200: openapi.Response(
                description='The updated calendar entry data.',
            ),
            400: openapi.Response(
                description='Bad request. The provided ID is not valid, or other parameter issues.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def patch(self, request):
        """
        Check a list of calendar entries by ID for the authenticated user.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            Response: The HTTP response object.
        """
        # Get query parameters
        user = request.user

        # Validate args
        serializer = CalendarEntryListUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)

        CalendarEntry.objects.filter(id__in=serializer.validated_data['checked_done'], user=user).update(checked_done=True)
        CalendarEntry.objects.filter(id__in=serializer.validated_data['checked_removed'], user=user).update(checked_done=False)

        return Response(status=status.HTTP_200_OK)



###
#   Calendar Ingredients
##
   
class CalendarIngredientsListView(APIView):
    permission_classes = [IsAuthenticated]

    # Swagger Decorator
    @swagger_auto_schema(
        tags=['Calendar'],
        operation_summary="List all ingredients in calendar entries within a date range.",
        operation_description="List all ingredients in calendar entries within a date range for the authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                'from_date',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="The start date of the date range. (DD/MM/YYYYThh:mm:ss)"
            ),
            openapi.Parameter(
                'to_date',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="The end date of the date range. (DD/MM/YYYYThh:mm:ss)"
            ),
        ],
        responses={
            400: openapi.Response(
                description='Bad request. From date and to date cannot be null, from date cannot be after to date, or user cannot have default portion to access this.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def get(self, request):
        """
        List all ingredients in calendar entries within a date range.
        """
        
        # Get user auth
        user = request.user
        
        # Get query parameters
        from_date = parse_date(request.query_params.get('from_date'))
        to_date = parse_date(request.query_params.get('to_date'))

        # Validate args
        if not from_date or not to_date:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.ARGS,message= "Missing arguments.").data, status=status.HTTP_400_BAD_REQUEST)
        if from_date > to_date:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.ARGS,message= "From date cannot be after to date.").data, status=status.HTTP_400_BAD_REQUEST)

        # Validate user portion
        if user.user_portion == -1:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING,message= "User cannot have default portion to access this.").data, status=status.HTTP_400_BAD_REQUEST)

        # Get ingredients
        response_holder = {}
        from django.db.models import Q

        # Filter RecipeIngredientQuantity based on CalendarEntry's user and realization_date range
        # Assuming user_logged_id is an integer and from_date, to_date are datetime objects
        query = (RecipeIngredientQuantity.objects
                .filter(
                    recipe__calendar_entries__user=user,
                    recipe__calendar_entries__realization_date__range=(from_date, to_date)
                )
                .distinct())

        # Get total ingredients 

        total_ingredients = {}

        ## TODO recheck this
        for item in query:
            ratio = 1
            if item.recipe.portion and 'pessoas' in item.recipe.portion:
                portion = int(item.recipe.portion.split(" ")[0])
                if user.user_portion >= 1:
                    ratio = user.user_portion / portion

            ingredient_name = item.ingredient.name
            if ingredient_name in total_ingredients:
                total_ingredients[ingredient_name]["quantity"] += float(item.quantity_normalized) * ratio
                if item.extra_quantity:
                    total_ingredients[ingredient_name]["extra_quantity"] += float(item.extra_quantity) * ratio
            else:
                total_ingredients[ingredient_name] = ShoppingIngredientSerializer({
                    "ingredient": item.ingredient,
                    "quantity": math.ceil(float(item.quantity_normalized) * ratio),
                    "extra_quantity": math.ceil(float(item.extra_quantity) * ratio) if item.extra_quantity else None,
                    "units": item.units_normalized,
                    "extra_units": item.extra_units,
                }).data

        response_holder["result"] = list(total_ingredients.values())

        return Response(response_holder, status=status.HTTP_200_OK)
