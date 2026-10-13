#!/usr/bin/env python3
"""Read-only smoke sweep of the PeopleCoral app's main screens with agent-device.

Run it on a logged-in Home screen. For each feature in the sweep it opens the
screen (stable ids when the build has them, labels otherwise),
waits for it to settle, saves a screenshot and the snapshot text, classifies
the screen, and returns to Home. Never submits, sends or edits anything.

Writes <out>/<feature>.png, <out>/<feature>.txt and <out>/results.json;
prints one JSON line per feature. Exit: 0 every screen pass or valid-empty,
1 any fail, 2 blocked (not on Home, device unreachable), 3 not-verified
(timeouts, e.g. host overload).

Example:
  smoke.py --platform ios --udid <sim> --session qa --out "$RUN/evidence/ios"
  smoke.py --platform android --serial emulator-5554 --session qa --out /tmp/qa --only payslips
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

# (feature, how to reach it, text that proves the screen loaded)
SWEEP = [
    ("time-off", ("tile", "timeOff", "Time Off"), ("Pending", "Approved", "Rejected")),
    ("remote-work", ("tile", "remote", "Remote Work"), ("Pending", "Approved", "Rejected")),
    ("sick-leave", ("tile", "sickLeave", "Sick Leave"), ("Pending", "Approved", "Rejected")),
    ("overtime", ("tile", "overtime", "Overtime"), ("Pending", "Approved", "Rejected")),
    ("chat", ("tile", "chat", "Chat"), ("Chat", "Search")),
    ("contact", ("tile", "contact", "Contact"), ("Your Contacts", "Contact")),
    ("expenses", ("tile", "expense", "Expenses"), ("Expense Reimbursement",)),
    ("payslips", ("tile", "payslips", "Payslips"), ("Payslip",)),
    ("calendar", ("tab", "history", 1), ("Calendar",)),
    ("notifications", ("tab", "notifications", 2), ("Notification",)),
    ("profile", ("tab", "profile", 3), ("Personal Info", "Payroll", "Profile")),
]
# Missing tile is policy, not an app fail. Time Off / Remote / Contact / Payslips stay required.
OPTIONAL = {"overtime", "sick-leave", "chat", "expenses"}


def optional_tile_missing(feature, error):
    return feature in OPTIONAL and "not found" in str(error)
TAB_X = (0.14, 0.37, 0.61, 0.84)
TAB_Y = 0.94
ERROR = re.compile(r"something went wrong|try again|failed to load|network error|unexpected error"
                   r"|we don't recognize|no internet|server error|\b5\d\d\b", re.I)
EMPTY = re.compile(r"no (data|records?|requests?|payslips?|notifications?|messages?|contacts?|items?)"
                   r"|nothing (here|yet)|empty", re.I)


class Blocked(Exception):
    pass


class Timeout(Exception):
    pass


def classify(text, expect):
    """pass | valid-empty | fail, from the settled screen's accessibility text."""
    if ERROR.search(text):
        return "fail", "error text on screen"
    if any(word.lower() in text.lower() for word in expect):
        return ("valid-empty", "loaded, no records") if EMPTY.search(text) else ("pass", "loaded")
    return "fail", "expected content not found: " + ", ".join(expect)


def nodes(tree):
    out = []

    def walk(item):
        if isinstance(item, dict):
            if item.get("ref"):
                out.append(item)
            for value in item.values():
                walk(value)
        elif isinstance(item, list):
            for value in item:
                walk(value)
    walk(tree)
    return out


def screen_text(tree):
    seen = []
    for node in nodes(tree):
        label = str(node.get("label") or node.get("value") or "").strip()
        if label and "@" not in label:  # never keep e-mail addresses in evidence
            seen.append(label)
    return "\n".join(seen)


def find_by_identifier(tree, identifier):
    return next((n for n in nodes(tree) if n.get("identifier") == identifier), None)


def find_tile(tree, label, platform):
    """Home tiles: iOS lists the same label as [other] and [image]; only the image takes the press."""
    matches = [n for n in nodes(tree) if str(n.get("label") or "").split("\n")[0].strip() == label]
    if platform == "ios":
        images = [n for n in matches if str(n.get("type", "")).lower() == "image"]
        matches = images or matches
    return matches[0] if matches else None


def app_frame(tree):
    for node in nodes(tree):
        rect = node.get("rect") or node.get("frame")
        if str(node.get("type", "")).lower() == "application" and rect:
            return rect
    return None


def ref(node):
    value = str(node["ref"])
    return value if value.startswith("@") else "@" + value


