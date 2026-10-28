#!/usr/bin/env python3
"""Install the pinned fw4 patch; does not change a live firewall."""
from pathlib import Path
import argparse,shutil
p=argparse.ArgumentParser();p.add_argument('openwrt',type=Path);a=p.parse_args()
build=Path(__file__).resolve().parent.parent
pkg=a.openwrt/'package/network/config/firewall4'
assert 'PKG_SOURCE_VERSION:=bac1d656e09b48e542f860844fe91cbba82abae2' in (pkg/'Makefile').read_text(),'fw4 version changed; revalidate patch before building'
src=build/'patches/990-honk-direct-only-flowtable.patch';assert src.is_file()
dst=pkg/'patches'/src.name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
print('Installed honk native-direct-only fw4 flowtable admission patch')
