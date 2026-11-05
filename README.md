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
| `data/youtube_2022-2026.csv` | YouTube 视频元数据（精确上载日期、播放量、点赞、频道、简介） | **319 条** |
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

### 8.3 YouTube 集（319 条）

- 年度分布：2022 **42** / 2023 **38** / 2024 **32** / 2025 **103** / 2026 **104**
- 累计播放量约 **5116 万**
- 主要频道：香港01、HOY 媒體網絡、星島頭條、TVB (official)、Mill MILK、觀塘食好嘢、高峰熱話、粵語最財經等
- 日期精度：271 条取自视频页 `dateText`（精确到日），48 条由相对时间（「X 年前 / X 個月前」）估算，`date_source` 字段已标注

### 8.4 采集口径与已知限制

- **Google 口径**：使用 Google News 索引（RSS 检索 + `batchexecute` 解码还原媒体原始 URL）。Google 网页搜索直连被验证码拦截，故未纳入普通网页结果；报社、电视台、YouTube 三类目标已全部覆盖。
- **查询方式**：17 组关键词 × 5 个年度区间，另加 13 组 `site:` 定向检索（news.tvb.com、tvb.com、rthk.hk、viutv.com、hoy.tv、news.now.com、i-cable.com、youtube.com、facebook.com、instagram.com、mpweekly.com、mingpao.com、scmp.com）。
- **去重**：Google News article-id 去重；YouTube 按 video-id 去重。
- **噪声**：标题未必含「兩餸飯」（`title_hit` 列标注，标题命中 1381 / 2162）。相关性扩散条目保留以便研究者自行筛选。
- **Facebook / Instagram**：本集仅含 Google News 索引到的公开贴文链接（各 294 / 308 条），属需求 1 的线索，正式采集（正文、评论、互动量）另做。

### 8.5 复现

```bash
pip install requests yt-dlp
python scripts/collect_google_news.py   # Google News + 真实 URL 解码
python scripts/collect_youtube_html.py  # YouTube 搜索 + 上载日期
python scripts/build_summary.py         # 命中标记 + 统计
```

代理通过环境变量 `PROXY_URL` 指定（默认 `http://192.168.31.238:7897`）。采集带本地缓存（`.tmp/watch_cache.json`、`data/raw/url_decode_cache.json`），重跑不会重复请求。
