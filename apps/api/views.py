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
from apps.api.serializers import TokenSerializer,ErrorResponseSerializer,LoginSerializer,ResetSerializer,LogoutSerializer,SuccessResponseSerializer
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from apps.api.constants import ERROR_TYPES,RESPONSE_CODES

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

from apps.user_app.models import User, FollowRequest,Follow
from apps.user_app.serializers import UserSerializer,SimpleUserSerializer,PatchUserSerializer,UserToFollowSerializer

###
#   Auth
##

class LoginView(APIView):
    """
    View for user login authentication.

    - Accepts POST requests with email and password.
    - Returns a token for successful authentication.
    """
    authentication_classes = [TokenAuthentication]

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
        token_serializer = TokenSerializer.for_user(user)
        
        return Response(token_serializer.data, status=status.HTTP_200_OK)


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
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        if self.request.method == 'DELETE':
            return [IsAuthenticated()]
        return []

    def get(self, request):
        """
        Handle GET request for user authentication.

        Args:
            request: HTTP request object.

        Returns:
            Response: HTTP response with user data or authentication error.
        """
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)

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
            return Response(ErrorResponseSerializer.from_dict({"exception":str(e)}).data, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """
        Handle POST request for user logout.

        Args:
            request: HTTP request object containing user token.

        Returns:
            Response: HTTP response with success message or error.
        """
        
        serializer = LogoutSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)
        try:
                # Get user authed
            user = request.user
            
            
            # Retrieve the user's refresh token
            refresh_token = RefreshToken.for_user(user)
            
            
            # Blacklist the refresh token
            refresh_token.blacklist()
            
            return Response(status=status.HTTP_200_OK)
            
            return Response(status= status.HTTP_200_OK)
        except Exception as e:
            return Response(ErrorResponseSerializer.from_dict({"exception":str(e)}).data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



###
#   User
##


class UserListView(APIView):
    def get(self, request):
        """
        Retrieve a paginated list of users based on optional search criteria.

        Args:
            request: HttpRequest object representing the incoming request.
            string_to_search (str, optional): A string to search for in users' first name, last name, or email address.
                Defaults to an empty string.
            page (int, optional): The page number to retrieve. Defaults to 1.
            page_size (int, optional): The number of users per page. Must be one of [5, 10, 20, 40]. Defaults to 5.

        Returns:
            Response: A JSON response containing the paginated list of users and metadata.
                The metadata includes information about the current page, page size, total pages, and total users.

        """
        
        # Get query parameters
        string_to_search = request.query_params.get('string', '')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 5))
                
        # Build base query
        base_query = User.objects.exclude(user_type=User.UserType.ADMIN.value).order_by('created_at')
        
        # Perform search if string_to_search is provided
        if string_to_search:
            base_query = base_query.filter(
                Q(first_name__icontains=string_to_search) |
                Q(last_name__icontains=string_to_search) |
                Q(email__icontains=string_to_search)
            )
        
        # Paginate the results
        paginator = Paginator(base_query, page_size)
        total_users = paginator.count
        total_pages = paginator.num_pages
        
        # Get the requested page
        try:
            users_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_dict({"exception":"Page does not exist."}).data, status=status.HTTP_400_BAD_REQUEST)
        
       
        serializer = SimpleUserSerializer(users_page, many=True)
        
        # Build response data
        response_data = {
            "_metadata": {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_users": total_users
            },
            "result": serializer.data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    
    
class UserView(APIView):
    """
    API endpoint for user operations.

    Supports GET, DELETE, and PATCH methods.
    Requires JWT authentication.
    """

    permission_classes = [IsAuthenticated]
    
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
                return Response(ErrorResponseSerializer.from_dict({"missing":"User couldn't be found by this id."}).data,status=status.HTTP_400_BAD_REQUEST)
        elif username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return Response(ErrorResponseSerializer.from_dict({"missing":"User couldn't be found by this username."}).data,status=status.HTTP_400_BAD_REQUEST)
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
        user_data = SimpleUserSerializer(user).data
        #user_data['followed_state'] = followed_state

        return Response(data = user_data, status=status.HTTP_200_OK)



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


        # Validate user data
        serializer = PatchUserSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Update user instance
        try:
            validated_data = serializer.validated_data
            if 'password' in validated_data:
                if not user.check_password(validated_data.pop('old_password', '')):
                    return Response(ErrorResponseSerializer.from_dict({"validation":"Old password is incorrect."}).data, status=status.HTTP_400_BAD_REQUEST)
                
                user.set_password(validated_data.pop('password'))
                
            for key, value in validated_data.items():
                setattr(user, key, value)

            user.updated_date = datetime.now(timezone.utc)
            user.save()

            return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(ErrorResponseSerializer.from_dict({"exception":"Error updating user."}).data, status=status.HTTP_400_BAD_REQUEST)
        
    
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
        
        # Blacklist the refresh token
        refresh_token.blacklist()
        return Response(status=status.HTTP_200_OK)
    
class FollowView(APIView):
    
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
            
        follow.delete()
            
        return Response(status=status.HTTP_200_OK)

class FollowRequestListView(APIView):
    
     def get(self,request):

        # Get user auth id
        user = request.user

        # Get args
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 5))

        # Query
        
        # select all followers ids corresponding to current user       
        follow_requests = FollowRequest.objects.filter(followed=user).order_by('created_at')
        
        # Paginate the results
        paginator = Paginator(follow_requests, page_size)
        total_users = paginator.count
        total_pages = paginator.num_pages
        
        # Get the requested page
        try:
            users_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.PAGINATION.value,message ="Page does not exist.").data, status=status.HTTP_400_BAD_REQUEST)
        
       
        serializer = SimpleUserSerializer(users_page, many=True)

        # Build response data
        response_data = {
            "_metadata": {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_users": total_users
            },
            "result": serializer.data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    

class FollowRequestView(APIView):
    
   
    def post(self,request):
        
        # Get user authed
        user = request.user
        
        # Get query parameters
        
        user_to_permit_follow_id = request.query_params.get('user_id')

        # Validate args
        if not user_to_permit_follow_id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing arguments...").data, status=status.HTTP_400_BAD_REQUEST)
        
        user_to_permit_follow_id = int(user_to_permit_follow_id)

        if user_to_permit_follow_id == user.id:
            logger.error("This isn't supose to happen, this problem should be caught on FollowView post method where we create the follow request...") # TODO make test about this
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.LOGICAL.value,message="User can't accept follow request himself...").data, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_follow_request = FollowRequest.objects.get(follower=user_to_permit_follow_id,followed= user)
        except User.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.MISSING_MODEL.value,message="User couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
            
        # Automatically follow if user profile_type is public
        follow, created = Follow.objects.get_or_create(follower=user_follow_request.follower, followed=user_follow_request.followed)
        if not created:
            logger.error("This isn't supose to happen, this problem should be caught on FollowView post method where we create the follow request...") # TODO make test about this
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.LOGICAL.value,message="User already follows this account.").data, status=status.HTTP_400_BAD_REQUEST)
        
        # delete obselete follow request
        user_follow_request.delete()
        # send new follow notification to recipient (implement your own function)
        # push_notification(to=user_to_be_followed, by=user, notification_type="FOLLOWED_USER") TODO
        return Response(status=status.HTTP_201_CREATED)
    
    def delete(self,request):
    
        # Get user auth id
        user = request.user
        
        # Get query parameters
        user_followed_id = request.query_params.get('user_id')
        
        try:
            user_follow_request = FollowRequest.objects.get(follower=user,followed= user_followed_id)
        except User.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.MISSING_MODEL.value,message="User couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
            
        user_follow_request.delete()
            
        return Response(status=status.HTTP_200_OK)
        
        

