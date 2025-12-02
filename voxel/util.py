from __future__ import annotations

from math import floor
from typing import Tuple

from . import settings


# Coordinate helpers ---------------------------------------------------------
def world_to_chunk(x: int, z: int) -> Tuple[int, int]:
    """Return chunk coords (cx, cz) that contain world block (x, z)."""
    cx = x // settings.CHUNK_SIZE_X
    cz = z // settings.CHUNK_SIZE_Z
    return cx, cz


def local_coords(x: int, y: int, z: int) -> Tuple[int, int, int]:
    """Return local block coords within its chunk for a world block position."""
    lx = x - (x // settings.CHUNK_SIZE_X) * settings.CHUNK_SIZE_X
    lz = z - (z // settings.CHUNK_SIZE_Z) * settings.CHUNK_SIZE_Z
    # y is within [0, CHUNK_SIZE_Y)
    return lx, y, lz


def index_3d(lx: int, y: int, lz: int) -> int:
    """Packed index for local coords in a chunk (x-major within z-major within y-major)."""
    return (y * settings.CHUNK_SIZE_Z + lz) * settings.CHUNK_SIZE_X + lx


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


# Simplex noise terrain generation (no external deps) --------------------------
# 2D Simplex noise implementation for better performance than Perlin noise

# Simplex noise gradient vectors
_GRAD3 = [
    (1, 1, 0), (-1, 1, 0), (1, -1, 0), (-1, -1, 0),
    (1, 0, 1), (-1, 0, 1), (1, 0, -1), (-1, 0, -1),
    (0, 1, 1), (0, -1, 1), (0, 1, -1), (0, -1, -1)
]

# Permutation table for pseudo-random gradients
_PERM = list(range(256))


def _init_simplex_noise(seed=None):
    """Initialize the permutation table with the seed."""
    import random
    if seed is None:
        seed = settings.SEED
    rng = random.Random(seed)
    global _PERM
    _PERM = list(range(256))
    rng.shuffle(_PERM)
    # Duplicate to avoid modulo operations
    _PERM.extend(_PERM)


def set_world_seed(seed: int):
    """
    Set the world seed and reinitialize noise generation.
    This should be called before generating any terrain.
    """
    settings.SEED = seed
    _init_simplex_noise(seed)
    print(f"[Util] World seed set to: {seed}")


def _dot2(g, x, y):
    """2D dot product."""
    return g[0] * x + g[1] * y


def _simplex_noise_2d(x: float, y: float) -> float:
    """
    2D Simplex noise function.
    Returns a value in approximately [-1, 1].
    More efficient than Perlin noise with better visual characteristics.
    """
    # Skewing and unskewing factors for 2D
    F2 = 0.5 * (3.0 ** 0.5 - 1.0)
    G2 = (3.0 - 3.0 ** 0.5) / 6.0
    
    # Skew the input space to determine which simplex cell we're in
    s = (x + y) * F2
    i = int(x + s) if x + s > 0 else int(x + s) - 1
    j = int(y + s) if y + s > 0 else int(y + s) - 1
    
    t = (i + j) * G2
    X0 = i - t
    Y0 = j - t
    x0 = x - X0
    y0 = y - Y0
    
    # Determine which simplex we're in
    if x0 > y0:
        i1, j1 = 1, 0  # Lower triangle
    else:
        i1, j1 = 0, 1  # Upper triangle
    
    # Offsets for middle corner
    x1 = x0 - i1 + G2
    y1 = y0 - j1 + G2
    # Offsets for last corner
    x2 = x0 - 1.0 + 2.0 * G2
    y2 = y0 - 1.0 + 2.0 * G2
    
    # Work out the hashed gradient indices
    ii = i & 255
    jj = j & 255
    gi0 = _PERM[ii + _PERM[jj]] % 12
    gi1 = _PERM[ii + i1 + _PERM[jj + j1]] % 12
    gi2 = _PERM[ii + 1 + _PERM[jj + 1]] % 12
    
    # Calculate the contribution from the three corners
    t0 = 0.5 - x0 * x0 - y0 * y0
    if t0 < 0:
        n0 = 0.0
    else:
        t0 *= t0
        n0 = t0 * t0 * _dot2(_GRAD3[gi0], x0, y0)
    
    t1 = 0.5 - x1 * x1 - y1 * y1
    if t1 < 0:
        n1 = 0.0
    else:
        t1 *= t1
        n1 = t1 * t1 * _dot2(_GRAD3[gi1], x1, y1)
    
    t2 = 0.5 - x2 * x2 - y2 * y2
    if t2 < 0:
        n2 = 0.0
    else:
        t2 *= t2
        n2 = t2 * t2 * _dot2(_GRAD3[gi2], x2, y2)
    
    # Add contributions and scale to [-1, 1]
    return 70.0 * (n0 + n1 + n2)


# Initialize simplex noise on module load
_init_simplex_noise()


def _simplex_noise_3d(x: float, y: float, z: float) -> float:
    """
    3D Simplex noise function.
    Returns a value in approximately [-1, 1].
    """
    # Skewing and unskewing factors for 3D
    F3 = 1.0 / 3.0
    G3 = 1.0 / 6.0

    # Skew the input space to determine which simplex cell we're in
    s = (x + y + z) * F3
    i = int(x + s) if x + s > 0 else int(x + s) - 1
    j = int(y + s) if y + s > 0 else int(y + s) - 1
    k = int(z + s) if z + s > 0 else int(z + s) - 1

    t = (i + j + k) * G3
    X0 = i - t
    Y0 = j - t
    Z0 = k - t
    x0 = x - X0
    y0 = y - Y0
    z0 = z - Z0

    # Determine which simplex we're in
    if x0 >= y0:
        if y0 >= z0:
            i1, j1, k1 = 1, 0, 0
            i2, j2, k2 = 1, 1, 0
        elif x0 >= z0:
            i1, j1, k1 = 1, 0, 0
            i2, j2, k2 = 1, 0, 1
        else:
            i1, j1, k1 = 0, 0, 1
            i2, j2, k2 = 1, 0, 1
    else:
        if y0 < z0:
            i1, j1, k1 = 0, 0, 1
            i2, j2, k2 = 0, 1, 1
        elif x0 < z0:
            i1, j1, k1 = 0, 1, 0
            i2, j2, k2 = 0, 1, 1
        else:
            i1, j1, k1 = 0, 1, 0
            i2, j2, k2 = 1, 1, 0

    # Offsets for remaining corners
    x1 = x0 - i1 + G3
    y1 = y0 - j1 + G3
    z1 = z0 - k1 + G3
    x2 = x0 - i2 + 2.0 * G3
    y2 = y0 - j2 + 2.0 * G3
    z2 = z0 - k2 + 2.0 * G3
    x3 = x0 - 1.0 + 3.0 * G3
    y3 = y0 - 1.0 + 3.0 * G3
    z3 = z0 - 1.0 + 3.0 * G3

    # Work out the hashed gradient indices
    ii = i & 255
    jj = j & 255
    kk = k & 255
    
    gi0 = _PERM[ii + _PERM[jj + _PERM[kk]]] % 12
    gi1 = _PERM[ii + i1 + _PERM[jj + j1 + _PERM[kk + k1]]] % 12
    gi2 = _PERM[ii + i2 + _PERM[jj + j2 + _PERM[kk + k2]]] % 12
    gi3 = _PERM[ii + 1 + _PERM[jj + 1 + _PERM[kk + 1]]] % 12

    # Calculate the contribution from the four corners
    t0 = 0.6 - x0 * x0 - y0 * y0 - z0 * z0
    if t0 < 0:
        n0 = 0.0
    else:
        t0 *= t0
        n0 = t0 * t0 * _dot3(_GRAD3[gi0], x0, y0, z0)

    t1 = 0.6 - x1 * x1 - y1 * y1 - z1 * z1
    if t1 < 0:
        n1 = 0.0
    else:
        t1 *= t1
        n1 = t1 * t1 * _dot3(_GRAD3[gi1], x1, y1, z1)

    t2 = 0.6 - x2 * x2 - y2 * y2 - z2 * z2
    if t2 < 0:
        n2 = 0.0
    else:
        t2 *= t2
        n2 = t2 * t2 * _dot3(_GRAD3[gi2], x2, y2, z2)

    t3 = 0.6 - x3 * x3 - y3 * y3 - z3 * z3
    if t3 < 0:
        n3 = 0.0
    else:
        t3 *= t3
        n3 = t3 * t3 * _dot3(_GRAD3[gi3], x3, y3, z3)

    # Add contributions and scale to [-1, 1]
    return 32.0 * (n0 + n1 + n2 + n3)


def _dot3(g, x, y, z):
    """3D dot product."""
    return g[0] * x + g[1] * y + g[2] * z


def get_chunk_worms(cx: int, cz: int) -> list:
    """
    Deterministically generate a list of worms that START in this chunk.
    Returns list of dicts with worm properties.
    """
    # Seed based on chunk coords
    # Use a large prime mix to get a unique seed for this chunk
    seed = (cx * 3418731287 + cz * 132897987543) & 0xFFFFFFFF
    import random
    rng = random.Random(seed)
    
    worms = []
    # Reduce density: ~15% chance of a worm starting in a chunk
    # Previously was randint(0, 2) which is ~100% chance of at least 1 worm.
    if rng.random() < 0.15:
        num_worms = 1
    else:
        num_worms = 0
    
    for _ in range(num_worms):
        # Start position within the chunk
        start_x = cx * settings.CHUNK_SIZE_X + rng.randint(0, settings.CHUNK_SIZE_X - 1)
        start_z = cz * settings.CHUNK_SIZE_Z + rng.randint(0, settings.CHUNK_SIZE_Z - 1)
        # Start height: mostly deep, but some higher
        start_y = rng.randint(10, 50)
        
        # Initial direction (random 3D vector)
        yaw = rng.uniform(0, 6.28)
        pitch = rng.uniform(-1.0, 1.0)
        
        # Properties
        length = rng.randint(25, 60)
        radius = rng.uniform(2.0, 4.5)
        
        worms.append({
            'x': float(start_x),
            'y': float(start_y),
            'z': float(start_z),
            'yaw': yaw,
            'pitch': pitch,
            'length': length,
            'radius': radius,
            'seed': rng.randint(0, 999999) # Seed for path noise
        })
    return worms


def generate_chunk_caves(cx: int, cz: int) -> set:
    """
    Generate the set of local block coordinates (lx, y, lz) that are carved out by caves.
    Simulates worms from the current chunk and all nearby neighbors.
    """
    carved = set()
    
    # Check worms from a 5x5 area of chunks (radius 2)
    # Worms can travel ~60 blocks, which is < 4 chunks (16*4=64).
    # Radius 2 (2 chunks away) is 32 blocks. 
    # Radius 3 (3 chunks away) is 48 blocks.
    # Radius 4 (4 chunks away) is 64 blocks.
    # To be safe for 60-block worms, we should check radius 4.
    # That's 9x9 chunks = 81 chunks. A bit heavy?
    # Let's limit worm length to 48 and check radius 3 (7x7 = 49 chunks).
    # Or optimize: only simulate worms that head TOWARDS our chunk? 
    # For now, let's try radius 3.
    
    neighbor_radius = 3
    
    # Chunk bounds in world coords
    min_wx = cx * settings.CHUNK_SIZE_X
    max_wx = min_wx + settings.CHUNK_SIZE_X
    min_wz = cz * settings.CHUNK_SIZE_Z
    max_wz = min_wz + settings.CHUNK_SIZE_Z
    
    for ncx in range(cx - neighbor_radius, cx + neighbor_radius + 1):
        for ncz in range(cz - neighbor_radius, cz + neighbor_radius + 1):
            worms = get_chunk_worms(ncx, ncz)
            
            for worm in worms:
                # Simulate the worm
                wx, wy, wz = worm['x'], worm['y'], worm['z']
                yaw, pitch = worm['yaw'], worm['pitch']
                radius = worm['radius']
                length = worm['length']
                w_seed = worm['seed']
                
                # Optimization: Rough distance check?
                # If worm starts > length + radius away from chunk bounds, skip.
                # Closest point on chunk AABB to worm start?
                # Simple check: Manhattan distance from chunk center?
                # Chunk center:
                ccx = min_wx + 8
                ccz = min_wz + 8
                dist = abs(wx - ccx) + abs(wz - ccz)
                if dist > length + 20: # +20 buffer
                    continue

                import math
                
                for step in range(length):
                    # Carve sphere at current position
                    # Only if sphere intersects our chunk
                    # Sphere bounds
                    s_min_x = int(wx - radius)
                    s_max_x = int(wx + radius + 1)
                    s_min_z = int(wz - radius)
                    s_max_z = int(wz + radius + 1)
                    s_min_y = int(wy - radius)
                    s_max_y = int(wy + radius + 1)
                    
                    # Check intersection with chunk
                    if (s_max_x >= min_wx and s_min_x < max_wx and
                        s_max_z >= min_wz and s_min_z < max_wz):
                        
                        # Iterate blocks in sphere that are INSIDE our chunk
                        # Clamp to chunk bounds
                        iter_min_x = max(s_min_x, min_wx)
                        iter_max_x = min(s_max_x, max_wx)
                        iter_min_z = max(s_min_z, min_wz)
                        iter_max_z = min(s_max_z, max_wz)
                        iter_min_y = max(s_min_y, 1) # Don't carve bedrock
                        iter_max_y = min(s_max_y, settings.CHUNK_SIZE_Y - 1) # Don't carve top layer
                        
                        r_sq = radius * radius
                        
                        for bx in range(iter_min_x, iter_max_x):
                            for bz in range(iter_min_z, iter_max_z):
                                for by in range(iter_min_y, iter_max_y):
                                    # Check distance squared
                                    dx = bx - wx
                                    dy = by - wy
                                    dz = bz - wz
                                    if dx*dx + dy*dy + dz*dz < r_sq:
                                        # Convert to local coords
                                        lx = bx - min_wx
                                        lz = bz - min_wz
                                        carved.add((lx, by, lz))
                    
                    # Move worm
                    # Use noise to change direction
                    # We use 2D noise based on step and seed to modify yaw/pitch
                    # Scale step to make changes smooth
                    noise_scale = 0.1
                    yaw_change = _simplex_noise_2d(step * noise_scale, w_seed * 0.01) * 0.4
                    pitch_change = _simplex_noise_2d(step * noise_scale, w_seed * 0.01 + 100) * 0.4
                    
                    yaw += yaw_change
                    pitch += pitch_change
                    
                    # Clamp pitch to avoid going straight up/down
                    pitch = max(-1.0, min(1.0, pitch))
                    
                    # Update position
                    speed = 1.0
                    wx += math.cos(yaw) * math.cos(pitch) * speed
                    wy += math.sin(pitch) * speed
                    wz += math.sin(yaw) * math.cos(pitch) * speed
                    
    return carved


# Deprecated: Old is_cave function
# def is_cave(wx: int, wy: int, wz: int) -> bool: ...


def terrain_height(wx: int, wz: int, biome: str = 'plains', desert_weight: float = 0.0) -> int:
    """
    Simplex noise terrain generation for natural-looking terrain.
    Returns a height in [0, settings.CHUNK_SIZE_Y).
    Uses multiple octaves of Simplex noise at different frequencies for detail at multiple scales.
    Different biomes have different terrain characteristics, with smooth blending between them.
    Simplex noise is faster and has better visual quality than Perlin noise.
    """
    x = float(wx) * settings.HILL_FREQ_X
    z = float(wz) * settings.HILL_FREQ_Z

    total = 0.0
    amplitude = 1.0
    frequency = 1.0
    max_value = 0.0  # Used for normalizing result to [-1, 1]

    # Combine multiple octaves of Simplex noise
    for _ in range(settings.OCTAVE_COUNT):
        total += _simplex_noise_2d(x * frequency, z * frequency) * amplitude
        max_value += amplitude
        amplitude *= settings.OCTAVE_PERSISTENCE
        frequency *= settings.OCTAVE_LACUNARITY

    # Normalize to [-1, 1]
    total /= max_value

    # Generate BOTH terrain types completely, then blend them
    # This prevents walls by ensuring smooth height transitions
    
    # Plains terrain (standard)
    plains_base = settings.BASE_HEIGHT
    plains_amplitude = settings.HILL_AMPLITUDE
    plains_height = plains_base + plains_amplitude * total

    # Desert terrain (VERY subtle differences to prevent walls)
    # Key: differences must be small enough that small weight changes don't create visible cliffs
    desert_base = settings.BASE_HEIGHT * 0.98  # Only 2% lower (was 5%, too much)
    desert_amplitude = settings.HILL_AMPLITUDE * 0.92  # Only 8% smaller hills (was 20%, too much)
    desert_total = total * 0.95  # Only 5% noise reduction (was 10%, too much)
    desert_height = desert_base + desert_amplitude * desert_total

    # Smoothly blend between the two complete terrain heights
    # This ensures continuity and prevents walls
    blended_height = plains_height * (1.0 - desert_weight) + desert_height * desert_weight
    
    # Jungle terrain (hilly, varied)
    if biome == 'jungle':
        # Jungle is hillier and more chaotic
        jungle_base = settings.BASE_HEIGHT * 1.05
        jungle_amplitude = settings.HILL_AMPLITUDE * 1.5
        jungle_height = jungle_base + jungle_amplitude * total
        
        # Simple blend for now (could be better with weight like desert)
        # If we are in jungle, we are likely far from desert, so blending with plains is main concern
        # Ideally we'd have a jungle_weight similar to desert_weight
        # For now, just use the calculated height if biome is jungle
        # To avoid hard edges, we rely on the noise function continuity, 
        # but since we change amplitude, there might be seams.
        # A proper weight system for all biomes would be better, but for this task:
        blended_height = jungle_height

    # --- Mountain Generation ---
    # Generate a mask to define where mountains form (large scale)
    mountain_mask = _simplex_noise_2d(float(wx) * 0.004, float(wz) * 0.004)
    
    # Threshold to start mountains (e.g., > 0.2 means 40% of world is mountainous)
    threshold = 0.2
    if mountain_mask > threshold:
        # Calculate strength (0.0 to 1.0) of the mountain influence
        mask_strength = (mountain_mask - threshold) / (1.0 - threshold)
        
        # Small mountains layer (rocky, bumpy)
        small_m = _simplex_noise_2d(float(wx) * settings.SMALL_MOUNTAIN_FREQ, float(wz) * settings.SMALL_MOUNTAIN_FREQ)
        # Normalize to 0-1 and scale
        small_m = (small_m + 1.0) * 0.5 * settings.SMALL_MOUNTAIN_AMP
        
        # Big mountains layer (large peaks)
        big_m = _simplex_noise_2d(float(wx) * settings.BIG_MOUNTAIN_FREQ, float(wz) * settings.BIG_MOUNTAIN_FREQ)
        # Normalize to 0-1
        big_m = (big_m + 1.0) * 0.5
        # Cubing makes peaks sharper and valleys wider/flatter
        big_m = big_m * big_m * big_m * settings.BIG_MOUNTAIN_AMP
        
        # Combine and apply mask strength
        # Smoothstep the mask strength for nicer transitions
        mask_strength = mask_strength * mask_strength * (3 - 2 * mask_strength)
        
        mountain_height = (small_m + big_m) * mask_strength
        blended_height += mountain_height

    # --- Semi-Flat Terrain Generation ---
    # Create semi-flat areas of various sizes (small, medium, large)
    # don't make it completely flat but semi flat
    
    # Generate noise for each scale
    large_flat = _simplex_noise_2d(float(wx) * settings.SEMI_FLAT_LARGE_FREQ, float(wz) * settings.SEMI_FLAT_LARGE_FREQ)
    medium_flat = _simplex_noise_2d(float(wx) * settings.SEMI_FLAT_MEDIUM_FREQ, float(wz) * settings.SEMI_FLAT_MEDIUM_FREQ)
    small_flat = _simplex_noise_2d(float(wx) * settings.SEMI_FLAT_SMALL_FREQ, float(wz) * settings.SEMI_FLAT_SMALL_FREQ)
    
    # Calculate flatness strength (how much this area should be flattened)
    # We look for areas where the noise is above the threshold
    flatness_strength = 0.0
    
    if large_flat > settings.SEMI_FLAT_THRESHOLD:
        flatness_strength = max(flatness_strength, (large_flat - settings.SEMI_FLAT_THRESHOLD))
        
    if medium_flat > settings.SEMI_FLAT_THRESHOLD:
        flatness_strength = max(flatness_strength, (medium_flat - settings.SEMI_FLAT_THRESHOLD))
        
    if small_flat > settings.SEMI_FLAT_THRESHOLD:
        flatness_strength = max(flatness_strength, (small_flat - settings.SEMI_FLAT_THRESHOLD))
    
    # Apply flattening if we are in a semi-flat area
    if flatness_strength > 0.0:
        # Normalize strength to range [0, 1] for blending
        # Scaling up so the effect is more pronounced when above threshold
        blend_factor = min(flatness_strength * 3.0, 1.0)
        
        # Calculate the target "semi-flat" height
        # Instead of flattening to a single value, we just reduce the variation from base height
        # This creates "semi-flat" terrain that still has some bumpiness
        current_deviation = blended_height - settings.BASE_HEIGHT
        dampened_deviation = current_deviation * settings.SEMI_FLAT_FACTOR
        semi_flat_height = settings.BASE_HEIGHT + dampened_deviation
        
        # Blend the original terrain with the semi-flat terrain
        blended_height = blended_height * (1.0 - blend_factor) + semi_flat_height * blend_factor

    # Convert to integer
    height = int(blended_height)

    # Clamp to valid range
    if height < 1:
        height = 1
    if height >= settings.CHUNK_SIZE_Y:
        height = settings.CHUNK_SIZE_Y - 1

    return height


# AABB helpers ---------------------------------------------------------------
class AABB:
    """Axis-aligned bounding box defined by min/max inclusive bounds."""

    __slots__ = ("min_x", "min_y", "min_z", "max_x", "max_y", "max_z")

    def __init__(self, min_x: float, min_y: float, min_z: float, max_x: float, max_y: float, max_z: float):
        self.min_x = min_x
        self.min_y = min_y
        self.min_z = min_z
        self.max_x = max_x
        self.max_y = max_y
        self.max_z = max_z

    def intersects(self, other: "AABB") -> bool:
        return not (
            self.max_x <= other.min_x
            or self.min_x >= other.max_x
            or self.max_y <= other.min_y
            or self.min_y >= other.max_y
            or self.max_z <= other.min_z
            or self.min_z >= other.max_z
        )

    def moved(self, dx: float, dy: float, dz: float) -> "AABB":
        return AABB(self.min_x + dx, self.min_y + dy, self.min_z + dz, self.max_x + dx, self.max_y + dy, self.max_z + dz)


def block_aabb(bx: int, by: int, bz: int) -> AABB:
    """Return the AABB for a block at integer coords (size 1)."""
    return AABB(bx, by, bz, bx + 1.0, by + 1.0, bz + 1.0)


def get_biome(wx: int, wz: int) -> str:
    """
    Determine the biome at given world coordinates using multi-octave noise.
    Returns 'desert' or 'plains' based on noise patterns.
    Uses multiple noise layers to create natural, varied biome shapes and sizes.
    Desert biome has medium-low chance (around 25%).
    """
    # Layer 1: Large-scale continental noise (creates big desert regions)
    continental_noise = _simplex_noise_2d(float(wx) * 0.003, float(wz) * 0.003)
    
    # Layer 2: Medium-scale regional noise (creates medium-sized variations)
    regional_noise = _simplex_noise_2d(float(wx) * 0.008, float(wz) * 0.008)
    
    # Layer 3: Small-scale local noise (creates fine detail and irregular edges)
    local_noise = _simplex_noise_2d(float(wx) * 0.02, float(wz) * 0.02)
    
    # Layer 4: Additional variation using different offset for more complexity
    variation_noise = _simplex_noise_2d(float(wx) * 0.012 + 100.0, float(wz) * 0.012 + 100.0)
    
    # Combine noise layers with decreasing weights for natural appearance
    # Continental has most influence, local adds detail
    combined_noise = (
        continental_noise * 0.5 +      # 50% - Large-scale patterns
        regional_noise * 0.25 +         # 25% - Medium variations
        local_noise * 0.15 +            # 15% - Fine detail
        variation_noise * 0.1           # 10% - Extra complexity
    )
    
    # Use the combined noise with a varying threshold for organic shapes
    # The threshold itself varies slightly based on position for even more natural variation
    threshold_variation = _simplex_noise_2d(float(wx) * 0.001, float(wz) * 0.001) * 0.1
    desert_threshold = -0.5 + threshold_variation  # Base threshold with local variation
    
    # Desert occurs where combined noise is below the varying threshold
    if combined_noise < desert_threshold:
        return 'desert'
        
    # Jungle occurs where combined noise is high (hot/wet area)
    # Using a high threshold for jungle
    jungle_threshold = 0.3 + threshold_variation
    if combined_noise > jungle_threshold:
        return 'jungle'

    return 'plains'


def should_place_tree(wx: int, wz: int) -> bool:
    """
    Use noise to determine if a tree should be placed at world coordinates (wx, wz).
    Returns True if a tree should be placed, False otherwise.
    Uses grid-based spacing with noise to create natural but well-spaced tree distribution.
    Only places trees in non-desert biomes.
    """
    # Never place trees in desert
    if get_biome(wx, wz) == 'desert':
        return False

    # Grid-based spacing: only check positions on a 6-block grid
    # This prevents trees from being too close together
    # User requested more spread out trees, so increasing grid size
    grid_size = 10  # Increased from 6
    if wx % grid_size != 0 or wz % grid_size != 0:
        return False

    # Use noise to decide which grid positions get trees (not all of them)
    # Higher frequency creates more variation
    tree_noise = _simplex_noise_2d(float(wx) * 0.03, float(wz) * 0.03)
    
    # Additional layer of noise for more natural distribution
    density_noise = _simplex_noise_2d(float(wx) * 0.015, float(wz) * 0.015)

    # Only place trees on relatively flat terrain
    terrain_noise = _simplex_noise_2d(float(wx) * settings.HILL_FREQ_X, float(wz) * settings.HILL_FREQ_Z)
    terrain_flatness = 1.0 - abs(terrain_noise) * 0.5

    # Combine noise layers with stricter thresholds for natural but sparse distribution
    # About 30-40% of grid positions will have trees in suitable areas
    
    # Jungle has much higher density
    if get_biome(wx, wz) == 'jungle':
        # Denser grid for jungle
        if wx % 4 != 0 or wz % 4 != 0:
            return False
        return (tree_noise > 0.0 and density_noise > -0.2)
        
    return (tree_noise > 0.4 and
            density_noise > 0.2 and
            terrain_flatness > 0.6)


def get_tree_type(wx: int, wz: int) -> str:
    """
    Determine the type of tree to place at (wx, wz).
    Returns 'oak' or 'birch'.
    """
    # Use a different noise function or offset to decide tree type
    # Birch trees often grow in groups, so low frequency noise is good
    type_noise = _simplex_noise_2d(float(wx) * 0.05, float(wz) * 0.05)
    
    if type_noise > 0.2:
        return 'birch'
    return 'oak'


def generate_tree(wx: int, wy: int, wz: int) -> list:
    """
    Generate tree blocks at the given world position.
    Returns a list of (wx, wy, wz, block_id) tuples for all tree blocks.
    Tree consists of:
    - Trunk: 4-5 blocks high wood
    - Leaves: Smaller, more natural shape with proper gaps
    """
    blocks = []

    # Randomize tree height slightly (4-5 blocks, smaller than before)
    height_noise = _simplex_noise_2d(float(wx) * 0.1, float(wz) * 0.1)
    trunk_height = 4 + int((height_noise + 1.0) * 0.5)  # 4-5 blocks

    # Generate trunk
    for y_offset in range(trunk_height):
        blocks.append((wx, wy + y_offset, wz, 6))  # BLOCK_WOOD

    # Generate leaves with more natural, less dense pattern
    leaf_center_y = wy + trunk_height - 1
    
    # Layer above trunk top (small cap)
    for dx in range(-1, 2):
        for dz in range(-1, 2):
            # Skip corners for more natural shape
            if abs(dx) + abs(dz) > 2:
                continue
            
            leaf_x = wx + dx
            leaf_z = wz + dz
            
            # Add some randomness
            gap_noise = _simplex_noise_2d(float(leaf_x) * 0.3, float(leaf_z) * 0.3)
            if gap_noise < 0.0:  # 50% density for variety
                continue
            
            # Don't place directly above trunk
            if dx == 0 and dz == 0:
                continue
                
            blocks.append((leaf_x, leaf_center_y + 1, leaf_z, 7))  # BLOCK_LEAVES
    
    # Main leaf layer at trunk top (3x3 with gaps)
    for dx in range(-1, 2):
        for dz in range(-1, 2):
            leaf_x = wx + dx
            leaf_z = wz + dz
            
            # Skip corners for rounder shape
            if abs(dx) == 1 and abs(dz) == 1:
                gap_noise = _simplex_noise_2d(float(leaf_x) * 0.4, float(leaf_z) * 0.4)
                if gap_noise < 0.3:  # Higher chance to skip corners
                    continue
            
            # Don't place on trunk itself
            if dx == 0 and dz == 0:
                continue
            
            blocks.append((leaf_x, leaf_center_y, leaf_z, 7))  # BLOCK_LEAVES
    
    # Lower leaf layer (smaller, more sparse)
    for dx in range(-1, 2):
        for dz in range(-1, 2):
            # Only cross pattern for lower layer (not corners)
            if abs(dx) + abs(dz) > 1:
                continue
            
            leaf_x = wx + dx
            leaf_z = wz + dz
            
            # Skip center (trunk is there)
            if dx == 0 and dz == 0:
                continue
            
            blocks.append((leaf_x, leaf_center_y - 1, leaf_z, 7))  # BLOCK_LEAVES

    return blocks


def should_place_cactus(wx: int, wz: int) -> bool:
    """
    Use noise to determine if a cactus should be placed at world coordinates (wx, wz).
    Returns True if a cactus should be placed, False otherwise.
    Uses grid-based spacing with noise to create natural but well-spaced cactus distribution.
    Only places cacti in desert biomes.
    """
    # Only place cacti in desert
    if get_biome(wx, wz) != 'desert':
        return False

    # Grid-based spacing: only check positions on a 5-block grid
    # This prevents cacti from being too close together
    grid_size = 5
    if wx % grid_size != 0 or wz % grid_size != 0:
        return False

    # Use noise to decide which grid positions get cacti
    cactus_noise = _simplex_noise_2d(float(wx) * 0.04, float(wz) * 0.04)
    
    # Additional layer of noise for more natural distribution
    density_noise = _simplex_noise_2d(float(wx) * 0.02, float(wz) * 0.02)

    # About 40-50% of grid positions will have cacti in desert areas
    return cactus_noise > 0.3 and density_noise > 0.1


def generate_cactus(wx: int, wy: int, wz: int) -> list:
    """
    Generate cactus blocks at the given world position.
    Returns a list of (wx, wy, wz, block_id) tuples for all cactus blocks.
    Cactus is simple: vertical stack of 1-4 blocks.
    """
    blocks = []

    # Randomize cactus height (1-4 blocks)
    height_noise = _simplex_noise_2d(float(wx) * 0.15, float(wz) * 0.15)
    cactus_height = 1 + int((height_noise + 1.0) * 1.5)  # 1-4 blocks

    # Generate vertical stack
    for y_offset in range(cactus_height):
        blocks.append((wx, wy + y_offset, wz, 11))  # BLOCK_CACTUS

    return blocks


def generate_jungle_tree(wx: int, wy: int, wz: int) -> list:
    """
    Generate a large jungle tree.
    """
    blocks = []
    
    # Taller trunk (8-12 blocks)
    height_noise = _simplex_noise_2d(float(wx) * 0.1, float(wz) * 0.1)
    trunk_height = 8 + int((height_noise + 1.0) * 2.0)
    
    # Generate trunk
    for y_offset in range(trunk_height):
        blocks.append((wx, wy + y_offset, wz, 30))  # BLOCK_JUNGLE_LOG
        
    # Generate canopy (flat top, wide)
    leaf_y_start = wy + trunk_height - 3
    
    # Wide canopy layers
    for y_offset in range(4):
        y = leaf_y_start + y_offset
        radius = 3 if y_offset < 2 else 2
        
        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                # Circle-ish shape
                if dx*dx + dz*dz > radius*radius + 1:
                    continue
                    
                # Don't replace trunk
                if dx == 0 and dz == 0 and y < wy + trunk_height:
                    continue
                    
                blocks.append((wx + dx, y, wz + dz, 31))  # BLOCK_JUNGLE_LEAVES
                
    # Cocoa pods or vines could go here
    
    return blocks


def generate_birch_tree(wx: int, wy: int, wz: int) -> list:
    """
    Generate a birch tree.
    Similar to oak but with birch blocks and slightly taller/straighter.
    """
    blocks = []

    # Birch trees are often taller and straighter
    height_noise = _simplex_noise_2d(float(wx) * 0.1, float(wz) * 0.1)
    trunk_height = 5 + int((height_noise + 1.0) * 0.5)  # 5-6 blocks

    # Generate trunk
    for y_offset in range(trunk_height):
        blocks.append((wx, wy + y_offset, wz, 32))  # BLOCK_BIRCH_LOG

    # Generate leaves
    leaf_center_y = wy + trunk_height - 1
    
    # Top layer (small)
    for dx in range(-1, 2):
        for dz in range(-1, 2):
            if abs(dx) + abs(dz) > 1:
                continue
            if dx == 0 and dz == 0: # Skip trunk top
                continue
            blocks.append((wx + dx, leaf_center_y + 1, wz + dz, 33)) # BLOCK_BIRCH_LEAVES

    # Middle layer (wider)
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            # Rounded shape
            if dx*dx + dz*dz > 5:
                continue
            if dx == 0 and dz == 0:
                continue
            blocks.append((wx + dx, leaf_center_y, wz + dz, 33))

    # Bottom layer (same as middle but maybe sparse)
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            if dx*dx + dz*dz > 5:
                continue
            if dx == 0 and dz == 0:
                continue
            
            # 70% chance for bottom leaves
            if _simplex_noise_2d(float(wx+dx)*0.5, float(wz+dz)*0.5) > -0.4:
                blocks.append((wx + dx, leaf_center_y - 1, wz + dz, 33))

    return blocks
