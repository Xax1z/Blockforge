from panda3d.core import InputDevice
try:
    print(f"InputDevice.Axis exists: {InputDevice.Axis}")
except Exception as e:
    print(f"InputDevice.Axis error: {e}")

try:
    print(f"InputDevice.Button exists: {InputDevice.Button}")
except Exception as e:
    print(f"InputDevice.Button error: {e}")
    
import panda3d.core
print("Dir(panda3d.core): search for Gamepad")
for x in dir(panda3d.core):
    if "Gamepad" in x or "Button" in x:
        print(x)
