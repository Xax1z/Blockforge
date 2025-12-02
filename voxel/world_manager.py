"""
World Manager for handling multiple worlds.
Manages world metadata, screenshots, and world selection.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
import random


class WorldInfo:
    """Information about a saved world."""
    
    def __init__(self, name: str, folder: str, seed: int, created: str, last_played: str = None, screenshot: str = None, game_mode: str = "Survival", difficulty: int = 2):
        self.name = name
        self.folder = folder  # Folder name in saves directory
        self.seed = seed
        self.created = created
        self.last_played = last_played or created
        self.screenshot = screenshot  # Path to screenshot PNG
        self.game_mode = game_mode
        self.difficulty = difficulty
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "folder": self.folder,
            "seed": self.seed,
            "created": self.created,
            "last_played": self.last_played,
            "screenshot": self.screenshot,
            "game_mode": getattr(self, "game_mode", "Survival"),
            "difficulty": getattr(self, "difficulty", 2)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorldInfo':
        """Create WorldInfo from dictionary."""
        return cls(
            name=data["name"],
            folder=data["folder"],
            seed=data["seed"],
            created=data["created"],
            last_played=data.get("last_played"),
            screenshot=data.get("screenshot"),
            game_mode=data.get("game_mode", "Survival"),
            difficulty=data.get("difficulty", 2)
        )


class WorldManager:
    """Manages multiple worlds and their metadata."""
    
    def __init__(self, base_save_dir: str = "saves"):
        self.base_save_dir = base_save_dir
        self.worlds_file = os.path.join(base_save_dir, "worlds.json")
        
        # Create base save directory if it doesn't exist
        if not os.path.exists(base_save_dir):
            os.makedirs(base_save_dir)
        
        # Load or initialize worlds list
        self.worlds: List[WorldInfo] = []
        self._load_worlds()
    
    def _load_worlds(self):
        """Load worlds list from JSON file."""
        if os.path.exists(self.worlds_file):
            try:
                with open(self.worlds_file, 'r') as f:
                    data = json.load(f)
                    self.worlds = [WorldInfo.from_dict(w) for w in data.get("worlds", [])]
                    print(f"[WorldManager] Loaded {len(self.worlds)} worlds")
            except Exception as e:
                print(f"[WorldManager] Error loading worlds: {e}")
                self.worlds = []
        else:
            self.worlds = []
    
    def _save_worlds(self):
        """Save worlds list to JSON file."""
        try:
            data = {
                "worlds": [w.to_dict() for w in self.worlds]
            }
            with open(self.worlds_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"[WorldManager] Saved {len(self.worlds)} worlds")
        except Exception as e:
            print(f"[WorldManager] Error saving worlds: {e}")
    
    def create_world(self, name: str, seed: Optional[int] = None, game_mode: str = "Survival", difficulty: int = 2) -> WorldInfo:
        """
        Create a new world.
        
        Args:
            name: World name
            seed: World seed (random if None)
            game_mode: Game mode (Survival)
            difficulty: Difficulty level (2 = Normal)
        
        Returns:
            WorldInfo object for the new world
        """
        # Generate seed if not provided
        if seed is None:
            seed = random.randint(0, 999999999)
        
        # Create unique folder name
        folder = self._generate_folder_name(name)
        
        # Create world directory
        world_dir = os.path.join(self.base_save_dir, folder)
        os.makedirs(world_dir, exist_ok=True)
        
        # Create chunks subdirectory
        chunks_dir = os.path.join(world_dir, "chunks")
        os.makedirs(chunks_dir, exist_ok=True)
        
        # Create world info
        timestamp = datetime.now().isoformat()
        world_info = WorldInfo(
            name=name,
            folder=folder,
            seed=seed,
            created=timestamp,
            last_played=timestamp,
            game_mode=game_mode,
            difficulty=difficulty
        )
        
        # Add to worlds list
        self.worlds.append(world_info)
        self._save_worlds()
        
        print(f"[WorldManager] Created world '{name}' with seed {seed}, mode {game_mode}, difficulty {difficulty}")
        return world_info
    
    def _generate_folder_name(self, name: str) -> str:
        """Generate a unique folder name from world name."""
        # Sanitize name for filesystem
        base = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in name)
        if not base:
            base = "world"
        
        # Ensure uniqueness
        folder = base
        counter = 1
        while any(w.folder == folder for w in self.worlds):
            folder = f"{base}_{counter}"
            counter += 1
        
        return folder
    
    def get_world(self, folder: str) -> Optional[WorldInfo]:
        """Get world info by folder name."""
        for world in self.worlds:
            if world.folder == folder:
                return world
        return None
    
    def get_world_by_name(self, name: str) -> Optional[WorldInfo]:
        """Get world info by world name."""
        for world in self.worlds:
            if world.name == name:
                return world
        return None
    
    def delete_world(self, folder: str) -> bool:
        """Delete a world and its data."""
        import shutil
        import time
        
        try:
            # Find world
            world = self.get_world(folder)
            if not world:
                return False
            
            # Delete world directory - use robust Windows-compatible approach
            world_dir = os.path.join(self.base_save_dir, folder)
            if os.path.exists(world_dir):
                # Try multiple times with delays for Windows file locking
                max_attempts = 3
                for attempt in range(max_attempts):
                    try:
                        # Use ignore_errors for better Windows compatibility
                        shutil.rmtree(world_dir, ignore_errors=False, onerror=self._handle_remove_readonly)
                        print(f"[WorldManager] Deleted world directory '{folder}'")
                        break
                    except Exception as e:
                        if attempt < max_attempts - 1:
                            print(f"[WorldManager] Delete attempt {attempt + 1} failed, retrying...")
                            time.sleep(0.3)  # Wait for Windows to release locks
                        else:
                            # Last attempt - try with ignore_errors=True
                            shutil.rmtree(world_dir, ignore_errors=True)
                            print(f"[WorldManager] Deleted world directory with some errors ignored")
            
            # Remove from worlds list
            self.worlds = [w for w in self.worlds if w.folder != folder]
            self._save_worlds()
            
            print(f"[WorldManager] Deleted world '{world.name}'")
            return True
            
        except Exception as e:
            print(f"[WorldManager] Error deleting world: {e}")
            return False
    
    def _handle_remove_readonly(self, func, path, exc):
        """Error handler for Windows readonly files."""
        import stat
        try:
            # Try to make file writable and retry
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception as e:
            print(f"[WorldManager] Could not delete {path}: {e}")
    
    def update_last_played(self, folder: str):
        """Update the last played timestamp for a world."""
        world = self.get_world(folder)
        if world:
            world.last_played = datetime.now().isoformat()
            self._save_worlds()
    
    def get_world_path(self, folder: str) -> str:
        """Get the full path to a world's directory."""
        return os.path.join(self.base_save_dir, folder)
    
    def get_worlds_sorted_by_last_played(self) -> List[WorldInfo]:
        """Get worlds sorted by last played (most recent first)."""
        return sorted(self.worlds, key=lambda w: w.last_played, reverse=True)
    
    def save_screenshot(self, folder: str, screenshot_path: str):
        """Save screenshot path for a world."""
        world = self.get_world(folder)
        if world:
            world.screenshot = screenshot_path
            self._save_worlds()
