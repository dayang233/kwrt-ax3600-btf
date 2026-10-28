#!/usr/bin/env python3
from pathlib import Path
import sys
cfg=Path(sys.argv[1]);s=cfg.read_text();values=dict(line.split('=',1) for line in s.splitlines() if line.startswith('CONFIG_') and '=' in line)
required='BPF BPF_SYSCALL BPF_JIT CGROUPS CGROUP_BPF NET_SCHED NET_CLS_ACT NET_XGRESS NET_NS DEBUG_INFO_BTF FTRACE FUNCTION_TRACER DYNAMIC_FTRACE'
for option in required.split():
 assert values.get('CONFIG_'+option)=='y',f'missing built-in CONFIG_{option}'
for option in ['NF_TABLES','NF_TABLES_INET','NFT_CT','NFT_QUEUE','NETFILTER_NETLINK_QUEUE']:
 assert values.get('CONFIG_'+option) in ['y','m'],f'missing CONFIG_{option}'
print('Actual generated kernel configuration passes honk datapath and native UDP tracing requirements')
