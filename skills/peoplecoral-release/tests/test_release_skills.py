"""Offline contract tests. No real credentials, stores, devices or network."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest.mock
import unittest
from unittest.mock import patch

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


account = load("verify_review_account")
filler = load("review_account_fill")
inputs = load("prepare_verify_inputs")
versions = load("resolve_store_version")
ledger = load("release_context")


class AccountTests(unittest.TestCase):
    def run_check(self, login=None, me=200, logout=204, raises=None):
        calls = []
        if login is None:
            login = (200, {"data": {"access_token": "fake-token"}})

        def call(method, path, body=None, token=None):
            calls.append(path)
            if path == raises:
                raise RuntimeError("fake-secret-should-not-appear")
            if path.endswith("/login"):
                return login
            return (me if path.endswith("/me") else logout), {}

        result = account.check_account("fake-user", "fake-password", call)
        return result, calls

    def test_success_and_cleanup(self):
        result, calls = self.run_check()
        self.assertEqual(result, [])
        self.assertEqual(calls, ["/v1/auth/login", "/v1/auth/me", "/v1/auth/logout"])

    def test_me_failure_is_blocking_and_logs_out(self):
        result, calls = self.run_check(me=401)
        self.assertIn("authenticated /me failed", result)
        self.assertEqual(calls[-1], "/v1/auth/logout")

    def test_me_exception_still_logs_out_and_is_sanitized(self):
        result, calls = self.run_check(raises="/v1/auth/me")
        self.assertEqual(result, ["backend request failed"])
        self.assertEqual(calls[-1], "/v1/auth/logout")

    def test_logout_failure_blocks(self):
        for status in (401, 500):
            with self.subTest(status=status):
                self.assertIn("logout cleanup failed", self.run_check(logout=status)[0])

    def test_logout_exception_blocks(self):
        self.assertIn("logout cleanup failed", self.run_check(raises="/v1/auth/logout")[0])

    def test_login_failure_does_not_echo_server_body(self):
        result, calls = self.run_check(login=(401, {"error": {"message": "fake-password"}}))
        self.assertEqual(result, ["login failed"])
        self.assertEqual(len(calls), 1)

    def test_missing_token_and_malformed_data(self):
        for body in ({}, {"data": None}, {"data": []}, {"data": {"access_token": 123}}):
            with self.subTest(body=body):
                self.assertEqual(self.run_check(login=(200, body))[0],
                                 ["login returned no access token"])

    def test_two_factor_blocks_even_if_token_is_present(self):
        result, calls = self.run_check(login=(200, {"requires_2fa": True, "access_token": "fake"}))
        self.assertEqual(result, ["review account requires 2FA"])
        self.assertEqual(calls[-1], "/v1/auth/logout")
        self.assertNotIn("/v1/auth/me", calls)

    def test_redacted_or_missing_credentials_block(self):
        for value in ("", "(redacted)", None):
            with self.subTest(value=value), self.assertRaises(account.Blocked):
                account.credentials({"data": {"attributes": {
                    "demoAccountName": "fake", "demoAccountPassword": value}}})

    def test_supported_review_response_shapes(self):
        attrs = {"demoAccountName": "fake", "demoAccountPassword": "dummy"}
        for shape in (attrs, {"attributes": attrs}, {"data": [{"attributes": attrs}]}):
            self.assertEqual(account.credentials(shape), ("fake", "dummy"))

    def test_redirects_are_refused(self):
        with self.assertRaises(account.Blocked):
            account.NoRedirect().redirect_request(None, None, 307, "", {}, "https://other.test")

    def test_endpoints_validate_before_credentials_are_sent(self):
        template = {"parameters": {"base_url": {"defaultValue": {"value": "https://good.test"}}}}
        self.assertEqual(account.resolve_endpoints(
            template, "API_ENDPOINT='https://good.test/'", {"good.test"}), ["https://good.test"])
        for env in ("", "API_ENDPOINT=http://good.test",
                    "API_ENDPOINT=https://user:pass@good.test",
                    "API_ENDPOINT=https://good.test?token=fake",
                    "API_ENDPOINT=https://good.test:444",
                    "API_ENDPOINT=https://good.test\nAPI_ENDPOINT=https://good.test"):
            with self.subTest(env=env), self.assertRaises(account.Blocked):
                account.resolve_endpoints(template, env, {"good.test"})

    def test_unapproved_host_needs_approval_and_names_it(self):
        template = {"parameters": {"base_url": {"defaultValue": {"value": "https://good.test"}}}}
        with self.assertRaises(account.NeedsApproval) as caught:
            account.resolve_endpoints(template, "API_ENDPOINT=https://other.test", {"good.test"})
        self.assertEqual(str(caught.exception), "other.test")

    def test_approved_hosts_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            self.assertEqual(account.approved_hosts(path, ["a.test"]), {"a.test"})  # missing file
            path.write_text(json.dumps({"approvedBackendHosts": ["b.test"]}))
            self.assertEqual(account.approved_hosts(path, ["a.test"]), {"a.test", "b.test"})
            path.write_text("{bad")
            with self.assertRaises(account.Blocked):
                account.approved_hosts(path, None)

    def test_main_exit_4_on_unapproved_host_without_reading_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, env = Path(tmp) / "rc.json", Path(tmp) / "a.env"
            rc.write_text(json.dumps({"parameters": {"base_url": {
                "defaultValue": {"value": "https://new.test"}}}}))
            env.write_text("API_ENDPOINT=https://new.test")
            output = io.StringIO()
            with patch.object(account.subprocess, "run") as run, contextlib.redirect_stdout(output):
                code = account.main(["--version-id", "v1", "--remote-config", str(rc),
                                     "--bundled-env", str(env),
                                     "--approved-hosts-file", str(Path(tmp) / "none.json")])
            self.assertEqual(code, 4)
            self.assertIn("new.test", output.getvalue())
            run.assert_not_called()

    def test_unknown_or_conditional_remote_config_blocks(self):
        for template in ({}, {"parameters": {"base_url": {
                "defaultValue": {"value": "https://good.test"}, "conditionalValues": {"ios": {}}}}}):
            with self.assertRaises(account.Blocked):
                account.resolve_endpoints(template, "API_ENDPOINT=https://good.test", {"good.test"})

    def test_distinct_approved_fallback_is_checked(self):
        template = {"parameters": {"base_url": {"defaultValue": {"value": "https://good.test"}}}}
        self.assertEqual(len(account.resolve_endpoints(
            template, "API_ENDPOINT=https://fallback.test", {"good.test", "fallback.test"})), 2)

    def test_main_fails_on_missing_template_without_fetching_credentials(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(account.subprocess, "run") as run:
            path = Path(tmp) / "missing"
            with contextlib.redirect_stdout(io.StringIO()):
                code = account.main(["--version-id", "v1", "--remote-config", str(path),
                                     "--bundled-env", str(path), "--allow-host", "good.test"])
            self.assertEqual(code, 2)
            run.assert_not_called()

    def run_two_backends(self, failing):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            rc = directory / "rc.json"
            env = directory / "artifact.env"
            rc.write_text(json.dumps({"parameters": {"base_url": {
                "defaultValue": {"value": "https://good.test"}}}}))
            env.write_text("API_ENDPOINT=https://fallback.test")
            fake = subprocess.CompletedProcess([], 0, stdout=json.dumps({
                "demoAccountName": "fake-user", "demoAccountPassword": "fake-password"}).encode())
            def http(api, method, path, body=None, token=None):
                if failing in api:
                    return 401, {}
                return (200, {"access_token": "fake-token"}) if path.endswith("/login") else (200, {})
            output = io.StringIO()
            with patch.object(account.subprocess, "run", return_value=fake), \
                    patch.object(account, "http_call", side_effect=http), \
                    contextlib.redirect_stdout(output):
                code = account.main(["--version-id", "v1", "--remote-config", str(rc),
                                     "--bundled-env", str(env), "--allow-host", "good.test",
                                     "--allow-host", "fallback.test"])
            self.assertEqual(set(directory.iterdir()), {rc, env})
            self.assertNotIn("fake-password", output.getvalue())
            self.assertNotIn("fake-user", output.getvalue())
            return code, output.getvalue()

    def test_fallback_only_failure_is_a_gate_warning(self):
        code, output = self.run_two_backends("fallback")
        self.assertEqual(code, 5)
        self.assertIn("remote-config: PASS", output)
        self.assertIn("WARN", output)

    def test_remote_config_failure_blocks(self):
        code, output = self.run_two_backends("good")
        self.assertEqual(code, 1)
        self.assertIn("remote-config: FAIL", output)


def tree(*items):
    return {"data": {"nodes": [dict(ref=f"e{i}", **item) for i, item in enumerate(items, 1)]}}


class FillTests(unittest.TestCase):
    """Shapes recorded from agent-device 0.21.8 snapshots of the login screen."""

    def test_android_editable_fields(self):
        fields = filler.input_fields(tree(
            {"type": "group", "label": "Username or email  *"},
            {"type": "text-field", "editable": True},
            {"type": "group", "label": "Password  *"},
            {"type": "text-field", "editable": True}))
        self.assertEqual([filler.ref(f) for f in fields], ["@e2", "@e4"])

    def test_ios_fields_reported_as_other(self):
        fields = filler.input_fields(tree(
            {"type": "StaticText", "label": "Username or email  *"},
            {"type": "Other", "label": "Enter your username or email"},
            {"type": "StaticText", "label": "Password  *"},
            {"type": "Other", "label": "Enter password"}))
        self.assertEqual([filler.ref(f) for f in fields], ["@e2", "@e4"])

    def test_paste_picks_the_menu_item_not_container_or_text(self):
        item = filler.paste_item(tree(
            {"type": "CollectionView", "label": "Paste"},
            {"type": "MenuItem", "label": "Paste"},
            {"type": "StaticText", "label": "Paste"}))
        self.assertEqual(item["ref"], "e2")
        older = filler.paste_item(tree({"type": "collection", "label": "Paste"},
                                       {"type": "cell", "label": "Paste"}))
        self.assertEqual(older["ref"], "e2")
        self.assertIsNone(filler.paste_item(tree({"type": "StaticText", "label": "Paste"})))

    def test_masked_password_check(self):
        self.assertTrue(filler.masked_matches("\u2022" * 5, "abcde"))
        self.assertFalse(filler.masked_matches("\u2022" * 4, "abcde"))
        self.assertFalse(filler.masked_matches("abcde", "abcde"))

    def test_leak_scan_finds_only_new_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "old.log"
            old.write_text("fake-secret")
            os.utime(old, (1, 1))
            (root / "clean.log").write_text("nothing")
            (root / "new.log").write_text("x fake-secret y")
            hits = filler.leaked_files(["fake-secret"], [root], since=10)
            self.assertEqual([Path(h).name for h in hits], ["new.log"])

    def test_redacted_credentials_block_before_device_use(self):
        fake = subprocess.CompletedProcess([], 0, stdout=json.dumps(
            {"demoAccountName": "fake", "demoAccountPassword": "(redacted)"}).encode())
        with patch.object(filler.subprocess, "run", return_value=fake), \
                self.assertRaises(filler.Blocked):
            filler.credentials("v1")


def row(state="PREPARE_FOR_SUBMISSION", version="2.0.1", platform="IOS", identifier="v1"):
    return {"id": identifier, "attributes": {
        "versionString": version, "platform": platform, "appVersionState": state}}


class InputsTests(unittest.TestCase):
    TEMPLATE = json.dumps({"parameters": {"base_url": {
        "defaultValue": {"value": "https://remote.test/api"}}}}).encode()

    def artifact(self, directory, members):
        path = Path(directory) / "app.aab"
        import zipfile
        with zipfile.ZipFile(path, "w") as archive:
            for name in members:
                archive.writestr(name, "API_ENDPOINT=https://bundled.test\n")
        return path

    def test_extracts_env_from_aab_and_ipa_layouts(self):
        for member in ("base/assets/flutter_assets/configs/env/wpseoai.env",
                       "Payload/Runner.app/Frameworks/App.framework/flutter_assets/configs/env/wpseoai.env"):
            with self.subTest(member=member), tempfile.TemporaryDirectory() as tmp:
                art = self.artifact(tmp, [member, member.replace("wpseoai", "demo")])
                summary = inputs.prepare(Path(tmp) / "run", "android", art,
                                         fetch=lambda project: self.TEMPLATE)
                self.assertEqual(summary["bundledEnv"]["member"], member)
                self.assertEqual(summary["bundledEnv"]["host"], "bundled.test")
                self.assertEqual(summary["remoteConfig"]["host"], "remote.test")
                self.assertFalse(summary["sameBackend"])
                env_file = Path(summary["bundledEnv"]["path"])
                self.assertEqual(env_file.stat().st_mode & 0o777, 0o600)

    def test_missing_or_duplicate_env_blocks_before_fetch(self):
        for members in ([], ["a/flutter_assets/configs/env/wpseoai.env",
                             "b/flutter_assets/configs/env/wpseoai.env"]):
            with tempfile.TemporaryDirectory() as tmp:
                art = self.artifact(tmp, members)
                fetch = unittest.mock.Mock()
                with self.assertRaises(inputs.Blocked):
                    inputs.prepare(Path(tmp) / "run", "ios", art, fetch=fetch)
                fetch.assert_not_called()

    def test_non_json_template_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = self.artifact(tmp, ["base/assets/flutter_assets/configs/env/wpseoai.env"])
            with self.assertRaises(inputs.Blocked):
                inputs.prepare(Path(tmp) / "run", "android", art, fetch=lambda project: b"<html>")


class VersionTests(unittest.TestCase):
    def test_items_shape_from_latest_flag(self):
        self.assertEqual(versions.select_version({"items": [row()]}, "2.0.1")["versionId"], "v1")

    def test_exact_target_not_latest_or_other_platform(self):
        result = versions.select_version({"data": [
            row(version="2.0.0"), row(platform="MAC_OS"), row()]}, "2.0.1")
        self.assertEqual(result["versionId"], "v1")

    def test_missing_target_is_read_only_by_default(self):
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            return {"data": []}
        with self.assertRaisesRegex(ValueError, "missing"):
            versions.resolve("2.0.1", run=run)
        self.assertEqual(len(calls), 1)
        self.assertIn("--paginate", calls[0])

    def test_create_requires_both_flags_before_api_access(self):
        for create, confirm in ((True, False), (False, True)):
            with patch.object(versions, "asc") as run, self.assertRaises(ValueError):
                versions.resolve("2.0.1", create, confirm, run=run)
            run.assert_not_called()

    def test_create_then_read_back(self):
        calls = []
        def run(args, **kwargs):
            calls.append((args, kwargs))
            return {"data": [row()]} if len(calls) == 3 else {"data": []}
        self.assertEqual(versions.resolve("2.0.1", True, True, run)["versionId"], "v1")
        self.assertEqual(calls[1][0][:2], ["versions", "create"])
        self.assertIn("--if-exists", calls[1][0])
        self.assertEqual(calls[1][1], {"write": True})

    def test_existing_version_does_not_create_even_when_authorized(self):
        with patch.object(versions, "asc", return_value={"data": [row()]}) as run:
            versions.resolve("2.0.1", True, True, run)
            self.assertEqual(run.call_count, 1)

    def test_review_live_unknown_or_ambiguous_blocks_without_cancellation(self):
        for state in ("WAITING_FOR_REVIEW", "IN_REVIEW", "READY_FOR_SALE", "UNKNOWN"):
            with self.subTest(state=state), self.assertRaises(ValueError):
                versions.select_version({"data": [row(state=state)]}, "2.0.1")
        with self.assertRaises(ValueError):
            versions.select_version({"data": [row(), row(identifier="v2")]}, "2.0.1")

    def test_failed_create_readback_is_blocking(self):
        with self.assertRaises(ValueError):
            versions.resolve("2.0.1", True, True, lambda *args, **kwargs: {"data": []})


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / "run"
        self.commit = "a" * 40
        ledger.initialize(self.run, "2.0.1", self.commit, ["android", "ios"], "full-release", "message-1")
        self.context = json.loads((self.run / "context.json").read_text())
        self.artifact = self.root / "fake.aab"
        self.artifact.write_bytes(b"fake-test-artifact")
        self.record = {
            "flavor": "wpseoai", "applicationId": ledger.APP, "platform": "android",
            "artifactKind": "aab", "version": "2.0.1", "buildNumber": "163",
            "outcome": "uploaded", "artifactSha256": ledger.digest(self.artifact),
            "source": {"sha": self.commit, "clean": True, "nonReleaseTest": False},
        }
        self.record_path = self.root / "record.json"
        self.record_path.write_text(json.dumps(self.record))

    def test_init_is_private_and_never_overwrites(self):
        self.assertEqual(self.run.stat().st_mode & 0o777, 0o700)
        with self.assertRaises(FileExistsError):
            ledger.initialize(self.run, "2.0.1", self.commit, ["ios"], "testing", "message-2")

    def test_invalid_version_or_sha_does_not_create_run(self):
        for version, commit in (("latest", self.commit), ("2.0.1", "main")):
            with self.assertRaises(ValueError):
                ledger.initialize(self.root / "other", version, commit, ["ios"], "testing", "m")
        self.assertFalse((self.root / "other").exists())

    def test_bind_preserves_artifact_and_missing_platform(self):
        ledger.bind(self.run, self.context, "android", self.record_path, self.artifact)
        self.assertEqual(ledger.check(self.run, self.context), ["ios"])
        self.artifact.write_bytes(b"overwritten-by-next-build")
        self.assertEqual(ledger.check(self.run, self.context), ["ios"])

    def test_same_bind_is_idempotent(self):
        for _ in range(2):
            ledger.bind(self.run, self.context, "android", self.record_path, self.artifact)
        self.assertEqual(len(self.context["builds"]), 1)

    def test_bound_build_cannot_be_replaced(self):
        ledger.bind(self.run, self.context, "android", self.record_path, self.artifact)
        self.record["buildNumber"] = "164"
        self.record_path.write_text(json.dumps(self.record))
        with self.assertRaises(ValueError):
            ledger.bind(self.run, self.context, "android", self.record_path, self.artifact)
        with self.assertRaises(ValueError):
            ledger.check(self.run, self.context)

    def test_hash_mismatch_and_dirty_source_block(self):
        for key, value in (("artifactSha256", "b" * 64), ("version", "2.0.0"),
                           ("outcome", "built"), ("applicationId", "other.app")):
            record = dict(self.record, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                ledger.validate_record(self.context, record, "android", self.artifact)
        for source in ({"sha": self.commit, "clean": False, "nonReleaseTest": False},
                       {"sha": "b" * 40, "clean": True, "nonReleaseTest": False}):
            with self.assertRaises(ValueError):
                ledger.validate_record(self.context, dict(self.record, source=source),
                                       "android", self.artifact)

    def test_unselected_platform_blocks(self):
        self.context["platforms"] = ["ios"]
        with self.assertRaises(ValueError):
            ledger.validate_record(self.context, self.record, "android", self.artifact)

    def test_record_promotion_updates_are_allowed(self):
        ledger.bind(self.run, self.context, "android", self.record_path, self.artifact)
        self.record["promotions"] = [{"kind": "promotion"}]
        self.record_path.write_text(json.dumps(self.record))
        self.assertEqual(ledger.check(self.run, self.context), ["ios"])

    def test_approve_writes_the_entry_the_lanes_check(self):
        with self.assertRaises(ValueError):  # nothing bound yet
            ledger.approve(self.run, self.context, "android", "promote", "msg-9", rollout=1)
        ledger.bind(self.run, self.context, "android", self.record_path, self.artifact)
        entry = ledger.approve(self.run, self.context, "android", "promote", "msg-9", rollout=1)
        self.assertEqual((entry["build"], entry["artifactSha256"], entry["rollout"]),
                         ("163", self.record["artifactSha256"], "1.0"))
        self.assertIn("expiresAt", entry)
        saved = json.loads((self.run / "approvals.json").read_text())["approvals"]
        self.assertEqual(saved, [entry])
        for bad in (dict(action="submit", rollout=1), dict(action="promote", rollout=None),
                    dict(action="promote", rollout=1.5)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                ledger.approve(self.run, self.context, "android", ref="msg-9", **bad)
        with self.assertRaises(ValueError):  # ios not bound, and needs a release mode
            ledger.approve(self.run, self.context, "ios", "submit", "msg-9")

    def test_decision_log_is_tsv_with_one_row_per_call(self):
        ledger.log_decision(self.run, "verify", "block android", "first launch\tfailed\non fallback")
        ledger.log_decision(self.run, "gate", "ask", "per platform")
        rows = (self.run / "decisions.tsv").read_text().splitlines()
        self.assertEqual(rows[0].split("\t"), ["at", "phase", "decision", "reason", "evidence"])
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1].split("\t")[3], "first launch failed on fallback")

    def test_history_lists_runs_newest_first_with_evidence(self):
        ledger.bind(self.run, self.context, "android", self.record_path, self.artifact)
        (self.run / "evidence" / "android.json").write_text(
            json.dumps({"level": "aab-derived-universal", "firstLaunch": "fail", "extra": 1}))
        older = self.root / "older"
        ledger.initialize(older, "2.0.0", self.commit, ["ios"], "testing", "m0")
        os.utime(older / "context.json", (1, 1))
        (self.root / "junk").mkdir()
        (self.root / "junk" / "context.json").write_text("{bad")
        runs = ledger.history(self.root)
        self.assertEqual([r["run"] for r in runs], ["run", "older"])
        self.assertEqual(runs[0]["builds"], {"android": "163"})
        self.assertEqual(runs[0]["evidence"]["android"],
                         {"level": "aab-derived-universal", "firstLaunch": "fail"})
        self.assertIsNone(runs[0]["evidence"]["ios"])
        self.assertEqual(len(ledger.history(self.root, limit=1)), 1)

    def test_corrupted_bound_artifact_blocks(self):
        ledger.bind(self.run, self.context, "android", self.record_path, self.artifact)
        (self.run / self.context["builds"]["android"]["artifact"]).write_bytes(b"bad")
        with self.assertRaises(ValueError):
            ledger.check(self.run, self.context)


class WorkhubTests(unittest.TestCase):
    def run_fn(self, cwd, command, env=None):
        merged = dict(os.environ)
        merged.pop("PEOPLECORAL_WORKHUB", None)
        merged.pop("PEOPLECORAL_CONFIGS", None)
        if env:
            merged.update(env)
        return subprocess.run(
            ["bash", "-c", 'source "$1" && ' + command, "workhub", str(SCRIPTS / "workhub.sh")],
            cwd=cwd, env=merged, capture_output=True, text=True,
        )

    def run_workhub(self, cwd, env=None):
        return self.run_fn(cwd, "workhub", env)

    def init_checkout(self, path):
        path.mkdir(parents=True)
        (path / "pubspec.yaml").write_text("name: peoplecoral_mobile_app\n")
        subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
        subprocess.run(["git", "add", "pubspec.yaml"], cwd=path, check=True, capture_output=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "init"],
            cwd=path, check=True, capture_output=True,
        )

    def test_worktree_wins_over_main_and_env_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = Path(tmp) / "main"
            worktree = Path(tmp) / "worktree"
            self.init_checkout(main)
            subprocess.run(
                ["git", "worktree", "add", str(worktree), "-b", "wt"],
                cwd=main, check=True, capture_output=True,
            )
            nested = worktree / "lib" / "feature"
            nested.mkdir(parents=True)
            from_worktree = self.run_workhub(nested, env={"PEOPLECORAL_WORKHUB": str(main)})
            self.assertEqual(from_worktree.returncode, 0, from_worktree.stderr)
            self.assertEqual(Path(from_worktree.stdout.strip()).resolve(), worktree.resolve())
            from_main = self.run_workhub(main)
            self.assertEqual(from_main.returncode, 0, from_main.stderr)
            self.assertEqual(Path(from_main.stdout.strip()).resolve(), main.resolve())

    def test_env_is_only_used_when_cwd_is_not_a_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkout = Path(tmp) / "checkout"
            outside = Path(tmp) / "outside"
            self.init_checkout(checkout)
            outside.mkdir()
            pinned = self.run_workhub(outside, env={"PEOPLECORAL_WORKHUB": str(checkout)})
            self.assertEqual(pinned.returncode, 0, pinned.stderr)
            self.assertEqual(Path(pinned.stdout.strip()).resolve(), checkout.resolve())
            missing = self.run_workhub(outside)
            self.assertEqual(missing.returncode, 2)
            self.assertNotIn("Documents/repos/peoplecoral/peoplecoral-workhub", missing.stdout)

    def test_configs_default_to_checkout_and_can_be_overridden(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkout = Path(tmp) / "checkout"
            shared = Path(tmp) / "shared-configs"
            outside = Path(tmp) / "outside"
            self.init_checkout(checkout)
            shared.mkdir()
            (shared / "env").mkdir()
            (shared / "env" / "demo.env").write_text("API_ENDPOINT=https://example.test\n")
            outside.mkdir()
            default = self.run_fn(checkout, "configs_root")
            self.assertEqual(default.returncode, 0, default.stderr)
            self.assertEqual(Path(default.stdout.strip()).resolve(), (checkout / "configs").resolve())
            override = self.run_fn(outside, "configs_root", env={"PEOPLECORAL_CONFIGS": str(shared)})
            self.assertEqual(override.returncode, 0, override.stderr)
            self.assertEqual(Path(override.stdout.strip()).resolve(), shared.resolve())

    def test_missing_config_names_the_file_and_the_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkout = Path(tmp) / "checkout"
            self.init_checkout(checkout)
            result = self.run_fn(checkout, "require_config env/demo.env")
            self.assertEqual(result.returncode, 2)
            self.assertIn("missing", result.stderr)
            self.assertIn("env/demo.env", result.stderr)
            self.assertIn("PEOPLECORAL_CONFIGS", result.stderr)

    def test_check_configs_accepts_override_and_rejects_unknown_flavor(self):
        with tempfile.TemporaryDirectory() as tmp:
            shared = Path(tmp) / "shared-configs"
            (shared / "env").mkdir(parents=True)
            (shared / "env" / "demo.env").write_text("API_ENDPOINT=https://example.test\n")
            merged = dict(os.environ)
            merged.pop("PEOPLECORAL_WORKHUB", None)
            merged.pop("PEOPLECORAL_CONFIGS", None)
            merged["PEOPLECORAL_CONFIGS"] = str(shared)
            ok = subprocess.run(
                ["bash", str(SCRIPTS / "check-configs.sh"), "flavor", "demo"],
                cwd=tmp, env=merged, capture_output=True, text=True,
            )
            self.assertEqual(ok.returncode, 0, ok.stderr)
            missing = subprocess.run(
                ["bash", str(SCRIPTS / "check-configs.sh"), "store"],
                cwd=tmp, env=merged, capture_output=True, text=True,
            )
            self.assertEqual(missing.returncode, 2)
            self.assertIn("PEOPLECORAL_CONFIGS", missing.stderr)
            bad = subprocess.run(
                ["bash", str(SCRIPTS / "check-configs.sh"), "flavor", "prod"],
                cwd=tmp, env=merged, capture_output=True, text=True,
            )
            self.assertEqual(bad.returncode, 2)
            self.assertIn("unknown flavor", bad.stderr)

    def test_other_repos_are_not_treated_as_workhub(self):
        with tempfile.TemporaryDirectory() as tmp:
            other = Path(tmp) / "other"
            other.mkdir()
            (other / "pubspec.yaml").write_text("name: something_else\n")
            subprocess.run(["git", "init"], cwd=other, check=True, capture_output=True)
            result = self.run_workhub(other)
            self.assertEqual(result.returncode, 2)


class ShellTests(unittest.TestCase):
    def test_shell_syntax(self):
        for path in SCRIPTS.glob("*.sh"):
            with self.subTest(script=path.name):
                subprocess.run(["bash", "-n", str(path)], check=True, capture_output=True)

    def test_gpc_refuses_production_track_writes_before_touching_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, PATH="/usr/bin:/bin", PLAY_STORE_JSON_KEY=str(Path(tmp) / "missing.json"))
            for args in (["tracks", "update", "--track", "production", "--version-code", "1"],
                         ["tracks", "promote", "--from", "internal", "--to", "production"],
                         ["tracks", "halt", "--track=production"]):
                with self.subTest(args=args):
                    result = subprocess.run(["/bin/bash", str(SCRIPTS / "gpc.sh"), *args],
                                            env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 3)
                    self.assertIn("BLOCKED", result.stderr)
            # Reads and non-production tracks reach the normal key check (exit 2 here).
            for args in (["tracks", "get", "--track", "production"],
                         ["tracks", "update", "--track", "internal"]):
                with self.subTest(args=args):
                    result = subprocess.run(["/bin/bash", str(SCRIPTS / "gpc.sh"), *args],
                                            env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 2)

    def test_fill_helper_requires_arguments(self):
        result = subprocess.run(["bash", str(SCRIPTS / "review-account-fill.sh")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--version-id", result.stderr)

    def test_status_requests_testflight_and_live_ios_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            shutil.copyfile(SCRIPTS / "store-status.sh", directory / "store-status.sh")
            log = directory / "cmds.log"
            stub = (
                "#!/bin/sh\n"
                f"printf '%s ' \"$0\" >> '{log}'\n"
                f"printf '%s\\n' \"$*\" >> '{log}'\n"
                "echo '{\"releases\":[],\"data\":[],\"items\":[]}'\n"
            )
            for name in ("asc.sh", "gpc.sh"):
                path = directory / name
                path.write_text(stub)
                path.chmod(0o700)
            result = subprocess.run(["bash", str(directory / "store-status.sh")],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            cmds = log.read_text()
            self.assertIn("builds,testflight,appstore,submission,review", cmds)
            self.assertIn("READY_FOR_SALE --latest", cmds)

    def test_status_read_failures_have_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            shutil.copyfile(SCRIPTS / "store-status.sh", directory / "store-status.sh")
            for name in ("asc.sh", "gpc.sh"):
                path = directory / name
                path.write_text("#!/bin/sh\nexit 1\n")
                path.chmod(0o700)
            result = subprocess.run(["bash", str(directory / "store-status.sh")],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("UNKNOWN", result.stdout)

    def test_asc_wrapper_read_only_default_and_explicit_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            env_file = directory / "fake.env"
            env_file.write_text("ASC_API_KEY_ID=fake\nASC_API_ISSUER_ID=fake\n"
                                "ASC_API_KEY_CONTENT=fake-base64\n")
            executable = directory / "asc"
            executable.write_text("#!/bin/sh\nprintf '%s' \"$ASC_READ_ONLY\"\n")
            executable.chmod(0o700)
            env = dict(os.environ, PATH=str(directory) + os.pathsep + os.environ["PATH"],
                       ASC_ENV_FILE=str(env_file), ASC_READ_ONLY="0", ASC_WRITE="0")
            result = subprocess.run(["bash", str(SCRIPTS / "asc.sh"), "status"],
                                    env=env, capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout, "1")
            env.update(ASC_READ_ONLY="1", ASC_WRITE="1")
            result = subprocess.run(["bash", str(SCRIPTS / "asc.sh"), "status"],
                                    env=env, capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout, "0")


if __name__ == "__main__":
    unittest.main()
