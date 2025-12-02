from __future__ import annotations

from typing import Callable, Optional, List

from panda3d.core import (
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
)

from . import settings
from .util import index_3d, get_biome
from .texture_manager import TextureManager, get_block_texture_name

# Global texture manager instance
_texture_manager = None

def init_texture_manager():
    """Initialize the global texture manager."""
    global _texture_manager
    if _texture_manager is None:
        _texture_manager = TextureManager()
    return _texture_manager

def get_texture_manager():
    """Get the global texture manager."""
    return _texture_manager


# Block ids
BLOCK_AIR = 0
BLOCK_GRASS = 1
BLOCK_DIRT = 2
BLOCK_STONE = 3
BLOCK_BEDROCK = 4
BLOCK_SAND = 5
BLOCK_WOOD = 6
BLOCK_LEAVES = 7
BLOCK_COBBLESTONE = 8
BLOCK_BRICK = 9
BLOCK_SANDSTONE = 10
BLOCK_CACTUS = 11

# Crafting materials
BLOCK_PLANKS = 12
BLOCK_STICKS = 13

# Tools
BLOCK_PICKAXE_WOOD = 14
BLOCK_PICKAXE_STONE = 15
BLOCK_PICKAXE_IRON = 16
BLOCK_AXE_WOOD = 17
BLOCK_AXE_STONE = 18
BLOCK_AXE_IRON = 19
BLOCK_SHOVEL_WOOD = 20
BLOCK_SHOVEL_STONE = 21
BLOCK_SHOVEL_IRON = 22
BLOCK_SWORD_WOOD = 23
BLOCK_SWORD_STONE = 24
BLOCK_SWORD_IRON = 25

# Crafting stations and storage
BLOCK_CRAFTING_TABLE = 26
BLOCK_FURNACE = 27
BLOCK_CHEST = 28

# Materials for advanced crafting
BLOCK_IRON_INGOT = 29

# Jungle Biome Blocks
BLOCK_JUNGLE_LOG = 30
BLOCK_JUNGLE_LEAVES = 31

# Birch Biome Blocks
BLOCK_BIRCH_LOG = 32
BLOCK_BIRCH_LEAVES = 33

# New Plank Types
BLOCK_JUNGLE_PLANKS = 38
BLOCK_BIRCH_PLANKS = 39

# Ores
BLOCK_COAL_ORE = 34
BLOCK_IRON_ORE = 35
BLOCK_DIAMOND_ORE = 36
BLOCK_GOLD_ORE = 37


def is_block_solid(block_id: int) -> bool:
    return block_id != BLOCK_AIR


