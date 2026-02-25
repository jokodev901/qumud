import random
import time
import math

from django.db import transaction
from django.db.models import Prefetch, Count, Q

from world.models import Event, Player, Enemy, EventLog, PlayerLog, Location, Entity
from core.utils import utils


def get_or_create_event(location: Location) -> Event | None:
    # We want to overflow players into the same events vs race-creating individual events
    # select_for_update() on the location row as a transaction to ensure only one event created
    # at a time

    with transaction.atomic():
        # Find existing events with less than player_limit number of players
        prefetch_list = []

        player_count = Count("entity", filter=Q(entity__type='P'))
        event_prefetch = Prefetch('event_set',
                                  queryset=Event.objects.all()
                                  .annotate(player_count=player_count)
                                  .filter(player_count__lt=location.max_players, ended=0))
        prefetch_list.append(event_prefetch)

        if location.type == 'D':
            prefetch_list.append(Prefetch('enemytemplate_set'))

        location_locked = (Location.objects.select_for_update()
                           .prefetch_related(*prefetch_list)
                           .get(id=location.id))

        events = location_locked.event_set.all()

        if events:
            # Just picking first available here
            # Consider ordering or some other rank
            event = events[0]

        else:
            if location_locked.type == 'T':
                event = Event.objects.create(location=location, last_update=time.time())

            elif location_locked.type == 'D':
                delta = time.time() - location_locked.last_event
                ticks = math.floor(delta)

                if ticks < location_locked.spawn_rate:
                    return None

                eventlogs = []
                event = Event.objects.create(location=location, last_update=time.time())

                e_temps = location.enemytemplate_set.all()
                e_positions = []

                # Just spawn one of each enemy type for now
                for enemy in e_temps:
                    position = 55 + enemy.initiative
                    left = utils.clamp(((position / event.size) * 100), 5, 95)
                    pos_round = 5 * round(left / 5)
                    e_positions.append(pos_round)
                    pos_count = e_positions.count(pos_round)
                    flip = 1

                    if pos_count % 2 == 0:
                        flip = -1

                    top = utils.clamp(50 + (math.floor(pos_count / 2) * 10 * flip), 5, 95)

                    e = Enemy.objects.create(svg=enemy.svg, event=event, event_joined=time.time(), name=enemy.name,
                                             max_health=enemy.max_health, health=enemy.max_health,
                                             attack_range=enemy.attack_range, attack_damage=enemy.attack_damage,
                                             speed=enemy.speed, initiative=enemy.initiative, max_targets=1,
                                             level=1, position=position, left=left, top=top)

                    eventlogs.append(
                        EventLog(event=event,
                                 htclass='text-warning log-entry',
                                 log=f'Encountered lvl {e.level} {e.name}!')
                    )

                EventLog.objects.bulk_create(eventlogs)

    return event


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
                                   .filter(dead=None)
                                   .order_by('-initiative'), to_attr='entities')

        try:
            event_lock = (Event.objects.select_for_update()
                          .prefetch_related(entity_prefetch)
                          .select_related('location__region')
                          .get(pk=event.id))

        except Event.DoesNotExist:
            return None

        # fetch backlog regardless of update timing
        event_logs = (EventLog.objects.all()
                      .filter(created_at__gte=player.owner.last_refresh, event=event_lock)
                      .order_by('-created_at'))

        player_count = 0
        enemy_count = 0

        for entity in event_lock.entities:
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
            newlogs = []
            killed_entities = []

            for tick in range(ticks):
                e_positions = []
                p_positions = []

                for entity in event_lock.entities[:]:
                    if entity.type == 'E':
                        dmg = random.choice(range(1,5))
                        entity.health -= dmg

                        newlogs.append(
                            EventLog(event=event_lock,
                                     htclass='text-danger log-entry',
                                     log=f'{entity.name} took {dmg} damage')
                        )

                    elif entity.type == 'P':
                        entity.health -= 1

                        newlogs.append(
                            EventLog(event=event_lock,
                                     htclass='text-danger log-entry',
                                     log=f'{entity.name} took 1 damage')
                        )

                    if entity.health < 1:
                        newlogs.append(
                            EventLog(event=event_lock,
                                     htclass='text-primary log-entry',
                                     log=f'{entity.name} is dead')
                        )

                        if entity.type == 'P':
                            player_count -= 1

                            # Send player to town and heal them
                            # this is where death penalties would be processed
                            entity.health = entity.max_health
                            town = Location.objects.filter(region=event_lock.location.region, type='T').first()
                            Player.objects.filter(id=entity.id).update(last_travel=time.time(),
                                                                       location=town,
                                                                       health=entity.max_health,
                                                                       event=None)

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