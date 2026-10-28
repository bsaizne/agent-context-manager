from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from _helpers import SRC  # noqa: F401
from agent_context.config import config_path, load_config, save_config
from agent_context.templates import DEFAULT_AGENT_PROMPT_TEMPLATE


class ConfigTests(unittest.TestCase):
    def test_config_uses_local_override_and_creates_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("AGENT_CONTEXT_CONFIG_DIR")
            os.environ["AGENT_CONTEXT_CONFIG_DIR"] = str(Path(tmp) / "config")
            try:
                config = load_config(create=True)
                self.assertTrue(config_path().exists())
                self.assertTrue(config["archive_enabled"])
            finally:
                if old is None:
                    os.environ.pop("AGENT_CONTEXT_CONFIG_DIR", None)
                else:
                    os.environ["AGENT_CONTEXT_CONFIG_DIR"] = old

    def test_agent_prompt_template_round_trips(self) -> None:
        # agent_prompt_template is the one key users are expected to edit by
        # hand (or via the GUI Settings page); a broken round-trip would
        # silently throw their custom prompt back to the default.
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("AGENT_CONTEXT_CONFIG_DIR")
            os.environ["AGENT_CONTEXT_CONFIG_DIR"] = str(Path(tmp) / "config")
            try:
                self.assertEqual(load_config()["agent_prompt_template"], DEFAULT_AGENT_PROMPT_TEMPLATE)
                save_config({"agent_prompt_template": "自定义模板 {resume}"})
                self.assertEqual(load_config()["agent_prompt_template"], "自定义模板 {resume}")
            finally:
                if old is None:
                    os.environ.pop("AGENT_CONTEXT_CONFIG_DIR", None)
                else:
                    os.environ["AGENT_CONTEXT_CONFIG_DIR"] = old
