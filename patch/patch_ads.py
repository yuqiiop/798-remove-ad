#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""798 广告总闸切除（apktool 解包目录上执行）

依据：应用代码（com.ilife / com.cloudora）不直接引用任何第三方广告 SDK，
全部广告经 com.ilife.lib.common.ad.* → 穿山甲 TTAdSdk（Gromore 聚合）出口。

四刀：
 1. TTAdHelper.initTTAdSdk(Context,String)      -> return-void   （SDK 永不 init）
 2. TTAdHelper.startTTAdSdk(Function0,Function0)-> return-void   （SDK 永不 start）
 3. TTAdHelper.preloadSplashAd(Activity)        -> return-void   （不预加载开屏）
 4. TTAdManager.isShowAd(List,int)              -> return false  （所有广告位判定关死）
 5. n0.d()                                      -> return true   （隐私已同意态；跳过温馨提示弹窗）

注意：n0.d() 是「隐私政策已同意」标志（SplashActivity: if (n0.d()) initData(); else 弹 dlg_privacy_policy）。
强制 false 会让 App 每次启动都弹窗，故必须置 true；广告不走这条路径，由 1–4 刀封死。

用法：python patch_ads.py <apktool 解包目录>
"""

import io
import os
import re
import sys

HELPER = os.path.join(
    "smali_classes5", "com", "ilife", "lib", "common", "ad", "TTAdHelper.smali"
)
MANAGER = os.path.join(
    "smali_classes5", "com", "ilife", "lib", "common", "ad", "TTAdManager.smali"
)
CONF = os.path.join("smali_classes5", "com", "ilife", "lib", "common", "util", "n0.smali")


def _stub(text, sig_line, body_lines):
    pat = re.compile("(" + re.escape(sig_line) + ".*?)^\\.end method", re.S | re.M)
    m = pat.search(text)
    if not m:
        raise SystemExit("未找到方法：" + sig_line)
    body = m.group(1)
    loc = re.search(r"\n(    \.locals \d+\n)", body.replace("\r\n", "\n"))
    keep = loc.group(1) if loc else "    .locals 1\n"
    new = sig_line + "\n" + keep + "\n" + body_lines + "\n.end method"
    print("[ok] stub %s" % sig_line.split("(")[0].split()[-1])
    return text[: m.start()] + new + text[m.end():]


def patch(path, edits):
    src = io.open(path, encoding="utf-8", newline="").read()
    crlf = "\r\n" in src
    norm = src.replace("\r\n", "\n")
    for sig, body in edits:
        norm = _stub(norm, sig, body)
    if crlf:
        norm = norm.replace("\n", "\r\n")
    io.open(path, "w", encoding="utf-8", newline="").write(norm)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    root = sys.argv[1]
    if not os.path.isdir(root):
        raise SystemExit("目录不存在：" + root)

    patch(
        os.path.join(root, HELPER),
        [
            (".method public final initTTAdSdk(Landroid/content/Context;Ljava/lang/String;)V",
             "    return-void"),
            (".method public final startTTAdSdk(Lkotlin/jvm/functions/Function0;Lkotlin/jvm/functions/Function0;)V",
             "    return-void"),
            (".method public final preloadSplashAd(Landroid/app/Activity;)V",
             "    return-void"),
        ],
    )

    patch(
        os.path.join(root, MANAGER),
        [
            (".method public final isShowAd(Ljava/util/List;I)Z",
             "    const/4 v0, 0x0\n\n    return v0"),
        ],
    )

    patch(
        os.path.join(root, CONF),
        [
            (".method public final d()Z",
             "    const/4 v0, 0x1\n\n    return v0"),
        ],
    )
    print("完成。apktool b 重打包后签名安装。")


if __name__ == "__main__":
    main()
