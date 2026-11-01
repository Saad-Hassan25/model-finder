import importlib.util
import os
from pathlib import Path
import shutil
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


class SkillCopyTests(unittest.TestCase):
    def make_copy(self, root):
        source = root / "skills/model-finder"
        for name, content in (("SKILL.md", b"name: model-finder\n"),
                              ("references/guide.md", b"Current guidance\n"),
                              ("scripts/helper.py", b"print('example')\n"),
                              ("assets/sample.bin", b"\x00\r\n")):
            file = source / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(content)
        installed = root / ".agents/skills/model-finder"
        shutil.copytree(source, installed)
        return source, installed

    def test_absent_local_copy_is_optional(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(validator.validate_skill_copy(Path(temp)), [])

    def test_equal_copy_allows_text_line_endings_and_python_caches(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, installed = self.make_copy(root)
            (installed / "references/guide.md").write_bytes(b"Current guidance\r\n")
            cache = installed / "scripts/__pycache__/helper.cpython-310.pyc"
            cache.parent.mkdir()
            cache.write_bytes(b"generated cache")
            (installed / "scripts/helper.pyc").write_bytes(b"generated cache")
            self.assertEqual(validator.validate_skill_copy(root), [])

    def test_changed_reference_or_script_is_detected(self):
        for name in ("SKILL.md", "references/guide.md", "scripts/helper.py"):
            with self.subTest(file=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                _, installed = self.make_copy(root)
                (installed / name).write_bytes(b"stale contents\n")
                errors = validator.validate_skill_copy(root)
                self.assertEqual(len(errors), 1)
                self.assertIn(name, errors[0])

    def test_missing_and_extra_files_are_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, installed = self.make_copy(root)
            (installed / "references/guide.md").unlink()
            (installed / "references/obsolete.md").write_text("old guidance", encoding="utf-8")
            errors = validator.validate_skill_copy(root)
            self.assertEqual(len(errors), 2)
            self.assertTrue(any("missing file" in item and "references/guide.md" in item for item in errors))
            self.assertTrue(any("extra file" in item and "references/obsolete.md" in item for item in errors))

    def test_binary_files_are_compared_exactly(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, installed = self.make_copy(root)
            (installed / "assets/sample.bin").write_bytes(b"\x00\n")
            errors = validator.validate_skill_copy(root)
            self.assertEqual(len(errors), 1)
            self.assertIn("assets/sample.bin", errors[0])


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

    def test_extracted_release_passes_its_own_validator(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = package.build(root / "release.zip")
            extracted = root / "extracted"
            with ZipFile(output) as archive:
                archive.extractall(extracted)
            self.assertEqual(validator.validate(extracted), [])

    def test_repository_validation_rejects_a_stale_local_install(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = package.build(root / "release.zip")
            extracted = root / "extracted"
            with ZipFile(output) as archive:
                archive.extractall(extracted)
            installed = extracted / ".agents/skills/model-finder"
            shutil.copytree(extracted / "skills/model-finder", installed)
            (installed / "references/sources.md").write_text("stale sources", encoding="utf-8")
            errors = validator.validate(extracted)
            self.assertEqual(len(errors), 1)
            self.assertIn("references/sources.md", errors[0])


if __name__ == "__main__":
    unittest.main()
