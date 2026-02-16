import random
import time
import math

from django.db import transaction
from django.db.models import Prefetch

from world.models import Event, Player, Enemy, EventLog, PlayerLog, Location


def clamp(n, minn, maxn):
    return max(min(maxn, n), minn)


def process_town_event(player: Player, event: Event, full: bool) -> dict | None:
    # Placeholder town event processing
    players = Player.objects.all().filter(event=event).exclude(pk=player.id)

    return {'log': [], 'players': players, 'enemies': []}


def process_dungeon_event(player: Player, event: Event, full: bool) -> dict | None:
    ticks = math.floor(time.time() - event.last_update)

    # fetch backlog regardless of update timing
    event_logs = (EventLog.objects.all().
               filter(created_at__gte=player.owner.last_refresh, event=event).
               order_by('-created_at'))

    with transaction.atomic():
        player_prefetch = Prefetch('player_set',
                                   Player.objects.all().filter(active__isnull=False), to_attr='players')
        enemy_prefetch = Prefetch('enemy_set',
                                  Enemy.objects.all().filter(dead__isnull=True), to_attr='enemies')

        try:
            event_lock = (Event.objects.select_for_update()
                          .prefetch_related(player_prefetch, enemy_prefetch)
                          .get(pk=event.id))

        except Event.DoesNotExist:
            return None

        newlogs = []

        # Consider event paused while inactive (due to no players present)
        # Resume with fresh update time when a player joins again
        if not event_lock.active:
            Event.objects.filter(pk=event_lock.pk).update(last_update=time.time(), active=True)
            ticks = 0

        # If no enemies are left then event is over, update location last_event and delete
        if not event_lock.enemies:
            Location.objects.filter(pk=event_lock.location_id).update(last_event=time.time())
            Enemy.objects.filter(event=event_lock).delete()
            Event.objects.filter(pk=event_lock.pk).delete()

            return {'log': event_logs, 'players': None, 'enemies': None}

        # player_logs = {player.id: [] for player in event_lock.players}
        killed_enemies = []
        dead_players = []

        if ticks > 0:
            for tick in range(ticks):
                for enemy in event_lock.enemies[:]:
                    dmg = random.choice(range(3))
                    enemy.health -= dmg

                    newlogs.append(
                        EventLog(event=event_lock,
                                 htclass='text-danger',
                                 log=f'{enemy.name} took {dmg} damage')
                    )

                    if enemy.health < 1:
                        newlogs.append(
                            EventLog(event=event_lock,
                                     htclass='text-primary',
                                     log=f'{enemy.name} is dead')
                        )
                        enemy.dead = time.time()
                        event_lock.enemies.remove(enemy)
                        killed_enemies.append(enemy)
                        continue

                    enemy.position = (enemy.position + random.choice((-3, -2, -1, 0, 1, 2, 3))) % event_lock.size
                    enemy.left = clamp(((enemy.position / event_lock.size) * 100), 5, 95)

                if not event_lock.enemies:
                    # All enemies are dead, log it and stop processing ticks
                    newlogs.append(
                        EventLog(event=event_lock,
                                 htclass='text-success',
                                 log=f'All enemies defeated!')
                    )
                    break

            # Process event logs
            if newlogs:
                EventLog.objects.bulk_create(newlogs)

            event_lock.last_update = time.time() - (time.time() % event_lock.last_update)
            event_lock.save(update_fields=['last_update'])
            Enemy.objects.bulk_update(killed_enemies + event_lock.enemies, ['health', 'dead', 'position', 'left'])

    return {'log': event_logs, 'players': event_lock.players, 'enemies': event_lock.enemies + killed_enemies}