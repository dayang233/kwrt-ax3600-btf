# Native-direct-only admission

Source pins: honk v0.1.0-beta.3; fw4 bac1d656e09b48e542f860844fe91cbba82abae2; PPE-NSS 74c3517f72f8a2c8bdb97a1115fe1426ae607267.

Use `dip(geoip: cn) && !dport(53) -> direct(mark: 0x200, must)` in honk Rule mode, with the default global effective socket mark 0x100. Never reuse direct policy mark 0x200 as the global mark. Other/private/local direct rules should carry no 0x200 mark. DNS policy remains separately configured.

Firmware fw4 gate is empty on boot/reload: no flow is admitted to the software or hardware flowtable until the gate is opened. After confirming honk READY, CN/direct marking, and proxy behavior, one manual enable command is:

    nft add element inet fw4 honk_hw_gate '{ 0x200 }'

Close admission BEFORE any honk stop, restart, reload, or policy change:

    /usr/bin/honk-hw-close

This closes the gate, flushes the fw4 flowtable, clears ONLY conntrack bit 0x200 for both IPv4 and IPv6, and verifies no such marks remain. It does not delete unmarked connections or reset other conntrack bits. conntrack-tools 1.4.8 source src/conntrack.c:2058-2065 implements masked update as `(old & ~mask) ^ value`; lines 2154-2190 show UPDATE has no old-mark equality filter. With value 0 and mask 0x200, unrelated bits are preserved. Exit 1 is ambiguous (print_stats:2893), so the helper checks the resulting marked list rather than assuming success. No background service or automatic reopening is supplied. If clearing/flush fails, the gate stays closed.

Connect this helper to honk's actual init stop/reload hooks before packaging. Runtime/applied confirmation is still required before reopening after restart or reload. Hot reload with uninterrupted acceleration is NOT supported by this handoff.

Static validation completed: pinned fw4 patch dry-run, helper shell syntax. Parent will check the nft syntax file on the live Linux host with nft -c; this file does not itself alter a firewall.

Runtime acceptance: exercise IPv4/IPv6 TCP and UDP separately from a real LAN client; verify CN direct ct mark=0x200, [HW_OFFLOAD] and increasing PPE/NSS Wi-Fi installed-flow counters; verify foreign/proxy tuples have no whitelist mark/hardware entry and honk outbound counters rise. Distinguish software [OFFLOAD] from [HW_OFFLOAD]. Test DNS under load; inspect no ambiguous DNS rule became native. Wired acceleration is PPE in this design; Wi-Fi endpoints use the NSS Wi-Fi backend. Counters for direct hardware traffic naturally stop traversing honk's per-packet hooks after admission.

Hardware fastpath may bypass TC after the first classified packets; this is intentional ONLY for immutable native-direct flows already admitted by honk. First-packet ordering, hardware classifier support, IPv6/NAT behavior, NSS Wi-Fi behavior and stale-flow withdrawal require real-device verification. Honk documents TC-bypassing hardware paths outside its own ownership boundary, so configuration plus a running daemon is not proof of compatibility.
