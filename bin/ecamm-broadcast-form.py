#!/usr/bin/env python3
"""Fill Ecamm Live's Create New Broadcast form, read every field back, and Cancel (dry run), Schedule or Go Live Now.

Usage:
  ecamm-broadcast-form.py check [--only facebook]    # connections only: open form, verify, Cancel
  ecamm-broadcast-form.py fill --title T --desc-file F [--thumb IMG] [--minute MM] [--now] [--only facebook]
                               [--submit] [--shot out.png]
  ecamm-broadcast-form.py restore [--wait-live-end]  # put LinkedIn back, select Scheduled, Cancel

check   - passes when the form has the wanted destinations (Facebook and LinkedIn, or Facebook
          alone with --only facebook) and Required Speed shows, with no reconnect warning.
fill    - also sets title, description and either Scheduled Start Time (minute field only;
          Ecamm's default is about 10 minutes out, which Facebook needs) plus the thumbnail, or
          Go Live Now (--now; Ecamm shows no thumbnail there). Reads every field back. Without
          --submit it presses Cancel, so nothing is created. With --submit it presses Schedule or
          Go Live Now and waits for the form to close; with --now it then waits for "End Live
          Session" to turn on, the proof the broadcast started.
restore - --only facebook removes LinkedIn from Ecamm's saved destinations (it sticks for every
          later broadcast, and so does Go Live Now), so run this after a Facebook-only live.
          --wait-live-end first waits for the live session to end (polls every 10 s).

The thumbnail goes through the macOS file chooser (see choose_file). Keystrokes only go out
while Ecamm is frontmost; anything else in front aborts the step.
How the form tells platforms apart (both pills show your account name): LinkedIn adds the
"Generate Automatic Captions (English)" checkbox, Facebook adds the Privacy pop-up. The Add menu
lists the destinations not on the form, each named " <name>" with a leading space; restore and
--only facebook need "account_name" in your settings (bin/ecamm_runner_settings.py).
Exit 0 = every check passed. Notes: docs/how-it-works.md.
"""
import argparse, os, subprocess, sys, time

import Quartz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ecamm_runner_settings as settings

FORM = "Create New Broadcast"
CAPTIONS = "Generate Automatic Captions (English)"
PILLS = f'UI element 1 of row 1 of table 1 of scroll area 1 of window "{FORM}"'
ADD = f'(first button of {PILLS} whose description is "Add New Destination")'


def osa(script):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()


def ecamm(body):
    return osa(f'tell application "System Events" to tell process "Ecamm Live"\n{body}\nend tell')


def form_open():
    return FORM in ecamm("return name of every window")


def open_form():
    if not form_open():
        osa('tell application "Ecamm Live" to activate')
        time.sleep(0.4)
        ecamm(f'click menu item "{FORM}..." of menu 1 of menu bar item "Ecamm" of menu bar 1')
    for _ in range(20):
        time.sleep(0.5)
        if form_open():
            time.sleep(2)  # destinations load from the platforms
            return
    raise RuntimeError("Create New Broadcast did not open")


def front_is_ecamm():
    return osa('tell application "System Events" to get name of first process whose frontmost is true') == "Ecamm Live"


def keys_to_ecamm(script):
    """Run keystrokes only while Ecamm is frontmost (your other windows must never get them)."""
    for _ in range(3):  # an editor you are typing in can take focus straight back
        osa('tell application "Ecamm Live" to activate')
        time.sleep(0.6)
        if front_is_ecamm():
            osa(f'tell application "System Events"\n{script}\nend tell')
            return
        time.sleep(1.5)
    raise RuntimeError("Ecamm is not frontmost; refusing to type")


def cleanup():
    """After an error: cancel any open file chooser, then the form, so nothing is left half-filled."""
    try:
        ecamm('''repeat with w in windows
if exists sheet 1 of w then
set s to sheet 1 of w
try
click button "Cancel" of splitter group 1 of s
end try
try
click button "Cancel" of s
end try
end if
end repeat''')
        time.sleep(1)
        if form_open():
            ecamm(f'click button "Cancel" of window "{FORM}"')
    except Exception:
        pass


