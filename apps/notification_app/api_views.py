
from django.core.paginator import Paginator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.api.serializers import ErrorResponseSerializer
from django.core.paginator import Paginator
from apps.api.constants import ERROR_TYPES
from rest_framework.permissions import IsAuthenticated


from .models import Notification
from .serializers import NotificationSerializer,NotificationPatchSerializer
from ..user_app.models import User
from ..api.serializers import PaginationMetadataSerializer,IdListInputSerializer

###
#   Notifications
##


class NotificationView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    
    def get(self,request):
        
        # TODO not really needed yet

        return Response(status=status.HTTP_204_NO_CONTENT)    

    def patch(self,request):
        
        # Get user authed
        user = request.user
        
        # Get args
        id = int(request.GET.get('id', -1))
        
        # Validate args
        if id == -1:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Recipe Report Id not supplied.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Retrieve the instance
        try:
            instance = Notification.objects.get(id=id, user = user)
        except Notification.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.MISSING_MODEL.value,message="Recipe Report can't be found by this id.").data, status=status.HTTP_400_BAD_REQUEST)
        
        
        # Deserialize the incoming data
        
        serializer = NotificationPatchSerializer(instance, data=request.data)
        
        # Validate and update the instance
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)
        
        
        serializer.save()
        return Response(serializer.data,status=status.HTTP_200_OK)

    
    def delete(self,request):
        """
        Deletes a notification instance for the authenticated user.

        Parameters:
            request (HttpRequest): The HTTP request object.

        Returns:
            Response: The HTTP response object. If the 'id' parameter is missing, a 400 Bad Request response with an error message is returned. If the notification instance is not found, a 400 Bad Request response with an error message is returned. Otherwise, a 200 OK response is returned.
        """
        
        # Get user authed
        user = request.user
        
        # Get args
        id = request.GET.get('id')

        # Validate args
        if not id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing param Id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Get Instance
        try:
            instance = Notification.objects.get(id=id,to_user = user)
        except Notification.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe Report couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        
        instance.delete()

        return Response(status=status.HTTP_200_OK)

class NotificationListView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self,request):
        """
        Retrieves a paginated list of notifications for the authenticated user.

        Parameters:
            request (Request): The HTTP request object.

        Returns:
            Response: The HTTP response object containing the paginated list of notifications.
                The response data has the following structure:
                {
                    "_metadata": {
                        "page": int,
                        "page_size": int,
                        "total_pages": int,
                        "total_items": int,
                        "name": str
                    },
                    "result": [
                        {
                            "id": int,
                            "message": str,
                            "created_at": datetime,
                            "updated_at": datetime
                        },
                        ...
                    ]
                }
        """
        
        # Get user auth id
        user = request.user

        # Get args
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 5))
        


        # Query building
        query = Notification.objects.filter ( to_user = user).order_by("-created_at")

        # Paginate the results
        paginator = Paginator(query, page_size)
        total_items = paginator.count
        total_pages = paginator.num_pages

        try:
            recipes_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_dict({ERROR_TYPES.PAGINATION.value:"Page does not exist."}).data, status=status.HTTP_400_BAD_REQUEST)
        
        # Build metadata
        metadata = PaginationMetadataSerializer.build_metadata(page, page_size, total_pages, total_items, "notification_list")
        
        # Serialize the data
        serializer = NotificationSerializer(recipes_page, many=True)
            
        # Build response data
        response_data = {
            "_metadata": metadata,
            "result": serializer.data
        }
        

        return Response(response_data, status=200)

    
    def patch(self,request):
        
        # Get user authed
        user = request.user
        
        # Get args
        id = int(request.GET.get('id', -1))
        
        # Validate args
        if id == -1:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Recipe Report Id not supplied.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Validate serializer
        serializer = IdListInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)
        
        # Get Instance
        try:
            instance = Notification.objects.filter(to_user = user, id__in = serializer.data['ids']) 
        except Notification.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe Report couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        
        instance.update(seen=True)
        
        return Response(serializer.data,status=status.HTTP_200_OK)

    
    def delete(self,request):
        
        # Get user authed
        user = request.user
        
        # Get args
        id = request.GET.get('id')

        # Validate args
        if not id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing param Id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Validate serializer
        serializer = IdListInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)
        
        # Get Instance
        try:
            instance = Notification.objects.filter(to_user = user, id__in = serializer.data['ids']) 
        except Notification.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe Report couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        
        instance.delete()

        return Response(status=status.HTTP_200_OK)