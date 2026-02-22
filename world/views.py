import json
import time
import re
import math

from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, reverse
from django.http import HttpResponse
from django.db.models import Prefetch, Count, Q
from django.db import transaction

from django.utils.html import strip_tags
from django.template import engines
from django.template.loader import render_to_string

from rest_framework.authtoken.models import Token

from core.utils import generators, utils
from authentication.models import User
from .models import (World, Region, Location, RegionChatMessage, Player, Enemy, EnemyTemplate,
                     Event, EventLog)
from .forms import CharacterCreationForm, WorldCreationForm
from .event import process_dungeon_event, process_town_event


class BaseView(View):
    def prep_user(self, related: list = ()) -> User | None:
        '''
        Avoids duplicate user queries each time authentication is checked and prepares related data
        '''

        # Extract user id from session data
        user_id = self.request.session.get('_auth_user_id')

        if not user_id:
            return None

        user = (
            User.objects
            .select_related(*related)
            .get(id=user_id)
        )

        return user

    def prep_player(self, related: list = ()) -> Player | None:
        '''
        Avoids duplicate user queries each time authentication is checked and prepares related data
        '''

        # Extract user id from session data
        user_id = self.request.session.get('_auth_user_id')

        if not user_id:
            return None

        try:
            player = (
                Player.objects
                .select_related(*related)
                .get(active_id=user_id)
            )
        except Player.DoesNotExist:
            return None

        return player

    @staticmethod
    def clean_text(text: str) -> str:
        cleaned = strip_tags(text)
        cleaned = cleaned.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        cleaned = re.sub(' +', ' ', cleaned)

        return cleaned.strip()

    @staticmethod
    def get_region_messages(player: Player, count: int = 50, full: bool = False):
        """
        we have to select either way, so lets get our ordered candidate messages, but only return them
        if the latest one has a sent_at >= user.last_refresh
        """

        messages = (RegionChatMessage.objects.all()
                    .select_related('user')
                    .filter(region=player.location.region, created_at__gte=time.time()-600)
                    .order_by('-created_at'))[:count]

        if messages:
            if (messages[0].created_at >= player.owner.last_refresh) or full:
                return messages

        return None

    @staticmethod
    def get_region_players(region: Region, timeout: int = 10):
        players = (User.objects.all()
                   .filter(player__location__region=region, last_refresh__gte=(time.time() - timeout))
                   .order_by('alias'))

        return players

    @staticmethod
    def get_travel_data(player: Player) -> dict:
        context = {}
        current_location = player.location
        region = current_location.region
        world = region.world

        locations = Location.objects.all().filter(region=region).order_by('level', 'id')
        towns = [location for location in locations if location.type == 'T']
        dungeons = [location for location in locations if location.type == 'D']

        context['towns'] = towns
        context['dungeons'] = dungeons
        context['region'] = region
        context['current_location'] = current_location
        context['world'] = world

        return context

    @staticmethod
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
                # No suitable event found, so create a new one
                delta = time.time() - location.last_event
                ticks = math.floor(delta)

                # Doing a fixed 5-second interval between events for now
                # could make this variable or have ways to force an event
                if location.type == 'D':
                    if ticks < location.spawn_rate:
                        return None

                eventlogs = []
                event = Event.objects.create(location=location, last_update=time.time())

                if location.type == 'D':
                    etemps = location.enemytemplate_set.all()
                    e_positions = []

                    # Just spawn one of each enemy type for now
                    for enemy in etemps:
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

    @staticmethod
    def get_event_data(player: Player, full: bool = False) -> tuple[dict, bool]:
        event_data = {'log': [{'log': 'Exploring...', 'htclass': 'text-white log-entry'}], 'entities': None}
        event = player.event
        location = player.location
        joined = False

        # If player is not already in an event, try to put them in one
        if not player.event:
            event = BaseView.get_or_create_event(location)

            if event:
                player.event = event
                player.position = 40
                player.event_joined = time.time()
                player.save(update_fields=['event', 'position', 'event_joined'])

                joined = True

        if location.type == 'D' and event:
            event_data = process_dungeon_event(player, event, full)

        if location.type == 'T' and event:
            event_data = process_town_event(player, event, full)

        return event_data, joined


class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        token = Token.objects.filter(user=self.request.user).first()

        context['api_key'] = token.key if token else None

        return context

    def post(self, request, *args, **kwargs):
        if "generate_token" in request.POST:
            Token.objects.filter(user=request.user).delete()
            Token.objects.create(user=request.user)

        return redirect('profile')