def read_form():
    out = ecamm(f'''set w to window "{FORM}"
set t to table 1 of scroll area 1 of w
set dests to {{}}
repeat with r in rows of t
repeat with c in UI elements of r
repeat with x in UI elements of c
if role of x is "AXStaticText" then set end of dests to (value of x as text)
end repeat
end repeat
end repeat
set AppleScript's text item delimiters to ";"
set dests to dests as text
set texts to (value of every static text of w) as text
set ttl to value of text field 1 of w
set dsc to value of text area 1 of scroll area 2 of w
set img to "(none)"
try
set img to name of (first button of w whose description is "Upload Stream Thumbnail Image")
end try
set dt to "(see capture)"
try
set dt to value of (first UI element of w whose role is "AXDateTimeArea")
end try
set sched to value of radio button "Scheduled Start Time:" of w
set li to "0"
repeat with a in scroll areas of w
if exists checkbox "{CAPTIONS}" of a then set li to "1"
end repeat
set fb to (count of pop up buttons of w) as text
set AppleScript's text item delimiters to "|~|"
return {{dests as text, texts, ttl, (length of dsc) as text, img, dt as text, sched as text, li, fb}} as text''')
    dests, texts, ttl, dlen, img, dt, sched, li, fb = (out.split("|~|") + [""] * 9)[:9]
    return {"dests": [d for d in dests.split(";") if d], "texts": texts, "title": ttl,
            "desc_len": int(dlen or 0), "thumb_button": img, "start": dt, "scheduled": sched,
            "linkedin": li == "1", "facebook": fb not in ("", "0")}


def check(f, only_facebook):
    problems = []
    want = 1 if only_facebook else 2
    if len(f["dests"]) != want:
        problems.append(f"expected {want} destinations, found {f['dests']}")
    if not f["facebook"]:
        problems.append("no Facebook destination (Privacy pop-up missing)")
    if f["linkedin"] == only_facebook:
        problems.append("LinkedIn is on the form" if only_facebook else "no LinkedIn destination (captions checkbox missing)")
    if "Required Speed" not in f["texts"]:
        problems.append("no Required Speed line")
    if "reconnect" in f["texts"].lower() or "log in" in f["texts"].lower():
        problems.append("form asks to reconnect or log in")
    return problems


def add_destinations():
    """Add every destination named account_name the Add menu offers (LinkedIn, and Facebook if it was removed)."""
    name = settings.require("account_name").replace('"', '\\"')
    for _ in range(2):
        f = read_form()
        if f["linkedin"] and f["facebook"]:
            return
        # The menu only exists while open, and only hangs off a resolved button (not a whose-filter).
        items = ecamm(f'''set b to {ADD}
repeat 3 times
click b
repeat 7 times
delay 0.3
if exists menu 1 of b then exit repeat
end repeat
if exists menu 1 of b then exit repeat
end repeat
return name of every menu item of menu 1 of b''').split(", ")
        if name not in [i.strip() for i in items]:
            keys_to_ecamm("key code 53")
            raise RuntimeError(f"Add menu has no {name!r} destination: {items}")
        ecamm(f'''set b to {ADD}
click (first menu item of menu 1 of b whose name is " {name}")''')
        time.sleep(2)


def remove_linkedin():
    """Remove pills from the left until the captions checkbox is gone; Facebook must survive."""
    for _ in range(3):
        if not read_form()["linkedin"]:
            return
        ecamm(f'click item 1 of (every button of {PILLS} whose description is "Remove Destination")')
        time.sleep(1.5)
        if not read_form()["facebook"]:
            add_destinations()
            raise RuntimeError("removed Facebook instead of LinkedIn; put both back")
    raise RuntimeError("LinkedIn is still on the form")


def set_mode(now):
    ecamm(f'click radio button "{"Go Live Now (Unscheduled)" if now else "Scheduled Start Time:"}" of window "{FORM}"')
    time.sleep(0.5)


