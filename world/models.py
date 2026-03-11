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
    max_players = models.IntegerField(default=3)
    spawn_rate = models.IntegerField(null=True, default=5)

    region = models.ForeignKey(Region, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Event(BaseModel):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    size = models.IntegerField(default=100)
    active = models.BooleanField(default=True, db_index=True)
    ended = models.FloatField(default=0)
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

    def delete(self, *args, **kwargs):
        Enemy.objects.filter(event=self).delete()
        super().delete(*args, **kwargs)


class EventLog(BaseModel):
    htclass = models.CharField(max_length=64, blank=True, null=True)
    log = models.TextField()

    event = models.ForeignKey(Event, on_delete=models.CASCADE)


class Entity(BaseModel):
    ENTITY_TYPES = (
        ('P', 'Player'),
        ('E', 'Enemy'),
    )

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField('Name', max_length=32)
    type = models.CharField('Entity type', max_length=1, choices=ENTITY_TYPES)

    attack_range = models.IntegerField(default=1)
    min_damage = models.IntegerField(default=1)
    max_damage = models.IntegerField(default=1)
    speed = models.IntegerField(default=1)
    initiative = models.IntegerField(default=0)
    max_targets = models.IntegerField(default=1)
    max_health = models.IntegerField(default=1)
    health = models.IntegerField(default=1)
    max_mana = models.IntegerField(default=1)
    mana = models.IntegerField(default=1)

    level = models.IntegerField(default=1)

    svg = models.TextField()
    top = models.IntegerField(default=50)
    left = models.IntegerField(default=50)
    position = models.IntegerField(default=None, null=True, db_index=True)
    dead = models.FloatField(null=True, blank=True)
    event_joined = models.FloatField(default=0)

    # References
    target = models.ForeignKey('Entity', null=True, blank=True, on_delete=models.SET_NULL)
    event = models.ForeignKey(Event, null=True, blank=True, on_delete=models.SET_NULL)

    @property
    def health_perc(self):
        return math.floor((self.health / self.max_health) * 100)

    @property
    def mana_perc(self):
        return math.floor((self.mana / self.max_mana) * 100)

    @property
    def render_svg(self):
        return self.svg.format(public_id=self.public_id, top=self.top, left=self.left)

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        Enemy.objects.filter(event=self).delete()
        super().delete(*args, **kwargs)


class PlayerClass(models.Model):
    name = models.CharField('Class name')
    str = models.IntegerField(default=1)
    dex = models.IntegerField(default=1)
    int = models.IntegerField(default=1)
    vit = models.IntegerField(default=1)
    mnd = models.IntegerField(default=1)


class Player(Entity):
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL)
    owner = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name='user_characters')
    active = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE)
    last_travel = models.FloatField(default=0)
    xp = models.IntegerField(default=0)
    xp_next_lvl = models.IntegerField(default=0)
    stat_points = models.IntegerField(default=0)

    str = models.IntegerField(default=1)
    dex = models.IntegerField(default=1)
    int = models.IntegerField(default=1)
    vit = models.IntegerField(default=1)
    mnd = models.IntegerField(default=1)

    @property
    def xp_perc(self):
        return math.floor((self.xp / self.xp_next_lvl) * 100)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # We may need to update previous relationships, so set those ids here
        self._previous_event_id = self.event_id

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.id:
            self.xp_next_lvl = self.level**3 + 9*self.level**2
            self.type = 'P'
            self.svg = """
            <svg id="svg-{public_id}"
             class="position-absolute sprite"
             style="top: {top}%; left: {left}%; transform: translate(-50%, -50%); width: 3rem; height: 3rem; z-index: 1;"
            viewBox="0 0 100 100" width="100" height="100" xmlns="http://www.w3.org/2000/svg">
              <rect x="35" y="45" width="30" height="30" fill="white" stroke="black" stroke-width="2" rx="2" />            
              <rect x="30" y="15" width="40" height="35" fill="white" stroke="black" stroke-width="2" rx="5" />            
              <rect x="35" y="28" width="30" height="8" fill="black" />            
              <rect x="25" y="50" width="10" height="20" fill="white" stroke="black" stroke-width="2" rx="2" />            
              <rect x="65" y="50" width="10" height="20" fill="white" stroke="black" stroke-width="2" rx="2" />            
              <rect x="38" y="75" width="10" height="15" fill="white" stroke="black" stroke-width="2" />
              <rect x="52" y="75" width="10" height="15" fill="white" stroke="black" stroke-width="2" />
            </svg>
            """

        super().save(*args, **kwargs)

    def add_xp(self, add):
        self.xp += add

        if self.xp >= self.xp_next_lvl:
            self.xp = self.xp % self.xp_next_lvl
            self.level += 1
            self.stat_points += 5
            PlayerLog.objects.create(player=self, htclass="", log=f"Leveled up to {self.level}!")
            self.xp_next_lvl = self.level**3 + 9*self.level**2

        self.save()
        return self

    def add_stats(self, stats):
        if 'str' in stats and self.stat_points:
            stat_capped = min(stats['str'], self.stat_points)
            self.str += stat_capped
            self.stat_points -= stat_capped

        if 'dex' in stats and self.stat_points:
            stat_capped = min(stats['dex'], self.stat_points)
            self.dex += stat_capped
            self.stat_points -= stat_capped

        if 'int' in stats and self.stat_points:
            stat_capped = min(stats['int'], self.stat_points)
            self.int += stat_capped
            self.stat_points -= stat_capped

        if 'vit' in stats and self.stat_points:
            stat_capped = min(stats['vit'], self.stat_points)
            self.vit += stat_capped
            self.stat_points -= stat_capped

        if 'mnd' in stats and self.stat_points:
            stat_capped = min(stats['mnd'], self.stat_points)
            self.mnd += stat_capped
            self.stat_points -= stat_capped

        self.save()
        return self


class PlayerLog(BaseModel):
    htclass = models.CharField(max_length=64, blank=True, null=True)
    log = models.TextField()

    player = models.ForeignKey(Player, on_delete=models.CASCADE)


class EnemyArchetype(models.Model):
    name = models.CharField(max_length=64)
    dmg_dev = models.FloatField('Percent deviation from center for damage range', default=1)
    dmg_multi = models.FloatField('Damage multiplier for stronger vs weaker attacks', default=1)
    attack_range = models.IntegerField(default=1)
    speed = models.IntegerField(default=1)
    attack_rate = models.IntegerField('Attacks per round', default=1)
    hp_multi = models.FloatField('HP multiplier', default=1)
    init_multi = models.FloatField('Initiative multiplier', default=1)

    def __str__(self):
        return self.name


class EnemyTemplate(BaseModel):
    svg = models.TextField()
    name = models.CharField('Name', max_length=32)
    max_health = models.IntegerField(default=1)
    attack_range = models.IntegerField(default=1)
    min_damage = models.IntegerField(default=1)
    max_damage = models.IntegerField(default=1)
    speed = models.IntegerField(default=1)
    initiative = models.IntegerField(default=0)
    max_targets = models.IntegerField(default=1)
    level = models.IntegerField(default=1)
    award_xp = models.IntegerField(default=1)

    archetype = models.ForeignKey(EnemyArchetype, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.id:
            self.award_xp = math.floor(((self.level**2) / 5) + self.level)

        super().save(*args, **kwargs)


class Enemy(Entity):
    award_xp = models.IntegerField(default=1)

    def save(self, *args, **kwargs):
        if not self.id:
            self.type = 'E'

        super().save(*args, **kwargs)


class RegionChatMessage(BaseModel):
    message = models.TextField()

    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