class SelectCharacter(BaseView):
    def post(self, request):
        user = self.prep_user()
        if not user:
            return redirect('login')

        selected = request.POST.get('selected_id')
        character = Player.objects.select_related('owner').only('owner__id').get(public_id=selected)

        if character:
            if character.owner == user:
                with transaction.atomic():
                    try:
                        current_char = Player.objects.get(active=user)
                    except Player.DoesNotExist:
                        current_char = None

                    if current_char:
                        current_char.active = None
                        current_char.save(update_fields=['active'])

                    character.active = user
                    character.save(update_fields=['active'])

                if request.headers.get('HX-Request'):
                    location_data = {
                        "path": reverse('world'),
                        "target": "#main-content",
                        "swap": "innerHTML"
                    }
                    response = HttpResponse(status=204)
                    response['HX-Location'] = json.dumps(location_data)
                    return response

        return HttpResponse('Invalid selection', status=400)


class GetPlayerCharacters(BaseView):
    template_name = 'player_characters.html'

    def get(self, request):
        user = self.prep_user()
        if not user:
            return redirect('login')

        characters = Player.objects.filter(owner=user).order_by('id')
        context = {'characters': characters}

        return render(request, self.template_name, context)


class CreateCharacter(BaseView):
    template_name = 'create_character.html'

    def get(self, request):
        user = self.prep_user()
        if not user:
            return redirect('login')

        form = CharacterCreationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        user = self.prep_user()
        if not user:
            return redirect('login')

        form = CharacterCreationForm(request.POST)

        if form.is_valid():
            player = form.save(commit=False)
            player.owner = user
            player.health = player.max_health

            player.save()

            if request.headers.get('HX-Request'):
                location_data = {
                    "path": reverse('home'),
                    "target": "#main-content",
                    "swap": "innerHTML"
                }

                response = HttpResponse(status=204)
                response['HX-Location'] = json.dumps(location_data)
                return response

            return redirect('home')

        return render(request, self.template_name, {'form': form})


class SelectWorld(BaseView):
    template_name = 'world.html'

    def get(self, request):
        player = self.prep_player(['location__region__world'])

        if not player:
            return redirect('home')

        form = WorldCreationForm()
        world_name = None

        if player.location:
            world_name = player.location.region.world.name

        return render(request, self.template_name, {'world': world_name, 'form': form})

    def post(self, request):
        player = self.prep_player(['location'])
        if not player:
            return redirect('login')

        form = WorldCreationForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                world_form = form.save(commit=False)
                world, created = World.objects.get_or_create(
                    name=world_form.name
                )

                if created:
                    # For a new world, create the starting Region and locations
                    region_data = generators.generate_region(seed=world.name, level=1)
                    region = Region(name=region_data['name'], biome=region_data['biome'], world=world)
                    region.save()

                    for town in region_data['locations']['towns']:
                        t = Location.objects.create(name=town['name'], level=town['level'], region=region,
                                                    type='T', spawn_rate=None, max_players=100)

                        world.start_location = t

                    for dungeon in region_data['locations']['dungeons']:
                        d = Location.objects.create(name=dungeon['name'], level=dungeon['level'], region=region,
                                                    type='D', spawn_rate=5, max_players=3)

                        enemy_temps = generators.generate_enemies(seed=dungeon['name'], level=dungeon['level'],
                                                                  biome=region_data['biome'], count=5)

                        for enemy in enemy_temps:
                            EnemyTemplate.objects.create(location=d, name=enemy['name'], svg=enemy['svg'],
                                                         max_health=enemy['max_health'])

                    world.save()

                player.location = world.start_location
                player.save(update_fields=['location'])

            if request.headers.get('HX-Request'):
                response = HttpResponse(status=204)

                location_data = {
                    "path": reverse('map'),
                    "target": "#main-content",
                    "swap": "innerHTML"
                }

                response['HX-Location'] = json.dumps(location_data)
                return response

        return render(request, self.template_name, {'form': form})


