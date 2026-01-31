import uuid

from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    alias = models.CharField('In game alias', max_length=36, unique=True, default=uuid.uuid4)

    def __str__(self):
        return self.username
