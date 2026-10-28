#!/usr/bin/env python3
"""Close the hardware whitelist before package-managed honk lifecycle actions."""
from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('openwrt',type=Path);a=p.parse_args()
path=a.openwrt/'package/honk/files/honk.init';s=path.read_text()
assert '/usr/bin/honk-hw-close' not in s,'gate hooks already installed; inspect before retry'
for marker in ['start_service() {','service_stopped() {','hot_reload() {']:
    assert s.count(marker)==1, f'Changed honk init: {marker}'
assert 'stop_service() {' not in s
s=s.replace('start_service() {','start_service() {\n    /usr/bin/honk-hw-close || return 1',1)
s=s.replace('service_stopped() {','stop_service() {\n    # rc.common invokes this before procd_kill. Admission never auto-reopens.\n    /usr/bin/honk-hw-close || return 1\n}\n\nservice_stopped() {',1)
s=s.replace('hot_reload() {','hot_reload() {\n    /usr/bin/honk-hw-close || return 1',1)
path.write_text(s)
print('Honk init start/stop/hot_reload now close hardware admission first; no automatic gate reopen')
