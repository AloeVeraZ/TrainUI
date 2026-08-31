#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="https://github.com/AloeVeraZ/TrainUI.git"
REPO_DIR="${TRAINUI_REPO_DIR:-${TRAINUI_APP_DIR:-$HOME/TrainUI}}"
APP_DIR="$REPO_DIR/Train UI XL"
VENV_DIR="$APP_DIR/.venv"
SOURCE_DIR="$APP_DIR"
MAIN_FILE=""
RUNNER="$APP_DIR/run_trainui.sh"
AUTOSTART_DIR="$HOME/.config/autostart"
LABWC_DIR="$HOME/.config/labwc"
TRAINUI_CONFIG_DIR="$HOME/.config/trainui"
TRAINUI_CONFIG_FILE="$TRAINUI_CONFIG_DIR/config.json"
LOG_FILE="$APP_DIR/trainui.log"
DEPENDENCY_STAMP="$VENV_DIR/.trainui-requirements.sha256"
GTFS_WHEEL_URL="https://files.pythonhosted.org/packages/b3/67/1f030547f94716b3259d99ad93467a6608703942bc62f35e43b1bb8bc2e9/gtfs_realtime_bindings-1.0.0-py3-none-any.whl"
GTFS_WHEEL_SHA256="0a9b57a103a5401895b65b6051344003b5fb213523ea4383596be017e6d67e2d"

say() {
    printf '\n\033[1;36m[TrainUI]\033[0m %s\n' "$*"
}

apt_get() {
    local attempt=1
    local max_attempts=20
    local retry_delay=15
    local apt_output

    apt_output="$(mktemp)"

    while true; do
        # Raspberry Pi OS often starts PackageKit during boot. It can briefly
        # own an APT lock while this installer is starting.
        if sudo env DEBIAN_FRONTEND=noninteractive apt-get \
            -o DPkg::Lock::Timeout=60 "$@" 2>&1 | tee "$apt_output"; then
            rm -f "$apt_output"
            return 0
        fi

        if ! grep -Eq \
            'Could not get lock|Unable to (acquire|lock)|is another process using it' \
            "$apt_output"; then
            rm -f "$apt_output"
            return 1
        fi

        if [ "$attempt" -ge "$max_attempts" ]; then
            rm -f "$apt_output"
            fail "APT is still busy after repeated retries. Wait for system updates to finish, then rerun this installer."
        fi

        say "Another system update is using APT. Waiting ${retry_delay} seconds before retrying ($attempt/$max_attempts)..."
        sleep "$retry_delay"
        attempt=$((attempt + 1))
        : > "$apt_output"
    done
}

apt_lists_refreshed=false

refresh_apt_lists() {
    if [ "$apt_lists_refreshed" = false ]; then
        apt_get update
        apt_lists_refreshed=true
    fi
}

package_is_installed() {
    dpkg-query -W -f='${Status}\n' "$1" 2>/dev/null |
        grep -q '^install ok installed$'
}

fail() {
    printf '\n\033[1;31m[TrainUI ERROR]\033[0m %s\n' "$*" >&2
    exit 1
}

trap 'fail "Installation stopped on line $LINENO. Read the error above, then run this installer again."' ERR

if [ "$(id -u)" -eq 0 ]; then
    fail "Run this as your normal Raspberry Pi user. Do not put sudo before it."
fi

if ! command -v sudo >/dev/null 2>&1; then
    fail "sudo is required. Use the normal Raspberry Pi OS user created in Raspberry Pi Imager."
fi

SYSTEM_PACKAGES=(
    ca-certificates
    curl
    git
    python3
    python3-pip
    python3-tk
    python3-venv
    python3-pil
    python3-pil.imagetk
    python3-protobuf
    python3-requests
    fonts-dejavu-core
    iw
    rfkill
    wlr-randr
    x11-xserver-utils
)

missing_packages=()
for package in "${SYSTEM_PACKAGES[@]}"; do
    if ! package_is_installed "$package"; then
        missing_packages+=("$package")
    fi
done

if [ "${#missing_packages[@]}" -gt 0 ]; then
    say "Installing ${#missing_packages[@]} missing Raspberry Pi dependencies..."
    refresh_apt_lists
    apt_get install -y "${missing_packages[@]}"
else
    say "Raspberry Pi dependencies are already installed; skipping APT."
fi

