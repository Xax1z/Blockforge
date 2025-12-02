"""
Save and load system for the voxel game.
Saves player state and modified chunks to JSON files.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Set

from . import settings


class SaveSystem:
    """Handles saving and loading game state."""
    
    def __init__(self, save_dir: str = "saves"):
        self.save_dir = save_dir
        # Create saves directory if it doesn't exist
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        # Create chunks directory for individual chunk saves
        self.chunks_dir = os.path.join(save_dir, "chunks")
        if not os.path.exists(self.chunks_dir):
            os.makedirs(self.chunks_dir)
        
        # World metadata file path (stores seed and other world info)
        self.world_metadata_path = os.path.join(save_dir, "world.json")
    
    def save_game(self, player, world, save_name: str = "quicksave") -> bool:
        """
        Save the current game state.
        
        Args:
            player: Player instance
            world: World instance
            save_name: Name for the save file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare save data
            save_data = {
                "version": "1.0",
                "timestamp": datetime.now().isoformat(),
                "player": self._serialize_player(player),
                "world": self._serialize_world(world)
            }
            
            # Write to file
            save_path = os.path.join(self.save_dir, f"{save_name}.json")
            with open(save_path, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            print(f"[SaveSystem] Game saved to {save_path}")
            return True
            
        except Exception as e:
            print(f"[SaveSystem] Error saving game: {e}")
            return False

    # ------------------------------------------------------------------
    # Minecraft-style individual chunk saving
    # ------------------------------------------------------------------
    def save_chunk(self, chunk, cx: int, cz: int) -> None:
        """
        Save a single chunk to its own file (Minecraft-style).
        Saves the complete block data, not just differences.
        """
        try:
            # Create filename: chunk_X_Z.json
            chunk_filename = f"chunk_{cx}_{cz}.json"
            chunk_path = os.path.join(self.chunks_dir, chunk_filename)
            
            # Serialize all block data
            chunk_data = {
                "cx": cx,
                "cz": cz,
                "blocks": chunk.blocks  # Save complete block array
            }
            
            # Write to file
            with open(chunk_path, 'w') as f:
                json.dump(chunk_data, f)
                
        except Exception as e:
            print(f"[SaveSystem] Error saving chunk ({cx}, {cz}): {e}")
    
    def load_chunk(self, cx: int, cz: int) -> Optional[List[int]]:
        """
        Load a single chunk's block data from its file.
        Returns the blocks array if found, None otherwise.
        """
        try:
            chunk_filename = f"chunk_{cx}_{cz}.json"
            chunk_path = os.path.join(self.chunks_dir, chunk_filename)
            
            if not os.path.exists(chunk_path):
                return None
            
            with open(chunk_path, 'r') as f:
                chunk_data = json.load(f)
            
            return chunk_data.get("blocks")
            
        except Exception as e:
            print(f"[SaveSystem] Error loading chunk ({cx}, {cz}): {e}")
            return None
    
    def save_world_seed(self, seed: int) -> bool:
        """
        Save the world seed to world.json file.
        Returns True if successful, False otherwise.
        """
        try:
            world_data = {
                "seed": seed,
                "created": datetime.now().isoformat()
            }
            
            with open(self.world_metadata_path, 'w') as f:
                json.dump(world_data, f, indent=2)
            
            print(f"[SaveSystem] Saved world seed: {seed}")
            return True
            
        except Exception as e:
            print(f"[SaveSystem] Error saving world seed: {e}")
            return False
    
    def load_world_seed(self) -> Optional[int]:
        """
        Load the world seed from world.json file.
        Returns the seed if found, None otherwise.
        """
        try:
            if not os.path.exists(self.world_metadata_path):
                return None
            
            with open(self.world_metadata_path, 'r') as f:
                world_data = json.load(f)
            
            seed = world_data.get("seed")
            if seed is not None:
                print(f"[SaveSystem] Loaded world seed: {seed}")
            return seed
            
        except Exception as e:
            print(f"[SaveSystem] Error loading world seed: {e}")
            return None
    
    def save_player_data(self, player) -> None:
        """
        Save player data to player.json file.
        Stores position, orientation, velocity, and hotbar/inventory.
        """
        try:
            player_path = os.path.join(self.save_dir, "player.json")
            player_data = self._serialize_player(player)
            
            with open(player_path, 'w') as f:
                json.dump(player_data, f, indent=2)
                
        except Exception as e:
            print(f"[SaveSystem] Error saving player data: {e}")
    
    def load_player_data(self, player) -> bool:
        """
        Load player data from player.json file.
        Returns True if successful, False if file doesn't exist.
        """
        try:
            player_path = os.path.join(self.save_dir, "player.json")
            
            if not os.path.exists(player_path):
                return False
            
            with open(player_path, 'r') as f:
                player_data = json.load(f)
            
            # Backward compatibility: if file is a full save, extract nested player data
            if "position" not in player_data and "player" in player_data:
                player_data = player_data["player"]
            
            # Only load if position data is present
            if "position" in player_data:
                self._deserialize_player(player_data, player)
                return True
            else:
                return False
            
        except Exception as e:
            print(f"[SaveSystem] Error loading player data: {e}")
            return False
    
    def save_block_edit(self, world, wx: int, wy: int, wz: int, save_name: str = "quicksave") -> None:
        """
        Save the chunk containing the edited block immediately.
        Uses Minecraft-style per-chunk files.
        """
        try:
            cx = wx // settings.CHUNK_SIZE_X
            cz = wz // settings.CHUNK_SIZE_Z
            
            # Get the chunk from world
            chunk = world.chunks.get((cx, cz))
            if chunk is not None:
                self.save_chunk(chunk, cx, cz)
                
        except Exception as e:
            print(f"[SaveSystem] Error in save_block_edit: {e}")

    def _save_modified_chunk(self, world, cx: int, cz: int, save_name: str) -> None:
        """
        Update/save data for a single chunk (cx, cz) inside the given save file.
        Uses the same 'modified_chunks' schema as full saves, but only touches one chunk.
        """
        save_path = os.path.join(self.save_dir, f"{save_name}.json")

        # Load existing save if present; otherwise start a new minimal structure.
        if os.path.exists(save_path):
            try:
                with open(save_path, "r") as f:
                    save_data = json.load(f)
            except Exception:
                # If existing file is corrupt, fall back to fresh structure.
                save_data = {}
        else:
            save_data = {}

        # Ensure base structure
        if "version" not in save_data:
            save_data["version"] = "1.0"
        save_data["timestamp"] = datetime.now().isoformat()

        if "player" not in save_data:
            # If no player snapshot yet, we do NOT attempt to infer it here;
            # autosaves for chunks are purely world-state. Quicksave (F5) will
            # capture full player state when requested.
            save_data["player"] = {}
        if "world" not in save_data:
            save_data["world"] = {}
        if "modified_chunks" not in save_data["world"]:
            save_data["world"]["modified_chunks"] = {}

        modified_chunks = save_data["world"]["modified_chunks"]

        # Locate the chunk in memory; if it's not loaded, generate it so we can diff.
        chunk = world.chunks.get((cx, cz))
        if chunk is None:
            # Ensure chunk exists so we can inspect its blocks.
            chunk = world._ensure_chunk(cx, cz)

        # Compute diff for this chunk only
        modified_blocks = []
        for y in range(settings.CHUNK_SIZE_Y):
            for lz in range(settings.CHUNK_SIZE_Z):
                for lx in range(settings.CHUNK_SIZE_X):
                    current_block = chunk.get_block_local(lx, y, lz)
                    wx = cx * settings.CHUNK_SIZE_X + lx
                    wz = cz * settings.CHUNK_SIZE_Z + lz
                    generated_block = world.block_id_at(wx, y, wz)
                    if current_block != generated_block:
                        modified_blocks.append({
                            "x": lx,
                            "y": y,
                            "z": lz,
                            "block_id": current_block,
                        })

        key = f"{cx},{cz}"
        if modified_blocks:
            modified_chunks[key] = modified_blocks
        else:
            # If no differences remain, drop this chunk from save to keep file small.
            if key in modified_chunks:
                del modified_chunks[key]

        # Write updated save file
        with open(save_path, "w") as f:
            json.dump(save_data, f, indent=2)
    
    def load_game(self, player, world, save_name: str = "quicksave") -> bool:
        """
        Load a saved game state.
        
        Args:
            player: Player instance to restore state to
            world: World instance to restore state to
            save_name: Name of the save file to load
            
        Returns:
            True if successful, False otherwise
        """
        try:
            save_path = os.path.join(self.save_dir, f"{save_name}.json")
            
            if not os.path.exists(save_path):
                print(f"[SaveSystem] Save file not found: {save_path}")
                return False
            
            # Read save file
            with open(save_path, 'r') as f:
                save_data = json.load(f)
            
            # Restore player state
            self._deserialize_player(save_data["player"], player)
            
            # Restore world state (modified chunks)
            self._deserialize_world(save_data["world"], world)
            
            print(f"[SaveSystem] Game loaded from {save_path}")
            return True
            
        except Exception as e:
            print(f"[SaveSystem] Error loading game: {e}")
            return False
    
    def _serialize_player(self, player) -> dict:
        """Serialize player state to a dictionary."""
        data = {
            "position": {
                "x": float(player.position.x),
                "y": float(player.position.y),
                "z": float(player.position.z)
            },
            "velocity": {
                "x": float(player.velocity.x),
                "y": float(player.velocity.y),
                "z": float(player.velocity.z)
            },
            "orientation": {
                "yaw": float(player.yaw),
                "pitch": float(player.pitch)
            },
            "on_ground": player.on_ground,
            "health": float(player.health),
            "hunger": float(player.hunger),
            "saturation": float(player.saturation),
        }

        # Serialize hotbar from the owning App instance if available
        app = getattr(player, "app", None)
        if app is not None and hasattr(app, "hotbar") and hasattr(app, "selected_hotbar_slot"):
            data["hotbar"] = {
                "slots": app.hotbar,
                "selected": app.selected_hotbar_slot,
            }
            if hasattr(app, "inventory"):
                data["inventory"] = app.inventory

        return data
    
    def _deserialize_player(self, data: dict, player) -> None:
        """Restore player state from a dictionary."""
        from panda3d.core import Vec3
        
        # Restore position
        player.position = Vec3(
            data["position"]["x"],
            data["position"]["y"],
            data["position"]["z"]
        )
        
        # Restore velocity
        player.velocity = Vec3(
            data["velocity"]["x"],
            data["velocity"]["y"],
            data["velocity"]["z"]
        )
        
        # Restore orientation
        player.yaw = data["orientation"]["yaw"]
        player.pitch = data["orientation"]["pitch"]
        
        # Restore ground state
        player.on_ground = data["on_ground"]
        
        # Restore survival stats (with defaults for backward compatibility)
        player.health = float(data.get("health", player.max_health))
        player.hunger = float(data.get("hunger", player.max_hunger))
        player.saturation = float(data.get("saturation", 5.0))
        
        # Update camera to reflect new position
        player._update_camera()

        # Restore hotbar if available
        app = getattr(player, "app", None)
        hotbar_data: Any = data.get("hotbar")
        if app is not None and hotbar_data is not None:
            # Only assign if structure matches expected keys
            slots = hotbar_data.get("slots")
            selected = hotbar_data.get("selected")
            if isinstance(slots, list) and isinstance(selected, int):
                app.hotbar = slots
                app.selected_hotbar_slot = max(0, min(selected, getattr(app, "hotbar_size", len(slots)) - 1))
                if hasattr(app, "_update_hotbar_ui"):
                    app._update_hotbar_ui()
        
        # Restore inventory
        inventory_data: Any = data.get("inventory")
        if app is not None and inventory_data is not None and hasattr(app, "inventory"):
             if isinstance(inventory_data, list):
                 # Copy saved inventory, handling size mismatches gracefully
                 for i in range(min(len(app.inventory), len(inventory_data))):
                     app.inventory[i] = inventory_data[i]
    
    def _serialize_world(self, world) -> dict:
        """
        Serialize modified chunks to a dictionary.
        Only saves chunks that have been modified from their generated state.
        """
        modified_chunks = {}
        
        for (cx, cz), chunk in world.chunks.items():
            # Get modified blocks in this chunk
            modified_blocks = []
            
            for y in range(settings.CHUNK_SIZE_Y):
                for lz in range(settings.CHUNK_SIZE_Z):
                    for lx in range(settings.CHUNK_SIZE_X):
                        # Get current block
                        current_block = chunk.get_block_local(lx, y, lz)
                        
                        # Get what the block should be based on terrain generation
                        wx = cx * settings.CHUNK_SIZE_X + lx
                        wz = cz * settings.CHUNK_SIZE_Z + lz
                        generated_block = world.block_id_at(wx, y, wz)
                        
                        # If different from generated, save it
                        if current_block != generated_block:
                            modified_blocks.append({
                                "x": lx,
                                "y": y,
                                "z": lz,
                                "block_id": current_block
                            })
            
            # Only save chunk if it has modifications
            if modified_blocks:
                chunk_key = f"{cx},{cz}"
                modified_chunks[chunk_key] = modified_blocks
        
        return {
            "modified_chunks": modified_chunks
        }
    
    def _deserialize_world(self, data: dict, world) -> None:
        """
        Restore modified chunks to the world.
        Applies block modifications on top of generated terrain.
        """
        modified_chunks = data.get("modified_chunks", {})
        
        for chunk_key, modified_blocks in modified_chunks.items():
            # Parse chunk coordinates
            cx, cz = map(int, chunk_key.split(','))
            
            # Ensure chunk exists
            chunk = world._ensure_chunk(cx, cz)
            
            # Apply each modified block
            for block_data in modified_blocks:
                lx = block_data["x"]
                y = block_data["y"]
                lz = block_data["z"]
                block_id = block_data["block_id"]
                
                chunk.set_block_local(lx, y, lz, block_id)
            
            # Mark chunk as dirty so it gets re-meshed
            chunk.dirty = True
        
        print(f"[SaveSystem] Restored {len(modified_chunks)} modified chunks")
    
    def list_saves(self) -> List[str]:
        """List all available save files."""
        if not os.path.exists(self.save_dir):
            return []
        
        saves = []
        for filename in os.listdir(self.save_dir):
            if filename.endswith('.json'):
                saves.append(filename[:-5])  # Remove .json extension
        
        return sorted(saves)
    
    def delete_save(self, save_name: str) -> bool:
        """Delete a save file."""
        try:
            save_path = os.path.join(self.save_dir, f"{save_name}.json")
            if os.path.exists(save_path):
                os.remove(save_path)
                print(f"[SaveSystem] Deleted save: {save_path}")
                return True
            return False
        except Exception as e:
            print(f"[SaveSystem] Error deleting save: {e}")
            return False

    @staticmethod
    def save_settings() -> None:
        """Save current global settings to settings.json."""
        try:
            data = {
                "fov": float(settings.FOV)
            }
            with open("settings.json", 'w') as f:
                json.dump(data, f, indent=2)
            print("[SaveSystem] Global settings saved")
        except Exception as e:
            print(f"[SaveSystem] Error saving settings: {e}")

    @staticmethod
    def load_settings() -> None:
        """Load global settings from settings.json."""
        try:
            if not os.path.exists("settings.json"):
                return
            
            with open("settings.json", 'r') as f:
                data = json.load(f)
                
            if "fov" in data:
                settings.FOV = float(data["fov"])
                print(f"[SaveSystem] Loaded FOV: {settings.FOV}")
                
        except Exception as e:
            print(f"[SaveSystem] Error loading settings: {e}")