"""
Settings menu for the voxel game.
"""

from direct.gui.DirectGui import DirectFrame, DirectLabel, DirectButton, DirectSlider
from direct.showbase.DirectObject import DirectObject
from voxel import settings
from voxel.save_system import SaveSystem

class SettingsMenu(DirectObject):
    """Settings menu with FOV slider."""
    
    def __init__(self, app):
        self.app = app
        self.frame = None
        self.back_btn = None
        self.fov_slider = None
        self.fov_label = None
        self.active = False
        self.source = "title" # 'title' or 'pause'
        
        self.elements = []
        self.selected_index = 0
        
    def create(self):
        """Create the settings menu."""
        # Main background frame
        self.frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.3, 0.9),
            frameSize=(-0.8, 0.8, -0.6, 0.6),
            pos=(0, 0, 0),
            parent=self.app.aspect2d
        )
        
        # Title
        DirectLabel(
            text="SETTINGS",
            scale=0.15,
            pos=(0, 0, 0.45),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.frame
        )
        
        # FOV Label
        self.fov_label = DirectLabel(
            text=f"Field of View: {int(settings.FOV * 180 / 3.14159)}°",
            scale=0.08,
            pos=(0, 0, 0.2),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.frame
        )

        # FOV Slider
        self.fov_slider = DirectSlider(
            range=(40, 120),
            value=settings.FOV * 180 / 3.14159,  # Convert radians to degrees
            pageSize=5,
            command=self._on_fov_change,
            scale=0.5,
            pos=(0, 0, 0.05),
            parent=self.frame
        )
        
        # Back button
        self.back_btn = DirectButton(
            text="BACK",
            scale=0.1,
            pos=(0, 0, -0.45),
            command=self._on_back,
            parent=self.frame,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.2, 0.2, 0.8, 1)
        )
        
        self.elements = [self.fov_slider, self.back_btn]
        
        self.frame.hide()
        return self.frame
    
    def _register_events(self):
        self.accept("control-back", self._on_back)
        self.accept("control-up", self._on_nav_up)
        self.accept("control-down", self._on_nav_down)
        self.accept("control-left", self._on_nav_left)
        self.accept("control-right", self._on_nav_right)
        self.accept("control-select", self._on_select)

    def _ignore_events(self):
        self.ignore("control-back")
        self.ignore("control-up")
        self.ignore("control-down")
        self.ignore("control-left")
        self.ignore("control-right")
        self.ignore("control-select")
        
    def _on_fov_change(self):
        if not self.frame: return
        
        # Update settings
        degrees = self.fov_slider['value']
        settings.FOV = degrees * (3.14159 / 180.0)
        
        # Update label
        self.fov_label['text'] = f"Field of View: {int(degrees)}°"
        
        # Update camera if app is running
        if hasattr(self.app, 'camLens'):
             self.app.camLens.setFov(degrees)
             
    def _on_back(self):
        """Return to previous screen."""
        self.hide()
        
        # Save settings when leaving the menu
        SaveSystem.save_settings()
        
        if self.source == 'title':
            if hasattr(self.app, 'title_screen'):
                self.app.title_screen.show()
        elif self.source == 'pause':
            # Return to pause menu
             if hasattr(self.app, '_show_pause_menu'):
                 self.app._show_pause_menu()
                 
    def show(self, source="title"):
        """Show the settings menu."""
        self.source = source
        if self.frame:
            self.frame.show()
            self.active = True
            self._register_events()
            
            # Sync slider with current settings
            degrees = settings.FOV * 180 / 3.14159
            self.fov_slider['value'] = degrees
            self.fov_label['text'] = f"Field of View: {int(degrees)}°"
            
            self.selected_index = 0
            self._update_highlight()
            
    def hide(self):
        """Hide the settings menu."""
        if self.frame:
            self.frame.hide()
            self.active = False
            self._ignore_events()
            
    def _on_nav_up(self):
        if not self.active: return
        self.selected_index = (self.selected_index - 1) % len(self.elements)
        self._update_highlight()
        
    def _on_nav_down(self):
        if not self.active: return
        self.selected_index = (self.selected_index + 1) % len(self.elements)
        self._update_highlight()
        
    def _on_nav_left(self):
        if not self.active: return
        if self.elements[self.selected_index] == self.fov_slider:
            self.fov_slider['value'] -= self.fov_slider['pageSize']
            self._on_fov_change()
            
    def _on_nav_right(self):
        if not self.active: return
        if self.elements[self.selected_index] == self.fov_slider:
            self.fov_slider['value'] += self.fov_slider['pageSize']
            self._on_fov_change()
            
    def _on_select(self):
        if not self.active: return
        element = self.elements[self.selected_index]
        if element == self.back_btn:
            self._on_back()
            
    def _update_highlight(self):
        for i, element in enumerate(self.elements):
            if element == self.back_btn:
                if i == self.selected_index:
                    element['frameColor'] = (0.3, 0.3, 0.9, 1)
                    element.setScale(0.11)
                else:
                    element['frameColor'] = (0.2, 0.2, 0.8, 1)
                    element.setScale(0.1)
