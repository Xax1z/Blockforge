from direct.gui.DirectGui import DirectFrame, DirectLabel, DirectButton, DGG, DirectScrolledFrame
from direct.showbase.DirectObject import DirectObject
from direct.task import Task
from panda3d.core import TextNode, TransparencyAttrib
from voxel import settings
from voxel.chunk import (
    BLOCK_GRASS, BLOCK_DIRT, BLOCK_STONE, BLOCK_SAND, BLOCK_WOOD, BLOCK_LEAVES,
    BLOCK_COBBLESTONE, BLOCK_BRICK, BLOCK_BEDROCK, BLOCK_SANDSTONE, BLOCK_PLANKS,
    BLOCK_STICKS, BLOCK_CRAFTING_TABLE,
    BLOCK_PICKAXE_WOOD, BLOCK_PICKAXE_STONE, BLOCK_PICKAXE_IRON,
    BLOCK_AXE_WOOD, BLOCK_AXE_STONE, BLOCK_AXE_IRON,
    BLOCK_SHOVEL_WOOD, BLOCK_SHOVEL_STONE, BLOCK_SHOVEL_IRON,
    BLOCK_SWORD_WOOD, BLOCK_SWORD_STONE, BLOCK_SWORD_IRON,
    BLOCK_JUNGLE_LOG, BLOCK_BIRCH_LOG, BLOCK_JUNGLE_PLANKS, BLOCK_BIRCH_PLANKS
)
from voxel.mob_system import ITEM_RAW_MEAT, ITEM_RAW_CHICKEN, ITEM_RAW_PORK

