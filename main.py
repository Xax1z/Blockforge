from panda3d.core import loadPrcFileData, WindowProperties, Vec3, CollisionRay, CollisionNode, CollisionTraverser, CollisionHandlerQueue, LineSegs, TextNode, Fog, TransparencyAttrib
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui.DirectGui import DGG, DirectFrame, DirectLabel, DirectButton, DirectSlider

from voxel import settings
from voxel.world import World
from voxel.player import Player
from voxel.save_system import SaveSystem
from voxel.crafting import crafting_system, open_crafting_menu, crafting_menu
from voxel.drop_system import DropSystem
from voxel.mob_system import MobSystem, ITEM_RAW_MEAT, ITEM_RAW_CHICKEN, ITEM_RAW_PORK
from voxel.chunk import (
    BLOCK_GRASS,
    BLOCK_DIRT,
    BLOCK_STONE,
    BLOCK_SAND,
    BLOCK_WOOD,
    BLOCK_LEAVES,
    BLOCK_COBBLESTONE,
    BLOCK_BRICK,
    BLOCK_BEDROCK,
    BLOCK_SANDSTONE,
    BLOCK_PLANKS,
    BLOCK_STICKS,
    BLOCK_PICKAXE_WOOD,
    BLOCK_PICKAXE_STONE,
    BLOCK_AXE_WOOD,
    BLOCK_AXE_STONE,
    BLOCK_SHOVEL_WOOD,
    BLOCK_SHOVEL_STONE,
    BLOCK_SWORD_WOOD,
    BLOCK_SWORD_STONE,
    BLOCK_CRAFTING_TABLE,
)

from voxel.title_screen import create_title_screen
from voxel.world_manager import WorldManager
from voxel.world_menus import WorldSelectionMenu, WorldCreationMenu
from voxel.settings_menu import SettingsMenu
from voxel.inventory_ui import InventoryUI
from voxel.input_handler import InputHandler


