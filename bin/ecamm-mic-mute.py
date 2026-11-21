#!/usr/bin/env python3
"""Mute, unmute or read Ecamm Live's main mic through Ecamm's own scripting commands.

Usage: ecamm-mic-mute.py status|mute|unmute|toggle

Reads the state with `get mute` and flips it with `set mute` (Ecamm's scripting dictionary; macOS
asks once to allow controlling Ecamm). No mouse, no screenshots, no focus change. This is the same
mute as the MUTE button on the mic's row in Sound Levels. Prints MUTED or LIVE; exit 0 when the
final state is the one asked for. Notes: docs/how-it-works.md.
"""
import subprocess, sys, time


def ecamm(cmd):
    r = subprocess.run(["osascript", "-e", f'tell application "Ecamm Live" to {cmd}'], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()


def state():
    return "MUTED" if ecamm("get mute") == "yes" else "LIVE"


def main():
    action = sys.argv[1] if len(sys.argv) == 2 else ""
    if action not in ("status", "mute", "unmute", "toggle"):
        print(__doc__.split("\n\n")[1])
        return 2
    try:
        now = state()
        want = {"mute": "MUTED", "unmute": "LIVE", "toggle": "LIVE" if now == "MUTED" else "MUTED"}.get(action)
        if want and want != now:
            ecamm("set mute")
            time.sleep(0.5)
        final = state()
        print(final)
        return 0 if (not want or final == want) else 1
    except Exception as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
