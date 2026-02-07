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
from django.template.loader import render_to_string

from rest_framework.authtoken.models import Token

from core.utils import generators
from authentication.models import User
from .models import Entity, World, Region, Location, RegionChatMessage, EnemyTemplate, Event
from .forms import CharacterCreationForm, WorldCreationForm


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

    @staticmethod
    def clean_text(text: str) -> str:
        cleaned = strip_tags(text)
        cleaned = cleaned.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        cleaned = re.sub(' +', ' ', cleaned)

        return cleaned.strip()

    @staticmethod
    def get_region_messages(region: Region, count: int = 50):
        messages = (RegionChatMessage.objects.all().select_related('user')
                    .filter(region=region).order_by('-sent_at'))[:count]

        return messages

    @staticmethod
    def get_region_players(region: Region, timeout: int = 10):
        players = (User.objects.all()
                   .filter(entity__location__region=region, last_update__gte=time.time() - timeout)
                   .order_by('alias'))

        return players

    @staticmethod
    def get_travel_data(user: User) -> dict:
        context = {}
        current_location = user.entity.location
        region = current_location.region
        world = region.world

        locations = Location.objects.all().filter(region=region).order_by('level', 'id')
        towns = [location for location in locations if location.location_type == 'T']
        dungeons = [location for location in locations if location.location_type == 'D']

        context['towns'] = towns
        context['dungeons'] = dungeons
        context['region'] = region
        context['current_location'] = current_location
        context['world'] = world

        return context

    @staticmethod
    def get_event(location: Location) -> Event | None:
        player_limit = 1
        event_cooldown = 5

        # We want to overflow players into the same events vs race-creating individual events
        # select_for_update() on the location row as a transaction to ensure only one event created
        # at a time
        with transaction.atomic():
            # Find existing events with less than player_limit number of players
            player_count = Count("entity", filter=Q(entity__entity_type='P'))
            event_prefetch = Prefetch('event_set',
                                      queryset=Event.objects.all()
                                      .annotate(player_count=player_count)
                                      .filter(active=True, player_count__lt=player_limit))
            etemp_prefetch = Prefetch('enemytemplate_set')

            location_locked = (Location.objects.select_for_update()
                                .prefetch_related(event_prefetch, etemp_prefetch)
                                .get(id=location.id))

            events = location_locked.event_set.all()

            if events:
                # Just picking first available here
                # Consider ordering or some other rank
                return events[0]

            # No suitable event found, so create a new one
            delta = time.time() - location_locked.last_event
            ticks = math.floor(delta)

            # Doing a fixed 5-second interval between events for now
            # could make this variable or have ways to force an event
            if ticks < event_cooldown:
                return None

            event = Event.objects.create(location=location_locked, last_update=time.time())
            etemps = location_locked.enemytemplate_set.all()

            # Just spawn one of each enemy type for now
            for enemy in etemps:
                Entity.objects.create(template=enemy, event=event, name=enemy.name, entity_type='E',
                                      max_health=enemy.max_health, health=enemy.max_health,
                                      attack_range=enemy.attack_range, attack_damage=enemy.attack_damage,
                                      speed=enemy.speed, initiative=enemy.initiative, max_targets=1, level=1)

            return event

    @staticmethod
    def get_event_data(user: User, full: bool = False) -> dict:
        context = {}

        if user.entity.location.location_type == 'D':
            if user.entity.new_location or (not user.entity.event) or full:
                user.entity.new_location = False
                event = BaseView.get_event(user.entity.location)

                if event:
                    user.entity.event = event
                    enemies = Entity.objects.select_related('template').filter(event=event, entity_type='E')
                    players = Entity.objects.filter(event=event, entity_type='P').exclude(pk=user.entity.id)
                    context['enemies'] = enemies
                    context['players'] = players

                user.entity.save(update_fields=['event', 'new_location'])

        # If we were in an event and moved to a town, return empty enemy data and updated players in town
        elif user.entity.location.location_type == 'T':
            if user.entity.new_location or (not user.entity.event) or full:
                user.entity.new_location = False
                user.entity.event = None # currently assuming no events in town, update this if that changes
                players = (Entity.objects.filter(location=user.entity.location, entity_type='P')
                           .exclude(pk=user.entity.id))
                context['players'] = players

                user.entity.save(update_fields=['event', 'new_location'])

        return context


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
        character = Entity.objects.select_related('owner').only('owner__id').get(public_id=selected)

        if character:
            if character.owner == user:
                with transaction.atomic():
                    try:
                        current_entity = Entity.objects.get(active=user)
                    except Entity.DoesNotExist:
                        current_entity = None

                    if current_entity:
                        current_entity.active = None
                        current_entity.save(update_fields=['active'])

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

        characters = Entity.objects.filter(owner=user).order_by('id')
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
            entity = form.save(commit=False)
            entity.owner = user
            entity.entity_type = 'P'
            entity.health = entity.max_health

            entity.save()

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
        user = self.prep_user(['entity__location__region__world'])
        if not user:
            return redirect('login')

        if not user.entity:
            return redirect('home')

        form = WorldCreationForm()
        world_name = None

        if user.entity.location:
            world_name = user.entity.location.region.world.name

        return render(request, self.template_name, {'world': world_name, 'form': form})

    def post(self, request):
        user = self.prep_user(['entity__location'])
        if not user:
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
                        t = Location.objects.create(location_type='T', name=town['name'], level=town['level'],
                                                    region=region)
                        world.start_location = t

                    for dungeon in region_data['locations']['dungeons']:
                        location = Location.objects.create(location_type='D', name=dungeon['name'],
                                                           level=dungeon['level'], region=region)

                        enemy_temps = generators.generate_enemies(seed=dungeon['name'], level=dungeon['level'],
                                                                  biome=region_data['biome'], count=5)

                        for enemy in enemy_temps:
                            EnemyTemplate.objects.create(location=location, name=enemy['name'], svg=enemy['svg'])

                    world.save()

                user.entity.location = world.start_location
                user.entity.save(update_fields=['location'])

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

    def render_partials(self, partials, context):
        """
        Takes a list of template paths and returns a combined HttpResponse.
        """
        html = "".join([render_to_string(partial, context) for partial in partials])
        return HttpResponse(html)

    def get(self, request):
        user = self.prep_user(['entity__location__region__world', 'entity__event'])
        if not user:
            return redirect('login')

        context = {}

        try:
            # Render partials (update trigger)
            if request.GET.get('trigger', None) == 'update':
                delta = time.time() - user.last_update
                ticks = math.floor(delta)

                if ticks >= 1:
                    user.last_update = time.time()
                    user.save(update_fields=['last_update'])

                    partials = []

                    recent_messages = self.get_region_messages(region=user.entity.location.region)
                    region_players = self.get_region_players(region=user.entity.location.region)
                    event_data = self.get_event_data(user=user)

                    if user.entity.new_status:
                        context['character'] = user.entity
                        context['character_health_perc'] = user.entity.health_perc
                        partials.append('partials/status.html')

                    if recent_messages:
                        context['messages'] = recent_messages
                        partials.append('partials/region_chat.html')

                    if region_players:
                        context['region_players'] = region_players
                        partials.append('partials/region_players.html')

                    if event_data:
                        context['event'] = event_data
                        partials.append('partials/event.html')

                    if partials:
                        return self.render_partials(partials, context)

                return HttpResponse(status=204)

            # Render full template ( initial load )
            else:
                recent_messages = self.get_region_messages(region=user.entity.location.region)
                region_players = self.get_region_players(region=user.entity.location.region)
                context['travel'] = self.get_travel_data(user=user)
                context['event'] = self.get_event_data(user=user, full=True)
                context['region_players'] = region_players
                context['messages'] = recent_messages
                context['character'] = user.entity
                context['character_health_perc'] = user.entity.health_perc

                user.last_update = time.time()
                user.entity.new_location = False

                user.save(update_fields=['last_update'])
                user.entity.save(update_fields=['new_location'])

                return render(request, self.template_name, context)

        except SyntaxError:
            return redirect('home')


