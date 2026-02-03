import json
import time
import re


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
    partials = []
    context = {}

    def render_partials(self, partials, context):
        """
        Takes a list of template paths and returns a combined HttpResponse.
        """
        # rendered = []
        # for partial in partials:
        #     rendered.append(render_to_string(partial, context))
        #
        # html = ''.join(rendered)

        html = "".join([render_to_string(partial, context) for partial in partials])
        return HttpResponse(html, context)

    def prep_player(self):
        player_char = (Entity.objects.select_related('location__region__world')
                       .only('location', 'location__region', 'location__region__world')
                       .get(active_id=self.request.user.id))

        return player_char

    def update_location_data(self, player_char):
        current_location = player_char.location
        region = current_location.region
        world = region.world

        locations = Location.objects.all().filter(region=region).order_by('level', 'id')
        towns = [location for location in locations if location.location_type == 'T']
        dungeons = [location for location in locations if location.location_type == 'D']

        self.context['towns'] = towns
        self.context['dungeons'] = dungeons
        self.context['region'] = region
        self.context['current_location'] = current_location
        self.context['world'] = world

    def get(self, request):
        if not self.request.user.is_authenticated:
            return redirect('login')

        user = self.request.user

        try:
            # Do partial processing
            if request.GET.get('trigger', None) == 'refresh':
                # We can convert this to just last_refresh and use it for everything
                if time.time() - user.last_chat_refresh >= 1:
                    # Chat processing
                    recent_messages = (
                        RegionChatMessage.objects.all()
                        .select_related('user')
                        .filter(region=user.entity.location.region,
                                sent_at__gte=time.time() - 3600).order_by('-sent_at')
                    )

                    if recent_messages:
                        self.context['messages'] = recent_messages
                        self.partials.append('partials/region_chat.html')

                    # Nearby players processing
                    region_players = (
                        User.objects.all()
                        .filter(entity__location__region=user.entity.location.region)
                    )

                    if region_players:
                        self.context['region_players'] = region_players
                        self.partials.append('partials/region_players.html')

                    # Final time update
                    user.last_chat_refresh = time.time()
                    user.save(update_fields=['last_chat_refresh'])

                    if self.partials:
                        return self.render_partials(self.partials, self.context)

                return HttpResponse(status=204)

            # Do full processing ( initial load )
            else:
                player_char = self.prep_player()
                self.update_location_data(player_char)

                recent_messages = (
                    RegionChatMessage.objects.all()
                    .select_related('user')
                    .filter(region=player_char.location.region,
                            sent_at__gte=time.time() - 3600).order_by('-sent_at')
                )

                self.context['messages'] = recent_messages

                player_char.active.last_chat_refresh = time.time()
                player_char.active.save(update_fields=['last_chat_refresh'])

                return render(request, self.template_name, self.context)

        except SyntaxError:
            return redirect('home')


class Travel(LoginRequiredMixin, View):
    template = 'partials/travel.html'

    def post(self, request):
        context = {}

        selected_location = (Location.objects.select_related('region')
                             .only('region', 'last_event')
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

                locations = Location.objects.all().filter(region=selected_location.region).order_by('level', 'id')
                towns = [location for location in locations if location.location_type == 'T']
                dungeons = [location for location in locations if location.location_type == 'D']

                context['towns'] = towns
                context['dungeons'] = dungeons
                context['region'] = selected_location.region
                context['current_location'] = selected_location

                return render(request, self.template, context)

            return HttpResponse('Invalid selection', status=400)

        return HttpResponse(status=204)


class RegionChat(View):
    template = 'partials/region_chat.html'
    context = {}

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

        msg = request.POST.get('region-chat-msg', '')
        msg_cleaned = clean_text(msg)

        user = self.prep_user()
        region = user.entity.location.region

        RegionChatMessage.objects.create(message=msg_cleaned, user=user, region=region)
        messages = (RegionChatMessage.objects.all().select_related('user')
                    .filter(region=region, sent_at__gte=(time.time() - 3600)).order_by('-sent_at'))

        self.context['messages'] = messages

        return render(request, self.template, self.context)