class App(ShowBase):
    def __init__(self):
        # Panda3D configuration
        
        # Handle PyInstaller paths for plugins (fixes "No graphics pipe" error)
        import sys
        import os
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # In a frozen bundle, plugins are in the internal temp directory
            # We need to tell Panda3D where to look
            loadPrcFileData('', f'plugin-path {sys._MEIPASS}')
            loadPrcFileData('', f'plugin-path {os.path.join(sys._MEIPASS, "panda3d")}')
            # Force load the OpenGL display module
            loadPrcFileData('', 'load-display pandagl')

        # Load global settings first
        SaveSystem.load_settings()
        
        loadPrcFileData(
            "",
            f"""
            window-title {settings.WINDOW_TITLE}
            show-frame-rate-meter {1 if settings.FRAME_RATE_METER else 0}
            sync-video {1 if settings.VSYNC else 0}
            """
        )
        super().__init__()

        # Basic window/camera setup
        self.set_background_color(*settings.BACKGROUND_COLOR)
        self.disableMouse()  # use our own FPS camera controls
        
        # Configure camera near/far planes to reduce Z-fighting
        # Near plane should be as far as possible without clipping nearby geometry
        # Far plane should cover the render distance
        self.camLens.setNear(0.1)  # Prevents clipping very close objects
        self.camLens.setFar(500.0)  # Covers render distance with buffer
        
        # Setup fog for render distance
        if settings.FOG_ENABLED:
            self._setup_fog()
            
        # Apply loaded FOV setting
        self.camLens.setFov(settings.FOV * 180 / 3.14159)

        # Input handling
        self.keys = {
            "forward": False,
            "back": False,
            "left": False,
            "right": False,
            "jump": False,
            "crouch": False,
        }
        self.accept("w", self._set_key, ["forward", True])
        self.accept("w-up", self._set_key, ["forward", False])
        self.accept("s", self._set_key, ["back", True])
        self.accept("s-up", self._set_key, ["back", False])
        self.accept("a", self._set_key, ["left", True])
        self.accept("a-up", self._set_key, ["left", False])
        self.accept("d", self._set_key, ["right", True])
        self.accept("d-up", self._set_key, ["right", False])
        self.accept("space", self._set_key, ["jump", True])
        self.accept("space-up", self._set_key, ["jump", False])
        self.accept("shift", self._set_key, ["crouch", True])
        self.accept("shift-up", self._set_key, ["crouch", False])
        self.accept("escape", self._toggle_pause_menu)
        # Re-lock mouse when clicking the window after pressing Escape
        self.accept("mouse1", self._on_left_mouse_down)
        self.accept("mouse1-up", self._on_left_mouse_up)
        self.accept("mouse3", self._on_right_click)
        
        # Track mouse button state
        self.left_mouse_down = False
        # Save/Load shortcuts
        self.accept("f5", self._quicksave)
        self.accept("f9", self._quickload)
        self.accept("e", self._toggle_inventory)

        # Mouse lock for FPS look
        self.mouse_locked = True
        self.mouse_initialized = False
        self.skip_next_mouse_frame = False
        self._apply_mouse_lock()
        
        # Controller Input Handler
        self.input_handler = InputHandler(self)

        # Pause menu
        self.paused = False
        self.pause_menu = None
        self.pause_elements = []
        self.pause_nav_index = 0
        self._create_pause_menu()
        
        # HUD frame (init early)
        self.hud_frame = None

        # Loading screen
        self.loading_screen = None
        self.loading_label = None
        self._create_loading_screen()
        self._hide_loading_screen()  # Hide by default
        
        # World management
        self.world_manager = WorldManager()
        self.selected_world_folder = None
        
        # Create menus
        self.title_screen = create_title_screen(self)
        # Activate title screen events
        self.title_screen.show()
        
        self.world_selection_menu = WorldSelectionMenu(self, self.world_manager)
        self.world_selection_menu.create()
        self.world_creation_menu = WorldCreationMenu(self, self.world_manager)
        self.world_creation_menu.create()
        self.settings_menu = SettingsMenu(self)
        self.settings_menu.create()

        # Unlock mouse for title screen
        self.mouse_locked = False
        self._apply_mouse_lock()

        # World and player (defer initialization)
        self.world = None
        self.player = None
        self.drop_system = None
        self.mob_system = None
        self.game_ready = False
        self.in_title_screen = True

        # Save system (will be updated when world is selected)
        self.save_system = SaveSystem()
        
        # Save notification label
        self.save_notification = None
        self._create_save_notification()

        # Add crosshair (will be hidden during loading)
        self._create_crosshair()
        self.crosshair.hide()

        # Hotbar system: start empty, fill from mined blocks
        self.hotbar_size = 9
        # Each slot: {'block': block_id, 'count': int} or None
        self.hotbar = [None for _ in range(self.hotbar_size)]
        self.selected_hotbar_slot = 0
        self.hotbar_ui = None
        self.hotbar_images = {}  # Maps slot index to OnscreenImage
        self._create_hotbar()
        self.hotbar_ui.hide()

        # Main Inventory (27 slots)
        self.inventory = [None] * 27
        self.inventory_ui = InventoryUI(self)
        
        # Scroll wheel for hotbar selection
        self.accept("wheel_up", self._scroll_hotbar, [-1])
        self.accept("wheel_down", self._scroll_hotbar, [1])
        
        # Block breaking overlay (for visual crack effect)
        self.break_overlay = None
        self._create_break_overlay()
        
        # Survival HUD
        self.hearts_ui = []
        self.hunger_ui = []
        # self.hud_frame initialized earlier
        self._create_status_hud()
        
        # Day/Night Cycle
        self.day_time = 0.0
        self.day_length = 600.0  # 10 minutes in seconds
        
        # Register cleanup handler for saving on exit
        self.accept("escape-up", self._check_exit)
        self.exitFunc = self._on_exit

    def _check_exit(self):
        """Check if window is being closed."""
        # This is handled by _toggle_pause_menu, but we keep this for compatibility
        pass
    
    def _on_exit(self):
        """Save game state when exiting."""
        if self.player is not None and self.save_system is not None:
            self.save_system.save_player_data(self.player)
            print("[App] Player data saved on exit")
            
            # Save screenshot if in a world
            if self.selected_world_folder:
                import os
                screenshot_filename = "screenshot.png"
                # We need the full path for Panda3D to save it
                # But we want to save it in the world folder
                world_path = self.world_manager.get_world_path(self.selected_world_folder)
                full_path = os.path.join(world_path, screenshot_filename)
                
                # Save screenshot
                if self.win and self.win.getGsg():
                    try:
                        self.win.saveScreenshot(full_path)
                        print(f"[App] Saved screenshot to {full_path}")
                        
                        # Update world metadata
                        self.world_manager.save_screenshot(self.selected_world_folder, screenshot_filename)
                    except Exception as e:
                        print(f"[App] Failed to save screenshot on exit: {e}")

    def _set_key(self, name: str, value: bool):
        self.keys[name] = value

    def _apply_mouse_lock(self):
        # Don't lock mouse if crafting menu or inventory is open
        from voxel.crafting import crafting_menu
        
        inventory_open = hasattr(self, 'inventory_ui') and self.inventory_ui.is_open
        crafting_menu_open = crafting_menu is not None and crafting_menu.is_open
        
        if inventory_open or crafting_menu_open:
            self.mouse_locked = False
            props = WindowProperties()
            props.setCursorHidden(False)
            self.win.requestProperties(props)
            return

        props = WindowProperties()
        props.setCursorHidden(self.mouse_locked)
        self.win.requestProperties(props)
        if self.mouse_locked:
            self._center_mouse()

    def _toggle_pause_menu(self):
        # Don't allow pausing when on title screen
        if self.in_title_screen:
            return

        # If inventory is open, close it instead of pausing
        if hasattr(self, 'inventory_ui') and self.inventory_ui and self.inventory_ui.is_open:
            self.inventory_ui.close()
            return

        self.paused = not self.paused
        if self.paused:
            self._show_pause_menu()
        else:
            self._hide_pause_menu()

    def _create_pause_menu(self):
        # Create pause menu frame (hidden by default)
        self.pause_menu = DirectFrame(
            frameColor=(0, 0, 0, 0.7),
            frameSize=(-1, 1, -1, 1),
            parent=self.aspect2d
        )
        self.pause_menu.hide()

        # Title
        DirectLabel(
            text="PAUSED",
            scale=0.15,
            pos=(0, 0, 0.6),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.pause_menu
        )

        # Settings Button
        self.settings_btn = DirectButton(
            text="Settings",
            scale=0.08,
            pos=(0, 0, 0.1),
            command=self._show_settings_menu,
            extraArgs=["pause"],
            parent=self.pause_menu,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.2, 0.2, 0.2, 1)
        )

        # Instructions
        DirectLabel(
            text="F5 - Quicksave | F9 - Quickload\nPress ESC to resume",
            scale=0.06,
            pos=(0, 0, -0.3),
            text_fg=(0.8, 0.8, 0.8, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.pause_menu
        )

        # Resume button
        self.resume_btn = DirectButton(
            text="Resume (ESC)",
            scale=0.08,
            pos=(0, 0, -0.6),
            command=self._toggle_pause_menu,
            parent=self.pause_menu,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.2, 0.2, 0.2, 1)
        )

        # Return to Title button
        self.return_btn = DirectButton(
            text="Return to Title",
            scale=0.08,
            pos=(0, 0, -0.8),
            command=self._return_to_title,
            parent=self.pause_menu,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.2, 0.2, 0.2, 1)
        )
        
        # Store interactive elements for navigation
        # 0: Settings, 1: Resume, 2: Return to Title
        self.pause_elements = [self.settings_btn, self.resume_btn, self.return_btn]

    def _show_pause_menu(self):
        self.pause_menu.show()
        self.mouse_locked = False
        self._apply_mouse_lock()
        if self.hotbar_ui:
            self.hotbar_ui.hide()
        
        # Reset nav
        self.pause_nav_index = 1 # Default to Resume button
        self._update_pause_visuals()
        
        # Register input events
        self.accept("control-up", self._on_pause_nav, ["up"])
        self.accept("control-down", self._on_pause_nav, ["down"])
        self.accept("control-left", self._on_pause_nav, ["left"])
        self.accept("control-right", self._on_pause_nav, ["right"])
        self.accept("control-select", self._on_pause_select)
        # control-pause is already handled by toggle

    def _hide_pause_menu(self):
        self.pause_menu.hide()
        self.mouse_locked = True
        self._apply_mouse_lock()
        if self.hotbar_ui:
            self.hotbar_ui.show()
            
        # Unregister input events
        self.ignore("control-up")
        self.ignore("control-down")
        self.ignore("control-left")
        self.ignore("control-right")
        self.ignore("control-select")

    def _quit_game(self):
        """Quit the game."""
        # Save player data before quitting
        if self.player is not None and self.save_system is not None:
            self.save_system.save_player_data(self.player)
            print("[App] Player data saved on quit")
        # Exit the application
        base.userExit()

    def _return_to_title(self):
        """Return to the title screen, saving game state."""
        # Save player data before returning to title
        if self.player is not None and self.save_system is not None:
            try:
                self.save_system.save_player_data(self.player)
                print("[App] Player data saved on return to title")
                
                # Save screenshot
                if self.selected_world_folder:
                    try:
                        import os
                        screenshot_filename = "screenshot.png"
                        world_path = self.world_manager.get_world_path(self.selected_world_folder)
                        full_path = os.path.join(world_path, screenshot_filename)
                        
                        # 1. Disable input to prevent movement/interaction
                        self.ignoreAll()
                        
                        # 2. Hide UI elements for screenshot
                        if self.pause_menu: self.pause_menu.hide()
                        if self.hud_frame: self.hud_frame.hide()
                        if self.crosshair: self.crosshair.hide()
                        if self.hotbar_ui: self.hotbar_ui.hide()
                        if self.save_notification: self.save_notification.hide()
                        
                        # 3. Force multiple frame renders to ensure UI is cleared from buffer
                        for _ in range(3):
                            base.graphicsEngine.renderFrame()
                        
                        # 4. Save screenshot
                        if self.win and self.win.getGsg():
                            self.win.saveScreenshot(full_path)
                            print(f"[App] Saved screenshot to {full_path}")
                            
                            # Update world metadata
                            self.world_manager.save_screenshot(self.selected_world_folder, screenshot_filename)
                    except Exception as e:
                        print(f"[App] Warning: Failed to save screenshot: {e}")
            except Exception as e:
                print(f"[App] Error saving player data on return to title: {e}")

        # Clean up mobs and drops (Always clean up even if save fails)
        try:
            if self.mob_system:
                self.mob_system.cleanup()
                self.mob_system = None
            
            if self.drop_system:
                self.drop_system.cleanup()
                self.drop_system = None

            # Clean up the world properly - remove all chunks from render tree
            if self.world is not None:
                self.world.cleanup()
            
            # Now clear the references
            self.world = None
            self.player = None

            # Hide pause menu
            self.paused = False
            if self.pause_menu:
                self.pause_menu.hide()

            # Hide game UI elements
            if self.hotbar_ui:
                self.hotbar_ui.hide()
            if self.crosshair:
                self.crosshair.hide()
            if self.save_notification:
                self.save_notification.hide()
            if self.hud_frame:
                self.hud_frame.hide()

            # Show title screen
            if self.title_screen:
                self.title_screen.show()

            # Set title screen state
            self.in_title_screen = True
            self.game_ready = False
            self.mouse_locked = False
            self._apply_mouse_lock()
            
            # Re-register basic keys
            self.accept("escape", self._toggle_pause_menu) 
            self.accept("escape-up", self._check_exit)
            
            # Mouse input
            self.accept("mouse1", self._on_left_mouse_down)
            self.accept("mouse1-up", self._on_left_mouse_up)
            self.accept("mouse3", self._on_right_click)
            
            # Movement keys
            self.accept("w", self._set_key, ["forward", True])
            self.accept("w-up", self._set_key, ["forward", False])
            self.accept("s", self._set_key, ["back", True])
            self.accept("s-up", self._set_key, ["back", False])
            self.accept("a", self._set_key, ["left", True])
            self.accept("a-up", self._set_key, ["left", False])
            self.accept("d", self._set_key, ["right", True])
            self.accept("d-up", self._set_key, ["right", False])
            self.accept("space", self._set_key, ["jump", True])
            self.accept("space-up", self._set_key, ["jump", False])
            self.accept("shift", self._set_key, ["crouch", True])
            self.accept("shift-up", self._set_key, ["crouch", False])
            
            # Save/Load
            self.accept("f5", self._quicksave)
            self.accept("f9", self._quickload)
            self.accept("e", self._toggle_inventory)
            self.accept("wheel_up", self._scroll_hotbar, [-1])
            self.accept("wheel_down", self._scroll_hotbar, [1])

            # Remove the main update task to pause the game
            self.taskMgr.remove("update")

            # Stop auto-save if running
            self.taskMgr.remove("auto_save")
            
        except Exception as e:
             print(f"[App] Critical error during cleanup: {e}")
             # Try to return to title anyway
             if self.title_screen:
                self.title_screen.show()
             self.in_title_screen = True
             self.game_ready = False


    def _on_pause_nav(self, direction):
        if not self.paused: return
        
        if direction == "up":
            self.pause_nav_index = (self.pause_nav_index - 1) % len(self.pause_elements)
        elif direction == "down":
            self.pause_nav_index = (self.pause_nav_index + 1) % len(self.pause_elements)
                
        self._update_pause_visuals()
        
    def _on_pause_select(self):
        if not self.paused: return
        
        el = self.pause_elements[self.pause_nav_index]
        if isinstance(el, DirectButton):
            el.commandFunc(None)
            
    def _update_pause_visuals(self):
        for i, el in enumerate(self.pause_elements):
            if i == self.pause_nav_index:
                # Highlight
                if isinstance(el, DirectButton):
                    el.setScale(0.09)
                    el['frameColor'] = (0.3, 0.3, 0.9, 1)
            else:
                # Reset
                if isinstance(el, DirectButton):
                    el.setScale(0.08)
                    el['frameColor'] = (0.2, 0.2, 0.2, 1)

    def _on_left_mouse_down(self):
        # Left mouse button pressed
        # Don't block mining when crafting menu is open, but don't lock mouse either
        from voxel.crafting import crafting_menu
        
        if self.mouse_locked:
            self.left_mouse_down = True
        else:
            # Only lock mouse if game is running (not in title screen, paused, or crafting menu)
            crafting_menu_open = crafting_menu is not None and crafting_menu.is_open
            if (self.game_ready and
                not self.paused and
                not self.in_title_screen and
                not crafting_menu_open):  # Don't lock mouse if crafting menu is open
                self.mouse_locked = True
                self._apply_mouse_lock()

    def _on_left_mouse_up(self):
        # Left mouse button released
        self.left_mouse_down = False
        if hasattr(self, 'player') and self.player:
            self.player.reset_breaking()

    def _on_right_click(self):
        # Right click: interact with block (crafting table), eat food, or place block
        if self.mouse_locked:
            # Check for eating first
            slot = self.hotbar[self.selected_hotbar_slot]
            if slot:
                block_type = slot['block']
                # Meat items
                is_food = block_type in (ITEM_RAW_MEAT, ITEM_RAW_CHICKEN, ITEM_RAW_PORK)
                
                if is_food:
                    # Try to eat
                    # 10 hunger points = 20 units. Each meat gives say 4 units (2 full hunger points)
                    if self.player.hunger < self.player.max_hunger:
                        self.player.add_hunger(4.0, 2.0)
                        # Consume item (unless Creative)
                        if self.player.game_mode != "Creative":
                            slot['count'] -= 1
                            if slot['count'] <= 0:
                                self.hotbar[self.selected_hotbar_slot] = None
                        self._update_hotbar_ui()
                        # Optional: Play eating sound or animation
                        return

            # First check if looking at a crafting table
            hit = self.player.raycast_block(max_distance=5.0)
            if hit:
                wx, wy, wz = hit
                block_type = self.world.get_block(wx, wy, wz)
                if block_type == BLOCK_CRAFTING_TABLE:
                    # Open crafting table UI
                    self._open_crafting_table_ui()
                    return
            # Otherwise, place block
            self._place_block()

    def _center_mouse(self):
        if not self.win:
            return
        x = int(self.win.getProperties().getXSize() / 2)
        y = int(self.win.getProperties().getYSize() / 2)
        self.win.movePointer(0, x, y)

    def _handle_mouse(self, dt: float):
        if not self.mouse_locked:
            self.mouse_initialized = False
            self.skip_next_mouse_frame = False
            return
        
        # Wait for valid window and mouse data
        if not self.win or not self.mouseWatcherNode.hasMouse():
            return
        
        # Get window center
        cx = int(self.win.getProperties().getXSize() / 2)
        cy = int(self.win.getProperties().getYSize() / 2)
        
        # Initialize on first frame - center mouse and skip processing
        if not self.mouse_initialized:
            self.mouse_initialized = True
            self.win.movePointer(0, cx, cy)
            self.skip_next_mouse_frame = True
            return
        
        # Skip this frame if we just re-centered (prevents detecting re-center as movement)
        if self.skip_next_mouse_frame:
            self.skip_next_mouse_frame = False
            return
        
        # Get current mouse position
        mw = self.win.getPointer(0)
        mx = mw.getX()
        my = mw.getY()
        
        # Calculate delta from center
        dx = mx - cx
        dy = my - cy
        
        # Clamp delta to prevent excessive rotation
        max_delta = 100
        if abs(dx) > max_delta:
            dx = max_delta if dx > 0 else -max_delta
        if abs(dy) > max_delta:
            dy = max_delta if dy > 0 else -max_delta
        
        # Process movement if significant (deadzone prevents jitter)
        if abs(dx) > 2 or abs(dy) > 2:
            self.player.add_look(dx, dy)
        
        # Re-center mouse for next frame
        self.win.movePointer(0, cx, cy)
        # CRITICAL: Skip next frame to avoid processing the re-center as movement
        self.skip_next_mouse_frame = True

    def _create_crosshair(self):
        # Create a simple crosshair using LineSegs
        crosshair_size = 0.02
        crosshair_thickness = 2
        
        # Create line segments for crosshair
        ls = LineSegs()
        ls.setThickness(crosshair_thickness)
        ls.setColor(1, 1, 1, 0.8)  # white with slight transparency
        
        # Horizontal line
        ls.moveTo(-crosshair_size, 0, 0)
        ls.drawTo(crosshair_size, 0, 0)
        
        # Vertical line
        ls.moveTo(0, 0, -crosshair_size)
        ls.drawTo(0, 0, crosshair_size)
        
        # Create node and attach to aspect2d (2D overlay)
        crosshair_node = ls.create()
        self.crosshair = self.aspect2d.attachNewNode(crosshair_node)

    def _create_break_overlay(self):
        """Create a visual overlay for block breaking animation."""
        self.break_overlay = DirectFrame(
            frameColor=(0, 0, 0, 0),
            frameSize=(-0.08, 0.08, -0.08, 0.08),
            pos=(0, 0, 0),
            parent=self.aspect2d
        )
        self.break_overlay.hide()
    
    def _create_status_hud(self):
        """Create Health and Hunger HUD."""
        # Main frame above hotbar
        self.hud_frame = DirectFrame(
            frameColor=(0, 0, 0, 0),
            frameSize=(-0.9, 0.9, 0, 0.1),
            pos=(0, 0, -0.75),
            parent=self.aspect2d
        )
        
        # Create 10 hearts (left side)
        # Each heart is 2 health points (20 max health)
        for i in range(10):
            # Background (empty heart container)
            bg = DirectFrame(
                frameColor=(0.2, 0, 0, 0.5),
                frameSize=(-0.03, 0.03, -0.03, 0.03),
                pos=(-0.35 + i * 0.07, 0, 0.05),
                parent=self.hud_frame
            )
            # Foreground (filled heart) - will be scaled/colored
            fg = DirectFrame(
                frameColor=(0.8, 0.1, 0.1, 1),
                frameSize=(-0.025, 0.025, -0.025, 0.025),
                pos=(0, 0, 0),
                parent=bg
            )
            self.hearts_ui.append(fg)

        # Create 10 hunger points (right side)
        # Each hunger point is 2 hunger units (20 max hunger)
        for i in range(10):
            # Reverse index for right-to-left filling or left-to-right? 
            # MC does right-to-left from center, let's do left-to-right from center-right.
            # Actually, let's mirror hearts: starts at 0.35 and goes right?
            # Let's start at 0.35 and go right.
            
            # Background
            bg = DirectFrame(
                frameColor=(0.2, 0.1, 0, 0.5),
                frameSize=(-0.03, 0.03, -0.03, 0.03),
                pos=(0.35 - i * 0.07, 0, 0.05), # Grow inwards or outwards?
                # Hearts: -0.35 + i*0.07 -> -0.35, -0.28... -> Grows right towards center? No, -0.35 is left of center.
                # -0.9 is left edge.
                # Let's position hearts on left (-0.8 to -0.1) and hunger on right (0.1 to 0.8)?
                # Hotbar is -0.9 to 0.9.
                # Hearts at -0.4 start, going left?
                # Standard MC: Hearts left of hotbar center, Hunger right of hotbar center.
                # Hotbar center is 0.
                # Hearts: -0.5 to -0.1?
                parent=self.hud_frame
            )
            # Adjust hearts pos
            # Let's redo positions in update or init properly.
            
            # Foreground (filled hunger)
            fg = DirectFrame(
                frameColor=(0.6, 0.4, 0.1, 1),
                frameSize=(-0.025, 0.025, -0.025, 0.025),
                pos=(0, 0, 0),
                parent=bg
            )
            self.hunger_ui.append(fg)
            
        # Reposition for clarity
        # Hearts: Left side, index 0 is left-most usually.
        # Let's put hearts at x = -0.8 + i * 0.05 (compact)
        for i, heart in enumerate(self.hearts_ui):
             heart.getParent().setPos(-0.5 + i * 0.045, 0, 0.05)
             
        # Hunger: Right side, index 0 is right-most or left-most?
        # Usually mirror hearts.
        for i, hunger in enumerate(self.hunger_ui):
             hunger.getParent().setPos(0.5 - i * 0.045, 0, 0.05)
             
        self.hud_frame.hide() # Hide until game starts

    def _update_hud(self):
        """Update HUD elements based on player stats."""
        if not self.player:
            return
        
        # Hide HUD in Creative Mode
        if self.player.game_mode == "Creative":
            if self.hud_frame:
                self.hud_frame.hide()
            return
            
        # Update Hearts
        # Health 0-20. 10 hearts.
        # i=0 is first heart (left).
        # If health = 20, all full.
        # If health = 19, last heart (i=9) is half.
        # If health = 18, last heart (i=9) is empty.
        # Wait, i=9 is right-most heart. 
        
        # Logic:
        # Heart i represents health interval [2*i, 2*i+2]
        # If health >= 2*i + 2: Full
        # If health >= 2*i + 1: Half
        # Else: Empty
        
        for i, heart in enumerate(self.hearts_ui):
            threshold_full = (i + 1) * 2
            threshold_half = threshold_full - 1
            
            if self.player.health >= threshold_full:
                heart.show()
                heart['frameColor'] = (0.8, 0.1, 0.1, 1) # Full Red
                heart.setScale(1.0)
            elif self.player.health >= threshold_half:
                heart.show()
                heart['frameColor'] = (0.8, 0.1, 0.1, 1) # Red
                # Half heart visual (hacky: scale x by 0.5 and move)
                heart.setScale(0.5, 1, 1)
                heart.setX(-0.0125) # Shift left to look like left half
            else:
                heart.hide() # Empty

        # Update Hunger
        # Same logic
        for i, hunger in enumerate(self.hunger_ui):
            threshold_full = (i + 1) * 2
            threshold_half = threshold_full - 1
            
            if self.player.hunger >= threshold_full:
                hunger.show()
                hunger['frameColor'] = (0.6, 0.4, 0.1, 1) # Brown
                hunger.setScale(1.0)
                hunger.setX(0)
            elif self.player.hunger >= threshold_half:
                hunger.show()
                hunger['frameColor'] = (0.6, 0.4, 0.1, 1)
                hunger.setScale(0.5, 1, 1)
                hunger.setX(0.0125) # Shift right to look like right half (mirror of heart) or just half
            else:
                hunger.hide()

    def _update_break_overlay(self, stage: int):
        """Update the break overlay based on the break stage (0-9)."""
        if stage <= 0:
            self.break_overlay.hide()
            return
        
        # Show overlay with intensity based on stage
        # Create a cracking pattern using lines
        self.break_overlay.show()
        
        # Calculate alpha based on stage (darker as more broken)
        alpha = 0.2 + (stage / 10.0) * 0.6
        
        # Update the frame color to show damage (dark overlay)
        self.break_overlay['frameColor'] = (0, 0, 0, alpha * 0.3)

    def _create_hotbar(self):
        """Create the hotbar UI at the bottom of the screen."""
        # Create hotbar container
        self.hotbar_ui = DirectFrame(
            frameColor=(0, 0, 0, 0),
            frameSize=(-0.9, 0.9, -0.15, 0.05),
            pos=(0, 0, -0.85),
            parent=self.aspect2d
        )
        
        # Create individual hotbar slots
        self.hotbar_slots = []
        slot_width = 0.18
        start_x = -0.8
        
        for i in range(self.hotbar_size):
            # Slot background
            slot_frame = DirectFrame(
                frameColor=(0.9, 0.9, 0.9, 0.9) if i == self.selected_hotbar_slot else (0.3, 0.3, 0.3, 0.8),
                frameSize=(-slot_width / 2, slot_width / 2, -0.1, 0.1),
                pos=(start_x + i * slot_width, 0, -0.05),
                parent=self.hotbar_ui
            )
            
            # Block indicator (initially empty/transparent) - will hold texture image
            block_indicator = DirectFrame(
                frameColor=(0, 0, 0, 0),
                frameSize=(-0.06, 0.06, -0.06, 0.06),
                pos=(0, 0, 0.03),
                parent=slot_frame
            )
            block_indicator.setTransparency(TransparencyAttrib.MAlpha)
            
            # Block count / name label (starts empty)
            name_label = DirectLabel(
                text="",
                scale=0.035,
                pos=(0, 0, -0.04),
                text_fg=(1, 1, 1, 1),
                frameColor=(0, 0, 0, 0),
                parent=slot_frame
            )
            
            # Slot number label
            number_label = DirectLabel(
                text=str(i + 1),
                scale=0.035,
                pos=(0, 0, 0.08),
                text_fg=(0.8, 0.8, 0.8, 1),
                frameColor=(0, 0, 0, 0),
                parent=slot_frame
            )
            
            self.hotbar_slots.append({
                'frame': slot_frame,
                'indicator': block_indicator,
                'name': name_label,
                'number': number_label
            })
    
    def _get_item_texture(self, block_id):
        """Get the texture for a given block/item ID."""
        # Get texture manager (must be called after world is initialized)
        from voxel.chunk import (
            get_texture_manager,
            BLOCK_STICKS, BLOCK_PICKAXE_WOOD, BLOCK_PICKAXE_STONE, BLOCK_PICKAXE_IRON,
            BLOCK_AXE_WOOD, BLOCK_AXE_STONE, BLOCK_AXE_IRON,
            BLOCK_SHOVEL_WOOD, BLOCK_SHOVEL_STONE, BLOCK_SHOVEL_IRON,
            BLOCK_SWORD_WOOD, BLOCK_SWORD_STONE, BLOCK_SWORD_IRON
        )
        from voxel.texture_manager import BLOCK_TEXTURES
        
        texture_manager = get_texture_manager()
        if not texture_manager:
            return None
        
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
            return texture_manager.load_texture(category, f'{name}.png')
        
        # Check if it's meat
        if block_id in meat_map:
            category, name = meat_map[block_id]
            return texture_manager.load_texture(category, f'{name}.png')
        
        # Check if it's a block
        if block_id in BLOCK_TEXTURES:
            texture_name = BLOCK_TEXTURES[block_id]
            return texture_manager.get_block_texture(texture_name)
        
        return None
    
    def _update_hotbar_ui(self):
        """Sync hotbar UI with stored items."""
        if not hasattr(self, "hotbar_slots"):
            return
        
        for i, slot in enumerate(self.hotbar_slots):
            data = self.hotbar[i]
            
            # Highlight selection
            if i == self.selected_hotbar_slot:
                slot['frame']['frameColor'] = (0.9, 0.9, 0.9, 0.9)
            else:
                slot['frame']['frameColor'] = (0.3, 0.3, 0.3, 0.8)
            
            if data is None:
                # Empty slot - remove image if exists
                if i in self.hotbar_images:
                    self.hotbar_images[i].destroy()
                    del self.hotbar_images[i]
                slot['indicator']['frameColor'] = (0, 0, 0, 0)
                slot['name']['text'] = ""
            else:
                block_id = data['block']
                count = data['count']
                
                # Get texture for this item
                texture = self._get_item_texture(block_id)
                
                if texture:
                    # Remove old image if exists
                    if i in self.hotbar_images:
                        self.hotbar_images[i].destroy()
                    
                    # Make indicator transparent
                    slot['indicator']['frameColor'] = (0, 0, 0, 0)
                    
                    # Create new OnscreenImage with texture
                    img = OnscreenImage(
                        image=texture,
                        scale=(0.06, 1, 0.06),
                        parent=slot['indicator']
                    )
                    img.setTransparency(TransparencyAttrib.MAlpha)
                    self.hotbar_images[i] = img
                
                # Update count label
                slot['name']['text'] = str(count)
    
    def _scroll_hotbar(self, direction):
        """Scroll through hotbar slots. Direction: -1 for up (left), 1 for down (right)."""
        if not self.game_ready:
            return
        
        # Update selected slot
        self.selected_hotbar_slot = (self.selected_hotbar_slot + direction) % self.hotbar_size
        self._update_hotbar_ui()
    
    def _create_save_notification(self):
        """Create the save notification label."""
        self.save_notification = DirectLabel(
            text="",
            scale=0.08,
            pos=(0, 0, -0.65),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.aspect2d
        )
        self.save_notification.hide()

    def _show_notification(self, message: str, duration: float = 2.0):
        """Show a temporary notification message."""
        self.save_notification['text'] = message
        self.save_notification.show()
        # Schedule hiding the notification
        self.taskMgr.doMethodLater(duration, self._hide_notification, "hide_notification")

    def _hide_notification(self, task=None):
        """Hide the notification."""
        self.save_notification.hide()
        if task:
            return Task.done

    def _quicksave(self):
        """Quick save the game (F5)."""
        if not self.game_ready or self.paused:
            return
        
        success = self.save_system.save_game(self.player, self.world, "quicksave")
        if success:
            self._show_notification("Game Saved (F5)")
        else:
            self._show_notification("Save Failed!", duration=3.0)

    def _quickload(self):
        """Quick load the game (F9)."""
        if not self.game_ready or self.paused:
            return

        success = self.save_system.load_game(self.player, self.world, "quicksave")
        if success:
            self._show_notification("Game Loaded (F9)")
            # Force re-mesh of all loaded chunks
            for chunk in self.world.chunks.values():
                chunk.dirty = True
            # Reset mouse state to prevent camera drift after load
            self.mouse_initialized = False
            self._center_mouse()
        else:
            self._show_notification("Load Failed - No Save Found!", duration=3.0)

    def _toggle_inventory(self):
        """Toggle the inventory UI."""
        if not self.game_ready or self.paused:
            return
        
        # Use Creative Inventory in Creative Mode
        if self.player.game_mode == "Creative":
            if not hasattr(self, 'creative_inventory_ui') or self.creative_inventory_ui is None:
                from voxel.creative_inventory_ui import CreativeInventoryUI
                self.creative_inventory_ui = CreativeInventoryUI(self)
                self.creative_inventory_ui.create()
            
            if self.creative_inventory_ui.is_open:
                self.creative_inventory_ui.close()
            else:
                self.creative_inventory_ui.open()
        else:
            # Use normal Survival Inventory
            if self.inventory_ui:
                self.inventory_ui.toggle()
    
    def _open_crafting_table_ui(self):
        """Open 3x3 crafting table UI when right-clicking a crafting table."""
        if not self.game_ready or self.paused:
            return
        
        # Import crafting table UI
        if not hasattr(self, 'crafting_table_ui') or self.crafting_table_ui is None:
            from voxel.inventory_ui import CraftingTableUI
            self.crafting_table_ui = CraftingTableUI(self)
        
        self.crafting_table_ui.open()

    def _add_block_to_hotbar(self, block_type: int):
        """Add a mined block to the hotbar, stacking where possible."""
        if block_type in (BLOCK_BEDROCK,):
            return  # Don't collect bedrock or invalid
        
        # Stack onto existing slot
        for slot in self.hotbar:
            if slot is not None and slot['block'] == block_type:
                slot['count'] += 1
                self._update_hotbar_ui()
                return
        
        # Put into first empty slot
        for i in range(self.hotbar_size):
            if self.hotbar[i] is None:
                self.hotbar[i] = {'block': block_type, 'count': 1}
                self._update_hotbar_ui()
                return
        # If full, silently drop (could show message if desired)
    
    def _mine_block(self):
        # Raycast from camera to find block to mine
        hit = self.player.raycast_block(max_distance=5.0)
        if hit:
            wx, wy, wz = hit
            block_type = self.world.get_block(wx, wy, wz)
            if self.world.remove_block(wx, wy, wz):
                # Persist this chunk's modification immediately
                self.save_system.save_block_edit(self.world, wx, wy, wz)
                # Also save player data (position, inventory)
                self.save_system.save_player_data(self.player)
                self._add_block_to_hotbar(block_type)

    def _place_block(self):
        # Raycast from camera to find where to place block
        hit = self.player.raycast_block(max_distance=5.0, return_previous=True)
        if hit:
            wx, wy, wz = hit
            # Don't place block if it would intersect with player
            if not self.player.intersects_position(wx, wy, wz):
                slot = self.hotbar[self.selected_hotbar_slot]
                if slot is None:
                    return  # nothing to place
                block_type = slot['block']
                
                # Check if item is placeable (tools, weapons, and items are not placeable)
                if block_type in (
                    # Meat items
                    ITEM_RAW_MEAT, ITEM_RAW_CHICKEN, ITEM_RAW_PORK,
                    # Tools and weapons
                    BLOCK_STICKS,
                    BLOCK_PICKAXE_WOOD, BLOCK_PICKAXE_STONE,
                    BLOCK_AXE_WOOD, BLOCK_AXE_STONE,
                    BLOCK_SHOVEL_WOOD, BLOCK_SHOVEL_STONE,
                    BLOCK_SWORD_WOOD, BLOCK_SWORD_STONE
                ):
                    # Can't place tools, weapons, or items
                    return
                
                if self.world.place_block(wx, wy, wz, block_type=block_type):
                    # Persist this chunk's modification immediately
                    self.save_system.save_block_edit(self.world, wx, wy, wz)
                    # Also save player data (position, inventory)
                    self.save_system.save_player_data(self.player)
                    #  Consume one from hotbar (unless Creative)
                    if self.player.game_mode != "Creative":
                        slot['count'] -= 1
                        if slot['count'] <= 0:
                            self.hotbar[self.selected_hotbar_slot] = None
                    self._update_hotbar_ui()

    def _setup_fog(self):
        """Setup exponential fog for render distance fade effect."""
        fog = Fog("render_distance_fog")
        fog.setColor(*settings.FOG_COLOR[:3])  # Use RGB only (no alpha)
        fog.setExpDensity(0.08)  # Exponential fog density
        self.render.setFog(fog)
    
    def _create_loading_screen(self):
        """Create loading screen overlay."""
        self.loading_screen = DirectFrame(
            frameColor=(0.1, 0.1, 0.1, 1.0),
            frameSize=(-1, 1, -1, 1),
            parent=self.aspect2d
        )
        
        # Title
        DirectLabel(
            text="Loading World...",
            scale=0.12,
            pos=(0, 0, 0.3),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.loading_screen
        )
        
        # Progress label
        self.loading_label = DirectLabel(
            text="Generating terrain...",
            scale=0.07,
            pos=(0, 0, 0),
            text_fg=(0.8, 0.8, 0.8, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.loading_screen
        )
        
        # Instructions
        DirectLabel(
            text="Please wait while the world loads",
            scale=0.05,
            pos=(0, 0, -0.3),
            text_fg=(0.6, 0.6, 0.6, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.loading_screen
        )
    
    def _show_loading_screen(self):
        """Show the loading screen."""
        if self.loading_screen:
            self.loading_screen.show()
        if self.hud_frame:
            self.hud_frame.hide()
    
    def _hide_loading_screen(self):
        """Hide the loading screen."""
        if self.loading_screen:
            self.loading_screen.hide()
        if self.hud_frame:
            self.hud_frame.show()
    
    def _preload_world(self, task):
        """Preload world chunks around spawn before starting game."""
        import random
        from voxel.util import set_world_seed
        
        # Check if a world save exists
        saved_seed = self.save_system.load_world_seed()
        
        if saved_seed is not None:
            # Load existing world with saved seed
            self.loading_label['text'] = f"Loading existing world (Seed: {saved_seed})..."
            set_world_seed(saved_seed)
        else:
            # Generate a new random seed for a fresh world
            new_seed = random.randint(0, 999999999)
            self.loading_label['text'] = f"Generating new world (Seed: {new_seed})..."
            set_world_seed(new_seed)
            # Save the seed immediately so we can reload this world
            self.save_system.save_world_seed(new_seed)
        
        # Initialize world and player
        self.world = World(self.render, self.save_system)
        self.player = Player(self.camera, self.world)
        # Link back so SaveSystem can access hotbar via player.app
        self.player.app = self
        
        # Initialize drop and mob systems
        self.drop_system = DropSystem(self.render, self.world)
        # Default difficulty for legacy load
        self.mob_system = MobSystem(self.render, self.world, self.drop_system, settings.DIFFICULTY_NORMAL)
        
        # Clear hotbar and inventory before loading new world data
        self.hotbar = [None for _ in range(self.hotbar_size)]
        self.inventory = [None] * 27
        self.selected_hotbar_slot = 0
        self._update_hotbar_ui()
        
        # Try to load saved player data (position, inventory)
        if self.save_system.load_player_data(self.player):
            self.loading_label['text'] = "Loading saved player data..."
        
        # Update loading label
        self.loading_label['text'] = "Loading chunks..."
        
        # Preload all chunks around player spawn position
        chunks_created, chunks_meshed = self.world.preload_chunks_around(
            self.player.position.x,
            self.player.position.z
        )
        
        # Update loading label with results
        self.loading_label['text'] = f"Loaded {chunks_created} chunks, meshed {chunks_meshed} chunks"
        
        # Wait a brief moment to show completion message
        self.taskMgr.doMethodLater(0.5, self._start_game, "start_game")
        return Task.done

    def _show_world_selection(self):
        """Show world selection menu."""
        if self.title_screen:
            self.title_screen.hide()
        if self.world_selection_menu:
            self.world_selection_menu.show()
    
    def _show_settings_menu(self, source="title"):
        """Show settings menu."""
        if self.title_screen:
            self.title_screen.hide()
        if self.pause_menu:
            self.pause_menu.hide()
        if self.settings_menu:
            self.settings_menu.show(source=source)
    
    def _start_game_with_world(self, world_folder: str):
        """Start game with a specific world folder."""
        # Update save system to use the world-specific folder
        world_path = self.world_manager.get_world_path(world_folder)
        self.save_system = SaveSystem(save_dir=world_path)
        
        # Store the selected world folder
        self.selected_world_folder = world_folder
        
        # Hide menus and start game
        self.in_title_screen = False
        self._show_loading_screen()
        self.taskMgr.doMethodLater(0.1, self._preload_world_from_folder, "preload", extraArgs=[world_folder])
    
    def _preload_world_from_folder(self, world_folder: str, task=None):
        """Preload world from specific folder."""
        from voxel.util import set_world_seed
        
        # Get world info
        world_info = self.world_manager.get_world(world_folder)
        if not world_info:
            print(f"[App] Error: World folder '{world_folder}' not found!")
            return Task.done
        
        # Set the seed for this world
        self.loading_label['text'] = f"Loading world '{world_info.name}' (Seed: {world_info.seed})..."
        set_world_seed(world_info.seed)
        
        # Initialize world and player
        self.world = World(self.render, self.save_system)
        game_mode = world_info.game_mode
        self.player = Player(self.camera, self.world, game_mode=game_mode)
        # Link back so SaveSystem can access hotbar via player.app
        self.player.app = self
        print(f"[App] Player initialized in {game_mode} mode")
        
        # Initialize drop and mob systems
        self.drop_system = DropSystem(self.render, self.world)
        difficulty = world_info.difficulty if hasattr(world_info, 'difficulty') else settings.DIFFICULTY_NORMAL
        self.mob_system = MobSystem(self.render, self.world, self.drop_system, difficulty)
        
        # Clear hotbar and inventory before loading new world data
        self.hotbar = [None for _ in range(self.hotbar_size)]
        self.inventory = [None] * 27
        self.selected_hotbar_slot = 0
        self._update_hotbar_ui()
        
        # Try to load saved player data (position, inventory)
        if self.save_system.load_player_data(self.player):
            self.loading_label['text'] = "Loading saved player data..."
        
        # Update loading label
        self.loading_label['text'] = "Loading chunks..."
        
        # Preload all chunks around player spawn position
        chunks_created, chunks_meshed = self.world.preload_chunks_around(
            self.player.position.x,
            self.player.position.z
        )
        
        # Update loading label with results
        self.loading_label['text'] = f"Loaded {chunks_created} chunks, meshed {chunks_meshed} chunks"
        
        # Wait a brief moment to show completion message
        self.taskMgr.doMethodLater(0.5, self._start_game, "start_game")
        return Task.done

    def _start_title_game(self):
        """Start game from title screen (legacy - now uses world selection)."""
        if self.title_screen:
            self.title_screen.hide()
        self.in_title_screen = False
        self._show_loading_screen()
        self.taskMgr.doMethodLater(0.1, self._preload_world, "preload")

    def _delete_save_data(self):
        """Delete all save data (player and chunks)."""
        import os
        import shutil
        import time

        try:
            # First unload world to ensure files are closed
            if hasattr(self, 'world') and self.world:
                # Properly clean up the world - remove all chunks from render tree
                self.world.cleanup()
                # Clear the references
                self.world = None
                self.player = None
                import gc
                gc.collect()  # Force garbage collection
                time.sleep(0.2)  # Give OS time to release file handles

            # Clear hotbar data
            self.hotbar = [None for _ in range(self.hotbar_size)]
            self.selected_hotbar_slot = 0
            if hasattr(self, 'hotbar_ui'):
                self._update_hotbar_ui()

            # Delete player data
            player_file = os.path.join("saves", "player.json")
            if os.path.exists(player_file):
                try:
                    os.remove(player_file)
                    print("[App] Deleted player.json")
                except Exception as e:
                    print(f"[App] Warning: Could not delete player.json: {e}")

            # Delete world metadata (seed)
            world_file = os.path.join("saves", "world.json")
            if os.path.exists(world_file):
                try:
                    os.remove(world_file)
                    print("[App] Deleted world.json (seed)")
                except Exception as e:
                    print(f"[App] Warning: Could not delete world.json: {e}")

            # Delete all chunk data - use more robust approach for Windows
            chunks_dir = os.path.join("saves", "chunks")
            if os.path.exists(chunks_dir):
                deleted_count = 0
                failed_files = []
                
                # Delete all files in the directory
                try:
                    file_list = os.listdir(chunks_dir)
                except Exception as e:
                    print(f"[App] Warning: Could not list chunk files: {e}")
                    file_list = []
                
                for filename in file_list:
                    file_path = os.path.join(chunks_dir, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            deleted_count += 1
                        elif os.path.isdir(file_path):
                            # Remove subdirectories if any
                            shutil.rmtree(file_path, ignore_errors=True)
                    except Exception as e:
                        failed_files.append(filename)
                        print(f"[App] Warning: Could not delete {filename}: {e}")
                
                if deleted_count > 0:
                    print(f"[App] Deleted {deleted_count} chunk files")
                
                # Give Windows extra time to release handles
                time.sleep(0.1)
                
                # Try to remove and recreate the directory
                try:
                    if not os.listdir(chunks_dir):  # Only if empty
                        os.rmdir(chunks_dir)
                        print("[App] Removed chunks directory")
                        # Recreate it
                        os.makedirs(chunks_dir)
                        print("[App] Recreated chunks directory")
                    elif failed_files:
                        print(f"[App] Warning: {len(failed_files)} files could not be deleted")
                    else:
                        print("[App] Chunks directory emptied successfully")
                except Exception as e:
                    # On Windows, directory may still be locked - just ensure it exists
                    if not os.path.exists(chunks_dir):
                        os.makedirs(chunks_dir, exist_ok=True)
                        print("[App] Recreated chunks directory")
                    else:
                        print(f"[App] Chunks directory exists (some Windows locks may persist)")
            else:
                # Create chunks directory if it doesn't exist
                os.makedirs(chunks_dir, exist_ok=True)
                print("[App] Created chunks directory")

            # Reinitialize the save system to clear any cached data
            self.save_system = SaveSystem()
            print("[App] Reinitialized save system")

            print("[App] Save data deletion complete!")

        except Exception as e:
            print(f"[App] Error deleting save data: {e}")

    def _quit_title_game(self):
        """Quit from title screen."""
        base.userExit()

    def _start_game(self, task=None):
        """Start the actual game after loading."""
        self.game_ready = True
        self._hide_loading_screen()
        self.crosshair.show()
        self.hotbar_ui.show()

        # Lock mouse for FPS controls
        self.mouse_locked = True
        self._apply_mouse_lock()

        # Reset mouse state for proper initialization
        self.mouse_initialized = False

        # Register the main update task (THIS IS CRITICAL!)
        self.taskMgr.add(self._update, "update")

        # Start auto-save task every 5 seconds
        self.taskMgr.doMethodLater(5.0, self._auto_save_player, "auto_save")
        if task:
            return Task.done

    def _auto_save_player(self, task):
        """Periodically save player position (every 5 seconds)."""
        if self.player is not None and self.save_system is not None and self.game_ready:
            self.save_system.save_player_data(self.player)
        # Repeat every 5 seconds
        return Task.again

    def _handle_controller(self, dt):
        """Handle controller input for gameplay."""
        if not self.input_handler or not self.input_handler.gamepad:
            self.controller_move_vec = (0.0, 0.0)
            return
            
        # Get state
        state = self.input_handler.state
        
        # Movement (Left Stick)
        move_x, move_y = self.input_handler.get_move()
        
        # Don't move if inventory is open
        if hasattr(self, 'inventory_ui') and self.inventory_ui.is_open:
            move_x, move_y = 0.0, 0.0
            
        self.controller_move_vec = (move_x, move_y)
        
        # Look (Right Stick)
        look_x, look_y = self.input_handler.get_look()
        if abs(look_x) > 0.1 or abs(look_y) > 0.1:
            # Sensitivity for controller
            # Mouse sensitivity is usually pixels, here we have normalized (0-1) * time
            # So we need a speed factor.
            # Say 120 degrees per second max rotation?
            # settings.MOUSE_SENSITIVITY is 0.15 degrees per pixel.
            # We want degrees.
            turn_speed = 1500.0 # degrees per second? Trial and error.
            
            # Invert Y usually?
            # Player.add_look subtracts dy, so positive dy looks up (pitch decreases). 
            # Stick Up is usually negative in some APIs, but let's assume Up is negative (standard visual Y) or positive?
            # In InputHandler we kept it raw. 
            # Standard: Up is -1 on Y axis? No, DirectInput/XInput varies.
            # Let's assume Panda3D: Up is 1.0? 
            # If look_y > 0 (Up), we want to look Up. 
            # Player.add_look: pitch -= dy * sens.
            # So positive dy -> negative pitch -> look up? No, negative pitch is down usually?
            # Let's check: pitch -= dy. If dy is positive, pitch decreases. 
            # Class Player: pitch > MAX_PITCH (90). 
            # Typically pitch +90 is up, -90 is down.
            # So to look up (increase pitch), we need negative dy.
            # If Stick Up is +1, and we want +pitch, we need to subtract negative.
            # So pass -look_y?
            
            # Let's use pixels equivalent for add_look to keep it consistent?
            # add_look expects "pixels".
            # Let's synthesize pixels: speed * val * dt
            pixels_x = look_x * turn_speed * dt 
            pixels_y = look_y * turn_speed * dt 
            # Invert Y axis for controller typically
            self.player.add_look(pixels_x, -pixels_y ) 

        # Actions
        # Jump (edge-triggered in InputHandler, so only True for one frame)
        # We don't set self.keys["jump"] here to avoid mixing with keyboard input
        
        # Inventory (edge detection now handled in InputHandler)
        if state["inventory"]:
            self._toggle_inventory()
            
        # Pause (edge detection now handled in InputHandler)
        if state["pause"]:
            self._toggle_pause_menu()
            
        # Hotbar scrolling (Bumpers)
        # InputHandler already provides edge-detected button states
        # state["bumper_l"] and state["bumper_r"] are only True for one frame when pressed
        if state["bumper_l"]:
            self._scroll_hotbar(-1)
        
        if state["bumper_r"]:
            self._scroll_hotbar(1)
            
        # Mining / Placing (Triggers)
        # Left Trigger: Place / Interact (Right Click equivalent)
        if state["trigger_l"] > 0.5:
            if not getattr(self, "_last_trigger_l", False):
                 self._on_right_click() # Once per press
        self._last_trigger_l = state["trigger_l"] > 0.5
        
        # Right Trigger: Mine / Attack (Left Click equivalent)
        # Continuous 
        if state["trigger_r"] > 0.5:
             self.left_mouse_down = True
             # Also override mouse lock if we are using controller
             if not self.mouse_locked and self.game_ready and not self.paused:
                 self.mouse_locked = True
                 self._apply_mouse_lock()
        else:
             # Only release if mouse is also not pressed
             if not self.mouseWatcherNode.isButtonDown("mouse1"):
                 self.left_mouse_down = False
                 
    def _update(self, task: Task):
        # Don't update game logic when paused or not ready
        if self.paused or not self.game_ready:
            return Task.cont
            
        dt = globalClock.getDt()
        # Cap dt to avoid tunneling on low FPS spikes
        if dt > 0.05:
            dt = 0.05

        self._handle_mouse(dt)
        self._handle_controller(dt)
        
        # Store move vec from keys if no controller input for fallback?
        # No, passing both keys and move_vec to Player.update handles it priority?
        # modified Player.update takes move_vec. If it's None, uses keys.
        # We should pass controller_move_vec if magnitude > 0, else None?
        # Or pass it and let Player handle mixing?
        # Player.update implementation: if move_vec: use it. else: use keys.
        # So if we have any controller input, we pass it.
        # But stick might be (0,0). If so, we might want keyboard.
        # So pass None if magnitude is small.
        
        move_input = None
        if hasattr(self, 'controller_move_vec'):
             mx, my = self.controller_move_vec
             if abs(mx) > 0.1 or abs(my) > 0.1:
                 move_input = self.controller_move_vec
        
        # Merge inputs for actions that Player.update expects in 'keys'
        current_keys = self.keys.copy()
        # Add controller jump input (edge-triggered, only True for single frame)
        # Check if inventory is closed
        inventory_open = hasattr(self, 'inventory_ui') and self.inventory_ui.is_open
        if self.input_handler and self.input_handler.state["jump"] and not inventory_open:
            current_keys["jump"] = True
        else:
            # Explicitly set to False if controller jump is not pressed
            # This prevents the jump from "sticking" if keyboard was used previously
            if not self.keys.get("jump", False):
                current_keys["jump"] = False
                 
        # Handle combat and block breaking
        if self.left_mouse_down:
            # First check if player is looking at a mob (mobs have priority over blocks)
            mob_hit = False
            if self.mob_system:
                # Get camera direction
                cam_quat = self.camera.getQuat()
                forward_panda = cam_quat.xform(Vec3(0, 1, 0))
                # Convert to world coords
                ray_dir = Vec3(forward_panda.x, forward_panda.z, forward_panda.y)
                ray_origin = Vec3(
                    self.player.position.x,
                    self.player.position.y + settings.PLAYER_EYE_OFFSET,
                    self.player.position.z
                )
                
                # Check for mob hit
                hit_mob = self.mob_system.raycast_mob(ray_origin, ray_dir, max_distance=5.0)
                if hit_mob:
                    mob_hit = True
                    # Attack mob (2.0 damage per hit)
                    if hit_mob.damage(2.0):
                        # Mob died, it will drop items automatically in mob_system.update()
                        pass
            
            # If no mob hit, try breaking blocks
            if not mob_hit:
                hit = self.player.raycast_block(max_distance=5.0)
                if hit:
                    wx, wy, wz = hit
                    block_type = self.world.get_block(wx, wy, wz)
                    
                    # Start or continue breaking
                    self.player.start_breaking(hit, block_type)
                    
                    # Update breaking progress
                    if self.player.update_breaking(dt):
                        # Block is broken: remove it from world first, then spawn drop
                        if self.world.remove_block(wx, wy, wz):
                            # Persist this chunk's modification immediately
                            self.save_system.save_block_edit(self.world, wx, wy, wz)
                            # Also save player data (position, inventory)
                            self.save_system.save_player_data(self.player)
                            
                            # Spawn drop at block position
                            if self.drop_system and block_type not in (BLOCK_BEDROCK,):
                                drop_pos = Vec3(wx + 0.5, wy + 0.5, wz + 0.5)
                                self.drop_system.spawn_drop(block_type, drop_pos)
                        self._update_break_overlay(0)
                    else:
                        # Update visual feedback
                        stage = self.player.get_break_stage()
                        self._update_break_overlay(stage)
                else:
                    # Not looking at anything, reset breaking
                    self.player.reset_breaking()
                    self._update_break_overlay(0)
            else:
                # Hit a mob, reset block breaking
                self.player.reset_breaking()
                self._update_break_overlay(0)
        else:
            # Mouse not pressed, hide overlay
            self.player.reset_breaking()
            self._update_break_overlay(0)
        
        self.player.update(current_keys, dt, move_input)
        self.world.update(self.player.position)
        
        # Update drop system (handles item physics and collection)
        if self.drop_system:
            collected_items = self.drop_system.update(dt, self.player.position)
            # Add collected items to hotbar
            for item_type in collected_items:
                self._add_block_to_hotbar(item_type)
        
        # Update Day/Night Cycle
        self.day_time += dt
        if self.day_time >= self.day_length:
            self.day_time -= self.day_length
        
        # Calculate time of day (0.0 to 1.0)
        t = self.day_time / self.day_length
        
        # Update mob system (handles mob AI, physics, spawning/despawning)
        if self.mob_system:
            self.mob_system.update(dt, self.player, t)
            
        # Colors
        # 0.0 - 0.4: Day (Blue)
        # 0.4 - 0.5: Sunset (Orange/Red)
        # 0.5 - 0.9: Night (Dark Blue/Black)
        # 0.9 - 1.0: Sunrise (Yellow/Orange)
        
        sky_color = (0, 0, 0)
        light_color = (1, 1, 1) # Fog color
        
        if t < 0.4: # Day
            sky_color = settings.BACKGROUND_COLOR # (0.5, 0.7, 1.0)
            light_color = settings.FOG_COLOR
        elif t < 0.5: # Sunset
            # Lerp Day -> Night
            p = (t - 0.4) * 10.0 # 0 to 1
            c1 = settings.BACKGROUND_COLOR
            c2 = (0.0, 0.0, 0.1) # Night color
            sunset = (0.8, 0.4, 0.2) # Orange
            
            if p < 0.5: # Day to Sunset
                pp = p * 2
                sky_color = (
                    c1[0] * (1-pp) + sunset[0] * pp,
                    c1[1] * (1-pp) + sunset[1] * pp,
                    c1[2] * (1-pp) + sunset[2] * pp
                )
            else: # Sunset to Night
                pp = (p - 0.5) * 2
                sky_color = (
                    sunset[0] * (1-pp) + c2[0] * pp,
                    sunset[1] * (1-pp) + c2[1] * pp,
                    sunset[2] * (1-pp) + c2[2] * pp
                )
            light_color = (sky_color[0], sky_color[1], sky_color[2], 1.0)
            
        elif t < 0.9: # Night
            sky_color = (0.0, 0.0, 0.1)
            light_color = (0.0, 0.0, 0.1, 1.0)
            
        else: # Sunrise
             # Lerp Night -> Day
            p = (t - 0.9) * 10.0 # 0 to 1
            c1 = (0.0, 0.0, 0.1)
            c2 = settings.BACKGROUND_COLOR
            sunrise = (0.8, 0.6, 0.2)
            
            if p < 0.5:
                pp = p * 2
                sky_color = (
                    c1[0] * (1-pp) + sunrise[0] * pp,
                    c1[1] * (1-pp) + sunrise[1] * pp,
                    c1[2] * (1-pp) + sunrise[2] * pp
                )
            else:
                pp = (p - 0.5) * 2
                sky_color = (
                    sunrise[0] * (1-pp) + c2[0] * pp,
                    sunrise[1] * (1-pp) + c2[1] * pp,
                    sunrise[2] * (1-pp) + c2[2] * pp
                )
            light_color = (sky_color[0], sky_color[1], sky_color[2], 1.0)
            
        self.set_background_color(*sky_color)
        if self.render.getFog():
            self.render.getFog().setColor(*light_color[:3])
            
        # Update HUD
        self._update_hud()
        
        return Task.cont


if __name__ == "__main__":
    App().run()
