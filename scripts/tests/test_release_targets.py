import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

import yaml


class ReleaseTargetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.root = Path(cls.directory.name)
        entries = [
            {"in": {"inventory": {"BOARD": board, "BOARD_SUPPORT_LEVEL": "csc",
                                   "BOARD_HAS_VIDEO": True},
                    "vars": {"BRANCH": "current"}}, "out": {"ARCH": "arm64"}}
            for board in ["regular-board", "manual-board", "blocked-board"]
        ]
        inventory = cls.root / "image-info.json"
        inventory.write_text(json.dumps(entries))
        (cls.root / "targets-release-community-maintained.blacklist").write_text(
            "manual-board\nblocked-board\n")
        (cls.root / "targets-release-community-maintained.manual").write_text("""
manual-cli:
  enabled: yes
  pipeline:
    gha: *armbian-gha
  vars: { RELEASE: DEBIAN, BUILD_MINIMAL: "no", BUILD_DESKTOP: "no" }
  items:
    - { BOARD: manual-board, BRANCH: current }
manual-desktop:
  enabled: yes
  pipeline:
    gha: *armbian-gha
  vars: { RELEASE: UBUNTU, BUILD_DESKTOP: "yes", DESKTOP_ENVIRONMENT: kde-plasma }
  items:
    - { BOARD: manual-board, BRANCH: current }
""")
        (cls.root / "exposed.map.overrides.yaml").write_text("""
overrides:
  - boards: [manual-board]
    minimal:
      suffix: ""
    desktop:
      suffix: kde-plasma_desktop
""")
        script = Path(__file__).resolve().parents[1] / "generate_targets.py"
        subprocess.run([sys.executable, str(script), str(inventory), str(cls.root)],
                       check=True, capture_output=True, text=True)
        cls.patterns = (cls.root / "exposed.map").read_text().splitlines()
        cls.targets = yaml.safe_load(
            (cls.root / "targets-release-community-maintained.yaml").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def matches(self, filename):
        return any(re.fullmatch(pattern, filename) for pattern in self.patterns)

    def test_manual_images_remain_recommended(self):
        self.assertIn("manual-cli", self.targets["targets"])
        prefix = "Armbian_community_26.11.0-trunk.1_Manual-board_"
        self.assertTrue(self.matches(prefix + "trixie_current_6.18.42.img.xz"))
        self.assertTrue(self.matches(prefix + "resolute_current_6.18.42_kde-plasma_desktop.img.xz"))
        self.assertFalse(self.matches(prefix + "trixie_current_6.18.42_minimal.img.xz"))

    def test_blacklisted_board_without_targets_stays_hidden(self):
        self.assertFalse(any("Blocked-board" in pattern for pattern in self.patterns))

    def test_regular_images_remain_recommended(self):
        prefix = "Armbian_community_26.11.0-trunk.1_Regular-board_"
        self.assertTrue(self.matches(prefix + "trixie_current_6.18.42_minimal.img.xz"))
        self.assertTrue(self.matches(prefix + "resolute_current_6.18.42_gnome_desktop.img.xz"))


if __name__ == "__main__":
    unittest.main()
