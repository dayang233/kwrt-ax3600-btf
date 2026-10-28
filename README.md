# 本机 AX3600：PPE + NSS Wi-Fi + BTF + honk

工作流为 `.github/workflows/build-ax3600-ppe.yml`，由 `honk-ppe-singleubi` 分支推送或手动触发。只需将 `.github/`、`configs/`、`scripts/`、`files/`、`patches/` 和本 README 推到构建仓库；`source/`、`nss-packages/`、`validation/` 是本地核验材料，不应提交。

固定来源：

- JuliusBairaktaris/openwrt-ppe-nss `74c3517f72f8a2c8bdb97a1115fe1426ae607267`，真实 Linux 6.18。
- JuliusBairaktaris/nss-packages 的 ppe-nss `1f60d7e9409930bbd298eae1831c5b76d21eb1d2`，只提供 NSS 固件。
- kiddin9/op-packages `b21929fceb463c06b4cf703406c971be10bcbd45`，honk 预编译核心及 LuCI 包。
- fw4 `bac1d656e09b48e542f860844fe91cbba82abae2`，选择性 flowtable 模板补丁严格锁此版本。

常规 feeds 已逐一锁定到 configs/feed-lock.json 中的 commit；PPE 主源码、NSS 固件 feed、Honk/Doona 包 feed 和 fw4 均固定。CI 保留 feeds.buildinfo、OpenWrt配置、真实内核配置和日志。宿主 apt 工具链版本仍依赖 Ubuntu 22.04 runner，源码可复建不等于已证明所有产物逐字节一致。

## 设备兼容修正

这台机器已修改为 rootfs 从 0x00a00000 开始、长度 0x0f000000 的 240MiB 单 UBI；卷0=kernel、卷1=rootfs、卷2=rootfs_data。专用 dtsi 精确镜像实机14分区，保留 ART/NVMEM 及 MAC/校准引用，root=/dev/ubiblock0_1。升级脚本只处理 AX3600 单 UBI，不改引导程序flags，也不影响同源码的其他设备。补丁严格匹配已核验源码内容，漂移会失败。

源码这次将设备 DTS 放在 target/linux/qualcommax/dts，使用 swport/switchdev 网络架构；不能套旧6.12固件的二进制设备树，也不能整包恢复旧驱动配置。

## 硬件加速与 honk 的边界

该方案有线路由由内核 QCOM_80211AX_PPE + QCOM_EDMA 处理，fw4硬件flowtable是PPE接入点；SoC无线数据面由内置 kmod-nss-wifi-drv + ATH11K_NSS_WIFI 和 NSS12.5固件处理。没有 qca-nss-ecm/qca-nss-drv 旧厂商栈。

首启 flow_offloading=1、flow_offloading_hw=1、nss-wifi.general.offload=1，honk保持关闭。fw4模板已将默认全量flowadd替换为仅 honk 已实际分类的 native-direct mark 0x200 连接入表。未分类流不会获得该连接标记，因此首启即使硬件功能开启，也不会擅自把待代理流加速。

正式 honk 配置需加入：

```dae
routing {
    dip(geoip: cn) && !dport(53) -> direct(mark: 0x200, must)
    # 其他国内规则如果要获得加速，也必须明确作出相同 native-direct 决策。
    # 最终国外流转到代理组；不能把所有 direct fallback 都自动打相同mark。
}
```

global.so_mark 使用默认0x100；不得设为0x200。模板同时核对 skb mark 的 CLASSIFIED 高位与用户低30位，只允许 br-lan→wan 的TCP/UDP非53端口显式直连决策写入 ctmark；之后只有标记连接才能在LAN/WAN双向加入flowtable。标记规则是硬件准入契约，不能用未经核对的其他应用复用0x200。该模板尚未以实际运行的 honk/NSS/PPE 完成端到端验证。

## 静态检查与验收边界

布局脚本已对固定 PPE 源码精确应用，平台 shell 语法通过，ART/NVMEM保留；fw4补丁对固定版本可精确应用。工作流检查配置种子与真实Linux .config、vmlinux.BTF、编译成品DTB14分区、NSS驱动/固件及honk包选择，随后生成factory.ubi与sysupgrade.bin及SHA256。

编译成功仍不代表可启动。必须在本机验证：启动/内存/分区/无线/管理通道、honk BPF挂载、客户端TCP/UDP/DNS、国内直连PPE/NSS命中计数和国外代理实际出口。保留可回刷成功包与不死U-Boot恢复入口。当前工程未推送、未启动CI、未刷机。

## 1 GiB 扩容与内存专项核验（2026-10-29）

当前运行系统的 `live.dtb` 声明 RAM 为 `[0x40000000, 0x80000000)`，长度 `0x40000000` 即1GiB；本会话观测 MemTotal 为928184KiB（约906.43MiB）。成功包的静态DTB没有 `/memory` 节点，启动后的DTB才有该节点，证明当前启动链会传入实际内存范围。`ipq8074-512m.dtsi` 文件名不能当作“只支持512MiB”的证据：固定PPE源码中该文件只是覆盖TZAPP/Q6/ETR/M3保留区，没有声明RAM总容量。

成功包和当前运行DTB的9个保留区完全相同，合计84MiB：

