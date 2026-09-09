#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键发布：导出 → 翻译 → 建站。

    python scripts/publish.py                    # 全套
    python scripts/publish.py --no-translate     # 跳过翻译（不想调 API 时）
    python scripts/publish.py --vault D:\\xx\\知识库

跑完之后自己 git push 就上线了。
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(script: str, args: list[str]) -> int:
    print(f"\n{'─' * 52}\n▸ {script}\n{'─' * 52}")
    return subprocess.call([sys.executable, str(HERE / script), *args])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default="")
    ap.add_argument("--no-translate", action="store_true")
    a = ap.parse_args()

    ex = ["--vault", a.vault] if a.vault else []
    if run("export_public.py", ex) != 0:
        print("\n导出没通过，停在这里。")
        return 1
    if not a.no_translate:
        if run("translate.py", []) != 0:
            print("\n翻译有失败的，但继续建站——已有的英文版不受影响。")
    run("build_site.py", [])
    print(f"\n{'─' * 52}")
    print("完成。检查一遍 index.html，没问题就：")
    print('  git add -A && git commit -m "update" && git push')
    return 0


if __name__ == "__main__":
    sys.exit(main())
