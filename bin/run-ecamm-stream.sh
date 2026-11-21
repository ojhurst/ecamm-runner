#!/bin/bash
# Pre-stream checklist, then schedule or go live, for an Ecamm Live replay of a video file.
# Usage: run-ecamm-stream.sh --title T --desc-file F [--video FILE] [--thumb IMG] [--minute MM] [--now] [--only facebook] [--go]
#   Scheduled (default): needs --thumb; Facebook and LinkedIn events about 10 minutes out (or --minute).
#   --now: Go Live Now, no thumbnail (Ecamm hides it). --only facebook: drop LinkedIn for this broadcast.
#   Without --go it is a dry run: every check runs and the form is filled and read back, then Cancelled.
# Steps (each script checks its own result and exits 1 on a wrong end state):
#   0. video        bin/ecamm-load-video.py FILE        (skip when the video is already in the scene)
#                   bin/ecamm-video-transport.py cue     (0:00, paused; a loaded video starts playing)
#   1. connections  bin/ecamm-broadcast-form.py check [--only facebook]
#   2. mic muted    bin/ecamm-mic-mute.py mute          (a replay must not carry the room)
#   3. end video    bin/ecamm-end-behavior.py set end-broadcast   (takes the cursor ~2s; waits while you are busy)
#   4. form         bin/ecamm-broadcast-form.py fill ... [--now] [--only facebook] [--submit]
#   5. after        scheduled: LinkedIn post + Facebook event links from Ecamm's saved permalinks.
#                   live now: ecamm-video-transport.py play the moment Ecamm is live, then a background watcher waits for the broadcast to end, then
#                   ecamm-broadcast-form.py restore puts LinkedIn and Scheduled back (both stick in Ecamm).
#                   dry run with --only facebook: restore runs right away.
# After a replay, Ecamm also saved its own recording in ~/Movies/Ecamm Live Recordings; delete it if you do not need it.
# Ecamm does not save the Facebook post link; find it on your profile's Videos tab.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TITLE="" DESC="" THUMB="" MINUTE="" GO="" NOW="" ONLY="" VIDEO=""
while [ $# -gt 0 ]; do
  case "$1" in
    --title) TITLE="$2"; shift 2 ;;
    --desc-file) DESC="$2"; shift 2 ;;
    --thumb) THUMB="$2"; shift 2 ;;
    --minute) MINUTE="$2"; shift 2 ;;
    --video) VIDEO="$2"; shift 2 ;;
    --only) ONLY="$2"; shift 2 ;;
    --now) NOW=1; shift ;;
    --go) GO=1; shift ;;
    *) echo "unknown argument: $1"; exit 2 ;;
  esac
done
usage() { sed -n '2,6p' "$0"; exit 2; }
[ -n "$TITLE" ] && [ -f "$DESC" ] || usage
[ -n "$NOW" ] || [ -f "$THUMB" ] || usage
[ -z "$NOW" ] || { [ -z "$THUMB" ] && [ -z "$MINUTE" ]; } || usage
[ -z "$VIDEO" ] || [ -f "$VIDEO" ] || { echo "no such video: $VIDEO"; exit 2; }
[ -z "$ONLY" ] || [ "$ONLY" = facebook ] || usage

FORM="$HERE/ecamm-broadcast-form.py"
ONLY_ARGS=(); [ -n "$ONLY" ] && ONLY_ARGS=(--only "$ONLY")
step() { echo; echo "== $1"; }
restore() { python3 "$FORM" restore || echo "!! LinkedIn/Scheduled NOT restored; run: python3 $FORM restore"; }
fail() { echo "STOPPED at: $1"; [ -n "$ONLY" ] && restore; exit 1; }

if [ -n "$VIDEO" ]; then
  step "0. Load video"
  python3 "$HERE/ecamm-load-video.py" "$VIDEO" || fail "load video"
fi
step "0b. Cue video to 0:00, paused"
python3 "$HERE/ecamm-video-transport.py" cue || fail "cue video"

step "1. Destinations ($([ -n "$ONLY" ] && echo "Facebook only" || echo "Facebook and LinkedIn"))"
python3 "$FORM" check ${ONLY_ARGS[@]+"${ONLY_ARGS[@]}"} || fail "connections"

step "2. Mic muted"
python3 "$HERE/ecamm-mic-mute.py" mute || fail "mic mute"

step "3. When Video Ends = End Broadcast"
echo "   (waits up to 10 minutes for a natural pause before taking the mouse ~2s)"
python3 "$HERE/ecamm-end-behavior.py" set end-broadcast --wait-idle 600 || fail "end behavior (you were busy for 10 minutes, or controls hidden)"

MODE="$([ -n "$NOW" ] && echo "GO LIVE NOW" || echo SCHEDULE)"
step "4. Broadcast form ($([ -n "$GO" ] && echo "$MODE" || echo "dry run, $MODE"))"
args=(fill --title "$TITLE" --desc-file "$DESC" --shot "${TMPDIR:-/tmp}/ecamm-form.png" ${ONLY_ARGS[@]+"${ONLY_ARGS[@]}"})
[ -n "$THUMB" ] && args+=(--thumb "$THUMB")
[ -n "$MINUTE" ] && args+=(--minute "$MINUTE")
[ -n "$NOW" ] && args+=(--now)
[ -n "$GO" ] && args+=(--submit)
python3 "$FORM" "${args[@]}" || fail "broadcast form"

if [ -z "$GO" ]; then
  [ -n "$ONLY" ] && { step "5. Put LinkedIn back"; restore; }
elif [ -n "$NOW" ]; then
  step "5. Live: play the video"
  python3 "$HERE/ecamm-video-transport.py" play || echo "!! video did not start; run: python3 $HERE/ecamm-video-transport.py play"
  step "6. Watcher restores LinkedIn and Scheduled when the broadcast ends"
  LOG="$HERE/../logs/ecamm-restore.log"
  mkdir -p "$(dirname "$LOG")"
  nohup python3 "$FORM" restore --wait-live-end >>"$LOG" 2>&1 &
  echo "   watcher pid $!, log $LOG"
else
  step "5. Links"
  sleep 3
  TITLE="$TITLE" python3 - <<'PY'
import os, plistlib
p = plistlib.load(open(os.path.expanduser("~/Library/Preferences/com.ecamm.EcammLive.plist"), "rb"))
found = []
def walk(o):
    if isinstance(o, dict):
        if o.get("title") == os.environ["TITLE"] and o.get("permalinks"):
            found.append(o)
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(p)
if not found:
    print("no saved links yet for this title")
else:
    b = max(found, key=lambda o: o.get("start") or 0)
    for link in b["permalinks"]: print(link)
PY
  [ -n "$ONLY" ] && echo "   LinkedIn stays off in Ecamm until the scheduled live ends; then run: python3 $FORM restore"
fi
echo; echo "ALL CHECKS PASSED$([ -n "$GO" ] || echo ' (dry run, nothing created)')"
