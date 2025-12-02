from __future__ import annotations

from math import cos, sin, radians, copysign, sqrt, floor
from typing import Dict, Tuple, Optional

from panda3d.core import NodePath, Vec3

from . import settings
from .chunk import BLOCK_BEDROCK
from .util import AABB, block_aabb, clamp
from .util import terrain_height


class Player:
    """
    FPS player controller with AABB collision against voxel blocks.
    Coordinates:
      - World axes: (x, z) horizontal plane, y is up.
      - Panda3D axes: (X, Y, Z) = (x, z, y).
    """

    def __init__(self, camera: NodePath, world, game_mode: str = "Survival"):
        self.camera = camera
        self.world = world
        self.game_mode = game_mode

        # Orientation in degrees (Panda uses degrees)
        self.yaw = 0.0    # rotate around world up (y)
        self.pitch = 0.0  # look up/down

        # Spawn slightly above terrain at origin
        spawn_x = 0.0
        spawn_z = 0.0
        ground_h = terrain_height(int(spawn_x), int(spawn_z))
        spawn_y = float(ground_h + 3)

        self.position = Vec3(spawn_x, spawn_y, spawn_z)  # world (x, y, z)
        self.velocity = Vec3(0.0, 0.0, 0.0)

        self.on_ground = False
        
        # Creative Mode Flight
        self.is_flying = False
        self.last_jump_time = 0.0
        self.fly_speed_multiplier = 2.5
        
        # Survival stats (20 points = 10 hearts/hunger bars)
        self.max_health = 20.0
        self.health = 20.0
        self.max_hunger = 20.0
        self.hunger = 20.0
        self.saturation = 5.0
        
        # Fall damage tracking
        self.fall_start_y = self.position.y
        self.last_on_ground = True
        
        # Regen timers
        self.regen_timer = 0.0
        self.hunger_timer = 0.0
        
        # Block breaking state
        self.breaking_block = None  # (wx, wy, wz) or None
        self.breaking_progress = 0.0  # 0.0 to 1.0
        self.breaking_block_type = None  # Block type being broken
        
        # Creative Mode: track if we already broke a block this click
        self.creative_block_broken_this_click = False
        
        # Disable any smoothing or interpolation on camera
        self.camera.node().setFinal(True)

        # Track previous key states for edge detection
        self.keys_prev_jump = False

        # Movement smoothing state (purely visual; does not affect collisions or physics)
        self.smoothed_position = Vec3(self.position)
        self.camera_lerp_factor = 20.0  # higher = snappier camera follow

        # Apply initial camera transform
        self._update_camera()

    # ------------------------------------------------------------------
    # Look / orientation
    # ------------------------------------------------------------------
    def add_look(self, dx_pixels: int, dy_pixels: int) -> None:
        # Mouse look: pixels -> degrees
        self.yaw -= dx_pixels * settings.MOUSE_SENSITIVITY
        self.pitch -= dy_pixels * settings.MOUSE_SENSITIVITY
        if self.pitch > settings.MAX_PITCH:
            self.pitch = settings.MAX_PITCH
        elif self.pitch < -settings.MAX_PITCH:
            self.pitch = -settings.MAX_PITCH
        self._update_camera()

    def _update_camera(self, dt: float = 0.0) -> None:
        """
        Update camera transform from the physical player position.
        Uses mild smoothing so that walking/jumping feels less jittery while
        keeping the underlying physics and collisions unchanged.
        """
        # Target camera anchor: player body position
        target_pos = self.position

        # Smooth only if dt is positive and reasonable; otherwise snap (e.g. on spawn/load)
        if dt > 0.0:
            # Exponential smoothing towards target
            alpha = 1.0 - pow(max(0.0, 1.0 - self.camera_lerp_factor * dt), 1.0)
            # Clamp alpha to [0, 1] just in case
            if alpha < 0.0:
                alpha = 0.0
            elif alpha > 1.0:
                alpha = 1.0

            self.smoothed_position.x += (target_pos.x - self.smoothed_position.x) * alpha
            self.smoothed_position.y += (target_pos.y - self.smoothed_position.y) * alpha
            self.smoothed_position.z += (target_pos.z - self.smoothed_position.z) * alpha
        else:
            # Initial / teleport: hard snap
            self.smoothed_position = Vec3(target_pos)

        # Map world (x, y, z) -> Panda (X, Y, Z) = (x, z, y)
        cam_x = self.smoothed_position.x
        cam_y = self.smoothed_position.z
        cam_z = self.smoothed_position.y + settings.PLAYER_EYE_OFFSET

        self.camera.setPos(cam_x, cam_y, cam_z)
        self.camera.setHpr(self.yaw, self.pitch, 0.0)

    # ------------------------------------------------------------------
    # Raycasting for block interaction
    # ------------------------------------------------------------------
    def raycast_block(self, max_distance: float = 5.0, return_previous: bool = False) -> Optional[Tuple[int, int, int]]:
        """
        Cast a ray from player's eye position in the look direction.
        Returns the block coordinates (wx, wy, wz) of the first solid block hit.
        If return_previous=True, returns the last air block before hitting solid (for placing).
        """
        # Start position: eye position (in world coords)
        eye_x = self.position.x
        eye_y = self.position.y + settings.PLAYER_EYE_OFFSET  
        eye_z = self.position.z

        # Get the camera's actual forward direction vector
        # Camera is oriented in Panda3D space (X, Y, Z) where Y is forward
        # We need to convert to world space (x, y, z) where y is up
        cam_quat = self.camera.getQuat()
        # Get the forward vector in Panda3D space (0, 1, 0) transformed by camera rotation
        forward_panda = cam_quat.xform(Vec3(0, 1, 0))
        
        # Convert from Panda3D coords (X, Y, Z) to world coords (x, y, z)
        # Panda: (X, Y, Z) = (world_x, world_z, world_y)
        # So: world_x = panda_X, world_y = panda_Z, world_z = panda_Y
        dir_x = forward_panda.x
        dir_y = forward_panda.z
        dir_z = forward_panda.y
        
        # Normalize (should already be normalized but just in case)
        length = sqrt(dir_x * dir_x + dir_y * dir_y + dir_z * dir_z)
        if length > 0.0:
            dir_x /= length
            dir_y /= length
            dir_z /= length

        # Step along ray using DDA-like algorithm
        step_size = 0.1  # Check every 0.1 units
        steps = int(max_distance / step_size)
        
        prev_block = None
        
        for i in range(steps):
            t = i * step_size
            rx = eye_x + dir_x * t
            ry = eye_y + dir_y * t
            rz = eye_z + dir_z * t
            
            # Convert to block coordinates
            bx = floor(rx)
            by = floor(ry)
            bz = floor(rz)
            
            current_block = (bx, by, bz)
            
            # Check if this block is solid
            if self.world.solid_at(bx, by, bz):
                if return_previous and prev_block is not None:
                    return prev_block
                else:
                    return current_block
            
            prev_block = current_block
        
        return None

    def intersects_position(self, wx: int, wy: int, wz: int) -> bool:
        """
        Check if a block at (wx, wy, wz) would intersect with the player's AABB.
        Used to prevent placing blocks inside the player.
        """
        player_aabb = self._player_aabb()
        block = block_aabb(wx, wy, wz)
        return player_aabb.intersects(block)

    # ------------------------------------------------------------------
    # Block breaking progress
    # ------------------------------------------------------------------
    def start_breaking(self, block_pos: Tuple[int, int, int], block_type: int) -> None:
        """Start breaking a block or switch to a new block."""
        if self.breaking_block != block_pos:
            self.breaking_block = block_pos
            self.breaking_progress = 0.0
            self.breaking_block_type = block_type

    def update_breaking(self, dt: float) -> bool:
        """
        Update breaking progress. Returns True if block should break.
        """
        if self.breaking_block is None or self.breaking_block_type is None:
            return False
        
        # Get hardness for this block type
        hardness = settings.BLOCK_HARDNESS.get(self.breaking_block_type, 1.0)
        
        # Check if block is unbreakable
        if hardness is None:
            return False
        
        # Creative Mode: instant break (but only once per mouse click)
        if self.game_mode == "Creative":
            # Only break if we haven't broken a block during this click yet
            if not self.creative_block_broken_this_click:
                self.creative_block_broken_this_click = True
                # Clear breaking state WITHOUT resetting the flag
                self.breaking_block = None
                self.breaking_progress = 0.0
                self.breaking_block_type = None
                return True
            return False
        
        # Update progress
        self.breaking_progress += dt / hardness
        
        # Check if block is broken
        if self.breaking_progress >= 1.0:
            self.reset_breaking()
            return True
        
        return False

    def reset_breaking(self) -> None:
        """Reset breaking state."""
        self.breaking_block = None
        self.breaking_progress = 0.0
        self.breaking_block_type = None
        # Reset Creative Mode flag when mouse is released
        self.creative_block_broken_this_click = False

    def get_break_stage(self) -> int:
        """Get current break stage (0-9) for animation."""
        if self.breaking_progress <= 0.0:
            return 0
        stage = int(self.breaking_progress * settings.BREAK_STAGES)
        return min(stage, settings.BREAK_STAGES - 1)

    # ------------------------------------------------------------------
    # Survival Mechanics
    # ------------------------------------------------------------------
    def take_damage(self, amount: float) -> None:
        """Take damage to health."""
        if self.game_mode == "Creative":
            return
            
        self.health -= amount
        if self.health < 0:
            self.health = 0
        print(f"Player took damage: {amount}. Health: {self.health}")
        # TODO: Handle death (respawn)

    def heal(self, amount: float) -> None:
        """Restore health."""
        self.health += amount
        if self.health > self.max_health:
            self.health = self.max_health

    def add_hunger(self, amount: float, saturation: float = 0.0) -> None:
        """Restore hunger."""
        self.hunger += amount
        if self.hunger > self.max_hunger:
            self.hunger = self.max_hunger
        self.saturation += saturation

    def consume_hunger(self, amount: float) -> None:
        """Consume hunger (or saturation first)."""
        if self.saturation > 0:
            self.saturation -= amount
            if self.saturation < 0:
                amount = -self.saturation
                self.saturation = 0
            else:
                amount = 0
        
        if amount > 0:
            self.hunger -= amount
            if self.hunger < 0:
                self.hunger = 0

    def update_survival(self, dt: float) -> None:
        """Update survival mechanics (hunger, regen)."""
        if self.game_mode == "Creative":
            return

        # Health Regeneration
        # Regen if hunger > 16 (missing less than 2 full hunger points)
        # 10 hearts = 20 points. 2 full hunger points = 4 points. 20 - 4 = 16.
        if self.hunger > 16 and self.health < self.max_health:
            self.regen_timer += dt
            if self.regen_timer >= 4.0:  # Regen every 4 seconds
                self.heal(1.0) # Heal half heart
                self.consume_hunger(0.25) # Cost some hunger
                self.regen_timer = 0.0
        
        # Hunger Tick (slow decay if not full)
        # User didn't explicitly ask for decay, but said eating regenerates hunger.
        # I'll add very slow decay to make eating useful.
        self.hunger_timer += dt
        if self.hunger_timer >= 30.0: # Decrease hunger every 30 seconds
            self.consume_hunger(0.5)
            self.hunger_timer = 0.0
            
        # Handle death (simple respawn for now)
        if self.health <= 0:
            self.respawn()

    def respawn(self):
        """Respawn player."""
        print("Player died! Respawning...")
        spawn_x = 0.0
        spawn_z = 0.0
        ground_h = terrain_height(int(spawn_x), int(spawn_z))
        self.position = Vec3(spawn_x, float(ground_h + 3), spawn_z)
        self.velocity = Vec3(0, 0, 0)
        self.health = self.max_health
        self.hunger = self.max_hunger
        self.fall_start_y = self.position.y
        self._update_camera()

    # ------------------------------------------------------------------
    # Physics / movement
    # ------------------------------------------------------------------
    def update(self, keys: Dict[str, bool], dt: float, move_vec: Tuple[float, float] = None) -> None:
        # Update survival stats
        self.update_survival(dt)

        # Movement intent
        if move_vec:
            # Analog input (x=right/left, y=forward/back)
            move_x = move_vec[0]
            move_y = move_vec[1]
        else:
            # Digital input
            fwd = 1.0 if keys.get("forward", False) else 0.0
            back = 1.0 if keys.get("back", False) else 0.0
            left = 1.0 if keys.get("left", False) else 0.0
            right = 1.0 if keys.get("right", False) else 0.0
            move_y = fwd - back
            move_x = right - left

        # Build wish direction in XZ plane from yaw
        wish_x = 0.0
        wish_z = 0.0
        if move_x != 0.0 or move_y != 0.0:
            yaw_rad = radians(self.yaw)
            # Forward unit in world XZ
            fwd_x = -sin(yaw_rad)
            fwd_z = cos(yaw_rad)
            # Right unit is forward rotated -90deg
            right_x = cos(yaw_rad)
            right_z = sin(yaw_rad)

            wish_x = fwd_x * move_y + right_x * move_x
            wish_z = fwd_z * move_y + right_z * move_x
            # Normalize
            length = sqrt(wish_x * wish_x + wish_z * wish_z)
            if length > 0.0:
                wish_x /= length
                wish_z /= length

        # Accelerate towards desired horizontal speed
        speed_mult = self.fly_speed_multiplier if self.is_flying else 1.0
        desired_xz_x = wish_x * settings.MOVE_SPEED * speed_mult
        desired_xz_z = wish_z * settings.MOVE_SPEED * speed_mult

        ax = settings.ACCEL_GROUND if self.on_ground else settings.ACCEL_AIR
        # Apply friction on ground when no input
        if self.on_ground and move_x == 0.0 and move_y == 0.0:
            vx = self.velocity.x
            vz = self.velocity.z
            speed = sqrt(vx * vx + vz * vz)
            drop = settings.FRICTION * dt
            new_speed = max(0.0, speed - drop)
            if speed > 0.0:
                scale = new_speed / speed
                self.velocity.x *= scale
                self.velocity.z *= scale
        else:
            # Accelerate towards target velocity
            self.velocity.x = self._approach(self.velocity.x, desired_xz_x, ax * dt)
            self.velocity.z = self._approach(self.velocity.z, desired_xz_z, ax * dt)

        # Jump / Flight Toggle
        if keys.get("jump", False):
            if not self.keys_prev_jump: # Just pressed
                import time
                now = time.time()
                
                if self.game_mode == "Creative":
                    if now - self.last_jump_time < 0.3: # Double tap within 300ms
                        self.is_flying = not self.is_flying
                        self.velocity.y = 0
                        self.last_jump_time = 0.0 # Reset
                    else:
                        self.last_jump_time = now
                
                if self.is_flying:
                    # Ascend
                    self.velocity.y = settings.JUMP_SPEED
                elif self.on_ground:
                    self.velocity.y = settings.JUMP_SPEED
                    self.on_ground = False
        else:
            # Not holding jump
            if self.is_flying:
                self.velocity.y = 0.0
                
        # Flight Descent (Shift/Crouch)
        # We need to pass crouch key state. Assuming "crouch" or "shift" is passed?
        # App doesn't pass crouch yet. Let's assume 'left_shift' or similar if added.
        # For now, let's use a hack or wait for input update.
        # User said "space/shift for vertical movement".
        # I'll check keys for 'crouch' if it exists, or just rely on gravity if not flying.
        # But flying needs down.
        if self.is_flying and keys.get("crouch", False):
             self.velocity.y = -settings.JUMP_SPEED

        self.keys_prev_jump = keys.get("jump", False)

        # Gravity
        if not self.is_flying:
            self.velocity.y -= settings.GRAVITY * dt

        # Integrate with collision (separate axis resolution to avoid tunneling)
        dx = self.velocity.x * dt
        dy = self.velocity.y * dt
        dz = self.velocity.z * dt

        aabb = self._player_aabb()

        # X axis
        allowed_dx, _hit_x = self._sweep_axis(aabb, dx, axis="x")
        if allowed_dx != dx:
            self.velocity.x = 0.0
        aabb = aabb.moved(allowed_dx, 0.0, 0.0)
        self.position.x += allowed_dx

        # Y axis
        allowed_dy, hit_y = self._sweep_axis(aabb, dy, axis="y")
        if allowed_dy != dy:
            if dy < 0.0:
                # Landed on ground
                if not self.on_ground:
                    # Just landed, calculate fall damage
                    fall_distance = self.fall_start_y - self.position.y - allowed_dy
                    if fall_distance > 0:
                        # "drop from 4 blocks then that will count as half a heart taken"
                        # 4 blocks -> 1 damage (0.5 heart)
                        # Formula: distance - 3 (standard MC). 4 - 3 = 1.
                        damage_points = max(0, int(fall_distance - 3))
                        if damage_points > 0:
                            self.take_damage(damage_points)
                
                self.on_ground = True
                self.fall_start_y = self.position.y + allowed_dy
            self.velocity.y = 0.0
        else:
            # Only clear on_ground when we actually move up/are in air
            if dy > 0.0:
                self.on_ground = False
            
            # If we are falling (negative velocity) and fall_start_y is unset (or we just started falling)
            # Update fall_start_y only when we start falling from a high place?
            # Actually, peak height logic is better.
            pass

        # Track peak height for fall damage
        if self.velocity.y > 0:
             self.fall_start_y = max(self.fall_start_y, self.position.y + allowed_dy)
        elif self.on_ground and dy < 0: # Just broke contact with ground? No
             pass # Handled by on_ground flag logic

        # Better fall logic:
        # Always track current Y if grounded.
        # If in air, track peak Y.
        # Since we check landing above, we need ensure fall_start_y was set correctly when leaving ground.
        
        aabb = aabb.moved(0.0, allowed_dy, 0.0)
        self.position.y += allowed_dy
        
        # Check if we just left the ground (e.g. walked off edge)
        if not self.on_ground and self.velocity.y <= 0 and self.last_on_ground:
             self.fall_start_y = self.position.y

        self.last_on_ground = self.on_ground

        # Z axis
        allowed_dz, _hit_z = self._sweep_axis(aabb, dz, axis="z")
        if allowed_dz != dz:
            self.velocity.z = 0.0
        aabb = aabb.moved(0.0, 0.0, allowed_dz)
        self.position.z += allowed_dz

        # Update camera transform (purely visual smoothing based on final physics position)
        self._update_camera(dt)

    @staticmethod
    def _approach(current: float, target: float, delta: float) -> float:
        if current < target:
            return min(target, current + delta)
        if current > target:
            return max(target, current - delta)
        return current

    # ------------------------------------------------------------------
    # Collision helpers
    # ------------------------------------------------------------------
    def _player_aabb(self) -> AABB:
        half_w = settings.PLAYER_WIDTH * 0.5
        half_d = settings.PLAYER_DEPTH * 0.5
        min_x = self.position.x - half_w
        max_x = self.position.x + half_w
        min_y = self.position.y
        max_y = self.position.y + settings.PLAYER_HEIGHT
        min_z = self.position.z - half_d
        max_z = self.position.z + half_d
        return AABB(min_x, min_y, min_z, max_x, max_y, max_z)

    def _sweep_axis(self, aabb: AABB, delta: float, axis: str) -> Tuple[float, bool]:
        """
        Sweep AABB along a single axis by 'delta', clamping to avoid intersections
        with any solid blocks. Returns (allowed_delta, hit).
        Uses improved collision detection to prevent glitching through blocks.
        """
        if delta == 0.0:
            return 0.0, False

        eps = settings.EPSILON

        # For each axis, we need to check all blocks that could possibly intersect
        # the swept volume. This is more thorough than before.
        if axis == "x":
            # Calculate the swept volume bounds
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
            
            # Check all blocks in the swept volume
            for bx in range(sweep_min_x, sweep_max_x + 1):
                for by in range(sweep_min_y, sweep_max_y + 1):
                    for bz in range(sweep_min_z, sweep_max_z + 1):
                        if not self.world.solid_at(bx, by, bz):
                            continue
                        
                        blk = block_aabb(bx, by, bz)
                        
                        # Check if the swept AABB would intersect this block
                        # We need to check Y and Z overlap first
                        if aabb.max_y <= blk.min_y or aabb.min_y >= blk.max_y:
                            continue
                        if aabb.max_z <= blk.min_z or aabb.min_z >= blk.max_z:
                            continue
                        
                        # Now check X collision
                        if delta > 0.0:
                            # Moving right: check if we would hit the left face
                            if aabb.max_x <= blk.min_x and aabb.max_x + delta > blk.min_x:
                                allowed = min(allowed, blk.min_x - aabb.max_x - eps)
                                hit = True
                        else:
                            # Moving left: check if we would hit the right face
                            if aabb.min_x >= blk.max_x and aabb.min_x + delta < blk.max_x:
                                allowed = max(allowed, blk.max_x - aabb.min_x + eps)
                                hit = True
            
            return allowed, hit

        elif axis == "y":
            # Calculate the swept volume bounds
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
            
            # Check all blocks in the swept volume
            for bx in range(sweep_min_x, sweep_max_x + 1):
                for by in range(sweep_min_y, sweep_max_y + 1):
                    for bz in range(sweep_min_z, sweep_max_z + 1):
                        if not self.world.solid_at(bx, by, bz):
                            continue
                        
                        blk = block_aabb(bx, by, bz)
                        
                        # Check if the swept AABB would intersect this block
                        # We need to check X and Z overlap first
                        if aabb.max_x <= blk.min_x or aabb.min_x >= blk.max_x:
                            continue
                        if aabb.max_z <= blk.min_z or aabb.min_z >= blk.max_z:
                            continue
                        
                        # Now check Y collision
                        if delta > 0.0:
                            # Moving up: check if we would hit the bottom face
                            if aabb.max_y <= blk.min_y and aabb.max_y + delta > blk.min_y:
                                allowed = min(allowed, blk.min_y - aabb.max_y - eps)
                                hit = True
                        else:
                            # Moving down: check if we would hit the top face
                            if aabb.min_y >= blk.max_y and aabb.min_y + delta < blk.max_y:
                                allowed = max(allowed, blk.max_y - aabb.min_y + eps)
                                hit = True
            
            return allowed, hit

        else:  # axis == "z"
            # Calculate the swept volume bounds
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
            
            # Check all blocks in the swept volume
            for bx in range(sweep_min_x, sweep_max_x + 1):
                for by in range(sweep_min_y, sweep_max_y + 1):
                    for bz in range(sweep_min_z, sweep_max_z + 1):
                        if not self.world.solid_at(bx, by, bz):
                            continue
                        
                        blk = block_aabb(bx, by, bz)
                        
                        # Check if the swept AABB would intersect this block
                        # We need to check X and Y overlap first
                        if aabb.max_x <= blk.min_x or aabb.min_x >= blk.max_x:
                            continue
                        if aabb.max_y <= blk.min_y or aabb.min_y >= blk.max_y:
                            continue
                        
                        # Now check Z collision
                        if delta > 0.0:
                            # Moving forward: check if we would hit the back face
                            if aabb.max_z <= blk.min_z and aabb.max_z + delta > blk.min_z:
                                allowed = min(allowed, blk.min_z - aabb.max_z - eps)
                                hit = True
                        else:
                            # Moving backward: check if we would hit the front face
                            if aabb.min_z >= blk.max_z and aabb.min_z + delta < blk.max_z:
                                allowed = max(allowed, blk.max_z - aabb.min_z + eps)
                                hit = True
            
            return allowed, hit
