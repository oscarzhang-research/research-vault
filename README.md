# research-vault

Public research record — memory semiconductors, AI infrastructure.

Live: https://oscarzhang-research.github.io/research-vault

## 这个仓库是什么

私人知识库（`C:\Investment\知识库`，不在 git 里）导出后的公开版本。
知识库本身永远不进 git —— 只有脱敏、筛选后的内容进这里。

## 日常流程

写完笔记之后，一条命令：

```bash
python scripts/publish.py
git add -A && git commit -m "update" && git push
```

`publish.py` 依次做三件事：从知识库导出并脱敏检查 → 翻译改过的和没翻过的 → 生成中英页面。

**英文自动跟随中文。** 每篇正文都存了内容哈希，中文改了哈希就变，
下次跑 `publish.py` 会自动重翻那一篇；没改的直接跳过，不重复花钱。

分步跑也可以：

```bash
python scripts/export_public.py     # 知识库 → site.json，含脱敏检查
python scripts/translate.py         # 翻译需要翻的，结果存 translations/
python scripts/build_site.py        # 渲染中英页面
```

常用参数：

```bash
python scripts/export_public.py --check   # 只跑脱敏检查，不写文件
python scripts/translate.py --dry         # 只报告哪些要翻，不调 API
python scripts/translate.py --only mu     # 只翻某一篇
python scripts/translate.py --all         # 强制全部重翻
python scripts/publish.py --no-translate  # 跳过翻译
```

## API key

翻译要调 Anthropic API，key 从环境变量读，**永远不要写进任何文件**：

```powershell
setx ANTHROPIC_API_KEY "sk-ant-..."
```

设完重开一个终端窗口才生效。没设的话 `translate.py` 会提示你，
其余步骤照常能跑。

推送后 GitHub Actions 会自动部署，约两分钟生效。

## 排除某篇不公开

在知识库那篇笔记的元数据里加一行：

```
公开: false
```

## 只跑检查不写文件

```bash
python scripts/export_public.py --check
```

命中金额、账户、个人交易记录会中止导出并打印位置。
