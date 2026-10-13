#!/usr/bin/env python3
"""API-only check of the App Review demo account on both backends a fresh
install can use: login without 2FA, GET /v1/auth/me, logout. Credentials are
read from App Store Connect into memory and never printed.

Inputs come from prepare_verify_inputs.py. Backend hosts must be approved:
pass --approved-hosts-file (JSON {"approvedBackendHosts": [...]}) and/or
--allow-host. An unapproved host stops before any credential is sent.

Exit: 0 pass, 1 fails on the Remote Config backend, 2 blocked (inputs),
4 a backend host needs the user's approval (the host is printed; add it to
the file only after the user confirms it), 5 passes on Remote Config but
fails on the bundled fallback (a warning for the approval gate, not a block).
"""
import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


class Blocked(Exception):
    pass


class NeedsApproval(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Blocked("backend redirect refused")


def endpoint(value, allowed_hosts):
    if not isinstance(value, str):
        raise Blocked("endpoint is missing")
    parsed = urllib.parse.urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment
            or parsed.port not in (None, 443)):
        raise Blocked("endpoint must be a plain HTTPS URL")
    if parsed.hostname not in allowed_hosts:
        raise NeedsApproval(parsed.hostname)
    return value.rstrip("/")


def approved_hosts(path, extra):
    hosts = set(extra or [])
    if path:
        try:
            hosts.update(json.loads(Path(path).read_text()).get("approvedBackendHosts", []))
        except FileNotFoundError:
            pass  # first run: every host needs approval
        except ValueError:
            raise Blocked("approved hosts file is not valid JSON")
    return hosts


def resolve_endpoints(template, env_text, allowed_hosts):
    parameter = template.get("parameters", {}).get("base_url", {})
    if parameter.get("conditionalValues"):
        raise Blocked("conditional Remote Config needs device-specific resolution")
    remote = parameter.get("defaultValue", {}).get("value")
    values = [line.split("=", 1)[1].strip().strip("'\"")
              for line in env_text.splitlines() if line.startswith("API_ENDPOINT=")]
    if len(values) != 1:
        raise Blocked("bundled env must contain exactly one API_ENDPOINT")
    # Validate both before sending any credentials to either backend.
    return list(dict.fromkeys(endpoint(v, allowed_hosts) for v in (remote, values[0])))


def credentials(document):
    data = document.get("data", document) if isinstance(document, dict) else document
    if isinstance(data, list):
        if len(data) != 1:
            raise Blocked("expected exactly one review account")
        data = data[0]
    if not isinstance(data, dict):
        raise Blocked("invalid review account response")
    data = data.get("attributes", data)
    user, password = data.get("demoAccountName"), data.get("demoAccountPassword")
    if not all(isinstance(v, str) and v and v != "(redacted)" for v in (user, password)):
        raise Blocked("review credentials are missing or redacted")
    return user, password


def http_call(api, method, path, body=None, token=None):
    request = urllib.request.Request(
        api + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    if token:
        request.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=20) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        # Never print or parse server error text: it may echo credentials.
        return error.code, {}


def check_account(user, password, call):
    token = None
    failures = []
    try:
        status, body = call("POST", "/v1/auth/login",
                            {"username": user, "password": password, "client_type": "mobile"})
        data = body.get("data", body) if isinstance(body, dict) else {}
        if not isinstance(data, dict):
            data = {}
        token = data.get("access_token")
        if not isinstance(token, str) or not token:
            token = None
        if status != 200:
            failures.append("login failed")
        elif data.get("requires_2fa"):
            failures.append("review account requires 2FA")
        elif token is None:
            failures.append("login returned no access token")
        else:
            status, _ = call("GET", "/v1/auth/me", token=token)
            if status != 200:
                failures.append("authenticated /me failed")
    except Exception:
        failures.append("backend request failed")
    finally:
        if token:
            try:
                status, _ = call("POST", "/v1/auth/logout", token=token)
                if status not in (200, 204):
                    failures.append("logout cleanup failed")
            except Exception:
                failures.append("logout cleanup failed")
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version-id", required=True,
                        help="App Store version whose review details hold the demo account")
    parser.add_argument("--remote-config", required=True, type=Path,
                        help="$RUN/inputs/remote-config.json from prepare_verify_inputs.py")
    parser.add_argument("--bundled-env", required=True, type=Path,
                        help="$RUN/inputs/<platform>-bundled.env from prepare_verify_inputs.py")
    parser.add_argument("--approved-hosts-file", type=Path,
                        help="JSON with approvedBackendHosts, kept outside the repo")
    parser.add_argument("--allow-host", action="append", help="extra approved hostname")
    args = parser.parse_args(argv)
    if not args.approved_hosts_file and not args.allow_host:
        parser.error("pass --approved-hosts-file or --allow-host")
    try:
        endpoints = resolve_endpoints(
            json.loads(args.remote_config.read_text()), args.bundled_env.read_text(),
            approved_hosts(args.approved_hosts_file, args.allow_host),
        )
        result = subprocess.run(
            [str(Path(__file__).with_name("asc.sh")), "review", "details-for-version",
             "--version-id", args.version_id, "--include-sensitive", "--output", "json"],
            capture_output=True, check=True, timeout=60,
        )
        user, password = credentials(json.loads(result.stdout))
        # endpoints[0] is Remote Config (what the app uses once it has fetched);
        # endpoints[1], when distinct, is the bundled fallback for a slow first launch.
        results = {}
        for index, api in enumerate(endpoints):
            role = "remote-config" if index == 0 else "bundled-fallback"
            results[role] = check_account(
                user, password,
                lambda method, path, body=None, token=None: http_call(api, method, path, body, token),
            )
            problems = results[role]
            print(f"{role}: " + ("FAIL " + "; ".join(problems) if problems else "PASS"))
        if results["remote-config"]:
            return 1
        if results.get("bundled-fallback"):
            print("WARN the account fails on the bundled fallback backend. A fresh install whose first "
                  "Remote Config fetch is slow will reject the reviewer. Show this at the approval gate.")
            return 5
        print("PASS API-only account check; device first-launch verification still required")
        return 0
    except NeedsApproval as error:
        print(f"NEEDS_APPROVAL backend host {error} is not approved; ask the user, then add it "
              "to approvedBackendHosts. No credentials were sent.")
        return 4
    except Blocked as error:
        print("BLOCKED " + str(error))
    except Exception:
        print("BLOCKED unable to read or validate required verification inputs")
    return 2


if __name__ == "__main__":
    sys.exit(main())
