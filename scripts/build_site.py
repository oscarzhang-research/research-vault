#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读 site.json，生成静态页面。

    python scripts/build_site.py

生成：
    index.html          首页
    method.html         方法页
    coverage.html       覆盖清单
    judgments/*.html    每篇笔记一页（中文）

英文版：Claude Code 按 TRANSLATION.md 生成 *.en.html，本脚本不覆盖已存在的 .en.html。
"""
from __future__ import annotations

import json
import re
import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent

SITE_TITLE = "Baichuan (Oscar) Zhang"
SITE_SUB = "Semiconductors · Memory · AI Infrastructure"
EMAIL = "baichuanzhang273@gmail.com"
GITHUB = "https://github.com/oscarzhang-research"

STANCE_CLS = {"Long": "pos", "Short": "neg", "Neutral": "mid", "Watch": "mid"}


def money(v: str, ccy: str = "$") -> str:
    """1730000 → ₩1,730,000"""
    v = str(v).strip()
    if not v:
        return ""
    try:
        f = float(v.replace(",", ""))
        return f"{ccy}{f:,.0f}" if f >= 100 else f"{ccy}{f:,.2f}".rstrip("0").rstrip(".")
    except ValueError:
        return f"{ccy}{v}"


def inline(s: str) -> str:
    s = escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return s


def md_block(md: str) -> str:
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    out, in_ul = [], False
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            if in_ul:
                out.append("</ul>")
                in_ul = False
            continue
        m = re.match(r"^\s*[-*]\s*\[([ xX!])\]\s*(.+)$", line)
        if m:
            if not in_ul:
                out.append('<ul class="checks">')
                in_ul = True
            st = m[1].lower().strip()
            cls = {"": "open", "x": "done", "!": "false"}.get(st, "open")
            mk = {"open": "☐", "done": "☑", "false": "☒"}[cls]
            out.append(f'<li class="{cls}"><span class="mk">{mk}</span>{inline(m[2])}</li>')
            continue
        m = re.match(r"^\s*(?:[-*]|\d+[.．、])\s+(.+)$", line)
        if m:
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline(m[1])}</li>")
            continue
        if in_ul:
            out.append("</ul>")
            in_ul = False
        out.append(f"<p>{inline(line)}</p>")
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


def shell(title: str, body: str, depth: int = 0, lang_href: str = "",
          lang_label: str = "中") -> str:
    up = "../" * depth
    lang = (f'<a class="lang" href="{lang_href}">{lang_label}</a>' if lang_href else "")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
<link rel="stylesheet" href="{up}assets/style.css"></head>
<body><div class="wrap">
<header class="top">
  <a class="home" href="{up}index.html">{SITE_TITLE}</a>
  <nav><a href="{up}coverage.html">Coverage</a><a href="{up}method.html">Method</a>
  <a href="{GITHUB}">GitHub</a>{lang}</nav>
</header>
{body}
<footer><p>{EMAIL} · <a href="{GITHUB}">GitHub</a></p>
<p class="dim">Nothing here is investment advice. Primary research written in Chinese.</p>
</footer></div></body></html>"""


def note_page(n: dict, en: dict | None = None) -> str:
    """en 为 None 时渲染中文页；给了 en 就用里面的英文内容渲染英文页。"""
    ccy = n.get("ccy") or "$"
    facts = []
    for lbl, key in (("Price at writing", "price"), ("Target", "target"),
                     ("Threshold", "threshold"), ("Window", "horizon"),
                     ("Conviction", "conviction")):
        v = str(n.get(key, "")).strip()
        if not v:
            continue
        if key == "threshold":
            v = f"±{v}%"
        elif key == "conviction":
            v = f"{v} / 5"
        elif key == "horizon":
            v = v.replace("m", " months")
        else:
            v = money(v, ccy)
        facts.append(f'<div><b>{escape(v)}</b><span>{lbl}</span></div>')
    facts_html = f'<div class="facts">{"".join(facts)}</div>' if facts else ""

    if en:
        secs = "".join(
            f'<section class="sec"><h2>{escape(t)}</h2>{b}</section>'
            for t, b in en.get("sections", []))
    else:
        secs = "".join(
            f'<section class="sec"><h2>{escape(t)}</h2>{md_block(b)}</section>'
            for t, b in n["sections"])

    stance = n.get("stance_en") or ""
    pill = (f'<span class="pill {STANCE_CLS.get(stance,"mid")}">{escape(stance)}</span>'
            if stance else "")
    subj = n.get("subject_en") or "、".join(n["companies"]) or n["title"]
    tick = f' <span class="tick">{escape(", ".join(n["tickers"]))}</span>' if n["tickers"] else ""

    ten = (en or {}).get("title_en") or n.get("title_en") or ""
    sub_t = f'<div class="subt">{escape(ten)}</div>' if ten and ten != subj else ""
    banner = (f"Written {escape(n['date'])} and published unedited. "
              "Translated from the Chinese original — see the 中 link above."
              if en else
              f"Written {escape(n['date'])}. Published unedited — this is the Chinese original.")
    body = f"""<article class="note">
<div class="eyebrow">{escape(n['type_en'])} · {escape(n['date'])}</div>
<h1>{escape(subj)}{tick} {pill}</h1>{sub_t}
<div class="banner">{banner}</div>
{facts_html}
{secs}
</article>"""
    if en:
        return shell(f"{subj} — {SITE_TITLE}", body, depth=1,
                     lang_href=f"{n['slug']}.html", lang_label="中")
    tf = SITE / "translations" / f"{n['slug']}.json"
    href = f"{n['slug']}.en.html" if tf.exists() else ""
    return shell(f"{subj} — {SITE_TITLE}", body, depth=1,
                 lang_href=href, lang_label="EN")


def index_page(d: dict) -> str:
    s = d["stats"]
    notes = d["notes"]
    cands = [n for n in notes if n["type"] == "投资"]
    picks = sorted(cands, key=lambda x: -x.get("weight", 0))[:1]

    def row(n: dict, show_stance: bool = True) -> str:
        subj = n.get("title_en") or n.get("subject_en") \
               or "、".join(n["companies"]) or n["title"]
        stance = n.get("stance_en") or "—"
        cls = STANCE_CLS.get(stance, "mid")
        st = f'<td class="{cls}">{escape(stance)}</td>' if show_stance else \
             f'<td class="dim">{escape(n["type_en"])}</td>'
        opens = len(n["checks"]["open"])
        tail = f'{opens} open' if opens else "—"
        return (f'<tr><td><a href="judgments/{n["slug"]}.html">{escape(subj)}</a></td>'
                f'{st}<td class="mono dim">{escape(n["date"])}</td>'
                f'<td class="mono dim">{tail}</td></tr>')

    judg = [n for n in notes if n["type"] in ("投资", "宏观")]
    other = [n for n in notes if n["type"] not in ("投资", "宏观")]

    lead = picks[0] if picks else None
    lead_html = ""
    if lead:
        subj = lead.get("subject_en") or "、".join(lead["companies"]) or lead["title"]
        lccy = lead.get("ccy") or "$"
        lead_html = f"""<div class="startrow">
<div class="k">→ <a href="judgments/{lead['slug']}.html">{escape(subj)} — what one complete judgment looks like</a></div>
<div class="d">Written {escape(lead['date'])} at {escape(money(lead['price'], lccy))}. {escape(lead.get('stance_en',''))},
target {escape(money(lead['target'], lccy))}, {escape(lead['threshold'])}% threshold,
{escape(lead['horizon'].replace('m',' month'))} window.
{len(lead['checks']['open'])} tracking signals. Unedited.</div></div>"""

    other_sec = ""
    if other:
        other_sec = f"""<div class="eyebrow mt">REVIEWS, READING &amp; NOTES</div>
<p class="dim">Not scored — these carry no price or deadline. The post-mortem is here.</p>
<table class="tbl"><tr><th>Title</th><th>Kind</th><th>Written</th><th>Items</th></tr>
{''.join(row(n, show_stance=False) for n in other)}</table>"""

    body = f"""<div class="hero">
<h1>{SITE_TITLE}</h1><div class="sub">{SITE_SUB}</div>
</div>
<p class="lede">I research memory semiconductors. Every judgment I make is logged with the price
I wrote it at, the threshold that decides right or wrong, a resolution window, and the conditions
that would prove me wrong. When the window closes, a script scores it.
<strong>I do not edit what I wrote before.</strong></p>
<p class="dim">This site is that record — plus the models and the machinery behind it.
Everything I have written is on this page.</p>

<div class="eyebrow mt">START HERE</div>
{lead_html}
<div class="startrow"><div class="k">→ <a href="method.html">Method — how the system works, and what it can't tell you yet</a></div>
<div class="d">The scoring rules, the three-state assumption tracker, and an honest note on sample size.</div></div>
<div class="startrow"><div class="k">→ <a href="coverage.html">Coverage — every name and theme on file</a></div>
<div class="d">{s['companies']} tickers under active judgment, {s['notes']} notes, {s['open']} open assumptions.</div></div>

<div class="eyebrow mt">JUDGMENTS · SCORED</div>
<p class="dim">Each carries a price at writing, a threshold, and a deadline. A script settles them.</p>
<table class="tbl"><tr><th>Name</th><th>Stance</th><th>Written</th><th>Assumptions</th></tr>
{''.join(row(n) for n in judg)}</table>
{other_sec}
<p class="dim mt">{s['notes']} pieces in total. Last updated {s['updated']}.</p>"""
    return shell(SITE_TITLE, body)


def method_page(d: dict) -> str:
    s = d["stats"]
    body = f"""<h1>Method</h1>
<p class="lede">How the record works, what it can prove today, and what it cannot.</p>

<div class="eyebrow mt">THE RULE THAT MATTERS</div>
<p>When I open a thesis I have to commit four numbers before I am allowed to save the file:
the price at that moment, the percentage move that decides right or wrong, how long the window
runs, and my conviction. Then I write the conditions that would prove me wrong.
<strong>After that I don't touch the file.</strong> A script reads the price history and scores it.</p>

<div class="eyebrow mt">SCORING</div>
<p>The script scans every trading day inside the window using the intraday high and low, not the
close — a thesis that hits its target midday counts, and one that breaches its stop counts against
me even if it closes flat. Whichever side is touched first settles the call and locks it; later
price action cannot rescue or spoil it. If neither side is touched by the end of the window, it is
a draw. For a neutral call the logic inverts: touching either bound means I was wrong about it
being quiet.</p>

<div class="eyebrow mt">ASSUMPTIONS HAVE THREE STATES</div>
<ul class="checks">
<li class="open"><span class="mk">☐</span>Open — still tracking</li>
<li class="done"><span class="mk">☑</span>Confirmed</li>
<li class="false"><span class="mk">☒</span>Falsified — gets its own page; the original note is not edited</li>
</ul>

<div class="callout">
<div class="eyebrow">WHAT THIS RECORD CANNOT TELL YOU YET</div>
<p>The system went live in August 2026. As of {s['updated']} there are
<strong>{s['open']} open assumptions and {s['confirmed'] + s['falsified']} resolved</strong>.
The first real batch resolves in November. There is no hit rate worth quoting yet, and I am not
going to quote one. What is on this site is the method and the discipline — not a track record.</p>
</div>

<div class="eyebrow mt">THE STACK</div>
<p><strong>memory-desk</strong> — a news agent I built that pulls sources daily and scores each
item against the open assumptions above.<br>
<strong>The ledger</strong> — this record. Python, local files, no external service.<br>
<strong>Models</strong> — where a name is worth the work, a three-scenario DCF in Excel with every
assumption traced to a historical anchor and a falsification signal.</p>

<div class="eyebrow mt">ON AI, PLAINLY</div>
<p>I use AI heavily — for retrieval, for drafting, for building the tooling behind this site, and
for translating these pages out of Chinese. What it does not do is choose which question to work
on, decide which assumptions are load-bearing, set the parameter ranges in the models, or decide
when I was wrong. Scarce in 2026 is not the ability to generate a research report. It is the
ability to find the error in one.</p>

<div class="eyebrow mt">WHY THE PRIMARY RESEARCH IS IN CHINESE</div>
<p>The memory supply chain is Korean, Japanese, Taiwanese and Chinese. Korean-language disclosure,
CXMT capacity reporting and Chinese-language supply-chain coverage all carry information that
reaches English-language research late or not at all. I read those sources directly and think in
Chinese while doing it. Every page here has an English version; the Chinese original is one toggle
away and is the version I actually wrote.</p>"""
    return shell(f"Method — {SITE_TITLE}", body)


def coverage_page(d: dict) -> str:
    notes, reports = d["notes"], d["reports"]
    by_tk: dict = {}
    for n in notes:
        for t in (n["tickers"] or ["—"]):
            by_tk.setdefault(t, []).append(n)

    jrows = []
    for tk, ns in sorted(by_tk.items()):
        if tk == "—":
            continue
        ns.sort(key=lambda x: x["date"])
        last = ns[-1]
        name = last.get("subject_en") or "、".join(last["companies"]) or tk
        stance = last.get("stance_en") or "—"
        jrows.append(
            f'<tr><td class="mono">{escape(tk)}</td><td>{escape(name)}</td>'
            f'<td class="{STANCE_CLS.get(stance,"mid")}">{escape(stance)}</td>'
            f'<td class="mono dim">{escape(ns[0]["date"])}</td>'
            f'<td class="mono dim">{escape(last["date"])}</td>'
            f'<td class="mono dim">{len(ns)}</td></tr>')

    rrows = []
    for r in reports:
        if not r["count"]:
            continue
        rrows.append(
            f'<tr><td class="mono">{escape(r["ticker"])}</td>'
            f'<td>{escape(r["name_en"] or r["name"])}</td>'
            f'<td class="dim">{escape(r["note"])}</td>'
            f'<td class="mono dim">{escape(r["first"])}</td>'
            f'<td class="mono dim">{escape(r["last"])}</td>'
            f'<td class="mono dim">{r["count"]}</td></tr>')
    rsec = (f"""<div class="eyebrow mt">RESEARCH BRIEFS</div>
<p class="dim">Company briefs I commissioned and directed — I chose the questions, the coverage and
the framework; drafting and formatting were AI-assisted. The judgments above are where I put my own
conclusions on the line.</p>
<table class="tbl"><tr><th>Ticker</th><th>Name</th><th>View</th><th>First</th><th>Last</th><th>#</th></tr>
{''.join(rrows)}</table>""" if rrows else f"""<div class="eyebrow mt">RESEARCH BRIEFS</div>
<p class="dim">Company briefs are being organised by ticker and will appear here as they are
filed. {len(reports)} folders staged.</p>""")

    body = f"""<h1>Coverage</h1>
<p class="lede">Two kinds of work. Judgments carry a price, a threshold and a deadline —
they get scored. Briefs are background research and are not scored.</p>
<div class="eyebrow mt">JUDGMENTS · SCORED</div>
<table class="tbl"><tr><th>Ticker</th><th>Name</th><th>Stance</th><th>First</th><th>Last</th><th>#</th></tr>
{''.join(jrows)}</table>
{rsec}"""
    return shell(f"Coverage — {SITE_TITLE}", body)


def main() -> int:
    sp = SITE / "site.json"
    if not sp.exists():
        print("先跑 python scripts/export_public.py")
        return 1
    d = json.loads(sp.read_text(encoding="utf-8"))

    (SITE / "index.html").write_text(index_page(d), encoding="utf-8")
    (SITE / "method.html").write_text(method_page(d), encoding="utf-8")
    (SITE / "coverage.html").write_text(coverage_page(d), encoding="utf-8")
    jd = SITE / "judgments"
    jd.mkdir(exist_ok=True)
    td = SITE / "translations"
    n = en_n = stale = 0
    for note in d["notes"]:
        (jd / f"{note['slug']}.html").write_text(note_page(note), encoding="utf-8")
        n += 1
        tf = td / f"{note['slug']}.json"
        if tf.exists():
            tr = json.loads(tf.read_text(encoding="utf-8"))
            (jd / f"{note['slug']}.en.html").write_text(
                note_page(note, en=tr), encoding="utf-8")
            en_n += 1
            # 中文改过但没重翻的，提醒一下
            try:
                from importlib import util as _u
                spec = _u.spec_from_file_location("_t", HERE / "translate.py")
                m = _u.module_from_spec(spec)
                spec.loader.exec_module(m)
                if tr.get("hash") and tr["hash"] != m.content_hash(note):
                    stale += 1
                    print(f"  ! {note['slug']} 的中文改过了，英文版是旧的")
            except Exception:
                pass
    print(f"生成 index / method / coverage + {n} 篇中文页 + {en_n} 篇英文页")
    if stale:
        print(f"  有 {stale} 篇英文过期，跑 python scripts/translate.py 更新")
    elif en_n < n:
        print(f"  还有 {n - en_n} 篇没有英文版，跑 python scripts/translate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
