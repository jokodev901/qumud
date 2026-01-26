import uuid
from django.db import models

from authentication.models import User
from world.models import Entity


class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    alias = models.CharField('in game alias', max_length=32, unique=True)
    current_character = models.OneToOneField(Entity, on_delete=models.SET_NULL, null=True, blank=True)
