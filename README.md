# 信息觅食视角下平民美食的跨平台传播实践 —— 以香港「兩餸飯」现象为例

> 资料采集需求说明书（Data Collection Brief）

## 一、研究主题

以香港「兩餸飯」（社区平价两菜一饭快餐）为研究对象，从**信息觅食理论**（Information Foraging Theory）视角，考察这一平民美食现象在**社交平台**与**搜索引擎/视频平台**之间的跨平台传播实践：用户如何在信息环境中识别「信息气味」（information scent）、选择信息斑块（information patch）、并在多平台之间迁移觅食行为。

## 二、采集需求

### 需求 1：社交平台上的评论与贴文

以 **Instagram**、**Facebook**、**Threads** 为主，采集围绕「兩餸飯」的用户生成内容：

| 内容类型 | 说明 |
| --- | --- |
| 贴文（post） | 图文/视频贴文的文案、发布时间、互动量（赞、评论、分享、收藏）、话题标签、定位 |
| 评论（comment） | 贴文下的评论与回复文本、层级关系、时间、点赞数 |
| 账号信息 | 发布者类型（个人 / 店铺 / 媒体 / KOL / 社群主页）、粉丝量级、地域标识 |

### 需求 2：Google 检索结果与媒体内容

围绕「兩餸飯」检索并归档：

- **报社**：香港本地报纸及网媒的报道、专栏、评论（如星岛、明报、HK01、东方、经济日报等）
- **电视台**：TVB、ViuTV、HOY 等电视媒体的新闻报道与专题节目（含节目页、文字稿、视频链接）
- **YouTube**：探店、评测、街访、vlog 等视频（标题、简介、发布时间、播放/点赞/评论数、字幕或评论样本）

## 三、时间范围

**2022 年 1 月 —— 2026 年 10 月**

- 起：2022-01-01，覆盖「兩餸飯」在疫情后成为社会话题的爆发期
- 止：2026-10-31，覆盖现象延续与演变阶段
- 边界处理：跨期内容按**发布时间**归档；发布时间不可考的，记录抓取时间并单独标注

## 四、检索关键词

| 语言/变体 | 关键词 |
| --- | --- |
| 繁体（主） | 兩餸飯、两餸饭、兩𩠌飯、三餸飯、四餸飯 |
| 简体 | 两𩠌饭、两菜一饭 |
| 英文/俗语 | two-dish rice、this this rice、HK two dish rice、$38 rice |
| 关联词 | 穷鬼餐、穷人恩物、平民饭堂、社企兩餸飯、兩餸飯地图 |
| 平台标签 | #兩餸飯 #two_disH_rice #hkfood #香港美食 #平民美食 |

## 五、参考字段（采集表结构建议）

```
platform          平台（instagram / facebook / threads / google / youtube）
source_type       来源类型（post / comment / news / tv_program / video）
source_name       媒体或账号名称
url               原始链接
title_or_text     标题或正文
published_at      发布时间
collected_at      采集时间
engagement        互动数据（JSON：likes/comments/shares/views）
keyword           命中关键词
lang              语言
location          地域/定位信息
note              备注（是否为转载、是否含商业推广等）
```

## 六、合规与伦理

- 仅采集**公开可见**内容，不绕过平台登录墙、不抓取私密社群
- 用户昵称、头像等身份信息在分析阶段做**匿名化处理**（如 U001、U002）
- 引用贴文与评论时保留原链接，遵守各平台服务条款与合理使用原则
- 数据仅用于学术研究，不用于商业用途、不二次分发原始数据集

## 七、交付物

1. 社交平台内容数据集（贴文 + 评论，含元数据）
2. Google / 媒体 / YouTube 内容清单（含链接与抓取快照说明）
3. 采集说明与清洗记录（去重、剔除规则、时间边界处理）
4. 平台分布与时间分布的描述性统计

---

## 八、需求 2 采集结果（已完成）

> 采集时间：2026-11-05　｜　覆盖区间：2022-01-01 ~ 2026-10-31

### 8.1 产出文件

| 文件 | 内容 | 规模 |
| --- | --- | --- |
| `data/google_news_2022-2026.csv` | Google News 索引的报社、网媒、电视台、YouTube、FB/IG 帖文条目（含解码后的媒体原始链接） | **2162 条** |
| `data/youtube_2022-2026.csv` | YouTube 视频元数据（精确上载日期、播放量、点赞、时长、频道、简介） | **327 条** |
| `data/兩餸飯_跨平台传播_2022-2026.xlsx` | **汇总 Excel**：8 个 sheet（说明 / 全部数据 / Instagram帖子 / Instagram评论 / YouTube视频 / 报刊网媒 / 电视台 / 平台统计），内容表 17 列统一表头 | **3513 条内容 + 9352 条评论** |
| `data/ig/posts.jsonl` | Instagram 帖子（标签 / 关键词搜索直采） | **1024 条** |
| `data/ig/comments.jsonl` | Instagram 评论（一级 + 二级回复） | **9352 条** |
| `data/summary.md` | 描述性统计摘要（类型 / 年份 / 来源域名 / 频道） | — |
| `data/stats.json` | 同上的机器可读版 | — |
| `data/raw/*.json` | 原始采集记录 | — |

