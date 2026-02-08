from django.contrib import admin
from datetime import datetime
from .models import (
    World, Region, Location, Town, Dungeon,
    Event, EnemyTemplate, Entity, Player, Enemy,
    RegionChatMessage
)


# ==========================================
# Inlines
# ==========================================

class LocationInline(admin.TabularInline):
    model = Location
    extra = 0
    fields = ('name', 'type', 'level', 'max_players')
    readonly_fields = ('last_event',)
    show_change_link = True


class PlayerInline(admin.TabularInline):
    model = Player
    extra = 0
    fields = ('name', 'health', 'level')
    readonly_fields = ('name', 'health', 'level')
    verbose_name = "Player in Event"
    show_change_link = True


class EnemyInline(admin.TabularInline):
    model = Enemy
    extra = 0
    fields = ('name', 'health', 'level')
    readonly_fields = ('name', 'health', 'level')
    verbose_name = "Enemy in Event"
    show_change_link = True


# ==========================================
# Model Admins
# ==========================================

@admin.register(World)
class WorldAdmin(admin.ModelAdmin):
    list_display = ('name', 'public_id', 'start_location')
    readonly_fields = ('public_id',)
    raw_id_fields = ('start_location',)
    search_fields = ('name', 'public_id')


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'biome', 'level', 'world')
    list_filter = ('world', 'biome')
    raw_id_fields = ('world',)
    readonly_fields = ('public_id',)
    search_fields = ('name', 'public_id')
    inlines = [LocationInline]


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'level', 'region', 'max_players')
    list_filter = ('type', 'level', 'region__world')
    raw_id_fields = ('region',)
    readonly_fields = ('public_id',)
    search_fields = ('name', 'public_id')


@admin.register(Town)
class TownAdmin(LocationAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(type='T')


@admin.register(Dungeon)
class DungeonAdmin(LocationAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(type='D')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'active', 'size', 'last_update_fmt')
    list_filter = ('active', 'location__region')
    raw_id_fields = ('location',)
    readonly_fields = ('public_id', 'last_update')

    inlines = [PlayerInline, EnemyInline]

    def last_update_fmt(self, obj):
        return datetime.fromtimestamp(obj.last_update).strftime('%H:%M:%S') if obj.last_update else "-"

    last_update_fmt.short_description = "Last Update"


@admin.register(EnemyTemplate)
class EnemyTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'location')
    list_filter = ('level', 'location__region')
    raw_id_fields = ('location',)
    search_fields = ('name',)


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'level', 'health')
    list_filter = ('type', 'level')
    raw_id_fields = ('target',)
    readonly_fields = ('public_id',)
    search_fields = ('name', 'public_id')


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'level', 'location', 'event')
    list_filter = ('level', 'new_location', 'new_event')
    raw_id_fields = ('owner', 'active', 'location', 'event', 'target')
    readonly_fields = ('public_id',)
    search_fields = ('name', 'public_id', 'owner__username')

    fieldsets = (
        ('Identity', {'fields': ('public_id', 'name', 'owner', 'active')}),
        ('State', {'fields': ('location', 'event', 'target', 'position')}),
        ('Flags', {'fields': ('new_status', 'new_location', 'new_event')}),
        ('Stats', {'fields': (('level', 'health', 'max_health'), ('attack_damage', 'attack_range', 'speed'))}),
    )


@admin.register(Enemy)
class EnemyAdmin(admin.ModelAdmin):
    list_display = ('name', 'template', 'level', 'event')
    list_filter = ('level', 'new_event')
    raw_id_fields = ('template', 'event', 'target')
    readonly_fields = ('public_id',)
    search_fields = ('name', 'public_id')


@admin.register(RegionChatMessage)
class RegionChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'region', 'message_preview', 'sent_at_fmt')
    raw_id_fields = ('user', 'region')
    readonly_fields = ('sent_at',)
    ordering = ('-sent_at',)

    def message_preview(self, obj):
        return obj.message[:50]

    def sent_at_fmt(self, obj):
        return datetime.fromtimestamp(obj.sent_at).strftime('%Y-%m-%d %H:%M:%S')