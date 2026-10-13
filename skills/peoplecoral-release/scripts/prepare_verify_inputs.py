#!/usr/bin/env python3
"""Collect the inputs verify_review_account.py needs for one bound artifact.

Extracts the bundled configs/env/wpseoai.env from the uploaded AAB/IPA (the
backend a fresh install falls back to) and fetches the current Remote Config
template of peoplecoral-prod with the installed firebase CLI (read-only).
Writes into <run>/inputs/ (mode 600) and prints a JSON summary with hashes
and backend hosts on stdout. Never prints file contents.

Exit: 0 ready, 2 blocked (missing artifact, ambiguous env, fetch failed).

Example:
  prepare_verify_inputs.py --run "$RUN" --platform android \
    --artifact "$RUN/artifacts/android-163.aab"
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import zipfile
from pathlib import Path

ENV_SUFFIX = "flutter_assets/configs/env/wpseoai.env"
PROJECT = "peoplecoral-prod"


class Blocked(Exception):
    pass


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def host(url):
    return urllib.parse.urlsplit(url or "").hostname or ""


def env_api(text):
    values = [line.split("=", 1)[1].strip().strip("'\"")
              for line in text.splitlines() if line.startswith("API_ENDPOINT=")]
    return values[0] if len(values) == 1 else ""


def extract_env(artifact):
    try:
        with zipfile.ZipFile(artifact) as archive:
            members = [m for m in archive.namelist() if m.endswith(ENV_SUFFIX)]
            if len(members) != 1:
                raise Blocked(f"expected one {ENV_SUFFIX} in the artifact, found {len(members)}")
            return members[0], archive.read(members[0])
    except zipfile.BadZipFile:
        raise Blocked("artifact is not a zip (AAB/IPA)")


def fetch_remote_config(project):
    firebase = shutil.which("firebase")
    if not firebase:
        raise Blocked("firebase CLI not installed; install it once (npm i -g firebase-tools), "
                      "do not use npx @latest during a release")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "rc.json"
        result = subprocess.run([firebase, "remoteconfig:get", "--project", project, "-o", str(out)],
                                cwd=tmp, capture_output=True, timeout=120)
        if result.returncode != 0 or not out.exists():
            raise Blocked("firebase remoteconfig:get failed; check `firebase login` "
                          "and access to " + project)
        return out.read_bytes()


def remote_base_url(template):
    parameter = template.get("parameters", {}).get("base_url", {})
    return parameter.get("defaultValue", {}).get("value", ""), bool(parameter.get("conditionalValues"))


def write_private(path, data):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)


def prepare(run, platform, artifact, project=PROJECT, fetch=fetch_remote_config):
    if not artifact.is_file():
        raise Blocked(f"artifact not found: {artifact}")
    member, env_bytes = extract_env(artifact)
    rc_bytes = fetch(project)
    try:
        template = json.loads(rc_bytes)
    except ValueError:
        raise Blocked("Remote Config template is not JSON")
    remote_url, conditional = remote_base_url(template)
    inputs = run / "inputs"
    write_private(inputs / f"{platform}-bundled.env", env_bytes)
    write_private(inputs / "remote-config.json", rc_bytes)
    summary = {
        "platform": platform,
        "artifact": str(artifact),
        "artifactSha256": sha256(artifact.read_bytes()),
        "bundledEnv": {"member": member, "sha256": sha256(env_bytes),
                       "path": str(inputs / f"{platform}-bundled.env"),
                       "host": host(env_api(env_bytes.decode("utf-8", "replace")))},
        # `firebase remoteconfig:get` output carries no version number; the hash identifies it.
        "remoteConfig": {"project": project, "sha256": sha256(rc_bytes),
                         "path": str(inputs / "remote-config.json"),
                         "host": host(remote_url), "conditional": conditional},
        "fetchedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }
    summary["sameBackend"] = summary["bundledEnv"]["host"] == summary["remoteConfig"]["host"]
    write_private(inputs / f"{platform}-inputs.json", json.dumps(summary, indent=2).encode())
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, required=True, help="release run directory")
    parser.add_argument("--platform", choices=("ios", "android"), required=True)
    parser.add_argument("--artifact", type=Path, required=True, help="bound AAB or IPA")
    parser.add_argument("--project", default=PROJECT)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(prepare(args.run, args.platform, args.artifact, args.project), indent=2))
        return 0
    except Blocked as error:
        print("BLOCKED " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    os.umask(0o077)
    sys.exit(main())
