# yike-photo-export

把百度**一刻相册**里的照片和视频以**原图**批量导出到本地，支持 MD5 字节级校验、断点续传和相同内容去重。

## 目录

```text
yike-photo-export/
├── README.md
├── SKILL.md                      # skill 主入口（两平台共用）
├── agents/
│   └── openai.yaml               # Codex UI 配置
├── references/
│   └── api-notes.md              # 接口协议、字段含义、排错对照表
└── scripts/
    ├── yike_export.py            # 主程序（走单文件接口，逐个下载 + MD5 校验）
    ├── yike_batch.py             # 备用：走 batchdownload 接口，绕开单文件限流
    ├── yike-resume.py            # 长时间续传驱动：限流退避 + 多轮重试
    ├── yike.sh                   # 包装器，自动注入 .pydeps/ 到 PYTHONPATH
    └── test_yike_export.py       # 端到端测试（含 mock 服务器，42+ 项断言）
```

仓库根 `yike-photo-export.skill` 是 `npm run pack` 生成的打包产物，已入库。

## 用途

适合这些问题：

- 「我想把一刻相册的照片全部下载下来」
- 「相册要搬家到 NAS / 移动硬盘，怎么整批导出」
- 「下载下来的到底是不是原图，怎么确认」
- 「几个相册里有重复照片，不想占双份空间」

核心设计取舍：**逐个文件下载 + MD5 校验**，而不是用官方网页的"打包成 zip 下载"。
理由是无法逐文件校验、大账号易超时、失败不可续传。备份场景下可靠性优先。

## 快速开始

```bash
pip install requests
# 可选：让工具直接从浏览器读取 Cookie，免去手动复制
pip install browser_cookie3

cd scripts

# 1. 验证凭据并盘点规模（只读）
python3 yike_export.py check --browser chrome

# 2. 试跑 20 项，确认目录结构
python3 yike_export.py download --browser chrome --out ./yike --limit 20

# 3. 全量下载，按年月归档
python3 yike_export.py download --browser chrome --out ./yike --jobs 4 --layout year-month

# 4. 校验本地副本与云端 MD5 一致
python3 yike_export.py verify --out ./yike
```

不支持 `browser_cookie3` 时，用 `--cookie-file cookies.txt` 手动提供 Cookie
（浏览器 F12 → Network → 任意 `photo.baidu.com` 请求 → 复制 `Cookie` 请求头）。

## 子命令

| 命令 | 作用 |
|---|---|
| `check` | 验证 Cookie，统计项目总数、照片/视频分布、总容量 |
| `list` | 导出清单 JSONL + CSV，不下载任何文件 |
| `albums` | 列出所有相册及项目数，拿 `album_id` |
| `download` | 批量下载，支持断点续传、去重、归档布局 |
| `verify` | 重新计算本地文件 MD5，与云端记录比对 |

退出码：`0` 全部成功 · `1` 有失败项或分页异常 · `2` Cookie 失效 · `3` 参数/环境错误。

## 数据完整性设计

备份工具最危险的失败不是报错，而是**静默给出不完整的结果**。针对这一点做了三层防护：

1. **MD5 逐文件校验**：每个文件下载后与云端 `md5` 字段比对，不一致则删除重试，
   绝不把损坏文件留在目标目录。`.part` 临时文件 + 原子 `os.replace`，进程被 kill
   也不会留下半成品冒充完整文件；中断时会清理残留的 `.part`。
2. **分页异常不静默**：服务端 `has_more=1` 却给空游标/重复游标时，在下载前中止并
   警告（退出码 `1`），避免只备份了第一批就报告成功。`check`/`list` 会标注总数
   只是下限。确需继续用 `--allow-partial`。清单为空同样报非 0 退出码。
3. **同名文件绝不覆盖**：云端返回顺序会变，多相机又常产出同名文件。工具保证
   "一个磁盘路径只归一个文件所有"，续传时沿用状态里的原路径而非重新分配；
   目标名被内容不同的既有文件占用时另存为 `名字 (1).jpg` 并警告。
   只有**云端 MD5 校验通过**才认为本地文件可用——只比大小会误判
   （两台相机的 `IMG_0001.jpg` 经常同为 4096 字节）。
4. **去重前校验源文件内容**：硬链接/复制前比对 MD5，不符则退化为真实下载，
   避免把错误内容传播成 N 份。
5. **断点续传可验证**：状态文件记录每个 fsid 的落盘路径与 MD5；重跑时已存在且
   内容一致的文件直接跳过，不会重复下载也不会漏项。

> **删除云端副本前**：先全量下载 → `verify` 通过 → **再跑一次下载**（应为全部跳过）
> → **再 `verify` 一次**。`verify` 只证明"当时"磁盘与云端一致，不保证之后仍然如此。

