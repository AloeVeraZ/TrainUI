#!/bin/bash -e

python3 -m venv --system-site-packages /opt/trainui/.venv
/opt/trainui/.venv/bin/python -m pip install --no-cache-dir --no-deps \
    'gtfs-realtime-bindings>=1.0.0,<2'

/opt/trainui/.venv/bin/python -m py_compile /opt/trainui/timertest.py
TRAINUI_TEST_CONFIG=1 /opt/trainui/.venv/bin/python - <<'PY'
import tkinter
import requests
from google.transit import gtfs_realtime_pb2
from PIL import Image, ImageTk

print("TrainUI image runtime imports passed.")
PY

