#!/usr/bin/env python3
"""Local identity ledger over existing release records, never a deployment tool."""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

APP = "com.wpseoai.peoplecoral"


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def save(path, data):
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def initialize(directory, version, commit, platforms, scope, approval_ref):
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("version must be an explicit x.y.z")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("commit must be a full SHA")
    if not approval_ref.strip():
        raise ValueError("reference the user's scope/version authorization")
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    for name in ("notes", "artifacts", "evidence", "inputs"):
        (directory / name).mkdir(mode=0o700)
    save(directory / "context.json", {
        "schemaVersion": 1, "flavor": "wpseoai", "applicationId": APP,
        "version": version, "commit": commit, "platforms": sorted(set(platforms)),
        "scope": scope, "scopeApprovalRef": approval_ref, "builds": {},
    })


def validate_record(context, record, platform, artifact):
    expected = {
        "flavor": "wpseoai", "applicationId": APP, "platform": platform,
        "version": context["version"], "outcome": "uploaded",
        "artifactKind": "ipa" if platform == "ios" else "aab",
    }
    if platform not in context["platforms"]:
        raise ValueError("platform is outside approved scope")
    if any(record.get(key) != value for key, value in expected.items()):
        raise ValueError("release record does not match target identity/outcome")
    source = record.get("source", {})
    if (source.get("sha") != context["commit"] or source.get("clean") is not True
            or source.get("nonReleaseTest") is not False):
        raise ValueError("release record does not match clean target commit")
    if not re.fullmatch(r"[1-9]\d*", str(record.get("buildNumber", ""))):
        raise ValueError("release record has no valid build number")
    if digest(artifact) != record.get("artifactSha256"):
        raise ValueError("artifact hash does not match uploaded record")


def bind(directory, context, platform, record_path, artifact):
    record = json.loads(record_path.read_text())
    validate_record(context, record, platform, artifact)
    identity = {"buildNumber": str(record["buildNumber"]),
                "sha256": record["artifactSha256"], "record": str(record_path.resolve())}
    previous = context["builds"].get(platform)
    if previous:
        if any(previous.get(key) != value for key, value in identity.items()):
            raise ValueError("platform already bound; use a new run for another build")
        check(directory, context)
        return
    target = directory / "artifacts" / f"{platform}-{identity['buildNumber']}.{record['artifactKind']}"
    # Copy privately and verify before publishing, including interrupted-copy recovery.
    fd, temporary = tempfile.mkstemp(dir=target.parent)
    os.close(fd)
    try:
        shutil.copyfile(artifact, temporary)
        if digest(temporary) != identity["sha256"]:
            raise ValueError("artifact changed while being copied")
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    identity["artifact"] = str(target.relative_to(directory))
    context["builds"][platform] = identity
    save(directory / "context.json", context)


def check(directory, context):
    for platform, binding in context["builds"].items():
        record = json.loads(Path(binding["record"]).read_text())
        artifact = (directory / binding["artifact"]).resolve()
        if directory.resolve() not in artifact.parents:
            raise ValueError("artifact must be inside this run")
        validate_record(context, record, platform, artifact)
        if (str(record["buildNumber"]) != binding["buildNumber"]
                or record["artifactSha256"] != binding["sha256"]):
            raise ValueError("bound record identity changed")
    missing = sorted(set(context["platforms"]) - set(context["builds"]))
    return missing


ACTIONS = {"ios": ("submit",), "android": ("promote", "rollout", "halt")}
RELEASE_MODES = ("manual-phased", "manual-immediate", "automatic-phased", "automatic-immediate")


def approve(directory, context, platform, action, ref, rollout=None, release_mode=None,
            expires_hours=24, now=None):
    """Record one user approval in approvals.json, the file the make lanes require
    (approval=$RUN/approvals.json). Binds it to the bound build, not to 'latest'."""
    if action not in ACTIONS.get(platform, ()):
        raise ValueError(f"{action} is not a {platform} production action")
    if not ref.strip():
        raise ValueError("reference the user's approval message")
    build = context["builds"].get(platform)
    if not build:
        raise ValueError(f"{platform} has no bound build; bind the uploaded record first")
    check(directory, context)
    entry = {"platform": platform, "action": action, "version": context["version"],
             "build": build["buildNumber"], "artifactSha256": build["sha256"], "ref": ref}
    if platform == "android":
        if rollout is None or not 0 < float(rollout) <= 1:
            raise ValueError("android approvals need --rollout in (0, 1]")
        entry["rollout"] = str(float(rollout))
    else:
        if release_mode not in RELEASE_MODES:
            raise ValueError(f"ios approvals need --release-mode, one of {', '.join(RELEASE_MODES)}")
        entry["releaseMode"] = release_mode
    now = now or datetime.datetime.now(datetime.timezone.utc)
    entry["approvedAt"] = now.isoformat(timespec="seconds")
    entry["expiresAt"] = (now + datetime.timedelta(hours=expires_hours)).isoformat(timespec="seconds")
    path = directory / "approvals.json"
    data = json.loads(path.read_text()) if path.exists() else {"approvals": []}
    data["approvals"].append(entry)
    save(path, data)
    return entry


