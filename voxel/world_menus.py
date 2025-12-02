"""
World selection and creation menus for the voxel game.
"""

from direct.gui.DirectGui import DirectFrame, DirectLabel, DirectButton, DirectEntry, DirectScrolledFrame
from direct.gui.OnscreenImage import OnscreenImage
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode
import os
from panda3d.core import TextNode, TexturePool


from . import settings

class WorldSelectionMenu(DirectObject):
    """World selection menu with grid of worlds."""
    
    def __init__(self, app, world_manager):
        self.app = app
        self.world_manager = world_manager
        self.frame = None
        self.world_buttons = []
        self.selected_world = None
        self.scroll_frame = None
        self.active = False
        
        # Navigation state
        self.control_buttons = [] # Bottom row buttons
        self.grid_cols = 4
        self.nav_index = 0 # Index in combined list (worlds + controls)
        # Or better: coordinate system?
        # Let's use a flat list of interactive elements for simplicity, or sections.
        # Sections: Worlds Grid -> Bottom Row.
        self.nav_section = "worlds" # "worlds" or "controls"
        self.nav_row = 0
        self.nav_col = 0
        
    def create(self):
        """Create the world selection menu."""
        # Main background frame
        self.frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.3, 0.9),
            frameSize=(-1.5, 1.5, -1, 1),
            pos=(0, 0, 0),
            parent=self.app.aspect2d
        )
        
        # Title
        DirectLabel(
            text="SELECT WORLD",
            scale=0.12,
            pos=(0, 0, 0.85),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.frame
        )
        
        # Scrollable area for worlds
        self.scroll_frame = DirectScrolledFrame(
            frameSize=(-1.3, 1.3, -0.7, 0.7),
            canvasSize=(-1.2, 1.2, -2, 0.6),
            scrollBarWidth=0.04,
            frameColor=(0.15, 0.15, 0.4, 0.5),
            pos=(0, 0, 0),
            parent=self.frame
        )
        
        # Populate worlds
        self._populate_worlds()
        
        # Bottom buttons
        button_y = -0.85
        button_scale = 0.08
        
        # BACK button
        back_btn = DirectButton(
            text="BACK",
            scale=button_scale,
            pos=(-0.8, 0, button_y),
            command=self._on_back,
            parent=self.frame,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.2, 0.2, 0.8, 1)
        )
        
        # CREATE button
        create_btn = DirectButton(
            text="CREATE",
            scale=button_scale,
            pos=(-0.3, 0, button_y),
            command=self._on_create,
            parent=self.frame,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.1, 0.1, 0.1, 1)
        )
        
        # DELETE button
        delete_btn = DirectButton(
            text="DELETE",
            scale=button_scale,
            pos=(0.35, 0, button_y),
            command=self._on_delete,
            parent=self.frame,
            text_fg=(1, 0.3, 0.3, 1),
            frameColor=(0.3, 0.1, 0.1, 1)
        )
        
        # PLAY button
        play_btn = DirectButton(
            text="PLAY",
            scale=button_scale,
            pos=(0.9, 0, button_y),
            command=self._on_play,
            parent=self.frame,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.1, 0.5, 0.1, 1)
        )
        
        self.control_buttons = [back_btn, create_btn, delete_btn, play_btn]
        
        self.frame.hide()
        return self.frame
    
    def _populate_worlds(self):
        """Populate the world grid."""
        # Clear existing buttons
        for btn_data in self.world_buttons:
            if 'frame' in btn_data:
                btn_data['frame'].destroy()
        self.world_buttons = []
        
        # Get worlds sorted by last played
        worlds = self.world_manager.get_worlds_sorted_by_last_played()
        
        if not worlds:
            # No worlds message
            DirectLabel(
                text="No worlds found.\nClick CREATE to make a new world.",
                scale=0.08,
                pos=(0, 0, 0),
                text_fg=(0.8, 0.8, 0.8, 1),
                frameColor=(0, 0, 0, 0),
                parent=self.scroll_frame.getCanvas()
            )
            # Initialize nav to controls if no worlds
            self.nav_section = "controls"
            self.nav_col = 1 # Create button
            return
        
        # Layout: First world (most recent) is larger
        # Then a grid of smaller worlds
        
        y_pos = 0.4
        
        # First world (largest - most recently played)
        if worlds:
            world = worlds[0]
            self._create_world_card(world, 0, 0, y_pos, large=True, row=0, col=0)
            y_pos -= 0.5
        
        # Rest of the worlds in a grid (4 per row)
        self.grid_cols = 4
        card_width = 0.35
        card_height = 0.35
        x_spacing = 0.65
        y_spacing = 0.5
        
        for i, world in enumerate(worlds[1:], start=1):
            row = 1 + (i - 1) // self.grid_cols
            col = (i - 1) % self.grid_cols
            
            x_pos = -1.0 + col * x_spacing
            y_pos_card = y_pos - (row - 1) * y_spacing
            
            self._create_world_card(world, i, x_pos, y_pos_card, large=False, row=row, col=col)
        
        # Update canvas size for scrolling
        total_rows = 1 + ((len(worlds) - 1) // self.grid_cols) + 1
        canvas_height = 0.7 + total_rows * y_spacing
        self.scroll_frame['canvasSize'] = (-1.2, 1.2, -canvas_height, 0.6)
        
        # Reset nav if we populated worlds
        self.nav_section = "worlds"
        self.nav_row = 0
        self.nav_col = 0
        self.selected_world = worlds[0]
    
    def _create_world_card(self, world, index, x, y, large=False, row=0, col=0):
        """Create a world card with thumbnail and name."""
        if large:
            width = 0.7
            height = 0.4
            name_scale = 0.08
        else:
            width = 0.3
            height = 0.25
            name_scale = 0.05
        
        # Card frame
        card_frame = DirectFrame(
            frameColor=(0.2, 0.2, 0.2, 0.8),
            frameSize=(-width/2, width/2, -height/2, height/2),
            pos=(x, 0, y),
            parent=self.scroll_frame.getCanvas()
        )
        
        # Screenshot placeholder or actual image
        screenshot_height = height * 0.6
        screenshot_width = width - 0.04
        
        # Check if screenshot exists
        screenshot_path = None
        if world.screenshot:
            # Construct full path
            full_path = self.world_manager.get_world_path(world.folder) + "/" + world.screenshot
            if os.path.exists(full_path):
                # Force reload of texture from disk
                tex = TexturePool.findTexture(full_path)
                if tex:
                    TexturePool.releaseTexture(tex)
                screenshot_path = full_path
        
        if screenshot_path:
            # Display screenshot
            screenshot_bg = OnscreenImage(
                image=screenshot_path,
                pos=(0, 0, height/2 - screenshot_height/2 - 0.02),
                scale=(screenshot_width/2, 1, screenshot_height/2),
                parent=card_frame
            )
        else:
            # Placeholder
            screenshot_bg = DirectFrame(
                frameColor=(0.4, 0.4, 0.4, 1),
                frameSize=(-screenshot_width/2, screenshot_width/2, -screenshot_height/2, screenshot_height/2),
                pos=(0, 0, height/2 - screenshot_height/2 - 0.02),
                parent=card_frame
            )
            
            # Add "WORLD PNG" text only if no screenshot
            DirectLabel(
                text="WORLD PNG",
                scale=0.04 if large else 0.03,
                pos=(0, 0, 0),
                text_fg=(0.7, 0.7, 0.7, 1),
                frameColor=(0, 0, 0, 0),
                parent=screenshot_bg
            )
        
        # World name
        name_label = DirectLabel(
            text=world.name,
            scale=name_scale,
            pos=(0, 0, -height/2 + 0.08),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            parent=card_frame
        )
        
        # Make card clickable
        card_button = DirectButton(
            frameSize=(-width/2, width/2, -height/2, height/2),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0),
            command=self._on_world_selected,
            extraArgs=[world, card_frame],
            parent=card_frame,
            pressEffect=False
        )
        
        self.world_buttons.append({
            'world': world,
            'frame': card_frame,
            'button': card_button,
            'index': index,
            'row': row,
            'col': col
        })
    
    def _on_world_selected(self, world, card_frame):
        """Handle world selection."""
        # Unhighlight all cards
        for btn_data in self.world_buttons:
            # Reset color based on if it's active in grid nav??
            # No, mouse click logic conflicts with key nav logic.
            # Standardize: mouse hover updates nav state?
            pass
            
        # But for mouse logic (existing code), we just visual highlight and set self.selected_world
        self.selected_world = world
        print(f"[WorldSelectionMenu] Selected world: {world.name}")
        self._update_visuals()
    
    def show(self):
        """Show the menu."""
        if self.frame:
            # Refresh worlds list when showing
            self._populate_worlds()
            self.frame.show()
            self.active = True
            self._register_events()
            self._update_visuals()
    
    def hide(self):
        """Hide the menu."""
        if self.frame:
            self.frame.hide()
            self.active = False
            self._ignore_events()

    def _register_events(self):
        self.accept("control-up", self._on_nav, ["up"])
        self.accept("control-down", self._on_nav, ["down"])
        self.accept("control-left", self._on_nav, ["left"])
        self.accept("control-right", self._on_nav, ["right"])
        self.accept("control-select", self._on_select)
        self.accept("control-back", self._on_back)
        
    def _ignore_events(self):
        self.ignore("control-up")
        self.ignore("control-down")
        self.ignore("control-left")
        self.ignore("control-right")
        self.ignore("control-select")
        self.ignore("control-back")

    def _on_nav(self, direction):
        if not self.active: return
        
        if self.nav_section == "worlds":
            self._nav_worlds(direction)
        else:
            self._nav_controls(direction)
            
        self._update_visuals()

    def _nav_worlds(self, direction):
        # Logic for grid navigation
        if not self.world_buttons:
            # Empty worlds, force to controls
            self.nav_section = "controls"
            self.nav_col = 1
            return

        # Current item is determined by nav_row, nav_col
        # Find index of current item?
        # Actually simpler: track index directly in self.world_buttons?
        # But we have rows/cols.
        # Let's just find the closest button in desired direction?
        # Or strict grid logic.
        
        # The first world is row 0, col 0 (center/large).
        # Subsequent worlds are row 1+, col 0-3.
        
        current_btn = None
        current_idx = -1
        for i, b in enumerate(self.world_buttons):
            if b['row'] == self.nav_row and b['col'] == self.nav_col:
                current_btn = b
                current_idx = i
                break
        
        if current_btn is None:
             # Reset
             self.nav_row = 0
             self.nav_col = 0
             return

        if direction == "down":
            next_row = self.nav_row + 1
            # Check if world exists at this row
            exists = any(b['row'] == next_row for b in self.world_buttons)
            if exists:
                # Find closest col
                # If current is row 0 (center), go to col 1 or 2?
                # If next is row 1 (grid), try to match col logic.
                # But row 0 is single item.
                if self.nav_row == 0: next_col = 1 
                else: next_col = self.nav_col
                
                # Clamp col
                while not any(b['row'] == next_row and b['col'] == next_col for b in self.world_buttons) and next_col >= 0:
                    next_col -= 1
                if any(b['row'] == next_row and b['col'] == next_col for b in self.world_buttons):
                    self.nav_row = next_row
                    self.nav_col = next_col
            else:
                # Go to controls
                self.nav_section = "controls"
                # Map column?
                self.nav_col = 1 # Create
        
        elif direction == "up":
            if self.nav_row > 0:
                next_row = self.nav_row - 1
                if next_row == 0:
                    self.nav_row = 0
                    self.nav_col = 0
                else:
                    # Just move up
                    if any(b['row'] == next_row and b['col'] == self.nav_col for b in self.world_buttons):
                        self.nav_row = next_row
                    else:
                        # try closest
                        pass

        elif direction == "left":
            if self.nav_col > 0 and self.nav_row > 0:
                self.nav_col -= 1
        
        elif direction == "right":
            if self.nav_row > 0:
                if any(b['row'] == self.nav_row and b['col'] == self.nav_col + 1 for b in self.world_buttons):
                    self.nav_col += 1

    def _nav_controls(self, direction):
        if direction == "left":
            self.nav_col = (self.nav_col - 1) % len(self.control_buttons)
        elif direction == "right":
            self.nav_col = (self.nav_col + 1) % len(self.control_buttons)
        elif direction == "up":
            # Go back to worlds
            if self.world_buttons:
                self.nav_section = "worlds"
                # Go to last row
                last_world = self.world_buttons[-1]
                self.nav_row = last_world['row']
                self.nav_col = min(last_world['col'], 1) # roughly center

    def _on_select(self):
        if self.nav_section == "worlds":
            # Select world
            # Find current
            for b in self.world_buttons:
                if b['row'] == self.nav_row and b['col'] == self.nav_col:
                    self.selected_world = b['world']
                    # Auto play on double select? 
                    # For now just selecting highlights it. 
                    # Pressing PLAY button (in controls) launches needs separate action.
                    # Or pressing A on a world selects it.
                    # Maybe pressing A on already selected world -> Play?
                    self._on_play() # Let's make A == Play for convenience
                    break
        else:
            # Press button
            btn = self.control_buttons[self.nav_col]
            btn.commandFunc(None)

    def _update_visuals(self):
        # Highlight worlds
        for b in self.world_buttons:
            # Base color
            color = (0.2, 0.2, 0.2, 0.8)
            # If selected world
            if self.selected_world == b['world']:
                 color = (0.3, 0.5, 0.3, 0.9)
            
            # If nav cursor is here (Bright border?)
            if self.nav_section == "worlds" and b['row'] == self.nav_row and b['col'] == self.nav_col:
                # Highlight
                b['frame']['frameColor'] = (0.5, 0.7, 0.5, 1)
                # Ensure visible in scroll frame?
                # self.scroll_frame... scrollTo? difficult in Panda3D DirectScrolledFrame
            else:
                b['frame']['frameColor'] = color
                
        # Highlight controls
        for i, btn in enumerate(self.control_buttons):
            if self.nav_section == "controls" and i == self.nav_col:
                btn.setScale(0.09)
                # Add highlight color
                if i == 2: # Delete (special color)
                     btn['frameColor'] = (0.5, 0.2, 0.2, 1)
                else:
                     btn['frameColor'] = (0.3, 0.3, 0.9, 1)
            else:
                btn.setScale(0.08)
                # Reset colors
                if i == 2: # Delete
                     btn['frameColor'] = (0.3, 0.1, 0.1, 1)
                elif i == 0: # Back
                     btn['frameColor'] = (0.2, 0.2, 0.8, 1)
                elif i == 1: # Create
                     btn['frameColor'] = (0.1, 0.1, 0.1, 1)
                elif i == 3: # Play
                     btn['frameColor'] = (0.1, 0.5, 0.1, 1)

    def _on_back(self):
        """Return to title screen."""
        self.hide()
        if hasattr(self.app, 'title_screen'):
            self.app.title_screen.show()
    
    def _on_create(self):
        """Open world creation menu."""
        self.hide()
        if hasattr(self.app, 'world_creation_menu'):
            self.app.world_creation_menu.show()
    
    def _on_delete(self):
        """Delete selected world."""
        if self.selected_world:
            # Confirm and delete
            self.world_manager.delete_world(self.selected_world.folder)
            self.selected_world = None
            # Refresh the list
            self._populate_worlds()
            print(f"[WorldSelectionMenu] World deleted")
    
    def _on_play(self):
        """Play selected world."""
        # If in controls section, self.selected_world might be set from before.
        if self.selected_world:
            print(f"[WorldSelectionMenu] Playing world: {self.selected_world.name}")
            # Set the selected world in app
            self.app.selected_world_folder = self.selected_world.folder
            # Update last played
            self.world_manager.update_last_played(self.selected_world.folder)
            # Hide menu and start game
            self.hide()
            self.app._start_game_with_world(self.selected_world.folder)
        else:
            print("[WorldSelectionMenu] No world selected")


