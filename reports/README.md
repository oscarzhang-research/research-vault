# 独立研报

一个公司一个文件夹，文件夹名用股票代码。

```
reports/
├── NVDA/
│   ├── _meta.md                    ← 公司信息，见下
│   ├── 2026-05-12-initiation.html
│   └── 2026-08-03-q2-review.html
└── AVGO/
```

## 文件命名

`日期-标题.html`，日期用 `YYYY-MM-DD`。脚本按日期排序，
并从文件名提取首次覆盖和最后更新时间。

## _meta.md 格式

```
---
name: 英伟达
name_en: NVIDIA
stance: Long
note: AI 算力的定价权持有者，但估值已计入完美执行
---
```

`stance` 用 Long / Short / Neutral / Watch，会显示在 Coverage 页。
`note` 一句话，几十个字就够。

放好之后跑 `python scripts/export_public.py` + `python scripts/build_site.py`，
Coverage 页会自动更新。
