#!/usr/bin/env python3
"""Install non-secret, per-image first-boot defaults and lifecycle guards."""
from pathlib import Path
import argparse, shutil, json
p=argparse.ArgumentParser();p.add_argument('openwrt',type=Path);p.add_argument('profile',choices=['stable','accelerated']);a=p.parse_args()
project=Path(__file__).resolve().parent.parent
root=a.openwrt/'files';defaults=root/'etc/uci-defaults';defaults.mkdir(parents=True,exist_ok=True)
for name in ['99-honk-safe','99zz-honk-doona']:
    shutil.copyfile(project/'files'/name,defaults/name);(defaults/name).chmod(0o755)
s=(project/'files/99-ppe-lan').read_text()
if a.profile=='stable':
    s=s.replace("flow_offloading='1'","flow_offloading='0'").replace("flow_offloading_hw='1'","flow_offloading_hw='0'").replace("nss-wifi.general.offload='1'","nss-wifi.general.offload='0'")
(defaults/'99-ppe-lan').write_text(s);(defaults/'99-ppe-lan').chmod(0o755)
dest=root/'usr/bin/honk-hw-close';dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(project/'files/honk-hw-close',dest);dest.chmod(0o755)
(root/'etc/ax3600-build-profile').write_text(a.profile+'\n')
lock=json.loads((project/'configs/feed-lock.json').read_text())
lines=[f"src-git {name} {spec['url']}^{spec['commit']}" for name,spec in lock.items()]
lines.append('src-git nss https://github.com/JuliusBairaktaris/nss-packages.git^1f60d7e9409930bbd298eae1831c5b76d21eb1d2')
(a.openwrt/'feeds.conf').write_text('\n'.join(lines)+'\n')
print(f'Prepared {a.profile}: NSS stack compiled in both; safe CPU baseline versus gated hardware experiment')