# Install a graphical desktop when Raspberry Pi OS Lite is being used.
if ! command -v labwc >/dev/null 2>&1 && \
   ! command -v startlxde-pi >/dev/null 2>&1; then
    say "No graphical desktop detected. Installing one..."
    refresh_apt_lists

    if apt-cache show rpd-wayland-core >/dev/null 2>&1; then
        apt_get install -y \
            rpd-wayland-core \
            rpd-theme \
            rpd-preferences \
            lightdm
    elif apt-cache show raspberrypi-ui-mods >/dev/null 2>&1; then
        apt_get install -y \
            raspberrypi-ui-mods \
            lightdm
    else
        fail "Desktop packages were not found. Flash Raspberry Pi OS with Desktop and rerun this installer."
    fi
fi

sudo systemctl set-default graphical.target
sudo systemctl enable lightdm 2>/dev/null || true

say "Downloading TrainUI from GitHub..."

install_fresh_copy() {
    local reason="${1:-An existing TrainUI folder was found.}"
    local install_stamp="$(date +%Y%m%d-%H%M%S).$$"
    local backup_dir="${REPO_DIR}.backup.${install_stamp}"
    local fresh_dir="${REPO_DIR}.installing.${install_stamp}"

    say "$reason"
    # Clone before moving the working installation. If GitHub is unavailable,
    # the currently installed copy remains exactly where it was.
    git clone --branch main --single-branch "$REPO_URL" "$fresh_dir"
    mv "$REPO_DIR" "$backup_dir"
    mv "$fresh_dir" "$REPO_DIR"
    say "The previous installation was preserved at $backup_dir"
}

if [ -d "$APP_DIR/.git" ]; then
    # Older installers generated run_trainui.sh without adding it to .gitignore.
    # Ignore installer-owned runtime files (run_trainui.sh, logs, locks, venv)
    # so existing checkouts can be upgraded.
    checkout_changes=""
    checkout_is_valid=true
    if checkout_changes="$(git -C "$APP_DIR" status --porcelain --untracked-files=all)"; then
        checkout_changes="$(
            printf '%s\n' "$checkout_changes" |
                grep -vE '^\?\? (run_trainui\.sh|trainui\.log|\.trainui\.lock|\.venv/)' || true
        )"
    else
        checkout_is_valid=false
    fi

    if [ "$checkout_is_valid" != true ]; then
        install_fresh_copy "The existing Git checkout is damaged; reinstalling it."
    elif ! git -C "$REPO_DIR" fetch --prune origin main; then
        install_fresh_copy "The existing Git checkout could not be updated; reinstalling it."
    elif [ -n "$checkout_changes" ]; then
        install_fresh_copy "Local changes were found; reinstalling a clean copy."
    elif ! git -C "$REPO_DIR" show-ref --verify --quiet refs/heads/main; then
        install_fresh_copy "The existing checkout has no main branch; reinstalling it."
    elif ! git -C "$REPO_DIR" merge-base --is-ancestor main origin/main; then
        install_fresh_copy "The existing main branch has local commits; reinstalling a clean copy."
    else
        git -C "$REPO_DIR" checkout -f main
        git -C "$REPO_DIR" reset --hard origin/main
    fi
else
    if [ -e "$REPO_DIR" ]; then
        install_fresh_copy "A non-Git TrainUI folder was found; reinstalling a clean copy."
    else
        git clone --branch main --single-branch "$REPO_URL" "$REPO_DIR"
    fi
fi

# TrainUI originally occupied the repository root. The current family repo
# keeps the Raspberry Pi build in "Train UI/" beside "Train UI Mini/". Detect
# both layouts so existing flat checkouts and current clones use the same
# installer and preserve the same ~/TrainUI runtime directory.
if [ -f "$APP_DIR/Train UI/timertest.py" ]; then
    SOURCE_DIR="$APP_DIR/Train UI"
fi
MAIN_FILE="$SOURCE_DIR/timertest.py"

if [ ! -f "$MAIN_FILE" ]; then
    fail "timertest.py was not found in the GitHub repository."
fi

if [ ! -f "$SOURCE_DIR/installer/configure.py" ] || \
   [ ! -f "$SOURCE_DIR/installer/subway_catalog.json" ]; then
    fail "The route and station configurator was not found in the GitHub repository."
fi

