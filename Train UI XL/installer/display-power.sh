#!/usr/bin/env bash
set -u

ACTION="${1:-}"
STATE_DIR="/run/trainui"
SLEEP_MARKER="$STATE_DIR/display-sleep-v2"
LEGACY_SLEEP_MARKER="$STATE_DIR/scheduled-sleep"
TRAINUI_USER="${TRAINUI_USER:-pi}"
TRAINUI_HOME="${TRAINUI_HOME:-/home/$TRAINUI_USER}"

if [ "$ACTION" != "sleep" ] && [ "$ACTION" != "wake" ]; then
    echo "Usage: trainui-display-power sleep|wake" >&2
    exit 2
fi

TRAINUI_UID="$(id -u "$TRAINUI_USER" 2>/dev/null || true)"
RUNTIME_DIR="/run/user/$TRAINUI_UID"

run_wayland() {
    [ -n "$TRAINUI_UID" ] || return 1
    [ -d "$RUNTIME_DIR" ] || return 1
    local socket_name=""
    socket_name="$(find "$RUNTIME_DIR" -maxdepth 1 -type s -name 'wayland-*' \
        -printf '%f\n' 2>/dev/null | head -n 1)"
    [ -n "$socket_name" ] || return 1
    runuser -u "$TRAINUI_USER" -- env \
        XDG_RUNTIME_DIR="$RUNTIME_DIR" \
        WAYLAND_DISPLAY="$socket_name" \
        "$@"
}

run_x11() {
    [ -n "$TRAINUI_UID" ] || return 1
    runuser -u "$TRAINUI_USER" -- env \
        DISPLAY=:0 \
        XAUTHORITY="$TRAINUI_HOME/.Xauthority" \
        "$@"
}

restore_legacy_disabled_outputs() {
    # Older TrainUI releases disabled the compositor output with wlr-randr.
    # Re-enable that state once during wake so this update can recover a Pi
    # that was already asleep when the new script was installed.
    command -v wlr-randr >/dev/null 2>&1 || return 0
    run_wayland wlr-randr 2>/dev/null | awk '
        /^[^[:space:]]/ { output=$1 }
        /Enabled: no/ && output != "" { print output }
    ' | while IFS= read -r output; do
        [ -n "$output" ] || continue
        run_wayland wlr-randr --output "$output" --on --transform 270 \
            >/dev/null 2>&1 || true
    done
}

mkdir -p "$STATE_DIR"

if [ "$ACTION" = "sleep" ]; then
    # Do not wake the old launcher's output-disabling sleep loop during an
    # in-place upgrade. The v2 marker is understood by the updated launcher
    # and ignored safely by an already-running older launcher.
    rm -f "$LEGACY_SLEEP_MARKER"
    touch "$SLEEP_MARKER"

    # Power-manage the monitor without disabling the compositor output or
    # stopping TrainUI. Disabling the only output can tear down the desktop
    # session and expose the login screen when it comes back.
    if command -v wlopm >/dev/null 2>&1 && \
       run_wayland wlopm --off '*' >/dev/null 2>&1; then
        exit 0
    fi
    if command -v xset >/dev/null 2>&1 && \
       run_x11 xset dpms force off >/dev/null 2>&1; then
        # An already-running pre-v2 X11 launcher needs its old marker so its
        # display watchdog does not immediately force DPMS back on. Its X11
        # sleep path does not end the desktop session.
        touch "$LEGACY_SLEEP_MARKER"
        exit 0
    fi
    if command -v vcgencmd >/dev/null 2>&1 && \
       vcgencmd display_power 0 >/dev/null 2>&1; then
        exit 0
    fi

    echo "TrainUI could not power off the display without ending the desktop session." >&2
    rm -f "$SLEEP_MARKER" "$LEGACY_SLEEP_MARKER"
    exit 1
else
    # Clear the marker first so the display watchdog cannot race the wake-up.
    rm -f "$SLEEP_MARKER" "$LEGACY_SLEEP_MARKER"
    woke_display=false
    if command -v wlopm >/dev/null 2>&1 && \
       run_wayland wlopm --on '*' >/dev/null 2>&1; then
        woke_display=true
    fi
    if command -v xset >/dev/null 2>&1 && \
       run_x11 xset dpms force on >/dev/null 2>&1; then
        woke_display=true
    fi
    if command -v vcgencmd >/dev/null 2>&1 && \
       vcgencmd display_power 1 >/dev/null 2>&1; then
        woke_display=true
    fi

    restore_legacy_disabled_outputs
    if [ "$woke_display" != true ]; then
        echo "TrainUI could not wake the display through Wayland, X11, or firmware." >&2
        exit 1
    fi
fi
