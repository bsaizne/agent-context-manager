from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from _helpers import SRC  # noqa: F401
from agent_context.config import config_path, load_config


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
