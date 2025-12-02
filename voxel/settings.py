# Voxel engine settings and tuning parameters
# All values are centralized here so you can tweak performance/feel in one place.

from math import pi

# Window / rendering
WINDOW_TITLE = "Blockforge"
FRAME_RATE_METER = True
BACKGROUND_COLOR = (0.53, 0.81, 0.92, 1.0)  # sky-ish
VSYNC = False  # Disabled to prevent stuttering during chunk generation

# Chunking
CHUNK_SIZE_X = 8  # Reduced from 16 for faster chunk generation
CHUNK_SIZE_Y = 128  # Increased to allow for big mountains
CHUNK_SIZE_Z = 8  # Reduced from 16 for faster chunk generation

# Difficulty Levels
DIFFICULTY_PEACEFUL = 0
DIFFICULTY_EASY = 1
DIFFICULTY_NORMAL = 2
DIFFICULTY_HARD = 3

# View distance in chunks (radius). 1 => 3x3 = 9 chunks; 2 => 5x5 = 25 chunks; 3 => 7x7 = 49 chunks; 4 => 9x9 = 81 chunks
RENDER_DISTANCE = 4

# Limit chunk work per frame to avoid stutter (ultra-conservative to eliminate ALL lag spikes)
MAX_CHUNK_CREATES_PER_FRAME = 1  # Only 1 per frame ensures zero lag spikes
MAX_CHUNK_MESHES_PER_FRAME = 1  # Only 1 per frame ensures silky-smooth performance

# Block metrics
BLOCK_SIZE = 1.0  # world units per block (1.0 is standard)
HALF = 0.5

# World generation (simple analytic terrain; no external deps)
SEED = 1337
BASE_HEIGHT = 18          # base ground level
HILL_AMPLITUDE = 8        # hill height variation (reduced for smoother terrain)
HILL_FREQ_X = 0.02        # reduced frequency for larger, smoother features
HILL_FREQ_Z = 0.02        # reduced frequency for larger, smoother features

# Semi-Flat Terrain Settings
# Frequency controls the size of the areas (lower = larger areas)
SEMI_FLAT_LARGE_FREQ = 0.005
SEMI_FLAT_MEDIUM_FREQ = 0.015
SEMI_FLAT_SMALL_FREQ = 0.04
# Thresholds control how common these areas are (higher = rarer)
SEMI_FLAT_THRESHOLD = 0.2
# Factor controls how flat "semi-flat" is (0.0 = completely flat, 1.0 = normal terrain)
SEMI_FLAT_FACTOR = 0.23

# Mountain settings
SMALL_MOUNTAIN_FREQ = 0.015
SMALL_MOUNTAIN_AMP = 15
BIG_MOUNTAIN_FREQ = 0.005
BIG_MOUNTAIN_AMP = 40

CAVE_THRESHOLD = 0.0      # not used initially; kept for future expansion

# Octave noise settings for terrain generation
OCTAVE_COUNT = 2          # Reduced to 2 for better performance (less noise calculations)
OCTAVE_PERSISTENCE = 0.5  # amplitude multiplier for each octave (0.5 = half amplitude each time)
OCTAVE_LACUNARITY = 2.0   # frequency multiplier for each octave (2.0 = double frequency each time)

# Player / Controller
PLAYER_WIDTH = 0.6
PLAYER_DEPTH = 0.6
PLAYER_HEIGHT = 1.8
PLAYER_EYE_OFFSET = 1.6   # camera height from feet

MOVE_SPEED = 6.0          # units/sec, walking
AIR_CONTROL = 0.25        # fraction of ground control in air
ACCEL_GROUND = 40.0       # acceleration on ground
ACCEL_AIR = ACCEL_GROUND * AIR_CONTROL
FRICTION = 20.0           # ground friction
GRAVITY = 26.0            # units/sec^2
JUMP_SPEED = 8.5

# Mouse / Look
MOUSE_SENSITIVITY = 0.11  # heading/pitch degrees per pixel
MAX_PITCH = 89.0          # avoid gimbal/flip

# Collision
EPSILON = 0.001            # small padding against surfaces to prevent jitter (increased from 1e-4)