def live():
    return ecamm('return enabled of menu item "End Live Session" of menu 1 of menu bar item "Ecamm" of menu bar 1') == "true"


def set_text(title, desc):
    d = desc.replace("\\", "\\\\").replace('"', '\\"')
    t = title.replace("\\", "\\\\").replace('"', '\\"')
    ecamm(f'''set w to window "{FORM}"
set value of text field 1 of w to "{t}"
set value of text area 1 of scroll area 2 of w to "{d}"''')


def set_minute(mm):
    keys_to_ecamm(f'''tell process "Ecamm Live"
set w to window "{FORM}"
perform action "AXRaise" of w
set focused of (first UI element of w whose role is "AXDateTimeArea") to true
end tell
delay 0.3
repeat 4 times
key code 124
delay 0.1
end repeat
keystroke "{mm:02d}"
delay 0.3
key code 48''')


def choose_file(path):
    """Answer an open macOS file chooser (a sheet on an Ecamm window) with path, without the clipboard.

    Cmd+Shift+G opens Go To Folder as a sheet on the chooser sheet. Its text field takes the path
    through AX, but Return only lands once the field is AX-focused (AXConfirm does nothing). Then
    Open is pressed through AX. A pasted path is not used: a clipboard manager replaced it mid-paste
    once and a URL went in instead.
    """
    has_goto = 'repeat with w in windows\nif exists sheet 1 of sheet 1 of w then return "yes"\nend repeat\nreturn "no"'
    for attempt in range(2):  # the Go To sheet can take a few seconds; resend the shortcut once
        keys_to_ecamm('keystroke "g" using {command down, shift down}')
        for _ in range(10):
            time.sleep(0.5)
            if ecamm(has_goto) == "yes":
                break
        else:
            continue
        break
    p = path.replace("\\", "\\\\").replace('"', '\\"')
    found = ecamm(f'''repeat with w in windows
if exists sheet 1 of sheet 1 of w then
set g to sheet 1 of sheet 1 of w
set value of text field 1 of g to "{p}"
delay 0.8
set focused of text field 1 of g to true
return "ok"
end if
end repeat
return "no Go To Folder sheet"''')
    if found != "ok":
        raise RuntimeError(found)
    keys_to_ecamm("key code 36")
    time.sleep(2)
    state = ecamm('''repeat with w in windows
if exists sheet 1 of w then
set s to sheet 1 of w
if exists sheet 1 of s then return "Go To Folder still open"
set b to missing value
try
set b to button "Open" of splitter group 1 of s
end try
if b is missing value then
try
set b to button "Open" of s
end try
end if
if b is missing value then return "no Open button"
if not (enabled of b) then return "Open disabled (file not found?)"
click b
return "opened"
end if
end repeat
return "no chooser"''')
    if state != "opened":
        raise RuntimeError(f"file chooser: {state}; press Cancel in Ecamm's file chooser")


def set_thumb(path):
    ecamm(f'click (first button of window "{FORM}" whose description is "Upload Stream Thumbnail Image")')
    time.sleep(2)
    choose_file(path)
    for _ in range(10):
        time.sleep(0.5)
        if ecamm(f'return count of sheets of window "{FORM}"') == "0":
            break


def capture(path):
    for w in Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID):
        if w.get("kCGWindowOwnerName") == "Ecamm" and w.get("kCGWindowName") == FORM:
            subprocess.run(["screencapture", "-x", "-o", "-l", str(w["kCGWindowNumber"]), path], check=True)
            return path


def close(submit, now=False):
    button = ("Go Live Now" if now else "Schedule") if submit else "Cancel"
    ecamm(f'click button "{button}" of window "{FORM}"')
    for _ in range(60 if submit else 10):
        time.sleep(1)
        if not form_open():
            return True
    return False


