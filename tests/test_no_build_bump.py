"""Building never changes a version: bump.py is the one explicit way to raise it."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class BuildScriptsDoNotBumpTests(unittest.TestCase):
    def test_no_build_script_runs_a_bump(self):
        offenders = []
        for script in sorted([*ROOT.glob("*.sh"), *ROOT.glob("*.bat")]):
            for number, line in enumerate(script.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
                code = line.strip()
                if code.startswith(("#", "REM ", "rem ", "echo", "printf")):
                    continue
                if "bump_version.py" in code or "bump_manifest_version.py" in code or "bump.py" in code:
                    offenders.append(f"{script.name}:{number}: {code}")
        self.assertEqual(offenders, [])

    def test_the_explicit_bump_command_exists(self):
        self.assertTrue((ROOT / "bump.py").is_file())


if __name__ == "__main__":
    unittest.main()
