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

from apps.user_app.models import User, FollowRequest,Follow


##
#   Serializers
#

from apps.user_app.serializers import UserSerializer,UserSimpleSerializer,UserPatchSerializer,UserToFollowSerializer,UserProfileSerializer,FollowRequestSerializer
from apps.api.serializers import LoginSerializer,LogoutSerializer,TokenSerializer,SuccessResponseSerializer,ErrorResponseSerializer,ListResponseSerializer,IdResponseSerializer


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

class LoginView(APIView):
    """
    View for user login authentication.

    - Accepts POST requests with email and password.
    - Returns a token for successful authentication.
    """


    @swagger_auto_schema(
        tags=['Auth'], 
        operation_id="login", 
        request_body=LoginSerializer,
        responses={
            200: TokenSerializer,
            400: ErrorResponseSerializer,
            401: ErrorResponseSerializer,
        }
    )
    def post(self, request):
        """
        Handle POST request for user login.

        Args:
            request: HTTP request object containing user login data.

        Returns:
            Response: HTTP response with token data or error message.
        """
        
        # Validate serializer
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)
        
        # Authenticate user
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        user = authenticate(request, username=email, password=password)
        
        if not user:
            return Response(ErrorResponseSerializer.from_dict({'auth': ['Invalid email or password']}).data, status=status.HTTP_401_UNAUTHORIZED)
        
        # Generate token and expiration time
        return Response(TokenSerializer.for_user(user).data, status=status.HTTP_200_OK)


class AuthView(APIView):
    """
    View for user authentication and registration.

    - GET: Returns user data if authenticated.
    - POST: Registers a new user.
    """
    
    def get_permissions(self):
        """
        Define permissions based on HTTP method.

        Returns:
            list: List of permissions for the request.
        """
        if self.request.method in ['GET', 'DELETE']:
            return [IsAuthenticated()]
        return []

    @swagger_auto_schema(
        tags=['Auth'],      
        operation_id="session",     
        responses={
            200: UserSerializer,
            401: ErrorResponseSerializer,
        }
    )
    def get(self, request):
        """
        Handle GET request for user authentication.

        Args:
            request: HTTP request object.

        Returns:
            Response: HTTP response with user data or authentication error.
        """
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=['Auth'],
        operation_id="register", 
        request_body=UserSerializer,
        responses={
            201: UserSerializer,
            400: ErrorResponseSerializer,
        }
    )
    def post(self, request):    
        """
        Handle POST request for user registration.

        Args:
            request: HTTP request object containing user registration data.

        Returns:
            Response: HTTP response with success message or error.
        """
        # Validate user input
        serializer = UserSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Save user data
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(ErrorResponseSerializer.from_dict({"exception": str(e)}).data, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        tags=['Auth'],
        operation_id="logout", 
        request_body=LogoutSerializer,
        responses={
            200: openapi.Response(description="Logout successful"),
            400: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        }
    )
    def delete(self, request):
        """
        Handle DELETE request for user logout.

        Args:
            request: HTTP request object containing user token.

        Returns:
            Response: HTTP response with success message or error.
        """
        
        serializer = LogoutSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            
            
            # Retrieve the user's refresh token
            refresh_token = RefreshToken(serializer.validated_data['refresh'])
            
            # Blacklist the refresh token
            refresh_token.blacklist()
            
            return Response( status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.INTERNAL.value, message= str(e)).data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from datetime import datetime
from django.utils import timezone

class CustomTokenRefreshView(TokenRefreshView):
    def get_serializer_class(self):
        # Use the existing TokenRefreshSerializer from simple_jwt
        return TokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        # Call the parent class's post method to get the original response
        print(request.data)
        response = super().post(request, *args, **kwargs)

        
        # Extract expiration dates
        access_token_expires = timezone.now() + settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
        refresh_token_expires = timezone.now() + settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']


        # Add expiration details to the response data
        response.data ={
            'refresh_token': str(response.data['refresh']),            
            'refresh_token_expires': refresh_token_expires.isoformat(),
            'access_token': str(response.data['access']),
            'access_token_expires': access_token_expires.isoformat()
            
        }

        return response

