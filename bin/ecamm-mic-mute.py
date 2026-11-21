#!/usr/bin/env python3
"""Mute, unmute or read the mic in Ecamm Live's Sound Levels window, without the mouse.

Usage: ecamm-mic-mute.py status|mute|unmute|toggle [--mic "<Sound Levels row name>"] [--shot out.png]

--mic defaults to "mic" in your settings (bin/ecamm_runner_settings.py).

Presses the MUTE button on the mic's own row through Accessibility (no cursor, no focus
change). Ecamm does not expose the mute state to AX, so the state is read from a
window-ID capture of Sound Levels: a muted MUTE button is drawn bright white, an
unmuted one is dim gray. Prints MUTED or LIVE; exit 0 on success, 1 on failure.
Notes: docs/how-it-works.md.
"""
import argparse, os, subprocess, sys, tempfile, time

import Quartz
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ecamm_runner_settings as settings

BRIGHT = 220  # mean of the brightest quarter of the button's pixels; measured muted 254, live 182


def osa(script):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()


def mute_button(mic):
    """Index (1-based, among buttons named MUTE) and frame of the MUTE button on the mic's row."""
    out = osa(f'''tell application "System Events" to tell process "Ecamm Live"
set AppleScript's text item delimiters to ","
set w to window "Sound Levels"
set rowPos to position of (first button of w whose name is "{mic}")
set rowY to item 2 of rowPos
set i to 0
repeat with b in (buttons of w whose name is "MUTE")
set i to i + 1
set btnPos to position of b
set btnY to item 2 of btnPos
if (btnY - rowY) < 8 and (rowY - btnY) < 8 then return ({{i}} & btnPos & (size of b) & (position of w) & (size of w)) as text
end repeat
return ""
end tell''')
    if not out:
        raise RuntimeError(f'no MUTE button on the "{mic}" row')
    i, bx, by, bw, bh, wx, wy, ww, _ = map(int, out.split(","))
    return i, (bx - wx, by - wy, bw, bh, ww)


def window_id():
    for w in Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID):
        if w.get("kCGWindowOwnerName") == "Ecamm" and w.get("kCGWindowName") == "Sound Levels":
            return w["kCGWindowNumber"]
    raise RuntimeError("Sound Levels window not found (is Ecamm Live open?)")


def state(mic, shot=None):
    _, (x, y, w, h, win_w) = mute_button(mic)
    path = shot or tempfile.mktemp(suffix=".png")
    subprocess.run(["screencapture", "-x", "-o", "-l", str(window_id()), path], check=True)
    im = Image.open(path).convert("L")
    s = im.width / win_w  # 2.0 on Retina
    px = sorted(im.crop((int(x * s), int(y * s), int((x + w) * s), int((y + h) * s))).tobytes())
    top = px[len(px) * 3 // 4:]
    level = sum(top) / len(top)
    if not shot:
        os.remove(path)
    return ("MUTED" if level >= BRIGHT else "LIVE"), level


def press(mic):
    i, _ = mute_button(mic)
    osa(f'tell application "System Events" to tell process "Ecamm Live" to click (button {i} of (buttons of window "Sound Levels" whose name is "MUTE"))')
    time.sleep(0.6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["status", "mute", "unmute", "toggle"])
    ap.add_argument("--mic", default=settings.load()["mic"])
    ap.add_argument("--shot", help="save the Sound Levels capture used for the final check")
    a = ap.parse_args()
    if not a.mic:
        ap.error(f'no mic: pass --mic or set "mic" in {settings.PATH}')
    try:
        now, _ = state(a.mic)
        want = {"mute": "MUTED", "unmute": "LIVE", "toggle": "LIVE" if now == "MUTED" else "MUTED"}.get(a.action)
        if want and want != now:
            press(a.mic)
        final, level = state(a.mic, a.shot)
        print(f"{final} ({a.mic}, brightness {level:.0f})")
        return 0 if (not want or final == want) else 1
    except Exception as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
