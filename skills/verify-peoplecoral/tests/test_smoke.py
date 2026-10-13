"""Offline tests for the smoke driver's decisions. No devices."""
import importlib.util
import subprocess
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location("smoke", SCRIPTS / "smoke.py")
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


def tree(*items):
    return {"data": {"nodes": [dict(ref=f"e{i}", **item) for i, item in enumerate(items, 1)]}}


class ClassifyTests(unittest.TestCase):
    def test_loaded_screen_passes(self):
        self.assertEqual(smoke.classify("Pending\nApproved\nRejected", ("Pending",))[0], "pass")

    def test_loaded_but_empty_is_valid(self):
        self.assertEqual(smoke.classify("Payslip\nNo payslips yet", ("Payslip",))[0], "valid-empty")

    def test_error_text_fails_even_when_title_shows(self):
        self.assertEqual(smoke.classify("Payslip\nSomething went wrong", ("Payslip",))[0], "fail")

    def test_wrong_screen_fails(self):
        self.assertEqual(smoke.classify("Hi Isabelle", ("Payslip",))[0], "fail")


class SelectionTests(unittest.TestCase):
    def test_stable_identifier_wins(self):
        t = tree({"type": "Button", "identifier": "bottom-tab-profile"})
        self.assertEqual(smoke.find_by_identifier(t, "bottom-tab-profile")["ref"], "e1")

    def test_ios_tile_prefers_the_image_twin(self):
        t = tree({"type": "Other", "label": "Time Off"}, {"type": "Image", "label": "Time Off"})
        self.assertEqual(smoke.find_tile(t, "Time Off", "ios")["ref"], "e2")

    def test_chat_tile_label_with_unread_count(self):
        t = tree({"type": "Image", "label": "Chat\n2"})
        self.assertEqual(smoke.find_tile(t, "Chat", "ios")["ref"], "e1")

    def test_screen_text_drops_email_addresses(self):
        text = smoke.screen_text(tree({"label": "someone@example.com"}, {"label": "Profile"}))
        self.assertEqual(text, "Profile")

    def test_home_detection(self):
        self.assertTrue(smoke.on_home(tree({"label": "Hi Isabelle!"}, {"label": "Time Off"})))
        self.assertFalse(smoke.on_home(tree({"label": "Payslip"})))
        self.assertFalse(
            smoke.on_home(tree({"label": "Time Off"}, {"label": "Pending"}, {"label": "Approved"})),
        )
        self.assertTrue(smoke.on_home(tree({"label": "Hi Manager!"}, {"label": "Approvals"})))

    def test_sweep_includes_overtime_and_drops_messages(self):
        names = [row[0] for row in smoke.SWEEP]
        self.assertIn("overtime", names)
        chat = next(row for row in smoke.SWEEP if row[0] == "chat")
        self.assertEqual(chat[2], ("Chat", "Search"))
        self.assertEqual(smoke.OPTIONAL, {"overtime", "sick-leave", "chat", "expenses"})
        self.assertTrue(
            smoke.optional_tile_missing("overtime", smoke.Blocked("home tile Overtime not found")),
        )
        self.assertFalse(
            smoke.optional_tile_missing("time-off", smoke.Blocked("home tile Time Off not found")),
        )


class ExitTests(unittest.TestCase):
    def test_exit_codes(self):
        self.assertEqual(smoke.exit_code([{"result": "pass"}, {"result": "valid-empty"}]), 0)
        self.assertEqual(smoke.exit_code([{"result": "pass"}, {"result": "fail"}]), 1)
        self.assertEqual(smoke.exit_code([{"result": "not-verified"}]), 3)

    def test_doctor_usage(self):
        result = subprocess.run(["bash", str(SCRIPTS / "doctor.sh")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)

    def test_doctor_rejects_unknown_flavor(self):
        result = subprocess.run(
            ["bash", str(SCRIPTS / "doctor.sh"), "ios", "UDID-FAKE", "staging"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown flavor", result.stderr)


if __name__ == "__main__":
    unittest.main()