### 8.2 结构分布（Google 新闻集 2162 条）

| 来源类型 | 条数 | 说明 |
| --- | --- | --- |
| news | 643 | 报社 / 网媒（明报、星岛、香港01、经济日报、文汇、am730…） |
| lifestyle | 322 | 生活饮食媒体（weekendhk、U Food、ULifestyle、Gotrip、新地…） |
| instagram | 308 | IG 贴文线索（需求 1 预采） |
| youtube | 307 | Google News 索引的 YouTube 视频 |
| facebook | 294 | FB 贴文线索（需求 1 预采） |
| tv | 225 | 电视台：TVB 97+28、Now 新闻 49、有线 28、myTV SUPER 9、HOY 7、RTHK 2 |
| aggregator | 40 | Yahoo 新闻等聚合页 |
| other / intl | 23 | 其他站点 / 境外媒体 |

年度分布：2022 **394** / 2023 **342** / 2024 **416** / 2025 **512** / 2026 **498**（截至 10 月）。

### 8.3 YouTube 集（327 条）

- 年度分布：2022 **38** / 2023 **34** / 2024 **34** / 2025 **112** / 2026 **109**
- 累计播放量约 **4977 万**，269 条有点赞数
- 主要频道：香港01、HOY 媒體網絡、星島頭條、TVB (official)、Mill MILK、觀塘食好嘢、高峰熱話、粵語最財經等
- 日期精度：231 条取自视频页 `dateText`（精确到日），96 条由相对时间（「X 年前 / X 個月前」）估算，`date_source` 字段已标注

### 8.3.1 Excel 汇总表

`data/兩餸飯_跨平台传播_2022-2026.xlsx`（2489 行）统一为 16 列：

| 列 | 含义 |
| --- | --- |
| 序号 / 平台 / 采集通道 / 来源类型 | 记录编号与**平台标注**（Instagram / Facebook / Threads / YouTube / 电视台 / 报社网媒 / 生活饮食媒体 / 新闻聚合 / 境外媒体 / 其他网站） |
| 来源名称 / 域名 | 媒体名、频道名或账号，及站点域名 |
| 标题 / 发布日期 / 采集日期 | 内容标题、发布时间（YYYY-MM-DD）、抓取日期 |
| 链接 | 可点击原始链接（Google News 链接已解码） |
| 播放量 / 点赞数 / 时长(秒) | YouTube 专有指标，其余留空 |
| 检索关键词 / 标题命中 / 备注 | 命中该条时的检索词、标题是否直含关键词、数据状态提示 |

格式：表头深蓝加粗居中、首行冻结、自动筛选、列宽按内容设定、隔行浅色底。

### 8.4 采集口径与已知限制

- **Google 口径**：使用 Google News 索引（RSS 检索 + `batchexecute` 解码还原媒体原始 URL）。Google 网页搜索直连被验证码拦截，故未纳入普通网页结果；报社、电视台、YouTube 三类目标已全部覆盖。
- **查询方式**：17 组关键词 × 5 个年度区间，另加 13 组 `site:` 定向检索（news.tvb.com、tvb.com、rthk.hk、viutv.com、hoy.tv、news.now.com、i-cable.com、youtube.com、facebook.com、instagram.com、mpweekly.com、mingpao.com、scmp.com）。
- **去重**：Google News article-id 去重；YouTube 按 video-id 去重。
- **噪声**：标题未必含「兩餸飯」（`title_hit` 列标注，标题命中 1381 / 2162）。相关性扩散条目保留以便研究者自行筛选。
- **Facebook / Instagram**：本集仅含 Google News 索引到的公开贴文链接（各 294 / 308 条），属需求 1 的线索，正式采集（正文、评论、互动量）另做。

### 8.5 正文全文采集（`data/articles.jsonl`）

标题层之外，对报社 / 电视台 / 生活媒体的报道页抓取**正文全文**：

| 项 | 结果 |
| --- | --- |
| 目标条数 | 1234 条（news + tv + lifestyle + aggregator + intl） |
| 成功抓取 | **1088 条**（88%），合计 **136.5 万字**，平均 1254 字/篇 |
| 长度分布 | ≥1000 字 448 篇、300–999 字 559 篇、<300 字 81 篇 |
| 全成功的媒体 | 明报 153/153、星岛 152/152、香港01 151/151、明周 114/114、TVB 97/97、am730 22/22 |
| YouTube 视频简介 | **267 / 327** 条（`data/youtube_details.jsonl`，另补全 319 条点赞数） |

**方法**：不写逐站规则（各站 DOM 结构不同），统一用 `trafilatura` 的通用正文抽取（基于文本密度与 DOM 结构的启发式）。
失败 89 条已按要求放弃：`topick.hket.com` / `news.hket.com`（405 反爬，34 条）、`hk.news.yahoo.com`（404 跳转失效，31 条）、`programme.tvb.com`（纯 JS 渲染，5 条）、`health.mingpao.com`（403，5 条）等。

