#!/usr/bin/env python3
"""Compare this AX3600's candidate/runtime DTB against measured 1 GiB layout.
Candidate DTBs often omit /memory; only --runtime can establish bootloader fixup.
"""
from pathlib import Path
import argparse,json,struct
p=argparse.ArgumentParser();p.add_argument('dtb',type=Path);p.add_argument('--runtime',action='store_true');p.add_argument('--kernel-image',type=Path,help='uncompressed ARM64 Image');p.add_argument('--kernel-load',type=lambda s:int(s,0),default=0x41000000);a=p.parse_args()
b=a.dtb.read_bytes();assert b[:4]==bytes.fromhex('d00dfeed'),'Not a DTB'
total,so,stro=struct.unpack_from('>III',b,4);assert total<=len(b)
i=so;stack=[];nodes={}
while i<total:
 t=int.from_bytes(b[i:i+4],'big');i+=4
 if t==1:
  e=b.index(0,i);stack.append(b[i:e].decode());i=(e+4)&~3;nodes['/'.join(stack)]={}
 elif t==2:stack.pop()
 elif t==3:
  n,no=struct.unpack_from('>II',b,i);i+=8;e=b.index(0,stro+no);key=b[stro+no:e].decode();nodes['/'.join(stack)][key]=b[i:i+n];i=(i+n+3)&~3
 elif t==9:break
 else:assert t==4,'invalid token'
def reg64(v):
 assert len(v)%16==0
 return [struct.unpack_from('>QQ',v,i) for i in range(0,len(v),16)]
# Exact base/size pairs found in both good-fdt-1.bin and captured live.dtb.
expected={(0x40000000,0x01000000):'NSS',(0x4a400000,0x00100000):'TZAPP',(0x4a600000,0x00400000):'bootloader',(0x4aa00000,0x00100000):'SBL',(0x4ab00000,0x00100000):'SMEM',(0x4ac00000,0x00400000):'reserved',(0x4b000000,0x03700000):'Wi-Fi/Q6',(0x4e700000,0x00100000):'Q6 ETR',(0x4e800000,0x00100000):'M3 dump'}
actual={r:node for node,v in nodes.items() if node.startswith('/reserved-memory/') and 'reg' in v for r in reg64(v['reg'])}
# PPE-NSS 6.18 patch 0930 adds a ramoops@pstore carveout on top of the
# measured good/live layout; treat it as a known, documented addition.
allowed_extra={(0x51200000,0x00100000):'ramoops'}
missing=set(expected)-set(actual)
unexpected=set(actual)-set(expected)-set(allowed_extra)
assert not missing,{'missing':sorted(missing)}
assert not unexpected,{'unexpected':sorted(unexpected)}
for r,node in actual.items():
 assert 'no-map' in nodes[node],f'reserved area became mapped: {node}'
 assert 0x40000000<=r[0]<r[0]+r[1]<=0x80000000
ranges=sorted(actual)
for first,second in zip(ranges,ranges[1:]):assert first[0]+first[1]<=second[0],'Reserved-memory overlap'
mem=[r for v in nodes.values() if v.get('device_type')==b'memory\0' for r in reg64(v['reg'])]
if mem:assert mem==[(0x40000000,0x40000000)],f'RAM changed: {mem}'
if a.runtime:assert mem,'Runtime /memory missing; cannot verify 1 GiB fixup'
# If new DTB describes NSS cores, every load address must stay inside the old NSS carveout.
loads=[int.from_bytes(v['qcom,load-addr'],'big') for v in nodes.values() if 'qcom,load-addr' in v]
for addr in loads:assert 0x40000000<=addr<0x41000000,f'NSS core load outside carveout: {addr:#x}'
kernel=None
if a.kernel_image:
 raw=a.kernel_image.read_bytes();assert raw[56:60]==b'ARMd','Expected uncompressed ARM64 Image'
 size=struct.unpack_from('<Q',raw,16)[0] or len(raw);assert size>=len(raw)
 start=a.kernel_load;end=start+size;assert 0x40000000<=start<end<=0x80000000
 for base,length in actual:assert end<=base or start>=base+length,f'Kernel overlaps {expected.get((base,length),"reserved")} at {base:#x}'
 kernel={'load':hex(start),'reserved_image_size':size,'end':hex(end)}
print(json.dumps({'reserved_layout':'matches measured good/live DTB','reserved_total_bytes':sum(size for _,size in actual),'ram_capacity':'runtime 1 GiB verified' if a.runtime else ('DTB declares 1 GiB; still need runtime fixup acceptance' if mem else 'not in candidate DTB; must verify runtime bootloader fixup'),'nss_core_loads':[hex(x) for x in loads],'kernel_image':kernel,'runtime_memory_profile':'not inferred from RAM; inspect NSS driver/firmware and real traffic'},indent=2))