class WorldCreationMenu(DirectObject):
    """World creation menu for entering name and seed."""
    
    def __init__(self, app, world_manager):
        self.app = app
        self.world_manager = world_manager
        self.frame = None
        self.name_entry = None
        self.seed_entry = None
        self.active = False
        
        self.nav_index = 0 
        # 0: Name, 1: Seed, 2: Game Mode, 3: Difficulty, 4: Cancel, 5: Create
        self.elements = []
        self.game_mode = "Survival"
        self.difficulty = settings.DIFFICULTY_NORMAL
        self.mode_label = None
        self.diff_label = None
        
    def create(self):
        """Create the world creation menu."""
        # Main background frame
        self.frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.3, 0.9),
            frameSize=(-0.8, 0.8, -0.6, 0.6),
            pos=(0, 0, 0),
            parent=self.app.aspect2d
        )
        
        # Title
        DirectLabel(
            text="CREATE NEW WORLD",
            scale=0.12,
            pos=(0, 0, 0.45),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.frame
        )
        
        # World name label
        DirectLabel(
            text="World Name:",
            scale=0.08,
            pos=(-0.3, 0, 0.2),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.frame,
            text_align=TextNode.ALeft
        )
        
        # World name entry
        self.name_entry = DirectEntry(
            scale=0.07,
            pos=(-0.25, 0, 0.08),
            width=10,
            numLines=1,
            focus=1,
            frameColor=(0.3, 0.3, 0.3, 1),
            text_fg=(1, 1, 1, 1),
            parent=self.frame,
            initialText="New World"
        )
        
        # Seed label
        DirectLabel(
            text="Seed (optional):",
            scale=0.08,
            pos=(-0.3, 0, -0.1),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.frame,
            text_align=TextNode.ALeft
        )
        
        # Seed entry
        self.seed_entry = DirectEntry(
            scale=0.07,
            pos=(-0.25, 0, -0.22),
            width=10,
            numLines=1,
            frameColor=(0.3, 0.3, 0.3, 1),
            text_fg=(1, 1, 1, 1),
            parent=self.frame,
            initialText=""
        )
        
        # Game Mode Label
        DirectLabel(
            text="Game Mode:",
            scale=0.08,
            pos=(-0.4, 0, -0.35),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.frame,
            text_align=TextNode.ALeft
        )
        
        # Toggle Button (Label that acts as button)
        self.mode_label = DirectLabel(
            text="Survival",
            scale=0.07,
            pos=(0.15, 0, -0.35),
            text_fg=(0.5, 1, 0.5, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.frame
        )
        # Make it clickable
        self.mode_btn = DirectButton(
            frameSize=(-2, 2, -0.5, 0.5), # Relative to scale
            frameColor=(0,0,0,0),
            pos=(0, 0, 0),
            parent=self.mode_label,
            command=self._toggle_game_mode
        )
        
        # Difficulty Label
        DirectLabel(
            text="Difficulty:",
            scale=0.08,
            pos=(-0.4, 0, -0.5),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.frame,
            text_align=TextNode.ALeft
        )
        
        # Difficulty Toggle Button
        self.diff_label = DirectLabel(
            text="Normal",
            scale=0.07,
            pos=(0.15, 0, -0.5),
            text_fg=(1, 1, 0, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.frame
        )
        # Make it clickable
        self.diff_btn = DirectButton(
            frameSize=(-2, 2, -0.5, 0.5), # Relative to scale
            frameColor=(0,0,0,0),
            pos=(0, 0, 0),
            parent=self.diff_label,
            command=self._toggle_difficulty
        )
        
        # Instructions
        DirectLabel(
            text="Leave seed empty for random generation",
            scale=0.05,
            pos=(0, 0, -0.65),
            text_fg=(0.7, 0.7, 0.7, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.frame
        )
        
        # Bottom buttons
        button_y = -0.75
        button_scale = 0.08
        
        # CANCEL button
        cancel_btn = DirectButton(
            text="CANCEL",
            scale=button_scale,
            pos=(-0.25, 0, button_y),
            command=self._on_cancel,
            parent=self.frame,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.5, 0.2, 0.2, 1)
        )
        
        # CREATE button
        create_btn = DirectButton(
            text="CREATE",
            scale=button_scale,
            pos=(0.25, 0, button_y),
            command=self._on_create,
            parent=self.frame,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.2, 0.5, 0.2, 1)
        )
        
        self.elements = [
            {'type': 'entry', 'obj': self.name_entry},
            {'type': 'entry', 'obj': self.seed_entry},
            {'type': 'toggle', 'obj': self.mode_btn}, # Placeholder obj
            {'type': 'toggle', 'obj': self.diff_btn}, # Placeholder obj
            {'type': 'button', 'obj': cancel_btn},
            {'type': 'button', 'obj': create_btn}
        ]
        
        self.frame.hide()
        return self.frame
    
    def show(self):
        if self.frame:
            # Reset entries
            self.name_entry.enterText("New World")
            self.seed_entry.enterText("")
            self.game_mode = "Survival"
            self.mode_label['text'] = "Survival"
            self.mode_label['text_fg'] = (0.5, 1, 0.5, 1)
            
            self.difficulty = settings.DIFFICULTY_NORMAL
            self.diff_label['text'] = "Normal"
            self.diff_label['text_fg'] = (1, 1, 0, 1)
            
            self.name_entry['focus'] = 1
            self.frame.show()
            self.active = True
            self._register_events()
            self.nav_index = 0
            self._update_visuals()
    
    def hide(self):
        if self.frame:
            self.frame.hide()
            self.active = False
            self._ignore_events()

    def _register_events(self):
        self.accept("control-up", self._on_nav, ["up"])
        self.accept("control-down", self._on_nav, ["down"])
        self.accept("control-left", self._on_nav, ["left"])
        self.accept("control-right", self._on_nav, ["right"])
        self.accept("control-select", self._on_select)
        self.accept("control-back", self._on_cancel)

    def _ignore_events(self):
        self.ignore("control-up")
        self.ignore("control-down")
        self.ignore("control-left")
        self.ignore("control-right")
        self.ignore("control-select")
        self.ignore("control-back")

    def _on_nav(self, direction):
        if not self.active: return
        
        if direction == "up":
            self.nav_index = (self.nav_index - 1) % len(self.elements)
        elif direction == "down":
            self.nav_index = (self.nav_index + 1) % len(self.elements)
        elif direction == "left" or direction == "right":
            if self.nav_index == 2: # Game Mode Toggle
                self._toggle_game_mode()
            elif self.nav_index == 3: # Difficulty Toggle
                self._toggle_difficulty()
            elif self.nav_index >= 4: # Buttons
                 if self.nav_index == 4: self.nav_index = 5
                 else: self.nav_index = 4
        
        self._update_visuals()
        
    def _on_select(self):
        if not self.active: return
        el = self.elements[self.nav_index]
        if el['type'] == 'button':
            el['obj'].commandFunc(None)
        elif el['type'] == 'entry':
            # Focus currently active entry
            el['obj']['focus'] = 1
        elif el['type'] == 'toggle':
            if self.nav_index == 2:
                self._toggle_game_mode()
            elif self.nav_index == 3:
                self._toggle_difficulty()

    def _toggle_difficulty(self):
        self.difficulty = (self.difficulty + 1) % 4
        
        if self.difficulty == settings.DIFFICULTY_PEACEFUL:
            self.diff_label['text'] = "Peaceful"
            self.diff_label['text_fg'] = (0.5, 1, 0.5, 1)
        elif self.difficulty == settings.DIFFICULTY_EASY:
            self.diff_label['text'] = "Easy"
            self.diff_label['text_fg'] = (0.5, 0.8, 1, 1)
        elif self.difficulty == settings.DIFFICULTY_NORMAL:
            self.diff_label['text'] = "Normal"
            self.diff_label['text_fg'] = (1, 1, 0, 1)
        elif self.difficulty == settings.DIFFICULTY_HARD:
            self.diff_label['text'] = "Hard"
            self.diff_label['text_fg'] = (1, 0.5, 0.5, 1)
            
    def _toggle_game_mode(self):
        if self.game_mode == "Survival":
            self.game_mode = "Creative"
            self.mode_label['text_fg'] = (0.5, 0.8, 1, 1) # Blue-ish for Creative
        else:
            self.game_mode = "Survival"
            self.mode_label['text_fg'] = (0.5, 1, 0.5, 1) # Green-ish for Survival
        self.mode_label['text'] = self.game_mode

    def _update_visuals(self):
        for i, el in enumerate(self.elements):
            if i == self.nav_index:
                if el['type'] == 'button':
                    el['obj'].setScale(0.09)
                elif el['type'] == 'entry':
                    el['obj']['focus'] = 1
                elif el['type'] == 'toggle':
                    if i == 2: # Mode
                         self.mode_label.setScale(0.08)
                    elif i == 3: # Difficulty
                         self.diff_label.setScale(0.08)
            else:
                if el['type'] == 'button':
                    el['obj'].setScale(0.08)
                elif el['type'] == 'entry':
                    el['obj']['focus'] = 0
                elif el['type'] == 'toggle':
                    if i == 2:
                        self.mode_label.setScale(0.07)
                    elif i == 3:
                        self.diff_label.setScale(0.07)
        
    def _on_cancel(self):
        """Cancel world creation."""
        self.hide()
        if hasattr(self.app, 'world_selection_menu'):
            self.app.world_selection_menu.show()
    
    def _on_create(self):
        """Create the world and launch it immediately."""
        # Get name and seed
        name = self.name_entry.get().strip()
        if not name:
            name = "New World"
        
        seed_text = self.seed_entry.get().strip()
        seed = None
        if seed_text:
            try:
                seed = int(seed_text)
            except ValueError:
                # Use hash of string as seed
                seed = hash(seed_text) % (2**31)
        
        # Create world
        world_info = self.world_manager.create_world(name, seed, game_mode=self.game_mode, difficulty=self.difficulty)
        print(f"[WorldCreationMenu] Created world: {name} (seed: {world_info.seed}, diff: {self.difficulty})")
        
        # Clear entries
        self.name_entry.enterText("")
        self.seed_entry.enterText("")
        
        # Hide this menu and launch the game with the new world
        self.hide()
        if hasattr(self.app, '_start_game_with_world'):
            self.app._start_game_with_world(world_info.folder)
