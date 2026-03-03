import math, random

from core.utils.generators import procgen_enemies
from .models import Location, EnemyTemplate, EnemyArchetype


def generate_enemy_templates(loc: Location, biome: str, count: int) -> None:
    seed = loc.name
    random.seed(seed)
    templates = []

    procgen_data = procgen_enemies(seed=seed, biome=biome, count=count)
    archetypes = random.choices(EnemyArchetype.objects.all().order_by('id'),  k=count)

    i = 0
    for data in procgen_data:
        archetype = archetypes[i]
        templates.append(
            EnemyTemplate(
                name=data['name'],
                svg=data['svg'],
                max_health = loc.level * 2 * archetype.hp_multi + 10,
                attack_range = archetype.attack_range,
                min_damage = math.floor(loc.level*(1 - archetype.dmg_dev/2) + 1),
                max_damage= math.floor(loc.level*(1 + archetype.dmg_dev/2) + 1),
                speed = archetype.speed,
                initiative = loc.level * archetype.init_multi,
                max_targets = 1,
                level = loc.level,
                award_xp = math.floor(((loc.level**2) / 5) + loc.level),
                location = loc,
                archetype = archetype
            )
        )
        i += 1

    EnemyTemplate.objects.bulk_create(templates)