#!/usr/bin/env python3
"""Match this modified AX3600's existing single-UBI layout. No flash writes."""
from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('openwrt',type=Path);args=p.parse_args();root=args.openwrt
base=root/'target/linux/qualcommax'
dts=base/'dts/ipq8071-ax3600.dtsi'
platform=base/'ipq807x/base-files/lib/upgrade/platform.sh'
s=dts.read_text()
old='''\t\t\tpartition@900000 {
\t\t\t\t/* This is crash + crash_syslog parts combined */
\t\t\t\tlabel = "pstore";
\t\t\t\treg = <0x900000 0x100000>;
\t\t\t};

\t\t\t/* Make the first rootfs a dedicated ubi partition for kernel */
\t\t\tpartition@a00000 {
\t\t\t\tlabel = "ubi_kernel";
\t\t\t\treg = <0xa00000 0x23c0000>;
\t\t\t};

\t\t\t/* Place the real rootfs in the original second rootfs and
\t\t\t * expand it to the end of the nand
\t\t\t */
\t\t\trootfs: partition@2dc0000 {
\t\t\t\tlabel = "rootfs";
\t\t\t\treg = <0x2dc0000 0xd240000>;
\t\t\t};'''
new='''\t\t\t/* This device already has a 240 MiB rootfs in its SMEM table.
\t\t\t * Mirror that layout while retaining the ART NVMEM cells above.
\t\t\t * The factory UBI contains kernel(0), rootfs(1), rootfs_data(2).
\t\t\t */
\t\t\tpartition@900000 {
\t\t\t\tlabel = "crash";
\t\t\t\treg = <0x900000 0x80000>;
\t\t\t};
\t\t\tpartition@980000 {
\t\t\t\tlabel = "crash_syslog";
\t\t\t\treg = <0x980000 0x80000>;
\t\t\t};
\t\t\trootfs: partition@a00000 {
\t\t\t\tlabel = "rootfs";
\t\t\t\treg = <0xa00000 0xf000000>;
\t\t\t};
\t\t\tpartition@fa00000 {
\t\t\t\tlabel = "rsvd0";
\t\t\t\treg = <0xfa00000 0x80000>;
\t\t\t\tread-only;
\t\t\t};'''
old=old.replace('reg = <0x2dc0000 0xd240000>;', 'reg = <0x2dc0000 0xd240000>;\n\t\t\t\tlinux,rootfs;')
new=new.replace('reg = <0xa00000 0xf000000>;', 'reg = <0xa00000 0xf000000>;\n\t\t\t\tlinux,rootfs;')
assert s.count(old)==1,'DTS changed upstream; inspect before applying'
assert s.count(' root=/dev/ubiblock0_0')==1
s=s.replace(old,new).replace(' root=/dev/ubiblock0_0',' root=/dev/ubiblock0_1')
# Do not modify sibling AX6 using the shared dtsi. Clone a private include for AX3600.
private=dts.with_name('ipq8071-ax3600-single-ubi.dtsi')
private.write_text(s)
board=dts.with_name('ipq8071-ax3600.dts');b=board.read_text()
assert b.count('#include "ipq8071-ax3600.dtsi"')==1
board.write_text(b.replace('#include "ipq8071-ax3600.dtsi"','#include "ipq8071-ax3600-single-ubi.dtsi"'))
s=platform.read_text()
# Remove AX3600 from the shared destructive initramfs/split-UBI handlers.
assert s.count('\txiaomi,ax3600|\\\n')==2
s=s.replace('\txiaomi,ax3600|\\\n','')
needle='platform_do_upgrade() {\n\tcase "$(board_name)" in\n'
handler='''\txiaomi,ax3600)
\t\t# This board's bootloader uses a single rootfs MTD. Never change
\t\t# U-Boot flags or assume a stock split-UBI partition scheme here.
\t\t[ "$(cat /sys/class/mtd/mtd$(find_mtd_index rootfs)/size)" = "251658240" ] || {
\t\t\techo "AX3600 single-UBI layout mismatch" >&2
\t\t\treturn 1
\t\t}
\t\tCI_UBIPART="rootfs"
\t\tCI_KERNPART="kernel"
\t\tCI_ROOTPART="rootfs"
\t\tunset CI_KERN_UBIPART CI_ROOT_UBIPART CI_DATA_UBIPART
\t\tnand_do_upgrade "$1"
\t\t;;
'''
assert s.count(needle)==1
platform.write_text(s.replace(needle,needle+handler))
# Raw kernel config overlay. Required options are independently asserted after compilation.
config=base/'config-6.18'
config.write_text(config.read_text()+'''\n# AX3600 honk datapath requirements
CONFIG_BPF=y
CONFIG_BPF_SYSCALL=y
CONFIG_BPF_JIT=y
CONFIG_CGROUPS=y
CONFIG_CGROUP_BPF=y
CONFIG_NET_NS=y
CONFIG_NET_SCHED=y
CONFIG_NET_CLS_ACT=y
CONFIG_NET_XGRESS=y
CONFIG_FTRACE=y
CONFIG_FUNCTION_TRACER=y
CONFIG_DYNAMIC_FTRACE=y
''')
print('Applied AX3600 single-UBI layout; shared board include and other devices unchanged')
