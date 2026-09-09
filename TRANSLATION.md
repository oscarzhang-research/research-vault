# 翻译规则

给 Claude Code 的指令文件。任何中译英都按这里的规则执行。

## 任务

`judgments/*.html` 是中文原文页。为每一篇生成对应的 `judgments/*.en.html`。
已存在 `.en.html` 的不要重新翻译，除非中文原文的修改时间更新。

英文版与中文版**结构完全一致**——同样的段落、同样的顺序、同样的清单条目数量。
只翻译正文文字，不动 HTML 结构、class 名、CSS 链接。
把页头 `<a class="lang" href="...">` 指向对应的另一语言版本。

## 术语表（必须严格使用）

| 中文 | 英文 |
|---|---|
| 晶圆损耗 | wafer penalty（不要用 wafer loss） |
| 位元供给 / bit 供给 | bit supply |
| 位元需求 | bit demand |
| 合约价 | contract price |
| 现货价 | spot price |
| 长协 / 长期供应协议 | long-term agreement (LTA) |
| 良率爬坡 | yield ramp |
| 先进封装 | advanced packaging |
| 硅通孔 | through-silicon via (TSV) |
| 产能爬坡 | capacity ramp |
| 出片 | wafer starts / output |
| 稼动率 / 加载率 | utilization |
| 供需缺口 | supply–demand gap |
| 超级周期 | supercycle |
| 结构性需求 | structural demand |
| 供给纪律 | supply discipline |
| 资本开支 | capex |
| 五大云厂 | the top-five hyperscalers |
| 企业级 SSD | enterprise SSD |
| 单位 bit 利润率 | per-bit margin |
| 二阶导 | second derivative（讲价格增速放缓时用 rate of change 更自然） |
| 消费电子 | consumer electronics |
| 需求破坏 | demand destruction |
| 渗透率 | penetration rate |
| 一句话结论 | Thesis in one sentence |
| 核心逻辑 | Core logic |
| 关键假设与验证信号 | Key assumptions and tracking signals |
| 关键数据与验证信号 | Key data and tracking signals |
| 风险与证伪条件 | What would prove me wrong |
| 与市场共识的差异 | Where I differ from consensus |
| 对我持仓的含义 | What this means for my positioning |
| 核心逻辑与产业最新动态 | Core logic and latest industry developments |
| 这段时间我判断对了什么 | What I got right |
| 判断错了什么 | What I got wrong |
| 错的共同原因 | The common cause behind the misses |
| 下一步改什么 | What I'm changing |
| 落笔价 | price at writing |
| 判定阈值 | threshold |
| 观察窗口 | resolution window |
| 信心 | conviction |
| 已证伪 | falsified |
| 待验证 | open |


## 公司专有名词（这些曾经翻错过，务必照抄）

| 简称 | 正确全称 | 说明 |
|---|---|---|
| SCA | Strategic Customer Agreements (SCAs) | **不是** Supply Commitment Agreements。机制上是 take-or-pay + price band（floor/ceiling）的多年供货协议 |
| NBM | New Business Model (NBM) | SanDisk 的商业模式名，不是产品型号。首次出现写全称 |
| CMBU | Cloud Memory Business Unit | 美光云内存事业部 |
| CDBU | Core Data Center Business Unit | 美光核心数据中心事业部。**注意不是 CDMU** |
| MCBU | Mobile and Client Business Unit | 美光移动与客户端事业部 |
| AEBU | Automotive and Embedded Business Unit | 美光汽车与嵌入式事业部 |
| RPO | remaining performance obligation | 剩余履约义务。SCA 那个 $100B 是 RPO / 最低承诺量口径，**不是"预期收入"** |
| HBF | High Bandwidth Flash (HBF) | 首次出现写全称 |
| 长江存储 | YMTC | 中文媒体写长江存储，英文界用 YMTC |

**缩写一律不要自己展开。** 原文写 SCA 就查这张表，表里没有就保留缩写并问我。
上一版把 SCA 展开成 "Supply Commitment Agreements" 是错的 —— 中文原文根本没写全称，
是译者自己加的，这违反「不要补充我没写的东西」。

**表里没有的术语，先问我，不要自己发挥。** 尤其是韩国和中国大陆公司的产品线代号、
以及中文财经媒体特有的说法。

## 写作规范

**拆长句。** 中文一句可以套三层括号，英文这么写没人读得下去。一个中文长句通常
拆成两到三个英文句子。

**括号里的自我反驳，提到正文。** 我习惯在看多的段落里用括号插入反对意见，比如
「（不过这里不得不重视一个风险，就是供给端的结构性问题一定会被解决……）」。
这是整篇最有价值的部分，不要留在括号里。提出来，用 `<em>My own caveat: ...</em>`
单独成句。

**结论先行。** 中文习惯先铺陈再给结论，英文机构研究习惯反过来。段落内部可以
重排语序，把结论提到句首。

**保留第一人称。** 我写的是「我认为」「我倾向于」，不要改成 "one could argue" 这类
学术腔。保持 "I think" / "I lean toward" / "My read is"。

**数字和单位照抄，不换算。** EB、ZB、bit、万亿韩元这些原样保留。
韩元金额保留 ₩ 和原数量级，不要折成美元。

**不确定的地方标出来。** 如果某句话的意思我写得含糊，不要猜测后自信地翻出来，
用 `<!-- TRANSLATOR: 这句我不确定指的是 X 还是 Y -->` 标在旁边，我会自己改。

## 绝对不要做的事

- **不要润色我的观点。** 我说错的地方就让它错着，这是公开原始判断记录的意义。
- **不要补充我没写的论据。** 哪怕你知道更好的理由。
- **不要把口语化的判断改成学术表述。** 「我倾向于乐观情景」就是 "I lean optimistic"，
  不是 "the author's base case skews constructive"。
- **不要删掉任何一条待验证信号或证伪条件。** 数量必须和中文版一致。
- **不要改变立场标签。** 看多就是 Long，不要软化成 "constructive"。

## 页头语言切换

中文页：`<a class="lang" href="xxx.en.html">EN</a>`
英文页：`<a class="lang" href="xxx.html">中</a>`

## 完成后自检

1. 中英两版的 `<li>` 数量是否一致
2. 有没有遗漏 `<section>`
3. 术语表里的词有没有用错
4. 有没有 `TRANSLATOR:` 标记还没处理
