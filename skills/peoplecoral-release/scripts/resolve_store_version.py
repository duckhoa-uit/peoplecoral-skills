#!/usr/bin/env python3
"""Resolve an exact editable iOS version. Reads by default; explicit create gate."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

APP = "6756572980"
EDITABLE = {"PREPARE_FOR_SUBMISSION", "DEVELOPER_REJECTED", "REJECTED", "METADATA_REJECTED"}


def select_version(document, version):
    # asc returns {"data": [...]}, or {"items": [...]} for some flags such as --latest.
    rows = (document.get("data", document.get("items"))
            if isinstance(document, dict) else document)
    if not isinstance(rows, list):
        raise ValueError("invalid versions response")
    matches = []
    for row in rows:
        attrs = row.get("attributes", {})
        if attrs.get("versionString") == version and attrs.get("platform") == "IOS":
            matches.append(row)
    if len(matches) > 1:
        raise ValueError("ambiguous target version")
    if not matches:
        return None
    row = matches[0]
    state = row["attributes"].get("appVersionState") or row["attributes"].get("appStoreState")
    if not row.get("id") or state not in EDITABLE:
        raise ValueError("target version is not editable; do not cancel review automatically")
    return {"appId": APP, "platform": "IOS", "version": version,
            "versionId": row["id"], "state": state}


def asc(arguments, write=False):
    env = dict(os.environ, ASC_WRITE="1" if write else "0",
               ASC_READ_ONLY="0" if write else "1")
    result = subprocess.run(
        [str(Path(__file__).with_name("asc.sh")), *arguments],
        env=env, capture_output=True, check=True, timeout=90,
    )
    return json.loads(result.stdout)


def resolve(version, create=False, confirm=False, run=asc):
    if create != confirm:
        raise ValueError("creating a draft requires both --create and --confirm")
    query = ["versions", "list", "--app", APP, "--platform", "IOS",
             "--version", version, "--paginate", "--output", "json"]
    target = select_version(run(query), version)
    if target is None:
        if not create:
            raise ValueError("target draft missing; creating it requires authorized --create --confirm")
        run(["versions", "create", "--app", APP, "--platform", "IOS",
             "--version", version, "--release-type", "MANUAL",
             "--if-exists", "skip", "--output", "json"], write=True)
        target = select_version(run(query), version)
        if target is None:
            raise ValueError("target version could not be read back")
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(resolve(args.version, args.create, args.confirm)))
        return 0
    except ValueError as error:
        print("BLOCKED " + str(error), file=sys.stderr)
    except Exception:
        print("BLOCKED App Store version operation failed; re-read before retrying", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