正文并入 Excel 的「报道正文」sheet（1355 行 = 1088 篇报道 + 267 条视频简介），主表新增「正文字数」列可按有无正文筛选。

### 8.6 复现

```bash
pip install requests yt-dlp
python scripts/collect_google_news.py   # Google News + 真实 URL 解码
python scripts/collect_youtube_html.py  # YouTube 搜索 + 上载日期
python scripts/fetch_articles.py        # 报道正文全文（trafilatura）
python scripts/fetch_youtube_desc.py    # YouTube 视频简介
python scripts/threads_collect.py       # Threads 帖子
python scripts/threads_collect_replies.py  # Threads 回复
python scripts/build_summary.py         # 命中标记 + 统计
python scripts/build_xlsx.py            # 生成汇总 Excel
```

代理通过环境变量 `PROXY_URL` 指定（默认 `http://192.168.31.238:7897`）。采集带本地缓存（`.tmp/watch_cache.json`、`data/raw/url_decode_cache.json`），重跑不会重复请求。

---

## 九、需求 1 采集结果：Instagram 帖子与评论（已完成）

> 采集时间：2026-11-05　｜　覆盖区间：2022-01-01 ~ 2026-10-31　｜　账号：3 个已登录 profile 轮换（端口 9222 / 9223 / 9224）

### 9.1 采集方式

Instagram 网页版的标签页实际走的是**关键词搜索接口**（`PolarisKeywordSearchExplorePageRelayQuery`），因此：

1. 用已登录浏览器打开 `explore/search/keyword/?q=<关键词>`，抓首屏 GraphQL 请求的完整表单与请求头（`lsd`、`fb_dtsg`、`X-FB-Entry-Nonce` 等一次性 token）
2. 用 `requests` 复放首屏请求，再用 `page_info.end_cursor` 翻页（`PolarisKeywordSearchExplorePageRelayPaginationQuery`）
3. 三个账号分摊关键词，降低单账号限流风险
4. **相关性过滤**：正文/标签必须真的含「餸飯 / 𩠌飯 / dish rice」等词，剔除无关内容（初采 5809 条 → 过滤后 1024 条）
5. 评论走 `/api/v1/media/{pk}/comments/`，在浏览器上下文 fetch（复用登录态），按 `next_min_id` 翻页

### 9.2 结果概览

| 项 | 数量 |
| --- | --- |
| IG 帖子 | **1024 条**（图片 383 / 视频 353 / 多图 288） |
| IG 评论 | **9352 条**（一级 9052 + 回复 549，覆盖 648 帖） |
| 涉及账号 | 500+ 个（opcafehk 31、sourspicynoodle 25、singtaoheadline 24、student.nurse_foodie 17 等） |
| 帖子年度分布 | 2022 **104** / 2023 **86** / 2024 **187** / 2025 **319** / 2026 **328** |
| 评论年度分布 | 2022 **574** / 2023 **635** / 2024 **1481** / 2025 **3614** / 2026 **3297** |

### 9.3 帖子字段（posts.jsonl / Instagram帖子 sheet）

`platform, collect_channel, query, code, pk, media_id, taken_at, published_at, user_username, user_fullname, user_pk, is_verified, media_type, product_type, caption, hashtags, like_count, comment_count, view_count, carousel_count, image_urls, video_url, location_name, location_id, coauthors, url, collected_at`

### 9.4 评论字段（comments.jsonl / Instagram评论 sheet）

`platform, post_pk, post_code, post_published_at, post_url, comment_pk, parent_pk, level, text, created_at, published_at, user_username, user_pk, like_count, child_count, collected_at`

### 9.5 已知限制

- IG 搜索结果**相关性随翻页衰减**：单个关键词翻到 50+ 页后返回的多为无关内容，实际有效结果集中在每词前 20~30 页；#兩餸飯 采到 531 条后基本饱和（标签总量 6900，但搜索接口不返回全量）。
- **评论覆盖率约 43%**（9352 / 21551）：每帖最多翻 5 页（约 75 条），热门帖（>150 评论）只取头部；如需全量可提高 `--max-pages`。
- 二级回复仅取 API 返回的预览（`preview_child_comments`），未逐条展开 `replies` 接口。
- 只采集公开账号内容，私密账号与已删除帖自动跳过。

### 9.6 复现

```bash
# 1. 启动三个已登录浏览器（profile: ig / ig2 / ig3）
python ig_browser.py --profile ig  --port 9222
python ig_browser.py --profile ig2 --port 9223
python ig_browser.py --profile ig3 --port 9224

# 2. 帖子（标签 + 关键词）
python scripts/ig_collect_keyword.py --ports 9222,9223,9224 --pages 40

# 3. 评论
python scripts/ig_collect_comments.py --ports 9222,9223,9224 --max-pages 5

# 4. 汇总 Excel
python scripts/build_xlsx.py
```
