"""
Texture manager for loading and managing block/item textures.
"""

from panda3d.core import Texture, TextureStage, PNMImage, SamplerState, Filename
import os
from typing import Dict, Optional


class TextureManager:
    """Manages loading and caching of textures."""
    
    def __init__(self):
        self.textures: Dict[str, Texture] = {}
        self.asset_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
        self.texture_stage = TextureStage("ts")
        self.texture_stage.setMode(TextureStage.MModulate)
        
        self.atlas = TextureAtlas()
        self.load_all_block_textures()
        
        print(f"[TextureManager] Asset path: {self.asset_path}")
        
    def load_all_block_textures(self):
        """Load all known block textures into the atlas."""
        block_path = os.path.join(self.asset_path, 'blocks')
        if not os.path.exists(block_path):
            print(f"[TextureManager] Error: Block path not found: {block_path}")
            return

        # List of all texture names we might need
        # This includes values in BLOCK_TEXTURES and special cases in get_block_texture_name
        needed_textures = set(BLOCK_TEXTURES.values())
        needed_textures.add('wood_top')
        needed_textures.add('jungle_log_top')
        needed_textures.add('birch_log_top')
        # Add any others that might be missing
        
        for filename in os.listdir(block_path):
            if filename.endswith('.png'):
                name = filename[:-4] # remove .png
                
                filepath = os.path.join(block_path, filename)
                panda_path = Filename.fromOsSpecific(filepath)
                
                img = PNMImage()
                if img.read(panda_path):
                    self.atlas.add_texture(name, img)
                    print(f"[TextureManager] Added to atlas: {name}")
                else:
                    print(f"[TextureManager] Failed to read: {filename}")
                    
        self.atlas.build()

    def get_atlas_texture(self) -> Optional[Texture]:
        return self.atlas.atlas_texture
        
    def get_uvs(self, texture_name: str):
        return self.atlas.get_uvs(texture_name)
    
    def load_texture(self, category: str, filename: str) -> Optional[Texture]:
        """
        Load a texture from assets folder.
        category: 'blocks', 'items', or 'meat'
        filename: name of the PNG file (e.g., 'grass.png')
        """
        key = f"{category}/{filename}"
        
        # Check cache
        if key in self.textures:
            return self.textures[key]
        
        # Load from file
        filepath = os.path.join(self.asset_path, category, filename)
        
        if not os.path.exists(filepath):
            print(f"[TextureManager] Warning: Texture not found: {filepath}")
            return None
        
        try:
            # Convert to Panda3D Filename (handles path conversion automatically)
            panda_path = Filename.fromOsSpecific(filepath)
            
            # Load image
            img = PNMImage()
            if not img.read(panda_path):
                print(f"[TextureManager] Error: Failed to read texture: {filepath}")
                return None
            
            # Create texture
            tex = Texture()
            tex.load(img)
            tex.setMagfilter(SamplerState.FT_nearest)  # Nearest neighbor for crisp pixels
            tex.setMinfilter(SamplerState.FT_nearest)
            tex.setWrapU(SamplerState.WM_repeat)
            tex.setWrapV(SamplerState.WM_repeat)
            
            # Cache it
            self.textures[key] = tex
            # print(f"[TextureManager] Loaded: {key}")
            
            return tex
            
        except Exception as e:
            print(f"[TextureManager] Error loading texture {filepath}: {e}")
            return None
    
    def get_block_texture(self, block_name: str) -> Optional[Texture]:
        """Get texture for a block type (legacy/single texture use)."""
        return self.load_texture('blocks', f'{block_name}.png')
    
    def get_item_texture(self, item_name: str) -> Optional[Texture]:
        """Get texture for an item type."""
        return self.load_texture('items', f'{item_name}.png')
    
    def get_meat_texture(self, meat_name: str) -> Optional[Texture]:
        """Get texture for a meat/food type."""
        return self.load_texture('meat', f'{meat_name}.png')
    
    def get_texture_stage(self) -> TextureStage:
        """Get the texture stage for applying textures."""
        return self.texture_stage