class CreativeInventoryUI(DirectObject):
    def __init__(self, app):
        self.app = app
        self.texture_manager = None
        
        self.frame = None
        self.window = None
        self.tabs = []
        self.current_tab = "Blocks"
        self.item_grid = None
        self.item_buttons = []
        
        self.is_open = False
        self.tooltip = None
        self.hovered_item = None
        
        # Categories
        self.categories = {
            "Blocks": [
                BLOCK_GRASS, BLOCK_DIRT, BLOCK_STONE, BLOCK_COBBLESTONE, 
                BLOCK_SAND, BLOCK_SANDSTONE, BLOCK_BEDROCK, BLOCK_BRICK,
                BLOCK_WOOD, BLOCK_LEAVES, BLOCK_PLANKS, BLOCK_CRAFTING_TABLE,
                BLOCK_JUNGLE_LOG, BLOCK_BIRCH_LOG, BLOCK_JUNGLE_PLANKS, BLOCK_BIRCH_PLANKS
            ],
            "Tools": [
                BLOCK_PICKAXE_WOOD, BLOCK_PICKAXE_STONE, BLOCK_PICKAXE_IRON,
                BLOCK_AXE_WOOD, BLOCK_AXE_STONE, BLOCK_AXE_IRON,
                BLOCK_SHOVEL_WOOD, BLOCK_SHOVEL_STONE, BLOCK_SHOVEL_IRON,
                BLOCK_SWORD_WOOD, BLOCK_SWORD_STONE, BLOCK_SWORD_IRON,
                BLOCK_STICKS
            ],
            "Food": [
                ITEM_RAW_MEAT, ITEM_RAW_CHICKEN, ITEM_RAW_PORK
            ]
        }
        
        self.slot_size = 0.12
        self.slot_spacing = 0.02
        
    def create(self):
        if self.frame: return
        
        # Main background
        self.frame = DirectFrame(
            frameColor=(0, 0, 0, 0.5),
            frameSize=(-2, 2, -2, 2),
            parent=self.app.aspect2d,
            state=DGG.NORMAL,
        )
        self.frame.hide()
        
        # Window
        self.window = DirectFrame(
            frameColor=(0.2, 0.2, 0.2, 0.95),
            frameSize=(-1.2, 1.2, -0.8, 0.8),
            parent=self.frame,
            pos=(0, 0, 0)
        )
        
        # Title
        DirectLabel(
            text="Creative Inventory",
            scale=0.06,
            pos=(0, 0, 0.7),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.window
        )
        
        # Tabs
        tab_y = 0.6
        tab_x_start = -0.8
        tab_width = 0.3
        
        for i, cat in enumerate(self.categories.keys()):
            btn = DirectButton(
                text=cat,
                scale=0.05,
                pos=(tab_x_start + i * (tab_width + 0.05), 0, tab_y),
                frameSize=(-2.5, 2.5, -0.5, 1),
                command=self._set_tab,
                extraArgs=[cat],
                parent=self.window,
                text_fg=(1, 1, 1, 1),
                frameColor=(0.3, 0.3, 0.3, 1)
            )
            self.tabs.append({'name': cat, 'btn': btn})
            
        # Scrollable Item Grid
        self.item_grid = DirectScrolledFrame(
            frameSize=(-1.1, 1.1, -0.6, 0.5),
            canvasSize=(-1.0, 1.0, -2, 0), # Dynamic
            scrollBarWidth=0.04,
            frameColor=(0.15, 0.15, 0.15, 1),
            pos=(0, 0, -0.1),
            parent=self.window
        )
        
        # Tooltip
        self.tooltip = DirectLabel(
            text="",
            scale=0.04,
            frameColor=(0.1, 0.1, 0.1, 0.9),
            text_fg=(1, 1, 1, 1),
            parent=self.frame,
            sortOrder=1000
        )
        self.tooltip.hide()
        
        # Mouse task
        self.app.taskMgr.add(self._update_mouse_task, "creative_mouse_update")
        
    def _set_tab(self, tab_name):
        self.current_tab = tab_name
        
        # Update tab visuals
        for tab in self.tabs:
            if tab['name'] == tab_name:
                tab['btn']['frameColor'] = (0.5, 0.5, 0.5, 1)
            else:
                tab['btn']['frameColor'] = (0.3, 0.3, 0.3, 1)
                
        self._populate_grid()
        
    def _populate_grid(self):
        # Clear existing
        for btn in self.item_buttons:
            btn.destroy()
        self.item_buttons = []
        
        items = self.categories[self.current_tab]
        
        cols = 8
        start_x = -0.9
        start_y = -0.1
        
        for i, item_id in enumerate(items):
            row = i // cols
            col = i % cols
            
            x = start_x + col * (self.slot_size + self.slot_spacing * 3)
            y = start_y - row * (self.slot_size + self.slot_spacing * 3)
            
            # Create button
            btn = DirectButton(
                frameColor=(0.4, 0.4, 0.4, 1),
                frameSize=(-self.slot_size/2, self.slot_size/2, -self.slot_size/2, self.slot_size/2),
                pos=(x, 0, y),
                parent=self.item_grid.getCanvas(),
                command=self._on_item_click,
                extraArgs=[item_id]
            )
            
            # Icon
            from direct.gui.OnscreenImage import OnscreenImage
            texture = self._get_item_texture(item_id)
            if texture:
                img = OnscreenImage(
                    image=texture,
                    scale=(self.slot_size/2.5, 1, self.slot_size/2.5),
                    parent=btn
                )
                img.setTransparency(TransparencyAttrib.MAlpha)
            
            # Hover events
            btn.bind(DGG.WITHIN, self._on_hover, [item_id, btn])
            btn.bind(DGG.WITHOUT, self._on_exit, [item_id, btn])
            
            self.item_buttons.append(btn)
            
        # Update canvas size
        rows = (len(items) - 1) // cols + 1
        height = rows * (self.slot_size + self.slot_spacing * 3) + 0.2
        self.item_grid['canvasSize'] = (-1.0, 1.0, -height, 0.1)

    def _get_item_texture(self, block_id):
        # Reuse logic from InventoryUI or refactor to shared util
        # For now, quick copy-paste or import?
        # Let's try to import InventoryUI's method if possible, or just duplicate for speed and safety
        # Duplicating the texture logic for now to avoid circular imports or refactoring risks
        from voxel.chunk import (
            BLOCK_STICKS, BLOCK_PICKAXE_WOOD, BLOCK_PICKAXE_STONE, BLOCK_PICKAXE_IRON,
            BLOCK_AXE_WOOD, BLOCK_AXE_STONE, BLOCK_AXE_IRON,
            BLOCK_SHOVEL_WOOD, BLOCK_SHOVEL_STONE, BLOCK_SHOVEL_IRON,
            BLOCK_SWORD_WOOD, BLOCK_SWORD_STONE, BLOCK_SWORD_IRON
        )
        from voxel.mob_system import ITEM_RAW_MEAT, ITEM_RAW_CHICKEN, ITEM_RAW_PORK
        from voxel.texture_manager import BLOCK_TEXTURES
        
        tool_map = {
            BLOCK_STICKS: ('items', 'stick'),
            BLOCK_PICKAXE_WOOD: ('items', 'pickaxe_wood'),
            BLOCK_PICKAXE_STONE: ('items', 'pickaxe_stone'),
            BLOCK_PICKAXE_IRON: ('items', 'pickaxe_iron'),
            BLOCK_AXE_WOOD: ('items', 'axe_wood'),
            BLOCK_AXE_STONE: ('items', 'axe_stone'),
            BLOCK_AXE_IRON: ('items', 'axe_iron'),
            BLOCK_SHOVEL_WOOD: ('items', 'shovel_wood'),
            BLOCK_SHOVEL_STONE: ('items', 'shovel_stone'),
            BLOCK_SHOVEL_IRON: ('items', 'shovel_iron'),
            BLOCK_SWORD_WOOD: ('items', 'sword_wood'),
            BLOCK_SWORD_STONE: ('items', 'sword_stone'),
            BLOCK_SWORD_IRON: ('items', 'sword_iron'),
        }
        
        meat_map = {
            ITEM_RAW_MEAT: ('meat', 'raw_meat'),
            ITEM_RAW_CHICKEN: ('meat', 'raw_chicken'),
            ITEM_RAW_PORK: ('meat', 'raw_pork'),
        }
        
        if block_id in tool_map:
            category, name = tool_map[block_id]
            return self.texture_manager.load_texture(category, f'{name}.png')
        
        if block_id in meat_map:
            category, name = meat_map[block_id]
            return self.texture_manager.load_texture(category, f'{name}.png')
        
        if block_id in BLOCK_TEXTURES:
            texture_name = BLOCK_TEXTURES[block_id]
            return self.texture_manager.get_block_texture(texture_name)
            
        return None

    def _on_item_click(self, item_id):
        # Add stack of 64 to hotbar
        # Find empty slot or same item slot
        
        # Check hotbar first
        for i in range(len(self.app.hotbar)):
            slot = self.app.hotbar[i]
            if slot and slot['block'] == item_id:
                slot['count'] = 64 # Refill to 64
                self.app._update_hotbar_ui()
                return
        
        # Find empty hotbar slot
        for i in range(len(self.app.hotbar)):
            if self.app.hotbar[i] is None:
                self.app.hotbar[i] = {'block': item_id, 'count': 64}
                self.app._update_hotbar_ui()
                return
                
        # If hotbar full, replace selected slot?
        idx = self.app.selected_hotbar_slot
        self.app.hotbar[idx] = {'block': item_id, 'count': 64}
        self.app._update_hotbar_ui()

    def open(self):
        if not self.frame:
            self.create()
            
        if self.texture_manager is None:
            from voxel.chunk import get_texture_manager
            self.texture_manager = get_texture_manager()
            
        self.is_open = True
        self.frame.show()
        self._set_tab(self.current_tab)
        
        self.app.mouse_locked = False
        self.app._apply_mouse_lock()
        
        self.accept("e", self.close)
        self.accept("escape", self.close)

    def close(self):
        if not self.is_open: return
        
        self.is_open = False
        self.frame.hide()
        self.tooltip.hide()
        
        self.app.mouse_locked = True
        self.app._apply_mouse_lock()
        
        self.ignore("e")
        self.ignore("escape")

    def _update_mouse_task(self, task):
        if not self.is_open: return Task.cont
        
        if self.app.mouseWatcherNode.hasMouse():
            mpos = self.app.mouseWatcherNode.getMouse()
            x = mpos.getX() * self.app.getAspectRatio()
            y = mpos.getY()
            
            if self.tooltip and not self.tooltip.isHidden():
                self.tooltip.setPos(x + 0.05, 0, y - 0.05)
                
        return Task.cont

    def _on_hover(self, item_id, btn, event=None):
        # Show tooltip
        # Need name mapping
        from voxel.inventory_ui import InventoryUI
        # Hacky way to get name, or duplicate logic
        # Let's just use a simple map or stringify for now
        self.tooltip['text'] = str(item_id) # Placeholder, ideally use name map
        self.tooltip.show()

    def _on_exit(self, item_id, btn, event=None):
        self.tooltip.hide()
