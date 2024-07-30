from django.db import models
from apps.common.models import BaseModel
from apps.user_app.models import User
from django.core.exceptions import ValidationError
# Create your models here.

class Group(BaseModel):
    """
    Model to store shopping lists.
    """
    
    name = models.CharField(max_length=255, null=False)
    users = models.ManyToManyField(User, related_name='groups')
    admins = models.ManyToManyField(User, related_name='admined_groups')
    owner = models.ForeignKey(User, related_name='owned_groups', on_delete=models.CASCADE)
    img_source = models.CharField(max_length=255, null=True)\
    
class GroupInvite(BaseModel):
    """
    Model to store shopping lists.
    """
    
    title = models.CharField(max_length=255, null=False)
    description = models.CharField(max_length=255, null=False)
    inviter = models.ForeignKey(Group, related_name='invites', on_delete=models.CASCADE)
    invited = models.ForeignKey(User, related_name='invites', on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('inviter', 'invited')

    @classmethod
    def create_invite(cls, group_inviter_id, invited_user_id, title, description):
        try:
            inviter = Group.objects.get(id=group_inviter_id)
            invited_user = User.objects.get(id=invited_user_id)
            
            # Check if an invite already exists
            if cls.objects.filter(inviter=inviter, invited=invited_user).exists():
                raise ValidationError("User already invited.")
            
            invite = cls(
                inviter=inviter,
                invited=invited_user,
                title=title,
                description=description
            )
            invite.save()
            return invite
        except Group.DoesNotExist:
            raise ValidationError("Inviter group does not exist.")
        except User.DoesNotExist:
            raise ValidationError("Invited user does not exist.")