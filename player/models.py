from django.db import models


class Player(models.Model):
    name = models.CharField('Player in game alias', max_length=32, unique=True)
