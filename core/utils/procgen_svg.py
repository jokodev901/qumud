import math
import hashlib
import random


def generate_abstract_entity(seed_string: str) -> str:
    """
    Generates a unique abstract SVG creature based on a seed string.

    Args:
        seed_string (str): Unique ID (e.g. "monster-1", "player-name")

    Returns:
        str: A complete SVG XML string.
    """

    # SEEDING
    # Convert string to a stable integer seed
    hash_obj = hashlib.md5(seed_string.encode())
    seed_int = int(hash_obj.hexdigest(), 16)
    random.seed(seed_int)

    # PARAMETERS
    # Viewbox center
    cx, cy = 50, 50

    # Determine Archetype
    # 0 = Organic (Curves), 1 = Crystalline (Sharp), 2 = Construct (90-degree steps)
    archetype = random.choice(['organic', 'crystalline', 'construct'])

    # Determine Symmetry (makes it look more like a "creature")
    has_symmetry = random.choice([True, True, False])  # 66% chance of symmetry

    # GENERATE VERTICES (Polar Coordinates)
    # We generate points around a circle, varying the radius
    points = []

    # Number of vertices
    num_points = random.randint(6, 16)
    angle_step = (2 * math.pi) / num_points

    # Base radius settings
    base_radius = random.randint(15, 30)
    variance = random.randint(10, 25)  # How wild the shape gets

    for i in range(num_points):
        # Calculate angle
        angle = i * angle_step

        # Calculate Radius with procedural noise
        # We use a secondary random call to simulate "noise" for the radius
        r_change = random.randint(-variance, variance)
        r = max(5, base_radius + r_change)  # Ensure radius is at least 5

        # If symmetry is on, we mirror the geometry
        # If we are past the halfway mark (PI), copy the radius from the matching side
        if has_symmetry and angle > math.pi:
            # Find the "mirror" index
            mirror_index = num_points - i
            r = points[mirror_index][0]  # Reuse the radius from the left side

        points.append((r, angle))

    # CONVERT TO SVG PATH
    path_d = ""

    # Helper to get XY coordinates
    def get_xy(r, theta):
        x = cx + r * math.cos(theta)
        y = cy + r * math.sin(theta)
        return x, y

    start_x, start_y = get_xy(points[0][0], points[0][1])
    path_d += f"M {start_x:.1f} {start_y:.1f} "

    for i in range(len(points)):
        # Current Point
        r_curr, a_curr = points[i]
        x_curr, y_curr = get_xy(r_curr, a_curr)

        # Next Point (wrap around to 0 at the end)
        next_idx = (i + 1) % len(points)
        r_next, a_next = points[next_idx]
        x_next, y_next = get_xy(r_next, a_next)

        if archetype == 'organic':
            # Use Quadratic Bezier (Q) for smooth blobs
            # Control point is halfway between current and next, but pushed out slightly
            mid_a = (a_curr + a_next) / 2
            if next_idx == 0: mid_a += math.pi  # Handle wrap-around angle logic

            # Control radius is average of both + some extra blobbiness
            ctrl_r = (r_curr + r_next) / 2 + random.randint(0, 10)
            cx_pt, cy_pt = get_xy(ctrl_r, mid_a)
            path_d += f"Q {cx_pt:.1f} {cy_pt:.1f}, {x_next:.1f} {y_next:.1f} "

        elif archetype == 'crystalline':
            # Use Line To (L) for sharp spikes
            path_d += f"L {x_next:.1f} {y_next:.1f} "

        elif archetype == 'construct':
            # Use Horizontal/Vertical steps (Manhattan geometry)
            # Move Horizontal then Vertical to the next point
            if random.choice([True, False]):
                path_d += f"L {x_next:.1f} {y_curr:.1f} L {x_next:.1f} {y_next:.1f} "
            else:
                path_d += f"L {x_curr:.1f} {y_next:.1f} L {x_next:.1f} {y_next:.1f} "

    path_d += "Z"  # Close path

    # GENERATE "CORE" (Eye/Center)
    core_svg = ""
    if random.random() >= 0.2:
        core_type = random.choice(['eyes', 'void', 'slits'])

        if core_type == 'eyes':
            # Round eyes near the center
            eye_r = random.randint(3, 5)
            eye_d = random.randint(5, 10)
            core_svg = (f'<circle cx="{50 - eye_d}" cy="50" r="{eye_r}" fill="black" stroke="white" stroke-width="2"/>'
                        f'<circle cx="{50 + eye_d}" cy="50" r="{eye_r}" fill="black" stroke="white" stroke-width="2"/>')

        elif core_type == 'void':
            # A hollow ring cut out (White stroke, black fill)
            r_void = random.randint(5, 8)
            core_svg = f'<circle cx="50" cy="50" r="{r_void}" fill="black" stroke="white" stroke-width="2" />'

        elif core_type == 'slits':
            # Narrow slits
            h = random.randint(3, 5)
            w = random.randint(5, 10)
            core_svg = (f'<rect x="{45 - w / 2}" y="{50 - h / 2}" width="{w}" height="{h}" fill="black" stroke="white"'
                        f' stroke-width="2" rx="2" />'
                        f'<rect x="{55 - w / 2}" y="{50 - h / 2}" width="{w}" height="{h}" fill="black" stroke="white"'
                        f' stroke-width="2"rx="2" />')

    # GENERATE ANIMATION
    anim_wrapper_open = "<g>"
    anim_wrapper_close = "</g>"
    anim_type = random.choice(['breathing', 'vibrating', 'hopping', 'floating'])

    # Calculate random duration (speed)
    # Higher duration = Slower animation
    speed_factor = random.uniform(0.5, 3.0)

    if anim_type == 'breathing':
        # Scale transform centered on 50,50
        dur = f"{2 * speed_factor:.1f}s"
        # Random intensity (1.05 to 1.15 scale)
        scale_max = round(random.uniform(1.05, 1.15), 2)

        anim_wrapper_open = (
            f'<g transform-origin="50 50">'
            f'<animateTransform attributeName="transform" type="scale" '
            f'values="1;{scale_max};1" keyTimes="0;0.5;1" '
            f'dur="{dur}" repeatCount="indefinite" calcMode="spline" keySplines="0.4 0 0.2 1; 0.4 0 0.2 1" />'
        )

    elif anim_type == 'vibrating':
        dur = f"{0.1 * speed_factor:.2f}s"
        offsets = []
        for _ in range(3):
            ox = random.randint(-2, 2)
            oy = random.randint(-2, 2)
            offsets.append(f"{ox},{oy}")

        val_string = f"0,0; {offsets[0]}; {offsets[1]}; {offsets[2]}; 0,0"
        anim_wrapper_open = (
            f'<g>'    
            f'<animateTransform attributeName="transform" type="translate" '    
            f'values="{val_string}" dur="{dur}" repeatCount="indefinite" />'
        )

    elif anim_type == 'hopping':
        # Up and down translation with a "ground" pause
        dur = f"{1.0 * speed_factor:.1f}s"
        height = random.randint(5, 15)

        # values: 0 (ground) -> -height (peak) -> 0 (ground) -> 0 (pause)
        anim_wrapper_open = (
            f'<g>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0,0; 0,-{height}; 0,0; 0,0" keyTimes="0; 0.3; 0.6; 1" '
            f'dur="{dur}" repeatCount="indefinite" calcMode="spline" '
            f'keySplines="0.4 0 0.2 1; 0.4 0 0.2 1; 0 0 1 1" />'
        )

    elif anim_type == 'floating':
        # Smooth Sine-wave bobbing
        dur = f"{3.0 * speed_factor:.1f}s"
        range_y = random.randint(3, 8)

        anim_wrapper_open = (
            f'<g>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0,-{range_y}; 0,{range_y}; 0,-{range_y}" '
            f'dur="{dur}" repeatCount="indefinite" calcMode="spline" '
            f'keySplines="0.45 0 0.55 1; 0.45 0 0.55 1" />'
        )

    # ASSEMBLE SVG
    svg_template = f"""
    <svg class="position-absolute sprite"
     style="top: 50%; left: 50%; transform: translate(-50%, -50%); width: 3rem; height: 3rem; z-index: 1;"
     xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
        {anim_wrapper_open}            
            <path d="{path_d}" fill="white" />
            {core_svg if core_svg else ""}            
        {anim_wrapper_close}
    </svg>
    """

    return " ".join(svg_template.split())