class Travel(BaseView):
    def render_partials(self, partials, context):
        """
        Takes a list of template paths and returns a combined HttpResponse.
        """
        html = "".join([render_to_string(partial, context) for partial in partials])
        return HttpResponse(html)

    def post(self, request):
        user = self.prep_user(['entity__location__region', 'entity__event__location'])
        if not user:
            return redirect('login')

        context = {}

        selected_location = (Location.objects.select_related('region__world')
                             .only('region', 'last_event', 'world')
                             .get(public_id=request.POST['public_id']))

        if selected_location != user.entity.location:
            if selected_location.region == user.entity.location.region:
                with transaction.atomic():
                    # Set event timer for unvisited location
                    if not selected_location.last_event:
                        selected_location.last_event = time.time()
                        selected_location.save(update_fields=['last_event'])

                    # Remove event if we left the event location
                    if user.entity.event and (user.entity.event.location != selected_location):
                        user.entity.event = None

                    user.entity.location = selected_location
                    user.entity.new_location = True
                    user.entity.save(update_fields=['location', 'new_location'])

                # Update and get event data
                context['event'] = self.get_event_data(user=user, full=True)
                context['travel'] = self.get_travel_data(user=user)
                templates = ('partials/travel.html', 'partials/event.html')

                return self.render_partials(templates, context)

            return HttpResponse('Invalid selection', status=400)

        return HttpResponse(status=204)


class RegionChat(BaseView):
    template = 'partials/region_chat.html'

    def post(self, request):
        user = self.prep_user(['entity__location__region',])
        if not user:
            return redirect('login')

        context = {}
        region = user.entity.location.region

        msg = request.POST.get('region-chat-msg', '')
        msg_cleaned = self.clean_text(text=msg)
        RegionChatMessage.objects.create(message=msg_cleaned, user=user, region=region)
        messages = self.get_region_messages(region=region)

        context['messages'] = messages

        return render(request, self.template, context)