## 安全须知

- 工具**不接触账号密码**，只复用你已登录浏览器的 Cookie。
- Cookie 等同登录态：手动模式用完请删除 `cookies.txt`，不要提交进 git。
- 工具**不落盘 Cookie**，也不调用任何删除云端文件的接口。
- **失败报告已脱敏**：`dlink` 是带签名的临时直链、接口 URL 带 `bdstoken`，
  这些在写入 `yike-export-report.json` 和打印前都会裁掉查询串，
  所以报告可以安全地分享或提交。
- 这是**非官方接口**，百度调整协议后可能失效；届时需按 `references/api-notes.md` 更新。

## 安装到 skill 目录

```bash
npm run validate yike-photo-export   # 校验
npm run pack yike-photo-export       # 打包 .skill
npm run install yike-photo-export    # 安装到本地工具链
```

## 测试

改完脚本务必重跑（会启动本地 mock 服务器，不联网、不消耗真实流量）：

```bash
python3 scripts/test_yike_export.py
```

覆盖：认证失败识别、游标分页、MD5 校验与篡改检测、断点续传、去重硬链接、
错误重试、年月归档、时间戳还原、相册模式、数量限制、分页异常中止、
失败报告凭据脱敏，以及四类回归用例：

| 回归用例 | 防止的问题 |
|---|---|
| 跨运行顺序变化 + 同名同尺寸 | 原图被静默覆盖、永久丢失 |
| 非 dict JSON 响应 | 裸 `AttributeError` 栈回溯 |
| `has_more` 为 `"true"` / `2` 等 | 被当成末页静默截断 |
| 空清单 | 谎报"备份完成" |
| 去重源内容不符 | 错误内容被硬链接传播 |

共 75 项断言。

## 脚本选型：什么时候用哪个

仓库里现在有 **3 个可运行的下载入口**，对应不同场景。先选工具，再选参数。

| 场景 | 工具 | 理由 |
|---|---|---|
| **首次、总量不大（< 几千张）** | `yike_export.py download` | 走单文件接口，失败可立即看到每张图的状态 |
| **遇到 `errno=50005` 限流** | 切到 `yike_batch.py` | 走批量 zip 接口，不受单文件限流影响；MD5 与原图一致 |
| **总量很大、想让它跑过夜/过几天** | `yike-resume.py` | 封装"探测→退避→下载→再探测"循环，不需人盯着 |
| **改完脚本后回归** | `test_yike_export.py` | mock 服务器本地跑，不联网不消耗真实流量 |

### `yike_batch.py`（限流绕开）

百度对 `file/v2/download`（单文件取直链）按账号级别限流 `errno=50005`，触发后可持续数小时。`yike_batch.py` 改走 `file/v1/batchdownload`（打包成 zip），实测 zip 内文件与原图 MD5 完全一致，是字节级原图，不损失完整性。

```bash
# 默认每批 30 个，下载 zip 后逐文件 MD5 校验并解压
python3 scripts/yike_batch.py \
  --cookie-file cookies.txt \
  --out /Volumes/Backup/yike

# 调大批次、关掉硬链接
python3 scripts/yike_batch.py \
  --cookie-file cookies.txt --out /Volumes/Backup/yike \
  --batch-size 50 --dedup copy
```

与 `yike_export.py` 共用同一个 `.yike-state.json`：已经成功下过的文件会自动跳过；中途切换两个工具，进度不会丢。

### `yike-resume.py`（长跑驱动）

适合总时长超过几小时的场景。`yike_export.py` 一次跑会持续打下载接口；一旦触发 `50005` 就只能中断。`yike-resume.py` 用一个**单次轻量探测**判断下载接口是否已解封，未解封就指数退避静默等待（5→10→20→30→45 分钟），解封后再启动 `yike_export.py` 跑一轮。

```bash
# 默认最长跑 24 小时
python3 scripts/yike-resume.py

# 想跑两天
python3 scripts/yike-resume.py --max-hours 48
```

前置条件（脚本里硬编码几个路径，使用前按需调整）：
- Cookie 写在 `/tmp/yike-cookie.txt`
- 下载目录为 `~/Pictures/yike`
- 云端预期总数 `EXPECTED_TOTAL = 7405`（写在脚本里，作为"完成"的判据）

中途任何时候 Ctrl-C，重跑同一命令即可继续。日志写 `~/Pictures/yike/resume.log`。

### 选型决策树

```
首次下载？
├─ 总量 < 3000 张 → yike_export.py
└─ 总量 ≥ 3000 张
   ├─ 准备跑过夜 → yike-resume.py
   └─ 不想改脚本、接受手工重试 → yike_export.py（遇到 50005 改用 yike_batch.py）
```
