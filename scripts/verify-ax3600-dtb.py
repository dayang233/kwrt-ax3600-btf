#!/usr/bin/env python3
"""Read-only check of compiled AX3600 DTB; no external Python modules."""
from pathlib import Path
import struct,sys
b=Path(sys.argv[1]).read_bytes();assert b[:4]==bytes.fromhex('d00dfeed')
total,so,stro=struct.unpack_from('>III',b,4);p=so;stack=[];nodes={}
while p<total:
 t=int.from_bytes(b[p:p+4],'big');p+=4
 if t==1:
  e=b.index(0,p);stack.append(b[p:e].decode());p=(e+4)&~3;nodes['/'.join(stack)]={}
 elif t==2:stack.pop()
 elif t==3:
  n,no=struct.unpack_from('>II',b,p);p+=8;e=b.index(0,stro+no);key=b[stro+no:e].decode();nodes['/'.join(stack)][key]=b[p:p+n];p=(p+n+3)&~3
 elif t==9:break
 else:assert t==4
assert nodes['']['model']==b'Xiaomi AX3600\0'
assert nodes['/chosen']['bootargs-append']==b' root=/dev/ubiblock0_1\0'
expected={'0:sbl1':(0,0x100000),'0:mibib':(0x100000,0x100000),'0:qsee':(0x200000,0x300000),'0:devcfg':(0x500000,0x80000),'0:rpm':(0x580000,0x80000),'0:cdt':(0x600000,0x80000),'0:appsblenv':(0x680000,0x80000),'0:appsbl':(0x700000,0x100000),'0:art':(0x800000,0x80000),'bdata':(0x880000,0x80000),'crash':(0x900000,0x80000),'crash_syslog':(0x980000,0x80000),'rootfs':(0xa00000,0xf000000),'rsvd0':(0xfa00000,0x80000)}
actual={v['label'].rstrip(b'\0').decode():struct.unpack('>II',v['reg']) for p,v in nodes.items() if '/partitions/partition@' in p and 'label' in v}
assert actual==expected,(actual,expected)
assert any(p.endswith('/nvmem-layout/caldata@4d000') for p in nodes)
assert any(v.get('nvmem-cell-names')==b'mac-address\0' for v in nodes.values())
print('Compiled DTB matches this AX3600: 14 partitions, 240MiB single-UBI, rootfs volume 1, ART/NVMEM retained')
