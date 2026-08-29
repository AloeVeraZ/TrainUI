import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = APP_ROOT.parent
INSTALLER_PATH = APP_ROOT / "installer" / "install.sh"
README_PATH = APP_ROOT / "README.md"
INSTALLER_README_PATH = APP_ROOT / "installer" / "README.md"
REQUIREMENTS_PATH = APP_ROOT / "requirements.txt"
IMAGE_LAUNCHER_PATH = (
    APP_ROOT / "image" / "stage-trainui" / "00-trainui" / "files" /
    "trainui-launcher"
)
IMAGE_BUILD_PATH = APP_ROOT / "image" / "build.sh"
IMAGE_STAGE_PATH = APP_ROOT / "image" / "stage-trainui" / "00-trainui" / "00-run.sh"
RUNTIME_WATCHDOG_PATH = (
    APP_ROOT / "installer" / "systemd" / "90-trainui-runtime-watchdog.conf"
)
ASSEMBLY_GUIDE_PATH = APP_ROOT / "Assembly Guide" / "README.md"
BOM_ASSETS = {
    "B0G5YZJLVZ": "usb-c-to-micro-usb-adapter.jpg",
    "B0CNGV7FQJ": "angled-mini-hdmi-cable.jpg",
    "B0D5V3TZLB": "heat-set-inserts.jpg",
    "B0F3WVBGCP": "usb-c-panel-mount.jpg",
    "B0F87W7P59": "micro-usb-cable.jpg",
    "B0FF4TDYKZ": "countersunk-fasteners.jpg",
    "B0FGJ9FRGQ": "m3-fasteners.jpg",
    "B07ZH9GJWP": "self-tapping-screws.jpg",
}

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
        cls.image_launcher = IMAGE_LAUNCHER_PATH.read_text(encoding="utf-8")
        cls.image_build = IMAGE_BUILD_PATH.read_text(encoding="utf-8")
        cls.image_stage = IMAGE_STAGE_PATH.read_text(encoding="utf-8")
        cls.runtime_watchdog = RUNTIME_WATCHDOG_PATH.read_text(encoding="utf-8")
        cls.assembly_guide = ASSEMBLY_GUIDE_PATH.read_text(encoding="utf-8")

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
            RUNTIME_WATCHDOG_PATH,
        )
        for path in expected_paths:
            with self.subTest(path=path.relative_to(REPOSITORY_ROOT)):
                self.assertTrue(path.is_file())

    def test_installed_launcher_recovers_a_frozen_or_exited_app(self):
        for launcher in (self.installer, self.image_launcher):
            with self.subTest(launcher="installer" if launcher is self.installer else "image"):
                self.assertIn("TRAINUI_HEARTBEAT_FILE", launcher)
                self.assertIn("HEARTBEAT_TIMEOUT_SECONDS=45", launcher)
                self.assertIn("MAX_RUNTIME_SECONDS=86400", launcher)
                self.assertIn("Clock heartbeat was stale", launcher)
                self.assertIn("Daily preventive restart", launcher)
                self.assertIn("kill -KILL", launcher)
                self.assertIn("restarting in 3 seconds", launcher)

    def test_full_pi_hang_enables_the_hardware_watchdog(self):
        self.assertIn("RuntimeWatchdogSec=2min", self.runtime_watchdog)
        self.assertIn("90-trainui-runtime-watchdog.conf", self.installer)
        self.assertIn("dtparam=watchdog=on", self.installer)
        self.assertIn("90-trainui-runtime-watchdog.conf", self.image_build)
        self.assertIn("90-trainui-runtime-watchdog.conf", self.image_stage)
        self.assertIn("dtparam=watchdog=on", self.image_stage)

    def test_bill_of_materials_keeps_every_listing_and_reference_photo(self):
        self.assertIn("> [!WARNING]", self.readme)
        self.assertIn("Assembly%20Guide/", self.readme)
        self.assertTrue(ASSEMBLY_GUIDE_PATH.is_file())
        self.assertIn("bill of materials", self.assembly_guide)

        parts_directory = ASSEMBLY_GUIDE_PATH.parent / "images" / "parts"
        for asin, filename in BOM_ASSETS.items():
            with self.subTest(asin=asin):
                self.assertIn(f"https://www.amazon.com/dp/{asin}", self.readme)
                self.assertIn(filename, self.readme)
                self.assertTrue((parts_directory / filename).is_file())

    def test_public_command_points_directly_to_xl_installer(self):
        self.assertGreaterEqual(self.readme.count(PUBLIC_INSTALL_COMMAND), 2)
        self.assertIn(PUBLIC_INSTALL_COMMAND, self.installer_readme)

    def test_no_duplicate_installer_remains_at_repository_root(self):
        self.assertFalse((REPOSITORY_ROOT / "Train UI").exists())
        self.assertFalse((REPOSITORY_ROOT / "installer").exists())


if __name__ == "__main__":
    unittest.main()
