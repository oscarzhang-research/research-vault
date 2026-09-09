#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 C:\\Investment\\知识库 里的笔记导出成公开网站。

用法（在 research-vault 目录下）：
    python scripts/export_public.py              # 正常导出
    python scripts/export_public.py --check      # 只跑脱敏检查，不写文件
    python scripts/export_public.py --vault D:\\别的路径\\知识库

做四件事：
  1. 扫描知识库里所有笔记，跳过写了「公开: false」的
  2. 脱敏检查 —— 命中金额、账户、卖方研报长引述等模式就报警并中止
  3. 抽取结构化数据（立场、落笔价、阈值、窗口、假设三态…）写进 site.json
  4. 生成中文 HTML 页面；英文版由 Claude Code 按 TRANSLATION.md 另行生成

设计原则：这个脚本只读知识库，绝不修改它。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from html import escape
from pathlib import Path

# ── 路径 ──────────────────────────────────────────────
HERE = Path(__file__).resolve().parent
SITE = HERE.parent
DEFAULT_VAULT = SITE.parent / "知识库"

SKIP_DIRS = ("99_模板", "示例", "输出", "证据", "数据", "kbcore", ".git", "模型")
SKIP_FILES = ("使用说明", "环境配置", "简报素材", "CLAUDE")

# 主体名归一：中文名 → 英文名 + 货币
# 标题归一：中文标题 → 英文标题
TITLE_MAP = {
    "美光投资前瞻": "Micron — initiation",
    "闪迪投资前瞻": "SanDisk — initiation",
    "三星电子的投资前瞻": "Samsung Electronics — initiation",
    "SNDK投资者日核心观点汇总": "SanDisk — investor day takeaways",
    "存储行业最新动态": "Memory — industry update",
    "存储周期性思考与最新动态": "Memory — is this cycle different?",
    "存储行业思考与最新动态": "Memory — industry update",
    "仓位管理": "Position sizing — what I got wrong",
    "听巴菲特1998年演讲后的感悟": "Notes on Buffett's 1998 talk",
    "对赌": "Notes on 对赌 (Betting on Growth)",
    "研究数据互联": "Linking the research data",
}

SUBJECT_MAP = {
    "micron technology": ("Micron Technology", "MU", "$"),
    "美光": ("Micron Technology", "MU", "$"),
    "sandisk": ("SanDisk", "SNDK", "$"),
    "闪迪": ("SanDisk", "SNDK", "$"),
    "sk hynix": ("SK hynix", "000660.KS", "₩"),
    "sk海力士": ("SK hynix", "000660.KS", "₩"),
    "海力士": ("SK hynix", "000660.KS", "₩"),
    "三星电子": ("Samsung Electronics", "005930.KS", "₩"),
    "samsung electronics": ("Samsung Electronics", "005930.KS", "₩"),
    "存储": ("Memory", "", ""),
    "memory": ("Memory", "", ""),
}
# ticker → 货币符号（韩股用韩元）
CCY = {"000660.KS": "₩", "005930.KS": "₩"}

TYPE_CN = {"投资": "个股判断", "宏观": "行业与宏观", "读书": "读书",
           "演讲": "演讲与访谈", "复盘": "复盘", "速记": "速记"}
TYPE_EN = {"投资": "Company", "宏观": "Theme", "读书": "Reading",
           "演讲": "Talks", "复盘": "Review", "速记": "Note"}
STANCE_EN = {"看多": "Long", "看空": "Short", "中性": "Neutral", "观望": "Watch"}

# ── 脱敏规则 ────────────────────────────────────────────
# 高危：命中就中止导出，必须人工处理
BLOCKERS = [
    # 只拦「我的钱」，不拦股价/市值 —— 后者是公开信息，本来就该显示
    ("我的资金金额", r"(我(?:的)?(?:账户|资金|本金|仓位|头寸|投入)|投入了|亏了|赚了)[^\n]{0,20}(?:\$|₩|US\$|USD\s?|人民币|美元)?[\d,]{4,}"),
    ("账户信息", r"(账户|券商账号|资金账号|证券账户)[^\n]{0,20}[\d]{4,}"),
    ("个人交易记录", r"(我(?:今天|昨天|上周|本周)?(?:买入|卖出|加仓|减仓|清仓|建仓)了?)[^\n]{0,30}[\d]+\s*(?:股|手|万|美元|元)"),
    ("家人信息", r"(家人|父母|老婆|太太|妻子|儿子|女儿)的?(?:账户|资金|钱|仓位)"),
]
# 提醒：不中止，但列出来让你自己过一眼
WARNINGS = [
    ("卖方机构提及", r"(高盛|Goldman|花旗|Citi|摩根士丹利|Morgan Stanley|摩根大通|JPM|美银|BofA|瑞银|UBS|野村|Nomura|巴克莱|Barclays|伯恩斯坦|Bernstein|杰富瑞|Jefferies|瑞穗|Mizuho)"),
    ("疑似长引述", r"[「“][^」”]{80,}[」”]"),
    ("仓位相关表述", r"(仓位|持仓|加仓|减仓|建仓|清仓|杠杆|保证金)"),
]


