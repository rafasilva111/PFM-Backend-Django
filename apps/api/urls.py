from django.urls import path

from .views import LoginView,AuthView,UserView,UserListView,UsersToFollowView,FollowView,FollowRequestView,FollowersListView,FollowsListView,FollowRequestListView,GoalsView,IdealWeightView



urlpatterns = [
    
    
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
    path(f'follow/requests/list', FollowRequestListView.as_view(), name="follow_requests"), # get follow requests
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
    #
    #   Recipe App
    #
    ##
    
    ###
    #   Recipe
    ##

    #path(f'recipe', RecipeDetailView.as_view(), name="login"),
    #path(f'recipe/list', RecipeListView.as_view(), name="login"),
] 
