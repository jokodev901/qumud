import json
import time
import re
import math


from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, reverse
from django.http import HttpResponse
from django.db import transaction

from django.utils.html import strip_tags
from django.template.loader import render_to_string

from rest_framework.authtoken.models import Token

from core.utils import generators
from authentication.models import User
from .models import Entity, World, Region, Location, RegionChatMessage, EnemyTemplate
from .forms import CharacterCreationForm, WorldCreationForm


class BaseView(View):

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
        data = {}
        current_location = user.entity.location
        region = current_location.region
        world = region.world

        locations = Location.objects.all().filter(region=region).order_by('level', 'id')
        towns = [location for location in locations if location.location_type == 'T']
        dungeons = [location for location in locations if location.location_type == 'D']

        data['towns'] = towns
        data['dungeons'] = dungeons
        data['region'] = region
        data['current_location'] = current_location
        data['world'] = world

        return data


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


class SelectCharacter(LoginRequiredMixin, View):
    def post(self, request):
        selected = request.POST.get('selected_id')
        character = Entity.objects.select_related('owner').only('owner__id').get(public_id=selected)

        user = self.request.user
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


class GetPlayerCharacters(LoginRequiredMixin, TemplateView):
    template_name = 'player_characters.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        characters = Entity.objects.filter(owner=self.request.user).order_by('id')
        context['characters'] = characters

        return context


class CreateCharacter(LoginRequiredMixin, View):
    template_name = 'create_character.html'

    def get(self, request):
        form = CharacterCreationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = CharacterCreationForm(request.POST)

        if form.is_valid():
            entity = form.save(commit=False)
            entity.owner = self.request.user
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


class SelectWorld(LoginRequiredMixin, BaseView):
    template_name = 'world.html'

    def get(self, request):
        try:
            user = (
                User.objects
                .select_related('entity__location__region__world')
                .get(id=request.user.id)
            )

            form = WorldCreationForm()
            world_name = None

            if user.entity and user.entity.location:
                world_name = user.entity.location.region.world.name

            return render(request, self.template_name, {'world': world_name, 'form': form})

        except Exception:
            return redirect('home')

    def post(self, request):
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

                character = request.user.entity
                character.location = world.start_location
                character.save(update_fields=['location'])

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

    def prep_user(self):
        user = (User.objects
                .select_related('entity__location__region__world')
                .get(id=self.request.user.id))

        return user

    def get(self, request):
        user = self.prep_user()

        if not user.is_authenticated:
            return redirect('login')

        context = {}

        try:
            # Render partials (update trigger)
            if request.GET.get('trigger', None) == 'update':
                delta = time.time() - user.last_update
                ticks = math.floor(delta)

                if ticks > 0:
                    partials = []

                    recent_messages = self.get_region_messages(region=user.entity.location.region)
                    region_players = self.get_region_players(region=user.entity.location.region)

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

                    # Placeholder event processing
                    # just rendering svgs and enemy names for now
                    # placeholder enemy rendering
                    if user.entity.new_location:
                        enemy_svgs = EnemyTemplate.objects.filter(location=user.entity.location)
                        context['enemy_svgs'] = enemy_svgs
                        partials.append('partials/event.html')
                        user.entity.new_location = False
                        user.entity.save(update_fields=['new_location'])

                    # Final time update
                    user.last_update = time.time()
                    user.save(update_fields=['last_update'])

                    if partials:
                        return self.render_partials(partials, context)

                return HttpResponse(status=204)

            # Render full template ( initial load )
            else:
                context['travel'] = self.get_travel_data(user)

                # placeholder enemy rendering
                enemy_svgs = EnemyTemplate.objects.filter(location=user.entity.location)
                context['enemy_svgs'] = enemy_svgs

                recent_messages = self.get_region_messages(region=user.entity.location.region)
                region_players = self.get_region_players(region=user.entity.location.region)

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


class Travel(LoginRequiredMixin, BaseView):
    template = 'partials/travel.html'

    def post(self, request):
        context = {}

        selected_location = (Location.objects.select_related('region__world')
                             .only('region', 'last_event', 'world')
                             .get(public_id=request.POST['public_id']))

        user = (User.objects.select_related('entity__location__region__world').get(id=self.request.user.id))

        if selected_location != user.entity.location:
            if selected_location.region ==  user.entity.location.region:
                with transaction.atomic():
                    if not selected_location.last_event:
                        selected_location.last_event = time.time()
                        selected_location.save(update_fields=['last_event'])

                    user.entity.location = selected_location
                    user.entity.new_location = True
                    user.entity.save(update_fields=['location', 'new_location'])

                context['travel'] = self.get_travel_data(user)

                return render(request, self.template, context)

            return HttpResponse('Invalid selection', status=400)

        return HttpResponse(status=204)


class RegionChat(BaseView):
    template = 'partials/region_chat.html'

    def prep_user(self):
        user = (
            User.objects
            .select_related('entity__location__region')
            .get(id=self.request.user.id)
        )

        return user

    def post(self, request):
        if not self.request.user.is_authenticated:
            return redirect('login')

        context = {}

        msg = request.POST.get('region-chat-msg', '')
        msg_cleaned = self.clean_text(text=msg)

        user = self.prep_user()
        region = user.entity.location.region

        RegionChatMessage.objects.create(message=msg_cleaned, user=user, region=region)
        messages = self.get_region_messages(region=region)

        context['messages'] = messages

        return render(request, self.template, context)