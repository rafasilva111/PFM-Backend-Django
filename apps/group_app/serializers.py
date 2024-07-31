
from rest_framework import serializers
from apps.shopping_app.models import ShoppingList, ShoppingIngredient
from apps.recipe_app.serializers import IngredientSerializer
from apps.group_app.models import Group, GroupInvite
from apps.user_app.models import User

from django.core.exceptions import ValidationError
##
#   Contants
#

from apps.common.constants import MAX_USER_NORMAL_GROUPS,MAX_USER_PREMIUM_GROUPS



class GroupSerializer(serializers.ModelSerializer):
    
    users = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        required=False,
        allow_empty=True
    )
    
    admins = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        required=False,
        allow_empty=True
    )

    
    
    class Meta:
        model = Group
        fields = '__all__'
        read_only_fields = ['id','owner']
        
        
    def create(self, validated_data):
        
        
        # Get context instances
        user = self.context.get('user')
    
        # Validate context instances               
        if not user:
            raise serializers.ValidationError("User is required to create a Group.")
        
        # Enforce Premium Priveleges
        if user:
            max_lists = MAX_USER_PREMIUM_GROUPS if user.user_type == user.UserType.PREMIUM else MAX_USER_NORMAL_GROUPS
            
            if user.groups.count() >= max_lists:
                raise serializers.ValidationError({
                    "archived": f"Exceeded the maximum allowed groups ({max_lists})."
                })
        
        
        # Create the Group instance
        group = Group.objects.create(owner= user,**validated_data)
        
        # Add the user to the group's users ManyToManyField
        group.users.add(user)
        
        return group

    def update(self, instance, validated_data):
        
        # Get context instances
        user = self.context.get('user')
        
        # Extract nested data
        users_data = validated_data.pop('users', None)
        admins_data = validated_data.pop('admins', None)

        # Update the main instance
        instance = super().update(instance, validated_data)

        # Handle nested data
        if user in instance.admins.all() or user == instance.owner:
            if users_data is not None:
                # Get current users in the group
                current_users = set(instance.users.all())

                # Convert users_data to a set of User instances
                new_users = set(users_data)

                # Users to be removed
                users_to_remove = current_users - new_users

                # Remove users not in the new users_data
                for user in users_to_remove:
                    instance.users.remove(user)

                # Add Users to the group's users
                for user in new_users:
                    # Send invite to user if not already in the group
                    if user not in current_users:
                        try:
                            GroupInvite.create_invite(instance.id, user.id, "Group Invite", "You've been invited to join a group.")
                        except ValidationError:
                            pass

        # Handle nested data for admins
        if user == instance.owner:
            if admins_data is not None:
                # Get current admins in the group
                current_admins = set(instance.admins.all())

                # Convert admins_data to a set of User instances
                new_admins = set(admins_data)

                # Admins to be removed
                admins_to_remove = current_admins - new_admins

                # Remove admins not in the new admins_data
                for admin in admins_to_remove:
                    instance.admins.remove(admin)

                # Add new admins
                for admin in new_admins:
                    instance.admins.add(admin)
                    # TODO: Notify user

        return instance



class GroupInviteSerializer(serializers.ModelSerializer):
    
    
    class Meta:
        model = GroupInvite
        fields = '__all__'
        read_only_fields = ['id','owner']
        
        
    def create(self, validated_data):
        
        
        # Get context instances
        user = self.context.get('user')
    
        # Validate context instances               
        if not user:
            raise serializers.ValidationError("User is required to create a Group.")
        
        # Enforce Premium Priveleges
        if user:
            max_lists = MAX_USER_PREMIUM_GROUPS if user.user_type == user.UserType.PREMIUM else MAX_USER_NORMAL_GROUPS
            
            if user.groups.count() >= max_lists:
                raise serializers.ValidationError({
                    "archived": f"Exceeded the maximum allowed groups ({max_lists})."
                })
        
        # Create the Group instance
        group = Group.objects.create(owner= user,**validated_data)
        
        # Add the user to the group's users ManyToManyField
        group.users.add(user)
        
        return group

    def update(self, instance, validated_data):
        
        # Extract nested data
        users_data = validated_data.pop('users', None)
        
        # Update the main instance
        instance = super().update(instance, validated_data)
        
        # Handle nested data
        if users_data:

            # Add Users to the group's users
            for user in users_data:
            
                instance.users.add(user)

                
        return instance
    