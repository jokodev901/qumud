import random
import time
import math

from django.db import transaction
from django.db.models import Prefetch

from world.models import Event, Player, Enemy, EventLog, PlayerLog, Location


def process_town_event(player: Player, event: Event, full: bool) -> dict | None:
    # Placeholder town event processing
    players = Player.objects.all().filter(event=event).exclude(pk=player.id)

    return {'log': [], 'players': players, 'enemies': []}


def process_dungeon_event(player: Player, event: Event, full: bool) -> dict | None:
    ticks = math.floor(time.time() - event.last_update)

    # fetch backlog regardless of update timing
    backlogs = (EventLog.objects.all().
               values_list('log', flat=True).
               filter(timestamp__gte=player.owner.last_refresh).
               order_by('-timestamp'))

    backlog = [item for log in backlogs for item in log]

    # Process if we have at least one tick
    if ticks > 0:
        with transaction.atomic():
            player_prefetch = Prefetch('player_set',
                                       Player.objects.all().filter(active__isnull=False), to_attr='players')
            enemy_prefetch = Prefetch('enemy_set',
                                      Enemy.objects.all().select_related('template')
                                      .filter(active=True), to_attr='enemies')
            try:
                event_lock = (Event.objects.select_for_update()
                              .prefetch_related(player_prefetch, enemy_prefetch)
                              .get(pk=event.id))

            except Event.DoesNotExist:
                return None

            newlog = []

            # Consider event paused while inactive (due to no players present)
            # Resume with fresh update time when a player joins again
            if not event_lock.active:
                event_lock.active = True
                event_lock.last_update = time.time()
                ticks = 0
                event_lock.save(update_fields=['active', 'last_update'])

            # If no enemies are left then event is over, update location last_event and delete
            if not event_lock.enemies:
                try:
                    location = Location.objects.get(pk=event_lock.location_id)
                    location.last_event = time.time()
                    location.save(update_fields=['last_event'])
                except Location.DoesNotExist:
                    pass
                event_lock.delete()
                return {'log': backlog, 'players': None, 'enemies': None}

            player_logs = {player.id: [] for player in event_lock.players}
            dead_enemies = []
            dead_players = []

            for tick in range(ticks):
                for enemy in event_lock.enemies[:]:
                    if enemy.active:
                        dmg = random.choice(range(3))
                        enemy.health -= dmg
                        newlog.append(f'{enemy.name} took {dmg} damage')

                        if enemy.health < 1:
                            newlog.append(f'{enemy.name} is dead')
                            enemy.active = False
                            event_lock.enemies.remove(enemy)
                            dead_enemies.append(enemy)

                if not event_lock.enemies:
                    # All enemies are dead, log it and stop processing ticks
                    newlog.append('All enemies defeated')
                    break

            # Process event logs
            newlog.reverse()
            eventlog = newlog + backlog
            if newlog:
                EventLog.objects.create(event=event_lock, log=newlog)

            event_lock.last_update = time.time()
            event_lock.save(update_fields=['last_update'])
            Enemy.objects.bulk_update(dead_enemies + event_lock.enemies, ['health', 'active'])

            return {'log': eventlog, 'players': event_lock.players, 'enemies': event_lock.enemies}

    return {'log': backlog}