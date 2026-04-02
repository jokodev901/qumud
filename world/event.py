import random
import time
import math
from typing import Any

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

        player_count = Count("entity", filter=Q(entity__type='P', active__isnull=False))
        event_prefetch = Prefetch('event_set',
                                  queryset=Event.objects.all()
                                  .annotate(player_count=player_count)
                                  .filter(player_count__lt=location.max_players, ended__isnull=True))
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

                # Spawn 2-5 enemies of any combination from the template set
                num_enemy = random.choice(range(2, 6))
                templates = random.choices(e_temps, k=num_enemy)

                for enemy in templates:
                    position = 55 + enemy.initiative
                    left = utils.clamp(((position / event.size) * 100), 5, 95)
                    pos_round = 5 * round(left / 5)
                    e_positions.append(pos_round)
                    pos_count = e_positions.count(pos_round)

                    # Alternate vertical position of close enemies above and below
                    flip = 1
                    if pos_count % 2 == 0:
                        flip = -1

                    top = utils.clamp(50 + (math.floor(pos_count / 2) * 10 * flip), 5, 95)

                    e = Enemy.objects.create(event=event,
                                             event_joined=time.time(),
                                             position=position,
                                             left=left,
                                             top=top,
                                             svg=enemy.svg,
                                             name=enemy.name,
                                             health=enemy.max_health,
                                             max_health=enemy.max_health,
                                             attack_range=enemy.attack_range,
                                             min_damage=enemy.min_damage,
                                             max_damage=enemy.max_damage,
                                             speed=enemy.speed,
                                             initiative=enemy.initiative,
                                             max_targets=enemy.max_targets,
                                             level=enemy.level,
                                             award_xp=enemy.award_xp)

                    eventlogs.append(
                        EventLog(event=event,
                                 htclass='text-warning log-entry',
                                 log=f'Encountered lvl {e.level} {e.name}!')
                    )

                EventLog.objects.bulk_create(eventlogs)

    return event


def process_ticks(enemy_count: int, event_lock: Event, killed_entities: list[Any], newlogs: list[Any], player: Player,
                  player_count: int, player_logs: list[Any], ticks: int | Any):

    # DEBUG
    player_logs.append(
        PlayerLog(player=player,
                  htclass='text-white',
                  log=f'Processing {ticks} ticks...')
    )

    for tick in range(ticks):
        e_positions = []
        p_positions = []

        for entity in event_lock.entities[:]:
            if entity.type == 'E':
                # Entity combat logic goes here
                dmg = random.choice(range(1, 5))
                entity.health -= dmg

                newlogs.append(
                    EventLog(event=event_lock,
                             htclass='text-danger log-entry',
                             log=f'{entity.name} took {dmg} damage')
                )

            elif entity.type == 'P':
                # Entity combat logic goes here
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
                    player_logs.append(
                        PlayerLog(player=player,
                                  htclass='text-danger',
                                  log=f'YOU DIED')
                    )
                    player_logs.append(
                        PlayerLog(player=player,
                                  htclass='text-white',
                                  log=f'Respawning in town...')
                    )

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
                    players = Player.objects.filter(event=event_lock, active__isnull=False)

                    for player in players:
                        player.add_xp(entity.enemy.award_xp)

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
            player_logs.append(
                PlayerLog(player=player,
                          htclass='text-success',
                          log=f'Won battle at {event_lock.location}!')
            )

            break

        if player_count == 0:
            event_lock.active = False
            pass


def process_town_event(player: Player, event: Event, full: bool, joined: bool) -> dict | None:
    players = Player.objects.all().filter(event=event, active__isnull=False, owner__last_refresh__gte=time.time() - 600)
    player_positions = []

    if joined:
        for p in players:
            if p.id == player.id:
                position = 50 + random.choice(range(-10, 10))
                p.position = position
            else:
                position = p.position

            pos_round = 5 * round(position / 5)
            player_positions.append(pos_round)
            pos_count = player_positions.count(pos_round)

            flip = 1
            if pos_count % 2 == 0:
                flip = -1

            p.top = utils.clamp(50 + (math.floor(pos_count / 2) * 10 * flip), 5, 95)
            p.left = pos_round

        Player.objects.bulk_update(players, ['position', 'left', 'top'])

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
        player_logs = []

        # DEBUG
        player_logs.append(
            PlayerLog(player=player,
                      htclass='text-white',
                      log=f'Event last update delta: {delta}')
        )

        player_count = 0
        enemy_count = 0

        for entity in event_lock.entities:
            if entity.type == 'P':
                player_count += 1
            elif entity.type == 'E':
                enemy_count += 1

        # Consider event paused while inactive (due to no players present)
        # Resume with fresh update time when a player joins again
        if not event_lock.active:
            event_lock.active = True
            event_lock.last_update = time.time()
            ticks = 0
            event_lock.save(update_fields=['last_update', 'active'])

        # If no enemies are left then event is over, update location last_event and set ended
        if enemy_count == 0:
            Location.objects.filter(pk=event_lock.location_id).update(last_event=time.time())
            Event.objects.filter(pk=event_lock.pk).update(ended=time.time())
            Player.objects.filter(pk=player.pk).update(event=None, event_joined=0)

            return {'log': event_logs, 'entities': []}

        if ticks > 0:
            newlogs = []
            killed_entities = []

            process_ticks(enemy_count, event_lock, killed_entities, newlogs, player, player_count, player_logs, ticks)

            # Process event logs
            if newlogs:
                EventLog.objects.bulk_create(newlogs)
                event_logs = (EventLog.objects.all()
                              .filter(created_at__gte=player.owner.last_refresh, event=event)
                              .order_by('-created_at'))

            event_lock.last_update = time.time() - offset

            if debug:
                event_lock.last_update = time.time()

            Entity.objects.bulk_update(killed_entities + event_lock.entities,
                                       ['health', 'dead', 'position', 'left', 'top'])
            event_lock.save(update_fields=['last_update', 'active'])

        if player_logs:
            PlayerLog.objects.bulk_create(player_logs)

    return {'log': event_logs, 'entities': event_lock.entities}