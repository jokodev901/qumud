import random
import uuid
import time
import math

from django.db import models
from authentication.models import User


class BaseModel(models.Model):
    created_at = models.FloatField(default=time.time, db_index=True)

    class Meta:
        abstract = True


class World(BaseModel):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField('name', max_length=64, unique=True, db_index=True)

    start_location = models.ForeignKey('Location', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name


class Region(BaseModel):
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
    level = models.IntegerField('level', default=1)

    world = models.ForeignKey(World, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Location(BaseModel):
    LOCATION_TYPES = (
        ('T', 'Town'),
        ('D', 'Dungeon'),
    )

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField('Location name', max_length=64)
    level = models.IntegerField('level', default=1)
    last_event = models.FloatField(null=True, blank=True, default=0)
    type = models.CharField('Location type', max_length=1, choices=LOCATION_TYPES)
    max_players = models.IntegerField(default=1)
    spawn_rate = models.IntegerField(null=True, default=5)

    region = models.ForeignKey(Region, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Event(BaseModel):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    size = models.IntegerField(default=100)
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


class EventLog(BaseModel):
    htclass = models.CharField(max_length=64, blank=True, null=True)
    log = models.TextField()

    event = models.ForeignKey(Event, on_delete=models.CASCADE)


class EnemyTemplate(BaseModel):
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


class Entity(BaseModel):
    ENTITY_TYPES = (
        ('P', 'Player'),
        ('E', 'Enemy'),
    )

    # Field types for conditional triggers
    EVENT_FIELDS = {'health', 'level', 'position', 'event',}
    STATUS_FIELDS = {'max_health', 'health', 'level',}
    LOCATION_FIELDS = {'location',}

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField('Name', max_length=32)
    type = models.CharField('Entity type', max_length=1, choices=ENTITY_TYPES)

    # Hidden combat fields that do not require display
    attack_range = models.IntegerField(default=1)
    attack_damage = models.IntegerField(default=1)
    speed = models.IntegerField(default=1)
    initiative = models.IntegerField(default=0)
    max_targets = models.IntegerField(default=1)

    # Combat fields that require display updates
    max_health = models.IntegerField(default=1)
    health = models.IntegerField(default=1)
    level = models.IntegerField(default=1)
    position = models.IntegerField(default=None, null=True, db_index=True)

    # References
    target = models.ForeignKey('Entity', null=True, blank=True, on_delete=models.SET_NULL)

    @property
    def health_perc(self):
        return math.floor((self.max_health / self.health) * 100)

    def __str__(self):
        return self.name


class Player(Entity):
    # State flags
    new_status = models.BooleanField(default=False) # Does the status pane need to be updated?
    new_location = models.BooleanField(default=False) # Do we need to do new location operations?

    # Relationships
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL)
    owner = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name='user_characters')
    active = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, null=True, blank=True, on_delete=models.SET_NULL)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # We may need to update previous relationships, so set those ids here
        self._previous_event_id = self.event_id

    def save(self, *args, **kwargs):
        if not self.id:
            self.type = 'P'

        else:
            update_fields = kwargs.get('update_fields')
            # push an updates to fields or related models when relevant field changes are made

            if update_fields is not None:
                update_set = set(update_fields)

                status_update = not update_set.isdisjoint(self.STATUS_FIELDS)
                location_update = not update_set.isdisjoint(self.LOCATION_FIELDS)

                if location_update:
                    self.new_location = True
                    update_set.add('new_location')

                if status_update:
                    self.new_status = True
                    update_set.add('new_status')

                kwargs['update_fields'] = update_set

        super().save(*args, **kwargs)


class PlayerLog(BaseModel):
    htclass = models.CharField(max_length=64, blank=True, null=True)
    log = models.TextField()

    player = models.ForeignKey(Player, on_delete=models.CASCADE)


class Enemy(Entity):
    event = models.ForeignKey(Event, null=True, blank=True, on_delete=models.CASCADE)
    dead = models.FloatField(null=True, blank=True)
    svg = models.TextField()
    top = models.IntegerField(default=50)
    left = models.IntegerField(default=50)

    @property
    def render_svg(self):
        dead = None

        if self.dead:
            dead = "defeat-animate"

        return self.svg.format(public_id=self.public_id, top=self.top, left=self.left, dead=dead)

    def save(self, *args, **kwargs):
        if not self.id:
            self.type = 'E'

        super().save(*args, **kwargs)


class RegionChatMessage(BaseModel):
    message = models.TextField()

    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
