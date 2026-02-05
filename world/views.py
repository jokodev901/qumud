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
from .models import Entity, World, Region, Location, RegionChatMessage
from .forms import CharacterCreationForm, WorldCreationForm


def clean_text(text: str) -> str:
    cleaned = strip_tags(text)
    cleaned = cleaned.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    cleaned = re.sub(' +', ' ', cleaned)

    return cleaned.strip()


def get_region_messages(region: Region, delta: float = 300):
    messages = (RegionChatMessage.objects.all().select_related('user')
                .filter(region=region, sent_at__gte=(time.time() - delta)).order_by('-sent_at'))[:50]

    return messages


def get_region_players(region: Region):
    players = (User.objects.all()
               .filter(entity__location__region=region, last_update__gte=time.time() - 10)
               .order_by('alias'))

    return players


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


class SelectWorld(LoginRequiredMixin, View):
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
                        Location.objects.create(location_type='D', name=dungeon['name'], level=dungeon['level'],
                                                region=region)

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


class Map(View):
    template_name = 'map.html'

    def render_partials(self, partials, context):
        """
        Takes a list of template paths and returns a combined HttpResponse.
        """
        html = "".join([render_to_string(partial, context) for partial in partials])
        return HttpResponse(html, context)

    def prep_user(self):
        user = (User.objects
                .select_related('entity__location__region__world')
                .get(id=self.request.user.id))

        return user

    def init_location_context(self, user):
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

    def get(self, request):
        if not self.request.user.is_authenticated:
            return redirect('login')

        user = self.prep_user()
        context = {}

        try:
            # Do partial processing
            if request.GET.get('trigger', None) == 'update':
                delta = time.time() - user.last_update
                ticks = math.floor(delta)

                if ticks > 0:
                    partials = []

                    recent_messages = get_region_messages(region=user.entity.location.region)
                    region_players = get_region_players(region=user.entity.location.region)

                    if user.entity.new_status:
                        health_perc = math.floor((user.entity.max_health / user.entity.health) * 100)
                        context['character'] = user.entity
                        context['character_health_perc'] = health_perc
                        partials.append('partials/status.html')

                    if recent_messages:
                        context['messages'] = recent_messages
                        partials.append('partials/region_chat.html')

                    if region_players:
                        context['region_players'] = region_players
                        partials.append('partials/region_players.html')

                    # Final time update
                    user.last_update = time.time()
                    user.save(update_fields=['last_update'])

                    if partials:
                        return self.render_partials(partials, context)

                return HttpResponse(status=204)

            # Do full processing ( initial load )
            else:
                context = self.init_location_context(user)

                recent_messages = get_region_messages(region=user.entity.location.region)
                region_players = get_region_players(region=user.entity.location.region)
                health_perc = math.floor((user.entity.max_health / user.entity.health) * 100)

                context['region_players'] = region_players
                context['messages'] = recent_messages
                context['character'] = user.entity
                context['character_health_perc'] = health_perc

                user.entity.active.last_update = time.time()
                user.entity.active.save(update_fields=['last_update'])

                return render(request, self.template_name, context)

        except SyntaxError:
            return redirect('home')


class Travel(LoginRequiredMixin, View):
    template = 'partials/travel.html'

    def post(self, request):
        context = {}

        selected_location = (Location.objects.select_related('region__world')
                             .only('region', 'last_event', 'world')
                             .get(public_id=request.POST['public_id']))

        player_char = (Entity.objects.select_related('location__region')
                       .only('location', 'location__region')
                       .get(active=self.request.user))

        if selected_location != player_char.location:
            if selected_location.region == player_char.location.region:
                with transaction.atomic():
                    if not selected_location.last_event:
                        selected_location.last_event = time.time()
                        selected_location.save(update_fields=['last_event'])

                    player_char.location = selected_location
                    player_char.save(update_fields=['location'])

                locations = (Location.objects.all()
                             .filter(region=selected_location.region).order_by('level', 'id'))
                towns = [location for location in locations if location.location_type == 'T']
                dungeons = [location for location in locations if location.location_type == 'D']

                context['towns'] = towns
                context['dungeons'] = dungeons
                context['region'] = selected_location.region
                context['world'] = selected_location.region.world
                context['current_location'] = selected_location

                return render(request, self.template, context)

            return HttpResponse('Invalid selection', status=400)

        return HttpResponse(status=204)


class RegionChat(View):
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
        msg_cleaned = clean_text(msg)

        user = self.prep_user()
        region = user.entity.location.region

        RegionChatMessage.objects.create(message=msg_cleaned, user=user, region=region)
        messages = get_region_messages(region=region)

        context['messages'] = messages

        return render(request, self.template, context)