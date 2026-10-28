# Kwrt AX3600 · BTF 内核 + 内置 honk

目标：编一个 **内核带 BTF**（`/sys/kernel/btf/vmlinux` 存在）的 Kwrt 固件，内置 honk 与 LuCI 面板，且 **honk 默认不启动**。

## 为什么必须自己编

现在这台路由的内核没开 `CONFIG_DEBUG_INFO_BTF`，`vmlinux-btf` 只是外挂 BTF，只能给 CO-RE 用，不能生成 fentry trampoline。所以 honk 的 UDP trace 挂不上：

```
BPF_PROG_LOAD ... Invalid argument (os error 22)  on __skb_recv_udp
```

这个只能靠重编内核解决，装包无解。

## 目录

```
.github/workflows/build-kwrt-ax3600-btf.yml   构建流水线
configs/ax3600-btf.config                     目标设备 + BTF + honk 的 config seed
files/99-honk-safe                            首启把 honk 关掉
```

## 用法

1. 在 GitHub 新建一个空仓库（public/private 都行），把本目录三个位置原样推上去：
   ```bash
   cd kwrt-btf-build
   git init -b main
   git add .
   git commit -m "build kwrt ax3600 with BTF + honk"
   git remote add origin git@github.com:<你的账号>/<仓库名>.git
   git push -u origin main
   ```
2. 仓库页面 → **Actions** → `Build Kwrt AX3600 (BTF + honk)` → **Run workflow**。
3. 约 2–4 小时后，在 run 页面底部下载 artifact `kwrt-ax3600-btf-honk`，里面是 `*sysupgrade.bin` 和 `sha256sums.txt`。
4. 流水线里已经校验过 `vmlinux` 的 `.BTF` 段，没有就直接失败，所以能下载到就说明 BTF 编进去了。

## 刷机（风险自负）

```sh
# 上传到路由 /tmp 后
sha256sum /tmp/*sysupgrade.bin     # 和 sha256sums.txt 对上
sysupgrade -n /tmp/*sysupgrade.bin  # -n 不保留配置，干净
```

> `-n` 会清空现在的配置（honk 订阅、网络设置都要重配）。想保留就去掉 `-n`，但跨固件保留配置有概率起不来，第一次建议 `-n`。

## 已知风险

- **内核体积**：AX3600 的 `KERNEL_SIZE` 是 36608k（约 36 MB），BTF 会增大 vmlinux，但压缩后一般仍在预算内；如果构建报 kernel too big，把 `CONFIG_KERNEL_DEBUG_INFO_REDUCED` 之外的调试项再收一收。
- **源码差异**：这里用的是 `kiddin9/Kwrt` 的 `master`，和你现在 25.12.5 的构建不一定逐字节一致；honk 来自它自带的 kiddin9 feed，版本可能比你现在装的 beta3-r23 新或旧。
- **CI 时长**：GitHub 单 job 上限 6 小时，这里设了 350 分钟；首次全量编译偏慢，失败多半是超时或某个 feed 拉取失败，重跑一次通常能过。
- **没实测过**：这套 workflow 我没法在本地验证（这台 Mac 是 arm64、无 Docker），第一次跑可能要修 1–2 处小问题（依赖包名、feed 路径），报错把日志贴我。

## 刷完后的收尾

1. 确认 BTF：`ls -l /sys/kernel/btf/vmlinux` 应该存在（这是这次编译的唯一目的）。
2. 确认 honk 装上但没跑：`/etc/init.d/honk status` → `active with no instances`，`uci get honk.config.enabled` → `0`。
3. 配订阅：`/etc/honk/config.d/node.dae` 里用
   ```
   subscription { sub: { url: 'https://…'  route: direct } }
   ```
   `dns.dae` 的 `local` 上游写 `223.5.5.5:53`，并打开 `ipversion_prefer: 4`。
4. 再启用 honk，观察 `honk.log` 里那条 `UDP receive trace unavailable` 是否消失。
