import json

from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, reverse
from django.http import HttpResponse
from django.db import transaction

from rest_framework.authtoken.models import Token

from core.utils import generators
from authentication.models import User
from .models import Entity, World, Region, Location
from .forms import CharacterCreationForm, WorldCreationForm


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
                response = HttpResponse(status=204)
                response['HX-Location'] = reverse('home')

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
                    # Starting region
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
                response['HX-Location'] = reverse('map')

                location_data = {
                    "path": reverse('map'),
                    "target": "#main-content",
                    "swap": "innerHTML"
                }

                response = HttpResponse(status=204)
                response['HX-Location'] = json.dumps(location_data)
                return response

        return render(request, self.template_name, {'form': form})


class Map(LoginRequiredMixin, TemplateView):
    template_name = 'map.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        character = user.entity
        location = character.location
        region = location.region

        locations = Location.objects.all().filter(region=region).values_list('name', flat=True)

        context['locations'] = locations
        context['region'] = region.name
        context['current_location'] = location

        return context