say "Configuring the train and station..."
mkdir -p "$TRAINUI_CONFIG_DIR"
if [ -t 1 ] && [ -r /dev/tty ]; then
    python3 "$SOURCE_DIR/installer/configure.py" \
        --config "$TRAINUI_CONFIG_FILE" </dev/tty
else
    python3 "$SOURCE_DIR/installer/configure.py" \
        --config "$TRAINUI_CONFIG_FILE" \
        --non-interactive
fi

say "Configuring Wi-Fi reliability and automatic setup fallback..."

# NetworkManager uses 2 for disabled Wi-Fi power saving. This global setting
# contains no network name or credentials. Do not modify individual saved
# connections: their names, backends, and permissions vary between systems.
if command -v nmcli >/dev/null 2>&1; then
    sudo install -d -m 0755 /etc/NetworkManager/conf.d
    sudo tee /etc/NetworkManager/conf.d/90-trainui-wifi.conf >/dev/null <<'EOF'
[connection]
wifi.powersave=2
EOF
fi

if [ ! -f "$SOURCE_DIR/installer/connectivity-watchdog.sh" ] || \
   [ ! -f "$SOURCE_DIR/installer/wifi_setup.py" ] || \
   [ ! -f "$SOURCE_DIR/installer/systemd/trainui-wifi-setup.service" ]; then
    fail "The Wi-Fi setup files were not found in the GitHub repository."
fi

# Keep installing the older oneshot watchdog for Raspberry Pi OS releases that
# do not let NetworkManager control Wi-Fi. Current Raspberry Pi OS uses the new
# service below; retaining this fallback keeps installer upgrades compatible.
sudo install -m 0755 \
    "$SOURCE_DIR/installer/connectivity-watchdog.sh" \
    /usr/local/sbin/trainui-connectivity
sudo install -m 0755 \
    "$SOURCE_DIR/installer/wifi_setup.py" \
    /usr/local/sbin/trainui-wifi-setup
sudo install -m 0644 \
    "$SOURCE_DIR/installer/systemd/trainui-connectivity.service" \
    /etc/systemd/system/trainui-connectivity.service
sudo install -m 0644 \
    "$SOURCE_DIR/installer/systemd/trainui-connectivity.timer" \
    /etc/systemd/system/trainui-connectivity.timer
sudo install -m 0644 \
    "$SOURCE_DIR/installer/systemd/trainui-wifi-setup.service" \
    /etc/systemd/system/trainui-wifi-setup.service

sudo systemctl daemon-reload

WIFI_SETUP_ENABLED=false
if command -v nmcli >/dev/null 2>&1 && \
   nmcli -t -f DEVICE,TYPE device status 2>/dev/null | grep ':wifi$' >/dev/null; then
    # Capture the currently active Raspberry Pi Imager connection before the
    # monitor starts. A rerun while the setup hotspot is active preserves the
    # previously captured client profile.
    if ! sudo /usr/local/sbin/trainui-wifi-setup init >/dev/null; then
        fail "The NetworkManager Wi-Fi setup service could not be initialized."
    fi
    sudo systemctl disable --now trainui-connectivity.timer 2>/dev/null || true
    sudo systemctl enable --now trainui-wifi-setup.service
    WIFI_SETUP_ENABLED=true
else
    # Older installations may still use wpa_supplicant directly. Do not take
    # over their networking during an update; preserve the existing watchdog.
    sudo systemctl disable --now trainui-wifi-setup.service 2>/dev/null || true
    sudo systemctl enable --now trainui-connectivity.timer
    say "NetworkManager does not control a Wi-Fi adapter; keeping the legacy reconnect watchdog."
fi

say "Preparing the TrainUI Python environment..."

if [ ! -x "$VENV_DIR/bin/python" ]; then
    python3 -m venv --system-site-packages "$VENV_DIR"

    "$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel

    if [ -f "$SOURCE_DIR/requirements.txt" ]; then
        "$VENV_DIR/bin/python" -m pip install -r "$SOURCE_DIR/requirements.txt"
    fi
else
    say "Reusing the existing Python environment."
fi
else
    say "Reusing the existing Python environment."
fi

python_imports_ok() {
    "$VENV_DIR/bin/python" -c '
import requests
from google.transit import gtfs_realtime_pb2
from PIL import Image, ImageTk
' >/dev/null 2>&1
}

