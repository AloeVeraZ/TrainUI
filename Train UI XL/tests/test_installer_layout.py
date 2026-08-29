import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = APP_ROOT.parent
INSTALLER_PATH = APP_ROOT / "installer" / "install.sh"
LEGACY_INSTALLER_PATH = REPOSITORY_ROOT / "Train UI" / "installer" / "install.sh"
README_PATH = APP_ROOT / "README.md"

PUBLIC_INSTALL_COMMAND = (
    "curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/TrainUI/"
    "main/Train%20UI/installer/install.sh | bash"
)
MAINTAINED_INSTALLER_URL = (
    "https://raw.githubusercontent.com/AloeVeraZ/TrainUI/"
    "main/Train%20UI%20XL/installer/install.sh"
)


class InstallerLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.installer = INSTALLER_PATH.read_text(encoding="utf-8")
        cls.legacy_installer = LEGACY_INSTALLER_PATH.read_text(encoding="utf-8")
        cls.readme = README_PATH.read_text(encoding="utf-8")

    def test_repository_and_xl_application_paths_are_separate(self):
        self.assertIn(
            'REPO_DIR="${TRAINUI_REPO_DIR:-${TRAINUI_APP_DIR:-$HOME/TrainUI}}"',
            self.installer,
        )
        self.assertIn('APP_DIR="$REPO_DIR/Train UI XL"', self.installer)
        self.assertIn('MAIN_FILE="$APP_DIR/timertest.py"', self.installer)
        self.assertIn('RUNNER="$APP_DIR/run_trainui.sh"', self.installer)
        self.assertNotIn('git -C "$APP_DIR"', self.installer)

    def test_autostart_quotes_the_xl_launcher_path(self):
        self.assertIn('Exec="$RUNNER"', self.installer)
        self.assertIn('"$RUNNER" &', self.installer)

    def test_expected_xl_files_exist_at_installer_runtime_locations(self):
        expected_paths = (
            APP_ROOT / "timertest.py",
            APP_ROOT / "requirements.txt",
            APP_ROOT / "installer" / "configure.py",
            APP_ROOT / "installer" / "subway_catalog.json",
            APP_ROOT / "installer" / "connectivity-watchdog.sh",
            APP_ROOT / "installer" / "systemd" / "trainui-connectivity.service",
            APP_ROOT / "installer" / "systemd" / "trainui-connectivity.timer",
        )
        for path in expected_paths:
            with self.subTest(path=path.relative_to(REPOSITORY_ROOT)):
                self.assertTrue(path.is_file())

    def test_old_public_command_redirects_to_maintained_xl_installer(self):
        self.assertIn(MAINTAINED_INSTALLER_URL, self.legacy_installer)
        self.assertIn('curl -fsSL "$INSTALLER_URL" | bash', self.legacy_installer)
        self.assertGreaterEqual(self.readme.count(PUBLIC_INSTALL_COMMAND), 2)


if __name__ == "__main__":
    unittest.main()
