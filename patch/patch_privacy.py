#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""798 去隐私弹窗（apktool 解包目录上执行）

SplashActivity.y0() 的启动分支：
    if (n0.d()) initData();   // 已同意
    else        C0();         // 未同意 → new a4.t(...) → dlg_privacy_policy「温馨提示」

本补丁把 else 分支的 C0() 直接换成 initData()，并把 B0()（同意后的二次确认窗）整段 stub：
- 无论 n0.d() 返回什么，都不会创建弹窗；
- 两条分支都走 initData()，不会卡在闪屏。

配合 patch_ads.py 的 n0.d()=true，双保险。
"""

import io
import os
import re
import sys

SPLASH = os.path.join(
    "smali_classes5", "com", "ilife", "lib", "common", "view", "activity", "SplashActivity.smali"
)

C0_CALL = "invoke-virtual {p0}, Lcom/ilife/lib/common/view/activity/SplashActivity;->C0()V"
INIT_CALL = "invoke-virtual {p0}, Lcom/ilife/lib/common/view/activity/SplashActivity;->initData()V"


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    root = sys.argv[1]
    path = os.path.join(root, SPLASH)
    src = io.open(path, encoding="utf-8", newline="").read()
    crlf = "\r\n" in src
    norm = src.replace("\r\n", "\n")

    if norm.count(C0_CALL) == 1:
        norm = norm.replace(C0_CALL, INIT_CALL)
        print("[ok] y0() else 分支：C0() -> initData()")
    elif norm.count(C0_CALL) == 0:
        print("[skip] y0() 已改过")
    else:
        raise SystemExit("C0() 调用点数量异常：%d" % norm.count(C0_CALL))

    for name in ("B0", "C0"):
        m = re.search(r"\.method public final " + name + r"\(\)V.*?\.end method", norm, re.S)
        if not m:
            raise SystemExit("未找到 " + name + "()")
        body = m.group(0)
        loc = re.search(r"\n(    \.locals \d+\n)", body)
        stub = (
            ".method public final " + name + "()V\n"
            + (loc.group(1) if loc else "    .locals 2\n")
            + "\n    return-void\n.end method"
        )
        norm = norm[: m.start()] + stub + norm[m.end():]
        print("[ok] %s() -> return-void" % name)

    if crlf:
        norm = norm.replace("\n", "\r\n")
    io.open(path, "w", encoding="utf-8", newline="").write(norm)
    print("完成。apktool b 重打包后签名安装。")


if __name__ == "__main__":
    main()
