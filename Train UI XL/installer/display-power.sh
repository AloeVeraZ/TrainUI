#!/usr/bin/env bash
set -u

ACTION="${1:-}"
STATE_DIR="/run/trainui"
SLEEP_MARKER="$STATE_DIR/scheduled-sleep"
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

wayland_outputs() {
    run_wayland wlr-randr 2>/dev/null | awk '/^[^[:space:]]/ {print $1}'
}

x11_outputs() {
    run_x11 xrandr --query 2>/dev/null | awk '/ connected/{print $1}'
}

mkdir -p "$STATE_DIR"

if [ "$ACTION" = "sleep" ]; then
    touch "$SLEEP_MARKER"

    # The launcher sees the marker and will not restart TrainUI until wake time.
    if [ -n "$TRAINUI_UID" ]; then
        pkill -TERM -u "$TRAINUI_UID" -f '/timertest[.]py([[:space:]]|$)' \
            2>/dev/null || true
    fi

    if command -v wlr-randr >/dev/null 2>&1; then
        while IFS= read -r output; do
            [ -n "$output" ] || continue
            run_wayland wlr-randr --output "$output" --off >/dev/null 2>&1 || true
        done < <(wayland_outputs)
    fi
    if command -v xset >/dev/null 2>&1; then
        run_x11 xset dpms force off >/dev/null 2>&1 || true
    fi
    if command -v xrandr >/dev/null 2>&1; then
        while IFS= read -r output; do
            [ -n "$output" ] || continue
            run_x11 xrandr --output "$output" --off >/dev/null 2>&1 || true
        done < <(x11_outputs)
    fi
    command -v vcgencmd >/dev/null 2>&1 && \
        vcgencmd display_power 0 >/dev/null 2>&1 || true
else
    # Clear the marker first so the launcher cannot race this wake-up by
    # issuing another display-off command while the output is coming back.
    rm -f "$SLEEP_MARKER"
    command -v vcgencmd >/dev/null 2>&1 && \
        vcgencmd display_power 1 >/dev/null 2>&1 || true
    if command -v wlr-randr >/dev/null 2>&1; then
        while IFS= read -r output; do
            [ -n "$output" ] || continue
            run_wayland wlr-randr --output "$output" --on --transform 270 \
                >/dev/null 2>&1 || true
        done < <(wayland_outputs)
    fi
    if command -v xrandr >/dev/null 2>&1; then
        while IFS= read -r output; do
            [ -n "$output" ] || continue
            run_x11 xrandr --output "$output" --auto --rotate left \
                >/dev/null 2>&1 || true
        done < <(x11_outputs)
    fi
    if command -v xset >/dev/null 2>&1; then
        run_x11 xset dpms force on >/dev/null 2>&1 || true
    fi
fi
