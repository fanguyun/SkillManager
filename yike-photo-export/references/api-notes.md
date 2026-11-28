# 一刻相册接口协议笔记

来源：对 `photo.baidu.com` 网页端接口的观察与验证，以及开源项目
[HengyueLi/baiduphoto](https://github.com/HengyueLi/baiduphoto)（MIT）的协议整理。
本文件是 `scripts/yike_export.py` 的实现依据。

## 认证

所有接口都靠 **Cookie** 认证，没有 OAuth、没有 API Key。关键字段：

| Cookie | 作用 |
|---|---|
| `BDUSS` / `BDUSS_BFESS` | 登录态核心。缺失必然失败 |
| `STOKEN` | 网盘系接口的会话令牌 |
| `BAIDUID` / `BIDUPSID` | 设备标识，辅助 |
| `__yjs_duid` | 设备指纹 |

另有一个 **`bdstoken`** 参数，从 `https://photo.baidu.com/photo/web/home` 的 HTML 里
以 `templateData` 形式带出。它随会话变化，本工具在首次请求时自动抓取并缓存。
抓不到时多数接口仍可用（工具会打印提示但不中断）。

**认证失败的判据**：响应 JSON 中 `errno == -6`。实测未带 Cookie 请求任一接口都返回
`{"errno":-6,"request_id":...}`，HTTP 状态仍是 200，所以**不能靠 HTTP 状态码判断登录态**。

## 接口清单

基址：`https://photo.baidu.com`。所有响应均为 JSON，成功时 `errno == 0`。

### 1. 获取文件列表（分页）

```
GET /youai/file/v1/list
参数：cursor（首页留空）、need_filter_hidden=0、clienttype=70、bdstoken
返回：{"errno":0, "list":[...], "has_more":0|1, "cursor":"下一页游标"}
```

`has_more == 1` 时用返回的 `cursor` 取下一页；`0` 表示结束。
列表项关键字段：

| 字段 | 说明 |
|---|---|
| `fsid`（部分返回 `fs_id`） | 文件唯一 ID，下载和删除都用它 |
| `path` | 形如 `/youa/web/IMG_0001.jpg`，文件名取最后一段 |
| `md5` | **云端文件的 MD5，校验原图完整性的依据** |
| `size` | 字节数 |
| `ctime` / `mtime` | 创建/修改时间，单位秒。用作拍摄时间 |
| `dlink` | 有时直接带下载直链；没有则需调下载接口 |

### 2. 获取下载直链

```
GET /youai/file/v2/download
参数：clienttype=70、fsid、bdstoken
返回：{"errno":0, "dlink":"https://..."}
```

`dlink` 是带签名的临时直链，可能有时效。因此实现上是**逐个文件先取 dlink 再立即下载**，
不预先批量取链接（否则并发下载时后半段链接可能已过期）。

### 3. 相册列表

```
GET /youai/album/v1/list
参数：clienttype=70、limit=30、need_amount=1、need_member=1、field=mtime、cursor
返回：{"errno":0, "list":[{"album_id":..., "title":..., "amount":...}], "has_more":..., "cursor":...}
```

### 4. 相册内文件

```
POST /youai/album/v1/listfile
表单：cursor、album_id
返回：同列表接口结构
```

注意是 **POST**，且分页游标同样靠 `cursor`。

### 5. 批量打包下载（本工具未采用）

```
GET  /youai/file/v1/batchdownloadvariable   → sign1/sign2/sign3/timestamp
GET  /youai/file/v1/batchdownload           → 一个 zip 的 dlink
```

`sign` 需要把 `sign1` 用一个 RC4 变体（密钥 `sign3`）加密后 base64。
**本工具刻意不使用这条路径**，原因有三：

1. 打包成 zip 后无法逐文件校验 MD5，失去"原图可验证"这一核心保证。
2. 大账号打包极易超时或失败，且失败后没有断点续传。
3. 开源实现里这条路径的下载函数是**空实现**（只有 `pass`），没有经过真实验证。

逐个文件下载虽然慢一些，但可靠、可续传、可校验，对"备份照片"这个目标更合适。

## 断点续传的判定语义（重要）

状态文件 `state-<fsid>` 记录每个文件的落盘路径与云端 md5。重跑时的判定规则：

| 条件 | 处理 |
|---|---|
| 有 ok 记录，路径存在，**md5 与云端一致** | 跳过（沿用原路径） |
| 有 ok 记录，但内容不符或文件丢失 | 重新下载 |
| 无记录，自然文件名在磁盘上且 **md5 一致** | 认领该文件，标记 ok |
| 无记录，自然文件名被**内容不同**的文件占用 | 另存为 `名字 (1).jpg`，打印警告 |
| 同 md5 的其它文件已在本轮就绪 | 硬链接/复制（**复制前先校验源文件 md5**） |

两条关键约束：

1. **只比 `size` 不能判定文件可用**。多相机同名照片经常同为 4096 字节，
   但内容不同。必须比对云端 `md5`。
2. **一个磁盘路径只能归一个 fsid**。云端返回顺序会变，若每轮按顺序重新分配
   文件名，同名文件就会被算到别的 fsid 头上，覆盖掉上一轮的原图。续传必须
   沿用状态记录里的 `file`，而不是本轮新算出的路径。

## 已废弃/易变项

- `get_SinglePage` / `getAllItems` 等旧方法名已废弃，以 `get_self_1page` 语义为准。
- 接口无版本保证。**如果工具突然全面失败，第一件事是用浏览器 F12 打开网页端，
  对比实际请求的路径和参数名是否变化**，再改 `yike_export.py` 中对应的 URL 与字段。

## 排错对照表

| 现象 | 原因 | 处理 |
|---|---|---|
| `errno=-6` | Cookie 失效或未登录 | 浏览器重新登录一刻相册，重取 Cookie |
| 响应不是 JSON，返回 HTML | 被风控拦截或跳转登录页 | 降并发、加 `--sleep`，稍后重试 |
| `接口未返回 dlink` | 该文件被限制或接口变更 | 记录 fsid，单独重试；持续失败则核对接口 |
| MD5 不匹配 | 传输损坏 | 工具自动删除并重试（默认 2 次） |
| 下载到一半中断 | 网络或 Cookie 过期 | 重跑同一命令，状态文件自动续传 |
| `list` 为空但账号有照片 | 接口分页语义变化 | 检查 `need_filter_hidden` 等参数 |
| 警告"清单可能不完整" | `has_more=1` 但游标为空/重复 | 见下方"分页完整性" |

## 分页完整性（重要）

`has_more` 与 `cursor` 可能不一致。实测到的异常形态：

- `has_more=1` 但 `cursor` 是空字符串
- `has_more=1` 但 `cursor` 与上一页相同（会死循环）
- 返回空 `list` 但 `has_more=1`

**这些都不能当作"已到末页"处理。** 早期实现把空游标视为结束，结果只下载了第一页就
报告成功——对备份场景是静默数据丢失。现在的处理：

- `_next_cursor()` 统一校验，异常时记录到 `client.warnings`
- `download` 在**开始下载前**中止（退出码 `1`），除非显式传 `--allow-partial`
- `check` / `list` / `albums` 打印警告并以退出码 `1` 结束，统计值标注为下限
- 回归测试见 `test_yike_export.py` 的【12】【13】两项

排错时若反复出现该警告，说明接口分页语义真的变了，需用 F12 对照网页端实际请求。

## 本地状态文件

下载目录下会生成：

| 文件 | 用途 |
|---|---|
| `.yike-state.json` | 每个 fsid 的状态（ok/failed）、落盘路径、MD5、大小。断点续传的依据 |
| `yike-export-report.json` | 最近一次运行的统计与失败明细 |
| `yike-inventory.jsonl` / `.csv` | `list` 子命令导出的完整清单 |

`.yike-state.json` 是隐藏文件，删除它会导致下次运行重新校验所有文件（但已存在且大小
一致的文件仍会被识别为完成，不会重复下载）。
