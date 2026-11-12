# 798-remove-ad

慧生活798（`com.cloudora.android`）去广告 / 去更新提示改版。

## 版本

| 版本 | 说明 | 备注 |
|---|---|---|
| `v1.0.0` | 去广告、无壳改版（基座） | 使用中会弹「客户端需要更新」 |
| `v1.1.0` | 在 v1.0.0 基础上移除更新提示，版本号对齐线上 3.1.10 | 本仓库 `dist/` |
| `v1.2.0` | 再切除广告总闸（穿山甲/Gromore 初始化 + 广告位判定） | 副作用：每次启动弹隐私窗 |
| `v1.3.0` | `n0.d()` 改回 true | 仅依赖标志，仍可能被旧缓存/旧包干扰 |
| `v1.4.0` | 直接把 `C0()`/`B0()` 弹窗构造函数 stub，`y0()` 两条分支都走 `initData()` | 推荐使用 |

## v1.4.0 改了什么（彻底去弹窗）

v1.3.0 只改标志（`n0.d()=true`），实测仍会弹——说明仅靠上游判定不够稳。v1.4.0 直接掐源头：

| # | 位置 | 改动 |
|---|---|---|
| 1 | `SplashActivity.y0()` else 分支 | `C0()` → `initData()`（两条分支都直达初始化） |
| 2 | `SplashActivity.C0()` | `return-void`（`dlg_privacy_policy`「温馨提示」构造函数空壳） |
| 3 | `SplashActivity.B0()` | `return-void`（同意后的二次确认窗同样空壳） |

全包只有这两个方法会 `new a4.t` / `new a4.r`（两个弹窗类），封掉后不存在任何能创建该弹窗的代码路径；同时 `y0()` 两分支都调 `initData()`，不会卡闪屏。

`n0.d()` 仍返回 true（v1.3.0 的改动保留），作为第一道闸。

## v1.3.0 改了什么（去隐私弹窗）

v1.2.0 把 `n0.d()` 当成「云端广告开关」强制成 false，实际它是**隐私政策已同意标志**：

```
SplashActivity.onCreate:
    if (n0.d()) { initData(); }        // 已同意 → 直接进主界面
    else        { C0(); }              // 未同意 → 弹 dlg_privacy_policy「温馨提示」
```

所以强制 false 等于「每次都未同意」，每次启动都弹窗。

v1.3.0 把 `n0.d()` 改为 `return true`：

- 启动直接走 `initData()`，`C0()`（隐私弹窗）与 `B0()`（同意后的二次确认弹窗）都不会被调用；
- 广告不依赖这条路径——`initTTAdSdk` / `startTTAdSdk` / `preloadSplashAd` 仍是 `return-void`，`isShowAd` 仍是 `false`，穿山甲/Gromore 依旧不初始化。

| # | 位置 | v1.2.0 | v1.3.0 |
|---|---|---|---|
| 5 | `n0.d()` | `return false`（弹窗复发） | `return true`（直达主界面） |

## v1.2.0 改了什么（切广告）

现象：基座「去广告」只在本地生效，服务端下发 `adSwitch` 后广告回归。

证据链：

1. 应用代码（`com.ilife` / `com.cloudora`）**不直接引用**任何第三方广告 SDK（`com.qq.e` / `com.kwad` / `com.sigmob` / `com.beizi` / `com.wangmai` / `com.yfanads` … 全部 0 命中），全部广告经 `com.ilife.lib.common.ad.*` → 穿山甲 `TTAdSdk`（Gromore 聚合）出口。
2. 云端开关路径：`SplashActivity` 拉 `CommonDS.adSwitch`（`CommonDS$x1` / `adSwitchReq`）→ 写入 `n0.E(Z)` → 本地 `n0.d()`；`App.w()` 读 `n0.d()` 决定是否 `startTTAdSdk`，`SplashActivity` 读 `n0.d()` 决定是否展示开屏。
3. `App.w()` 里 `TTAdHelper.initTTAdSdk(context, "5655586")` 是**全包唯一**的 `TTAdSdk.init` 调用点。
4. 广告位统一下发到 `TTAdManager.isShowAd(List, int)`（20+ 调用点：首页 banner、设备页、支付页、网课页…）。

五刀（`patch/patch_ads.py`）：

| # | 位置 | 改动 |
|---|---|---|
| 1 | `TTAdHelper.initTTAdSdk(Context,String)` | `return-void`，SDK 永不 init |
| 2 | `TTAdHelper.startTTAdSdk(Function0,Function0)` | `return-void` |
| 3 | `TTAdHelper.preloadSplashAd(Activity)` | `return-void`，不预加载开屏 |
| 4 | `TTAdManager.isShowAd(List,int)` | `return false`，所有广告位判定关死 |
| 5 | `n0.d()` | `return false`，云端开关本地缓存恒关 |

关键点：**云端只能改配置，改不了代码**。第 1 刀让 `TTAdSdk.init` 永不执行，服务端无论下发什么 adSwitch、adSlot、水位线，都没有可渲染的 SDK；第 4/5 刀再断掉判定与开屏路径。

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

`dist/798-v1.4.0-nodialog-signed.apk`（推荐，v1.4.0：无广告 + 无更新提示 + 无隐私弹窗）

```
size    52,018,364 B
sha256  5331b4e8da54c3fa8af342ab9f9e5ec246f5fc935c3a2f878989c2a1a74bc51c
```

`dist/798-v1.3.0-noad-noupdate-signed.apk`（v1.3.0，只改标志，实测仍弹窗，弃用）

```
size    52,018,364 B
sha256  b3fd5f54e650bf96158ca46a773a62d2240367a2da72f0f240217aed76e36132
```

`dist/798-noad-noupdate-3.1.10-signed.apk`（v1.2.0，广告已切但每次启动弹隐私窗，建议弃用）

```
size    52,018,364 B
sha256  c64ae744591c3dd0c90685bd705175a1f2a71d1818c8def42d48909671f74b5a
```

`dist/798-noupdate-3.1.10-signed.apk`（v1.1.0，仅去更新提示）

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
