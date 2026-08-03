#!/usr/bin/env bash
set -u

# Keep every detected Wi-Fi interface awake and reconnect a saved profile when
# the interface drops. This script is intentionally a small systemd oneshot;
# the accompanying timer runs it periodically without keeping a daemon alive.

command -v rfkill >/dev/null 2>&1 && rfkill unblock wifi 2>/dev/null || true

for interface_path in /sys/class/net/*; do
    [ -d "$interface_path/wireless" ] || continue
    interface="${interface_path##*/}"

    # Pi Wi-Fi chipsets can become unreliable when power saving is enabled.
    if command -v iw >/dev/null 2>&1; then
        iw dev "$interface" set power_save off 2>/dev/null || true
    fi

    if command -v nmcli >/dev/null 2>&1; then
        nmcli radio wifi on >/dev/null 2>&1 || true
        state="$(nmcli -g GENERAL.STATE device show "$interface" 2>/dev/null || true)"

        case "$state" in
            100*)
                # NetworkManager reports the interface as connected.
                ;;
            *)
                # Reuse a saved connection; never store an SSID or password here.
                echo "[TrainUI] $interface is disconnected; requesting a saved NetworkManager connection."
                if nmcli device connect "$interface" >/dev/null 2>&1; then
                    echo "[TrainUI] $interface reconnected."
                else
                    echo "[TrainUI] $interface is still offline; the timer will retry."
                fi
                ;;
        esac
    elif command -v wpa_cli >/dev/null 2>&1; then
        state="$(wpa_cli -i "$interface" status 2>/dev/null | sed -n 's/^wpa_state=//p')"
        if [ "$state" != "COMPLETED" ]; then
            echo "[TrainUI] $interface is disconnected; requesting wpa_supplicant reassociation."
            wpa_cli -i "$interface" reassociate >/dev/null 2>&1 || true
        fi
    fi
done
