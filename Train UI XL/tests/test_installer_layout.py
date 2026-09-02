import re
import unittest
import zipfile
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = APP_ROOT.parent
REPOSITORY_README_PATH = REPOSITORY_ROOT / "README.md"
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
CAD_DIRECTORY = APP_ROOT / "CAD"
FULL_ASSEMBLY_STEP_PATH = CAD_DIRECTORY / "case for screen.step"
PRINT_ONLY_STEP_PATH = CAD_DIRECTORY / "Only 3DP files.step"
FUSION_ARCHIVE_PATH = CAD_DIRECTORY / "case for screen.f3z"
XL_PHOTO_PATH = REPOSITORY_ROOT / "assets" / "images" / "train-ui-xl.png"
ASSEMBLY_STEP_ASSETS = {
    "01-faceplate-before-inserts.jpg",
    "02-faceplate-with-inserts.jpg",
    "03-screen-seated-in-faceplate.jpg",
}
ASSEMBLY_STEP_2_ASSETS = {
    "04-middle-plate-before-inserts.jpg",
    "05-middle-plate-with-pi-inserts.jpg",
    "06-pi-zero-w-mounted-and-wired.jpg",
}
ASSEMBLY_STEP_3_ASSETS = {
    "07-power-cable-fed-before-soldering.jpg",
    "08-usbc-power-board-soldered-and-mounted.jpg",
    "09-finished-internal-power-wiring.jpg",
}
ASSEMBLY_STEP_4_ASSETS = {
    "10-back-plate-final-assembly.jpg",
}
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
        cls.repository_readme = REPOSITORY_README_PATH.read_text(encoding="utf-8")
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
            APP_ROOT / "installer" / "wifi_setup.py",
            APP_ROOT / "installer" / "power_schedule.py",
            APP_ROOT / "installer" / "display-power.sh",
            APP_ROOT / "installer" / "systemd" / "trainui-connectivity.service",
            APP_ROOT / "installer" / "systemd" / "trainui-connectivity.timer",
            APP_ROOT / "installer" / "systemd" / "trainui-wifi-setup.service",
            APP_ROOT / "installer" / "systemd" / "trainui-sleep.service",
            APP_ROOT / "installer" / "systemd" / "trainui-sleep.timer",
            APP_ROOT / "installer" / "systemd" / "trainui-wake.service",
            APP_ROOT / "installer" / "systemd" / "trainui-wake.timer",
            APP_ROOT / "installer" / "systemd" / "trainui-schedule-sync.service",
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

    def test_parts_grid_uses_three_columns_with_two_centered_cards(self):
        self.assertEqual(self.readme.count('<td width="33%"'), 6)
        self.assertIn('<td colspan="3" align="center">', self.readme)
        self.assertIn('<table width="67%">', self.readme)

    def test_current_cad_files_are_linked_and_identify_print_only_export(self):
        for path in (FULL_ASSEMBLY_STEP_PATH, PRINT_ONLY_STEP_PATH):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file())
                with path.open("rb") as model:
                    self.assertEqual(model.readline().strip(), b"ISO-10303-21;")

        self.assertTrue(FUSION_ARCHIVE_PATH.is_file())
        self.assertTrue(zipfile.is_zipfile(FUSION_ARCHIVE_PATH))
        for filename in (
            FULL_ASSEMBLY_STEP_PATH.name,
            PRINT_ONLY_STEP_PATH.name,
            FUSION_ARCHIVE_PATH.name,
        ):
            self.assertIn(filename, self.repository_readme)
            self.assertIn(filename, self.readme)
        self.assertIn("Only the parts that need to be 3D printed", self.repository_readme)
        self.assertIn("3D-printed parts only", self.readme)

    def test_real_xl_photo_replaces_generated_placeholder(self):
        self.assertTrue(XL_PHOTO_PATH.is_file())
        self.assertFalse(
            (REPOSITORY_ROOT / "assets" / "images" / "train-ui-xl-placeholder.svg").exists()
        )
        self.assertIn(
            '<img src="assets/images/train-ui-xl.png" width="420"',
            self.repository_readme,
        )
        self.assertIn(
            '<img src="assets/images/train-ui-mini.jpg" width="420"',
            self.repository_readme,
        )
        self.assertIn(
            '<img src="../assets/images/train-ui-xl.png" width="420"',
            self.readme,
        )

    def test_first_assembly_step_keeps_its_instructions_and_photos(self):
        self.assertIn("Step 1 — Prepare the front faceplate", self.assembly_guide)
        self.assertIn("4 M3 × 4 mm heat-set threaded inserts", self.assembly_guide)
        steps_directory = ASSEMBLY_GUIDE_PATH.parent / "images" / "steps"
        for filename in ASSEMBLY_STEP_ASSETS:
            with self.subTest(filename=filename):
                self.assertIn(filename, self.assembly_guide)
                self.assertTrue((steps_directory / filename).is_file())

    def test_second_assembly_step_keeps_its_instructions_and_photos(self):
        self.assertIn("Step 2 — Prepare the middle plate", self.assembly_guide)
        self.assertIn("4 M2 × 4 mm heat-set threaded inserts", self.assembly_guide)
        self.assertIn("4 M2 × 6 mm screws", self.assembly_guide)
        self.assertIn("back plate will not fit correctly", self.assembly_guide)
        steps_directory = ASSEMBLY_GUIDE_PATH.parent / "images" / "steps"
        for filename in ASSEMBLY_STEP_2_ASSETS:
            with self.subTest(filename=filename):
                self.assertIn(filename, self.assembly_guide)
                self.assertTrue((steps_directory / filename).is_file())

    def test_third_assembly_step_keeps_power_wiring_order_and_photos(self):
        self.assertIn("Step 3 — Build and install the USB-C power inlet", self.assembly_guide)
        self.assertIn("before soldering", self.assembly_guide)
        self.assertIn("red wire to `V`", self.assembly_guide)
        self.assertIn("black wire to `G`", self.assembly_guide)
        self.assertIn("not the `USB`/OTG port", self.assembly_guide)
        steps_directory = ASSEMBLY_GUIDE_PATH.parent / "images" / "steps"
        for filename in ASSEMBLY_STEP_3_ASSETS:
            with self.subTest(filename=filename):
                self.assertIn(filename, self.assembly_guide)
                self.assertTrue((steps_directory / filename).is_file())

    def test_final_assembly_step_keeps_squaring_instructions_and_photo(self):
        self.assertIn("Step 4 — Square and close the enclosure", self.assembly_guide)
        self.assertIn("4 M3 × 25 mm screws", self.assembly_guide)
        self.assertIn("approximately 90 degrees to the tabletop", self.assembly_guide)
        self.assertIn("no cable may cross an edge", self.assembly_guide)
        self.assertIn("Phillips-head drywall screw", self.assembly_guide)
        self.assertIn("head about 8 mm wide", self.assembly_guide)
        self.assertIn("wall stud or a suitable drywall anchor", self.assembly_guide)
        steps_directory = ASSEMBLY_GUIDE_PATH.parent / "images" / "steps"
        for filename in ASSEMBLY_STEP_4_ASSETS:
            with self.subTest(filename=filename):
                self.assertIn(filename, self.assembly_guide)
                self.assertTrue((steps_directory / filename).is_file())

    def test_documentation_images_only_link_to_useful_destinations(self):
        documentation_paths = (
            REPOSITORY_ROOT / "README.md",
            APP_ROOT / "README.md",
            INSTALLER_README_PATH,
            ASSEMBLY_GUIDE_PATH,
            REPOSITORY_ROOT / "Train UI Mini" / "README.md",
        )
        markdown_image_link = re.compile(
            r"\[!\[[^\]]*\]\(([^)]+)\)\]\(([^)]+)\)"
        )
        html_image_link = re.compile(
            r'<a href="([^"]+)"><img src="([^"]+)"'
        )
        image_suffixes = (".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp")

        for path in documentation_paths:
            content = path.read_text(encoding="utf-8")
            with self.subTest(path=path.relative_to(REPOSITORY_ROOT)):
                for image_source, link_target in markdown_image_link.findall(content):
                    self.assertNotEqual(image_source, link_target)
                    self.assertFalse(
                        link_target.lower().split("#", 1)[0].endswith(image_suffixes)
                    )
                for link_target, image_source in html_image_link.findall(content):
                    self.assertNotEqual(image_source, link_target)
                    self.assertFalse(
                        link_target.lower().split("#", 1)[0].endswith(image_suffixes)
                    )
                for line in content.splitlines():
                    if "<img " in line:
                        self.assertIn('<a href="', line)
                        self.assertIn("</a>", line)
                    self.assertFalse(re.match(r"^\s*!\[", line))

    def test_wifi_setup_fallback_is_installed_by_script_and_image(self):
        self.assertIn("trainui-wifi-setup init", self.installer)
        self.assertIn("enable --now trainui-wifi-setup.service", self.installer)
        self.assertIn("installer/wifi_setup.py", self.image_build)
        self.assertIn("trainui-wifi-setup.service", self.image_build)
        self.assertIn("trainui-wifi-setup", self.image_stage)
        self.assertIn("enable trainui-wifi-setup.service", self.image_stage)

    def test_daily_display_schedule_is_installer_and_image_compatible(self):
        for expected in (
            "trainui-schedule",
            "trainui-display-power",
            "trainui-sleep.timer",
            "trainui-wake.timer",
            "trainui-schedule-sync.service",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.installer)
                self.assertIn(expected, self.image_stage)
        self.assertIn("--apply-existing", self.installer)
        self.assertIn("--initial", self.installer)
        self.assertIn("/run/trainui/scheduled-sleep", self.installer)
        self.assertIn("/run/trainui/scheduled-sleep", self.image_launcher)
        self.assertIn("Scheduled display sleep", self.installer)
        self.assertIn("Scheduled display sleep", self.image_launcher)

    def test_public_command_points_directly_to_xl_installer(self):
        self.assertGreaterEqual(self.readme.count(PUBLIC_INSTALL_COMMAND), 2)
        self.assertIn(PUBLIC_INSTALL_COMMAND, self.installer_readme)

    def test_no_duplicate_installer_remains_at_repository_root(self):
        self.assertFalse((REPOSITORY_ROOT / "Train UI").exists())
        self.assertFalse((REPOSITORY_ROOT / "installer").exists())


if __name__ == "__main__":
    unittest.main()
