from django.urls import path

from .views import LoginView,AuthView,UserView,UserListView,UsersToFollowView,FollowView,FollowRequestView,FollowersListView,FollowsListView,FollowRequestListView,GoalsView,IdealWeightView

from apps.recipe_app.api_views import RecipeListView,RecipeView,RecipeReportView,CommentView,RecipeReportListView,CommentListView,CommentLikeView,RecipesLikedView,RecipesSavedView,RecipesCreatedView

from apps.notification_app.api_views import NotificationView,NotificationListView


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
    
    path(f'recipe/likes', RecipesLikedView.as_view(), name="recipes_liked"), # get Recipes Liked; post, delete Recipe Like
    path(f'recipe/saves', RecipesSavedView.as_view(), name="recipes_saved"), # get Recipes Saved; post, delete Recipe Save
    path(f'recipe/creates', RecipesCreatedView.as_view(), name="recipes_created"), # get Recipes Created
    
    ###
    #   Recipe Report
    ##
    
    path(f'recipe/report', RecipeReportView.as_view(), name="recipe_report"), # get, post, put, delete Recipe Report
    path(f'recipe/report/list', RecipeReportListView.as_view(), name="recipe_report_list"), # get Recipe Reports
] 
