from direct.gui.DirectGui import DirectFrame, DirectLabel, DirectButton, DGG, OnscreenImage
from direct.showbase.DirectObject import DirectObject
from direct.task import Task
from panda3d.core import TextNode, TransparencyAttrib, Filename, CardMaker
from voxel import settings
from voxel.crafting import crafting_system, BLOCK_CRAFTING_TABLE
import os

class InventoryUI(DirectObject):
    def __init__(self, app):
        self.app = app
        
        # Texture manager will be initialized when inventory is opened
        self.texture_manager = None
        
        # OnscreenImage instances for icons (will be stored in slots)
        self.icon_images = {}  # Maps (slot_type, index) to OnscreenImage
        self.cursor_image = None  # OnscreenImage for cursor
        
        # Inventory data
        # 27 main inventory slots + 9 hotbar slots
        # We will reference app.hotbar for the hotbar slots
        # We need to create app.inventory for the 27 slots
        if not hasattr(self.app, 'inventory'):
            self.app.inventory = [None] * 27
            
        # Crafting grid (2x2)
        self.crafting_grid = [None] * 4
        self.crafting_output = None
        
        # Drag and drop state
        self.cursor_item = None # {'block': id, 'count': int}
        self.cursor_icon = None
        self.is_dragging = False
        
        # UI Elements
        self.frame = None
        self.slots = [] # List of dicts {frame, icon, count_label, type, index}
        self.tooltip = None
        self.is_open = False
        self.hovered_slot = None # tuple (type, index)
        
        # Controller Navigation
        self.selected_slot_index = 0 # Index in self.slots
        # We need to know structure of self.slots:
        # 0-3: Crafting
        # 4: Output
        # 5-31: Inventory (27)
        # 32-40: Hotbar (9)
        # Total 41 slots.
        self.nav_active = False
        
        # Slot configuration
        self.slot_size = 0.12
        self.slot_spacing = 0.01
        
    def create(self):
        """Create the inventory UI elements."""
        # Reset slots
        self.slots = []
        
        if self.frame:
            return

        # Main frame (covers whole screen for modal feeling, but transparent)
        self.frame = DirectFrame(
            frameColor=(0, 0, 0, 0.5),
            frameSize=(-2, 2, -2, 2),
            parent=self.app.aspect2d,
            state=DGG.NORMAL, # Blocks clicks behind it
        )
        self.frame.hide()
        
        # Inventory Window Background
        window_width = 9 * (self.slot_size + self.slot_spacing) + 0.1
        window_height = 1.2
        
        self.window = DirectFrame(
            frameColor=(0.2, 0.2, 0.2, 0.95),
            frameSize=(-window_width/2, window_width/2, -window_height/2, window_height/2),
            parent=self.frame,
            pos=(0, 0, 0)
        )
        
        # Title
        DirectLabel(
            text="Crafting",
            scale=0.05,
            pos=(-window_width/2 + 0.1, 0, window_height/2 - 0.08),
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            parent=self.window
        )
        
        # --- 2x2 Crafting Grid ---
        crafting_start_x = -0.2
        crafting_start_y = 0.35
        
        DirectLabel(
            text="Crafting",
            scale=0.04,
            pos=(crafting_start_x, 0, crafting_start_y + 0.15),
            text_fg=(0.8, 0.8, 0.8, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.window
        )
        
        for i in range(4):
            row = i // 2
            col = i % 2
            x = crafting_start_x + col * (self.slot_size + self.slot_spacing)
            y = crafting_start_y - row * (self.slot_size + self.slot_spacing)
            self._create_slot(x, y, "crafting", i)

        # Arrow
        DirectLabel(
            text="->",
            scale=0.08,
            pos=(crafting_start_x + 2.5 * (self.slot_size + self.slot_spacing), 0, crafting_start_y - 0.5 * (self.slot_size + self.slot_spacing)),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.window
        )

        # Output Slot
        output_x = crafting_start_x + 3.5 * (self.slot_size + self.slot_spacing)
        output_y = crafting_start_y - 0.5 * (self.slot_size + self.slot_spacing)
        self._create_slot(output_x, output_y, "output", 0)
        
        # --- Main Inventory (3 rows of 9) ---
        inv_start_x = -4 * (self.slot_size + self.slot_spacing)
        inv_start_y = -0.05
        
        for i in range(27):
            row = i // 9
            col = i % 9
            x = inv_start_x + col * (self.slot_size + self.slot_spacing)
            y = inv_start_y - row * (self.slot_size + self.slot_spacing)
            self._create_slot(x, y, "inventory", i)
            
        # --- Hotbar (1 row of 9) ---
        hotbar_start_y = inv_start_y - 3 * (self.slot_size + self.slot_spacing) - 0.05
        
        for i in range(9):
            x = inv_start_x + i * (self.slot_size + self.slot_spacing)
            y = hotbar_start_y
            self._create_slot(x, y, "hotbar", i)

        # Cursor Item (Icon that follows mouse)
        self.cursor_icon = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(-self.slot_size/2.5, self.slot_size/2.5, -self.slot_size/2.5, self.slot_size/2.5),
            parent=self.frame, # Parent to main frame so it's on top
            state=DGG.DISABLED
        )
        self.cursor_count = DirectLabel(
            text="",
            scale=0.04,
            pos=(self.slot_size/3, 0, -self.slot_size/3),
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.cursor_icon,
            text_align=TextNode.ARight
        )
        self.cursor_icon.hide()
        
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
        
        # Mouse update task for drag and tooltip
        self.app.taskMgr.add(self._update_mouse_task, "inventory_mouse_update")

    def _create_slot(self, x, y, slot_type, index):
        """Create a single inventory slot."""
        
        # Frame for collision/clicks
        frame = DirectButton(
            frameColor=(0.4, 0.4, 0.4, 1),
            frameSize=(-self.slot_size/2, self.slot_size/2, -self.slot_size/2, self.slot_size/2),
            pos=(x, 0, y),
            parent=self.window,
            relief=DGG.FLAT,
            command=self._on_slot_click,
            extraArgs=[slot_type, index]
        )
        # Right click handling
        frame.bind(DGG.B3PRESS, self._on_slot_right_click, [slot_type, index])
        # Hover events
        frame.bind(DGG.WITHIN, self._on_slot_hover, [slot_type, index])
        frame.bind(DGG.WITHOUT, self._on_slot_exit, [slot_type, index])
        
        # Inner background (darker)
        DirectFrame(
            frameColor=(0.2, 0.2, 0.2, 1),
            frameSize=(-self.slot_size/2 + 0.005, self.slot_size/2 - 0.005, -self.slot_size/2 + 0.005, self.slot_size/2 - 0.005),
            parent=frame,
            state=DGG.DISABLED
        )
        
        # Icon
        icon = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(-self.slot_size/2.5, self.slot_size/2.5, -self.slot_size/2.5, self.slot_size/2.5),
            parent=frame,
            state=DGG.DISABLED
        )
        icon.setTransparency(TransparencyAttrib.MAlpha)
        icon.hide()
        
        # Count Label
        count_label = DirectLabel(
            text="",
            scale=0.035,
            pos=(self.slot_size/2 - 0.01, 0, -self.slot_size/2 + 0.01),
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 1),
            frameColor=(0, 0, 0, 0),
            parent=frame,
            text_align=TextNode.ARight
        )
        
        self.slots.append({
            "frame": frame,
            "icon": icon,
            "count_label": count_label,
            "type": slot_type,
            "index": index,
            "x": x,
            "y": y
        })

    def toggle(self):
        if self.is_open:
            self.close()
        else:
            self.open()
            
    def open(self):
        if not self.frame:
            self.create()
        
        # Initialize texture manager if not already done
        if self.texture_manager is None:
            from voxel.chunk import get_texture_manager
            self.texture_manager = get_texture_manager()
            
        self.is_open = True
        self.frame.show()
        self.refresh_ui()
        
        self._register_events()
        self.selected_slot_index = 5 # Start at first inventory slot
        self.nav_active = True
        self._update_selection()
        
        # Unlock mouse
        self.app.mouse_locked = False
        self.app._apply_mouse_lock()
        
        # Hide game hotbar
        if self.app.hotbar_ui:
            self.app.hotbar_ui.hide()
        if self.app.crosshair:
            self.app.crosshair.hide()
        # Also close legacy crafting menu if open
        from voxel.crafting import crafting_menu
        if crafting_menu and crafting_menu.is_open:
            crafting_menu.hide_menu()

    def close(self):
        if not self.is_open:
            return
            
        self.is_open = False
        self.frame.hide()
        
        self._ignore_events()
        self.nav_active = False
        
        # Functionality: Drop cursor item or return to inventory?
        # For simplicity, return to inventory or drop if full.
        if self.cursor_item:
            self._distribute_item(self.cursor_item)
            self.cursor_item = None
            self._update_cursor_renderer()
            
        # Clear crafting grid (return items to inventory)
        for i in range(4):
            if self.crafting_grid[i]:
                self._distribute_item(self.crafting_grid[i])
                self.crafting_grid[i] = None
        self.crafting_output = None
        
        # Lock mouse
        self.app.mouse_locked = True
        self.app._apply_mouse_lock()
        
        # Show game hotbar
        if self.app.hotbar_ui:
            self.app.hotbar_ui.show()
            self.app._update_hotbar_ui() # Ensure sync
        if self.app.crosshair:
            self.app.crosshair.show()

    def _register_events(self):
        self.accept("control-up", self._on_nav, ["up"])
        self.accept("control-down", self._on_nav, ["down"])
        self.accept("control-left", self._on_nav, ["left"])
        self.accept("control-right", self._on_nav, ["right"])
        self.accept("control-select", self._on_select)
        self.accept("control-back", self.close) # B closes inventory
        self.accept("control-pause", self.close) # Also Start closes inventory

    def _ignore_events(self):
        self.ignore("control-up")
        self.ignore("control-down")
        self.ignore("control-left")
        self.ignore("control-right")
        self.ignore("control-select")
        self.ignore("control-back")
        self.ignore("control-pause")

    def _on_nav(self, direction):
        if not self.is_open: return
        
        # Slot layout analysis:
        # 0-3: Crafting (2x2)
        # 4: Output
        # 5-13: Inv Row 1
        # 14-22: Inv Row 2
        # 23-31: Inv Row 3
        # 32-40: Hotbar
        
        current = self.selected_slot_index
        
        if direction == "up":
            if 32 <= current <= 40: # From Hotbar to Inv Row 3
                self.selected_slot_index = current - 9
            elif 14 <= current <= 31: # Inv Body
                self.selected_slot_index = current - 9
            elif 5 <= current <= 13: # Inv Row 1 to Crafting/Output
                # Center aligns with crafting? Not really.
                # Left side -> Crafting, Right side -> Output
                if current <= 8: self.selected_slot_index = 2 # Crafting bottom left? 2 is row 1, col 0
                else: self.selected_slot_index = 4 # Output
            elif 0 <= current <= 3: # Crafting
                if current >= 2: self.selected_slot_index -= 2 # Up in 2x2
        elif direction == "down":
            if 0 <= current <= 1: # Crafting Top
                self.selected_slot_index += 2
            elif 2 <= current <= 3: # Crafting Bottom
                # To Inv Row 1
                self.selected_slot_index = 5 # Approx start
            elif current == 4: # Output
                self.selected_slot_index = 10 # Approx middle
            elif 5 <= current <= 22: # Inv Body
                self.selected_slot_index = current + 9
            elif 23 <= current <= 31: # Inv Row 3 to Hotbar
                self.selected_slot_index = current + 9
        elif direction == "left":
            # Simple decrement with boundary checks per section
            if current == 4: # Output
                 self.selected_slot_index = 1 # Crafting top right
            elif current in [0, 2]: # Crafting Left
                 pass # Can't go left
            elif current in [1, 3]: # Crafting Right
                 self.selected_slot_index -= 1
            elif current in [5, 14, 23, 32]: # Left edge of grid
                 pass
            else:
                 self.selected_slot_index -= 1
        elif direction == "right":
            if current in [0, 2]: # Crafting Left
                 self.selected_slot_index += 1
            elif current in [1, 3]: # Crafting Right
                 self.selected_slot_index = 4 # Output
            elif current in [13, 22, 31, 40]: # Right edge of grid
                 pass
            elif current == 4: # Output
                 pass
            else:
                 self.selected_slot_index += 1
                 
        # Clamp safety
        if self.selected_slot_index < 0: self.selected_slot_index = 0
        if self.selected_slot_index >= len(self.slots): self.selected_slot_index = len(self.slots) - 1
        
        self._update_selection()

    def _update_selection(self):
        # Highlight current slot
        for i, slot in enumerate(self.slots):
            if i == self.selected_slot_index:
                slot['frame']['frameColor'] = (0.6, 0.6, 0.6, 1)
                # Update hovered slot logic so tooltip shows up
                self._on_slot_hover(slot['type'], slot['index'])
            else:
                slot['frame']['frameColor'] = (0.4, 0.4, 0.4, 1)
    
    def _on_select(self):
        print("[InventoryUI] Received control-select") # Debug
        if not self.is_open: return
        slot = self.slots[self.selected_slot_index]
        self._on_slot_click(slot['type'], slot['index'])

    def _distribute_item(self, item_data):
        """Try to add item back to inventory/hotbar, else drop."""
        # Logic similar to collecting items
        # Try hotbar
        for i in range(len(self.app.hotbar)):
            slot = self.app.hotbar[i]
            if slot and slot['block'] == item_data['block']:
                slot['count'] += item_data['count']
                return
        for i in range(len(self.app.inventory)):
            slot = self.app.inventory[i]
            if slot and slot['block'] == item_data['block']:
                slot['count'] += item_data['count']
                return
                
        # Try empty slots
        for i in range(len(self.app.hotbar)):
            if self.app.hotbar[i] is None:
                self.app.hotbar[i] = item_data
                return
        for i in range(len(self.app.inventory)):
            if self.app.inventory[i] is None:
                self.app.inventory[i] = item_data
                return
        
        # If here, full. Drop item? (Not implemented yet, just vanishes :P)
        print("Inventory full, item lost: ", item_data)

    def _get_slot_data(self, slot_type, index):
        if slot_type == "inventory":
            return self.app.inventory[index]
        elif slot_type == "hotbar":
            return self.app.hotbar[index]
        elif slot_type == "crafting":
            return self.crafting_grid[index]
        elif slot_type == "output":
            return self.crafting_output
        return None

    def _set_slot_data(self, slot_type, index, data):
        if slot_type == "inventory":
            self.app.inventory[index] = data
        elif slot_type == "hotbar":
            self.app.hotbar[index] = data
        elif slot_type == "crafting":
            self.crafting_grid[index] = data
            self._check_crafting() # Update output
        elif slot_type == "output":
            self.crafting_output = data

    def refresh_ui(self):
        """Update all slot visuals."""
        for slot in self.slots:
            data = self._get_slot_data(slot['type'], slot['index'])
            self._update_slot_visual(slot, data)
        
        self._update_cursor_renderer()

    def _get_item_texture(self, block_id):
        """Get the texture for a given block/item ID."""
        from voxel.chunk import (
            BLOCK_STICKS, BLOCK_PICKAXE_WOOD, BLOCK_PICKAXE_STONE, BLOCK_PICKAXE_IRON,
            BLOCK_AXE_WOOD, BLOCK_AXE_STONE, BLOCK_AXE_IRON,
            BLOCK_SHOVEL_WOOD, BLOCK_SHOVEL_STONE, BLOCK_SHOVEL_IRON,
            BLOCK_SWORD_WOOD, BLOCK_SWORD_STONE, BLOCK_SWORD_IRON
        )
        from voxel.mob_system import ITEM_RAW_MEAT, ITEM_RAW_CHICKEN, ITEM_RAW_PORK
        from voxel.texture_manager import BLOCK_TEXTURES
        
        # Handle tools (items)
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
        
        # Handle meat items
        meat_map = {
            ITEM_RAW_MEAT: ('meat', 'raw_meat'),
            ITEM_RAW_CHICKEN: ('meat', 'raw_chicken'),
            ITEM_RAW_PORK: ('meat', 'raw_pork'),
        }
        
        # Check if it's a tool
        if block_id in tool_map:
            category, name = tool_map[block_id]
            return self.texture_manager.load_texture(category, f'{name}.png')
        
        # Check if it's meat
        if block_id in meat_map:
            category, name = meat_map[block_id]
            return self.texture_manager.load_texture(category, f'{name}.png')
        
        # Check if it's a block
        if block_id in BLOCK_TEXTURES:
            texture_name = BLOCK_TEXTURES[block_id]
            return self.texture_manager.get_block_texture(texture_name)
        
        return None
    
    def _update_slot_visual(self, slot_ui, data):
        # Get slot key for tracking image
        slot_key = (slot_ui['type'], slot_ui['index'])
        
        if data:
            # Get texture for this item
            texture = self._get_item_texture(data['block'])
            
            if texture:
                # Remove old image if exists
                if slot_key in self.icon_images:
                    self.icon_images[slot_key].destroy()
                
                # Change icon frame to transparent
                slot_ui['icon']['frameColor'] = (0, 0, 0, 0)
                slot_ui['icon'].show()
                
                # Create new OnscreenImage with texture
                img = OnscreenImage(
                    image=texture,
                    scale=(self.slot_size/2.5, 1, self.slot_size/2.5),
                    parent=slot_ui['icon']
                )
                img.setTransparency(TransparencyAttrib.MAlpha)
                self.icon_images[slot_key] = img
            
            # Update Count
            if data['count'] > 1:
                slot_ui['count_label']['text'] = str(data['count'])
            else:
                slot_ui['count_label']['text'] = ""
        else:
            # Hide icon by removing image
            if slot_key in self.icon_images:
                self.icon_images[slot_key].destroy()
                del self.icon_images[slot_key]
            slot_ui['icon'].hide()
            slot_ui['count_label']['text'] = ""
            
    def _update_cursor_renderer(self):
        # Clean up old cursor image
        if self.cursor_image:
            self.cursor_image.destroy()
            self.cursor_image = None
        
        if self.cursor_item:
            self.cursor_icon.show()
            self.cursor_icon['frameColor'] = (0, 0, 0, 0)  # Transparent
            
            # Get texture for cursor item
            texture = self._get_item_texture(self.cursor_item['block'])
            
            if texture:
                # Create OnscreenImage with texture
                self.cursor_image = OnscreenImage(
                    image=texture,
                    scale=(self.slot_size/2.5, 1, self.slot_size/2.5),
                    parent=self.cursor_icon
                )
                self.cursor_image.setTransparency(TransparencyAttrib.MAlpha)
            
            if self.cursor_item['count'] > 1:
                self.cursor_count['text'] = str(self.cursor_item['count'])
            else:
                self.cursor_count['text'] = ""
                
             # Position cursor at selected slot if using controller (optional visual aid)
             # But cursor_icon follows mouse in _update_mouse_task.
             # If using controller, we might want to force it to selected slot position?
             # Let's just let the selected slot highlight be the indicator, and the dragged item "float"
             # or stick to the selected slot.
             # For simplicity, if nav_active, force cursor icon to selected slot position.
             
            if self.nav_active:
                slot = self.slots[self.selected_slot_index]
                self.cursor_icon.setPos(slot['x'], 0, slot['y'])
                
        else:
            self.cursor_icon.hide()
            
    def _on_slot_click(self, slot_type, index):
        """Handle left click on slot."""
        clicked_data = self._get_slot_data(slot_type, index)
        
        if slot_type == "output":
            # Crafting Result Logic
            if self.cursor_item is None and clicked_data is not None:
                # Pick up crafted item
                self.cursor_item = clicked_data
                self._set_slot_data("output", 0, None)
                self._consume_crafting_ingredients()
            elif self.cursor_item is not None and clicked_data is not None:
                # Stack crafted item if same type
                if self.cursor_item['block'] == clicked_data['block']:
                    self.cursor_item['count'] += clicked_data['count']
                    self._set_slot_data("output", 0, None)
                    self._consume_crafting_ingredients()
            self.refresh_ui()
            return

        # Normal Slot Logic
        if self.cursor_item is None:
            if clicked_data is not None:
                # Pick up
                self.cursor_item = clicked_data
                self._set_slot_data(slot_type, index, None)
        else:
            if clicked_data is None:
                # Place down
                self._set_slot_data(slot_type, index, self.cursor_item)
                self.cursor_item = None
            else:
                # Swap or Stack
                if self.cursor_item['block'] == clicked_data['block']:
                    # Stack
                    clicked_data['count'] += self.cursor_item['count']
                    self.cursor_item = None
                else:
                    # Swap
                    temp = clicked_data
                    self._set_slot_data(slot_type, index, self.cursor_item)
                    self.cursor_item = temp
        
        self.refresh_ui()

    def _on_slot_right_click(self, slot_type, index, event=None):
        """Handle right click on slot."""
        clicked_data = self._get_slot_data(slot_type, index)
        
        if slot_type == "output":
            self._on_slot_click(slot_type, index) # Just treat as normal click for output for now
            return
            
        if self.cursor_item is None:
            if clicked_data is not None:
                # Split stack (take half)
                count = clicked_data['count']
                take = (count + 1) // 2
                leave = count - take
                
                new_cursor = {'block': clicked_data['block'], 'count': take}
                self.cursor_item = new_cursor
                
                if leave > 0:
                    clicked_data['count'] = leave
                else:
                    self._set_slot_data(slot_type, index, None)
        else:
            # Place one item
            if clicked_data is None:
                # Place 1 into empty slot
                one_item = {'block': self.cursor_item['block'], 'count': 1}
                self._set_slot_data(slot_type, index, one_item)
                
                self.cursor_item['count'] -= 1
                if self.cursor_item['count'] <= 0:
                    self.cursor_item = None
            elif clicked_data['block'] == self.cursor_item['block']:
                # Add 1 to existing stack
                clicked_data['count'] += 1
                
                self.cursor_item['count'] -= 1
                if self.cursor_item['count'] <= 0:
                    self.cursor_item = None
        
        self.refresh_ui()

    def _consume_crafting_ingredients(self):
        """Reduce count of items in crafting grid."""
        for i in range(4):
            slot = self.crafting_grid[i]
            if slot:
                slot['count'] -= 1
                if slot['count'] <= 0:
                    self.crafting_grid[i] = None
        
        self._check_crafting() # Re-check for next valid recipe

    def _check_crafting(self):
        """Check if current grid matches a recipe (2x2 inventory crafting)."""
        # Gather ingredients from 2x2 grid
        ingredients = {}
        non_empty_slots = 0
        for slot in self.crafting_grid:
            if slot:
                bid = slot['block']
                ingredients[bid] = ingredients.get(bid, 0) + 1
                non_empty_slots += 1
        
        if non_empty_slots == 0:
            self.crafting_output = None
            return

        # Check against 2x2 recipes only (use the crafting system's 2x2 recipe list)
        match = None
        
        # Iterate 2x2 recipes (requires_3x3 = False)
        for recipe in crafting_system.recipes_2x2:
            # Check ingredients
            req_ingredients = recipe['ingredients']
            
            # Check if counts match exactly
            matches = True
            
            # Check if we have extras
            for bid, count in ingredients.items():
                if req_ingredients.get(bid, 0) != count:
                    matches = False
                    break
            
            # Check if we are missing any
            for bid, count in req_ingredients.items():
                if ingredients.get(bid, 0) != count:
                    matches = False
                    break
            
            if matches:
                match = recipe
                break
        
        if match:
            out = match['output']
            self.crafting_output = {'block': out['block'], 'count': out['count']}
        else:
            self.crafting_output = None

    def _update_mouse_task(self, task):
        if not self.is_open:
            return Task.cont
            
        if self.app.mouseWatcherNode.hasMouse():
            mpos = self.app.mouseWatcherNode.getMouse()
            # Aspect ratio correction
            x = mpos.getX() * self.app.getAspectRatio()
            y = mpos.getY()
            
            # If nav is active, don't update from mouse unless mouse moved?
            # Or let mouse override nav
            if not self.nav_active:
                # Update cursor icon position
                if self.cursor_icon:
                    self.cursor_icon.setPos(x, 0, y)
                
                # Update tooltip position
                if self.tooltip and not self.tooltip.isHidden():
                    self.tooltip.setPos(x + 0.05, 0, y - 0.05)
            
        return Task.cont
    
    def _on_slot_hover(self, slot_type, index, event=None):
        self.hovered_slot = (slot_type, index)
        data = self._get_slot_data(slot_type, index)
        
        if data:
            block_id = data['block']
            # Get block name logic (copied/adapted fromcrafting menu)
            name = self._get_block_name(block_id)
            self.tooltip['text'] = name
            self.tooltip.show()
            
            # Update tooltip position to slot position if nav active
            if self.nav_active:
                # finding slot ui
                slot = next((s for s in self.slots if s['type'] == slot_type and s['index'] == index), None)
                if slot:
                    self.tooltip.setPos(slot['x'] + 0.05, 0, slot['y'] - 0.05)
        else:
            self.tooltip.hide()
            
    def _on_slot_exit(self, slot_type, index, event=None):
        if self.hovered_slot == (slot_type, index):
            self.hovered_slot = None
            self.tooltip.hide()

    def _get_block_name(self, block_id):
        # Importing here to avoid circular dependencies if any, or just rely on predefined dict
        # For now basic mapping
        from voxel.chunk import (
            BLOCK_GRASS, BLOCK_DIRT, BLOCK_STONE, BLOCK_SAND, BLOCK_WOOD,
            BLOCK_LEAVES, BLOCK_COBBLESTONE, BLOCK_BRICK, BLOCK_BEDROCK,
            BLOCK_SANDSTONE, BLOCK_PLANKS, BLOCK_STICKS,
            BLOCK_PICKAXE_WOOD, BLOCK_PICKAXE_STONE, BLOCK_AXE_WOOD,
            BLOCK_AXE_STONE, BLOCK_SHOVEL_WOOD, BLOCK_SHOVEL_STONE,
            BLOCK_SWORD_WOOD, BLOCK_SWORD_STONE, BLOCK_CRAFTING_TABLE,
            BLOCK_FURNACE, BLOCK_CHEST,
            BLOCK_JUNGLE_LOG, BLOCK_BIRCH_LOG, BLOCK_JUNGLE_PLANKS, BLOCK_BIRCH_PLANKS,
            BLOCK_IRON_INGOT
        )
        from voxel.mob_system import ITEM_RAW_MEAT, ITEM_RAW_CHICKEN, ITEM_RAW_PORK
        
        names = {
            BLOCK_GRASS: "Grass Block",
            BLOCK_DIRT: "Dirt",
            BLOCK_STONE: "Stone",
            BLOCK_SAND: "Sand",
            BLOCK_WOOD: "Oak Log",
            BLOCK_JUNGLE_LOG: "Jungle Log",
            BLOCK_BIRCH_LOG: "Birch Log",
            BLOCK_LEAVES: "Leaves",
            BLOCK_COBBLESTONE: "Cobblestone",
            BLOCK_BRICK: "Brick",
            BLOCK_BEDROCK: "Bedrock",
            BLOCK_SANDSTONE: "Sandstone",
            BLOCK_PLANKS: "Oak Planks",
            BLOCK_JUNGLE_PLANKS: "Jungle Planks",
            BLOCK_BIRCH_PLANKS: "Birch Planks",
            BLOCK_STICKS: "Sticks",
            BLOCK_PICKAXE_WOOD: "Wooden Pickaxe",
            BLOCK_PICKAXE_STONE: "Stone Pickaxe",
            BLOCK_AXE_WOOD: "Wooden Axe",
            BLOCK_AXE_STONE: "Stone Axe",
            BLOCK_SHOVEL_WOOD: "Wooden Shovel",
            BLOCK_SHOVEL_STONE: "Stone Shovel",
            BLOCK_SWORD_WOOD: "Wooden Sword",
            BLOCK_SWORD_STONE: "Stone Sword",
            BLOCK_CRAFTING_TABLE: "Crafting Table",
            BLOCK_FURNACE: "Furnace",
            BLOCK_CHEST: "Chest",
            BLOCK_IRON_INGOT: "Iron Ingot",
            ITEM_RAW_MEAT: "Raw Meat",
            ITEM_RAW_CHICKEN: "Raw Chicken",
            ITEM_RAW_PORK: "Raw Pork",
        }
        return names.get(block_id, f"Unknown Item ({block_id})")