| 区域 | 起点 | 长度 | 结束地址（不含） |
| --- | --- | --- | --- |
| NSS | 0x40000000 | 16MiB | 0x41000000 |
| TZAPP | 0x4a400000 | 1MiB | 0x4a500000 |
| bootloader | 0x4a600000 | 4MiB | 0x4aa00000 |
| SBL | 0x4aa00000 | 1MiB | 0x4ab00000 |
| SMEM | 0x4ab00000 | 1MiB | 0x4ac00000 |
| 其他保留区 | 0x4ac00000 | 4MiB | 0x4b000000 |
| Wi-Fi/Q6 | 0x4b000000 | 55MiB | 0x4e700000 |
| Q6 ETR | 0x4e700000 | 1MiB | 0x4e800000 |
| M3 dump | 0x4e800000 | 1MiB | 0x4e900000 |

这些区域互不重叠、均有no-map、均处于1GiB RAM范围内。成功包的ARM64 Image按头部image_size占用0x41000000至0x41e30000，不碰任何上述保留区；新内核更大，必须重新使用其解压Image核验，不能继承旧检查结果。

### PPE-NSS 源码说明的内存契约

- 固定源码的 `0931-arm64-dts-ipq8074-rename-nss-region.patch` 将NSS保留节点改为带 `nss_region` 标签的 `memory@40000000`，仍是16MiB。`ipq8074-nss.dtsi` 引用该节点，core0加载0x40000000，core1加载0x40800000，均在原保留区；扩容为1GiB不要求把该保留区扩大。
- `nss_core.c` 的 `nss_region_get()` 从DT保留区读取base/size，固件拷贝前检查镜像是否装得下，并设置32位DMA掩码。本机RAM顶端为0x80000000，小于4GiB，未越过该DMA地址限制。
- **16MiB只是固件启动/heap的保留区，不是NSS全部内存需求。** `nss_meminfo.c` 根据运行固件内置meminfo表为SDRAM请求动态分配DMA一致性内存，为IMEM请求分配片上存储；其他Wi-Fi rings、peer、TX descriptors及pbuf也消耗普通RAM。固件版本、无线台数/连接数和参数决定实际用量，必须由运行记录和负载验证。
- 默认 `pbuf_bytes=3100000`、`payloads=8192`、`radio_bufs=8192`；这些分别是额外包描述符预算/数量参数，不是“1GiB内存档位”。
- **不能把 `mem_profile=1` 解读为1GiB。** `nss_wifili.c` 的 `nss_wifili_mem_profile` 默认0；源文件2505附近明确指出这是profile而不是容量，协议header没有给出常量，不能靠猜数值确定配置。它会原样传入固件 `soc_mem_profile`。本工程没有擅自设置mem_profile，也没有放大各pool；这不代表默认0已经在这台扩容机上验收。

### 核验脚本及仍需实机确认

新增 `scripts/verify-ax3600-memory.py`，与成功包/实机观测的基线作严格比较：9个保留区、no-map、无重叠、RAM容量（runtime模式）、NSS加载地址（若候选描述了NSS core）以及解压ARM64 Image的驻留空间。额外/缺失保留区会拒绝，要求先人工核对原因。示例：

```sh
python3 scripts/verify-ax3600-memory.py candidate.dtb --kernel-image Image
python3 scripts/verify-ax3600-memory.py captured-runtime.dtb --runtime --kernel-image Image
```

已用本会话现有成功包DTB、live.dtb和成功包解压Image验证脚本通过。候选DTB通常没有RAM节点，脚本会明确输出“需要runtime fixup验证”，不会把静态通过说成1GiB启动已验证。本轮未改工作流或配置默认值，是否将该脚本接入CI由主任务整合。

刷前必须对**实际编译的**DTB和Image运行脚本；若新增其他合法保留区，应先审查并更新基线，不能直接绕过断言。刷后仍需确认：U-Boot传入1GiB范围、MemTotal符合新内核预算、内核无reserved-memory/DMA分配错误、NSS meminfo全部满足、实际mem_profile/pbuf/payload/radio参数、无线收发rings和NSS启动持续稳定、压力下无OOM/分配失败/重启。300Mbps稳定性优先时先保留保守参数和300M实际负载，不应为了“用满1GiB”扩大pool或套用其他设备profile。

## 当前双配置构建

GitHub Actions 对同一套锁定源码构建 stable 与 accelerated 两个配置，产物和日志分别保存。stable 是关闭 Flowtable/PPE 路由卸载与 NSS Wi-Fi 数据路径的 CPU/eBPF 基线，仍编译并保留 NSS/固件支持；accelerated 打开这些硬件功能，但硬件流量准入 gate 默认关闭，必须通过实机分流验收后显式开启。stable 是配置名称，不代表已经完成稳定性验收。两者初次启动 Honk 关闭，避免未迁移订阅/DNS时接管网络；Doona 离线资产及LAN管理配置已预置，服务自启动在实机配置验证后启用。

Doona 默认 config_write=false，代理组选节点仍可使用。此 Honk 版本的 Native API reload 并不受 config_write 限制；因此不能宣称 Doona 所有写操作都已原子接入硬件 gate。修改磁盘分流配置前必须先关闭 gate，完成热更新与模式切换验收前不自动重新开启。此限制不影响先构建安全基线，阻止把未验证的实验配置当成生产共存结果。
