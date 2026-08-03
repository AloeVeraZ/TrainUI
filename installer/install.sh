#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="https://github.com/AloeVeraZ/TrainUI.git"
APP_DIR="${TRAINUI_APP_DIR:-$HOME/TrainUI}"
VENV_DIR="$APP_DIR/.venv"
MAIN_FILE="$APP_DIR/timertest.py"
RUNNER="$APP_DIR/run_trainui.sh"
AUTOSTART_DIR="$HOME/.config/autostart"
LABWC_DIR="$HOME/.config/labwc"
LOG_FILE="$APP_DIR/trainui.log"

say() {
    printf '\n\033[1;36m[TrainUI]\033[0m %s\n' "$*"
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

say "Installing Raspberry Pi and Python dependencies..."

sudo apt-get update

sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates \
    curl \
    git \
    python3 \
    python3-pip \
    python3-tk \
    python3-venv \
    python3-pil \
    python3-pil.imagetk \
    fonts-dejavu-core \
    wlr-randr \
    x11-xserver-utils

# Install a graphical desktop when Raspberry Pi OS Lite is being used.
if ! command -v labwc >/dev/null 2>&1 && \
   ! command -v startlxde-pi >/dev/null 2>&1; then
    say "No graphical desktop detected. Installing one..."

    if apt-cache show rpd-wayland-core >/dev/null 2>&1; then
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
            rpd-wayland-core \
            rpd-theme \
            rpd-preferences \
            lightdm
    elif apt-cache show raspberrypi-ui-mods >/dev/null 2>&1; then
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
            raspberrypi-ui-mods \
            lightdm
    else
        fail "Desktop packages were not found. Flash Raspberry Pi OS with Desktop and rerun this installer."
    fi
fi

sudo systemctl set-default graphical.target
sudo systemctl enable lightdm 2>/dev/null || true

say "Downloading TrainUI from GitHub..."

if [ -d "$APP_DIR/.git" ]; then
    if [ -n "$(git -C "$APP_DIR" status --porcelain)" ]; then
        fail "$APP_DIR contains local changes. Commit or remove them before updating."
    fi

    git -C "$APP_DIR" fetch --prune origin main
    git -C "$APP_DIR" checkout main
    git -C "$APP_DIR" pull --ff-only origin main
else
    if [ -e "$APP_DIR" ]; then
        backup_dir="${APP_DIR}.backup.$(date +%Y%m%d-%H%M%S)"
        mv "$APP_DIR" "$backup_dir"
        say "Existing $APP_DIR moved to $backup_dir"
    fi

    git clone --branch main --single-branch "$REPO_URL" "$APP_DIR"
fi

if [ ! -f "$MAIN_FILE" ]; then
    fail "timertest.py was not found in the GitHub repository."
fi

say "Creating the TrainUI Python environment..."

python3 -m venv --system-site-packages "$VENV_DIR"

"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel

if [ -f "$APP_DIR/requirements.txt" ]; then
    "$VENV_DIR/bin/python" -m pip install -r "$APP_DIR/requirements.txt"
else
    "$VENV_DIR/bin/python" -m pip install requests protobuf gtfs-realtime-bindings pillow
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

say "Creating the persistent 270-degree launcher..."

cat > "$RUNNER" <<EOF
#!/usr/bin/env bash
set -u

APP_DIR="$APP_DIR"
PYTHON="$VENV_DIR/bin/python"
MAIN_FILE="$MAIN_FILE"
LOG_FILE="$LOG_FILE"

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

cd "\$APP_DIR"
rotate_display
wait_for_mta

exec "\$PYTHON" "\$MAIN_FILE" >> "\$LOG_FILE" 2>&1
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
Exec=$RUNNER
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
$RUNNER &
# TRAINUI END
EOF

say "Enabling desktop auto-login and disabling blanking..."

if command -v raspi-config >/dev/null 2>&1; then
    sudo raspi-config nonint do_boot_behaviour B4 || true
    sudo raspi-config nonint do_blanking 1 || true
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
echo "Runtime log: $LOG_FILE"

sync
sleep 5
sudo reboot
