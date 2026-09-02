#!/usr/bin/env bash
set -Eeuo pipefail

IMAGE_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINUI_PROJECT_DIR="$(cd "$IMAGE_SOURCE_DIR/.." && pwd)"
IMAGE_WORK_DIR="${TRAINUI_IMAGE_WORK_DIR:-/tmp/trainui-image-build}"
PI_GEN_DIR="$IMAGE_WORK_DIR/pi-gen"
PI_GEN_REF="${PI_GEN_REF:-master}"
DEFAULT_ROUTE="${TRAINUI_ROUTE:-D}"
DEFAULT_STATION="${TRAINUI_STATION:-B23}"
CUSTOM_STAGE_DIR="$PI_GEN_DIR/stage-trainui"
CUSTOM_STAGE_FILES="$CUSTOM_STAGE_DIR/00-trainui/files"

fail() {
    printf 'TrainUI image build error: %s\n' "$*" >&2
    exit 1
}

if [ "$(uname -s)" != "Linux" ]; then
    fail "pi-gen requires Linux. Run this on Debian/Raspberry Pi OS or in a Linux VM."
fi

for command_name in git python3 rsync; do
    command -v "$command_name" >/dev/null 2>&1 || \
        fail "$command_name is required on the image-build host."
done

case "$IMAGE_WORK_DIR" in
    ""|/)
        fail "TRAINUI_IMAGE_WORK_DIR must be a dedicated non-root directory."
        ;;
esac

mkdir -p "$IMAGE_WORK_DIR"

if [ ! -d "$PI_GEN_DIR/.git" ]; then
    if [ -e "$PI_GEN_DIR" ]; then
        fail "$PI_GEN_DIR exists but is not a pi-gen Git checkout."
    fi
    git clone --depth 1 --branch "$PI_GEN_REF" \
        https://github.com/RPi-Distro/pi-gen.git "$PI_GEN_DIR"
fi

if [ "$(git -C "$PI_GEN_DIR" remote get-url origin)" != \
     "https://github.com/RPi-Distro/pi-gen.git" ]; then
    fail "$PI_GEN_DIR does not point to the official RPi-Distro/pi-gen repository."
fi

# Keep all paths used by debootstrap inside pi-gen and free of spaces.
rsync -a --delete "$IMAGE_SOURCE_DIR/stage-trainui/" "$CUSTOM_STAGE_DIR/"
mkdir -p "$CUSTOM_STAGE_FILES/app/installer/systemd"

install -m 0644 "$TRAINUI_PROJECT_DIR/timertest.py" \
    "$CUSTOM_STAGE_FILES/app/timertest.py"
install -m 0644 "$TRAINUI_PROJECT_DIR/requirements.txt" \
    "$CUSTOM_STAGE_FILES/app/requirements.txt"
install -m 0644 "$TRAINUI_PROJECT_DIR/installer/configure.py" \
    "$CUSTOM_STAGE_FILES/app/installer/configure.py"
install -m 0644 "$TRAINUI_PROJECT_DIR/installer/subway_catalog.json" \
    "$CUSTOM_STAGE_FILES/app/installer/subway_catalog.json"
install -m 0755 "$TRAINUI_PROJECT_DIR/installer/connectivity-watchdog.sh" \
    "$CUSTOM_STAGE_FILES/app/installer/connectivity-watchdog.sh"
install -m 0755 "$TRAINUI_PROJECT_DIR/installer/wifi_setup.py" \
    "$CUSTOM_STAGE_FILES/app/installer/wifi_setup.py"
install -m 0755 "$TRAINUI_PROJECT_DIR/installer/power_schedule.py" \
    "$CUSTOM_STAGE_FILES/app/installer/power_schedule.py"
install -m 0755 "$TRAINUI_PROJECT_DIR/installer/display-power.sh" \
    "$CUSTOM_STAGE_FILES/app/installer/display-power.sh"
install -m 0644 "$TRAINUI_PROJECT_DIR/installer/systemd/trainui-connectivity.service" \
    "$CUSTOM_STAGE_FILES/app/installer/systemd/trainui-connectivity.service"
install -m 0644 "$TRAINUI_PROJECT_DIR/installer/systemd/trainui-connectivity.timer" \
    "$CUSTOM_STAGE_FILES/app/installer/systemd/trainui-connectivity.timer"
install -m 0644 "$TRAINUI_PROJECT_DIR/installer/systemd/trainui-wifi-setup.service" \
    "$CUSTOM_STAGE_FILES/app/installer/systemd/trainui-wifi-setup.service"
for schedule_unit in \
    trainui-sleep.service \
    trainui-sleep.timer \
    trainui-wake.service \
    trainui-wake.timer \
    trainui-schedule-sync.service; do
    install -m 0644 \
        "$TRAINUI_PROJECT_DIR/installer/systemd/$schedule_unit" \
        "$CUSTOM_STAGE_FILES/app/installer/systemd/$schedule_unit"
done
install -m 0644 "$TRAINUI_PROJECT_DIR/installer/systemd/90-trainui-runtime-watchdog.conf" \
    "$CUSTOM_STAGE_FILES/app/installer/systemd/90-trainui-runtime-watchdog.conf"

python3 "$TRAINUI_PROJECT_DIR/installer/configure.py" \
    --catalog "$TRAINUI_PROJECT_DIR/installer/subway_catalog.json" \
    --config "$CUSTOM_STAGE_FILES/config.json" \
    --route "$DEFAULT_ROUTE" \
    --station "$DEFAULT_STATION"

chmod +x \
    "$CUSTOM_STAGE_DIR/prerun.sh" \
    "$CUSTOM_STAGE_DIR/00-trainui/00-run.sh" \
    "$CUSTOM_STAGE_DIR/00-trainui/00-run-chroot.sh" \
    "$CUSTOM_STAGE_FILES/trainui-launcher"

install -m 0644 "$IMAGE_SOURCE_DIR/pi-gen.config" "$PI_GEN_DIR/config-trainui"

# Only export the final customized desktop image, not intermediate Lite/desktop
# images. Repeated builds may safely reuse pi-gen's existing work cache.
touch "$PI_GEN_DIR/stage2/SKIP_IMAGES"
touch "$PI_GEN_DIR/stage4/SKIP_IMAGES"

cd "$PI_GEN_DIR"
if [ "$(id -u)" -eq 0 ]; then
    ./build.sh -c config-trainui
else
    command -v sudo >/dev/null 2>&1 || fail "sudo is required to run pi-gen."
    sudo ./build.sh -c config-trainui
fi

printf '\nTrainUI image artifacts:\n'
find "$PI_GEN_DIR/deploy" -maxdepth 1 -type f \
    \( -name 'TrainUI*.img' -o -name 'TrainUI*.img.xz' \) -print