def face_color(block_id: int, face: str, biome: str = 'plains'):
    """
    Return RGBA color for a given block face.
    Faces: 'top', 'bottom', 'side'
    """
    if block_id == BLOCK_GRASS:
        if face == "top":
            if biome == 'jungle':
                return settings.COLOR_JUNGLE_GRASS_TOP
            return settings.COLOR_GRASS_TOP
        elif face == "bottom":
            return settings.COLOR_DIRT
        else:
            if biome == 'jungle':
                return settings.COLOR_JUNGLE_SIDES_GRASS
            return settings.COLOR_SIDES_GRASS
    elif block_id == BLOCK_DIRT:
        return settings.COLOR_DIRT
    elif block_id == BLOCK_STONE:
        return settings.COLOR_STONE
    elif block_id == BLOCK_BEDROCK:
        return settings.COLOR_BEDROCK
    elif block_id == BLOCK_SAND:
        return settings.COLOR_SAND
    elif block_id == BLOCK_WOOD:
        if face == "top" or face == "bottom":
            return settings.COLOR_WOOD_TOP
        else:
            return settings.COLOR_WOOD
    elif block_id == BLOCK_LEAVES:
        return settings.COLOR_LEAVES
    elif block_id == BLOCK_COBBLESTONE:
        return settings.COLOR_COBBLESTONE
    elif block_id == BLOCK_BRICK:
        return settings.COLOR_BRICK
    elif block_id == BLOCK_SANDSTONE:
        return settings.COLOR_SANDSTONE
    elif block_id == BLOCK_CACTUS:
        return settings.COLOR_CACTUS
    elif block_id == BLOCK_PLANKS:
        return (0.65, 0.45, 0.25, 1.0)  # Wooden planks
    elif block_id == BLOCK_JUNGLE_PLANKS:
        return (0.55, 0.35, 0.25, 1.0)  # Jungle planks (darker/pinkish)
    elif block_id == BLOCK_BIRCH_PLANKS:
        return (0.85, 0.80, 0.60, 1.0)  # Birch planks (lighter/pale)
    elif block_id == BLOCK_STICKS:
        return (0.55, 0.35, 0.20, 1.0)  # Wooden sticks
    elif block_id in (BLOCK_PICKAXE_WOOD, BLOCK_PICKAXE_STONE, BLOCK_PICKAXE_IRON,
                      BLOCK_AXE_WOOD, BLOCK_AXE_STONE, BLOCK_AXE_IRON):
        return (0.6, 0.6, 0.6, 1.0)  # Tool silver
    elif block_id in (BLOCK_SHOVEL_WOOD, BLOCK_SHOVEL_STONE, BLOCK_SHOVEL_IRON):
        return (0.7, 0.7, 0.7, 1.0)  # Tool silver-light
    elif block_id in (BLOCK_SWORD_WOOD, BLOCK_SWORD_STONE, BLOCK_SWORD_IRON):
        return (0.8, 0.8, 0.8, 1.0)  # Tool silver-bright
    elif block_id == BLOCK_CRAFTING_TABLE:
        if face in ("top", "bottom"):
            return (0.7, 0.5, 0.3, 1.0)  # Crafting table wood
        else:
            return (0.6, 0.4, 0.2, 1.0)  # Crafting table sides
    elif block_id == BLOCK_FURNACE:
        return (0.4, 0.4, 0.4, 1.0)  # Furnace gray
    elif block_id == BLOCK_CHEST:
        return (0.6, 0.4, 0.2, 1.0)  # Chest wood
    elif block_id == BLOCK_IRON_INGOT:
        return (0.8, 0.8, 0.8, 1.0)  # Iron ingot silver
    elif block_id == BLOCK_JUNGLE_LOG:
        if face == "top" or face == "bottom":
            return (0.4, 0.3, 0.2, 1.0)  # Darker wood top
        else:
            return (0.35, 0.25, 0.15, 1.0)  # Darker wood side
    elif block_id == BLOCK_JUNGLE_LEAVES:
        return (0.1, 0.5, 0.1, 1.0)  # Darker green leaves
    elif block_id == BLOCK_BIRCH_LOG:
        if face == "top" or face == "bottom":
            return (0.9, 0.85, 0.7, 1.0)  # Light wood top
        else:
            return (0.95, 0.95, 0.95, 1.0)  # White bark
    elif block_id == BLOCK_BIRCH_LEAVES:
        return (0.4, 0.7, 0.4, 1.0)  # Lighter green leaves
    elif block_id in (BLOCK_COAL_ORE, BLOCK_IRON_ORE, BLOCK_DIAMOND_ORE, BLOCK_GOLD_ORE):
        return settings.COLOR_STONE  # Base stone color, texture will provide detail
    else:
        # Default visible color if some unknown id slips through
        return (1.0, 0.0, 1.0, 1.0)


