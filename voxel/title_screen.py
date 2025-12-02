from direct.gui.DirectGui import DirectFrame, DirectLabel, DirectButton, DGG
from direct.showbase.DirectObject import DirectObject

class TitleScreen(DirectObject):
    def __init__(self, app):
        self.app = app
        self.frame = None
        self.buttons = []
        self.selected_index = 0
        self.active = False
        
        self._create()

    def _create(self):
        """Create the title screen UI."""
        # Create semi-transparent background frame
        self.frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.3, 0.8),
            frameSize=(-0.8, 0.8, -0.6, 0.6),
            pos=(0, 0, 0),
            parent=self.app.aspect2d
        )
        self.frame.show()

        # Title label
        DirectLabel(
            text="Blockforge",
            scale=0.2,
            pos=(0, 0, 0.25),
            text_fg=(0, 0, 0.5, 1),  # Dark blue color
            frameColor=(0, 0, 0, 0),
            parent=self.frame
        )

        # Play button (now opens world selection)
        play_button = DirectButton(
            text="PLAY",
            scale=0.12,
            pos=(0, 0, 0),
            command=self.app._show_world_selection,
            parent=self.frame,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.1, 0.5, 0.1, 1)
        )

        # Settings button
        settings_button = DirectButton(
            text="SETTINGS",
            scale=0.10,
            pos=(0, 0, -0.2),
            command=self.app._show_settings_menu,
            parent=self.frame,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.3, 0.3, 0.3, 1)
        )

        # Quit button
        quit_button = DirectButton(
            text="QUIT",
            scale=0.12,
            pos=(0, 0, -0.4),
            command=self.app._quit_title_game,
            parent=self.frame,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.5, 0.1, 0.1, 1)
        )
        
        self.buttons = [play_button, settings_button, quit_button]

        # Instructions
        DirectLabel(
            text="Explore, Build, Survive",
            scale=0.08,
            pos=(0, 0, -0.5),
            text_fg=(0.8, 0.8, 0.8, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.frame
        )
        
        # Initial highlight
        self._update_highlight()

    def show(self):
        if self.frame:
            self.frame.show()
            self.active = True
            self._register_events()
            # Reset selection
            self.selected_index = 0
            self._update_highlight()
            
    def hide(self):
        if self.frame:
            self.frame.hide()
            self.active = False
            self._ignore_events()

    def _register_events(self):
        self.accept("control-up", self._on_nav_up)
        self.accept("control-down", self._on_nav_down)
        self.accept("control-select", self._on_nav_select)
        
    def _ignore_events(self):
        self.ignore("control-up")
        self.ignore("control-down")
        self.ignore("control-select")

    def _on_nav_up(self):
        if not self.active: return
        self.selected_index = (self.selected_index - 1) % len(self.buttons)
        self._update_highlight()
        
    def _on_nav_down(self):
        if not self.active: return
        self.selected_index = (self.selected_index + 1) % len(self.buttons)
        self._update_highlight()
        
    def _on_nav_select(self):
        if not self.active: return
        btn = self.buttons[self.selected_index]
        # Simulate click
        btn.commandFunc(None)

    def _update_highlight(self):
        for i, btn in enumerate(self.buttons):
            if i == self.selected_index:
                # Highlight style
                btn['frameColor'] = (0.8, 0.8, 0.8, 1)
                btn.setScale(1.1 * btn.getScale()[0]/btn.getScale()[0]) # Hacky reset? No, relative
                # Just set scale based on original
                if i == 0: btn.setScale(0.13) # Play
                elif i == 1: btn.setScale(0.11) # Settings
                elif i == 2: btn.setScale(0.13) # Quit
            else:
                # Normal style
                btn['frameColor'] = (0.8, 0.8, 0.8, 1) # Default greyish?
                # Reset scale
                if i == 0: btn.setScale(0.12)
                elif i == 1: btn.setScale(0.10)
                elif i == 2: btn.setScale(0.12)
                
                # Override frameColor for specific buttons if they had defaults
                # DirectButton default is grey.
                btn['frameColor'] = (0.8, 0.8, 0.8, 1) 
                
        # Visual feedback
        btn = self.buttons[self.selected_index]
        btn['frameColor'] = (1, 1, 0.5, 1) # Light yellow highlight

def create_title_screen(app):
    # Helper for backward compatibility if main.py expects a simple call,
    # but we need `show()`/`hide()` methods on the returned object.
    # Since main.py expects `self.title_screen.show()`, returning the TitleScreen object works.
    return TitleScreen(app)