###
#   User
##


class UserListView(APIView):

    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['User'],
        operation_summary="Retrieve a paginated list of users",
        operation_description="Retrieve a paginated list of users based on optional search criteria.",
        manual_parameters=[
            openapi.Parameter(
                'string',
                openapi.IN_QUERY,
                description="String to search for in users' first name, last name, or email address.",
                type=openapi.TYPE_STRING,
                default=""
            ),
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="The page number to retrieve.",
                type=openapi.TYPE_INTEGER,
                default=1
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="The number of users per page. Must be one of [5, 10, 20, 40].",
                type=openapi.TYPE_INTEGER,
                default=5
            ),
        ],
        responses={
            200: openapi.Response(
                description='A paginated list of users.',
                schema=ListResponseSerializer
            ),
            400: openapi.Response(
                description='Bad request. The provided page does not exist or other parameter issues.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def get(self, request):
        """
        Retrieve a paginated list of users based on optional search criteria.

        Search criteria:
            - string: A string to search for in users' first name, last name, or email address. Defaults to an empty string.
            - page: The page number to retrieve. Defaults to 1.
            - page_size: The number of users per page. Must be one of [5, 10, 20, 40]. Defaults to 5.

        Returns:
            Response: A JSON response containing the paginated list of users and metadata.
                The metadata includes information about the current page, page size, total pages, and total users.
        """
        
        # Get query parameters
        string_to_search = request.query_params.get('string', '')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 5))
                
        # Build base query
        query = User.objects.exclude(user_type=User.UserType.ADMIN.value).order_by('created_at')
        
        # Perform search if string_to_search is provided
        if string_to_search:
            query = query.filter(
                Q(first_name__icontains=string_to_search) |
                Q(last_name__icontains=string_to_search) |
                Q(email__icontains=string_to_search)
            )
        
        # Paginate the results
        paginator = Paginator(query, page_size)

        
        # Get the requested page
        try:
            records_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_dict({"exception":"Page does not exist."}).data, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(
            ListResponseSerializer.build_(request,page,paginator,serializer = UserSimpleSerializer(records_page, many=True),endpoint_name="user_list").data,
            status=status.HTTP_200_OK)
    
    
