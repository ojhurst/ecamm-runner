#!/usr/bin/env python3
"""Load a video file as the current Ecamm scene's source and check it took.

Usage: ecamm-load-video.py /path/to/video.mp4

Uses Ecamm's own scripting command `set video id <path>`, which switches the scene to Video File
mode and starts the file playing. No file chooser, no keystrokes. Passes when `get current mode`
is "video" and the file is the newest entry in `get video list`.
ecamm-video-transport.py cue then puts it back to 0:00, paused. Notes: docs/how-it-works.md.
"""
import os, subprocess, sys, time


def ecamm(cmd):
    r = subprocess.run(["osascript", "-e", f'tell application "Ecamm Live" to {cmd}'], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()


def main():
    path = os.path.abspath(sys.argv[1]) if len(sys.argv) == 2 else ""
    if not os.path.isfile(path):
        print(__doc__.split("\n\n")[1])
        return 2
    try:
        p = path.replace("\\", "\\\\").replace('"', '\\"')
        ecamm(f'set video id "{p}"')
        for _ in range(20):
            time.sleep(0.5)
            newest = ecamm("get video list").split(", title:")[0].removeprefix("UUID:")
            if ecamm("get current mode") == "video" and newest == path:
                print(f"loaded: {os.path.basename(path)}")
                return 0
        print(f"PROBLEM: mode {ecamm('get current mode')!r}, newest video {newest!r}")
        return 1
    except Exception as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
