#!/usr/bin/env python3
"""Load a video file as the current Ecamm scene's source and check it took.

Usage: ecamm-load-video.py /path/to/video.mp4

Source > Video File > Choose File... opens the chooser as a sheet on the main Ecamm window, which
ecamm-broadcast-form.py's choose_file answers without the clipboard. Passes when the file's name is
the newest entry under Source > Video File > Recent Items. A loaded video starts playing at once;
ecamm-video-transport.py cue puts it back to 0:00, paused.
Exit 0 = loaded. Notes: docs/how-it-works.md.
"""
import importlib.util, os, sys, time

_spec = importlib.util.spec_from_file_location("form", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ecamm-broadcast-form.py"))
form = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(form)

MENU = 'menu 1 of menu item "Video File" of menu 1 of menu bar item "Source" of menu bar 1'


def recent():
    names = form.ecamm(f'return name of every menu item of {MENU}').split(", ")
    after = names[names.index("Recent Items") + 1:] if "Recent Items" in names else []
    return [n for n in after if n not in ("missing value", "Clear Recent Items", "Play/Pause")]


def main():
    path = os.path.abspath(sys.argv[1]) if len(sys.argv) == 2 else ""
    if not os.path.isfile(path):
        print(__doc__.split("\n\n")[1])
        return 2
    try:
        form.osa('tell application "Ecamm Live" to activate')
        time.sleep(0.4)
        form.ecamm(f'click menu item "Choose File..." of {MENU}')
        time.sleep(2)
        form.choose_file(path)
        name = os.path.basename(path)
        r = []
        for _ in range(20):
            time.sleep(0.5)
            r = recent()
            if r and r[0] == name:
                print(f"loaded: {name}")
                return 0
        print(f"PROBLEM: newest recent item is {r[:1]}, expected {name!r}")
        return 1
    except Exception as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
