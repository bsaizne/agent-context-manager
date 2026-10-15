from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from _helpers import SRC  # noqa: F401
from agent_context.git import collect_git_info, is_git_repository, run_git


class GitTests(unittest.TestCase):
    def test_non_git_project_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            info = collect_git_info(Path(tmp))
            self.assertFalse(info.repository_detected)

    def test_run_git_hides_windows_console(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("agent_context.git.subprocess.run") as mocked_run:
                mocked_run.return_value = subprocess.CompletedProcess(
                    ["git", "status"], 0, "ok\n", ""
                )

                code, stdout, stderr = run_git(Path(tmp), ["status"])

            self.assertEqual(code, 0)
            self.assertEqual(stdout, "ok")
            self.assertEqual(stderr, "")
            kwargs = mocked_run.call_args.kwargs
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                self.assertEqual(kwargs["creationflags"], subprocess.CREATE_NO_WINDOW)
            else:
                self.assertNotIn("creationflags", kwargs)

    @unittest.skipIf(shutil.which("git") is None, "git unavailable")
    def test_git_status_short_is_collected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
            (project / "tracked.txt").write_text("hello\n", encoding="utf-8")

            self.assertTrue(is_git_repository(project))
            info = collect_git_info(project)

            self.assertTrue(info.repository_detected)
            self.assertTrue(any("tracked.txt" in line for line in info.status_lines))


if __name__ == "__main__":
    unittest.main()
