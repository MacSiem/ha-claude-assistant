"""Retirement release 1.2.0: the claude.ai session-key mode is gone and stored keys are purged.

Pure python, like test_manifest_and_const.py: Home Assistant is not installed here, so
HA-dependent modules are checked by source, and the pure migration helper is executed.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT_DIR = ROOT / "custom_components" / "claude_assistant"

_PKG = "_claude_assistant_retirement_pkg"
pkg = types.ModuleType(_PKG)
pkg.__path__ = [str(COMPONENT_DIR)]
sys.modules[_PKG] = pkg


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"{_PKG}.{name}", COMPONENT_DIR / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    module.__package__ = _PKG
    sys.modules[f"{_PKG}.{name}"] = module
    spec.loader.exec_module(module)
    return module


const = _load("const")


class SessionModeRemovedTests(unittest.TestCase):
    def test_only_api_key_authentication_is_offered(self) -> None:
        self.assertEqual(const.AUTH_TYPES, [const.AUTH_TYPE_API_KEY])

    def test_config_flow_has_no_session_key_step(self) -> None:
        source = (COMPONENT_DIR / "config_flow.py").read_text(encoding="utf-8")
        self.assertNotIn("async_step_personal", source)
        self.assertNotIn("CONF_SESSION_KEY", source)
        self.assertNotIn("sessionKey", source)

    def test_api_client_has_no_session_branch(self) -> None:
        source = (COMPONENT_DIR / "api_client.py").read_text(encoding="utf-8")
        self.assertNotIn("AUTH_TYPE_PERSONAL", source)

    def test_translations_drop_session_step_and_explain_retirement(self) -> None:
        for name in ("strings.json", "translations/en.json"):
            with self.subTest(file=name):
                data = json.loads((COMPONENT_DIR / name).read_text(encoding="utf-8"))
                self.assertNotIn("personal", data["config"]["step"])
                self.assertNotIn("invalid_session", data["config"]["error"])
                self.assertIn("integration_retired", data["issues"])
                self.assertIn("session_mode_removed", data["issues"])


class EntryMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.migration = _load("migration")

    def test_session_entry_is_purged_and_flagged(self) -> None:
        old = {"auth_type": "personal_account", "session_key": "sk-ant-sid-secret", "model": "m"}
        new, legacy = self.migration.strip_session_mode(old)
        self.assertTrue(legacy)
        self.assertNotIn("session_key", new)
        self.assertEqual(new["auth_type"], const.AUTH_TYPE_API_KEY)
        self.assertTrue(new[self.migration.SESSION_MODE_REMOVED])
        self.assertEqual(new["model"], "m")
        self.assertIn("session_key", old, "input must not be mutated")

    def test_api_key_entry_is_unchanged(self) -> None:
        old = {"auth_type": "api_key", "api_key": "sk-ant-api", "model": "m"}
        new, legacy = self.migration.strip_session_mode(old)
        self.assertFalse(legacy)
        self.assertEqual(new, old)

    def test_stray_session_key_is_removed_even_without_personal_type(self) -> None:
        new, legacy = self.migration.strip_session_mode({"auth_type": "api_key", "api_key": "k", "session_key": "x"})
        self.assertNotIn("session_key", new)
        self.assertFalse(legacy)

    def test_entry_version_matches_config_flow(self) -> None:
        source = (COMPONENT_DIR / "config_flow.py").read_text(encoding="utf-8")
        self.assertEqual(self.migration.ENTRY_VERSION, 3)
        self.assertIn("VERSION = ENTRY_VERSION", source)
        init = (COMPONENT_DIR / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("async def async_migrate_entry", init)
        self.assertIn("strip_session_mode", init)


class ReleaseMetadataTests(unittest.TestCase):
    def test_versions_agree_on_retirement_release(self) -> None:
        manifest = json.loads((COMPONENT_DIR / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "1.2.0")
        self.assertEqual(const.VERSION, "1.2.0")
        self.assertIn("## 1.2.0", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))

    def test_readme_opens_with_retirement_and_migration(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        head = readme[:1500]
        self.assertIn("retired", head.lower())
        self.assertIn("home-assistant.io/integrations/anthropic", head)
        self.assertNotIn('"personal account" option', readme)


if __name__ == "__main__":
    unittest.main()
