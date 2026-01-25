import uuid
from django.db import models

from authentication.models import User


class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    alias = models.CharField('in game alias', max_length=32, unique=True)
