import random

from .markov import MarkovNameGenerator
from .procgen_svg import generate_abstract_entity
from .corpus import CORPUS


def generate_town(seed: str, level: int) -> dict:
    gen = MarkovNameGenerator(order=3, seed=seed, normalize_case=True)
    gen.fit(CORPUS['towns'])
    name = gen.generate(max_len=24, min_len=6, avoid_training=True)
    words = name.split()

    if len(words) > 1 and len(words[-1]) < 4:
        words.pop()

    name = " ".join(words).title()
    town_dict = {'name': name, 'level': level}

    return town_dict


def generate_dungeons(seed: str, level: int, count: int) -> list[dict]:
    dungeons = []
    random.seed(seed)

    levels = random.choices(range(level, level+4), k=count)

    gen = MarkovNameGenerator(order=3, seed=seed, normalize_case=True)
    gen.fit(CORPUS['dungeons'])
    names = gen.generate_many(k=count, max_len=24, min_len=6, avoid_training=True)

    for name in names:
        words = name.split()

        if len(words) > 1 and len(words[-1]) < 4:
            words.pop()

        dungeons.append({'name': " ".join(words).title(), 'level': levels.pop()})

    return dungeons


def generate_region(seed: str, level: int) -> dict:
    random.seed(seed)
    biome = random.choice(list(CORPUS['biomes'].keys()))

    gen = MarkovNameGenerator(order=3, seed=seed, normalize_case=True)
    gen.fit(CORPUS['biomes'][biome]['regions'])
    name = gen.generate(max_len=24, min_len=6, avoid_training=True)
    words = name.split()

    if len(words) > 1 and len(words[-1]) < 4:
        words.pop()

    name = " ".join(words).title()

    locations = {}
    town = generate_town(seed=seed, level=level)
    dungeons = generate_dungeons(seed=seed, level=level, count=5)
    locations['towns'] = [town]
    locations['dungeons'] = dungeons

    region_dict = {'name': name, 'biome': biome, 'locations': locations}

    return region_dict


def generate_enemies(seed: str, level: int, biome: str, count: int) -> list[dict]:
    enemies = []
    random.seed(seed)

    gen = MarkovNameGenerator(order=3, seed=seed, normalize_case=True)
    gen.fit(CORPUS['biomes'][biome]['enemies'])
    names = gen.generate_many(k=count, max_len=24, min_len=6, avoid_training=True)

    for name in names:
        words = name.split()

        if len(words) > 1 and len(words[-1]) < 4:
            words.pop()

        name = " ".join(words).title()
        svg = generate_abstract_entity(seed_string=name)

        enemy_dict = {'name': name, 'level': level, 'svg': svg, 'max_health': 20}
        enemies.append(enemy_dict)

    return enemies