class Chunk:
    """
    Stores block data for a (cx, cz) chunk and can build a Panda3D Geom for visible faces.
    Coordinate system:
      - World 'x' and 'z' are horizontal axes (XZ plane)
      - World 'y' is vertical (up)
      - Panda3D uses (X, Y, Z) with Z up. We map: Panda(X, Y, Z) = (world_x, world_z, world_y).
    """

    __slots__ = ("cx", "cz", "blocks", "node", "dirty")

    def __init__(self, cx: int, cz: int):
        self.cx = cx
        self.cz = cz
        # 1D array of size CHUNK_SIZE_X * CHUNK_SIZE_Y * CHUNK_SIZE_Z
        self.blocks: List[int] = [BLOCK_AIR] * (settings.CHUNK_SIZE_X * settings.CHUNK_SIZE_Y * settings.CHUNK_SIZE_Z)
        self.node: Optional[GeomNode] = None
        self.dirty: bool = True

    def set_block_local(self, lx: int, y: int, lz: int, block_id: int) -> None:
        if 0 <= lx < settings.CHUNK_SIZE_X and 0 <= y < settings.CHUNK_SIZE_Y and 0 <= lz < settings.CHUNK_SIZE_Z:
            self.blocks[index_3d(lx, y, lz)] = block_id
            self.dirty = True

    def get_block_local(self, lx: int, y: int, lz: int) -> int:
        if 0 <= lx < settings.CHUNK_SIZE_X and 0 <= y < settings.CHUNK_SIZE_Y and 0 <= lz < settings.CHUNK_SIZE_Z:
            return self.blocks[index_3d(lx, y, lz)]
        return BLOCK_AIR

    def build_mesh(self, is_world_solid: Callable[[int, int, int], bool]) -> Optional[GeomNode]:
        """
        Build a GeomNode containing all visible faces for this chunk.
        is_world_solid(wx, wy, wz) is used so culling works across chunk borders.
        Returns a GeomNode or None if no faces.
        """
        # Use format with texture coordinates
        fmt = GeomVertexFormat.getV3n3c4t2()
        vdata = GeomVertexData("chunk", fmt, Geom.UHStatic)

        vw = GeomVertexWriter(vdata, "vertex")
        nw = GeomVertexWriter(vdata, "normal")
        cw = GeomVertexWriter(vdata, "color")
        tw = GeomVertexWriter(vdata, "texcoord")

        prim = GeomTriangles(Geom.UHStatic)

        add_quad = _make_quad_adder(vw, nw, cw, tw, prim)

        # For each solid block, add faces where neighbor is not solid
        vx_count = 0

        # Chunk world origin
        wx0 = self.cx * settings.CHUNK_SIZE_X
        wz0 = self.cz * settings.CHUNK_SIZE_Z
        
        # Get texture manager for UV lookups
        tm = get_texture_manager()

        for y in range(settings.CHUNK_SIZE_Y):
            for lz in range(settings.CHUNK_SIZE_Z):
                for lx in range(settings.CHUNK_SIZE_X):
                    block_id = self.get_block_local(lx, y, lz)
                    if not is_block_solid(block_id):
                        continue

                    wx = wx0 + lx
                    wz = wz0 + lz

                    # Determine biome for color tinting
                    biome = 'plains'
                    if block_id == BLOCK_GRASS:
                        biome = get_biome(wx, wz)
                    
                    # Quick check: if all 6 neighbors are solid, skip this block entirely
                    if (is_world_solid(wx, y + 1, wz) and 
                        (y == 0 or is_world_solid(wx, y - 1, wz)) and
                        is_world_solid(wx + 1, y, wz) and
                        is_world_solid(wx - 1, y, wz) and
                        is_world_solid(wx, y, wz + 1) and
                        is_world_solid(wx, y, wz - 1)):
                        continue

                    # Top (+Y -> Panda +Z)
                    if not is_world_solid(wx, y + 1, wz):
                        c = face_color(block_id, "top", biome)
                        tex_name = get_block_texture_name(block_id, "top")
                        uvs = tm.get_uvs(tex_name)
                        if not uvs:
                             # Fallback to stone if texture missing
                             uvs = tm.get_uvs('stone')
                             if not uvs: uvs = (0, 0, 1, 1)
                        
                        add_quad(
                            (lx,     lz,     y + 1),
                            (lx + 1, lz,     y + 1),
                            (lx + 1, lz + 1, y + 1),
                            (lx,     lz + 1, y + 1),
                            (0.0, 0.0, 1.0),
                            c,
                            uvs
                        )
                        vx_count += 4

                    # Bottom (-Y -> Panda -Z)
                    if y == 0 or not is_world_solid(wx, y - 1, wz):
                        c = face_color(block_id, "bottom", biome)
                        tex_name = get_block_texture_name(block_id, "bottom")
                        uvs = tm.get_uvs(tex_name)
                        if not uvs:
                             uvs = tm.get_uvs('stone')
                             if not uvs: uvs = (0, 0, 1, 1)
                        
                        add_quad(
                            (lx,     lz + 1, y),
                            (lx + 1, lz + 1, y),
                            (lx + 1, lz,     y),
                            (lx,     lz,     y),
                            (0.0, 0.0, -1.0),
                            c,
                            uvs
                        )
                        vx_count += 4

                    # +X face (right)
                    if not is_world_solid(wx + 1, y, wz):
                        c = face_color(block_id, "side", biome)
                        tex_name = get_block_texture_name(block_id, "side")
                        uvs = tm.get_uvs(tex_name)
                        if not uvs:
                             uvs = tm.get_uvs('stone')
                             if not uvs: uvs = (0, 0, 1, 1)
                        
                        add_quad(
                            (lx + 1, lz,     y),
                            (lx + 1, lz + 1, y),
                            (lx + 1, lz + 1, y + 1),
                            (lx + 1, lz,     y + 1),
                            (1.0, 0.0, 0.0),
                            c,
                            uvs
                        )
                        vx_count += 4

                    # -X face (left)
                    if not is_world_solid(wx - 1, y, wz):
                        c = face_color(block_id, "side", biome)
                        tex_name = get_block_texture_name(block_id, "side")
                        uvs = tm.get_uvs(tex_name)
                        if not uvs:
                             uvs = tm.get_uvs('stone')
                             if not uvs: uvs = (0, 0, 1, 1)
                        
                        add_quad(
                            (lx, lz + 1, y),
                            (lx, lz,     y),
                            (lx, lz,     y + 1),
                            (lx, lz + 1, y + 1),
                            (-1.0, 0.0, 0.0),
                            c,
                            uvs
                        )
                        vx_count += 4

                    # +Z face (front) -> Panda +Y
                    if not is_world_solid(wx, y, wz + 1):
                        c = face_color(block_id, "side", biome)
                        tex_name = get_block_texture_name(block_id, "side")
                        uvs = tm.get_uvs(tex_name)
                        if not uvs:
                             uvs = tm.get_uvs('stone')
                             if not uvs: uvs = (0, 0, 1, 1)
                        
                        add_quad(
                            (lx + 1, lz + 1, y),
                            (lx,     lz + 1, y),
                            (lx,     lz + 1, y + 1),
                            (lx + 1, lz + 1, y + 1),
                            (0.0, 1.0, 0.0),
                            c,
                            uvs
                        )
                        vx_count += 4

                    # -Z face (back) -> Panda -Y
                    if not is_world_solid(wx, y, wz - 1):
                        c = face_color(block_id, "side", biome)
                        tex_name = get_block_texture_name(block_id, "side")
                        uvs = tm.get_uvs(tex_name)
                        if not uvs:
                             uvs = tm.get_uvs('stone')
                             if not uvs: uvs = (0, 0, 1, 1)
                        
                        add_quad(
                            (lx,     lz,     y),
                            (lx + 1, lz,     y),
                            (lx + 1, lz,     y + 1),
                            (lx,     lz,     y + 1),
                            (0.0, -1.0, 0.0),
                            c,
                            uvs
                        )
                        vx_count += 4

        if prim.getNumPrimitives() == 0:
            self.node = None
            return None

        geom = Geom(vdata)
        geom.addPrimitive(prim)

        node = GeomNode(f"chunk-{self.cx}-{self.cz}")
        node.addGeom(geom)
        self.node = node
        self.dirty = False
        return node


