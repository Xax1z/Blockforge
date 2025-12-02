from panda3d.core import InputDevice, InputDeviceManager, ButtonHandle, GamepadButton
from direct.showbase.DirectObject import DirectObject
from direct.task import Task

class InputHandler(DirectObject):
    def __init__(self, app):
        self.app = app
        self.gamepad = None
        self.deadzone = 0.2
        
        # Navigation state for menus
        self.nav_cooldown = 0.0
        self.nav_interval = 0.2
        self.last_nav_time = 0.0
        
        # Check for initial devices
        self._connect_gamepad()
        
        # Listen for device connection events
        self.accept("connect-device", self._on_connect)
        self.accept("disconnect-device", self._on_disconnect)
        
        # Input State
        self.state = {
            # Axes (-1.0 to 1.0)
            "move_x": 0.0,
            "move_y": 0.0,
            "look_x": 0.0,
            "look_y": 0.0,
            "trigger_l": 0.0, # 0.0 to 1.0
            "trigger_r": 0.0, # 0.0 to 1.0
            
            # Buttons (Pressed state)
            "jump": False,
            "crouch": False,
            "sprint": False,
            "interact": False,
            "inventory": False,
            "pause": False,
            "bumper_l": False,
            "bumper_r": False,
            
            # Menu Navigation (Impulse)
            "nav_up": False,
            "nav_down": False,
            "nav_left": False,
            "nav_right": False,
            "nav_select": False,
            "nav_back": False,
        }
        
        # Previous state for edge detection (triggering actions once per press)
        self.prev_button_state = {
            "jump": False,
            "crouch": False,
            "sprint": False,
            "interact": False,
            "inventory": False,
            "pause": False,
            "bumper_l": False,
            "bumper_r": False,
            "face_a": False,
            "face_b": False,
            "start": False,
        }
        
        # Start update task
        self.app.taskMgr.add(self._update, "input_handler_update")

    def _connect_gamepad(self):
        devices = self.app.devices.getDevices(InputDevice.DeviceClass.gamepad)
        if devices:
            self._on_connect(devices[0])
        else:
            print("[InputHandler] No gamepad found.")

    def _on_connect(self, device):
        if self.gamepad:
            return # Already have one
            
        if device.device_class == InputDevice.DeviceClass.gamepad:
            print(f"[InputHandler] Gamepad connected: {device.name}")
            self.gamepad = device
            self.app.attachInputDevice(device, prefix="gamepad")
            
    def _on_disconnect(self, device):
        if self.gamepad == device:
            print(f"[InputHandler] Gamepad disconnected: {device.name}")
            self.app.detachInputDevice(device)
            self.gamepad = None
            # Try to find another one
            self._connect_gamepad()

    def _update(self, task):
        dt = globalClock.getDt()
        
        if not self.gamepad:
            return Task.cont
            
        # Poll gamepad state
        self.gamepad.poll()
        
        # Reset impulses
        self.state["nav_up"] = False
        self.state["nav_down"] = False
        self.state["nav_left"] = False
        self.state["nav_right"] = False
        self.state["nav_select"] = False
        self.state["nav_back"] = False
        
        # Read Axes
        lx = self._apply_deadzone(self.gamepad.findAxis(InputDevice.Axis.left_x).value)
        ly = self._apply_deadzone(self.gamepad.findAxis(InputDevice.Axis.left_y).value)
        rx = self._apply_deadzone(self.gamepad.findAxis(InputDevice.Axis.right_x).value)
        ry = self._apply_deadzone(self.gamepad.findAxis(InputDevice.Axis.right_y).value)
        
        # Triggers (0 to 1) - Some gamepads map them to axes
        lt = self.gamepad.findAxis(InputDevice.Axis.left_trigger).value
        rt = self.gamepad.findAxis(InputDevice.Axis.right_trigger).value
        
        # Update Analog State
        self.state["move_x"] = lx
        self.state["move_y"] = ly 
        self.state["look_x"] = rx
        self.state["look_y"] = ry
        self.state["trigger_l"] = lt
        self.state["trigger_r"] = rt

        # Buttons
        # Define mappings (standard Xbox controller layout)
        btns = {
            "jump": GamepadButton.face_a(),
            "crouch": GamepadButton.rstick(), # R3
            "sprint": GamepadButton.lstick(),  # L3
            "interact": GamepadButton.face_x(),
            "inventory": GamepadButton.face_y(),
            "pause": GamepadButton.start(),
            "back": GamepadButton.back(), # View button
            "bumper_l": GamepadButton.lshoulder(),
            "bumper_r": GamepadButton.rshoulder(),
            "face_b": GamepadButton.face_b(), # Back/Cancel
            
            "dpad_up": GamepadButton.dpad_up(),
            "dpad_down": GamepadButton.dpad_down(),
            "dpad_left": GamepadButton.dpad_left(),
            "dpad_right": GamepadButton.dpad_right(),
        }
        
        # Helper to check button
        def is_pressed(btn_id):
            return self.gamepad.findButton(btn_id).pressed

        # All buttons use edge detection (only trigger once per press)
        # This prevents rapid toggling when holding a button down
        
        # Jump
        jump_pressed = is_pressed(btns["jump"])
        self.state["jump"] = jump_pressed and not self.prev_button_state["jump"]
        self.prev_button_state["jump"] = jump_pressed
        
        # Crouch
        crouch_pressed = is_pressed(btns["crouch"])
        self.state["crouch"] = crouch_pressed and not self.prev_button_state["crouch"]
        self.prev_button_state["crouch"] = crouch_pressed
        
        # Sprint
        sprint_pressed = is_pressed(btns["sprint"])
        self.state["sprint"] = sprint_pressed and not self.prev_button_state["sprint"]
        self.prev_button_state["sprint"] = sprint_pressed
        
        # Interact
        interact_pressed = is_pressed(btns["interact"])
        self.state["interact"] = interact_pressed and not self.prev_button_state["interact"]
        self.prev_button_state["interact"] = interact_pressed
        
        # Inventory
        inventory_pressed = is_pressed(btns["inventory"])
        self.state["inventory"] = inventory_pressed and not self.prev_button_state["inventory"]
        self.prev_button_state["inventory"] = inventory_pressed
        
        # Pause
        pause_pressed = is_pressed(btns["pause"])
        self.state["pause"] = pause_pressed and not self.prev_button_state["pause"]
        self.prev_button_state["pause"] = pause_pressed
        
        # Bumpers
        bumper_l_pressed = is_pressed(btns["bumper_l"])
        self.state["bumper_l"] = bumper_l_pressed and not self.prev_button_state["bumper_l"]
        self.prev_button_state["bumper_l"] = bumper_l_pressed
        
        bumper_r_pressed = is_pressed(btns["bumper_r"])
        self.state["bumper_r"] = bumper_r_pressed and not self.prev_button_state["bumper_r"]
        self.prev_button_state["bumper_r"] = bumper_r_pressed
        
        # Menu Navigation Logic (D-Pad + Stick)
        # Use a timer to prevent scrolling too fast
        time = globalClock.getFrameTime()
        if time - self.last_nav_time > self.nav_interval:
            nav_input = False
            
            # Up
            if is_pressed(btns["dpad_up"]) or ly > 0.5:
                self.state["nav_up"] = True
                nav_input = True
                
            # Down
            if is_pressed(btns["dpad_down"]) or ly < -0.5:
                self.state["nav_down"] = True
                nav_input = True
                
            # Left
            if is_pressed(btns["dpad_left"]) or lx < -0.5:
                self.state["nav_left"] = True
                nav_input = True
                
            # Right
            if is_pressed(btns["dpad_right"]) or lx > 0.5:
                self.state["nav_right"] = True
                nav_input = True
                
            if nav_input:
                self.last_nav_time = time
                
                # Emit events
                if self.state["nav_up"]: self.app.messenger.send("control-up")
                if self.state["nav_down"]: self.app.messenger.send("control-down")
                if self.state["nav_left"]: self.app.messenger.send("control-left")
                if self.state["nav_right"]: self.app.messenger.send("control-right")

        # Menu navigation select/back (edge-triggered)
        face_a_pressed = is_pressed(btns["jump"])
        if face_a_pressed and not self.prev_button_state["face_a"]:
            self.state["nav_select"] = True
            print("[InputHandler] Sending control-select") # Debug
            self.app.messenger.send("control-select")
        self.prev_button_state["face_a"] = face_a_pressed
        
        face_b_pressed = is_pressed(btns["face_b"])
        if face_b_pressed and not self.prev_button_state["face_b"]:
            self.state["nav_back"] = True
            self.app.messenger.send("control-back")
        self.prev_button_state["face_b"] = face_b_pressed
        
        # Start button for pause menu (edge-triggered)
        start_pressed = is_pressed(btns["pause"])
        if start_pressed and not self.prev_button_state["start"]:
            self.app.messenger.send("control-pause")
        self.prev_button_state["start"] = start_pressed

        return Task.cont

    def _apply_deadzone(self, value):
        if abs(value) < self.deadzone:
            return 0.0
        return value

    def get_move(self):
        """Get movement vector (x, y)."""
        return self.state["move_x"], self.state["move_y"]

    def get_look(self):
        """Get look vector (x, y)."""
        return self.state["look_x"], self.state["look_y"]
