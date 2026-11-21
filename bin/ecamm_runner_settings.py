"""Your Ecamm setup, read from ~/.config/ecamm-runner/settings.json (every key optional).

{
  "account_name": "Jane Doe",        # the name on your Facebook and LinkedIn destination pills
  "end_menu_offsets": {"do-nothing": 45, "loop": 69, "next-scene": 93, "end-broadcast": 141}
}

account_name is only needed for --only facebook and restore, which re-add a removed destination
from Ecamm's Add menu by name. end_menu_offsets are points below the When Video Ends control's
center; the defaults were measured on Ecamm 4.6 with the menu opening downward.
"""
import json, os

PATH = os.path.expanduser(os.environ.get("ECAMM_RUNNER_SETTINGS", "~/.config/ecamm-runner/settings.json"))
DEFAULTS = {
    "account_name": "",
    "end_menu_offsets": {"do-nothing": 45, "loop": 69, "next-scene": 93, "end-broadcast": 141},
}


def load():
    s = dict(DEFAULTS)
    if os.path.isfile(PATH):
        with open(PATH, encoding="utf-8") as f:
            s.update(json.load(f))
    return s


def require(key):
    v = load().get(key)
    if not v:
        raise RuntimeError(f'set "{key}" in {PATH} (see bin/ecamm_runner_settings.py)')
    return v