class Device:
    def __init__(self, args):
        self.args = args
        self.selector = (["--platform", "ios", "--udid", args.udid] if args.platform == "ios"
                         else ["--platform", "android"] + (["--serial", args.serial] if args.serial else []))

    def run(self, *argv, timeout=None):
        try:
            result = subprocess.run(["agent-device", *argv, "--session", self.args.session, *self.selector],
                                    capture_output=True, text=True, timeout=timeout or self.args.timeout)
        except subprocess.TimeoutExpired:
            raise Timeout(f"agent-device {argv[0]} timed out")
        return result

    def snapshot(self):
        result = self.run("snapshot", "-i", "--json")
        try:
            data = json.loads(result.stdout)
        except ValueError:
            raise Timeout("snapshot returned no JSON")
        if data.get("success") is False:
            code = (data.get("error") or {}).get("code", "")
            if code == "SESSION_NOT_FOUND":
                raise Blocked("no agent-device session: open the app with this --session first")
            raise Timeout(f"snapshot failed: {code}")
        return data

    def press(self, *target):
        if self.run("press", *target).returncode != 0:
            raise Timeout("press failed")

    def screenshot(self, path):
        self.run("screenshot", str(path))

    def back(self, tree):
        if self.args.platform == "android":
            self.run("back")
            return
        buttons = [n for n in nodes(tree) if str(n.get("type", "")).lower() == "button"]
        if buttons:
            self.press(ref(buttons[0]))


def on_home(tree):
    """Logged-in Home. Greeting only. 'Time Off' also appears on the request list."""
    text = screen_text(tree)
    return text.startswith("Hi ") or "\nHi " in text


def open_feature(device, tree, how):
    kind, key, fallback = how
    identifier = f"home-tile-{key}" if kind == "tile" else f"bottom-tab-{key}"
    node = find_by_identifier(tree, identifier)
    if node:
        device.press(ref(node))
        return "id"
    if kind == "tile":
        node = find_tile(tree, fallback, device.args.platform)
        if node is None:
            device.run("scroll", "down", "--until", f'label="{fallback}"')
            tree = device.snapshot()
            node = find_tile(tree, fallback, device.args.platform)
        if node is None:
            raise Blocked(f"home tile {fallback} not found")
        device.press(ref(node))
        return "label"
    frame = app_frame(tree)
    if not frame:
        raise Blocked("cannot find the app frame for a coordinate tab tap")
    x = int(frame.get("x", 0) + frame["width"] * TAB_X[fallback])
    y = int(frame.get("y", 0) + frame["height"] * TAB_Y)
    device.press(str(x), str(y))
    return "coordinate"


def go_home(device):
    for _ in range(3):
        tree = device.snapshot()
        if on_home(tree):
            return tree
        frame = app_frame(tree)
        home_tab = find_by_identifier(tree, "bottom-tab-home")
        if home_tab:
            device.press(ref(home_tab))
        elif frame:
            device.press(str(int(frame.get("x", 0) + frame["width"] * TAB_X[0])),
                         str(int(frame.get("y", 0) + frame["height"] * TAB_Y)))
        else:
            device.back(tree)
        time.sleep(2)
    raise Blocked("could not return to Home")


def sweep(device, out, only=None, settle=4.0):
    out.mkdir(parents=True, exist_ok=True)
    results = []
    tree = device.snapshot()
    if not on_home(tree):
        raise Blocked("start on the logged-in Home screen")
    for feature, how, expect in SWEEP:
        if only and feature not in only:
            continue
        entry = {"feature": feature}
        try:
            tree = go_home(device)
            entry["selectedBy"] = open_feature(device, tree, how)
            time.sleep(settle)
            tree = device.snapshot()
            text = screen_text(tree)
            entry["result"], entry["why"] = classify(text, expect)
            device.screenshot(out / f"{feature}.png")
            (out / f"{feature}.txt").write_text(text)
            entry["screenshot"] = str(out / f"{feature}.png")
            if how[0] == "tile":
                device.back(tree)
                time.sleep(1)
        except Blocked as error:
            if optional_tile_missing(feature, error):
                entry["result"], entry["why"] = "valid-empty", str(error)
            else:
                raise
        except Timeout as error:
            entry["result"], entry["why"] = "not-verified", str(error)
        print(json.dumps(entry), flush=True)
        results.append(entry)
    (out / "results.json").write_text(json.dumps(results, indent=2))
    return results


def exit_code(results):
    states = {r["result"] for r in results}
    if "fail" in states:
        return 1
    if "not-verified" in states:
        return 3
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--platform", choices=("ios", "android"), required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--udid", help="iOS simulator UDID (required for ios)")
    parser.add_argument("--serial", help="Android serial, e.g. emulator-5554")
    parser.add_argument("--out", type=Path, required=True, help="evidence directory")
    parser.add_argument("--only", nargs="*", help="feature names, e.g. payslips chat")
    parser.add_argument("--settle", type=float, default=4.0, help="seconds to wait after opening a screen")
    parser.add_argument("--timeout", type=int, default=90, help="seconds per agent-device command")
    args = parser.parse_args(argv)
    if args.platform == "ios" and not args.udid:
        parser.error("--udid is required for ios")
    try:
        return exit_code(sweep(Device(args), args.out, set(args.only or []) or None, args.settle))
    except Blocked as error:
        print("BLOCKED " + str(error))
        return 2
    except Timeout as error:
        print("NOT-VERIFIED " + str(error) + " (check host load before treating this as an app problem)")
        return 3


if __name__ == "__main__":
    sys.exit(main())
