import random
import time
import math

from django.db import transaction
from django.db.models import Prefetch

from world.models import Event, Player, Enemy, EventLog, PlayerLog, Location, Entity
from core.utils import utils


def process_town_event(player: Player, event: Event, full: bool) -> dict | None:
    # Placeholder town event processing
    players = Player.objects.all().filter(event=event).exclude(pk=player.id)

    return {'log': [], 'entities': players}


def process_dungeon_event(player: Player, event: Event, full: bool, debug: bool = False) -> dict | None:
    delta = time.time() - event.last_update
    ticks = math.floor(delta)
    offset = delta - ticks

    if debug:
        ticks = 1

    with transaction.atomic():
        entity_prefetch = Prefetch('entity_set',
                                   Entity.objects.all()
                                   .order_by('-initiative'), to_attr='entities')

        try:
            event_lock = (Event.objects.select_for_update()
                          .prefetch_related(entity_prefetch)
                          .get(pk=event.id))

        except Event.DoesNotExist:
            return None

        # fetch backlog regardless of update timing
        event_logs = (EventLog.objects.all()
                      .filter(created_at__gte=player.owner.last_refresh, event=event)
                      .order_by('-created_at'))

        player_count = 0
        enemy_count = 0
        newlogs = []
        killed_entities = []

        for entity in event_lock.entities:
            if not entity.dead:
                if entity.type == 'P':
                    player_count += 1
                elif entity.type == 'E':
                    enemy_count += 1

        # Consider event paused while inactive (due to no players present)
        # Resume with fresh update time when a player joins again
        if not event_lock.active and enemy_count > 0:
            Event.objects.filter(pk=event_lock.pk).update(last_update=time.time(), active=True)
            ticks = 0

        # If no enemies are left then event is over, update location last_event and set ended
        if enemy_count == 0:
            Location.objects.filter(pk=event_lock.location_id).update(last_event=time.time())
            Event.objects.filter(pk=event_lock.pk).update(ended=time.time(), active=False)
            Player.objects.filter(pk=player.pk).update(event=None, event_joined=0)

            return {'log': event_logs, 'entities': []}

        # player_logs = {player.id: [] for player in event_lock.players}

        if ticks > 0:
            for tick in range(ticks):
                e_positions = []
                p_positions = []

                for entity in event_lock.entities[:]:
                    if entity.dead:
                        continue

                    if entity.type == 'E':
                        dmg = random.choice(range(1,5))
                        entity.health -= dmg

                        newlogs.append(
                            EventLog(event=event_lock,
                                     htclass='text-danger log-entry',
                                     log=f'{entity.name} took {dmg} damage')
                        )

                    if entity.health < 1:
                        newlogs.append(
                            EventLog(event=event_lock,
                                     htclass='text-primary log-entry',
                                     log=f'{entity.name} is dead')
                        )

                        if entity.type == 'P':
                            player_count -= 1
                        elif entity.type == 'E':
                            enemy_count -= 1

                        entity.dead = time.time()
                        killed_entities.append(entity)
                        event_lock.entities.remove(entity)

                        continue

                    entity.position = (entity.position + random.choice((-3, -2, -1, 0, 1, 2, 3))) % event_lock.size
                    entity.left = utils.clamp(((entity.position / event_lock.size) * 100), 5, 95)

                    pos_round = 5 * round(entity.left / 5)

                    if entity.type == 'P':
                        p_positions.append(pos_round)
                        pos_count = p_positions.count(pos_round)

                    elif entity.type == 'E':
                        e_positions.append(pos_round)
                        pos_count = e_positions.count(pos_round)

                    flip = 1

                    if pos_count % 2 == 0:
                        flip = -1

                    entity.top = utils.clamp(50 + (math.floor(pos_count / 2) * 15 * flip), 5, 95)

                if enemy_count == 0:
                    # All enemies are dead, log it and stop processing ticks
                    newlogs.append(
                        EventLog(event=event_lock,
                                 htclass='text-success log-entry',
                                 log=f'All enemies defeated!')
                    )
                    break

                elif player_count == 0:
                    event_lock.active = False
                    pass

            # Process event logs
            if newlogs:
                EventLog.objects.bulk_create(newlogs)
                event_logs = (EventLog.objects.all()
                              .filter(created_at__gte=player.owner.last_refresh, event=event)
                              .order_by('-created_at'))

            event_lock.last_update = time.time() - offset

            if debug:
                event_lock.last_update = time.time()

            event_lock.save(update_fields=['last_update', 'active'])
            Entity.objects.bulk_update(killed_entities + event_lock.entities,
                                       ['health', 'dead', 'position', 'left', 'top'])

    return {'log': event_logs, 'entities': event_lock.entities}