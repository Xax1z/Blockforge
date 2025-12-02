"""
Universal drop system for items dropped by mobs and blocks.
Handles drop spawning, physics, and collection.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from panda3d.core import NodePath, Vec3, GeomNode
from math import floor, sqrt
import random

from . import settings
from .util import AABB


class DroppedItem:
    """Represents a dropped item in the world."""
    
    def __init__(self, item_type: int, position: Vec3, velocity: Vec3 = None):
        self.item_type = item_type
        self.position = Vec3(position)
        self.velocity = velocity if velocity else Vec3(0, 0, 0)
        self.age = 0.0  # How long the item has existed (in seconds)
        self.pickup_delay = 0.5  # Can't be picked up for first 0.5 seconds
        self.max_age = 300.0  # Despawn after 5 minutes (300 seconds)
        self.on_ground = False
        self.node_path: Optional[NodePath] = None
        
    def get_aabb(self) -> AABB:
        """Get collision box for the dropped item."""
        size = 0.25  # Small collision box
        return AABB(
            self.position.x - size,
            self.position.y - size,
            self.position.z - size,
            self.position.x + size,
            self.position.y + size,
            self.position.z + size
        )
    
    def is_collectable(self) -> bool:
        """Check if item can be collected by player."""
        return self.age >= self.pickup_delay
    
    def should_despawn(self) -> bool:
        """Check if item should despawn."""
        return self.age >= self.max_age


class DropSystem:
    """Manages all dropped items in the world."""
    
    def __init__(self, render: NodePath, world):
        self.render = render
        self.world = world
        self.root = self.render.attachNewNode("drops-root")
        self.dropped_items: List[DroppedItem] = []
        
        # Initialize texture manager
        from .chunk import get_texture_manager
        self.texture_manager = get_texture_manager()
        
        # Cache for block colors (used for rendering dropped items)
        from .chunk import (
            BLOCK_GRASS, BLOCK_DIRT, BLOCK_STONE, BLOCK_SAND,
            BLOCK_WOOD, BLOCK_LEAVES, BLOCK_COBBLESTONE, BLOCK_BRICK,
            BLOCK_SANDSTONE, BLOCK_PLANKS, BLOCK_STICKS
        )
        
        self.item_colors = {
            BLOCK_GRASS: settings.COLOR_GRASS_TOP,
            BLOCK_DIRT: settings.COLOR_DIRT,
            BLOCK_STONE: settings.COLOR_STONE,
            BLOCK_SAND: settings.COLOR_SAND,
            BLOCK_WOOD: settings.COLOR_WOOD,
            BLOCK_LEAVES: settings.COLOR_LEAVES,
            BLOCK_COBBLESTONE: settings.COLOR_COBBLESTONE,
            BLOCK_BRICK: settings.COLOR_BRICK,
            BLOCK_SANDSTONE: settings.COLOR_SANDSTONE,
            BLOCK_PLANKS: (0.65, 0.45, 0.25, 1.0),
            BLOCK_STICKS: (0.9, 0.7, 0.3, 1.0),
            # Meat items (new)
            100: (0.9, 0.4, 0.4, 1.0),  # RAW_MEAT (red)
            101: (0.95, 0.85, 0.7, 1.0),  # RAW_CHICKEN (pale yellow)
            102: (0.95, 0.7, 0.7, 1.0),  # RAW_PORK (pink)
        }
    
    def spawn_drop(self, item_type: int, position: Vec3, velocity: Vec3 = None) -> DroppedItem:
        """Spawn a dropped item at position with optional velocity."""
        if velocity is None:
            # Random small velocity for scatter effect
            velocity = Vec3(
                random.uniform(-1.5, 1.5),
                random.uniform(2.0, 4.0),  # Pop upward
                random.uniform(-1.5, 1.5)
            )
        
        dropped = DroppedItem(item_type, position, velocity)
        self.dropped_items.append(dropped)
        
        # Create visual representation
        self._create_item_mesh(dropped)
        
        return dropped
    
    def _create_item_mesh(self, item: DroppedItem) -> None:
        """Create a small cube mesh for the dropped item with texture."""
        from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexWriter
        from panda3d.core import Geom, GeomTriangles, GeomNode
        
        # Create vertex data with texture coordinates
        vformat = GeomVertexFormat.getV3c4t2()
        vdata = GeomVertexData("item", vformat, Geom.UHStatic)
        
        vertex = GeomVertexWriter(vdata, "vertex")
        color = GeomVertexWriter(vdata, "color")
        texcoord = GeomVertexWriter(vdata, "texcoord")
        
        # Get item color (for shading/fallback)
        item_color = self.item_colors.get(item.item_type, (1, 1, 1, 1))
        
        # Small rotating cube (0.25 units size)
        size = 0.125  # Half of 0.25
        
        # Define cube vertices with UV coords
        # Each face gets proper UV mapping
        cube_faces = [
            # Back face (-Y)
            [(-size, -size, -size), (size, -size, -size), (size, -size, size), (-size, -size, size)],
            # Front face (+Y)
            [(-size, size, -size), (-size, size, size), (size, size, size), (size, size, -size)],
            # Left face (-X)
            [(-size, -size, -size), (-size, -size, size), (-size, size, size), (-size, size, -size)],
            # Right face (+X)
            [(size, -size, -size), (size, size, -size), (size, size, size), (size, -size, size)],
            # Bottom face (-Z)
            [(-size, -size, -size), (-size, size, -size), (size, size, -size), (size, -size, -size)],
            # Top face (+Z)
            [(-size, -size, size), (size, -size, size), (size, size, size), (-size, size, size)],
        ]
        
        uv_coords = [(0, 0), (1, 0), (1, 1), (0, 1)]
        
        tris = GeomTriangles(Geom.UHStatic)
        vert_count = 0
        
        # Create each face
        for face_verts in cube_faces:
            for i, v in enumerate(face_verts):
                vertex.addData3(*v)
                color.addData4f(*item_color)
                texcoord.addData2f(*uv_coords[i])
            
            # Two triangles per face
            tris.addVertices(vert_count, vert_count + 1, vert_count + 2)
            tris.addVertices(vert_count, vert_count + 2, vert_count + 3)
            vert_count += 4
        
        tris.closePrimitive()
        
        # Create geom and node
        geom = Geom(vdata)
        geom.addPrimitive(tris)
        
        node = GeomNode("dropped_item")
        node.addGeom(geom)
        
        # Attach to scene
        item.node_path = self.root.attachNewNode(node)
        item.node_path.setPos(item.position.x, item.position.z, item.position.y)
        
        # Apply texture if available
        if self.texture_manager:
            texture = self._get_item_texture(item.item_type)
            if texture:
                item.node_path.setTexture(texture)
    
    def _get_item_texture(self, item_type: int):
        """Get the appropriate texture for an item type."""
        from .texture_manager import BLOCK_TEXTURES as TEX_MAP
        
        # Check if it's a block
        texture_name = TEX_MAP.get(item_type)
        if texture_name:
            return self.texture_manager.get_block_texture(texture_name)
        
        # Check if it's meat
        if item_type == 100:  # RAW_MEAT
            return self.texture_manager.get_meat_texture('raw_meat')
        elif item_type == 101:  # RAW_CHICKEN
            return self.texture_manager.get_meat_texture('raw_chicken')
        elif item_type == 102:  # RAW_PORK
            return self.texture_manager.get_meat_texture('raw_pork')
        
        # Default to stone if not found
        return self.texture_manager.get_block_texture('stone')
    
    def update(self, dt: float, player_position: Vec3) -> List[int]:
        """
        Update all dropped items (physics, aging, collection).
        Returns list of item types collected by player this frame.
        """
        collected_items = []
        items_to_remove = []
        
        for item in self.dropped_items:
            # Update age
            item.age += dt
            
            # Check for despawn
            if item.should_despawn():
                items_to_remove.append(item)
                continue
            
            # Apply physics
            self._update_item_physics(item, dt)
            
            # Check for player collection
            if item.is_collectable():
                if self._check_player_collection(item, player_position):
                    collected_items.append(item.item_type)
                    items_to_remove.append(item)
                    continue
            
            # Update visual position
            if item.node_path:
                item.node_path.setPos(item.position.x, item.position.z, item.position.y)
                # Rotate for visual effect
                item.node_path.setH(item.age * 90.0)  # Rotate 90 degrees per second
        
        # Remove collected/despawned items
        for item in items_to_remove:
            if item in self.dropped_items:
                self.dropped_items.remove(item)
            if item.node_path:
                item.node_path.removeNode()
        
        return collected_items
    
    def _update_item_physics(self, item: DroppedItem, dt: float) -> None:
        """Apply physics to dropped item (gravity, collision)."""
        # Apply gravity
        item.velocity.y -= settings.GRAVITY * dt
        
        # Apply movement
        dx = item.velocity.x * dt
        dy = item.velocity.y * dt
        dz = item.velocity.z * dt
        
        aabb = item.get_aabb()
        
        # X axis collision
        allowed_dx, hit_x = self._sweep_axis(aabb, dx, axis="x")
        if allowed_dx != dx:
            item.velocity.x = 0.0
        aabb = aabb.moved(allowed_dx, 0.0, 0.0)
        item.position.x += allowed_dx
        
        # Y axis collision (vertical)
        allowed_dy, hit_y = self._sweep_axis(aabb, dy, axis="y")
        if allowed_dy != dy:
            if dy < 0.0:
                item.on_ground = True
                # Apply friction when on ground
                item.velocity.x *= 0.85
                item.velocity.z *= 0.85
            item.velocity.y = 0.0
        else:
            item.on_ground = False
        aabb = aabb.moved(0.0, allowed_dy, 0.0)
        item.position.y += allowed_dy
        
        # Z axis collision
        allowed_dz, hit_z = self._sweep_axis(aabb, dz, axis="z")
        if allowed_dz != dz:
            item.velocity.z = 0.0
        aabb = aabb.moved(0.0, 0.0, allowed_dz)
        item.position.z += allowed_dz
    
    def _sweep_axis(self, aabb: AABB, delta: float, axis: str) -> Tuple[float, bool]:
        """Simplified collision detection for items."""
        if delta == 0.0:
            return 0.0, False
        
        eps = settings.EPSILON
        
        if axis == "x":
            if delta > 0.0:
                sweep_min_x = floor(aabb.min_x)
                sweep_max_x = floor(aabb.max_x + delta) + 1
            else:
                sweep_min_x = floor(aabb.min_x + delta)
                sweep_max_x = floor(aabb.max_x) + 1
            
            sweep_min_y = floor(aabb.min_y)
            sweep_max_y = floor(aabb.max_y) + 1
            sweep_min_z = floor(aabb.min_z)
            sweep_max_z = floor(aabb.max_z) + 1
            
            allowed = delta
            hit = False
            
            for bx in range(sweep_min_x, sweep_max_x + 1):
                for by in range(sweep_min_y, sweep_max_y + 1):
                    for bz in range(sweep_min_z, sweep_max_z + 1):
                        if not self.world.solid_at(bx, by, bz):
                            continue
                        
                        from .util import block_aabb
                        blk = block_aabb(bx, by, bz)
                        
                        if aabb.max_y <= blk.min_y or aabb.min_y >= blk.max_y:
                            continue
                        if aabb.max_z <= blk.min_z or aabb.min_z >= blk.max_z:
                            continue
                        
                        if delta > 0.0:
                            if aabb.max_x <= blk.min_x and aabb.max_x + delta > blk.min_x:
                                allowed = min(allowed, blk.min_x - aabb.max_x - eps)
                                hit = True
                        else:
                            if aabb.min_x >= blk.max_x and aabb.min_x + delta < blk.max_x:
                                allowed = max(allowed, blk.max_x - aabb.min_x + eps)
                                hit = True
            
            return allowed, hit
        
        elif axis == "y":
            sweep_min_x = floor(aabb.min_x)
            sweep_max_x = floor(aabb.max_x) + 1
            
            if delta > 0.0:
                sweep_min_y = floor(aabb.min_y)
                sweep_max_y = floor(aabb.max_y + delta) + 1
            else:
                sweep_min_y = floor(aabb.min_y + delta)
                sweep_max_y = floor(aabb.max_y) + 1
            
            sweep_min_z = floor(aabb.min_z)
            sweep_max_z = floor(aabb.max_z) + 1
            
            allowed = delta
            hit = False
            
            for bx in range(sweep_min_x, sweep_max_x + 1):
                for by in range(sweep_min_y, sweep_max_y + 1):
                    for bz in range(sweep_min_z, sweep_max_z + 1):
                        if not self.world.solid_at(bx, by, bz):
                            continue
                        
                        from .util import block_aabb
                        blk = block_aabb(bx, by, bz)
                        
                        if aabb.max_x <= blk.min_x or aabb.min_x >= blk.max_x:
                            continue
                        if aabb.max_z <= blk.min_z or aabb.min_z >= blk.max_z:
                            continue
                        
                        if delta > 0.0:
                            if aabb.max_y <= blk.min_y and aabb.max_y + delta > blk.min_y:
                                allowed = min(allowed, blk.min_y - aabb.max_y - eps)
                                hit = True
                        else:
                            if aabb.min_y >= blk.max_y and aabb.min_y + delta < blk.max_y:
                                allowed = max(allowed, blk.max_y - aabb.min_y + eps)
                                hit = True
            
            return allowed, hit
        
        else:  # axis == "z"
            sweep_min_x = floor(aabb.min_x)
            sweep_max_x = floor(aabb.max_x) + 1
            sweep_min_y = floor(aabb.min_y)
            sweep_max_y = floor(aabb.max_y) + 1
            
            if delta > 0.0:
                sweep_min_z = floor(aabb.min_z)
                sweep_max_z = floor(aabb.max_z + delta) + 1
            else:
                sweep_min_z = floor(aabb.min_z + delta)
                sweep_max_z = floor(aabb.max_z) + 1
            
            allowed = delta
            hit = False
            
            for bx in range(sweep_min_x, sweep_max_x + 1):
                for by in range(sweep_min_y, sweep_max_y + 1):
                    for bz in range(sweep_min_z, sweep_max_z + 1):
                        if not self.world.solid_at(bx, by, bz):
                            continue
                        
                        from .util import block_aabb
                        blk = block_aabb(bx, by, bz)
                        
                        if aabb.max_x <= blk.min_x or aabb.min_x >= blk.max_x:
                            continue
                        if aabb.max_y <= blk.min_y or aabb.min_y >= blk.max_y:
                            continue
                        
                        if delta > 0.0:
                            if aabb.max_z <= blk.min_z and aabb.max_z + delta > blk.min_z:
                                allowed = min(allowed, blk.min_z - aabb.max_z - eps)
                                hit = True
                        else:
                            if aabb.min_z >= blk.max_z and aabb.min_z + delta < blk.max_z:
                                allowed = max(allowed, blk.max_z - aabb.min_z + eps)
                                hit = True
            
            return allowed, hit
    
    def _check_player_collection(self, item: DroppedItem, player_position: Vec3) -> bool:
        """Check if player is close enough to collect item."""
        collection_radius = 1.5  # Player can collect items within 1.5 units
        
        dx = item.position.x - player_position.x
        dy = item.position.y - player_position.y
        dz = item.position.z - player_position.z
        
        distance_sq = dx * dx + dy * dy + dz * dz
        
        return distance_sq < (collection_radius * collection_radius)
    
    def cleanup(self) -> None:
        """Clean up all dropped items."""
        for item in self.dropped_items:
            if item.node_path:
                item.node_path.removeNode()
        
        self.dropped_items.clear()
        
        if self.root and not self.root.isEmpty():
            self.root.removeNode()
