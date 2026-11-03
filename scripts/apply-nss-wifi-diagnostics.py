#!/usr/bin/env python3
"""Add diagnostic-only NSS EAPOL visibility for the opt-in profile."""
from pathlib import Path
import argparse
import shutil
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("openwrt", type=Path)
args = parser.parse_args()

project = Path(__file__).resolve().parent.parent
openwrt = args.openwrt.resolve()
mac_patch = project / "patches/919-ath11k-nss-eapol-diagnostics.patch"
drv_patch = project / "patches/991-nss-wifi-eapol-stats.patch"
mac_dir = openwrt / "package/kernel/mac80211/patches/nss-wifi"
drv_source = openwrt / "package/kernel/nss-wifi-drv/src/nss_wifili.c"

if not mac_dir.is_dir() or not drv_source.is_file():
    raise SystemExit("NSS Wi-Fi patch sources are missing from the pinned tree")

mac_dest = mac_dir / mac_patch.name
if mac_dest.exists():
    raise SystemExit(f"refusing to overwrite existing patch: {mac_dest}")
shutil.copyfile(mac_patch, mac_dest)
subprocess.run(["git", "apply", "--check", str(drv_patch)], cwd=openwrt, check=True)
subprocess.run(["git", "apply", str(drv_patch)], cwd=openwrt, check=True)

source = drv_source.read_text()
if "eapol rx_exception_pass" not in source:
    raise SystemExit("NSS EAPOL stats formatter patch did not apply")
print("NSS EAPOL diagnostics applied; packet routing and offload defaults are unchanged")
