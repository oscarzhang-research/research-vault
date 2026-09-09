#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自动翻译：中文原文改了，英文自己跟上。

    python scripts/translate.py            # 只翻改过的和没翻过的
    python scripts/translate.py --all      # 强制全部重翻
    python scripts/translate.py --only mu  # 只翻 slug 里含 mu 的
    python scripts/translate.py --dry      # 只报告哪些需要翻，不调 API

原理：给每篇中文正文算一个哈希存起来。下次跑的时候比对，
哈希没变就跳过——所以重复跑不花钱，只有你真的改了内容才会重新翻。

需要环境变量 ANTHROPIC_API_KEY。设置方法（PowerShell，只在当前窗口有效）：
    $env:ANTHROPIC_API_KEY="sk-ant-..."
永久设置：
    setx ANTHROPIC_API_KEY "sk-ant-..."     然后重开窗口

绝对不要把 key 写进这个文件或任何会被 git 提交的地方。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
TRANS_DIR = SITE / "translations"
MODEL = "claude-sonnet-5"
MAX_TOKENS = 32000


def content_hash(note: dict) -> str:
    """只哈希会影响翻译结果的部分——正文和标题。改元数据不触发重翻。"""
    payload = json.dumps({
        "title": note["title"],
        "sections": note["sections"],
    }, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def build_prompt(rules: str) -> str:
    return f"""你是一位金融研究翻译，把中文投资笔记翻成英文。

{rules}

---

## 输出格式

只输出 JSON，不要任何前后说明、不要 markdown 代码块围栏。格式：

{{
  "title_en": "英文标题",
  "sections": [
    ["English section heading", "<p>...</p><p>...</p>"],
    ["English section heading", "<ul class=\\"checks\\"><li class=\\"open\\"><span class=\\"mk\\">☐</span>...</li></ul>"]
  ]
}}

正文用 HTML 片段，只允许这些标签：
  <p> <strong> <em> <ol> <ul> <li> <code>
  勾选清单用 <ul class="checks">，每条 <li class="open"><span class="mk">☐</span>正文</li>
  已验证用 class="done" 配 ☑，已证伪用 class="false" 配 ☒

section 的数量、顺序必须和原文完全一致。
每个清单里的条目数量必须和原文完全一致，一条都不能多不能少。
"""


def note_to_source(note: dict) -> str:
    parts = [f"标题：{note['title']}"]
    if note.get("companies"):
        parts.append(f"主体：{'、'.join(note['companies'])}")
    if note.get("stance"):
        parts.append(f"立场：{note['stance']}")
    parts.append("")
    for h, b in note["sections"]:
        parts.append(f"## {h}")
        parts.append(b)
        parts.append("")
    return "\n".join(parts)


def call_api(client, system: str, source: str, tries: int = 3) -> dict | None:
    """用流式调用 —— 长文章一次要写一两万 token，非流式会被 SDK 拒绝。"""
    for i in range(tries):
        try:
            chunks = []
            with client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": source}],
            ) as stream:
                for t in stream.text_stream:
                    chunks.append(t)
            txt = "".join(chunks).strip()
            txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt)
            return json.loads(txt)
        except json.JSONDecodeError as e:
            print(f"    返回的不是合法 JSON（第 {i+1} 次）：{e}")
        except Exception as e:
            print(f"    调用失败（第 {i+1} 次）：{e}")
        if i < tries - 1:
            time.sleep(2 * (i + 1))
    return None


def check_parity(zh: dict, en: dict) -> list[str]:
    """中英对不上就报出来——段落数、清单条目数。"""
    issues = []
    if len(zh["sections"]) != len(en.get("sections", [])):
        issues.append(f"段落数 {len(zh['sections'])} vs {len(en.get('sections', []))}")
    zh_checks = sum(len(re.findall(r"^\s*[-*]\s*\[[ xX!]\]", b, re.M))
                    for _, b in zh["sections"])
    en_checks = sum(len(re.findall(r"<li class=", b)) for _, b in en.get("sections", []))
    if zh_checks != en_checks:
        issues.append(f"清单条目 {zh_checks} vs {en_checks}")
    return issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="强制全部重翻")
    ap.add_argument("--only", default="", help="只翻 slug 含这个字符串的")
    ap.add_argument("--dry", action="store_true", help="只报告，不调 API")
    a = ap.parse_args()

    sp = SITE / "site.json"
    if not sp.exists():
        print("先跑 python scripts/export_public.py")
        return 1
    notes = json.loads(sp.read_text(encoding="utf-8"))["notes"]
    TRANS_DIR.mkdir(exist_ok=True)

    todo = []
    for n in notes:
        if a.only and a.only.lower() not in n["slug"].lower():
            continue
        f = TRANS_DIR / f"{n['slug']}.json"
        h = content_hash(n)
        if a.all or not f.exists():
            todo.append((n, h, "新增" if not f.exists() else "强制重翻"))
            continue
        old = json.loads(f.read_text(encoding="utf-8"))
        if old.get("hash") != h:
            todo.append((n, h, "中文改过了"))

    if not todo:
        print("所有英文版都是最新的，没有需要翻译的。")
        return 0

    print(f"需要翻译 {len(todo)} 篇：")
    for n, _, why in todo:
        print(f"  · {n['slug']:34} {why}")

    if a.dry:
        print("\n--dry 模式，没有调用 API。")
        return 0

    key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        print("\n没找到 ANTHROPIC_API_KEY 环境变量。")
        print('设置：setx ANTHROPIC_API_KEY "sk-ant-api03-..."  然后重开窗口')
        return 1
    if not key.isascii() or not key.startswith("sk-ant-") or len(key) < 40:
        print(f"\nANTHROPIC_API_KEY 看起来不是一个真的 key：{key[:24]}…")
        print("它应该是 sk-ant-api03- 开头、九十多个字符的纯英文数字串。")
        print("去 console.anthropic.com → API Keys → Create Key 复制，然后：")
        print('  setx ANTHROPIC_API_KEY "复制的那串"')
        print("设完关掉窗口重开一个再跑。")
        return 1
    try:
        from anthropic import Anthropic
    except ImportError:
        print("\n先装 SDK：pip install anthropic")
        return 1

    rules = (SITE / "TRANSLATION.md").read_text(encoding="utf-8")
    system = build_prompt(rules)
    client = Anthropic(api_key=key)

    ok = fail = 0
    print()
    for n, h, _ in todo:
        print(f"翻译 {n['slug']} …", end=" ", flush=True)
        out = call_api(client, system, note_to_source(n))
        if not out:
            print("失败，跳过")
            fail += 1
            continue
        issues = check_parity(n, out)
        out["hash"] = h
        out["slug"] = n["slug"]
        (TRANS_DIR / f"{n['slug']}.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        if issues:
            print("完成，但对不齐：" + "；".join(issues))
        else:
            print("完成")
        ok += 1

    print(f"\n成功 {ok} 篇，失败 {fail} 篇。")
    print("接下来跑：python scripts/build_site.py")
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
