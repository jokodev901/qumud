from django.contrib import admin
from .models import World, Region, Location, Event, Entity


# Inlines
class RegionInline(admin.TabularInline):
    model = Region
    extra = 1
    show_change_link = True


class LocationInline(admin.TabularInline):
    model = Location
    extra = 1
    show_change_link = True


class EntityInline(admin.TabularInline):
    model = Entity
    extra = 0
    fields = ('name', 'entity_type', 'health', 'position')


# Models
@admin.register(World)
class WorldAdmin(admin.ModelAdmin):
    list_display = ('name', 'public_id')
    search_fields = ('name',)
    inlines = [RegionInline]


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'biome', 'world', 'public_id')
    list_filter = ('biome', 'world')
    search_fields = ('name',)
    inlines = [LocationInline]


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'location_type', 'region', 'get_world')
    list_filter = ('location_type', 'region__world', 'region')
    search_fields = ('name',)

    @admin.display(description='World')
    def get_world(self, obj):
        return obj.region.world


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('location', 'active', 'size', 'last_update', 'public_id')
    list_filter = ('active', 'location__region__world')
    readonly_fields = ('last_update', 'public_id')
    inlines = [EntityInline]


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    # Organizes the detail view into logical blocks
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'entity_type', 'public_id')
        }),
        ('Stats', {
            'fields': (('health', 'max_health'), ('attack_damage', 'attack_range'), 'speed', 'initiative')
        }),
        ('Combat & Location', {
            'fields': ('position', 'target', 'event', 'location', 'player')
        }),
    )

    list_display = ('name', 'entity_type', 'health', 'location', 'event', 'player')
    list_filter = ('entity_type', 'location', 'event__active')
    search_fields = ('name', 'player__alias')  # Assumes Player has an alias field
    readonly_fields = ('public_id',)
    raw_id_fields = ('target', 'player', 'event')  # Better for large datasets than dropdowns