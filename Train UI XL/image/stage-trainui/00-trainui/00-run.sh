#!/bin/bash -e

install -d -m 0755 "${ROOTFS_DIR}/opt/trainui"
cp -a files/app/. "${ROOTFS_DIR}/opt/trainui/"

install -d -m 0755 "${ROOTFS_DIR}/etc/trainui"
install -m 0644 files/config.json "${ROOTFS_DIR}/etc/trainui/config.json"

install -d -m 0755 "${ROOTFS_DIR}/opt/trainui/bin"
install -m 0755 files/trainui-launcher \
    "${ROOTFS_DIR}/opt/trainui/bin/run-trainui"

install -d -m 0755 "${ROOTFS_DIR}/etc/xdg/autostart"
install -m 0644 files/trainui.desktop \
    "${ROOTFS_DIR}/etc/xdg/autostart/trainui.desktop"

install -m 0755 files/app/installer/connectivity-watchdog.sh \
    "${ROOTFS_DIR}/usr/local/sbin/trainui-connectivity"
install -m 0755 files/app/installer/wifi_setup.py \
    "${ROOTFS_DIR}/usr/local/sbin/trainui-wifi-setup"
install -m 0755 files/app/installer/power_schedule.py \
    "${ROOTFS_DIR}/usr/local/bin/trainui-schedule"
install -m 0755 files/app/installer/display-power.sh \
    "${ROOTFS_DIR}/usr/local/sbin/trainui-display-power"
install -m 0644 files/app/installer/systemd/trainui-connectivity.service \
    "${ROOTFS_DIR}/etc/systemd/system/trainui-connectivity.service"
install -m 0644 files/app/installer/systemd/trainui-connectivity.timer \
    "${ROOTFS_DIR}/etc/systemd/system/trainui-connectivity.timer"
install -m 0644 files/app/installer/systemd/trainui-wifi-setup.service \
    "${ROOTFS_DIR}/etc/systemd/system/trainui-wifi-setup.service"
for schedule_unit in \
    trainui-sleep.service \
    trainui-sleep.timer \
    trainui-wake.service \
    trainui-wake.timer \
    trainui-schedule-sync.service; do
    install -m 0644 \
        "files/app/installer/systemd/$schedule_unit" \
        "${ROOTFS_DIR}/etc/systemd/system/$schedule_unit"
done

install -d -m 0755 "${ROOTFS_DIR}/etc/systemd/system.conf.d"
install -m 0644 files/app/installer/systemd/90-trainui-runtime-watchdog.conf \
    "${ROOTFS_DIR}/etc/systemd/system.conf.d/90-trainui-runtime-watchdog.conf"

install -d -m 0755 "${ROOTFS_DIR}/etc/NetworkManager/conf.d"
install -m 0644 files/90-trainui-wifi.conf \
    "${ROOTFS_DIR}/etc/NetworkManager/conf.d/90-trainui-wifi.conf"

install -d -m 0755 "${ROOTFS_DIR}/etc/systemd/logind.conf.d"
install -m 0644 files/90-trainui-logind.conf \
    "${ROOTFS_DIR}/etc/systemd/logind.conf.d/90-trainui.conf"

on_chroot <<'EOF'
systemctl enable trainui-wifi-setup.service
systemctl enable trainui-schedule-sync.service
systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
EOF

CMDLINE_FILE="${ROOTFS_DIR}/boot/firmware/cmdline.txt"
if [ ! -f "$CMDLINE_FILE" ]; then
    CMDLINE_FILE="${ROOTFS_DIR}/boot/cmdline.txt"
fi
if [ -f "$CMDLINE_FILE" ] && ! grep -q 'consoleblank=0' "$CMDLINE_FILE"; then
    sed -i 's/$/ consoleblank=0/' "$CMDLINE_FILE"
fi

BOOT_CONFIG_FILE="${ROOTFS_DIR}/boot/firmware/config.txt"
if [ ! -f "$BOOT_CONFIG_FILE" ]; then
    BOOT_CONFIG_FILE="${ROOTFS_DIR}/boot/config.txt"
fi
if [ -f "$BOOT_CONFIG_FILE" ] && \
   ! grep -qE '^[[:space:]]*dtparam=watchdog=on([[:space:]]*(#.*)?)?$' "$BOOT_CONFIG_FILE"; then
    printf '\n# TrainUI automatic recovery from a full system hang\ndtparam=watchdog=on\n' \
        >>"$BOOT_CONFIG_FILE"
fi
