import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


installer = module("install")
package = module("package")
validator = module("validate")


class InstallerTests(unittest.TestCase):
    def test_all_client_destinations(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {}, clear=True):
            home, project = Path(temp) / "home", Path(temp) / "project"
            for client, relative in (("claude", ".claude/skills/model-finder"), ("codex", ".agents/skills/model-finder"), ("opencode", ".config/opencode/skills/model-finder")):
                self.assertEqual(installer.destination(client, "user", home, project), home / relative)
                expected = ".opencode/skills/model-finder" if client == "opencode" else relative
                self.assertEqual(installer.destination(client, "project", home, project), project / expected)

    def test_xdg_config_is_respected(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"XDG_CONFIG_HOME": temp}):
            self.assertEqual(installer.destination("opencode", "user", Path("unused"), Path("unused")), Path(temp) / "opencode/skills/model-finder")

    def test_install_is_complete_and_independent_of_initial_work(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "skill"
            installer.install(installer.SOURCE, target)
            for file in ("SKILL.md", "LICENSE", "references/sources.md", "references/helper.md", "scripts/model_finder.py", "agents/openai.yaml"):
                self.assertTrue((target / file).is_file(), file)
            self.assertFalse(any("Initial Work" in str(p) for p in target.rglob("*")))

    def test_existing_install_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "skill"
            target.mkdir()
            sentinel = target / "SKILL.md"
            sentinel.write_text("personal changes")
            with self.assertRaises(ValueError):
                installer.install(installer.SOURCE, target)
            self.assertEqual(sentinel.read_text(), "personal changes")

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "absent" / "skill"
            installer.install(installer.SOURCE, target, dry_run=True)
            self.assertFalse(target.parent.exists())

    def test_failed_copy_leaves_no_partial_skill(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "skill"
            with patch.object(installer.shutil, "copytree", side_effect=OSError("simulated copy failure")):
                with self.assertRaises(OSError):
                    installer.install(installer.SOURCE, target)
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(temp).iterdir()), [])


class DistributionTests(unittest.TestCase):
    def test_repository_contract(self):
        self.assertEqual(validator.validate(), [])

    def test_release_contains_complete_skill_and_no_local_data(self):
        with tempfile.TemporaryDirectory() as temp:
            output = package.build(Path(temp) / "release.zip")
            with ZipFile(output) as archive:
                names = set(archive.namelist())
                for required in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", ".agents/plugins/marketplace.json", ".mcp.json", "skills/model-finder/SKILL.md", "skills/model-finder/scripts/model_finder.py", "scripts/install.py", "bin/install.mjs", "package.json", "package-lock.json", "INSTALL.md", "LICENSE", "docs/setup.md"):
                    self.assertIn(required, names)
                for name in names:
                    self.assertFalse(any(part in name for part in ("Initial Work", "__pycache__", ".env", ".model-finder/", ".git/")), name)


if __name__ == "__main__":
    unittest.main()
