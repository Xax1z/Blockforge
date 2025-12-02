"""
Mob system for spawning and managing animals (sheep, cows, chickens, pigs).
Mobs have physics, collision, AI, health, and can be killed for drops.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from panda3d.core import NodePath, Vec3, GeomNode
from math import floor, sqrt, sin, cos, radians
import random

from . import settings
from .util import AABB, terrain_height


# Mob type constants
MOB_SHEEP = 0
MOB_COW = 1
MOB_CHICKEN = 2
MOB_PIG = 3
MOB_CREEPER = 4
MOB_ZOMBIE = 5
MOB_SKELETON = 6

# Item type constants for drops
ITEM_RAW_MEAT = 100     # Beef/mutton (sheep/cow drop)
ITEM_RAW_CHICKEN = 101  # Chicken drops
ITEM_RAW_PORK = 102     # Pig drops
ITEM_ROTTEN_FLESH = 103 # Zombie drop
ITEM_BONE = 104         # Skeleton drop
ITEM_GUNPOWDER = 105    # Creeper drop


class Mob:
    """Base class for all mobs."""
    
    def __init__(self, mob_type: int, position: Vec3, world):
        self.mob_type = mob_type
        self.position = Vec3(position)
        self.world = world
        self.velocity = Vec3(0, 0, 0)
        self.on_ground = False
        
        # Visual representation
        self.node_path: Optional[NodePath] = None
        self.color = (1, 1, 1, 1)
        self.size = Vec3(0.6, 0.9, 0.6)  # width, height, depth (same as player collision)
        
        # AI state
        self.wander_timer = 0.0
        self.wander_direction = random.uniform(0, 360)
        self.idle_timer = random.uniform(2.0, 5.0)
        self.is_idle = True
        
        # Hostile AI
        self.is_hostile = False
        self.attack_damage = 0.0
        self.attack_range = 1.5
        self.detection_range = 16.0
        self.attack_cooldown = 0.0
        self.move_speed = 1.5
        
        # Health and damage
        self.max_health = 10.0
        self.health = self.max_health
        self.is_dead = False
        self.death_timer = 0.0
        self.hit_cooldown = 0.0  # Prevent multiple hits in quick succession
        
        # Movement capability
        self.jump_force = 8.0  # Ability to jump over 1 block
        self.jump_cooldown = 0.0
        
        # Spawn position (for render distance check)
        self.spawn_chunk_x = floor(position.x / settings.CHUNK_SIZE_X)
        self.spawn_chunk_z = floor(position.z / settings.CHUNK_SIZE_Z)
        
        # Configure mob-specific properties
        self._configure_mob()
    
    def _configure_mob(self):
        """Configure mob-specific properties based on type."""
        if self.mob_type == MOB_SHEEP:
            self.color = (0.95, 0.95, 0.95, 1.0)  # White
            self.size = Vec3(0.6, 0.8, 0.6)
            self.max_health = 8.0
            self.health = self.max_health
        elif self.mob_type == MOB_COW:
            self.color = (0.3, 0.2, 0.15, 1.0)  # Brown
            self.size = Vec3(0.7, 1.0, 0.7)
            self.max_health = 10.0
            self.health = self.max_health
        elif self.mob_type == MOB_CHICKEN:
            self.color = (0.95, 0.95, 0.95, 1.0)  # White
            self.size = Vec3(0.4, 0.5, 0.4)
            self.max_health = 4.0
            self.health = self.max_health
        elif self.mob_type == MOB_PIG:
            self.color = (0.95, 0.7, 0.7, 1.0)  # Pink
            self.size = Vec3(0.6, 0.8, 0.6)
            self.max_health = 10.0
            self.health = self.max_health
        elif self.mob_type == MOB_CREEPER:
            self.color = (0.0, 0.8, 0.0, 1.0)   # Green
            self.size = Vec3(0.6, 1.7, 0.6)
            self.max_health = 20.0
            self.health = self.max_health
            self.is_hostile = True
            self.attack_damage = 10.0 # High damage (explosion simulation)
            self.move_speed = 2.0
        elif self.mob_type == MOB_ZOMBIE:
            self.color = (0.0, 0.6, 0.2, 1.0)   # Dark Green
            self.size = Vec3(0.6, 1.95, 0.6)
            self.max_health = 20.0
            self.health = self.max_health
            self.is_hostile = True
            self.attack_damage = 3.0
            self.move_speed = 2.0
        elif self.mob_type == MOB_SKELETON:
            self.color = (0.8, 0.8, 0.8, 1.0)   # Light Gray/Bone
            self.size = Vec3(0.5, 1.95, 0.5)    # Thinner
            self.max_health = 20.0
            self.health = self.max_health
            self.is_hostile = True
            self.attack_damage = 2.0 # Ranged usually, but melee for now
            self.move_speed = 2.0
    
    def get_aabb(self) -> AABB:
        """Get collision box for the mob (same system as player)."""
        half_w = self.size.x * 0.5
        half_d = self.size.z * 0.5
        return AABB(
            self.position.x - half_w,
            self.position.y,
            self.position.z - half_d,
            self.position.x + half_w,
            self.position.y + self.size.y,
            self.position.z + half_d
        )
    
    def damage(self, amount: float) -> bool:
        """
        Apply damage to the mob.
        Returns True if mob died from this damage.
        """
        if self.is_dead or self.hit_cooldown > 0.0:
            return False
        
        self.health -= amount
        self.hit_cooldown = 0.5  # 0.5 second cooldown between hits
        
        if self.health <= 0.0:
            self.health = 0.0
            self.is_dead = True
            return True
        
        return False
    
    def get_drops(self) -> List[int]:
        """Get item types this mob drops when killed."""
        if self.mob_type == MOB_SHEEP:
            # Sheep drop 1-2 raw meat
            return [ITEM_RAW_MEAT] * random.randint(1, 2)
        elif self.mob_type == MOB_COW:
            # Cows drop 1-3 raw meat
            return [ITEM_RAW_MEAT] * random.randint(1, 3)
        elif self.mob_type == MOB_CHICKEN:
            # Chickens drop 1 raw chicken
            return [ITEM_RAW_CHICKEN] * random.randint(1, 2)
        elif self.mob_type == MOB_PIG:
            # Pigs drop 1-3 raw pork
            return [ITEM_RAW_PORK] * random.randint(1, 3)
        elif self.mob_type == MOB_CREEPER:
            return [ITEM_GUNPOWDER] * random.randint(0, 2)
        elif self.mob_type == MOB_ZOMBIE:
            return [ITEM_ROTTEN_FLESH] * random.randint(0, 2)
        elif self.mob_type == MOB_SKELETON:
            return [ITEM_BONE] * random.randint(0, 2)
        return []
    
    def update(self, dt: float, player_position: Vec3, game_mode: str = "Survival", difficulty: int = 2) -> None:
        """Update mob AI, physics, and state."""
        if self.is_dead:
            self.death_timer += dt
            return
        
        # Update hit cooldown
        if self.hit_cooldown > 0.0:
            self.hit_cooldown -= dt

        # Update attack cooldown
        if self.attack_cooldown > 0.0:
            self.attack_cooldown -= dt
            
        # Update jump cooldown
        if self.jump_cooldown > 0.0:
            self.jump_cooldown -= dt
        
        # AI Update
        self._update_ai(dt, player_position, game_mode, difficulty)
        
        # Apply physics (same as player)
        self._update_physics(dt)
    
    def _update_ai(self, dt: float, player_position: Vec3, game_mode: str, difficulty: int) -> None:
        """Mob AI logic."""
        
        # Hostile Logic
        if self.is_hostile:
            # If Peaceful, should despawn (handled in MobSystem), but do nothing here
            if difficulty == settings.DIFFICULTY_PEACEFUL:
                 self.velocity.x = 0
                 self.velocity.z = 0
                 return
                 
            # If Creative, ignore player and wander
            if game_mode == "Creative":
                self._wander(dt)
                return
            
            # Survival Logic: Target Player
            dist_sq = (self.position.x - player_position.x)**2 + (self.position.z - player_position.z)**2
            dist = sqrt(dist_sq)
            
            if dist <= self.detection_range:
                # Move towards player
                dx = player_position.x - self.position.x
                dz = player_position.z - self.position.z
                
                # Normalize
                if dist > 0:
                    dx /= dist
                    dz /= dist
                
                # Determine speed based on difficulty?
                speed = self.move_speed
                if difficulty == settings.DIFFICULTY_HARD:
                    speed *= 1.2
                
                self.velocity.x = self._approach(self.velocity.x, dx * speed, 10.0 * dt)
                self.velocity.z = self._approach(self.velocity.z, dz * speed, 10.0 * dt)
                
                # Face direction
                # self.wander_direction ... (need to calculate angle from dx, dz)
                
                # Attack if close
                if dist <= self.attack_range and self.attack_cooldown <= 0.0:
                    self._attack_player(player_position)
                
            else:
                # Wander if player too far
                self._wander(dt)
                
        else:
            # Passive Logic
            self._wander(dt)

    def _wander(self, dt: float) -> None:
        """Standard wander behavior."""
        if self.is_idle:
            self.idle_timer -= dt
            if self.idle_timer <= 0.0:
                # Start wandering
                self.is_idle = False
                self.wander_timer = random.uniform(2.0, 4.0)
                self.wander_direction = random.uniform(0, 360)
        else:
            self.wander_timer -= dt
            if self.wander_timer <= 0.0:
                # Go idle
                self.is_idle = True
                self.idle_timer = random.uniform(2.0, 5.0)
            else:
                # Move in wander direction
                speed = 1.5  # Slow walking speed
                rad = radians(self.wander_direction)
                
                # Calculate desired velocity
                desired_x = sin(rad) * speed
                desired_z = cos(rad) * speed
                
                # Apply acceleration (like player but slower)
                accel = 10.0 if self.on_ground else 2.0
                self.velocity.x = self._approach(self.velocity.x, desired_x, accel * dt)
                self.velocity.z = self._approach(self.velocity.z, desired_z, accel * dt)

    def _attack_player(self, player_position: Vec3) -> None:
        """Attack the player."""
        self.attack_cooldown = 1.5 # Cooldown
        
        # We need access to the player object to damage it.
        # Currently we only have position. 
        # We can use MobSystem to handle the actual damage application via collision check or callback?
        # Or we can pass the player object instead of just position.
        # For now, let's assume Main loop checks distance and applies damage if Mob attacks.
        # But Mob needs to signal intent.
        
        # ACTUALLY: Main loop `_update` does `mob_system.update`.
        # We can check for attacks there or pass a callback.
        # Let's just return for now and handle actual damage in `main.py` or give `Mob` a reference to `Player`?
        # `Mob` has reference to `world`. `Player` is in `App` (main).
        
        # Let's change `update` signature to accept `player` object instead of position?
        # That would be cleaner.
        pass
    
    def _update_physics(self, dt: float) -> None:
        """Apply physics to mob (gravity, collision) - same as player."""
        # Apply gravity
        self.velocity.y -= settings.GRAVITY * dt
        
        # Integrate with collision (same as player)
        dx = self.velocity.x * dt
        dy = self.velocity.y * dt
        dz = self.velocity.z * dt
        
        aabb = self.get_aabb()
        
        # X axis
        allowed_dx, hit_x = self._sweep_axis(aabb, dx, axis="x")
        if allowed_dx != dx:
            self.velocity.x = 0.0
            
            # Try to jump if blocked and on ground
            if self.on_ground and self.jump_cooldown <= 0.0:
                self.velocity.y = self.jump_force
                self.on_ground = False
                self.jump_cooldown = 0.5
            else:
                # Hit a wall, change direction
                if not self.is_idle:
                    self.wander_direction = random.uniform(0, 360)
                    
        aabb = aabb.moved(allowed_dx, 0.0, 0.0)
        self.position.x += allowed_dx
        
        # Y axis
        allowed_dy, hit_y = self._sweep_axis(aabb, dy, axis="y")
        if allowed_dy != dy:
            if dy < 0.0:
                self.on_ground = True
            self.velocity.y = 0.0
        else:
            if dy > 0.0:
                self.on_ground = False
        aabb = aabb.moved(0.0, allowed_dy, 0.0)
        self.position.y += allowed_dy
        
        # Z axis
        allowed_dz, hit_z = self._sweep_axis(aabb, dz, axis="z")
        if allowed_dz != dz:
            self.velocity.z = 0.0
            
            # Try to jump if blocked and on ground
            if self.on_ground and self.jump_cooldown <= 0.0:
                self.velocity.y = self.jump_force
                self.on_ground = False
                self.jump_cooldown = 0.5
            else:
                # Hit a wall, change direction
                if not self.is_idle:
                    self.wander_direction = random.uniform(0, 360)
                
        aabb = aabb.moved(0.0, 0.0, allowed_dz)
        self.position.z += allowed_dz
        
        # Apply friction when on ground and idle
        if self.on_ground and self.is_idle:
            self.velocity.x *= 0.8
            self.velocity.z *= 0.8
    
    def _sweep_axis(self, aabb: AABB, delta: float, axis: str) -> Tuple[float, bool]:
        """Sweep AABB along axis (same implementation as player)."""
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
    
    @staticmethod
    def _approach(current: float, target: float, delta: float) -> float:
        """Smoothly approach target value."""
        if current < target:
            return min(target, current + delta)
        if current > target:
            return max(target, current - delta)
        return current


class MobSystem:
    """Manages all mobs in the world."""
    
    def __init__(self, render: NodePath, world, drop_system, difficulty: int = 2):
        self.render = render
        self.world = world
        self.drop_system = drop_system
        self.difficulty = difficulty
        self.root = self.render.attachNewNode("mobs-root")
        self.mobs: List[Mob] = []
        
        # Spawning parameters
        self.spawn_timer = 0.0
        self.spawn_interval = 5.0  # Try to spawn mobs every 5 seconds
        self.max_mobs_per_chunk = 3  # Maximum mobs per chunk
        self.spawn_attempts_per_cycle = 5  # Try 5 spawn attempts per cycle
        
        # Adjust max mobs based on difficulty
        if self.difficulty == settings.DIFFICULTY_PEACEFUL:
            self.max_mobs_per_chunk = 2 # Animals only
        elif self.difficulty == settings.DIFFICULTY_EASY:
            self.max_mobs_per_chunk = 3
        elif self.difficulty == settings.DIFFICULTY_NORMAL:
            self.max_mobs_per_chunk = 5
        elif self.difficulty == settings.DIFFICULTY_HARD:
            self.max_mobs_per_chunk = 8
    
    def spawn_mob(self, mob_type: int, position: Vec3) -> Optional[Mob]:
        """Spawn a mob at the specified position."""
        mob = Mob(mob_type, position, self.world)
        self.mobs.append(mob)
        
        # Create visual representation
        self._create_mob_mesh(mob)
        
        return mob
    
    def _create_mob_mesh(self, mob: Mob) -> None:
        """Create a simple box mesh for the mob."""
        from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexWriter
        from panda3d.core import Geom, GeomTriangles, GeomNode
        
        # Create vertex data
        vformat = GeomVertexFormat.getV3c4()
        vdata = GeomVertexData("mob", vformat, Geom.UHStatic)
        
        vertex = GeomVertexWriter(vdata, "vertex")
        color = GeomVertexWriter(vdata, "color")
        
        # Create a box using mob size
        w = mob.size.x * 0.5
        h = mob.size.y
        d = mob.size.z * 0.5
        
        # Define box vertices (centered at origin, extends upward)
        vertices = [
            (-w, -d, 0), (w, -d, 0), (w, d, 0), (-w, d, 0),  # Bottom
            (-w, -d, h), (w, -d, h), (w, d, h), (-w, d, h),  # Top
        ]
        
        # Define box faces
        faces = [
            # Bottom
            0, 2, 1, 0, 3, 2,
            # Top
            4, 5, 6, 4, 6, 7,
            # Front
            0, 1, 5, 0, 5, 4,
            # Back
            2, 3, 7, 2, 7, 6,
            # Left
            3, 0, 4, 3, 4, 7,
            # Right
            1, 2, 6, 1, 6, 5,
        ]
        
        # Add vertices with color
        for face_idx in faces:
            v = vertices[face_idx]
            vertex.addData3(v[0], v[1], v[2])
            color.addData4f(*mob.color)
        
        # Create triangles
        tris = GeomTriangles(Geom.UHStatic)
        for i in range(0, len(faces), 3):
            tris.addVertices(i, i + 1, i + 2)
        tris.closePrimitive()
        
        # Create geom and node
        geom = Geom(vdata)
        geom.addPrimitive(tris)
        
        node = GeomNode("mob_node")
        node.addGeom(geom)
        
        # Attach to scene
        mob.node_path = self.root.attachNewNode(node)
        mob.node_path.setPos(mob.position.x, mob.position.z, mob.position.y)
    
    def update(self, dt: float, player, time_of_day: float = 0.2) -> None:
        """Update all mobs and handle spawning/despawning."""
        # Update spawn timer
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0.0
            self._try_spawn_mobs(player.position, time_of_day)
        
        # Determine if it's day (for despawning hostiles)
        # Night is 0.5 to 0.9. Day is < 0.4 or > 0.9? 
        # User said: "spawn at night and attack... in creative they will spawn at night but they won't go towards the player... once in daytime they will despawn"
        is_night = 0.5 <= time_of_day < 0.9
        
        # Update existing mobs
        mobs_to_remove = []
        
        for mob in self.mobs:
            # Check if mob is outside render distance
            if self._is_outside_render_distance(mob, player.position):
                mobs_to_remove.append(mob)
                continue
            
            # Despawn hostiles during day
            if mob.is_hostile and not is_night:
                # Despawn effect? For now just remove
                mobs_to_remove.append(mob)
                continue
            
            # Check for Peaceful mode (despawn hostiles immediately)
            if mob.is_hostile and self.difficulty == settings.DIFFICULTY_PEACEFUL:
                mobs_to_remove.append(mob)
                continue
            
            # Update mob
            # Pass player position, game mode, and difficulty
            mob.update(dt, player.position, player.game_mode, self.difficulty)
            
            # Handle attack damage application
            if mob.is_hostile and not mob.is_dead and player.game_mode == "Survival":
                 # Check if mob wants to attack (cooldown handled in mob.update)
                 # But we didn't implement a way for mob to signal attack yet in update().
                 # Let's check distance here for actual damage application
                 dist_sq = (mob.position.x - player.position.x)**2 + (mob.position.z - player.position.z)**2
                 if dist_sq <= mob.attack_range**2:
                     # Check cooldown here? Or rely on mob state?
                     # Mob state has cooldown. We should probably access it or let mob handle it.
                     # Let's use the mob.attack_cooldown which we update in mob.update
                     # But mob.update decrement it. 
                     # If we attack, we set it.
                     if mob.attack_cooldown <= 0.0:
                         # Attack!
                         player.take_damage(mob.attack_damage)
                         mob.attack_cooldown = 1.5 # Reset cooldown
                         # Knockback?
                         dx = player.position.x - mob.position.x
                         dz = player.position.z - mob.position.z
                         length = sqrt(dx*dx + dz*dz)
                         if length > 0:
                             knockback = 8.0
                             player.velocity.x += (dx/length) * knockback
                             player.velocity.z += (dz/length) * knockback
                             player.velocity.y += 4.0 # slight lift
            
            # Handle death
            if mob.is_dead and mob.death_timer > 0.1:  # Short delay before dropping items
                # Spawn drops
                drops = mob.get_drops()
                for item_type in drops:
                    self.drop_system.spawn_drop(item_type, mob.position)
                
                mobs_to_remove.append(mob)
                continue
            
            # Update visual position
            if mob.node_path:
                mob.node_path.setPos(mob.position.x, mob.position.z, mob.position.y)
                # Face velocity?
                if abs(mob.velocity.x) > 0.1 or abs(mob.velocity.z) > 0.1:
                    import math
                    angle = math.degrees(math.atan2(mob.velocity.x, mob.velocity.z))
                    # Panda3D H is rotation around Z (Up). But our mob Z is Y.
                    # Mob node is placed at (x, z, y).
                    # Z is up. X, Y are horizontal.
                    # atan2(x, y) -> angle from Y axis?
                    mob.node_path.setH(angle)
        
        # Remove dead/despawned mobs
        for mob in mobs_to_remove:
            if mob in self.mobs:
                self.mobs.remove(mob)
            if mob.node_path:
                mob.node_path.removeNode()
    
    def _is_outside_render_distance(self, mob: Mob, player_position: Vec3) -> bool:
        """Check if mob is outside render distance from player."""
        # Calculate chunk distance
        player_cx = floor(player_position.x / settings.CHUNK_SIZE_X)
        player_cz = floor(player_position.z / settings.CHUNK_SIZE_Z)
        
        mob_cx = floor(mob.position.x / settings.CHUNK_SIZE_X)
        mob_cz = floor(mob.position.z / settings.CHUNK_SIZE_Z)
        
        chunk_dist = max(abs(mob_cx - player_cx), abs(mob_cz - player_cz))
        
        return chunk_dist > settings.RENDER_DISTANCE
    
    def _try_spawn_mobs(self, player_position: Vec3, time_of_day: float) -> None:
        """Try to spawn mobs around the player within render distance."""
        player_cx = floor(player_position.x / settings.CHUNK_SIZE_X)
        player_cz = floor(player_position.z / settings.CHUNK_SIZE_Z)
        
        is_night = 0.5 <= time_of_day < 0.9
        
        # Try several spawn attempts
        for _ in range(self.spawn_attempts_per_cycle):
            # Pick a random chunk within render distance
            offset_x = random.randint(-settings.RENDER_DISTANCE, settings.RENDER_DISTANCE)
            offset_z = random.randint(-settings.RENDER_DISTANCE, settings.RENDER_DISTANCE)
            
            spawn_cx = player_cx + offset_x
            spawn_cz = player_cz + offset_z
            
            # Check if this chunk already has too many mobs
            mobs_in_chunk = sum(1 for mob in self.mobs
                               if floor(mob.position.x / settings.CHUNK_SIZE_X) == spawn_cx
                               and floor(mob.position.z / settings.CHUNK_SIZE_Z) == spawn_cz)
            
            if mobs_in_chunk >= self.max_mobs_per_chunk:
                continue
            
            # Pick random position within chunk
            wx = spawn_cx * settings.CHUNK_SIZE_X + random.uniform(1, settings.CHUNK_SIZE_X - 1)
            wz = spawn_cz * settings.CHUNK_SIZE_Z + random.uniform(1, settings.CHUNK_SIZE_Z - 1)
            
            # Get terrain height
            wy = float(terrain_height(int(wx), int(wz))) + 1.0
            
            # Check if spawn position is valid (not in water, not underground)
            if wy < 5 or wy > 50:  # Reasonable height range
                continue
            
            # Check if position is clear (no blocks above)
            if self.world.solid_at(int(wx), int(wy), int(wz)):
                continue
            if self.world.solid_at(int(wx), int(wy + 1), int(wz)):
                continue
            
            # Decide mob type based on time and difficulty
            possible_mobs = []
            
            # Passive mobs (always spawn during day, maybe night too?)
            # Usually passive spawn in light. Night = Dark.
            # But for simplicity, let's say passives spawn in Day, Hostiles in Night.
            
            if is_night:
                # Night: Hostiles (if not Peaceful)
                if self.difficulty != settings.DIFFICULTY_PEACEFUL:
                    possible_mobs = [MOB_CREEPER, MOB_ZOMBIE, MOB_SKELETON]
                    # Maybe rare spider/etc?
                else:
                     # Peaceful night: maybe nothing? Or animals?
                     # User said: "in peaceful mode these mobs will not spawn"
                     continue
            else:
                # Day: Animals
                possible_mobs = [MOB_SHEEP, MOB_COW, MOB_CHICKEN, MOB_PIG]
            
            if not possible_mobs:
                continue
                
            # Pick random mob type
            mob_type = random.choice(possible_mobs)
            
            # Spawn the mob
            spawn_pos = Vec3(wx, wy, wz)
            self.spawn_mob(mob_type, spawn_pos)
            
            # Only spawn one mob per cycle
            break
    
    def get_mob_at_position(self, position: Vec3, max_distance: float = 5.0) -> Optional[Mob]:
        """Get the closest mob to a position within max_distance."""
        closest_mob = None
        closest_dist_sq = max_distance * max_distance
        
        for mob in self.mobs:
            if mob.is_dead:
                continue
            
            dx = mob.position.x - position.x
            dy = mob.position.y - position.y
            dz = mob.position.z - position.z
            
            dist_sq = dx * dx + dy * dy + dz * dz
            
            if dist_sq < closest_dist_sq:
                closest_dist_sq = dist_sq
                closest_mob = mob
        
        return closest_mob
    
    def raycast_mob(self, ray_origin: Vec3, ray_direction: Vec3, max_distance: float = 5.0) -> Optional[Mob]:
        """Cast a ray and return the first mob hit."""
        closest_mob = None
        closest_t = max_distance
        
        for mob in self.mobs:
            if mob.is_dead:
                continue
            
            # Simple ray-AABB intersection
            mob_aabb = mob.get_aabb()
            t = self._ray_aabb_intersection(ray_origin, ray_direction, mob_aabb)
            
            if t is not None and t < closest_t:
                closest_t = t
                closest_mob = mob
        
        return closest_mob
    
    def _ray_aabb_intersection(self, origin: Vec3, direction: Vec3, aabb: AABB) -> Optional[float]:
        """Test ray-AABB intersection, returns t value or None."""
        # Avoid division by zero
        eps = 1e-8
        
        # Calculate intersection with each axis slab
        t_min = float('-inf')
        t_max = float('inf')
        
        # X axis
        if abs(direction.x) > eps:
            tx1 = (aabb.min_x - origin.x) / direction.x
            tx2 = (aabb.max_x - origin.x) / direction.x
            t_min = max(t_min, min(tx1, tx2))
            t_max = min(t_max, max(tx1, tx2))
        elif origin.x < aabb.min_x or origin.x > aabb.max_x:
            return None
        
        # Y axis
        if abs(direction.y) > eps:
            ty1 = (aabb.min_y - origin.y) / direction.y
            ty2 = (aabb.max_y - origin.y) / direction.y
            t_min = max(t_min, min(ty1, ty2))
            t_max = min(t_max, max(ty1, ty2))
        elif origin.y < aabb.min_y or origin.y > aabb.max_y:
            return None
        
        # Z axis
        if abs(direction.z) > eps:
            tz1 = (aabb.min_z - origin.z) / direction.z
            tz2 = (aabb.max_z - origin.z) / direction.z
            t_min = max(t_min, min(tz1, tz2))
            t_max = min(t_max, max(tz1, tz2))
        elif origin.z < aabb.min_z or origin.z > aabb.max_z:
            return None
        
        # Check if intersection exists
        if t_max >= t_min and t_max >= 0:
            return t_min if t_min >= 0 else t_max
        
        return None
    
    def cleanup(self) -> None:
        """Clean up all mobs."""
        for mob in self.mobs:
            if mob.node_path:
                mob.node_path.removeNode()
        
        self.mobs.clear()
        
        if self.root and not self.root.isEmpty():
            self.root.removeNode()
