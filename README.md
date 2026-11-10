# 798-remove-ad

慧生活798（`com.cloudora.android`）去广告 / 去更新提示改版。

## 版本

| 版本 | 说明 | 备注 |
|---|---|---|
| `v1.0.0` | 去广告、无壳改版（基座） | 使用中会弹「客户端需要更新」 |
| `v1.1.0` | 在 v1.0.0 基础上移除更新提示，版本号对齐线上 3.1.10 | 本仓库 `dist/` 内成品 |

## v1.1.0 改了什么

基座：`v1.0.0` 的 `798.apk`（7 个明文 dex，Application = `com.ilife.lib.common.app.App`，无加固、无签名校验）。

四处补丁，全部通过 `patch/apply.py` 在 apktool 解包目录上完成：

| # | 位置 | 改动 | 作用 |
|---|---|---|---|
| 1 | `BaseAppUpdateActivity.g0()V` | 方法体 → `return-void` | 不再请求版本检查接口 |
| 2 | `BaseAppUpdateActivity.h0(LatestVersionData;)V` | 方法体 → `return-void` | 不再弹更新对话框 |
| 3 | `com.ilife.lib.common.util.t0.a(CharSequence)` | 入口注入静态判定，命中关键词直接 return | 拦掉服务端下发的更新类 toast（通用出口兜底） |
| 4 | `apktool.yml` | `versionCode 31006 → 31010`、`versionName 3.1.6 → 3.1.10` | 避免服务端按版本号拦截 |

关键词族（第 3 条）：`需要更新` `版本过低` `请更新客户端` `客户端需要` `请更新` `新版本` `升级到最新`。

第 3 条是关键：更新文案由服务端下发，会从任意接口的 msg 走通用 toast 弹出，只堵版本接口不够。

## 构建

```bash
apktool d -f 798.apk -o work          # apktool 2.6+ / 3.x
python patch/apply.py work
apktool b work -o patched.apk
java -jar uber-apk-signer-1.3.0.jar -a patched.apk -o signed/
```

产物：`signed/patched-aligned-debugSigned.apk`（debug key，v1+v2+v3 签名）。

## 成品

`dist/798-noupdate-3.1.10-signed.apk`

```
size    52,022,460 B
sha256  ecdc28a0f0fd222a939158829a2064786531bbc641cd5272c1eca833bc4a8fea
```

## 安装

签名与官方不同，**必须卸载旧版再装**，本地数据会清空：

```bash
adb uninstall com.cloudora.android
adb install -r dist/798-noupdate-3.1.10-signed.apk
```

## 实测记录（2026-11-10，Android 真机）

- 安装 → 隐私弹窗 → 首页正常渲染，进程存活，crash buffer 为空。
- frida 反射调用 `t0.a("客户端需要更新")` → `Toast.show` **未触发**。
- 对照组 `t0.a("布洛妮娅可见测试")` → `Toast.show` **触发**。过滤只吃更新类文案，不误伤正常提示。

未验证项：服务端真实回包文案（测试时设备无网络，无法联调）。若联网后仍弹，把原文一句补进 `patch/apply.py` 的 `KEYWORDS` 重新构建即可。

## 风险

- debug key 签名，部分系统可能有安装/兼容提示；长期使用可换自己的证书。
- 版本号抬高到 31010（与官方 3.1.10 同），如需更高自行改 `apktool.yml`。
- 本仓库仅作个人设备维护使用。