# Colors (vertex colors; no textures needed)
COLOR_GRASS_TOP = (0.46, 0.74, 0.36, 1.0)
COLOR_JUNGLE_GRASS_TOP = (0.35, 0.85, 0.30, 1.0) # Lighter/Brighter green for jungle
COLOR_DIRT = (0.56, 0.37, 0.24, 1.0)
COLOR_STONE = (0.55, 0.55, 0.56, 1.0)
COLOR_SIDES_GRASS = (0.38, 0.64, 0.29, 1.0)
COLOR_JUNGLE_SIDES_GRASS = (0.28, 0.74, 0.22, 1.0) # Lighter/Brighter green for jungle sides
COLOR_BEDROCK = (0.20, 0.20, 0.22, 1.0)
COLOR_SAND = (0.93, 0.89, 0.70, 1.0)
COLOR_WOOD = (0.55, 0.35, 0.20, 1.0)
COLOR_WOOD_TOP = (0.65, 0.45, 0.25, 1.0)
COLOR_LEAVES = (0.20, 0.60, 0.20, 1.0)
COLOR_COBBLESTONE = (0.50, 0.50, 0.52, 1.0)
COLOR_BRICK = (0.70, 0.30, 0.25, 1.0)
COLOR_SANDSTONE = (0.91, 0.83, 0.61, 1.0)
COLOR_CACTUS = (0.36, 0.64, 0.25, 1.0)

# Block breaking durations (in seconds, matching Minecraft roughly)
# These represent how long it takes to break each block type by hand
BLOCK_HARDNESS = {
    1: 0.6,    # BLOCK_GRASS - easy to break
    2: 0.5,    # BLOCK_DIRT - easy to break
    3: 1.5,    # BLOCK_STONE - harder
    4: None,   # BLOCK_BEDROCK - unbreakable
    5: 0.5,    # BLOCK_SAND - easy to break
    6: 2.0,    # BLOCK_WOOD - medium
    7: 0.3,    # BLOCK_LEAVES - very easy
    8: 2.0,    # BLOCK_COBBLESTONE - hard
    9: 2.0,    # BLOCK_BRICK - hard
    10: 0.8,   # BLOCK_SANDSTONE - medium-hard
    11: 0.3,   # BLOCK_CACTUS - very easy
    12: 2.0,   # BLOCK_PLANKS - wooden planks
    13: 1.0,   # BLOCK_STICKS - wooden sticks
    14: 2.0,   # BLOCK_PICKAXE_WOOD - wooden tools
    15: 3.0,   # BLOCK_PICKAXE_STONE - stone tools
    16: 4.0,   # BLOCK_PICKAXE_IRON - iron tools
    17: 2.0,   # BLOCK_AXE_WOOD - wooden tools
    18: 3.0,   # BLOCK_AXE_STONE - stone tools
    19: 4.0,   # BLOCK_AXE_IRON - iron tools
    20: 2.0,   # BLOCK_SHOVEL_WOOD - wooden tools
    21: 3.0,   # BLOCK_SHOVEL_STONE - stone tools
    22: 4.0,   # BLOCK_SHOVEL_IRON - iron tools
    23: 2.0,   # BLOCK_SWORD_WOOD - wooden tools
    24: 3.0,   # BLOCK_SWORD_STONE - stone tools
    25: 4.0,   # BLOCK_SWORD_IRON - iron tools
    26: 2.5,   # BLOCK_CRAFTING_TABLE - crafting table
    27: 3.5,   # BLOCK_FURNACE - furnace
    28: 2.5,   # BLOCK_CHEST - chest
    29: 5.0,   # BLOCK_IRON_INGOT - iron ingot
}

# Breaking animation settings
BREAK_STAGES = 10  # Number of crack stages (0-9, matching Minecraft)

# Debug
SHOW_COLLISION_AABB = False
PRINT_CHUNK_EVENTS = False

# Derived helpers
CHUNK_AREA_XZ = CHUNK_SIZE_X * CHUNK_SIZE_Z

# Camera config
FOV = 70.0 * (pi / 180.0)  # radians for any math; Panda3D takes degrees where needed

# Fog settings (for render distance fade)
FOG_ENABLED = False  # Disabled per user request
FOG_COLOR = BACKGROUND_COLOR  # Match sky color
FOG_START_DISTANCE = (RENDER_DISTANCE - 0.5) * CHUNK_SIZE_X  # Start fog slightly before render distance
FOG_END_DISTANCE = RENDER_DISTANCE * CHUNK_SIZE_X  # End fog at render distance