class UserView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    """
    API endpoint for user operations.

    Supports GET, DELETE, and PATCH methods.
    Requires JWT authentication.
    """

    
    @swagger_auto_schema(
        tags=['User'],
        operation_summary="Retrieve authenticated user profile",
        operation_description="Retrieve the authenticated user's profile by ID or username",
        manual_parameters=[
            openapi.Parameter('id', openapi.IN_QUERY, description="User ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('username', openapi.IN_QUERY, description="Username", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response(
                description='Successful operation',
                schema=UserSimpleSerializer
            ),
            400: openapi.Response(
                description='Bad request',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def get(self, request):
        """
        Retrieve a user profile by ID or username.

        Args:
            request: Request object containing query parameters.

        Returns:
            Response: JSON response containing the user profile.
        """


        # Get query parameters
        id = request.query_params.get('id')
        username = request.query_params.get('username')

        # Validate args
        if id:
            try:
                user = User.objects.get(id=id)
            except User.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="User couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        elif username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="User couldn't be found by this username.").data,status=status.HTTP_400_BAD_REQUEST)
        else:

            return Response(ErrorResponseSerializer.from_dict({"args":"Missing arguments."}).data,status=status.HTTP_400_BAD_REQUEST)

        # Check if user is following or pending
        #is_following = Follow.objects.filter(follower=user_logged_id, followed=user).exists()
        #is_pending = FollowRequest.objects.filter(follower=user_logged_id, followed=user).exists()

        # Set followed state based on user relationship
        #followed_state = FOLLOWED_STATE_SET.FOLLOWED.value if is_following else (
        #    FOLLOWED_STATE_SET.PENDING_FOLLOWED.value if is_pending else FOLLOWED_STATE_SET.NOT_FOLLOWED.value
        #)

        # Serialize user profile
        user_data = UserProfileSerializer(user).data
        #user_data['followed_state'] = followed_state

        return Response(data = user_data, status=status.HTTP_200_OK)



    @swagger_auto_schema(
        tags=['User'],
        operation_summary="Patch authenticated user",
        operation_description="Patch the authenticated user's profile",
        request_body=UserPatchSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                description='User profile updated successfully',
                schema=UserSerializer
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description='Error updating user profile',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def patch(self, request):
        """
        Patch the authenticated user.

        Args:
            request: Request object containing user data.

        Returns:
            Response: JSON response containing the updated user profile or error message.
        """

        # Get user authed
        user = request.user

        # Serialize    
        serializer = UserPatchSerializer(data=request.data, partial=True)
        
        # Validate Serializer
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)

        # Update instance
        try:
            validated_data = serializer.validated_data
            
            if 'password' in validated_data:
                if not user.check_password(validated_data.pop('old_password', '')):
                    return Response(ErrorResponseSerializer.from_dict({"validation":"Old password is incorrect."}).data, status=status.HTTP_400_BAD_REQUEST)
                
                user.set_password(validated_data.pop('password'))
                
            for key, value in validated_data.items():
                setattr(user, key, value)

            user.updated_date = timezone.now()
            user.save()
            
        except Exception as e:
            return Response(ErrorResponseSerializer.from_dict({"exception":"Error updating user."}).data, status=status.HTTP_400_BAD_REQUEST)
        
        
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        tags=['User'],
        operation_summary="Delete authenticated user",
        operation_description="Delete the authenticated user",
        responses={
            status.HTTP_200_OK: openapi.Response(
                description='User deleted successfully'
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description='Error deleting user',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def delete(self, request):
        """
        Delete the authenticated user.

        Args:
            request: Request object containing user ID.

        Returns:
            Response: JSON response indicating success or failure.
        """

        # Get user authed
        user = request.user
        
        
        # Retrieve the user's refresh token
        refresh_token = RefreshToken.for_user(user)
        
        # Delete user instance
        user.delete()
        
###
#   Follows
##

class FollowView(APIView):
    
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        tags=['Follow'],
        operation_summary="Follow or send a follow request to a user",
        operation_description=(
            "Follow a user or send a follow request based on the target user's profile type. "
            "If the target user's profile is private, a follow request is sent. If the profile is public, "
            "the user is followed automatically. "
            "Cannot follow oneself."
        ),
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_QUERY,
                description="The ID of the user to be followed.",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description='Follow request sent successfully if the user has a private profile.',
                schema=SuccessResponseSerializer
            ),
            201: openapi.Response(
                description='User followed successfully if the user has a public profile.',
            ),
            400: openapi.Response(
                description='Bad request due to missing parameters, logical errors, or user not found.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def post(self, request):
        
         # Get user authed
        user = request.user
        
        # Get query parameters
        
        user_to_be_followed_id = request.query_params.get('user_id')

        # Validate args
        if not user_to_be_followed_id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing arguments...").data, status=status.HTTP_400_BAD_REQUEST)
        
        user_to_be_followed_id = int(user_to_be_followed_id)

        if user_to_be_followed_id == user.id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.LOGICAL.value,message="User can't follow himself...").data, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_to_be_followed = User.objects.get(id=user_to_be_followed_id)
        except User.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.MISSING_MODEL.value,message="User couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
            

        # Create follow request if user profile_type is private
        if user_to_be_followed.profile_type == User.ProfileType.PRIVATE.value: 
            follow_request, created = FollowRequest.objects.get_or_create(follower=user, followed=user_to_be_followed)
            if not created:
                return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.LOGICAL.value,message="User already follows this account.").data, status=status.HTTP_400_BAD_REQUEST)

            # send new follow request notification to recipient (implement your own function)
            # push_notification(to=user_to_be_followed, by=user, notification_type="FOLLOW_REQUEST") TODO
            return Response(SuccessResponseSerializer.from_string(RESPONSE_CODES.REQUEST_SENT.value).data, status=status.HTTP_200_OK)
        
        # Automatically follow if user profile_type is public
        follow, created = Follow.objects.get_or_create(follower=user, followed=user_to_be_followed)
        if not created:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.LOGICAL.value,message="User already follows this account.").data, status=status.HTTP_400_BAD_REQUEST)

        # send new follow notification to recipient (implement your own function)
        # push_notification(to=user_to_be_followed, by=user, notification_type="FOLLOWED_USER") TODO
        return Response(status=status.HTTP_201_CREATED)
    
    @swagger_auto_schema(
        tags=['Follow'],
        operation_summary="Unfollow a user",
        operation_description="Unfollow a user by specifying either `user_follow_id` or `user_follower_id` in query parameters. Only one parameter can be supplied.",
        manual_parameters=[
            openapi.Parameter(
                'user_follow_id',
                openapi.IN_QUERY,
                description="The ID of the user to be unfollowed.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'user_follower_id',
                openapi.IN_QUERY,
                description="The ID of the user who is unfollowing.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description='Successfully unfollowed the user.',
            ),
            400: openapi.Response(
                description='Bad request due to missing or conflicting parameters, or user not found.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def delete(self,request):
    
         # Get user auth id
        user = request.user
        
        # Get query parameters
        user_follow_id = request.query_params.get('user_follow_id')
        user_follower_id = request.query_params.get('user_follower_id')
        
        # Validate args
        if not user_follow_id and not user_follower_id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing arguments...").data, status=status.HTTP_400_BAD_REQUEST)
        
        if user_follow_id and user_follower_id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Only one param can be supplied...").data, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            if user_follow_id:
                follow = Follow.objects.get(follower=user,followed= int(user_follow_id))

            else:
                follow = Follow.objects.get(follower=int(user_follower_id),followed= user)
                
        except Follow.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.MISSING_MODEL.value,message="User couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # delete
        id_removed = follow.id 
        follow.delete()
            
        return Response(IdResponseSerializer.build_(id=id_removed).data,status=status.HTTP_200_OK)

class FollowersListView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Follow'],
        operation_summary="Retrieve a paginated list of followers",
        operation_description=(
            "Retrieve a paginated list of users who are following the authenticated user. "
            "The results can be filtered and paginated using query parameters."
        ),
        manual_parameters=[
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="The page number to retrieve. Defaults to 1.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="The number of followers per page. Must be one of [5, 10, 20, 40]. Defaults to 5.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description='A paginated list of users.',
                schema=ListResponseSerializer
            ),
            400: openapi.Response(
                description='Bad request due to pagination errors.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def get(self,request):
        
        # Get args
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 5))
        search_string = request.GET.get('search_string', None)
        user_id = request.GET.get('user_id', None)
        
        # Validate args
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="User couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        else:
            # Get user auth
            user = request.user
        

        # Query
        
        query = User.objects.filter(followers__followed=user)
        
        # Filter by search string if provided
        if search_string:
            query = query.filter(Q(name__icontains=search_string) | Q(username__icontains=search_string))


        # Paginate the results
        paginator = Paginator(query, page_size)

        
        # Get the requested page
        try:
            users_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.PAGINATION.value,message ="Page does not exist.").data, status=status.HTTP_400_BAD_REQUEST)

        return Response(
        ListResponseSerializer.build_(request,page,paginator,serializer = UserSimpleSerializer(users_page, many=True),endpoint_name="follow_requests").data,
        status=status.HTTP_200_OK)
    
