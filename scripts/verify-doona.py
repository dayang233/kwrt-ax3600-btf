#!/usr/bin/env python3
"""Check the Doona bundle shipped by pinned luci-app-honk. No downloads."""
from pathlib import Path
import argparse,hashlib,re
p=argparse.ArgumentParser();p.add_argument('bundle',type=Path);a=p.parse_args();root=a.bundle
index=root/'index.html';assert index.is_file(),'Doona absent; do not rely on runtime download'
expected='52dabb6631ffa62ff1eb4f019066355bdfef1762cc20703be2e2ea6fe25d46bd'
assert hashlib.sha256(index.read_bytes()).hexdigest()==expected,'Doona index changed; revalidate native API contract'
refs=re.findall(r'(?:src|href)=["\']\./([^"\']+)["\']',index.read_text())
for ref in refs:assert (root/ref).is_file(),f'Missing Doona entry asset: {ref}'
assert (root/'sw.js').is_file()
assets=list((root/'assets').glob('*'));assert len(assets)>=100,'Doona bundle incomplete'
print(f'Pinned Doona index and {len(assets)} assets present; entry references resolve')
