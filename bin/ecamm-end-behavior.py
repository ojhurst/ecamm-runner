#!/usr/bin/env python3
"""Read or set Ecamm Live's "When Video Ends" menu (the hover-only control on the video preview).

Usage: ecamm-end-behavior.py status | set end-broadcast|do-nothing|loop|next-scene [--wait-idle SECONDS]

--wait-idle waits up to SECONDS for you to stop touching the mouse and keyboard, instead of giving up.

Takes the cursor for about two seconds: the control only exists while the mouse is over the
preview. It will not start while you have touched the mouse or keyboard in the last 3 seconds.
Before every click it checks the topmost window under the point is Ecamm. The current choice is
read from the checkmark in the open menu, then the menu is closed with Escape. Prints the checked
option; exit 0 when it matches what was asked. Menu offsets come from your settings
(end_menu_offsets). Notes: docs/how-it-works.md.
"""
import os, subprocess, sys, tempfile, time

import Quartz
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ecamm_runner_settings as settings

# Menu item offsets from the control's center, in points (menu opening downward).
ITEMS = settings.load()["end_menu_offsets"]
CHECK_DX = -3  # the checkmark column sits just left of the control's center
IDLE_SECS = 3


def idle_seconds():
    return Quartz.CGEventSourceSecondsSinceLastEventType(Quartz.kCGEventSourceStateHIDSystemState, Quartz.kCGAnyInputEventType)


def osa(script):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()


def mouse(kind, x, y):
    ev = {"move": Quartz.kCGEventMouseMoved, "down": Quartz.kCGEventLeftMouseDown, "up": Quartz.kCGEventLeftMouseUp}[kind]
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, Quartz.CGEventCreateMouseEvent(None, ev, (x, y), Quartz.kCGMouseButtonLeft))


def click(x, y):
    mouse("move", x, y); time.sleep(0.15); mouse("down", x, y); time.sleep(0.05); mouse("up", x, y)


def top_owner(x, y):
    for w in Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID):
        b = w["kCGWindowBounds"]
        if w.get("kCGWindowLayer", 0) < 0 or w.get("kCGWindowAlpha", 1) == 0 or w["kCGWindowOwnerName"] in ("Dock", "Window Server"):
            continue
        if b["X"] <= x <= b["X"] + b["Width"] and b["Y"] <= y <= b["Y"] + b["Height"]:
            return w["kCGWindowOwnerName"]


def main_window_frame():
    out = osa('''tell application "System Events" to tell process "Ecamm Live"
set AppleScript's text item delimiters to ","
repeat with w in windows
if name of w is "Ecamm" and (count of UI elements of w) > 20 then return ((position of w) & (size of w)) as text
end repeat
end tell''')
    return list(map(int, out.split(",")))


def control_center():
    out = osa('''tell application "System Events" to tell process "Ecamm Live"
set AppleScript's text item delimiters to ","
repeat with w in windows
if name of w is "Ecamm" and (count of UI elements of w) > 20 then
set m to (first UI element of w whose description is "Movie End Behavior Menu")
return ((position of m) & (size of m)) as text
end if
end repeat
end tell''')
    x, y, w, h = map(int, out.split(","))
    if y == 1080 and w == 0:
        raise RuntimeError("video controls hidden (hover did not register, or no video in this scene)")
    return x + w // 2, y + h // 2


def open_menu():
    osa('tell application "Ecamm Live" to activate')
    time.sleep(0.5)
    wx, wy, ww, wh = main_window_frame()
    px, py = wx + ww // 2, wy + wh // 2
    if top_owner(px, py) != "Ecamm":
        raise RuntimeError(f"{top_owner(px, py)} is on top of the Ecamm preview")
    for attempt in range(3):  # the first hover after a window change sometimes does not register
        mouse("move", px + attempt * 7, py); time.sleep(0.6)
        try:
            cx, cy = control_center()
            break
        except RuntimeError:
            if attempt == 2:
                raise
            time.sleep(1)
    if top_owner(cx, cy) != "Ecamm":
        raise RuntimeError("Ecamm is not on top at the menu control")
    click(cx, cy)
    time.sleep(0.8)
    return cx, cy


def checked(cx, cy):
    path = tempfile.mktemp(suffix=".png")
    subprocess.run(["screencapture", "-x", "-R", f"{cx - 20},{cy + 30},40,130", path], check=True)
    im = Image.open(path).convert("L")
    s = im.width / 40
    best, darkest = None, 255
    for name, dy in ITEMS.items():
        x0, y0 = int((20 + CHECK_DX - 6) * s), int((dy - 30 - 6) * s)
        px = sorted(im.crop((x0, y0, x0 + int(12 * s), y0 + int(12 * s))).tobytes())
        level = sum(px[:len(px) // 8]) / max(1, len(px) // 8)
        if level < darkest:
            best, darkest = name, level
    os.remove(path)
    return best if darkest < 100 else None


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("status", "set") or (sys.argv[1] == "set" and (len(sys.argv) < 3 or sys.argv[2] not in ITEMS)):
        print(__doc__); return 2
    want = sys.argv[2] if sys.argv[1] == "set" else None
    wait = int(sys.argv[sys.argv.index("--wait-idle") + 1]) if "--wait-idle" in sys.argv else 0
    deadline = time.time() + wait
    while True:
        if idle_seconds() >= IDLE_SECS:
            break
        if time.time() >= deadline:
            print("YIELD: you are using the mouse or keyboard right now" + (f" (waited {wait}s)" if wait else "")); return 1
        time.sleep(1)
    try:
        cx, cy = open_menu()
        now = checked(cx, cy)
        if want and now != want:
            click(cx + 40, cy + ITEMS[want]); time.sleep(0.6)
            wx, wy, ww, wh = main_window_frame()
            mouse("move", wx + ww // 2, wy + wh // 2); time.sleep(0.6)
            cx, cy = open_menu()
            now = checked(cx, cy)
        osa('tell application "System Events" to key code 53')
        print(now or "UNKNOWN (no checkmark found)")
        return 0 if (now and (not want or now == want)) else 1
    except Exception as e:
        print(f"ERROR {e}", file=sys.stderr)
        try: osa('tell application "System Events" to key code 53')
        except Exception: pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
