import random

from .markov import MarkovNameGenerator
from .corpus import CORPUS


def generate_town(seed: str, level: int) -> dict:
    rand = random.Random()
    rand.seed(seed)

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
    rand = random.Random()
    rand.seed(seed)

    levels = rand.choices(range(level, level+4), k=count)

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
    rand = random.Random()
    rand.seed(seed)
    biome = rand.choice(list(CORPUS['biomes'].keys()))

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


if __name__ == '__main__':
    print(generate_region('hello', 1))