def log_decision(directory, phase, decision, reason, evidence="", now=None):
    """Append one row to decisions.tsv so a resumed or reviewing agent sees why."""
    def clean(value):
        return " ".join(str(value).split())
    now = now or datetime.datetime.now(datetime.timezone.utc)
    path = directory / "decisions.tsv"
    new = not path.exists()
    with path.open("a") as stream:
        if new:
            stream.write("at\tphase\tdecision\treason\tevidence\n")
        stream.write("\t".join(clean(v) for v in (now.isoformat(timespec="seconds"), phase,
                                                   decision, reason, evidence)) + "\n")


def history(root, limit=5):
    """Newest runs first, derived from each run's own files (nothing to keep in sync)."""
    runs = []
    for context_file in Path(root).glob("*/context.json"):
        try:
            context = json.loads(context_file.read_text())
        except (OSError, ValueError):
            continue
        run = context_file.parent
        entry = {"run": run.name, "version": context.get("version"), "scope": context.get("scope"),
                 "commit": str(context.get("commit", ""))[:10],
                 "builds": {p: b.get("buildNumber") for p, b in context.get("builds", {}).items()},
                 "evidence": {}, "modified": context_file.stat().st_mtime}
        for platform in context.get("platforms", []):
            evidence = run / "evidence" / f"{platform}.json"
            try:
                data = json.loads(evidence.read_text())
                entry["evidence"][platform] = {k: data.get(k) for k in ("level", "firstLaunch")}
            except (OSError, ValueError):
                entry["evidence"][platform] = None
        runs.append(entry)
    runs.sort(key=lambda r: r.pop("modified"), reverse=True)
    return runs[:limit]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--directory", type=Path, required=True)
    init.add_argument("--version", required=True)
    init.add_argument("--commit", required=True)
    init.add_argument("--platform", choices=("ios", "android"), action="append", required=True)
    init.add_argument("--scope", choices=("full-release", "testing", "verify", "submit", "promote", "rollout"),
                      required=True)
    init.add_argument("--approval-ref", required=True, help="Message ID, not credentials or full transcript")
    attach = sub.add_parser("bind")
    attach.add_argument("--directory", type=Path, required=True)
    attach.add_argument("--platform", choices=("ios", "android"), required=True)
    attach.add_argument("--record", type=Path, required=True)
    attach.add_argument("--artifact", type=Path, required=True)
    verify = sub.add_parser("check")
    verify.add_argument("--directory", type=Path, required=True)
    verify.add_argument("--require-all", action="store_true")
    past = sub.add_parser("history", help="list recent runs under a runs root (read-only)")
    past.add_argument("--root", type=Path, required=True)
    past.add_argument("--limit", type=int, default=5)
    grant = sub.add_parser("approve", help="record a user's production approval for the lanes")
    grant.add_argument("--directory", type=Path, required=True)
    grant.add_argument("--platform", choices=("ios", "android"), required=True)
    grant.add_argument("--action", choices=("submit", "promote", "rollout", "halt"), required=True)
    grant.add_argument("--ref", required=True, help="the user's approval message id or quote, no credentials")
    grant.add_argument("--rollout", type=float, help="android fraction, e.g. 1 or 0.2")
    grant.add_argument("--release-mode", choices=RELEASE_MODES, help="ios, e.g. manual-phased")
    grant.add_argument("--expires-hours", type=int, default=24)
    note = sub.add_parser("log", help="append a row to decisions.tsv")
    note.add_argument("--directory", type=Path, required=True)
    note.add_argument("--phase", required=True)
    note.add_argument("--decision", required=True)
    note.add_argument("--reason", required=True)
    note.add_argument("--evidence", default="")
    args = parser.parse_args()
    try:
        if args.command == "history":
            for entry in history(args.root, args.limit):
                print(json.dumps(entry))
            return 0
        if args.command == "log":
            log_decision(args.directory, args.phase, args.decision, args.reason, args.evidence)
            return 0
        if args.command == "init":
            initialize(args.directory, args.version, args.commit, args.platform,
                       args.scope, args.approval_ref)
        else:
            with (args.directory / ".lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                context = json.loads((args.directory / "context.json").read_text())
                if args.command == "bind":
                    bind(args.directory, context, args.platform, args.record, args.artifact)
                elif args.command == "approve":
                    entry = approve(args.directory, context, args.platform, args.action, args.ref,
                                    args.rollout, args.release_mode, args.expires_hours)
                    print(json.dumps(entry))
                    print(f"pass approval={args.directory / 'approvals.json'} to the make lane")
                    return 0
                else:
                    missing = check(args.directory, context)
                    if args.require_all and missing:
                        raise ValueError("some platforms have no bound uploaded build")
                    print(json.dumps({"identity": "verified", "missingPlatforms": missing,
                                      "productionApproved": False}))
                    return 0
        print("PASS local release context updated; this is not production approval")
        return 0
    except ValueError as error:
        print("BLOCKED " + str(error), file=sys.stderr)
    except Exception:
        print("BLOCKED context operation failed; inspect local inputs before retrying", file=sys.stderr)
    return 2


if __name__ == "__main__":
    os.umask(0o077)
    sys.exit(main())