class FollowsListView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['User'],
        operation_summary="Retrieve a paginated list of users followed by the authenticated user",
        operation_description=(
            "Retrieve a paginated list of users who are followed by the authenticated user. "
            "The results can be filtered and paginated using query parameters."
        ),
        manual_parameters=[
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="The page number to retrieve. Defaults to 1.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="The number of followed users per page. Must be one of [5, 10, 20, 40]. Defaults to 5.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description='A paginated list of users.',
                schema=ListResponseSerializer
            ),
            400: openapi.Response(
                description='Bad request due to pagination errors.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def get(self,request):
        
        # Get args
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 5))
        search_string = request.GET.get('search_string', None)
        user_id = request.GET.get('user_id', None)
        
        # Validate args
        
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="User couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        else:
            # Get user auth
            user = request.user
        

        # Query
        
        query = User.objects.filter(followeds__follower=user)
        
        if search_string:
            query = query.filter(Q(name__icontains=search_string) | Q(username__icontains=search_string))


        # Paginate the results
        paginator = Paginator(query, page_size)

        
        # Get the requested page
        try:
            users_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.PAGINATION.value,message ="Page does not exist.").data, status=status.HTTP_400_BAD_REQUEST)
        
       
        return Response(
        ListResponseSerializer.build_(request,page,paginator,serializer = UserSimpleSerializer(users_page, many=True),endpoint_name="follow_requests").data,
        status=status.HTTP_200_OK)