def restore(wait_live_end):
    if wait_live_end:
        while live():
            time.sleep(10)
        time.sleep(5)  # the "broadcast has ended" summary comes up first
    # Ecamm can pop "Install and Relaunch" when a live ends and quit under us (2026-11-21): keep trying.
    for attempt in range(12):
        try:
            open_form()
            break
        except RuntimeError as e:
            if attempt == 11:
                raise
            print(f"restore: waiting for Ecamm ({e})")
            time.sleep(10)
    add_destinations()
    set_mode(False)
    f = read_form()
    problems = check(f, False)
    print(f"restore: {len(f['dests'])} destinations, LinkedIn={f['linkedin']}, Facebook={f['facebook']}, "
          f"scheduled={f['scheduled']}; " + ("OK" if not problems else "PROBLEM: " + "; ".join(problems)))
    closed = close(False)
    return 0 if not problems and f["scheduled"] == "1" and closed else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["check", "fill", "restore"])
    ap.add_argument("--title")
    ap.add_argument("--desc-file")
    ap.add_argument("--thumb")
    ap.add_argument("--minute", type=int)
    ap.add_argument("--now", action="store_true", help="Go Live Now instead of Scheduled Start Time")
    ap.add_argument("--only", choices=["facebook"], help="stream to Facebook alone (removes LinkedIn)")
    ap.add_argument("--submit", "--schedule", dest="submit", action="store_true",
                    help="press Schedule / Go Live Now (otherwise Cancel)")
    ap.add_argument("--wait-live-end", action="store_true", help="restore: wait for the live session to end first")
    ap.add_argument("--shot", help="save a capture of the filled form before closing it")
    a = ap.parse_args()
    if a.action == "fill" and not (a.title and a.desc_file):
        ap.error("fill needs --title and --desc-file")
    if a.now and (a.minute is not None or a.thumb):
        ap.error("--now takes no --minute or --thumb (Ecamm hides both for Go Live Now)")
    only_fb = a.only == "facebook"
    try:
        if a.action == "restore":
            return restore(a.wait_live_end)
        if live():
            raise RuntimeError("Ecamm is already live; end that session first")
        open_form()
        if only_fb:
            remove_linkedin()
        else:
            add_destinations()
        set_mode(a.now)
        f = read_form()
        problems = check(f, only_fb)
        print(f"connections: {len(f['dests'])} destinations {f['dests']}, LinkedIn={f['linkedin']}, "
              f"Facebook={f['facebook']}; " + ("OK" if not problems else "PROBLEM: " + "; ".join(problems)))
        if a.action == "fill" and not problems:
            desc = open(a.desc_file, encoding="utf-8").read().strip()
            set_text(a.title, desc)
            if a.minute is not None:
                set_minute(a.minute)
            if a.thumb:
                set_thumb(a.thumb)
            time.sleep(0.5)
            f = read_form()
            print(f"title: {f['title']!r}")
            print(f"description: {f['desc_len']} chars (file {len(desc)})")
            print(f"start: {'Go Live Now' if a.now else f['start']} (scheduled={f['scheduled']})")
            print(f"thumbnail button: {f['thumb_button']!r}")
            if f["title"] != a.title:
                problems.append("title did not stick")
            if f["desc_len"] < len(desc) - 5:
                problems.append("description did not stick")
            if f["scheduled"] != ("0" if a.now else "1"):
                problems.append(f"{'Go Live Now' if a.now else 'Scheduled Start Time'} not selected")
            if a.thumb and f["thumb_button"] == "Add Image":
                problems.append("thumbnail did not load")
        if a.shot:
            capture(a.shot)
            print(f"shot: {a.shot}")
        do_submit = a.submit and a.action == "fill" and not problems
        closed = close(do_submit, a.now)
        if not do_submit:
            print("cancelled (dry run)" + ("" if closed else " - form still open!"))
        elif not a.now:
            print("SCHEDULED" + ("" if closed else " - form still open!"))
        else:
            for _ in range(30):
                if live():
                    break
                time.sleep(1)
            started = live()
            print("LIVE" if started else "PROBLEM: pressed Go Live Now but End Live Session never turned on")
            closed = closed and started
        return 0 if not problems and closed else 1
    except Exception as e:
        print(f"ERROR {e}", file=sys.stderr)
        cleanup()
        return 1


if __name__ == "__main__":
    sys.exit(main())