requirements_hash="$(sha256sum "$APP_DIR/requirements.txt" | awk '{print $1}')"
dependencies_are_current=false

if [ -f "$DEPENDENCY_STAMP" ] && \
   [ "$(cat "$DEPENDENCY_STAMP")" = "$requirements_hash" ] && \
   python_imports_ok; then
    dependencies_are_current=true
fi

if [ "$dependencies_are_current" = true ]; then
    say "Python dependencies are already installed; skipping downloads."
else
    say "Installing the one Python package not provided by Raspberry Pi OS..."
    wheel_dir="$(mktemp -d)"
    wheel_file="$wheel_dir/gtfs_realtime_bindings-1.0.0-py3-none-any.whl"

    curl --fail --silent --show-error --location \
        --connect-timeout 15 \
        --max-time 60 \
        --retry 1 \
        "$GTFS_WHEEL_URL" \
        --output "$wheel_file"

    printf '%s  %s\n' "$GTFS_WHEEL_SHA256" "$wheel_file" | sha256sum --check --status

    env \
        PIP_CONFIG_FILE=/dev/null \
        PIP_DISABLE_PIP_VERSION_CHECK=1 \
        PIP_EXTRA_INDEX_URL= \
        "$VENV_DIR/bin/python" -m pip install \
            --no-index \
            --no-deps \
            "$wheel_file"

    rm -rf "$wheel_dir"
fi

say "Checking timertest.py and its libraries..."

"$VENV_DIR/bin/python" -m py_compile "$MAIN_FILE"

"$VENV_DIR/bin/python" -c '
import tkinter
import requests
from google.transit import gtfs_realtime_pb2
from PIL import Image, ImageTk
print("All TrainUI imports passed.")
'

printf '%s\n' "$requirements_hash" > "$DEPENDENCY_STAMP"

say "Creating the persistent 270-degree launcher..."

cat > "$RUNNER" <<EOF
#!/usr/bin/env bash
set -u

APP_DIR="$APP_DIR"
PYTHON="$VENV_DIR/bin/python"
MAIN_FILE="$MAIN_FILE"
LOG_FILE="$LOG_FILE"
CONFIG_FILE="$TRAINUI_CONFIG_FILE"

export TRAINUI_CONFIG="\$CONFIG_FILE"
export PYTHONUNBUFFERED=1

# This lives in tmpfs, not on the microSD card. timertest.py refreshes it from
# the same callback that updates the visible clock.
HEARTBEAT_FILE="\${XDG_RUNTIME_DIR:-/tmp}/trainui-\${UID}.heartbeat"
HEARTBEAT_TIMEOUT_SECONDS=45
MAX_RUNTIME_SECONDS=86400
export TRAINUI_HEARTBEAT_FILE="\$HEARTBEAT_FILE"

mkdir -p "\$APP_DIR"

# Prevent two desktop autostart mechanisms from opening duplicate windows.
exec 9>"\$APP_DIR/.trainui.lock"
flock -n 9 || exit 0

printf '\n===== TrainUI startup: %s =====\n' "\$(date)" >> "\$LOG_FILE"

rotate_display() {
    local output=""

    # Current Raspberry Pi OS: Wayland/labwc.
    if command -v wlr-randr >/dev/null 2>&1; then
        for _ in \$(seq 1 30); do
            output="\$(wlr-randr 2>/dev/null | awk '/^[^[:space:]]/ {print \$1; exit}')"

            if [ -n "\$output" ] && \
               wlr-randr --output "\$output" --transform 270 >> "\$LOG_FILE" 2>&1; then
                echo "Rotated \$output to 270 degrees." >> "\$LOG_FILE"
                return 0
            fi

            sleep 1
        done
    fi

    # Fallback for older Raspberry Pi OS using X11. "left" is 270 degrees.
    if command -v xrandr >/dev/null 2>&1; then
        for _ in \$(seq 1 30); do
            output="\$(xrandr --query 2>/dev/null | awk '/ connected/{print \$1; exit}')"

            if [ -n "\$output" ] && \
               xrandr --output "\$output" --rotate left >> "\$LOG_FILE" 2>&1; then
                echo "Rotated \$output to 270 degrees." >> "\$LOG_FILE"
                return 0
            fi

            sleep 1
        done
    fi

    echo "WARNING: Display rotation could not be applied." >> "\$LOG_FILE"
    return 0
}