class UsersToFollowView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        
        # Get user authed
        user = request.user
        
        # Get args
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        search_string = request.GET.get('search_string', None)
        
        # Fetch follow request and follow information
        follow_requests_ids = set(FollowRequest.objects.filter(follower=user.id).values_list('followed_id', flat=True))
        follows_ids = set(Follow.objects.filter(follower=user.id).values_list('followed_id', flat=True))
        
        # Annotate query to mark users with pending follow requests and if they are followed
        query = User.objects.exclude(user_type=User.UserType.ADMIN.value).exclude(id=user.id).exclude(id__in=follows_ids).order_by('created_at')

        # Annotate with request_sent and follower boolean fields
        query = query.annotate(
            request_sent=Case(
                When(id__in=follow_requests_ids, then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            ),
            follower=Case(
                When(id__in=follows_ids, then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            )
        ).order_by('-request_sent', 'created_at')
        
        if search_string:
            query = query.filter(Q(name__icontains=search_string) | Q(username__icontains=search_string))

        # Paginate the results
        paginator = Paginator(query, page_size)
        total_users = paginator.count
        total_pages = paginator.num_pages
        
        # Get the requested page
        try:
            users_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_dict({ERROR_TYPES.PAGINATION.value: "Page does not exist."}).data, status=status.HTTP_400_BAD_REQUEST)
        
        # Build response data
        response_data = {
            "_metadata": {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_users": total_users
            },
            "result": []
        }
        

        # Fill Results
        for item in users_page:
            user_data = UserToFollowSerializer(item).data
            response_data["result"].append(user_data)
        
        return Response(
        ListResponseSerializer.build_(request,page,paginator,serializer = UserToFollowSerializer(users_page, many=True),endpoint_name="users_to_follow_list").data,
        status=status.HTTP_200_OK)

##
#   Follow Request
#
class FollowRequestListView(APIView):
    
    
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        tags=['Follow Request'],
        operation_summary="Retrieve paginated list of follow requests",
        operation_description=(
            "Retrieve a paginated list of follow requests received by the authenticated user. "
            "The results can be filtered and paginated using query parameters."
        ),
        manual_parameters=[
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="The page number to retrieve. Defaults to 1.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="The number of follow requests per page. Must be one of [5, 10, 20, 40]. Defaults to 5.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        
            responses={
            200: openapi.Response(
                description='A paginated list of users.',
                schema=ListResponseSerializer
            ),
            400: openapi.Response(
                description='Bad request. The provided page does not exist or other parameter issues.',
                schema=ErrorResponseSerializer
            ),
            }
        
    )
    def get(self, request):
        # Get user auth id
        user = request.user

        # Get args
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 5))

        # Fetch follow request and follow information
        follow_requests_ids = set(FollowRequest.objects.filter(follower=user.id).values_list('followed_id', flat=True))
        follows_ids = set(Follow.objects.filter(follower=user.id).values_list('followed_id', flat=True))
        
        print(follows_ids)
        print(FollowRequest.objects.filter(followed=user).values_list('follower_id', flat=True))

        # Query and annotate with request_sent and is_follower boolean fields
        follow_requests = FollowRequest.objects.filter(followed=user).annotate(
            request_sent=Case(
                When(follower__id__in=follow_requests_ids, then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            )
        ).order_by('created_at')

        # Paginate the results
        paginator = Paginator(follow_requests, page_size)

        # Get the requested page
        try:
            users_page = paginator.page(page)
        except Exception:
            return Response(
                ErrorResponseSerializer.from_params(
                    type=ERROR_TYPES.PAGINATION.value,
                    message="Page does not exist."
                ).data, 
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            ListResponseSerializer.build_(
                request, page, paginator, serializer=FollowRequestSerializer(users_page, many=True), endpoint_name="follow_requests_list"
            ).data,
            status=status.HTTP_200_OK
        )
    

class FollowRequestView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Follow Request'],
        operation_summary="Accept a follow request",
        operation_description=(
            "Accept a follow request from a user. If the request is accepted, the users are followed. "
            "The request is automatically deleted. Cannot accept a follow request from oneself."
        ),
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_QUERY,
                description="The ID of the user whose follow request is to be accepted.",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            201: openapi.Response(
                description='Successfully accepted the follow request and followed the user.',
            ),
            400: openapi.Response(
                description='Bad request due to missing parameters, logical errors, or user not found.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def post(self,request):
        
        # Get user authed
        user = request.user
        
        # Get query parameters
        
        user_follow_request_id = request.query_params.get('id')

        # Validate args
        if not user_follow_request_id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing arguments...").data, status=status.HTTP_400_BAD_REQUEST)
        
        user_follow_request_id = int(user_follow_request_id)

        if user_follow_request_id == user.id:
           return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.LOGICAL.value,message="User can't accept follow request himself...").data, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_follow_request = FollowRequest.objects.get(id = user_follow_request_id,followed= user)
        except FollowRequest.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.MISSING_MODEL.value,message="User couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
            
        # Automatically follow if user profile_type is public
        follow, created = Follow.objects.get_or_create(follower=user_follow_request.follower, followed=user_follow_request.followed)
        if not created:
            #logger.error("This isn't supose to happen, this problem should be caught on FollowView post method where we create the follow request...") # TODO make test about this
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.LOGICAL.value,message="User already follows this account.").data, status=status.HTTP_400_BAD_REQUEST)
        
        # delete obselete follow request
        user_follow_request.delete()
        # send new follow notification to recipient (implement your own function)
        # push_notification(to=user_to_be_followed, by=user, notification_type="FOLLOWED_USER") TODO
        return Response(status=status.HTTP_201_CREATED)
    
    
    @swagger_auto_schema(
        tags=['Follow Request'],
        operation_summary="Reject a follow request",
        operation_description="Reject a follow request from a user. The request is deleted without further action.",
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_QUERY,
                description="The ID of the user whose follow request is to be rejected.",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description='Successfully rejected and deleted the follow request.',
            ),
            400: openapi.Response(
                description='Bad request due to missing parameters, logical errors, or user not found.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def delete(self,request):
    
        # Get user auth id
        user = request.user
        
        # Get query parameters
        follower_id = request.query_params.get('follower_id')
        followed_id = request.query_params.get('follow_id')
        
        # Validate args
        if follower_id:
            follower_id = int(follower_id)
            
        elif followed_id:
            followed_id = int(followed_id)
            
        else:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing arguments...").data, status=status.HTTP_400_BAD_REQUEST)
        
        # Parse args
        
        
        if follower_id:
            
            try:
                user_follow_request = FollowRequest.objects.get(followed_id = user.id,follower= follower_id)
            except FollowRequest.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.MISSING_MODEL.value,message="User couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                user_follow_request = FollowRequest.objects.get(followed_id = followed_id,follower= user.id)
            except FollowRequest.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.MISSING_MODEL.value,message="User couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # delete
        id_removed = user_follow_request.id 
        user_follow_request.delete()
            
        return Response(IdResponseSerializer.build_(id=id_removed).data,status=status.HTTP_200_OK)
        
        

     