# Block ID to texture name mapping
BLOCK_TEXTURES = {
    1: 'grass',        # BLOCK_GRASS
    2: 'dirt',         # BLOCK_DIRT
    3: 'stone',        # BLOCK_STONE
    4: 'bedrock',      # BLOCK_BEDROCK
    5: 'sand',         # BLOCK_SAND
    6: 'wood',         # BLOCK_WOOD
    7: 'leaves',       # BLOCK_LEAVES
    8: 'cobblestone',  # BLOCK_COBBLESTONE
    9: 'brick',        # BLOCK_BRICK
    10: 'sandstone',   # BLOCK_SANDSTONE
    11: 'cactus',      # BLOCK_CACTUS
    12: 'planks',      # BLOCK_PLANKS
    26: 'crafting_table',  # BLOCK_CRAFTING_TABLE
    27: 'furnace',     # BLOCK_FURNACE
    28: 'chest',       # BLOCK_CHEST
    30: 'jungle_log',  # BLOCK_JUNGLE_LOG
    31: 'jungle_leaves', # BLOCK_JUNGLE_LEAVES
    32: 'birch_log',   # BLOCK_BIRCH_LOG
    33: 'birch_leaves', # BLOCK_BIRCH_LEAVES
    34: 'coal_ore',     # BLOCK_COAL_ORE
    35: 'iron_ore',     # BLOCK_IRON_ORE
    36: 'diamond_ore',  # BLOCK_DIAMOND_ORE
    37: 'gold_ore',     # BLOCK_GOLD_ORE
    38: 'jungle_planks', # BLOCK_JUNGLE_PLANKS
    39: 'birch_planks',  # BLOCK_BIRCH_PLANKS
}


class TextureAtlas:
    """
    Manages a texture atlas (single large texture containing many smaller textures).
    This allows rendering chunks with a single draw call while supporting many block types.
    """
    def __init__(self, texture_size=32):
        self.texture_size = texture_size
        self.textures = {}  # name -> image
        self.uv_map = {}    # name -> (u_min, v_min, u_max, v_max)
        self.atlas_texture = None
        
    def add_texture(self, name, image):
        self.textures[name] = image
        
    def build(self):
        """Stitch all textures into a single atlas."""
        if not self.textures:
            return
            
        count = len(self.textures)
        import math
        # Calculate atlas size (power of 2)
        cols = math.ceil(math.sqrt(count))
        rows = math.ceil(count / cols)
        
        atlas_width = cols * self.texture_size
        atlas_height = rows * self.texture_size
        
        # Create atlas image
        self.atlas_image = PNMImage(atlas_width, atlas_height)
        # self.atlas_image.fill(1, 0, 1) # Debug pink background
        
        sorted_names = sorted(self.textures.keys())
        
        for i, name in enumerate(sorted_names):
            col = i % cols
            row = i // cols
            
            x = col * self.texture_size
            y = row * self.texture_size
            
            # Copy texture to atlas
            self.atlas_image.copySubImage(self.textures[name], x, y, 0, 0, self.texture_size, self.texture_size)
            
            # Calculate UVs
            # In Panda3D, V=0 is bottom, V=1 is top. But PNMImage (0,0) is top-left.
            # So we need to flip V coordinate when mapping to texture coordinates?
            # Actually, Texture.load(PNMImage) handles this. 
            # Standard UVs: (0,0) is bottom-left, (1,1) is top-right.
            # PNMImage: (0,0) is top-left.
            # So row 0 in PNMImage is the TOP of the texture (V=1.0).
            # Wait, let's stick to standard logic:
            # U = x / width
            # V = 1.0 - (y + height) / total_height  (if y is from top)
            
            u_min = x / atlas_width
            u_max = (x + self.texture_size) / atlas_width
            
            # PNMImage y is from top. Texture V is from bottom.
            # y=0 is top (V=1). y=atlas_height is bottom (V=0).
            # The sub-image at 'y' extends to 'y + size'.
            # In V coords, this corresponds to:
            # top_v = 1.0 - (y / atlas_height)
            # bottom_v = 1.0 - ((y + size) / atlas_height)
            
            v_max = 1.0 - (y / atlas_height)
            v_min = 1.0 - ((y + self.texture_size) / atlas_height)
            
            self.uv_map[name] = (u_min, v_min, u_max, v_max)
            
        # Create texture from atlas image
        self.atlas_texture = Texture()
        self.atlas_texture.load(self.atlas_image)
        self.atlas_texture.setMagfilter(SamplerState.FT_nearest)
        self.atlas_texture.setMinfilter(SamplerState.FT_nearest)
        
        print(f"[TextureAtlas] Built {atlas_width}x{atlas_height} atlas with {count} textures")

    def get_uvs(self, name):
        return self.uv_map.get(name)


def get_block_texture_name(block_id: int, face: str = 'side') -> Optional[str]:
    """
    Get the texture name for a block face.
    Some blocks have different textures on different faces.
    """
    if block_id == 1:  # GRASS
        if face == 'top':
            return 'grass'
        elif face == 'bottom':
            return 'dirt'
        else:
            return 'grass'  # Could create grass_side.png for better look
    elif block_id == 6:  # WOOD
        if face in ('top', 'bottom'):
            return 'wood_top'
        else:
            return 'wood'
    elif block_id == 30:  # JUNGLE_LOG
        if face in ('top', 'bottom'):
            return 'jungle_log_top'
        else:
            return 'jungle_log'
    elif block_id == 32:  # BLOCK_BIRCH_LOG
        if face in ('top', 'bottom'):
            return 'birch_log_top'
        else:
            return 'birch_log'
    else:
        return BLOCK_TEXTURES.get(block_id)