def _make_quad_adder(vw: GeomVertexWriter, nw: GeomVertexWriter, cw: GeomVertexWriter, tw: GeomVertexWriter, prim: GeomTriangles):
    """
    Returns a function that appends a quad given 4 vertices in chunk-local world-coords
    (x, z, y) mapping -> Panda (X, Y, Z) as (x, z, y), plus a Panda-space normal (nx, ny, nz)
    and color RGBA. Now includes texture coordinates.
    """
    def add_quad(v0, v1, v2, v3, normal, color, uvs=(0, 0, 1, 1)):
        base = vw.getWriteRow()
        
        # Apply simple ambient occlusion-style shading based on face direction
        nx, ny, nz = normal
        shade_factor = 1.0
        
        if nz > 0.5:  # Top face
            shade_factor = 1.0
        elif nz < -0.5:  # Bottom face
            shade_factor = 0.5
        elif abs(nx) > 0.5:  # East/West faces
            shade_factor = 0.75
        else:  # North/South faces
            shade_factor = 0.85
        
        r, g, b, a = color
        r *= shade_factor
        g *= shade_factor
        b *= shade_factor
        
        offset = 0.001
        
        # Unpack UVs: u_min, v_min, u_max, v_max
        u_min, v_min, u_max, v_max = uvs
        
        # Map corners to UVs
        # v0 (0,0) -> (u_min, v_min)
        # v1 (1,0) -> (u_max, v_min)
        # v2 (1,1) -> (u_max, v_max)
        # v3 (0,1) -> (u_min, v_max)
        
        # Wait, standard quad order:
        # v0: bottom-left (local 0,0)
        # v1: bottom-right (local 1,0)
        # v2: top-right (local 1,1)
        # v3: top-left (local 0,1)
        
        # Atlas UVs:
        # u_min, v_min is bottom-left of the sub-texture
        # u_max, v_max is top-right of the sub-texture
        
        quad_uvs = [
            (u_min, v_min), # v0
            (u_max, v_min), # v1
            (u_max, v_max), # v2
            (u_min, v_max)  # v3
        ]
        
        for i, v in enumerate((v0, v1, v2, v3)):
            x, z, y = v
            
            # Procedural variation (simplified for performance/atlas compatibility)
            # We can still tint, but we rely more on the texture now
            
            # Add texture coordinates
            tw.addData2f(*quad_uvs[i])
            
            # Add vertex data
            vw.addData3f(x + nx * offset, z + ny * offset, y + nz * offset)
            nw.addData3f(nx, ny, nz)
            cw.addData4f(r, g, b, a) # Use tinted color (white * shade)
        
        prim.addVertices(base + 0, base + 1, base + 2)
        prim.addVertices(base + 0, base + 2, base + 3)

    return add_quad
