#!/usr/bin/env python3
"""Fill the App Review demo account from App Store Connect into the app's login form.

Credentials stay in this process. iOS: agent-device `fill` text (even with
--record-as) reaches the XCTest runner.log and .xcresult logs, so the value goes
through the simulator pasteboard (simctl pbcopy via stdin) and the edit-menu
Paste, then the pasteboard is cleared. Android: `fill` was verified not to
persist text (agent-device 0.21.8). Afterwards ~/.agent-device and TMPDIR are
scanned; files are listed, never scrubbed.

Exit: 0 filled (and logged in with --submit), 1 fill/login failed,
2 blocked (inputs), 3 password found on disk. The username may appear in iOS
XCTest logs (it reads field values); that is reported, not a failure.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
USER_PLACEHOLDER = "Enter your username or email"
PASSWORD_PLACEHOLDER = "Enter password"
EDITABLE_TYPES = ("textfield", "securetextfield", "edittext", "text-field")


class Blocked(Exception):
    pass


class Failed(Exception):
    pass


def nodes(tree):
    found = []

    def walk(item):
        if isinstance(item, dict):
            if item.get("ref"):
                found.append(item)
            for value in item.values():
                walk(value)
        elif isinstance(item, list):
            for value in item:
                walk(value)

    walk(tree)
    return found


def ref(node):
    value = str(node["ref"])
    return value if value.startswith("@") else "@" + value


def label(node):
    return str(node.get("label") or node.get("value") or "")


def input_fields(tree):
    """Login inputs in screen order. iOS sometimes reports them as Other."""
    all_nodes = nodes(tree)
    editable = [n for n in all_nodes
                if n.get("editable") or str(n.get("type", "")).lower().replace(" ", "")
                .endswith(EDITABLE_TYPES)]
    if len(editable) >= 2:
        return editable[:2]
    # Fallback: the node right after each field caption ("Username or email *", "Password *").
    found = []
    for caption in ("Username or email", "Password"):
        for index, node in enumerate(all_nodes[:-1]):
            if label(node).startswith(caption) and label(node).rstrip().endswith("*"):
                found.append(all_nodes[index + 1])
                break
    return found if len(found) == 2 else editable


def paste_item(tree):
    # The edit menu exposes a container, the item and its text, all labelled "Paste";
    # only the item (MenuItem on iOS 27, cell on iOS 26) accepts a press.
    candidates = [n for n in nodes(tree) if label(n) == "Paste"]
    for wanted in ("menuitem", "cell"):
        for node in candidates:
            if str(node.get("type", "")).lower().replace(" ", "") == wanted:
                return node
    return None


def masked_matches(text, secret):
    return text == "\u2022" * len(secret)


def leaked_files(secrets, roots, since):
    hits = []
    needles = [s.encode() for s in secrets if s]
    for root in roots:
        for directory, _, files in os.walk(root):
            for name in files:
                path = Path(directory, name)
                try:
                    if path.stat().st_mtime < since or path.stat().st_size > 200_000_000:
                        continue
                    data = path.read_bytes()
                except OSError:
                    continue
                if any(n in data for n in needles):
                    hits.append(str(path))
    return hits


def credentials(version_id):
    try:
        result = subprocess.run(
            [str(SCRIPTS / "asc.sh"), "review", "details-for-version", "--version-id", version_id,
             "--include-sensitive", "--output", "json"],
            capture_output=True, check=True, timeout=60)
        document = json.loads(result.stdout)
    except Exception:
        raise Blocked("could not read review details from App Store Connect")
    data = document.get("data", document) if isinstance(document, dict) else document
    if isinstance(data, list):
        data = data[0] if len(data) == 1 else {}
    data = data.get("attributes", data) if isinstance(data, dict) else {}
    user, password = data.get("demoAccountName"), data.get("demoAccountPassword")
    if not all(isinstance(v, str) and v and v != "(redacted)" for v in (user, password)):
        raise Blocked("review account is missing or redacted in App Store Connect")
    return user, password


class Device:
    def __init__(self, session, selector=()):
        self.session = session
        # With several devices booted, agent-device reports AMBIGUOUS_MATCH unless
        # every command names the device, even inside a named session.
        self.selector = list(selector)

    def run(self, *args, stdin=None, check=True):
        # Output is discarded: agent-device may echo arguments in errors.
        result = subprocess.run(["agent-device", *args, "--session", self.session, *self.selector],
                                input=stdin, capture_output=True, timeout=120)
        if check and result.returncode != 0:
            raise Failed(f"agent-device {args[0]} failed")
        return result

    def snapshot(self):
        result = self.run("snapshot", "-i", "--json")
        try:
            return json.loads(result.stdout)
        except ValueError:
            raise Failed("snapshot was not JSON")

    def field(self, index):
        fields = input_fields(self.snapshot())
        if len(fields) < 2:
            raise Failed(f"found {len(fields)} login field(s), expected 2; is the login screen open?")
        return fields[index]


def ios_paste(device, udid, index, value):
    def pbcopy(text):
        subprocess.run(["xcrun", "simctl", "pbcopy", udid], input=text.encode(),
                       check=True, capture_output=True, timeout=30)
    try:
        pbcopy(value)
        device.run("longpress", ref(device.field(index)))
        time.sleep(1.5)
        item = paste_item(device.snapshot())
        if item is None:
            raise Failed("edit menu has no Paste item")
        device.run("press", ref(item))
        time.sleep(1)
    finally:
        try:
            pbcopy("")
        except Exception:
            print("WARN could not clear the simulator pasteboard; clear it before sharing the device")


def fill(args, user, password):
    if args.platform == "ios":
        selector = ["--platform", "ios", "--udid", args.udid]
    else:
        selector = ["--platform", "android"] + (["--serial", args.serial] if args.serial else [])
    device = Device(args.session, selector)
    for index, value in ((0, user), (1, password)):
        if args.platform == "ios":
            current = label(device.field(index))
            if current not in (USER_PLACEHOLDER, PASSWORD_PLACEHOLDER, ""):
                raise Failed("login field is not empty; reinstall for a clean first launch")
            ios_paste(device, args.udid, index, value)
        else:
            device.run("fill", ref(device.field(index)), value)
        time.sleep(0.5)
    shown_user, shown_password = (label(f) for f in input_fields(device.snapshot())[:2])
    if shown_user != user or not masked_matches(shown_password, password):
        raise Failed("fields do not hold the expected account after filling")
    print("filled username and password from App Store Connect review details")
    if args.submit:
        device.run("keyboard", "dismiss", check=False)
        log_in = next((n for n in nodes(device.snapshot()) if label(n) == "Log In"), None)
        if log_in is None:
            raise Failed("Log In control not found")
        device.run("press", ref(log_in))
        deadline = time.time() + args.wait
        while time.time() < deadline:
            time.sleep(3)
            try:
                texts = [label(n) for n in nodes(device.snapshot())]
            except Failed:
                continue  # snapshots fail transiently while the app changes screens
            if any(t.startswith("Hi ") for t in texts) and any("Time Off" in t for t in texts):
                print("PASS logged in: Home dashboard visible")
                return
            if any(t in (USER_PLACEHOLDER, PASSWORD_PLACEHOLDER) for t in texts) and \
                    any(("recognize" in t or "incorrect" in t.lower() or "invalid" in t.lower())
                        for t in texts):
                raise Failed("login rejected on the login screen")
        raise Failed("Home dashboard not reached in time; inspect with a screenshot")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version-id", required=True,
                        help="App Store version whose review details hold the demo account")
    parser.add_argument("--platform", choices=("ios", "android"), required=True)
    parser.add_argument("--session", required=True, help="agent-device session opened on the login screen")
    parser.add_argument("--udid", help="iOS simulator UDID (required for ios)")
    parser.add_argument("--serial", help="Android device serial, e.g. emulator-5554 "
                        "(needed when more than one device is booted)")
    parser.add_argument("--submit", action="store_true", help="press Log In and wait for Home")
    parser.add_argument("--wait", type=int, default=30, help="seconds to wait for Home after Log In")
    args = parser.parse_args(argv)
    if args.platform == "ios" and not args.udid:
        parser.error("--udid is required for ios")
    start = time.time() - 1
    code = 0
    user = password = None
    try:
        user, password = credentials(args.version_id)
        fill(args, user, password)
    except Blocked as error:
        print("BLOCKED " + str(error))
        code = 2
    except Failed as error:
        print("FAIL " + str(error))
        code = 1
    except Exception:
        print("FAIL unexpected error while filling (details suppressed)")
        code = 1
    finally:
        if user and password:
            roots = [Path.home() / ".agent-device", Path(tempfile.gettempdir())]
            home = str(Path.home())
            password_hits = leaked_files([password], roots, start)
            # XCTest logs every AX value it reads, so the filled username lands in the
            # runner log on iOS. It is not a secret (it is stored in ASC); report it.
            user_hits = leaked_files([user], roots, start)
            if password_hits:
                print("FAIL the review password was written to disk in these files "
                      "(delete them; do not share them):")
                for path in password_hits:
                    print("  " + path.replace(home, "~"))
                code = 3
            else:
                print("leak scan: review password not found in ~/.agent-device or TMPDIR")
            if user_hits:
                print(f"note: username appears in {len(user_hits)} local agent-device log file(s); "
                      "do not attach those logs to reports")
    return code


if __name__ == "__main__":
    sys.exit(main())
