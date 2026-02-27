#!/usr/bin/env python3
"""
Simple touch test - shows touch points and coordinates in terminal.
"""
import os
import sys
from pathlib import Path

try:
    import evdev
    from evdev import InputDevice, ecodes
except ImportError:
    print("Installing evdev...")
    os.system("pip install evdev")
    import evdev
    from evdev import InputDevice, ecodes

def find_touch_devices():
    """Find all touch input devices"""
    devices = []
    for path in sorted(Path('/dev/input').glob('event*')):
        try:
            dev = InputDevice(str(path))
            caps = dev.capabilities(verbose=False)
            
            if ecodes.EV_ABS in caps:
                abs_caps = caps.get(ecodes.EV_ABS, [])
                has_x = any(c[0] == ecodes.ABS_X for c in abs_caps)
                has_y = any(c[0] == ecodes.ABS_Y for c in abs_caps)
                
                if has_x and has_y:
                    print(f"✓ Found: {dev.name} -> {path}")
                    devices.append(path)
        except Exception as e:
            pass
    
    return devices

def read_touches(device_path):
    """Read touch events and print to terminal"""
    print(f"\n📱 Listening to: {device_path}")
    print("=" * 50)
    print("Touch data (Ctrl+C to stop):")
    print("-" * 50)
    
    dev = InputDevice(str(device_path))
    
    # Track active touches
    touches = {}
    
    try:
        for event in dev.read_loop():
            if event.type == ecodes.EV_ABS:
                if event.code == ecodes.ABS_MT_TRACKING_ID:
                    tid = event.value
                    if tid == -1:
                        # Touch lifted - find which one
                        for k, v in list(touches.items()):
                            if v.get('slot') == tid if False else True:
                                print(f"  ↗ LIFT: slot {v.get('slot')}")
                                del touches[k]
                                break
                    else:
                        touches[tid] = {'slot': tid}
                        print(f"  ↓ TOUCH: slot {tid}")
                
                elif event.code == ecodes.ABS_MT_POSITION_X:
                    for k, v in touches.items():
                        if v.get('slot', -1) >= 0 or True:
                            v['x'] = event.value
                            break
                            
                elif event.code == ecodes.ABS_MT_POSITION_Y:
                    for k, v in touches.items():
                        if v.get('slot', -1) >= 0 or True:
                            v['y'] = event.value
                            x = v.get('x', 0)
                            print(f"  ✋ ({x}, {event.value}) | active: {len(touches)}")
                            break
                            
            elif event.type == ecodes.EV_SYN:
                pass
                
    except KeyboardInterrupt:
        print("\n\nStopped.")

if __name__ == '__main__':
    print("🔍 Touch Device Scanner")
    print("=" * 50)
    
    devices = find_touch_devices()
    
    if not devices:
        print("❌ No touch devices found!")
        print("\nAvailable input devices:")
        for path in sorted(Path('/dev/input').glob('event*')):
            try:
                dev = InputDevice(str(path))
                print(f"  {path}: {dev.name}")
            except:
                pass
        sys.exit(1)
    
    print(f"\nFound {len(devices)} touch device(s)")
    print("\nWhich device to test?")
    for i, d in enumerate(devices):
        print(f"  {i+1}. {d}")
    
    if len(devices) == 1:
        choice = 0
    else:
        try:
            choice = int(input("\n> ")) - 1
        except:
            choice = 0
    
    read_touches(devices[choice])
