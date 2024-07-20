from django.urls import path, re_path

from rest_framework import permissions

from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from .views import LoginView,AuthView,UserView,UserListView,UsersToFollowView,FollowView,FollowRequestView,FollowersListView,FollowsListView,FollowRequestListView,GoalsView,IdealWeightView

###
#   Views
##

from apps.recipe_app.api_views import RecipeListView,RecipeView,RecipeReportView,CommentView,RecipeReportListView,CommentListView,CommentLikeView,RecipesLikedView,RecipesSavedView,RecipesCreatedView
from apps.calendar_app.api_views import CalendarListView, CalendarView, CalendarIngredientsListView, CalendarEntryListCheckView
from apps.notification_app.api_views import NotificationView,NotificationListView



schema_view = get_schema_view(
openapi.Info(
    title="GoodBites API Documentation",
    default_version='v1',
    description="Test description",
    #terms_of_service="https://www.google.com/policies/terms/",
    #contact=openapi.Contact(email="contact@myapi.local"),
    #license=openapi.License(name="BSD License"),
),
public=True,
permission_classes=(permissions.AllowAny,),
)

urlpatterns = [


    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
  
    
    ###
    #
    #   User App
    #
    ##
    
    ###
    #   Auth
    ##
    
    path(f'auth', AuthView.as_view(), name="auth"), # Get, Register, Logout Session
    path(f'auth/login', LoginView.as_view(), name="login"), # Log in Session
    
    ###
    #   User
    ##
    
    path(f'user', UserView.as_view(), name="user"), # get, post, put, delete user
    path(f'user/list', UserListView.as_view(), name="user_list"), # get users
    
    ###
    #   Follows
    ##
    
    path(f'follow', FollowView.as_view(), name="follow"), # post follow (can create follow request)
    path(f'follow/requests/list', FollowRequestListView.as_view(), name="follow_requests_list"), # get follow requests
    path(f'follow/requests', FollowRequestView.as_view(), name="follow_requests"), # post follow request (accepts follow request)
    path(f'follow/find', UsersToFollowView.as_view(), name="users_to_follow_list"), # get users to be followed
    path(f'follow/list/follows', FollowsListView.as_view(), name="user_follows_list"), # get user's follows
    path(f'follow/list/followers', FollowersListView.as_view(), name="user_followers_list"), # get user's followers
    
    ###
    #   Goals
    ##

    
    path(f'goals', GoalsView.as_view(), name="goals"), # get, post, delete goal
    path(f'goals/weight', IdealWeightView.as_view(), name="ideal_weight"), # get User's ideal weight
    
    ###
    #   Notifications
    ##
    
    path(f'notification', NotificationView.as_view(), name="notification"), # get, post, put, delete Recipe Report
    path(f'notification/list', NotificationListView.as_view(), name="notification_list"), # get, put, delete Notification List
    
    
    ###
    #
    #   Recipe App
    #
    ##
    
    ###
    #   Recipe
    ##

    path(f'recipe', RecipeView.as_view(), name="recipe"), # post Recipe
    path(f'recipe/list', RecipeListView.as_view(), name="recipe_list"), # get Recipes
    
    ###
    #   Comments
    ##
    
    path(f'recipe/comment', CommentView.as_view(), name="comment"), # get, post, put, delete Comment
    path(f'recipe/comment/list', CommentListView.as_view(), name="comment_list"), # get Comments
    path(f'recipe/comment/like', CommentLikeView.as_view(), name="comment_like"), # post, delete Comment like
    
    ###
    #   Backgrounds
    ##
    
    path(f'recipe/like', RecipesLikedView.as_view(), name="recipes_liked"), # get Recipes Liked; post, delete Recipe Like
    path(f'recipe/save', RecipesSavedView.as_view(), name="recipes_saved"), # get Recipes Saved; post, delete Recipe Save
    path(f'recipe/create', RecipesCreatedView.as_view(), name="recipes_created"), # get Recipes Created
    
    ###
    #   Recipe Report
    ##
    
    path(f'recipe/report', RecipeReportView.as_view(), name="recipe_report"), # get, post, put, delete Recipe Report
    path(f'recipe/report/list', RecipeReportListView.as_view(), name="recipe_report_list"), # get Recipe Reports
    
    
    ###
    #
    #   Calender App
    #
    ##
    
    path('calendar', CalendarView.as_view(), name='calendar'), # get, post, put, delete CalendarEntrys
    path('calendar/list', CalendarListView.as_view(), name='calendar_list'), # get CalendarEntrys
    path('calendar/ingredients/list', CalendarIngredientsListView.as_view(), name='calendar-ingredients-list'),
    path('calendar/list/check', CalendarEntryListCheckView.as_view(), name='calendar-list-check'),

] 
