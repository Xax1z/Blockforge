from __future__ import annotations

from math import floor
from typing import Dict, Iterable, List, Optional, Tuple

from panda3d.core import NodePath

from . import settings
from .chunk import (
    Chunk,
    BLOCK_AIR,
    BLOCK_BEDROCK,
    BLOCK_DIRT,
    BLOCK_GRASS,
    BLOCK_SAND,
    BLOCK_SANDSTONE,
    BLOCK_STONE,
    BLOCK_COAL_ORE,
    BLOCK_IRON_ORE,
    BLOCK_DIAMOND_ORE,
    BLOCK_GOLD_ORE,
    is_block_solid,
    init_texture_manager,
    get_texture_manager,
)
from .util import terrain_height, should_place_tree, generate_tree, get_biome, should_place_cactus, generate_cactus, generate_jungle_tree, generate_birch_tree, get_tree_type, generate_chunk_caves


class World:
    """
    Manages chunk streaming, meshing, and world/block queries.
    Coordinates:
      - World axes: (x, z) horizontal, y up.
      - Panda3D axes: (X, Y, Z) = (x, z, y). World nodes are positioned using this mapping.
    """

    def __init__(self, render: NodePath, save_system=None):
        self.render = render
        self.root = self.render.attachNewNode("world-root")

        # Loaded chunks and their NodePaths
        self.chunks: Dict[Tuple[int, int], Chunk] = {}
        self.chunk_nodes: Dict[Tuple[int, int], NodePath] = {}
        
        # Preloading state
        self.preload_complete = False
        
        # Save system reference for loading chunk modifications
        self.save_system = save_system
        
        # Initialize texture manager  
        self.texture_manager = init_texture_manager()
        
        # Load main block texture (use stone as default)
        # self.default_texture = self.texture_manager.get_block_texture('stone')

    # ---------------------------------------------------------------------
    # World/block queries (deterministic terrain, independent of chunk data)
    # ---------------------------------------------------------------------
    def block_id_at(self, wx: int, wy: int, wz: int) -> int:
        """Return block id at integer world coords (wx, wy, wz)."""
        if wy < 0:
            return BLOCK_BEDROCK  # solid floor below world
        if wy == 0:
            return BLOCK_BEDROCK
        if wy >= settings.CHUNK_SIZE_Y:
            return BLOCK_AIR

        h = terrain_height(wx, wz)
        if wy > h:
            return BLOCK_AIR
        if wy == h:
            return BLOCK_GRASS
        # top soil thickness
        if wy >= h - 3:
            return BLOCK_DIRT
        return BLOCK_STONE

    def is_solid(self, wx: int, wy: int, wz: int) -> bool:
        """
        Check if a block at world coordinates is solid.
        First checks loaded chunk data, falls back to terrain generation.
        IMPORTANT: For face culling during mesh generation, we need accurate data.
        If a chunk isn't loaded, we return False (air) to prevent incorrectly hiding faces.
        """
        # Check bounds
        if wy < 0:
            return True  # Bedrock below world
        if wy >= settings.CHUNK_SIZE_Y:
            return False  # Air above world
        
        # Determine chunk coordinates (use floor division for consistency)
        cx = floor(wx / settings.CHUNK_SIZE_X)
        cz = floor(wz / settings.CHUNK_SIZE_Z)
        
        # If chunk is loaded, check its actual block data
        chunk = self.chunks.get((cx, cz))
        if chunk is not None:
            lx = wx - cx * settings.CHUNK_SIZE_X
            lz = wz - cz * settings.CHUNK_SIZE_Z
            block_id = chunk.get_block_local(lx, wy, lz)
            return is_block_solid(block_id)
        
        # If chunk is not loaded, assume air (do NOT use terrain generation)
        # This prevents face culling errors when trees/cacti span chunk boundaries
        # The face will be visible until the neighbor chunk loads and gets meshed
        return False

    # ---------------------------------------------------------------------
    # Chunk lifecycle
    # ---------------------------------------------------------------------
    def _populate_chunk_blocks(self, chunk: Chunk, cx: int, cz: int) -> None:
        """Fill chunk.blocks array based on analytic terrain function with biomes."""
        wx0 = cx * settings.CHUNK_SIZE_X
        wz0 = cz * settings.CHUNK_SIZE_Z

        # Pre-calculate all terrain heights and biomes for this chunk (major performance optimization)
        heights = []
        biomes = []
        for lz in range(settings.CHUNK_SIZE_Z):
            height_row = []
            biome_row = []
            for lx in range(settings.CHUNK_SIZE_X):
                wx = wx0 + lx
                wz = wz0 + lz
                biome = get_biome(wx, wz)
                weight = self._get_biome_blend_weight(wx, wz)
                height_row.append(terrain_height(wx, wz, biome, weight))
                biome_row.append(biome)
            heights.append(height_row)
            biomes.append(biome_row)

        # Pre-calculate caves for this chunk using Perlin Worms
        # This returns a set of (lx, y, lz) tuples that should be air
        cave_blocks = generate_chunk_caves(cx, cz)

        # Now fill the chunk using the cached heights and biomes
        # Optimization: Iterate columns and only fill up to terrain height
        # Since chunk.blocks is initialized to BLOCK_AIR, we don't need to set air blocks
        for lz in range(settings.CHUNK_SIZE_Z):
            for lx in range(settings.CHUNK_SIZE_X):
                th = heights[lz][lx]
                biome = biomes[lz][lx]
                
                # Ensure we don't go out of bounds
                max_y = min(th, settings.CHUNK_SIZE_Y - 1)
                
                # Fill from bottom up to terrain height
                for y in range(max_y + 1):
                    bid = BLOCK_STONE # Default
                    
                    if y == 0:
                        bid = BLOCK_BEDROCK
                    elif biome == 'desert':
                        # Desert: sand -> sandstone -> stone
                        if y == th:
                            bid = BLOCK_SAND  # Top layer
                        elif y >= th - 4:
                            bid = BLOCK_SANDSTONE  # Middle layers
                        else:
                            bid = BLOCK_STONE  # Bottom layer
                    else:
                        # Plains: grass -> dirt -> stone
                        if y == th:
                            bid = BLOCK_GRASS  # Top layer
                        elif y >= th - 3:
                            bid = BLOCK_DIRT  # Soil layer
                        else:
                            bid = BLOCK_STONE  # Stone layer
                            
                    # Cave generation (carve out air)
                    # Check if this local coordinate is in our pre-calculated cave set
                    if bid != BLOCK_BEDROCK and bid != BLOCK_AIR:
                         if (lx, y, lz) in cave_blocks:
                             bid = BLOCK_AIR
                        
                    # Ore generation (only replace stone)
                    if bid == BLOCK_STONE:
                        import random
                        # Simple random chance for now (could use noise for veins later)
                        # Use deterministic random based on position
                        # Hash function for pseudo-randomness
                        rand_val = (wx0 + lx) * 374761393 + y * 668265263 + (wz0 + lz) * 3266489917
                        rand_val = rand_val & 0xFFFFFFFF
                        rand_float = rand_val / 4294967295.0
                        
                        if rand_float < 0.001 and y < 16: # Diamond: very rare, deep
                            bid = BLOCK_DIAMOND_ORE
                        elif rand_float < 0.003 and y < 32: # Gold: rare, deep-ish
                            bid = BLOCK_GOLD_ORE
                        elif rand_float < 0.01 and y < 64: # Iron: uncommon, everywhere
                            bid = BLOCK_IRON_ORE
                        elif rand_float < 0.02: # Coal: common, everywhere
                            bid = BLOCK_COAL_ORE

                    chunk.set_block_local(lx, y, lz, bid)

        # Place trees on the surface
        for lz in range(settings.CHUNK_SIZE_Z):
            for lx in range(settings.CHUNK_SIZE_X):
                wx = wx0 + lx
                wz = wz0 + lz
                th = heights[lz][lx]

                # Only place trees on grass blocks (surface level)
                if should_place_tree(wx, wz):
                    # Check if the ground block is actually grass (might have been removed by caves)
                    if chunk.get_block_local(lx, th, lz) != BLOCK_GRASS:
                        continue

                    # Generate tree blocks
                    if get_biome(wx, wz) == 'jungle':
                        tree_blocks = generate_jungle_tree(wx, th + 1, wz)
                    else:
                        # Decide between oak and birch
                        tree_type = get_tree_type(wx, wz)
                        if tree_type == 'birch':
                            tree_blocks = generate_birch_tree(wx, th + 1, wz)
                        else:
                            tree_blocks = generate_tree(wx, th + 1, wz)

                    # Place tree blocks that fall within this chunk
                    for tx, ty, tz, block_id in tree_blocks:
                        # Check if tree block is within this chunk's bounds
                        if (wx0 <= tx < wx0 + settings.CHUNK_SIZE_X and
                            wz0 <= tz < wz0 + settings.CHUNK_SIZE_Z and
                            0 <= ty < settings.CHUNK_SIZE_Y):
                            # Convert to local coordinates
                            local_lx = tx - wx0
                            local_lz = tz - wz0
                            chunk.set_block_local(local_lx, ty, local_lz, block_id)

        # Place cacti in desert areas
        for lz in range(settings.CHUNK_SIZE_Z):
            for lx in range(settings.CHUNK_SIZE_X):
                wx = wx0 + lx
                wz = wz0 + lz
                th = heights[lz][lx]

                # Only place cacti in desert on sand blocks (surface level)
                if should_place_cactus(wx, wz):
                    # Generate cactus blocks
                    cactus_blocks = generate_cactus(wx, th + 1, wz)

                    # Place cactus blocks that fall within this chunk
                    for cx_local, cy, cz_local, block_id in cactus_blocks:
                        # Check if cactus block is within this chunk's bounds
                        if (wx0 <= cx_local < wx0 + settings.CHUNK_SIZE_X and
                            wz0 <= cz_local < wz0 + settings.CHUNK_SIZE_Z and
                            0 <= cy < settings.CHUNK_SIZE_Y):
                            # Convert to local coordinates
                            local_lx = cx_local - wx0
                            local_lz = cz_local - wz0
                            chunk.set_block_local(local_lx, cy, local_lz, block_id)

        # Post-process: remove cacti that are touching each other
        for y in range(settings.CHUNK_SIZE_Y):
            for lz in range(settings.CHUNK_SIZE_Z):
                for lx in range(settings.CHUNK_SIZE_X):
                    block_id = chunk.get_block_local(lx, y, lz)
                    if block_id == 11:  # BLOCK_CACTUS
                        wx = wx0 + lx
                        wz = wz0 + lz
                        # Check if this cactus is touching another cactus
                        if self._cactus_touching_another(chunk, lx, y, lz, wx0, wz0):
                            # Remove this cactus
                            chunk.set_block_local(lx, y, lz, 0)  # BLOCK_AIR
                            # Also remove any cactus blocks above
                            for remove_y in range(y + 1, settings.CHUNK_SIZE_Y):
                                if chunk.get_block_local(lx, remove_y, lz) == 11:
                                    chunk.set_block_local(lx, remove_y, lz, 0)
                                else:
                                    break
                            break  # Move to next position

    def _ensure_chunk(self, cx: int, cz: int) -> Chunk:
        key = (cx, cz)
        ch = self.chunks.get(key)
        if ch is None:
            ch = Chunk(cx, cz)
            self._populate_chunk_blocks(ch, cx, cz)
            # Apply saved modifications if they exist
            self._apply_saved_modifications(ch, cx, cz)
            self.chunks[key] = ch
            if settings.PRINT_CHUNK_EVENTS:
                print(f"[World] Created chunk {key}")
        return ch

    def _build_mesh_for(self, cx: int, cz: int) -> bool:
        """Build mesh for chunk if dirty. Returns True if a mesh was built (budget use)."""
        key = (cx, cz)
        ch = self.chunks.get(key)
        if ch is None:
            return False
        if not ch.dirty and key in self.chunk_nodes:
            return False

        node = ch.build_mesh(self.is_solid)
        # Remove old node if any
        old_np = self.chunk_nodes.get(key)
        if old_np is not None and not old_np.isEmpty():
            old_np.removeNode()
            self.chunk_nodes.pop(key, None)

        if node is None:
            # No faces, keep as empty (rare for terrain)
            return False

        np = self.root.attachNewNode(node)
        # Position NP at chunk world origin (X=wx, Y=wz, Z=0)
        wx0 = cx * settings.CHUNK_SIZE_X
        wz0 = cz * settings.CHUNK_SIZE_Z
        np.setPos(float(wx0), float(wz0), 0.0)
        
        # Apply texture to the chunk
        atlas_texture = self.texture_manager.get_atlas_texture()
        if atlas_texture:
            np.setTexture(atlas_texture)

        self.chunk_nodes[key] = np
        if settings.PRINT_CHUNK_EVENTS:
            print(f"[World] Meshed chunk {key} (tris: {node.getGeom(0).getPrimitive(0).getNumPrimitives()})")
        return True

    def _spiral_coords(self, center: Tuple[int, int], radius: int) -> Iterable[Tuple[int, int]]:
        """Yield (cx, cz) in expanding square (spiral-like) order around center, within radius."""
        ccx, ccz = center
        yield (ccx, ccz)
        for r in range(1, radius + 1):
            # top and bottom rows
            for dx in range(-r, r + 1):
                yield (ccx + dx, ccz - r)
                yield (ccx + dx, ccz + r)
            # left and right columns (excluding corners already yielded)
            for dz in range(-r + 1, r):
                yield (ccx - r, ccz + dz)
                yield (ccx + r, ccz + dz)

    # ---------------------------------------------------------------------
    # Preloading
    # ---------------------------------------------------------------------
    def preload_chunks_around(self, center_x: float, center_z: float) -> Tuple[int, int]:
        """
        Preload all chunks around the given position within render distance.
        Returns (chunks_created, chunks_meshed) for progress tracking.
        """
        cx = floor(center_x) // settings.CHUNK_SIZE_X
        cz = floor(center_z) // settings.CHUNK_SIZE_Z
        center = (cx, cz)
        
        # Get all chunks within render distance
        desired: List[Tuple[int, int]] = []
        seen = set()
        for cc in self._spiral_coords(center, settings.RENDER_DISTANCE):
            if cc in seen:
                continue
            seen.add(cc)
            desired.append(cc)
        
        chunks_created = 0
        chunks_meshed = 0
        
        # Create all chunks
        for key in desired:
            if key not in self.chunks:
                self._ensure_chunk(*key)
                chunks_created += 1
        
        # Mesh all chunks
        for key in desired:
            if self._build_mesh_for(*key):
                chunks_meshed += 1
        
        self.preload_complete = True
        return chunks_created, chunks_meshed

    def _get_biome_blend_weight(self, wx: int, wz: int) -> float:
        """
        Get the biome blend weight for smooth terrain transitions.
        Returns a value from 0.0 (full plains) to 1.0 (full desert).
        Uses the same multi-octave noise system as biome detection for consistency.
        """
        from .util import _simplex_noise_2d
        
        # Use the same multi-layered noise calculation as get_biome()
        continental_noise = _simplex_noise_2d(float(wx) * 0.003, float(wz) * 0.003)
        regional_noise = _simplex_noise_2d(float(wx) * 0.008, float(wz) * 0.008)
        local_noise = _simplex_noise_2d(float(wx) * 0.02, float(wz) * 0.02)
        variation_noise = _simplex_noise_2d(float(wx) * 0.012 + 100.0, float(wz) * 0.012 + 100.0)
        
        # Combine with same weights as biome detection
        combined_noise = (
            continental_noise * 0.5 +
            regional_noise * 0.25 +
            local_noise * 0.15 +
            variation_noise * 0.1
        )
        
        # Use varying threshold matching get_biome()
        threshold_variation = _simplex_noise_2d(float(wx) * 0.001, float(wz) * 0.001) * 0.1
        desert_threshold = -0.5 + threshold_variation
        
        # Create smooth transition zone around the threshold
        # Wider zone for very smooth blending
        transition_width = 0.3
        
        if combined_noise < desert_threshold - transition_width:
            return 1.0  # Full desert
        elif combined_noise > desert_threshold + transition_width:
            return 0.0  # Full plains
        else:
            # Smooth interpolation in transition zone
            t = (combined_noise - (desert_threshold - transition_width)) / (2.0 * transition_width)
            # S-curve for ultra-smooth blending
            import math
            return 1.0 - (0.5 * (1.0 - math.cos(math.pi * t)))

    # ---------------------------------------------------------------------
    # Frame update
    # ---------------------------------------------------------------------
    def update(self, player_pos) -> None:
        """
        Stream chunks around player and build meshes within budgets.
        player_pos is a Vec3-like with (x, y, z) in world coordinates.
        """
        # Chunk in which the player is (use floor for negatives)
        cx = floor(player_pos.x) // settings.CHUNK_SIZE_X
        cz = floor(player_pos.z) // settings.CHUNK_SIZE_Z
        center = (cx, cz)

        # Determine desired chunk set
        desired: List[Tuple[int, int]] = []
        seen = set()
        for cc in self._spiral_coords(center, settings.RENDER_DISTANCE):
            if cc in seen:
                continue
            seen.add(cc)
            desired.append(cc)

        desired_set = set(desired)
        loaded_set = set(self.chunks.keys())

        # Unload chunks outside range
        for key in list(loaded_set - desired_set):
            # remove node
            np = self.chunk_nodes.pop(key, None)
            if np is not None and not np.isEmpty():
                np.removeNode()
            # remove data (rely on SaveSystem's incremental saves to preserve edits)
            self.chunks.pop(key, None)
            if settings.PRINT_CHUNK_EVENTS:
                print(f"[World] Unloaded chunk {key}")

        # Respect budgets: limited creates and meshes per frame
        creates_left = settings.MAX_CHUNK_CREATES_PER_FRAME
        meshes_left = settings.MAX_CHUNK_MESHES_PER_FRAME

        # Create missing chunks in near-to-far order
        for key in desired:
            if key in self.chunks:
                continue
            if creates_left <= 0:
                break
            self._ensure_chunk(*key)
            creates_left -= 1

        # Mesh dirty or new chunks in near-to-far order
        for key in desired:
            if meshes_left <= 0:
                break
            ch = self.chunks.get(key)
            if not ch:
                continue
            if ch.dirty or key not in self.chunk_nodes:
                if self._build_mesh_for(*key):
                    meshes_left -= 1

    # ---------------------------------------------------------------------
    # Block modification (mining and placing)
    # ---------------------------------------------------------------------
    def remove_block(self, wx: int, wy: int, wz: int) -> bool:
        """
        Remove (mine) a block at world coordinates (wx, wy, wz).
        Sets the block to AIR and marks the chunk as dirty for re-meshing.
        Returns True if successful, False if out of bounds or already air.
        """
        # Disallow modifying bedrock or blocks outside world height
        if wy <= 0 or wy >= settings.CHUNK_SIZE_Y:
            return False
        
        # Determine which chunk this block belongs to (use floor division for consistency)
        cx = floor(wx / settings.CHUNK_SIZE_X)
        cz = floor(wz / settings.CHUNK_SIZE_Z)
        
        chunk = self.chunks.get((cx, cz))
        if chunk is None:
            return False
        
        # Convert to local chunk coordinates
        lx = wx - cx * settings.CHUNK_SIZE_X
        lz = wz - cz * settings.CHUNK_SIZE_Z
        
        # Check if block is already air
        if chunk.get_block_local(lx, wy, lz) == BLOCK_AIR:
            return False
        
        # Set to air
        chunk.set_block_local(lx, wy, lz, BLOCK_AIR)
        
        # Mark neighboring chunks as dirty if block is on chunk edge
        self._mark_neighbors_dirty(wx, wy, wz, cx, cz)
        
        return True

    def place_block(self, wx: int, wy: int, wz: int, block_type: int) -> bool:
        """
        Place a block at world coordinates (wx, wy, wz).
        Returns True if successful, False if out of bounds or position is occupied.
        """
        # Disallow placing at bedrock level or outside world height
        if wy <= 0 or wy >= settings.CHUNK_SIZE_Y:
            return False
        
        # Determine which chunk this block belongs to (use floor division for consistency)
        cx = floor(wx / settings.CHUNK_SIZE_X)
        cz = floor(wz / settings.CHUNK_SIZE_Z)
        
        # Ensure chunk exists
        chunk = self._ensure_chunk(cx, cz)
        
        # Convert to local chunk coordinates
        lx = wx - cx * settings.CHUNK_SIZE_X
        lz = wz - cz * settings.CHUNK_SIZE_Z
        
        # Check if position is already occupied
        if chunk.get_block_local(lx, wy, lz) != BLOCK_AIR:
            return False
        
        # Place the block
        chunk.set_block_local(lx, wy, lz, block_type)
        
        # Mark neighboring chunks as dirty if block is on chunk edge
        self._mark_neighbors_dirty(wx, wy, wz, cx, cz)
        
        return True

    def _mark_neighbors_dirty(self, wx: int, wy: int, wz: int, cx: int, cz: int) -> None:
        """
        Mark neighboring chunks as dirty if the block is on a chunk boundary.
        This ensures that faces on adjacent chunks get updated correctly.
        """
        lx = wx - cx * settings.CHUNK_SIZE_X
        lz = wz - cz * settings.CHUNK_SIZE_Z
        
        # Check if block is on chunk boundaries and mark neighbor chunks dirty
        if lx == 0:
            neighbor = self.chunks.get((cx - 1, cz))
            if neighbor:
                neighbor.dirty = True
        elif lx == settings.CHUNK_SIZE_X - 1:
            neighbor = self.chunks.get((cx + 1, cz))
            if neighbor:
                neighbor.dirty = True
        
        if lz == 0:
            neighbor = self.chunks.get((cx, cz - 1))
            if neighbor:
                neighbor.dirty = True
        elif lz == settings.CHUNK_SIZE_Z - 1:
            neighbor = self.chunks.get((cx, cz + 1))
            if neighbor:
                neighbor.dirty = True

    # ---------------------------------------------------------------------
    # Utility for external collision queries
    # ---------------------------------------------------------------------
    def solid_at(self, wx: int, wy: int, wz: int) -> bool:
        """Public alias for is_solid, for clarity in other modules."""
        return self.is_solid(wx, wy, wz)

    def get_block(self, wx: int, wy: int, wz: int) -> int:
        """
        Get the block type at world coordinates (wx, wy, wz).
        Returns the block ID, checking loaded chunks first, then falling back to terrain generation.
        """
        # Check bounds
        if wy < 0:
            return BLOCK_BEDROCK
        if wy >= settings.CHUNK_SIZE_Y:
            return BLOCK_AIR
        
        # Determine chunk coordinates
        cx = floor(wx / settings.CHUNK_SIZE_X)
        cz = floor(wz / settings.CHUNK_SIZE_Z)
        
        # If chunk is loaded, check its actual block data
        chunk = self.chunks.get((cx, cz))
        if chunk is not None:
            lx = wx - cx * settings.CHUNK_SIZE_X
            lz = wz - cz * settings.CHUNK_SIZE_Z
            return chunk.get_block_local(lx, wy, lz)
        
        # Otherwise fall back to terrain generation
        return self.block_id_at(wx, wy, wz)
    
    def _apply_saved_modifications(self, chunk: Chunk, cx: int, cz: int) -> None:
        """
        Load saved chunk data from individual chunk file (Minecraft-style).
        If a saved chunk exists, load its complete block data.
        """
        if self.save_system is None:
            return
        
        try:
            # Try to load saved chunk data
            saved_blocks = self.save_system.load_chunk(cx, cz)
            
            if saved_blocks is not None:
                # Replace the chunk's blocks with saved data
                chunk.blocks = saved_blocks
                chunk.dirty = True
                
                if settings.PRINT_CHUNK_EVENTS:
                    print(f"[World] Loaded saved chunk data for ({cx}, {cz})")
        
        except Exception as e:
            print(f"[World] Error loading saved chunk ({cx}, {cz}): {e}")
    
    def cleanup(self) -> None:
        """
        Clean up all world resources: remove all chunk nodes from render tree
        and clear all data structures. Call this before destroying the world.
        """
        # Remove all chunk nodes from the render tree
        for key, node_path in list(self.chunk_nodes.items()):
            if node_path is not None and not node_path.isEmpty():
                node_path.removeNode()
        
        # Clear the chunk data
        self.chunk_nodes.clear()
        self.chunks.clear()
        
        # Remove the world root node from the render tree
        if self.root is not None and not self.root.isEmpty():
            self.root.removeNode()
            self.root = None
        
        print("[World] Cleaned up all world resources")

    def _cactus_touching_another(self, chunk: Chunk, lx: int, y: int, lz: int, wx0: int, wz0: int) -> bool:
        """
        Check if a cactus base at (lx, y, lz) is touching another cactus base.
        Touching includes adjacent blocks (including diagonals) at horizontal level.
        """
        # Check all 8 adjacent positions at this y level
        for dz in range(-1, 2):
            for dx in range(-1, 2):
                if dx == 0 and dz == 0:
                    continue  # Skip self

                check_lx = lx + dx
                check_lz = lz + dz

                # Check bounds (might be in adjacent chunks, but for now only within chunk)
                if 0 <= check_lx < settings.CHUNK_SIZE_X and 0 <= check_lz < settings.CHUNK_SIZE_Z:
                    if chunk.get_block_local(check_lx, y, check_lz) == 11:  # BLOCK_CACTUS
                        return True

        return False
