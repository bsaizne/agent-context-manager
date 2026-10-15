"""Regression tests for the .agentctx.json import path.

Before 0.5 a crafted payload could write outside the target directory (a ".."
key), silently overwrite a hand-written AGENTS.md, and replace context files
with no backup at all.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _helpers import SRC  # noqa: F401
from agent_context.checkpoint import run_checkpoint
from agent_context.project import init_project
from agent_context.transfer import context_token_stats, export_project, import_project
from agent_context.utils import ContextError


def _write_transfer(path: Path, files: dict[str, str]) -> Path:
    path.write_text(
        json.dumps(
            {"format": "agent-context-transfer", "version": 1, "project": "donor", "files": files}
        ),
        encoding="utf-8",
    )
    return path


class ImportSafetyTests(unittest.TestCase):
    def test_parent_directory_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target"
            target.mkdir()
            transfer = _write_transfer(root / "evil.agentctx.json", {"..\\escaped.txt": "PWNED"})

            with self.assertRaises(ContextError):
                import_project(transfer, target)

            self.assertFalse((root / "escaped.txt").exists())

    def test_absolute_paths_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            transfer = _write_transfer(root / "evil.agentctx.json", {"C:/Windows/Temp/pwned.txt": "x"})

            with self.assertRaises(ContextError):
                import_project(transfer, root / "target")

    def test_existing_files_are_backed_up_and_agents_is_kept(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            victim = root / "victim"
            victim.mkdir()
            init_project(victim)
            state_path = victim / ".agent" / "STATE.md"
            state_path.write_text("# PROJECT STATE\n\n## Project\n\n人类手写内容\n", encoding="utf-8")
            agents_path = victim / "AGENTS.md"
            agents_path.write_text("# 我的规则\n", encoding="utf-8")

            transfer = _write_transfer(
                root / "donor.agentctx.json",
                {
                    ".agent/STATE.md": "# PROJECT STATE\n\n## Project\n\n导入的内容\n",
                    "AGENTS.md": "# Agent Project Instructions\n",
                },
            )

            report = import_project(transfer, victim)

            self.assertIn(".agent/STATE.md", report.overwritten)
            self.assertIn("AGENTS.md", report.kept)
            self.assertIsNotNone(report.backup_dir)
            backup = report.backup_dir / ".agent" / "STATE.md"
            self.assertIn("人类手写内容", backup.read_text(encoding="utf-8"))
            self.assertIn("导入的内容", state_path.read_text(encoding="utf-8"))
            self.assertEqual(agents_path.read_text(encoding="utf-8"), "# 我的规则\n")

    def test_identical_files_are_reported_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            init_project(project)
            export_project(project)
            transfer = sorted(project.glob("project-*.agentctx.json"))[-1]

            report = import_project(transfer, project)

            self.assertEqual(report.created, [])
            self.assertEqual(report.overwritten, [])
            self.assertTrue(report.unchanged)


class TokenStatsTests(unittest.TestCase):
    def test_archive_is_counted_separately_from_the_resume_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            init_project(project)
            run_checkpoint(project)
            baseline = context_token_stats(project)
            self.assertEqual(baseline.archive_files, 1)

            archive_dir = project / ".agent" / "archive"
            sample = sorted(archive_dir.glob("checkpoint-*.md"))[0].read_text(encoding="utf-8")
            for index in range(5):
                (archive_dir / f"checkpoint-2020-01-01-00000{index}.md").write_text(sample, encoding="utf-8")

            grown = context_token_stats(project)

            self.assertEqual(grown.total_chars, baseline.total_chars)
            self.assertEqual(len(grown.files), len(baseline.files))
            self.assertGreater(grown.archive_chars, baseline.archive_chars)
            self.assertEqual(grown.archive_files, baseline.archive_files + 5)
            self.assertFalse(any("archive" in name for name in grown.files))


if __name__ == "__main__":
    unittest.main()
