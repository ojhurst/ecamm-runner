<!-- md-ok: public GitHub repo docs, rendered on GitHub next to the README -->
# How it works

This page lists what each script looks for in Ecamm Live, so you can fix a script when an Ecamm update moves something. Everything here was worked out on Ecamm Live 4.6 on macOS.

## Seeing Ecamm without bringing it forward

- **You can capture a window by its ID, even with other windows on top of it.** `screencapture -x -o -l <id> out.png` grabs the window's own pixels. Find the ID with Quartz `CGWindowListCopyWindowInfo`. The owner name is `Ecamm`, not `Ecamm Live`.
- **The main window** is the `Ecamm` window with more than 20 UI elements. `window 1` changes as other Ecamm windows come forward, so never rely on it.

## The video in the scene (`ecamm-load-video.py`, `ecamm-video-transport.py`)

- Source > Video File > Choose File... opens the file chooser as a sheet on the main window. Source > Video File > Recent Items lists the newest file first, which proves the file loaded.
- **A loaded video starts playing right away.**
- The preview's hover-only controls stay in the main window's Accessibility tree even while hidden. They include `Play/Pause Video`, `Rewind Video`, `Fast Forward Video`, `Movie End Behavior Menu` and `Movie Scrub Bar`. Each appears as `AXUnknown` at position `0,1080` with size `0,0`. **AXPress works on Play/Pause and Rewind while they are hidden.** Each Rewind press jumps back about 30 seconds.
- **The proof for play and pause** is the scene name element, for example `New Scene 02:28`. While the video plays, it counts down the time left. During a live broadcast, a separate `LIVE 0:18` element counts the broadcast time up. Skip that element, or a paused video looks like it is playing.

## The file chooser (`choose_file` in `ecamm-broadcast-form.py`)

- Cmd+Shift+G opens Go To Folder as a sheet on top of the chooser sheet (`sheet 1 of sheet 1 of <window>`). It can take a few seconds to appear.
- Its `text field 1` takes the path through Accessibility. **Return only works after the field has Accessibility focus.** `AXConfirm` does nothing. After Return, press `Open` through Accessibility.
- Do not paste the path. A clipboard manager can replace the clipboard between the copy and the paste.

## When Video Ends (`ecamm-end-behavior.py`)

- The Accessibility tree does not show the current choice, and `AXPress` on `Movie End Behavior Menu` opens nothing. The menu needs a real click while the mouse is over the preview.
- Move the mouse with Quartz `CGEventPost`, because cliclick can miss its target on a second display. Hover over the preview, read the control's real position from Accessibility, and click its center.
- The menu opens as its own window. Its items sit at fixed distances below the control's center, in points: Do Nothing +45, Loop Video +69, Go To Next Scene +93, End Broadcast +141. The script finds the checked item in a screenshot of the open menu.
- The first hover after a window change sometimes does not register, so the script tries the hover up to 3 times.
- The main window can move between displays. Always read its position fresh, and never reuse a saved coordinate.

## The mic (`ecamm-mic-mute.py`)

- The MUTE button on your mic's row in the Sound Levels window responds to an Accessibility press. Accessibility does not report whether it is muted, so the script reads that from a capture of the window. A muted button is bright white (brightness about 254) and a live one is dim gray (about 182). The cutoff is 220.

## Create New Broadcast (`ecamm-broadcast-form.py`)

- Ecamm > Create New Broadcast... opens the form. The destinations take about 2 seconds to load from the platforms.
- **Both destination pills show only your account name.** The script tells them apart by what each one adds to the form: LinkedIn adds a "Generate Automatic Captions (English)" checkbox, and Facebook adds the Privacy pop-up.
- Each pill has a `Remove Destination` button. **A removed destination stays removed for every later broadcast**, and choosing Go Live Now sticks the same way. `restore` adds the destination back and selects Scheduled again.
- The `Add New Destination` menu lists the destinations that are not on the form. Each name starts with a space (`" Jane Doe"`). Three quirks:
  - The menu only exists while it is open.
  - You can only reach it through a button saved in a variable, not through a `whose` filter.
  - On a freshly opened form, the first press is sometimes ignored.
- **Go Live Now (Unscheduled)** and **Scheduled Start Time:** are radio buttons. Go Live Now hides the date and the thumbnail, and the main button changes to `Go Live Now`.
- The date field does not report its value through Accessibility, so the saved screenshot is the record of the start time.
- When a thumbnail loads, its button loses the name "Add Image". If it still says "Add Image", the upload failed.
- Ecamm > End Live Session is only enabled while a broadcast is live. That is how the script knows when the broadcast started and when it ended.
- When a broadcast ends, Ecamm may offer to install an update and relaunch. `restore` waits for Ecamm to come back.
