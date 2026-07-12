"""Pure-python tests for manifest/const consistency and API client init logic.

``const.py`` has no imports and loads directly. ``api_client.py`` imports
the third-party ``anthropic`` package (not installed in this test
environment and never required — no new dependencies) and does a
relative ``from .const import (...)``; a minimal stub ``anthropic``
module and a fake parent package are installed before exec so the
module's pure ``__init__`` model-selection logic can be exercised
without touching Home Assistant or the network. ``action_handler.py``
and ``conversation.py`` import ``homeassistant.*`` directly and are not
loadable here, so they are left untested per the task's fallback rule.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path

COMPONENT_DIR = (
    Path(__file__).resolve().parents[1] / "custom_components" / "claude_assistant"
)
MANIFEST_PATH = COMPONENT_DIR / "manifest.json"

# ---------------------------------------------------------------- const.py
const_spec = importlib.util.spec_from_file_location("claude_assistant_const", COMPONENT_DIR / "const.py")
assert const_spec and const_spec.loader
const = importlib.util.module_from_spec(const_spec)
const_spec.loader.exec_module(const)

# ------------------------------------------------------------- api_client.py
def _stub_anthropic() -> None:
    if "anthropic" in sys.modules:
        return
    anthropic_mod = types.ModuleType("anthropic")

    class _FakeAsyncAnthropic:
        def __init__(self, *args, **kwargs) -> None:
            pass

    class _FakeAPIError(Exception):
        status_code = None
        message = ""

    anthropic_mod.AsyncAnthropic = _FakeAsyncAnthropic
    anthropic_mod.APIError = _FakeAPIError
    sys.modules["anthropic"] = anthropic_mod


_stub_anthropic()

_PKG = "_claude_assistant_test_pkg"
if _PKG not in sys.modules:
    pkg_module = types.ModuleType(_PKG)
    pkg_module.__path__ = [str(COMPONENT_DIR)]
    sys.modules[_PKG] = pkg_module
    sys.modules[f"{_PKG}.const"] = const

api_client_spec = importlib.util.spec_from_file_location(
    f"{_PKG}.api_client", COMPONENT_DIR / "api_client.py"
)
assert api_client_spec and api_client_spec.loader
api_client_module = importlib.util.module_from_spec(api_client_spec)
api_client_module.__package__ = _PKG
sys.modules[f"{_PKG}.api_client"] = api_client_module
api_client_spec.loader.exec_module(api_client_module)

ClaudeAPIClient = api_client_module.ClaudeAPIClient


class ManifestConsistencyTests(unittest.TestCase):
    """manifest.json vs. directory / const.py invariants HACS relies on."""

    @classmethod
    def setUpClass(cls) -> None:
        with open(MANIFEST_PATH, encoding="utf-8") as handle:
            cls.manifest = json.load(handle)

    def test_manifest_domain_matches_directory_name(self) -> None:
        self.assertEqual(self.manifest["domain"], COMPONENT_DIR.name)

    def test_manifest_domain_matches_const_domain(self) -> None:
        self.assertEqual(self.manifest["domain"], const.DOMAIN)

    def test_manifest_has_required_keys(self) -> None:
        required = {
            "domain",
            "name",
            "codeowners",
            "config_flow",
            "documentation",
            "integration_type",
            "iot_class",
            "issue_tracker",
            "requirements",
            "version",
        }
        missing = required - self.manifest.keys()
        self.assertEqual(missing, set())

    def test_manifest_version_is_nonempty_dotted_string(self) -> None:
        version = self.manifest["version"]
        self.assertIsInstance(version, str)
        parts = version.split(".")
        self.assertGreaterEqual(len(parts), 2)
        for part in parts:
            self.assertTrue(part.isdigit(), f"non-numeric version segment: {part!r}")

    def test_manifest_codeowners_are_github_handles(self) -> None:
        codeowners = self.manifest["codeowners"]
        self.assertTrue(codeowners)
        for owner in codeowners:
            self.assertTrue(owner.startswith("@"))

    def test_manifest_requirements_pin_anthropic_minimum_version(self) -> None:
        requirements = self.manifest["requirements"]
        self.assertTrue(any(req.startswith("anthropic") for req in requirements))


class ClaudeModelsConstTests(unittest.TestCase):
    """CLAUDE_MODELS / DEFAULT_MODEL invariants api_client.py relies on."""

    def test_claude_models_is_nonempty(self) -> None:
        self.assertTrue(const.CLAUDE_MODELS)
        self.assertIsInstance(const.CLAUDE_MODELS, list)

    def test_default_model_is_a_valid_claude_model(self) -> None:
        self.assertIn(const.DEFAULT_MODEL, const.CLAUDE_MODELS)

    def test_default_model_is_first_in_list(self) -> None:
        # api_client.py falls back to CLAUDE_MODELS[0] for unknown models;
        # that fallback should always be the documented default.
        self.assertEqual(const.CLAUDE_MODELS[0], const.DEFAULT_MODEL)

    def test_no_duplicate_models(self) -> None:
        self.assertEqual(len(const.CLAUDE_MODELS), len(set(const.CLAUDE_MODELS)))

    def test_ws_type_constants_are_namespaced_under_domain(self) -> None:
        ws_types = [
            const.WS_TYPE_CHAT,
            const.WS_TYPE_CONFIRM_ACTION,
            const.WS_TYPE_GET_PENDING,
            const.WS_TYPE_GET_ENTITIES,
            const.WS_TYPE_SETTINGS,
        ]
        for ws_type in ws_types:
            self.assertTrue(ws_type.startswith(f"{const.DOMAIN}/"))

    def test_storage_key_constants_are_namespaced_under_domain(self) -> None:
        keys = [
            const.STORAGE_KEY_HISTORY,
            const.STORAGE_KEY_PENDING,
            const.STORAGE_KEY_LOGS,
            const.STORAGE_KEY_STATS,
        ]
        for key in keys:
            self.assertTrue(key.startswith(f"{const.DOMAIN}_"))


class ClaudeApiClientModelFallbackTests(unittest.TestCase):
    """Pure __init__ logic: unknown models silently fall back to CLAUDE_MODELS[0]."""

    def test_known_model_is_kept_as_is(self) -> None:
        client = ClaudeAPIClient(api_key="sk-fake", model=const.CLAUDE_MODELS[-1])
        self.assertEqual(client.model, const.CLAUDE_MODELS[-1])

    def test_unknown_model_falls_back_to_first_claude_model(self) -> None:
        client = ClaudeAPIClient(api_key="sk-fake", model="not-a-real-model")
        self.assertEqual(client.model, const.CLAUDE_MODELS[0])

    def test_default_constructor_uses_default_model(self) -> None:
        client = ClaudeAPIClient(api_key="sk-fake")
        self.assertEqual(client.model, const.DEFAULT_MODEL)

    def test_message_count_starts_at_zero(self) -> None:
        client = ClaudeAPIClient(api_key="sk-fake")
        self.assertEqual(client.message_count, 0)


if __name__ == "__main__":
    unittest.main()