wait_for_mta() {
    for _ in \$(seq 1 30); do
        if "\$PYTHON" - <<'PY' >/dev/null 2>&1
import socket

connection = socket.create_connection(("api-endpoint.mta.info", 443), timeout=2)
connection.close()
PY
        then
            echo "MTA server connection available." >> "\$LOG_FILE"
            return 0
        fi

        sleep 1
    done

    echo "MTA server was not reachable yet; starting TrainUI anyway." >> "\$LOG_FILE"
    return 0
}

keep_display_awake() {
    while true; do
        # X11: disable the screensaver and DPMS, then wake the display.
        if command -v xset >/dev/null 2>&1; then
            xset s off >/dev/null 2>&1 || true
            xset s noblank >/dev/null 2>&1 || true
            xset -dpms >/dev/null 2>&1 || true
            xset dpms force on >/dev/null 2>&1 || true
        fi

        # Wayland/labwc: re-enable an output only if it became disabled.
        if command -v wlr-randr >/dev/null 2>&1; then
            display_state="\$(wlr-randr 2>/dev/null || true)"
            if printf '%s\n' "\$display_state" | grep -q 'Enabled: no'; then
                printf '%s\n' "\$display_state" |
                    awk '/^[^[:space:]]/ {print \$1}' |
                    while IFS= read -r display_output; do
                        [ -n "\$display_output" ] || continue
                        wlr-randr --output "\$display_output" --on \
                            >> "\$LOG_FILE" 2>&1 || true
                    done
            fi
        fi

        sleep 30
    done
}

cd "\$APP_DIR"
rotate_display
wait_for_mta

keep_display_awake &
display_watchdog_pid=\$!
app_pid=""

stop_app() {
    [ -n "\$app_pid" ] || return 0
    kill "\$app_pid" 2>/dev/null || return 0

    for _ in \$(seq 1 5); do
        kill -0 "\$app_pid" 2>/dev/null || return 0
        sleep 1
    done

    kill -KILL "\$app_pid" 2>/dev/null || true
}

cleanup() {
    stop_app
    kill "\$display_watchdog_pid" 2>/dev/null || true
    rm -f "\$HEARTBEAT_FILE"
}
trap cleanup EXIT
trap 'exit 0' INT TERM

# Keep the desktop session and display environment alive while supervising the
# Python process. A stopped clock, crash, or once-daily maintenance recycle all
# recover here without rebooting or waiting for another login.
while true; do
    rm -f "\$HEARTBEAT_FILE"
    app_started_at="\$(date +%s)"
    restart_reason="TrainUI exited"

    "\$PYTHON" "\$MAIN_FILE" >> "\$LOG_FILE" 2>&1 &
    app_pid=\$!
    echo "TrainUI process \$app_pid started." >> "\$LOG_FILE"

    while kill -0 "\$app_pid" 2>/dev/null; do
        sleep 10
        now="\$(date +%s)"
        heartbeat_at="\$app_started_at"
        if [ -e "\$HEARTBEAT_FILE" ]; then
            heartbeat_at="\$(stat -c %Y "\$HEARTBEAT_FILE" 2>/dev/null || echo "\$app_started_at")"
        fi

        if [ "\$((now - heartbeat_at))" -gt "\$HEARTBEAT_TIMEOUT_SECONDS" ]; then
            restart_reason="Clock heartbeat was stale for more than \${HEARTBEAT_TIMEOUT_SECONDS}s"
            stop_app
            break
        fi

        if [ "\$((now - app_started_at))" -ge "\$MAX_RUNTIME_SECONDS" ]; then
            restart_reason="Daily preventive restart"
            stop_app
            break
        fi
    done

    if wait "\$app_pid"; then
        exit_code=0
    else
        exit_code=\$?
    fi
    printf '%s (exit %s); restarting in 3 seconds.\n' \
        "\$restart_reason" "\$exit_code" >> "\$LOG_FILE"
    app_pid=""
    rm -f "\$HEARTBEAT_FILE"
    sleep 3
done
EOF

chmod +x "$RUNNER"

say "Enabling automatic TrainUI startup..."

mkdir -p "$AUTOSTART_DIR" "$LABWC_DIR"

cat > "$AUTOSTART_DIR/trainui.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=TrainUI
Comment=NYC D train departure display
Exec="$RUNNER"
Path=$APP_DIR
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true
EOF

