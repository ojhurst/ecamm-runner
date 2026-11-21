#!/usr/bin/env python3
"""Cue, play or read the video file in the current Ecamm scene, with no mouse and no focus steal.

Usage: ecamm-video-transport.py status | cue | play | pause

status - prints the time left and whether it is playing.
cue    - pause, then press Rewind until the time left stops climbing: the video sits at 0:00, paused.
play   - start it; passes once the time left is counting down.
pause  - stop it; passes once the time left holds still.

The hover-only controls (Play/Pause Video, Rewind Video) are in the main window's AX tree even while
hidden, and AXPress works on them without the mouse. Rewind jumps back about 30 seconds per
press. The proof of every step is the scene name element, "<Scene> MM:SS", which counts the time
LEFT down while the video plays. Exit 0 = the end state is right. Notes: docs/how-it-works.md.
"""
import re, subprocess, sys, time


def ecamm_main(body):
    """Run body with w bound to Ecamm's main window (the "Ecamm" window with the most controls)."""
    script = f'''tell application "System Events" to tell process "Ecamm Live"
repeat with w in windows
if name of w is "Ecamm" and (count of UI elements of w) > 20 then
{body}
end if
end repeat
end tell'''
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()


def left():
    """Seconds left in the scene's video, read from the scene name element."""
    names = ecamm_main('''set out to ""
repeat with e in UI elements of w
try
set out to out & (name of e as text) & linefeed
end try
end repeat
return out''')
    for name in names.splitlines():
        if name.strip().startswith("LIVE"):
            continue  # while live, "LIVE 0:18" counts the broadcast up and would fake "playing"
        m = re.search(r" (\d+):(\d\d)$", name)
        if m:
            return int(m.group(1)) * 60 + int(m.group(2))
    raise RuntimeError("no video timer in the scene name; is a video file loaded?")


def press(desc):
    ecamm_main(f'perform action "AXPress" of (first UI element of w whose description is "{desc}")\nreturn "ok"')


def playing():
    a = left()
    time.sleep(1.6)
    return left() != a


def fmt(s):
    return f"{s // 60}:{s % 60:02d}"


def set_playing(want):
    for _ in range(5):  # a press can be lost while a just-loaded video is still starting
        if playing() == want:
            return True
        press("Play/Pause Video")
        time.sleep(1)
    return playing() == want


def main():
    action = sys.argv[1] if len(sys.argv) == 2 else ""
    if action not in ("status", "cue", "play", "pause"):
        print(__doc__.split("\n\n")[1])
        return 2
    try:
        if action == "status":
            print(f"left {fmt(left())}, {'playing' if playing() else 'paused'}")
            return 0
        if action in ("play", "pause"):
            ok = set_playing(action == "play")
            print(f"{'playing' if action == 'play' else 'paused'}: {ok}, left {fmt(left())}")
            return 0 if ok else 1
        if not set_playing(False):
            print("PROBLEM: could not pause")
            return 1
        prev = -1
        for _ in range(40):
            press("Rewind Video")
            time.sleep(0.6)
            now = left()
            if now == prev:
                break
            prev = now
        still = not playing()
        print(f"cued: left {fmt(prev)} (full length), paused={still}")
        return 0 if still and prev > 0 else 1
    except Exception as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
