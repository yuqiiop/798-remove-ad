#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""慧生活798 (com.cloudora.android) 去更新提示补丁

在 apktool 解包目录上执行，做四件事：

  1. BaseAppUpdateActivity.g0()V                      -> return-void  （不再发版本检查请求）
  2. BaseAppUpdateActivity.h0(LatestVersionData;)V    -> return-void  （不再弹更新对话框）
  3. com.ilife.lib.common.util.t0.a(CharSequence)     入口注入关键词过滤
                                                       （拦掉服务端下发的「客户端需要更新」类 toast）
  4. apktool.yml versionCode/versionName              -> 31010 / 3.1.10（对齐线上最新版）

用法：

    apktool d -f 798.apk -o work
    python apply.py work
    apktool b work -o patched.apk
    java -jar uber-apk-signer-1.3.0.jar -a patched.apk -o signed/

注意：签名变了不能覆盖安装，目标机需先卸载旧包（数据会清空）。
"""

import io
import os
import re
import sys

T0_REL = os.path.join(
    "smali_classes5", "com", "ilife", "lib", "common", "util", "t0.smali"
)
UPD_REL = os.path.join(
    "smali_classes5", "com", "ilife", "lib", "common", "base", "BaseAppUpdateActivity.smali"
)

# 命中即丢弃的提示关键词族：服务端下发文案可能落在任意接口的 msg 上，
# 只堵版本接口不够，必须在通用 toast 出口兜底。
KEYWORDS = [
    "需要更新",
    "版本过低",
    "请更新客户端",
    "客户端需要",
    "请更新",
    "新版本",
    "升级到最新",
]

TOAST_SIG = ".method public final a(Ljava/lang/CharSequence;)V\n    .locals 4\n"

INJECT = TOAST_SIG + """
    invoke-static {p1}, Lcom/ilife/lib/common/util/t0;->x(Ljava/lang/CharSequence;)Z
    move-result v3

    if-eqz v3, :cond_tt_ok

    return-void

    :cond_tt_ok
"""


def build_helper(keywords):
    """生成静态判定方法 x(CharSequence)Z：命中关键词返回 true。"""
    out = [
        "# 注入：更新类提示过滤（apply.py）",
        ".method public static x(Ljava/lang/CharSequence;)Z",
        "    .locals 3",
        "",
        "    const/4 v0, 0x0",
        "",
        "    if-nez p0, :x_null",
        "",
        "    return v0",
        "",
        "    :x_null",
        "    invoke-interface {p0}, Ljava/lang/CharSequence;->toString()Ljava/lang/String;",
        "    move-result-object v1",
    ]
    for idx, kw in enumerate(keywords, start=1):
        nxt = "x%d" % idx
        out += [
            "",
            '    const-string v2, "%s"' % kw,
            "",
            "    invoke-virtual {v1, v2}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z",
            "    move-result v2",
            "",
            "    if-eqz v2, :%s" % nxt,
            "    const/4 v0, 0x1",
            "",
            "    return v0",
            "",
            "    :%s" % nxt,
        ]
    out += ["    return v0", ".end method", ""]
    return "\n".join(out)


def patch_toast_filter(root):
    path = os.path.join(root, T0_REL)
    src = io.open(path, encoding="utf-8", newline="").read()

    if "Lcom/ilife/lib/common/util/t0;->x(" in src:
        print("[skip] toast 过滤已存在")
        return

    crlf = "\r\n" in src
    norm = src.replace("\r\n", "\n")

    if TOAST_SIG not in norm:
        raise SystemExit("未找到 t0.a(CharSequence) 签名，包结构不匹配")

    norm = norm.replace(TOAST_SIG, INJECT, 1)
    norm = norm.rstrip("\n") + "\n" + build_helper(KEYWORDS) + "\n"

    if crlf:
        norm = norm.replace("\n", "\r\n")
    io.open(path, "w", encoding="utf-8", newline="").write(norm)
    print("[ok] toast 过滤已注入，关键词 %d 条" % len(KEYWORDS))


def stub_method(text, sig_line):
    """把整个方法体替换成 return-void，保留原 .locals 行。"""
    pat = re.compile("(" + re.escape(sig_line) + ".*?)^\\.end method", re.S | re.M)
    m = pat.search(text)
    if not m:
        raise SystemExit("未找到方法：" + sig_line)
    body = m.group(1)
    locals_line = re.search(r"\n(    \.locals \d+\n)", body.replace("\r\n", "\n"))
    keep = locals_line.group(1) if locals_line else "    .locals 2\n"
    new = sig_line + "\n" + keep + "\n    return-void\n.end method"
    return text[: m.start()] + new + text[m.end():]


def patch_update_activity(root):
    path = os.path.join(root, UPD_REL)
    src = io.open(path, encoding="utf-8", newline="").read()
    norm = src.replace("\r\n", "\n")

    for sig in (
        ".method public final h0(Lcom/ilife/lib/coremodel/data/bean/LatestVersionData;)V",
        ".method public final g0()V",
    ):
        norm = stub_method(norm, sig)
        print("[ok] 已 stub %s" % sig.split()[-1])

    if "\r\n" in src:
        norm = norm.replace("\n", "\r\n")
    io.open(path, "w", encoding="utf-8", newline="").write(norm)


def bump_version(root, code="31010", name="3.1.10"):
    path = os.path.join(root, "apktool.yml")
    s = io.open(path, encoding="utf-8", newline="").read()
    s = re.sub(r"versionCode: \d+", "versionCode: " + code, s)
    s = re.sub(r"versionName: [\w.\-]+", "versionName: " + name, s)
    io.open(path, "w", encoding="utf-8", newline="").write(s)
    print("[ok] 版本号 -> %s / %s" % (code, name))


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    root = sys.argv[1]
    if not os.path.isdir(root):
        raise SystemExit("目录不存在：" + root)
    patch_toast_filter(root)
    patch_update_activity(root)
    bump_version(root)
    print("完成。下一步：apktool b %s -o patched.apk" % root)


if __name__ == "__main__":
    main()