class Map(BaseView):
    template_name = 'map.html'

    def render_partials(self, request, partials, str_partials, headers, context):
        """
        Takes a list of template paths OR raw strings and returns a combined HttpResponse.
        """
        django_engine = engines['django']
        html_parts = []

        for partial in partials:
            html_parts.append(render_to_string(partial, context, request=request))

        for partial in str_partials:
            template_obj = django_engine.from_string(partial)
            html_parts.append(template_obj.render(context, request=request))

        return HttpResponse("".join(html_parts), headers=headers)

    def get(self, request):
        player = self.prep_player(['location__region__world', 'event', 'owner'])

        if not player:
            return redirect('login')

        context = {}
        player_updates = []

        try:
            # Render partials (update trigger)
            if request.GET.get('trigger', None) == 'update':
                partials = []
                str_partials = []
                living_svgs = []
                headers = {}
                recent_messages = self.get_region_messages(player=player)
                region_players = self.get_region_players(region=player.location.region)
                event_data, event_joined = self.get_event_data(player=player)

                if player.new_status:
                    context['character'] = player
                    context['character_health_perc'] = player.health_perc
                    partials.append('partials/status.html')

                if recent_messages:
                    context['messages'] = recent_messages
                    partials.append('partials/region_chat.html')

                if region_players:
                    context['region_players'] = region_players
                    partials.append('partials/region_players.html')

                if event_data:
                    context['event'] = event_data

                    # Full response
                    if event_joined:
                        partials.append('partials/event.html')

                    # Partial updates for logs, movement, death animations, rendering svgs for newly-joined entities
                    else:
                        trigger_data = {}

                        if event_data['entities']:
                            move_data = {'moveIds': [{'id': f'svg-{entity.public_id}', 'top': entity.top, 'left': entity.left}
                                                    for entity in event_data['entities']]}
                            trigger_data['triggerMove'] = move_data
                            new_svgs = [entity.render_svg for entity in event_data['entities']
                                        if entity.event_joined >= player.owner.last_refresh]

                            if new_svgs:
                                svg_partial = f"""
                                     <div id="event-window-swap"                                              
                                          hx-swap-oob="afterbegin">
                                          {''.join(new_svgs)}
                                     </div>
                                """
                                str_partials.append(svg_partial)

                            living_svgs = {'activeIds':
                                               [f"svg-{entity.public_id}" for entity in event_data['entities']]}

                        trigger_data['triggerDefeatAnimation'] = living_svgs
                        headers['HX-Trigger'] = json.dumps(trigger_data)

                        log_partial = """
                            <div id="event-log-swap"
                                 hx-swap-oob="afterbegin">
                                {% for log in event.log %}
                                <div class="log-wrapper">
                                    <div class="log-content">
                                        <div class="{{ log.htclass }}">{{ log.log }}</div>
                                    </div>
                                </div>
                                {% endfor %}
                            </div>
                        """
                        str_partials.append(log_partial)

                if player.new_location:
                    player.new_location = False
                    player_updates.append('new_location')

                if player.new_status:
                    player.new_status = False
                    player_updates.append('new_status')

                if player_updates:
                    with transaction.atomic():
                        player.save(update_fields=player_updates)

                player.owner.last_refresh = time.time()
                player.owner.save(update_fields=['last_refresh'])

                if partials:
                    return self.render_partials(request, partials, str_partials, headers, context)

                return HttpResponse(status=204, headers=headers)

            # Render full template ( initial load )
            else:
                recent_messages = self.get_region_messages(player=player, full=True)
                region_players = self.get_region_players(region=player.location.region)
                context['travel'] = self.get_travel_data(player=player)
                context['event'], _ = self.get_event_data(player=player, full=True)
                context['region_players'] = region_players
                context['messages'] = recent_messages
                context['character'] = player
                context['character_health_perc'] = player.health_perc

                if player.new_location:
                    player.new_location = False
                    player_updates.append('new_location')

                if player.new_status:
                    player.new_status = False
                    player_updates.append('new_status')

                if player_updates:
                    with transaction.atomic():
                        player.save(update_fields=player_updates)

                player.owner.last_refresh = time.time()
                player.owner.save(update_fields=['last_refresh'])

                return render(request, self.template_name, context)

        except SyntaxError:
            return redirect('home')


class Travel(BaseView):
    template = 'partials/travel.html'

    def post(self, request):
        player = self.prep_player(['location__region',
                                   'event',])
        if not player:
            return redirect('login')

        context = {}
        update_fields = []

        selected_location = (Location.objects.select_related('region')
                             .get(public_id=request.POST['public_id']))

        if selected_location != player.location:
            if selected_location.region == player.location.region:
                with transaction.atomic():
                    # Remove event since we have left the location
                    if player.event:
                        # If we are the last player to leave an event, then set it to inactive
                        event_players = player.event.entity_set.all().filter(type='P').exclude(pk=player.id)
                        if not event_players:
                            player.event.active = False
                            player.event.save(update_fields=["active", ])

                        player.event = None
                        player.event_joined = 0
                        update_fields.append('event')
                        update_fields.append('event_joined')

                    player.location = selected_location
                    update_fields.append('location')

                    player.save(update_fields=update_fields)

                # Refetch player object after updating location
                player = Player.objects.select_related('location__region__world', 'event', 'owner').get(pk=player.id)

                # Update and get event data
                context['event'], _ = self.get_event_data(player=player, full=True)
                context['travel'] = self.get_travel_data(player=player)

                player.owner.last_refresh = time.time()
                player.owner.save(update_fields=['last_refresh'])

                return render(request, self.template, context)

            return HttpResponse('Invalid selection', status=400)

        return HttpResponse(status=204)


class RegionChat(BaseView):
    template = 'partials/region_chat.html'

    def post(self, request):
        player = self.prep_player(['location__region', 'owner'])
        if not player:
            return redirect('login')

        context = {}
        region = player.location.region

        msg = request.POST.get('region-chat-msg', '')
        msg_cleaned = self.clean_text(text=msg)
        RegionChatMessage.objects.create(message=msg_cleaned, user=player.owner, region=region)
        messages = self.get_region_messages(player=player)

        context['messages'] = messages

        return render(request, self.template, context)