class CraftingTableUI(DirectObject):
    """UI for 3x3 crafting table."""
    
    def __init__(self, app):
        self.app = app
        
        # Texture manager will be initialized when crafting table is opened
        self.texture_manager = None
        
        # OnscreenImage instances for icons
        self.icon_images = {}  # Maps (slot_type, index) to OnscreenImage
        self.cursor_image = None  # OnscreenImage for cursor
        
        # Crafting grid (3x3)
        self.crafting_grid = [None] * 9
        self.crafting_output = None
        
        # Drag and drop state
        self.cursor_item = None
        self.cursor_icon = None
        
        # UI Elements
        self.frame = None
        self.slots = []
        self.tooltip = None
        self.is_open = False
        self.hovered_slot = None
        
        # Controller Navigation
        self.selected_slot_index = 0 
        # Slots order:
        # 0-8: Crafting (3x3)
        # 9: Output
        # 10-36: Inventory
        # 37-45: Hotbar
        self.nav_active = False
        
        # Slot configuration
        self.slot_size = 0.12
        self.slot_spacing = 0.01
    
    def create(self):
        """Create the crafting table UI elements."""
        self.slots = []
        if self.frame:
            return
        
        # Main frame
        self.frame = DirectFrame(
            frameColor=(0, 0, 0, 0.5),
            frameSize=(-2, 2, -2, 2),
            parent=self.app.aspect2d,
            state=DGG.NORMAL,
        )
        self.frame.hide()
        
        # Window Background
        window_width = 9 * (self.slot_size + self.slot_spacing) + 0.1
        window_height = 1.2
        
        self.window = DirectFrame(
            frameColor=(0.2, 0.2, 0.2, 0.95),
            frameSize=(-window_width/2, window_width/2, -window_height/2, window_height/2),
            parent=self.frame,
            pos=(0, 0, 0)
        )
        
        # Title
        DirectLabel(
            text="Crafting Table",
            scale=0.05,
            pos=(-window_width/2 + 0.15, 0, window_height/2 - 0.08),
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            parent=self.window
        )
        
        # --- 3x3 Crafting Grid ---
        crafting_start_x = -0.3
        crafting_start_y = 0.35
        
        DirectLabel(
            text="3x3 Crafting",
            scale=0.04,
            pos=(crafting_start_x + self.slot_size, 0, crafting_start_y + 0.15),
            text_fg=(0.8, 0.8, 0.8, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.window
        )
        
        for i in range(9):
            row = i // 3
            col = i % 3
            x = crafting_start_x + col * (self.slot_size + self.slot_spacing)
            y = crafting_start_y - row * (self.slot_size + self.slot_spacing)
            self._create_slot(x, y, "crafting", i)
        
        # Arrow
        DirectLabel(
            text="->",
            scale=0.08,
            pos=(crafting_start_x + 3.5 * (self.slot_size + self.slot_spacing), 0, crafting_start_y - (self.slot_size + self.slot_spacing)),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.window
        )
        
        # Output Slot
        output_x = crafting_start_x + 4.5 * (self.slot_size + self.slot_spacing)
        output_y = crafting_start_y - (self.slot_size + self.slot_spacing)
        self._create_slot(output_x, output_y, "output", 0)
        
        # --- Main Inventory (3 rows of 9) ---
        inv_start_x = -4 * (self.slot_size + self.slot_spacing)
        inv_start_y = -0.05
        
        for i in range(27):
            row = i // 9
            col = i % 9
            x = inv_start_x + col * (self.slot_size + self.slot_spacing)
            y = inv_start_y - row * (self.slot_size + self.slot_spacing)
            self._create_slot(x, y, "inventory", i)
        
        # --- Hotbar (1 row of 9) ---
        hotbar_start_y = inv_start_y - 3 * (self.slot_size + self.slot_spacing) - 0.05
        
        for i in range(9):
            x = inv_start_x + i * (self.slot_size + self.slot_spacing)
            y = hotbar_start_y
            self._create_slot(x, y, "hotbar", i)
        
        # Cursor Item
        self.cursor_icon = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(-self.slot_size/2.5, self.slot_size/2.5, -self.slot_size/2.5, self.slot_size/2.5),
            parent=self.frame,
            state=DGG.DISABLED
        )
        self.cursor_count = DirectLabel(
            text="",
            scale=0.04,
            pos=(self.slot_size/3, 0, -self.slot_size/3),
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.cursor_icon,
            text_align=TextNode.ARight
        )
        self.cursor_icon.hide()
        
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
        
        # Mouse update task
        self.app.taskMgr.add(self._update_mouse_task, "crafting_table_mouse_update")
    
    def _create_slot(self, x, y, slot_type, index):
        """Create a single slot."""
        frame = DirectButton(
            frameColor=(0.4, 0.4, 0.4, 1),
            frameSize=(-self.slot_size/2, self.slot_size/2, -self.slot_size/2, self.slot_size/2),
            pos=(x, 0, y),
            parent=self.window,
            relief=DGG.FLAT,
            command=self._on_slot_click,
            extraArgs=[slot_type, index]
        )
        frame.bind(DGG.B3PRESS, self._on_slot_right_click, [slot_type, index])
        frame.bind(DGG.WITHIN, self._on_slot_hover, [slot_type, index])
        frame.bind(DGG.WITHOUT, self._on_slot_exit, [slot_type, index])
        
        DirectFrame(
            frameColor=(0.2, 0.2, 0.2, 1),
            frameSize=(-self.slot_size/2 + 0.005, self.slot_size/2 - 0.005, -self.slot_size/2 + 0.005, self.slot_size/2 - 0.005),
            parent=frame,
            state=DGG.DISABLED
        )
        
        icon = DirectFrame(
            frameColor=(1, 1, 1, 1),
            frameSize=(-self.slot_size/2.5, self.slot_size/2.5, -self.slot_size/2.5, self.slot_size/2.5),
            parent=frame,
            state=DGG.DISABLED
        )
        icon.setTransparency(TransparencyAttrib.MAlpha)
        icon.hide()
        
        count_label = DirectLabel(
            text="",
            scale=0.035,
            pos=(self.slot_size/2 - 0.01, 0, -self.slot_size/2 + 0.01),
            text_fg=(1, 1, 1, 1),
            text_shadow=(0, 0, 0, 1),
            frameColor=(0, 0, 0, 0),
            parent=frame,
            text_align=TextNode.ARight
        )
        
        self.slots.append({
            "frame": frame,
            "icon": icon,
            "count_label": count_label,
            "type": slot_type,
            "index": index,
            "x": x,
            "y": y
        })
    
    def open(self):
        if not self.frame:
            self.create()
        
        # Initialize texture manager if not already done
        if self.texture_manager is None:
            from voxel.chunk import get_texture_manager
            self.texture_manager = get_texture_manager()
        
        self.is_open = True
        self.frame.show()
        self.refresh_ui()
        
        self._register_events()
        self.selected_slot_index = 10
        self.nav_active = True
        self._update_selection()
        
        # Unlock mouse
        self.app.mouse_locked = False
        self.app._apply_mouse_lock()
        
        # Hide game UI
        if self.app.hotbar_ui:
            self.app.hotbar_ui.hide()
        if self.app.crosshair:
            self.app.crosshair.hide()
        
        # Bind ESC key to close
        self.app.ignore("escape")
        self.app.accept("escape", self.close)
    
    def close(self):
        if not self.is_open:
            return
        
        self.is_open = False
        self.frame.hide()
        
        self._ignore_events()
        self.nav_active = False
        
        # Return items to inventory
        if self.cursor_item:
            self._distribute_item(self.cursor_item)
            self.cursor_item = None
        
        for i in range(9):
            if self.crafting_grid[i]:
                self._distribute_item(self.crafting_grid[i])
                self.crafting_grid[i] = None
        self.crafting_output = None
        
        # Lock mouse
        self.app.mouse_locked = True
        self.app._apply_mouse_lock()
        
        # Show game UI
        if self.app.hotbar_ui:
            self.app.hotbar_ui.show()
            self.app._update_hotbar_ui()
        if self.app.crosshair:
            self.app.crosshair.show()
        
        # Restore ESC key to pause menu
        self.app.ignore("escape")
        self.app.accept("escape", self.app._toggle_pause_menu)

    def _register_events(self):
        self.accept("control-up", self._on_nav, ["up"])
        self.accept("control-down", self._on_nav, ["down"])
        self.accept("control-left", self._on_nav, ["left"])
        self.accept("control-right", self._on_nav, ["right"])
        self.accept("control-select", self._on_select)
        self.accept("control-back", self.close)
        self.accept("control-pause", self.close)

    def _ignore_events(self):
        self.ignore("control-up")
        self.ignore("control-down")
        self.ignore("control-left")
        self.ignore("control-right")
        self.ignore("control-select")
        self.ignore("control-back")
        self.ignore("control-pause")

    def _on_nav(self, direction):
        if not self.is_open: return
        
        current = self.selected_slot_index
        # 0-8: Crafting (3x3)
        # 9: Output
        # 10-36: Inventory
        # 37-45: Hotbar
        
        if direction == "up":
            if 37 <= current <= 45:
                self.selected_slot_index = current - 9 
            elif 19 <= current <= 36:
                self.selected_slot_index = current - 9
            elif 10 <= current <= 18:
                if current <= 12: self.selected_slot_index = 6 # Bottom row of crafting
                else: self.selected_slot_index = 9 # Output
            elif 3 <= current <= 8:
                self.selected_slot_index = current - 3
            elif 9 == current: # Output
                pass # Can't go up
            elif 0 <= current <= 2:
                pass
                
        elif direction == "down":
            if 0 <= current <= 5: # Crafting up
                self.selected_slot_index += 3
            elif 6 <= current <= 8: # Crafting bot
                self.selected_slot_index = 10
            elif current == 9: # Output
                self.selected_slot_index = 15
            elif 10 <= current <= 27: # Inv
                self.selected_slot_index += 9
            elif 28 <= current <= 36: # Inv bot to hotbar
                self.selected_slot_index += 9
                
        elif direction == "left":
            if current in [0, 3, 6, 10, 19, 28, 37]: # Left edges
                pass
            elif current == 9: # Output
                self.selected_slot_index = 2 # Right crafting top
            else:
                self.selected_slot_index -= 1
                
        elif direction == "right":
            if current in [2, 5, 8]: # Crafting right
                self.selected_slot_index = 9 # Output
            elif current in [18, 27, 36, 45]: # Right edges
                pass
            elif current == 9:
                pass
            else:
                self.selected_slot_index += 1
        
        if self.selected_slot_index < 0: self.selected_slot_index = 0
        if self.selected_slot_index >= len(self.slots): self.selected_slot_index = len(self.slots) - 1
        
        self._update_selection()
        
    def _update_selection(self):
        # Highlight current slot
        for i, slot in enumerate(self.slots):
            if i == self.selected_slot_index:
                slot['frame']['frameColor'] = (0.6, 0.6, 0.6, 1)
                self._on_slot_hover(slot['type'], slot['index'])
            else:
                slot['frame']['frameColor'] = (0.4, 0.4, 0.4, 1)
                
    def _on_select(self):
        if not self.is_open: return
        slot = self.slots[self.selected_slot_index]
        self._on_slot_click(slot['type'], slot['index'])
    
    def _distribute_item(self, item_data):
        """Try to add item back to inventory/hotbar."""
        # Try to stack
        for i in range(len(self.app.hotbar)):
            slot = self.app.hotbar[i]
            if slot and slot['block'] == item_data['block']:
                slot['count'] += item_data['count']
                return
        for i in range(len(self.app.inventory)):
            slot = self.app.inventory[i]
            if slot and slot['block'] == item_data['block']:
                slot['count'] += item_data['count']
                return
        
        # Find empty slot
        for i in range(len(self.app.hotbar)):
            if self.app.hotbar[i] is None:
                self.app.hotbar[i] = item_data
                return
        for i in range(len(self.app.inventory)):
            if self.app.inventory[i] is None:
                self.app.inventory[i] = item_data
                return
        
        print("Inventory full, item lost: ", item_data)
    
    def _get_slot_data(self, slot_type, index):
        if slot_type == "inventory":
            return self.app.inventory[index]
        elif slot_type == "hotbar":
            return self.app.hotbar[index]
        elif slot_type == "crafting":
            return self.crafting_grid[index]
        elif slot_type == "output":
            return self.crafting_output
        return None
    
    def _set_slot_data(self, slot_type, index, data):
        if slot_type == "inventory":
            self.app.inventory[index] = data
        elif slot_type == "hotbar":
            self.app.hotbar[index] = data
        elif slot_type == "crafting":
            self.crafting_grid[index] = data
            self._check_crafting()
        elif slot_type == "output":
            self.crafting_output = data
    
    def refresh_ui(self):
        """Update all slot visuals."""
        for slot in self.slots:
            data = self._get_slot_data(slot['type'], slot['index'])
            self._update_slot_visual(slot, data)
        self._update_cursor_renderer()
    
    def _get_item_texture(self, block_id):
        """Get the texture for a given block/item ID."""
        from voxel.chunk import (
            BLOCK_STICKS, BLOCK_PICKAXE_WOOD, BLOCK_PICKAXE_STONE, BLOCK_PICKAXE_IRON,
            BLOCK_AXE_WOOD, BLOCK_AXE_STONE, BLOCK_AXE_IRON,
            BLOCK_SHOVEL_WOOD, BLOCK_SHOVEL_STONE, BLOCK_SHOVEL_IRON,
            BLOCK_SWORD_WOOD, BLOCK_SWORD_STONE, BLOCK_SWORD_IRON
        )
        from voxel.mob_system import ITEM_RAW_MEAT, ITEM_RAW_CHICKEN, ITEM_RAW_PORK
        from voxel.texture_manager import BLOCK_TEXTURES
        
        # Handle tools (items)
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
        
        # Handle meat items
        meat_map = {
            ITEM_RAW_MEAT: ('meat', 'raw_meat'),
            ITEM_RAW_CHICKEN: ('meat', 'raw_chicken'),
            ITEM_RAW_PORK: ('meat', 'raw_pork'),
        }
        
        # Check if it's a tool
        if block_id in tool_map:
            category, name = tool_map[block_id]
            return self.texture_manager.load_texture(category, f'{name}.png')
        
        # Check if it's meat
        if block_id in meat_map:
            category, name = meat_map[block_id]
            return self.texture_manager.load_texture(category, f'{name}.png')
        
        # Check if it's a block
        if block_id in BLOCK_TEXTURES:
            texture_name = BLOCK_TEXTURES[block_id]
            return self.texture_manager.get_block_texture(texture_name)
        
        return None
    
    def _update_slot_visual(self, slot_ui, data):
        # Get slot key for tracking image
        slot_key = (slot_ui['type'], slot_ui['index'])
        
        if data:
            # Get texture for this item
            texture = self._get_item_texture(data['block'])
            
            if texture:
                # Remove old image if exists
                if slot_key in self.icon_images:
                    self.icon_images[slot_key].destroy()
                
                # Change icon frame to transparent
                slot_ui['icon']['frameColor'] = (0, 0, 0, 0)
                slot_ui['icon'].show()
                
                # Create new OnscreenImage with texture
                img = OnscreenImage(
                    image=texture,
                    scale=(self.slot_size/2.5, 1, self.slot_size/2.5),
                    parent=slot_ui['icon']
                )
                img.setTransparency(TransparencyAttrib.MAlpha)
                self.icon_images[slot_key] = img
            
            # Update Count
            if data['count'] > 1:
                slot_ui['count_label']['text'] = str(data['count'])
            else:
                slot_ui['count_label']['text'] = ""
        else:
            # Hide icon by removing image
            if slot_key in self.icon_images:
                self.icon_images[slot_key].destroy()
                del self.icon_images[slot_key]
            slot_ui['icon'].hide()
            slot_ui['count_label']['text'] = ""
    
    def _update_cursor_renderer(self):
        # Clean up old cursor image
        if self.cursor_image:
            self.cursor_image.destroy()
            self.cursor_image = None
        
        if self.cursor_item:
            self.cursor_icon.show()
            self.cursor_icon['frameColor'] = (0, 0, 0, 0)  # Transparent
            
            # Get texture for cursor item
            texture = self._get_item_texture(self.cursor_item['block'])
            
            if texture:
                # Create OnscreenImage with texture
                self.cursor_image = OnscreenImage(
                    image=texture,
                    scale=(self.slot_size/2.5, 1, self.slot_size/2.5),
                    parent=self.cursor_icon
                )
                self.cursor_image.setTransparency(TransparencyAttrib.MAlpha)
            
            if self.cursor_item['count'] > 1:
                self.cursor_count['text'] = str(self.cursor_item['count'])
            else:
                self.cursor_count['text'] = ""
            
            if self.nav_active:
                slot = self.slots[self.selected_slot_index]
                self.cursor_icon.setPos(slot['x'], 0, slot['y'])
                
        else:
            self.cursor_icon.hide()
    
    def _on_slot_click(self, slot_type, index):
        """Handle left click on slot."""
        clicked_data = self._get_slot_data(slot_type, index)
        
        if slot_type == "output":
            # Crafting Result Logic
            if self.cursor_item is None and clicked_data is not None:
                self.cursor_item = clicked_data
                self._set_slot_data("output", 0, None)
                self._consume_crafting_ingredients()
            elif self.cursor_item is not None and clicked_data is not None:
                if self.cursor_item['block'] == clicked_data['block']:
                    self.cursor_item['count'] += clicked_data['count']
                    self._set_slot_data("output", 0, None)
                    self._consume_crafting_ingredients()
            self.refresh_ui()
            return
        
        # Normal Slot Logic
        if self.cursor_item is None:
            if clicked_data is not None:
                self.cursor_item = clicked_data
                self._set_slot_data(slot_type, index, None)
        else:
            if clicked_data is None:
                self._set_slot_data(slot_type, index, self.cursor_item)
                self.cursor_item = None
            else:
                if self.cursor_item['block'] == clicked_data['block']:
                    clicked_data['count'] += self.cursor_item['count']
                    self.cursor_item = None
                else:
                    temp = clicked_data
                    self._set_slot_data(slot_type, index, self.cursor_item)
                    self.cursor_item = temp
        
        self.refresh_ui()
    
    def _on_slot_right_click(self, slot_type, index, event=None):
        """Handle right click on slot."""
        clicked_data = self._get_slot_data(slot_type, index)
        
        if slot_type == "output":
            self._on_slot_click(slot_type, index)
            return
        
        if self.cursor_item is None:
            if clicked_data is not None:
                count = clicked_data['count']
                take = (count + 1) // 2
                leave = count - take
                
                self.cursor_item = {'block': clicked_data['block'], 'count': take}
                
                if leave > 0:
                    clicked_data['count'] = leave
                else:
                    self._set_slot_data(slot_type, index, None)
        else:
            if clicked_data is None:
                one_item = {'block': self.cursor_item['block'], 'count': 1}
                self._set_slot_data(slot_type, index, one_item)
                
                self.cursor_item['count'] -= 1
                if self.cursor_item['count'] <= 0:
                    self.cursor_item = None
            elif clicked_data['block'] == self.cursor_item['block']:
                clicked_data['count'] += 1
                
                self.cursor_item['count'] -= 1
                if self.cursor_item['count'] <= 0:
                    self.cursor_item = None
        
        self.refresh_ui()
    
    def _consume_crafting_ingredients(self):
        """Consume 1 item from each crafting slot."""
        for i in range(9):
            slot = self.crafting_grid[i]
            if slot:
                slot['count'] -= 1
                if slot['count'] <= 0:
                    self.crafting_grid[i] = None
        
        self._check_crafting()
    
    def _check_crafting(self):
        """Check if current 3x3 grid matches a recipe."""
        # Gather ingredients from 3x3 grid
        ingredients = {}
        non_empty_slots = 0
        for slot in self.crafting_grid:
            if slot:
                bid = slot['block']
                ingredients[bid] = ingredients.get(bid, 0) + 1
                non_empty_slots += 1
        
        if non_empty_slots == 0:
            self.crafting_output = None
            return
        
        # Check against all recipes
        match = None
        
        for recipe in crafting_system.recipes:
            req_ingredients = recipe['ingredients']
            
            # Check if counts match exactly
            matches = True
            
            for bid, count in ingredients.items():
                if req_ingredients.get(bid, 0) != count:
                    matches = False
                    break
            
            for bid, count in req_ingredients.items():
                if ingredients.get(bid, 0) != count:
                    matches = False
                    break
            
            if matches:
                match = recipe
                break
        
        if match:
            out = match['output']
            self.crafting_output = {'block': out['block'], 'count': out['count']}
        else:
            self.crafting_output = None
    
    def _update_mouse_task(self, task):
        if not self.is_open:
            return Task.cont
        
        if self.app.mouseWatcherNode.hasMouse():
            mpos = self.app.mouseWatcherNode.getMouse()
            x = mpos.getX() * self.app.getAspectRatio()
            y = mpos.getY()
            
            if not self.nav_active:
                if self.cursor_icon:
                    self.cursor_icon.setPos(x, 0, y)
                
                if self.tooltip and not self.tooltip.isHidden():
                    self.tooltip.setPos(x + 0.05, 0, y - 0.05)
        
        return Task.cont
    
    def _on_slot_hover(self, slot_type, index, event=None):
        self.hovered_slot = (slot_type, index)
        data = self._get_slot_data(slot_type, index)
        
        if data:
            block_id = data['block']
            name = self._get_block_name(block_id)
            self.tooltip['text'] = name
            self.tooltip.show()
            
            if self.nav_active:
                slot = next((s for s in self.slots if s['type'] == slot_type and s['index'] == index), None)
                if slot:
                    self.tooltip.setPos(slot['x'] + 0.05, 0, slot['y'] - 0.05)
        else:
            self.tooltip.hide()
    
    def _on_slot_exit(self, slot_type, index, event=None):
        if self.hovered_slot == (slot_type, index):
            self.hovered_slot = None
            self.tooltip.hide()
    
    def _get_block_name(self, block_id):
        from voxel.chunk import (
            BLOCK_GRASS, BLOCK_DIRT, BLOCK_STONE, BLOCK_SAND, BLOCK_WOOD,
            BLOCK_LEAVES, BLOCK_COBBLESTONE, BLOCK_BRICK, BLOCK_BEDROCK,
            BLOCK_SANDSTONE, BLOCK_PLANKS, BLOCK_STICKS,
            BLOCK_PICKAXE_WOOD, BLOCK_PICKAXE_STONE, BLOCK_AXE_WOOD,
            BLOCK_AXE_STONE, BLOCK_SHOVEL_WOOD, BLOCK_SHOVEL_STONE,
            BLOCK_SWORD_WOOD, BLOCK_SWORD_STONE, BLOCK_CRAFTING_TABLE,
            BLOCK_FURNACE, BLOCK_CHEST,
            BLOCK_JUNGLE_LOG, BLOCK_BIRCH_LOG, BLOCK_JUNGLE_PLANKS, BLOCK_BIRCH_PLANKS,
            BLOCK_IRON_INGOT
        )
        from voxel.mob_system import ITEM_RAW_MEAT, ITEM_RAW_CHICKEN, ITEM_RAW_PORK
        
        names = {
            BLOCK_GRASS: "Grass Block",
            BLOCK_DIRT: "Dirt",
            BLOCK_STONE: "Stone",
            BLOCK_SAND: "Sand",
            BLOCK_WOOD: "Oak Log",
            BLOCK_JUNGLE_LOG: "Jungle Log",
            BLOCK_BIRCH_LOG: "Birch Log",
            BLOCK_LEAVES: "Leaves",
            BLOCK_COBBLESTONE: "Cobblestone",
            BLOCK_BRICK: "Brick",
            BLOCK_BEDROCK: "Bedrock",
            BLOCK_SANDSTONE: "Sandstone",
            BLOCK_PLANKS: "Oak Planks",
            BLOCK_JUNGLE_PLANKS: "Jungle Planks",
            BLOCK_BIRCH_PLANKS: "Birch Planks",
            BLOCK_STICKS: "Sticks",
            BLOCK_PICKAXE_WOOD: "Wooden Pickaxe",
            BLOCK_PICKAXE_STONE: "Stone Pickaxe",
            BLOCK_AXE_WOOD: "Wooden Axe",
            BLOCK_AXE_STONE: "Stone Axe",
            BLOCK_SHOVEL_WOOD: "Wooden Shovel",
            BLOCK_SHOVEL_STONE: "Stone Shovel",
            BLOCK_SWORD_WOOD: "Wooden Sword",
            BLOCK_SWORD_STONE: "Stone Sword",
            BLOCK_CRAFTING_TABLE: "Crafting Table",
            BLOCK_FURNACE: "Furnace",
            BLOCK_CHEST: "Chest",
            BLOCK_IRON_INGOT: "Iron Ingot",
            ITEM_RAW_MEAT: "Raw Meat",
            ITEM_RAW_CHICKEN: "Raw Chicken",
            ITEM_RAW_PORK: "Raw Pork",
        }
        return names.get(block_id, f"Unknown Item ({block_id})")