# Raspberry Pi OS Wayland/labwc autostart.
touch "$LABWC_DIR/autostart"
sed -i '/# TRAINUI START/,/# TRAINUI END/d' "$LABWC_DIR/autostart"

cat >> "$LABWC_DIR/autostart" <<EOF
# TRAINUI START
"$RUNNER" &
# TRAINUI END
EOF

say "Enabling desktop auto-login and preventing sleep or blanking..."

if command -v raspi-config >/dev/null 2>&1; then
    sudo raspi-config nonint do_boot_behaviour B4 || true
    sudo raspi-config nonint do_blanking 1 || true
fi

# Prevent system-level idle actions and X11 display power management.
sudo install -d -m 0755 /etc/systemd/logind.conf.d
sudo tee /etc/systemd/logind.conf.d/90-trainui.conf >/dev/null <<'EOF'
[Login]
IdleAction=ignore
EOF

if [ -d /etc/lightdm ] || command -v lightdm >/dev/null 2>&1; then
    sudo install -d -m 0755 /etc/lightdm/lightdm.conf.d
    sudo tee /etc/lightdm/lightdm.conf.d/90-trainui.conf >/dev/null <<'EOF'
[Seat:*]
xserver-command=X -s 0 -dpms
EOF
fi

# A dedicated kiosk should never enter system sleep. Unsupported targets are
# ignored so this remains compatible across Raspberry Pi OS releases.
sudo systemctl mask \
    sleep.target \
    suspend.target \
    hibernate.target \
    hybrid-sleep.target \
    2>/dev/null || true

# Let the Raspberry Pi hardware watchdog recover from a full operating-system
# hang. The application heartbeat above handles the more common GUI-only hang.
if [ ! -f "$APP_DIR/installer/systemd/90-trainui-runtime-watchdog.conf" ]; then
    fail "The runtime watchdog configuration was not found in the GitHub repository."
fi
sudo install -d -m 0755 /etc/systemd/system.conf.d
sudo install -m 0644 \
    "$APP_DIR/installer/systemd/90-trainui-runtime-watchdog.conf" \
    /etc/systemd/system.conf.d/90-trainui-runtime-watchdog.conf

BOOT_CONFIG_FILE="/boot/firmware/config.txt"
if [ ! -f "$BOOT_CONFIG_FILE" ]; then
    BOOT_CONFIG_FILE="/boot/config.txt"
fi
if [ -f "$BOOT_CONFIG_FILE" ] && \
   ! grep -qE '^[[:space:]]*dtparam=watchdog=on([[:space:]]*(#.*)?)?$' "$BOOT_CONFIG_FILE"; then
    printf '\n# TrainUI automatic recovery from a full system hang\ndtparam=watchdog=on\n' | \
        sudo tee -a "$BOOT_CONFIG_FILE" >/dev/null
fi

CMDLINE_FILE="/boot/firmware/cmdline.txt"
if [ ! -f "$CMDLINE_FILE" ]; then
    CMDLINE_FILE="/boot/cmdline.txt"
fi

if [ -f "$CMDLINE_FILE" ]; then
    if grep -qE '(^| )consoleblank=[^ ]+' "$CMDLINE_FILE"; then
        sudo sed -i -E 's/(^| )consoleblank=[^ ]+/ consoleblank=0/g; s/^ //' "$CMDLINE_FILE"
    else
        sudo sed -i 's/$/ consoleblank=0/' "$CMDLINE_FILE"
    fi
fi

say "Installation complete."
echo "The Pi will reboot in five seconds."
echo "TrainUI will start automatically at 270 degrees."
echo "Network-agnostic Wi-Fi reliability checks run every 30 seconds."
echo "A frozen TrainUI process restarts automatically within about one minute."
echo "The application is also recycled once daily and the Pi hardware watchdog is enabled."
if [ "$WIFI_SETUP_ENABLED" = true ]; then
    echo "Wi-Fi fallback: join TrainUI with password TRAINUI1 after 30 seconds offline."
    echo "Wi-Fi setup page: http://10.42.0.1"
else
    echo "Legacy Wi-Fi reliability checks run every 30 seconds."
fi
echo "Desktop, console, X11, Wayland, and system sleep blanking are disabled."
echo "Runtime log: $LOG_FILE"

sync
sleep 5
sudo reboot
