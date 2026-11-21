# ecamm-runner

Run an Ecamm Live broadcast of a video file from the command line on macOS: schedule it, or go live now, to Facebook and LinkedIn or to Facebook alone. Nothing is clicked by hand. Every step checks its own result and stops on a wrong state.

```
bin/run-ecamm-stream.sh --video replay.mp4 --title "My title" --desc-file description.txt --now --only facebook
```

That one command:

1. Loads `replay.mp4` as the scene's video and rewinds it to 0:00, paused.
2. Checks the destinations (Facebook and LinkedIn, or Facebook alone) and that the accounts are connected.
3. Mutes your mic in Ecamm (a replay should not carry the room).
4. Sets **When Video Ends** to **End Broadcast**, so the live stops on its own.
5. Fills the Create New Broadcast form, reads every field back and saves a screenshot.
6. **Dry run by default**: it then presses Cancel. Add `--go` to really schedule or go live.
7. With `--now --go`: starts the video the moment Ecamm is live, then waits for the broadcast to end and puts your destinations and the Scheduled setting back.

## Requirements

- macOS with Ecamm Live (tested on 4.6.3), signed in to the destinations you stream to.
- Your terminal (or whatever runs the script) allowed under System Settings > Privacy & Security > **Accessibility** and **Screen Recording**.
- Python 3 with `pyobjc-framework-Quartz` and `Pillow`: `python3 -m pip install -r requirements.txt`

## Settings

Create `~/.config/ecamm-runner/settings.json`:

```json
{
  "account_name": "Jane Doe",
  "mic": "RODECaster Pro II Chat"
}
```

- `account_name`: the name shown on your destination pills in Create New Broadcast. Needed for `--only facebook`, which removes LinkedIn for one broadcast and adds it back afterward.
- `mic`: the row name in Ecamm's **Sound Levels** window. Leave it out to skip muting.
- `end_menu_offsets` (optional): where the When Video Ends menu items sit, in points below the control. The defaults fit Ecamm 4.6.

## Usage

```
bin/run-ecamm-stream.sh --title T --desc-file F [--video FILE] [--thumb IMG] [--minute MM] [--now] [--only facebook] [--go]
```

| Option | Meaning |
|---|---|
| `--video FILE` | Load this file into the current scene first. Leave it out if the video is already loaded. |
| `--thumb IMG` | Thumbnail for a scheduled broadcast (required unless `--now`). |
| `--minute MM` | Scheduled start minute. Ecamm's default is about 10 minutes out, the soonest Facebook accepts. |
| `--now` | Go Live Now instead of scheduling. Ecamm shows no thumbnail here. |
| `--only facebook` | Stream to Facebook alone. |
| `--go` | Really do it. Without it, everything runs and the form is cancelled. |

Each step is also its own script in `bin/` (`--help` or no arguments prints usage):

- `ecamm-load-video.py FILE`: load a video as the scene source
- `ecamm-video-transport.py status|cue|play|pause`: control the scene video without the mouse
- `ecamm-mic-mute.py status|mute|unmute|toggle`: the mic's MUTE button in Sound Levels
- `ecamm-end-behavior.py status|set end-broadcast|do-nothing|loop|next-scene`: When Video Ends
- `ecamm-broadcast-form.py check|fill|restore`: the Create New Broadcast form

## Good to know

- **The mouse is borrowed once, for about 2 seconds.** When Video Ends is a hover-only control. The script waits until you have not touched the mouse or keyboard for 3 seconds. Everything else goes through Accessibility, so your cursor is left alone.
- **Keystrokes only go to Ecamm.** The file chooser needs two keystrokes; the script refuses to type unless Ecamm is the frontmost app.
- **Ecamm remembers destination changes.** A removed destination stays removed for the next broadcast, so `--only facebook` always puts it back (right away on a dry run, after the live ends on `--now --go`).
- **Ecamm does not save the Facebook post link** after a Go Live Now broadcast. Find it on your profile's Videos tab.
- **Ecamm keeps its own recording** of every broadcast in `~/Movies/Ecamm Live Recordings`. For a replay of a file you already have, you can delete it.
- **Ecamm updates can move things.** If a step starts failing after an update, [docs/how-it-works.md](docs/how-it-works.md) explains what each script looks for.

This is an independent project, not made by or affiliated with Ecamm.

## License

MIT
