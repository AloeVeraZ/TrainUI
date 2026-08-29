#!/usr/bin/env bash
set -Eeuo pipefail

# Backward-compatible entry point retained for existing Raspberry Pis and old
# documentation. The maintained installer lives with the renamed XL project.
INSTALLER_URL="https://raw.githubusercontent.com/AloeVeraZ/TrainUI/main/Train%20UI%20XL/installer/install.sh"

curl -fsSL "$INSTALLER_URL" | bash
