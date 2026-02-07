import uuid
import time
import math

from django.db import models
from authentication.models import User


class World(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField('name', max_length=64, unique=True, db_index=True)

    start_location = models.ForeignKey('Location', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name


class Region(models.Model):
    REGION_BIOMES = (
        ('D', 'Desert'),
        ('F', 'Forest'),
        ('P', 'Plains'),
        ('M', 'Mountains'),
        ('S', 'Swamp'),
        ('T', 'Tundra')
    )

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField('region name', max_length=32)
    biome = models.CharField('biome', max_length=1, choices=REGION_BIOMES)
    level = models.IntegerField('level', null=False, blank=False, default=1)

    world = models.ForeignKey(World, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Location(models.Model):
    LOCATION_TYPES = (
        ('D', 'Dungeon'),
        ('T', 'Town'),
    )

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField('Location name', max_length=64)
    location_type = models.CharField('Location type', max_length=1, choices=LOCATION_TYPES)
    level = models.IntegerField('level', null=False, blank=False, default=1)
    last_event = models.FloatField(null=True, blank=True)

    region = models.ForeignKey(Region, on_delete=models.CASCADE)


    def __str__(self):
        return self.name


class Event(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    size = models.IntegerField(null=False, default=100)
    active = models.BooleanField(default=True, db_index=True)
    last_update = models.FloatField(default=0)

    location = models.ForeignKey(Location, on_delete=models.CASCADE)

    # self.combat_log_buffer = []
    # self.combat_log = []
    # self.status_log = []
    # self.debug_log_buffer = []
    # self.attack_buffer = []
    # self.move_buffer = []

    def __str__(self):
        return f'{self.location.name} Event {str(self.pk)}'


class EnemyTemplate(models.Model):
    svg = models.TextField()
    name = models.CharField('Name', max_length=32)
    max_health = models.IntegerField(default=1)
    attack_range = models.IntegerField(default=1)
    attack_damage = models.IntegerField(default=1)
    speed = models.IntegerField(default=1)
    initiative = models.IntegerField(default=0)
    max_targets = models.IntegerField(default=1)
    level = models.IntegerField(default=1)

    location = models.ForeignKey(Location, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Entity(models.Model):
    ENTITY_TYPES = (
        ('P', 'Player'),
        ('N', 'NPC'),
        ('E', 'Enemy')
    )

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    entity_type = models.CharField(max_length=1, choices=ENTITY_TYPES, db_index=True)
    name = models.CharField('Name', max_length=32)
    max_health = models.IntegerField(default=1)
    health = models.IntegerField(default=1)
    attack_range = models.IntegerField(default=1)
    attack_damage = models.IntegerField(default=1)
    speed = models.IntegerField(default=1)
    initiative = models.IntegerField(default=0)
    max_targets = models.IntegerField(default=1)
    position = models.IntegerField(default=None, null=True, db_index=True)
    level = models.IntegerField(default=1)
    new_status = models.BooleanField(default=False)
    new_location = models.BooleanField(default=False)

    target = models.ForeignKey('Entity', null=True, blank=True, on_delete=models.SET_NULL)
    owner = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name='user_characters')
    active = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, null=True, blank=True, on_delete=models.SET_NULL)
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL)
    template = models.ForeignKey(EnemyTemplate,  null=True, blank=True, on_delete=models.CASCADE)

    @property
    def health_perc(self):
        return math.floor((self.max_health / self.health) * 100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'entities'


class RegionChatMessage(models.Model):
    sent_at = models.FloatField(default=time.time)
    message = models.TextField()

    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
