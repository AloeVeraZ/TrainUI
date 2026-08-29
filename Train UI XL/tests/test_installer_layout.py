import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = APP_ROOT.parent
INSTALLER_PATH = APP_ROOT / "installer" / "install.sh"
README_PATH = APP_ROOT / "README.md"
INSTALLER_README_PATH = APP_ROOT / "installer" / "README.md"
REQUIREMENTS_PATH = APP_ROOT / "requirements.txt"

PUBLIC_INSTALL_COMMAND = (
    "curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/TrainUI/"
    "main/Train%20UI%20XL/installer/install.sh | bash"
)


class InstallerLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.installer = INSTALLER_PATH.read_text(encoding="utf-8")
        cls.readme = README_PATH.read_text(encoding="utf-8")
        cls.installer_readme = INSTALLER_README_PATH.read_text(encoding="utf-8")
        cls.requirements = REQUIREMENTS_PATH.read_text(encoding="utf-8")

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

    def test_reruns_skip_expensive_dependency_work(self):
        self.assertIn('package_is_installed()', self.installer)
        self.assertIn('skipping APT', self.installer)
        self.assertIn('DEPENDENCY_STAMP=', self.installer)
        self.assertIn('skipping downloads', self.installer)
        self.assertNotIn('pip install --upgrade', self.installer)

    def test_python_install_never_uses_the_slow_piwheels_index(self):
        self.assertNotIn('piwheels', self.installer)
        self.assertIn('PIP_CONFIG_FILE=/dev/null', self.installer)
        self.assertIn('PIP_EXTRA_INDEX_URL=', self.installer)
        self.assertIn('--no-index', self.installer)
        self.assertIn('--no-deps', self.installer)
        self.assertIn('GTFS_WHEEL_SHA256=', self.installer)

    def test_system_python_packages_match_bookworm_versions(self):
        self.assertIn('python3-protobuf', self.installer)
        self.assertIn('python3-requests', self.installer)
        self.assertIn('Pillow>=9.4,<13', self.requirements)
        self.assertIn('protobuf>=3.21,<7', self.requirements)
        self.assertIn('requests>=2.28,<3', self.requirements)

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

    def test_public_command_points_directly_to_xl_installer(self):
        self.assertGreaterEqual(self.readme.count(PUBLIC_INSTALL_COMMAND), 2)
        self.assertIn(PUBLIC_INSTALL_COMMAND, self.installer_readme)

    def test_no_duplicate_installer_remains_at_repository_root(self):
        self.assertFalse((REPOSITORY_ROOT / "Train UI").exists())
        self.assertFalse((REPOSITORY_ROOT / "installer").exists())


if __name__ == "__main__":
    unittest.main()