class UsersToFollowView(APIView):
    
    def get(self, request):
        
        # Get user authed
        user = request.user
        
        # Get args
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        search_string = request.GET.get('searchString', '')
        
        # Query
        query = User.objects.exclude(user_type=User.UserType.ADMIN.value).exclude(id=user.id).order_by('created_at')

        if search_string:
            query = query.filter(Q(name__icontains=search_string) | Q(id=search_string))

        # Fetch follow request and follow information
        follow_requests_ids = set(FollowRequest.objects.filter(follower=user.id).values_list('followed_id', flat=True))
        follows_ids = set(Follow.objects.filter(followed=user.id).values_list('follower_id', flat=True))

        # Paginate the results
        paginator = Paginator(query, page_size)
        total_users = paginator.count
        total_pages = paginator.num_pages
        
        # Get the requested page
        try:
            users_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_dict({ERROR_TYPES.PAGINATION.value:"Page does not exist."}).data, status=status.HTTP_400_BAD_REQUEST)
        
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
            user_data = UserToFollowSerializer({"user": item, "request_sent": item.id in follow_requests_ids, "follower": item.id in follows_ids}).data
            response_data["result"].append(user_data)
        
        return Response(response_data, status=status.HTTP_200_OK)
    
class FollowersListView(APIView):
    
    def get(self,request):
        
        # Get user auth id
        user = request.user

        # Get args
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 5))

        # Query
        
        # select all followers ids corresponding to current user       
        follower_ids = Follow.objects.filter(followed=user).values_list('follower_id', flat=True)
        
        # search ids directly on bd
        followers_users = User.objects.filter(id__in=follower_ids)

        # Paginate the results
        paginator = Paginator(followers_users, page_size)
        total_users = paginator.count
        total_pages = paginator.num_pages
        
        # Get the requested page
        try:
            users_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.PAGINATION.value,message ="Page does not exist.").data, status=status.HTTP_400_BAD_REQUEST)
        
       
        serializer = SimpleUserSerializer(users_page, many=True)

        # Build response data
        response_data = {
            "_metadata": {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_users": total_users
            },
            "result": serializer.data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
class FollowsListView(APIView):
    
    def get(self,request):
        
        # Get user auth id
        user = request.user

        # Get args
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 5))

        # Query
        
        # select all followers ids corresponding to current user       
        followed_ids = Follow.objects.filter(follower=user).values_list('followed_id', flat=True)
        
        # search ids directly on bd # TODO this should be better thought
        followeds_users = User.objects.filter(id__in=followed_ids).order_by('created_at')

        # Paginate the results
        paginator = Paginator(followeds_users, page_size)
        total_users = paginator.count
        total_pages = paginator.num_pages
        
        # Get the requested page
        try:
            users_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.PAGINATION.value,message ="Page does not exist.").data, status=status.HTTP_400_BAD_REQUEST)
        
       
        serializer = SimpleUserSerializer(users_page, many=True)

        # Build response data
        response_data = {
            "_metadata": {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_users": total_users
            },
            "result": serializer.data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

from apps.user_app.models import Goal
from apps.user_app.serializers import GoalSerializer,IdealWeightSerializer
from apps.user_app.functions import calculate_bmi

###
#   Goals
##

class IdealWeightView(APIView):
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
        