def read_text(p: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return p.read_text(encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return p.read_text(encoding="utf-8", errors="replace")


def parse_front_matter(text: str) -> tuple[dict, str]:
    """解析 --- 包起来的元数据块。不依赖 PyYAML，够用就好。"""
    m = re.match(r"^\ufeff?---\s*\r?\n(.*?)\r?\n---\s*\r?\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    meta: dict = {}
    for line in m[1].splitlines():
        line = re.sub(r"\s+#.*$", "", line).strip()   # 去掉行尾注释
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if v.startswith("[") and v.endswith("]"):
            v = [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
        meta[k] = v
    return meta, m[2]


def split_sections(body: str) -> list[tuple[str, str]]:
    """按 ## 标题切段，保留顺序。"""
    out, cur, buf = [], None, []
    for line in body.splitlines():
        m = re.match(r"^#{2,3}\s+(.+?)\s*$", line)
        if m:
            if cur and "".join(buf).strip():
                out.append((cur, "\n".join(buf).strip()))
            cur, buf = m[1].strip(), []
        else:
            buf.append(line)
    if cur and "".join(buf).strip():
        out.append((cur, "\n".join(buf).strip()))
    return out


def extract_checks(body: str) -> dict:
    """抽出假设三态。"""
    return {
        "open": re.findall(r"^\s*[-*]\s*\[\s\]\s*(.+)$", body, re.M),
        "confirmed": re.findall(r"^\s*[-*]\s*\[x\]\s*(.+)$", body, re.M | re.I),
        "falsified": re.findall(r"^\s*[-*]\s*\[\s*!\s*\]\s*(.+)$", body, re.M),
    }


def scan_sensitive(text: str, name: str) -> tuple[list, list]:
    """返回 (必须处理的, 提醒你看一眼的)。"""
    blocks, warns = [], []
    for tag, pat in BLOCKERS:
        for m in re.finditer(pat, text):
            s, e = max(0, m.start() - 40), min(len(text), m.end() + 40)
            blocks.append((tag, name, text[s:e].replace("\n", " ")))
    for tag, pat in WARNINGS:
        hits = list(re.finditer(pat, text))
        if hits:
            warns.append((tag, name, len(hits)))
    return blocks, warns


def md_to_html(md: str) -> str:
    """够用的 Markdown 渲染：段落、列表、勾选框、加粗、行内注释。"""
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
            state = m[1].lower()
            cls = {"": "open", " ": "open", "x": "done", "!": "false"}.get(state, "open")
            mark = {"open": "☐", "done": "☑", "false": "☒"}[cls]
            out.append(f'<li class="{cls}"><span class="mk">{mark}</span>{inline(m[2])}</li>')
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


def inline(s: str) -> str:
    s = escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def norm_subject(companies: list, tickers: list) -> tuple[str, str, str]:
    """把中英混写的主体名归一成 (英文名, 代码, 货币符号)。"""
    for c in companies:
        hit = SUBJECT_MAP.get(str(c).strip().lower())
        if hit:
            name, tk, ccy = hit
            tk = tickers[0] if tickers else tk
            return name, tk, CCY.get(tk, ccy or "$")
    name = "、".join(str(c) for c in companies) if companies else ""
    tk = tickers[0] if tickers else ""
    return name, tk, CCY.get(tk, "$")


def slugify(name: str, date: str, ticker: str) -> str:
    """URL 必须全英文 —— GitHub Pages 上中文路径会变成一串百分号编码。"""
    base = ticker or name
    base = re.sub(r"\.(KS|HK|SH|SZ)$", "", base, flags=re.I)
    base = re.sub(r"[^A-Za-z0-9]+", "-", base).strip("-").lower()
    if not base:
        base = "note"
    return f"{date}-{base}"


def collect(vault: Path) -> tuple[list, list, list]:
    notes, blocks, warns = [], [], []
    for p in sorted(vault.rglob("*.md")):
        rel = str(p.relative_to(vault)).replace("\\", "/")
        if any(d in rel for d in SKIP_DIRS) or any(f in p.stem for f in SKIP_FILES):
            continue
        text = read_text(p)
        meta, body = parse_front_matter(text)
        if not meta:
            continue
        if str(meta.get("公开", meta.get("public", ""))).lower() in ("false", "no", "0"):
            continue

        b, w = scan_sensitive(text, p.name)
        blocks += b
        warns += w

        ntype = str(meta.get("type", "")).strip()
        tickers = meta.get("tickers") or []
        if isinstance(tickers, str):
            tickers = [tickers]
        companies = meta.get("companies") or meta.get("industry") or []
        if isinstance(companies, str):
            companies = [companies]
        date = str(meta.get("date", "")).strip()[:10]

        subj_en, subj_tk, ccy = norm_subject(companies, tickers)
        notes.append({
            "file": p.name,
            "slug": slugify(subj_en or str(meta.get("title", p.stem)), date, subj_tk),
            "subject_en": subj_en,
            "ccy": ccy,
            "type": ntype,
            "type_cn": TYPE_CN.get(ntype, ntype),
            "type_en": TYPE_EN.get(ntype, ntype),
            "date": date,
            "title": str(meta.get("title", p.stem)).strip().rstrip("：:"),
            "title_en": TITLE_MAP.get(
                str(meta.get("title", p.stem)).strip().rstrip("：:"), ""),
            "companies": companies,
            "tickers": tickers,
            "stance": str(meta.get("stance", "")).strip(),
            "stance_en": STANCE_EN.get(str(meta.get("stance", "")).strip(), ""),
            "conviction": meta.get("conviction", ""),
            "horizon": str(meta.get("horizon", "")).strip(),
            "price": str(meta.get("price", "")).strip(),
            "target": str(meta.get("target", "")).strip(),
            "threshold": str(meta.get("threshold", "")).strip(),
            "tags": meta.get("tags") or [],
            "status": str(meta.get("status", "")).strip(),
            "sections": split_sections(body),
            "checks": extract_checks(body),
            "chars": len(body),
        })
    # 给每篇算一个「分量」，首页头条用它挑，而不是简单取最新
    for n in notes:
        n["weight"] = (n["chars"] // 100) + len(n["checks"]["open"]) * 20 \
                      + (60 if n["price"] and n["target"] else 0)
    # slug 撞车就加序号，保证每篇有唯一 URL
    seen: dict = {}
    for n in notes:
        base = n["slug"]
        if base in seen:
            seen[base] += 1
            n["slug"] = f"{base}-{seen[base]}"
        else:
            seen[base] = 1

    notes.sort(key=lambda n: n["date"], reverse=True)
    return notes, blocks, warns


# 模型说明：文件名关键词 → (展示名, 一句话作用, 结构描述)
MODEL_META = {
    "sndk": ("SanDisk — three-scenario DCF",
             "What SNDK is worth if the NAND price floor holds, softens, or breaks",
             "3 scenarios · ~800 live formulas"),
    "mu": ("Micron — three-scenario DCF",
           "What MU is worth across the range of memory pricing outcomes",
           "3 scenarios"),
    "缺口": ("The arithmetic of the gap",
             "Bit-level supply and demand — how wide the shortage is, and for how long",
             "supply–demand bridge"),
    "gap": ("The arithmetic of the gap",
            "Bit-level supply and demand — how wide the shortage is, and for how long",
            "supply–demand bridge"),
}


def scan_vault_models(vault: Path, site: Path) -> list:
    """扫知识库的模型文件夹，把 xlsx 复制到公开站，并生成清单。"""
    src = vault / "01_投资决策与前瞻" / "模型"
    out = []
    if not src.exists():
        return out
    dst = site / "models" / "files"
    dst.mkdir(parents=True, exist_ok=True)
    for f in sorted(src.glob("*.xls*")):
        if f.name.startswith(("~$", ".")):
            continue
        low = f.stem.lower()
        meta = None
        for k, v in MODEL_META.items():
            if k.lower() in low:
                meta = v
                break
        name, purpose, shape = meta or (f.stem, "", "")
        slug = re.sub(r"[^A-Za-z0-9]+", "-", f.stem).strip("-").lower() or "model"
        target = dst / f"{slug}{f.suffix}"
        try:
            target.write_bytes(f.read_bytes())
        except OSError as e:
            print(f"  复制 {f.name} 失败：{e}")
            continue
        out.append({
            "slug": slug,
            "name": name,
            "purpose": purpose,
            "shape": shape,
            "file": f"files/{target.name}",
            "filename": f.name,
            "size_kb": round(target.stat().st_size / 1024),
        })
    return out


def scan_reports(site: Path) -> list:
    """扫 reports/<TICKER>/ 下的独立研报，生成覆盖清单。"""
    out = []
    root = site / "reports"
    if not root.exists():
        return out
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        files = sorted([f for f in d.glob("*.html")])
        meta = {}
        mp = d / "_meta.md"
        if mp.exists():
            meta, _ = parse_front_matter(read_text(mp))
        dates = []
        for f in files:
            m = re.match(r"(\d{4}-\d{2}-\d{2})", f.stem)
            if m:
                dates.append(m[1])
        out.append({
            "ticker": d.name,
            "name": str(meta.get("name", meta.get("公司", d.name))).strip(),
            "name_en": str(meta.get("name_en", "")).strip(),
            "stance": str(meta.get("stance", meta.get("立场", ""))).strip(),
            "note": str(meta.get("note", meta.get("一句话", ""))).strip(),
            "first": min(dates) if dates else "",
            "last": max(dates) if dates else "",
            "count": len(files),
            "files": [{"name": f.name, "date": re.match(r"(\d{4}-\d{2}-\d{2})", f.stem)[1]
                       if re.match(r"(\d{4}-\d{2}-\d{2})", f.stem) else "",
                       "title": re.sub(r"^\d{4}-\d{2}-\d{2}-", "", f.stem)} for f in files],
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=str(DEFAULT_VAULT))
    ap.add_argument("--check", action="store_true", help="只跑脱敏检查")
    a = ap.parse_args()

    vault = Path(a.vault)
    if not vault.exists():
        print(f"找不到知识库：{vault}")
        print("用 --vault 指定路径，比如：python scripts/export_public.py --vault C:\\Investment\\知识库")
        return 1

    notes, blocks, warns = collect(vault)
    print(f"扫描 {vault}")
    print(f"读到 {len(notes)} 篇可公开笔记\n")

    if blocks:
        print("!! 发现必须处理的敏感内容，已中止导出：\n")
        for tag, name, ctx in blocks[:20]:
            print(f"  [{tag}] {name}")
            print(f"        …{ctx.strip()[:110]}…")
        print(f"\n共 {len(blocks)} 处。改掉，或在那篇笔记里写「公开: false」，再跑一次。")
        return 2

    if warns:
        print("提醒（不影响导出，但值得你扫一眼）：")
        agg: dict = {}
        for tag, name, n in warns:
            agg.setdefault(tag, []).append(f"{name}×{n}")
        for tag, items in agg.items():
            print(f"  · {tag}：{'、'.join(items[:6])}{' …' if len(items) > 6 else ''}")
        print()

    reports = scan_reports(SITE)
    models = scan_vault_models(vault, SITE)
    stats = {
        "notes": len(notes),
        "companies": len({t for n in notes for t in n["tickers"]}),
        "open": sum(len(n["checks"]["open"]) for n in notes),
        "confirmed": sum(len(n["checks"]["confirmed"]) for n in notes),
        "falsified": sum(len(n["checks"]["falsified"]) for n in notes),
        "reports": sum(r["count"] for r in reports),
        "models": len(models),
        "updated": dt.date.today().isoformat(),
    }
    print(f"统计：{stats['notes']} 篇 · {stats['companies']} 个标的 · "
          f"假设 {stats['open']} 待验证 / {stats['confirmed']} 已验证 / "
          f"{stats['falsified']} 已证伪 · 研报 {stats['reports']} 篇 · 模型 {stats['models']} 份")

    if a.check:
        print("\n--check 模式，没有写任何文件。")
        return 0

    data = {"stats": stats, "notes": notes, "reports": reports, "models": models}
    (SITE / "site.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n结构化数据 → {SITE / 'site.json'}")
    print("接下来跑：python scripts/translate.py  然后 python scripts/build_site.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
