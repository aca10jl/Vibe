# 日志分析报告

**生成时间**: 2026-03-11 14:55:13
**错误总数**: 135

## 统计总览

### 按严重程度

| 严重程度 | 数量 |
|----------|------|
| FATAL | 24 |
| ERROR | 77 |
| WARN | 34 |

### 按分类

| 分类 | 数量 |
|------|------|
| crash | 21 |
| database | 19 |
| performance | 15 |
| security | 15 |
| severity | 13 |
| resource | 13 |
| exception | 9 |
| permission | 8 |
| process | 8 |
| service | 7 |
| network | 7 |

### 按文件

| 文件 | 错误数 |
|------|--------|
| `sample_app.log` | 135 |

## 错误时间线

| 时间 | 严重程度 | 分类 | 文件:行号 | 描述 |
|------|----------|------|-----------|------|
| 2024-06-15 08:00:25 | ERROR | exception | `sample_app.log:51` | 通用异常/错误标记 |
| 2024-06-15 08:00:37 | ERROR | permission | `sample_app.log:77` | 权限被拒绝 |
| 2024-06-15 08:00:50 | ERROR | process | `sample_app.log:104` | 工作进程异常退出 |
| 2024-06-15 08:01:52 | ERROR | process | `sample_app.log:227` | 工作进程异常退出 |
| 2024-06-15 08:01:54 | WARN | performance | `sample_app.log:232` | 操作超时 |
| 2024-06-15 08:02:01 | ERROR | process | `sample_app.log:246` | 工作进程异常退出 |
| 2024-06-15 08:02:05 | FATAL | severity | `sample_app.log:254` | 致命级别错误 |
| 2024-06-15 08:02:26 | ERROR | database | `sample_app.log:296` | 数据库复制延迟或失败 |
| 2024-06-15 08:02:33 | ERROR | security | `sample_app.log:310` | SSL 握手失败 |
| 2024-06-15 08:02:48 | WARN | performance | `sample_app.log:339` | 操作超时 |
| 2024-06-15 08:03:04 | ERROR | permission | `sample_app.log:372` | 权限被拒绝 |
| 2024-06-15 08:03:55 | WARN | performance | `sample_app.log:474` | 消息队列满/积压 |
| 2024-06-15 08:04:26 | ERROR | database | `sample_app.log:536` | 数据库连接错误 |
| 2024-06-15 08:05:28 | ERROR | database | `sample_app.log:660` | 数据库连接错误 |
| 2024-06-15 08:05:53 | WARN | security | `sample_app.log:709` | 认证失败 |
| 2024-06-15 08:06:13 | ERROR | crash | `sample_app.log:750` | 空指针异常 |
| 2024-06-15 08:06:32 | FATAL | crash | `sample_app.log:787` | 段错误 / 内存访问违规 |
| 2024-06-15 08:06:57 | ERROR | exception | `sample_app.log:838` | 通用异常/错误标记 |
| 2024-06-15 08:06:58 | ERROR | service | `sample_app.log:842` | 服务启动/停止失败 |
| 2024-06-15 08:06:59 | ERROR | network | `sample_app.log:844` | 连接异常（拒绝/重置/超时） |
| 2024-06-15 08:07:13 | FATAL | severity | `sample_app.log:872` | 致命级别错误 |
| 2024-06-15 08:07:41 | WARN | security | `sample_app.log:928` | 认证失败 |
| 2024-06-15 08:08:02 | ERROR | exception | `sample_app.log:969` | 通用异常/错误标记 |
| 2024-06-15 08:08:03 | ERROR | process | `sample_app.log:973` | 工作进程异常退出 |
| 2024-06-15 08:08:12 | ERROR | database | `sample_app.log:991` | 数据库连接错误 |
| 2024-06-15 08:08:29 | ERROR | crash | `sample_app.log:1025` | 空指针异常 |
| 2024-06-15 08:08:35 | ERROR | crash | `sample_app.log:1038` | 空指针异常 |
| 2024-06-15 08:08:52 | WARN | security | `sample_app.log:1071` | 认证失败 |
| 2024-06-15 08:08:53 | FATAL | severity | `sample_app.log:1074` | 致命级别错误 |
| 2024-06-15 08:09:28 | WARN | performance | `sample_app.log:1144` | 消息队列满/积压 |
| 2024-06-15 08:09:40 | FATAL | crash | `sample_app.log:1168` | 段错误 / 内存访问违规 |
| 2024-06-15 08:10:01 | FATAL | severity | `sample_app.log:1210` | 致命级别错误 |
| 2024-06-15 08:10:07 | FATAL | severity | `sample_app.log:1222` | 致命级别错误 |
| 2024-06-15 08:10:18 | ERROR | database | `sample_app.log:1243` | 数据库连接错误 |
| 2024-06-15 08:10:22 | WARN | performance | `sample_app.log:1252` | 消息队列满/积压 |
| 2024-06-15 08:11:05 | WARN | security | `sample_app.log:1338` | 认证失败 |
| 2024-06-15 08:11:15 | ERROR | service | `sample_app.log:1357` | 服务启动/停止失败 |
| 2024-06-15 08:11:15 | WARN | security | `sample_app.log:1358` | 认证失败 |
| 2024-06-15 08:12:07 | ERROR | permission | `sample_app.log:1461` | 权限被拒绝 |
| 2024-06-15 08:12:48 | WARN | performance | `sample_app.log:1543` | 操作超时 |
| 2024-06-15 08:12:48 | WARN | security | `sample_app.log:1544` | 认证失败 |
| 2024-06-15 08:13:07 | WARN | security | `sample_app.log:1581` | 认证失败 |
| 2024-06-15 08:13:13 | ERROR | service | `sample_app.log:1594` | 服务启动/停止失败 |
| 2024-06-15 08:13:18 | ERROR | crash | `sample_app.log:1604` | 空指针异常 |
| 2024-06-15 08:13:36 | FATAL | crash | `sample_app.log:1639` | 段错误 / 内存访问违规 |
| 2024-06-15 08:13:40 | ERROR | database | `sample_app.log:1648` | 数据库复制延迟或失败 |
| 2024-06-15 08:13:53 | ERROR | database | `sample_app.log:1674` | 数据库连接错误 |
| 2024-06-15 08:13:58 | ERROR | network | `sample_app.log:1684` | 连接异常（拒绝/重置/超时） |
| 2024-06-15 08:14:45 | ERROR | permission | `sample_app.log:1777` | 权限被拒绝 |
| 2024-06-15 08:15:16 | WARN | performance | `sample_app.log:1839` | 消息队列满/积压 |
| 2024-06-15 08:15:29 | ERROR | crash | `sample_app.log:1865` | 空指针异常 |
| 2024-06-15 08:15:59 | FATAL | crash | `sample_app.log:1925` | 段错误 / 内存访问违规 |
| 2024-06-15 08:16:10 | ERROR | database | `sample_app.log:1947` | 数据库连接错误 |
| 2024-06-15 08:16:42 | ERROR | crash | `sample_app.log:2011` | 空指针异常 |
| 2024-06-15 08:16:53 | ERROR | service | `sample_app.log:2034` | 服务启动/停止失败 |
| 2024-06-15 08:16:55 | WARN | performance | `sample_app.log:2038` | 消息队列满/积压 |
| 2024-06-15 08:17:03 | ERROR | database | `sample_app.log:2053` | 数据库复制延迟或失败 |
| 2024-06-15 08:17:03 | WARN | security | `sample_app.log:2054` | 认证失败 |
| 2024-06-15 08:17:49 | WARN | performance | `sample_app.log:2146` | 消息队列满/积压 |
| 2024-06-15 08:18:00 | ERROR | resource | `sample_app.log:2167` | 打开文件数超限 |
| 2024-06-15 08:18:19 | FATAL | severity | `sample_app.log:2206` | 致命级别错误 |
| 2024-06-15 08:18:25 | WARN | performance | `sample_app.log:2218` | 操作超时 |
| 2024-06-15 08:18:38 | ERROR | network | `sample_app.log:2243` | 连接异常（拒绝/重置/超时） |
| 2024-06-15 08:18:50 | WARN | resource | `sample_app.log:2267` | 磁盘使用率超过 90% |
| 2024-06-15 08:18:55 | ERROR | database | `sample_app.log:2277` | 数据库复制延迟或失败 |
| 2024-06-15 08:19:58 | ERROR | database | `sample_app.log:2403` | 数据库复制延迟或失败 |
| 2024-06-15 08:20:07 | ERROR | database | `sample_app.log:2421` | 数据库复制延迟或失败 |
| 2024-06-15 08:20:54 | ERROR | resource | `sample_app.log:2516` | 打开文件数超限 |
| 2024-06-15 08:21:01 | WARN | resource | `sample_app.log:2530` | 磁盘使用率超过 90% |
| 2024-06-15 08:21:06 | ERROR | process | `sample_app.log:2539` | 工作进程异常退出 |
| 2024-06-15 08:21:36 | ERROR | exception | `sample_app.log:2599` | 通用异常/错误标记 |
| 2024-06-15 08:23:05 | ERROR | database | `sample_app.log:2780` | 数据库连接错误 |
| 2024-06-15 08:23:17 | FATAL | severity | `sample_app.log:2803` | 致命级别错误 |
| 2024-06-15 08:24:18 | ERROR | exception | `sample_app.log:2925` | 通用异常/错误标记 |
| 2024-06-15 08:24:46 | ERROR | database | `sample_app.log:2983` | 数据库连接错误 |
| 2024-06-15 08:25:24 | ERROR | permission | `sample_app.log:3060` | 权限被拒绝 |
| 2024-06-15 08:25:28 | ERROR | network | `sample_app.log:3067` | 连接异常（拒绝/重置/超时） |
| 2024-06-15 08:25:29 | ERROR | database | `sample_app.log:3069` | 数据库连接错误 |
| 2024-06-15 08:26:00 | ERROR | network | `sample_app.log:3132` | 连接异常（拒绝/重置/超时） |
| 2024-06-15 08:26:12 | ERROR | security | `sample_app.log:3155` | SSL 握手失败 |
| 2024-06-15 08:26:33 | ERROR | network | `sample_app.log:3198` | 连接异常（拒绝/重置/超时） |
| 2024-06-15 08:26:36 | ERROR | crash | `sample_app.log:3203` | 空指针异常 |
| 2024-06-15 08:26:38 | FATAL | crash | `sample_app.log:3207` | 段错误 / 内存访问违规 |
| 2024-06-15 08:26:39 | ERROR | resource | `sample_app.log:3209` | 打开文件数超限 |
| 2024-06-15 08:26:42 | WARN | performance | `sample_app.log:3216` | 操作超时 |
| 2024-06-15 08:26:49 | WARN | performance | `sample_app.log:3230` | 操作超时 |
| 2024-06-15 08:26:55 | WARN | performance | `sample_app.log:3242` | 消息队列满/积压 |
| 2024-06-15 08:27:04 | ERROR | process | `sample_app.log:3259` | 工作进程异常退出 |
| 2024-06-15 08:27:23 | ERROR | service | `sample_app.log:3298` | 服务启动/停止失败 |
| 2024-06-15 08:27:26 | WARN | resource | `sample_app.log:3304` | 磁盘使用率超过 90% |
| 2024-06-15 08:27:36 | ERROR | process | `sample_app.log:3323` | 工作进程异常退出 |
| 2024-06-15 08:28:13 | ERROR | database | `sample_app.log:3398` | 数据库连接错误 |
| 2024-06-15 08:28:16 | ERROR | service | `sample_app.log:3404` | 服务启动/停止失败 |
| 2024-06-15 08:28:42 | WARN | security | `sample_app.log:3455` | 认证失败 |
| 2024-06-15 08:29:08 | FATAL | crash | `sample_app.log:3508` | 段错误 / 内存访问违规 |
| 2024-06-15 08:29:25 | ERROR | process | `sample_app.log:3541` | 工作进程异常退出 |
| 2024-06-15 08:29:50 | ERROR | permission | `sample_app.log:3591` | 权限被拒绝 |
| 2024-06-15 08:29:55 | FATAL | crash | `sample_app.log:3602` | 段错误 / 内存访问违规 |
| 2024-06-15 08:30:00 | FATAL | crash | `sample_app.log:3611` | 段错误 / 内存访问违规 |
| 2024-06-15 08:30:07 | WARN | resource | `sample_app.log:3625` | 磁盘使用率超过 90% |
| 2024-06-15 08:31:17 | WARN | security | `sample_app.log:3766` | 认证失败 |
| 2024-06-15 08:31:47 | WARN | resource | `sample_app.log:3826` | 磁盘使用率超过 90% |
| 2024-06-15 08:32:03 | ERROR | exception | `sample_app.log:3857` | 通用异常/错误标记 |
| 2024-06-15 08:32:06 | ERROR | resource | `sample_app.log:3866` | 打开文件数超限 |
| 2024-06-15 08:32:10 | FATAL | severity | `sample_app.log:3874` | 致命级别错误 |
| 2024-06-15 08:32:11 | WARN | performance | `sample_app.log:3875` | 操作超时 |
| 2024-06-15 08:32:15 | WARN | resource | `sample_app.log:3884` | 磁盘使用率超过 90% |
| 2024-06-15 08:32:41 | ERROR | exception | `sample_app.log:3936` | 通用异常/错误标记 |
| 2024-06-15 08:32:51 | ERROR | resource | `sample_app.log:3957` | 打开文件数超限 |
| 2024-06-15 08:33:01 | WARN | security | `sample_app.log:3977` | 认证失败 |
| 2024-06-15 08:33:16 | FATAL | crash | `sample_app.log:4007` | 段错误 / 内存访问违规 |
| 2024-06-15 08:33:47 | FATAL | severity | `sample_app.log:4070` | 致命级别错误 |
| 2024-06-15 08:34:21 | ERROR | service | `sample_app.log:4137` | 服务启动/停止失败 |
| 2024-06-15 08:34:31 | FATAL | severity | `sample_app.log:4157` | 致命级别错误 |
| 2024-06-15 08:35:16 | FATAL | crash | `sample_app.log:4248` | 段错误 / 内存访问违规 |
| 2024-06-15 08:35:18 | ERROR | resource | `sample_app.log:4251` | 打开文件数超限 |
| 2024-06-15 08:35:27 | ERROR | crash | `sample_app.log:4269` | 空指针异常 |
| 2024-06-15 08:35:27 | ERROR | exception | `sample_app.log:4270` | 通用异常/错误标记 |
| 2024-06-15 08:35:45 | FATAL | severity | `sample_app.log:4307` | 致命级别错误 |
| 2024-06-15 08:36:08 | WARN | security | `sample_app.log:4353` | 认证失败 |
| 2024-06-15 08:36:16 | ERROR | resource | `sample_app.log:4369` | 打开文件数超限 |
| 2024-06-15 08:37:16 | ERROR | database | `sample_app.log:4489` | 数据库连接错误 |
| 2024-06-15 08:37:20 | ERROR | exception | `sample_app.log:4498` | 通用异常/错误标记 |
| 2024-06-15 08:37:40 | WARN | security | `sample_app.log:4539` | 认证失败 |
| 2024-06-15 08:38:12 | ERROR | permission | `sample_app.log:4603` | 权限被拒绝 |
| 2024-06-15 08:38:13 | FATAL | crash | `sample_app.log:4605` | 段错误 / 内存访问违规 |
| 2024-06-15 08:38:28 | FATAL | severity | `sample_app.log:4636` | 致命级别错误 |
| 2024-06-15 08:39:17 | ERROR | database | `sample_app.log:4734` | 数据库连接错误 |
| 2024-06-15 08:39:28 | ERROR | database | `sample_app.log:4755` | 数据库连接错误 |
| 2024-06-15 08:39:34 | WARN | performance | `sample_app.log:4767` | 消息队列满/积压 |
| 2024-06-15 08:39:35 | FATAL | severity | `sample_app.log:4770` | 致命级别错误 |
| 2024-06-15 08:39:51 | ERROR | crash | `sample_app.log:4801` | 空指针异常 |
| 2024-06-15 08:39:52 | ERROR | network | `sample_app.log:4804` | 连接异常（拒绝/重置/超时） |
| 2024-06-15 08:40:19 | ERROR | crash | `sample_app.log:4857` | 空指针异常 |
| 2024-06-15 08:40:33 | ERROR | permission | `sample_app.log:4885` | 权限被拒绝 |

## 错误详情

### 1. [ERROR] 通用异常/错误标记

- **文件**: `sample_app.log:51`
- **时间**: 2024-06-15 08:00:25
- **匹配规则**: `(?i)(?:Exception|Error|Traceback)\s*[:(\[]`
- **匹配内容**: `Traceback (`
- **分类**: exception

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:00:22.662] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:00:23.013] INFO Cache hit ratio: 66%
  [2024-06-15 08:00:23.743] INFO API response sent: 200 OK
  [2024-06-15 08:00:24.400] INFO Request handled successfully in 72ms
  [2024-06-15 08:00:24.888] INFO Cache hit ratio: 74%
>> [2024-06-15 08:00:25.442] ERROR Traceback (most recent call last):
    File "/app/handlers/order.py", line 89
      raise ValueError("Invalid order state transition")
  [2024-06-15 08:00:25.786] INFO Database query completed in 157ms
  [2024-06-15 08:00:26.418] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:00:26.532] INFO Connection pool stats: active=5 idle=15 total=20
```
</details>

---

### 2. [ERROR] 权限被拒绝

- **文件**: `sample_app.log:77`
- **时间**: 2024-06-15 08:00:37
- **匹配规则**: `(?i)permission\s+denied|access\s+denied|EACCES`
- **匹配内容**: `permission denied`
- **分类**: permission

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:00:34.578] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:00:35.243] INFO Health check passed
  [2024-06-15 08:00:35.740] INFO API response sent: 200 OK
  [2024-06-15 08:00:36.304] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:00:36.980] INFO Scheduled task completed: cleanup_sessions
>> [2024-06-15 08:00:37.183] ERROR permission denied: cannot write to /var/log/app/audit.log - check file ownership
  [2024-06-15 08:00:37.992] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:00:38.151] INFO API response sent: 200 OK
  [2024-06-15 08:00:38.826] INFO Database query completed in 167ms
  [2024-06-15 08:00:39.350] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:00:39.985] INFO User bob logged in from 192.168.1.100
```
</details>

---

### 3. [ERROR] 工作进程异常退出

- **文件**: `sample_app.log:104`
- **时间**: 2024-06-15 08:00:50
- **匹配规则**: `(?i)worker.*process.*exit|child process.*died`
- **匹配内容**: `worker process exit`
- **分类**: process

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:00:48.182] INFO Database query completed in 66ms
  [2024-06-15 08:00:48.615] INFO Health check passed
  [2024-06-15 08:00:49.349] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:00:49.777] INFO User bob logged in from 10.0.1.20
  [2024-06-15 08:00:50.107] DEBUG Processing message from queue
>> [2024-06-15 08:00:50.824] ERROR worker process exit with code 137 (SIGKILL) - possible OOM kill
  [2024-06-15 08:00:51.113] INFO API response sent: 200 OK
  [2024-06-15 08:00:51.898] DEBUG Processing message from queue
  [2024-06-15 08:00:52.338] INFO User charlie logged in from 10.0.1.10
  [2024-06-15 08:00:52.699] INFO Database query completed in 214ms
  [2024-06-15 08:00:53.072] INFO Connection pool stats: active=5 idle=15 total=20
```
</details>

---

### 4. [ERROR] 工作进程异常退出

- **文件**: `sample_app.log:227`
- **时间**: 2024-06-15 08:01:52
- **匹配规则**: `(?i)worker.*process.*exit|child process.*died`
- **匹配内容**: `worker process exit`
- **分类**: process

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:01:49.633] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:01:50.026] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:01:50.698] INFO Health check passed
  [2024-06-15 08:01:51.285] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:01:51.842] DEBUG Loading configuration from /etc/app/config.yaml
>> [2024-06-15 08:01:52.224] ERROR worker process exit with code 137 (SIGKILL) - possible OOM kill
  [2024-06-15 08:01:52.760] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:01:53.146] INFO Database query completed in 258ms
  [2024-06-15 08:01:53.683] INFO Cache hit ratio: 70%
  [2024-06-15 08:01:54.035] DEBUG Processing message from queue
  [2024-06-15 08:01:54.924] WARN timeout waiting for response from upstream service payment-api after 30s
```
</details>

---

### 5. [WARN] 操作超时

- **文件**: `sample_app.log:232`
- **时间**: 2024-06-15 08:01:54
- **匹配规则**: `(?i)timeout|timed?\s*out`
- **匹配内容**: `timeout`
- **分类**: performance

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:01:52.224] ERROR worker process exit with code 137 (SIGKILL) - possible OOM kill
  [2024-06-15 08:01:52.760] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:01:53.146] INFO Database query completed in 258ms
  [2024-06-15 08:01:53.683] INFO Cache hit ratio: 70%
  [2024-06-15 08:01:54.035] DEBUG Processing message from queue
>> [2024-06-15 08:01:54.924] WARN timeout waiting for response from upstream service payment-api after 30s
  [2024-06-15 08:01:55.184] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:01:55.766] INFO Health check passed
  [2024-06-15 08:01:56.047] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:01:56.961] INFO Cache hit ratio: 62%
  [2024-06-15 08:01:57.132] DEBUG Processing message from queue
```
</details>

---

### 6. [ERROR] 工作进程异常退出

- **文件**: `sample_app.log:246`
- **时间**: 2024-06-15 08:02:01
- **匹配规则**: `(?i)worker.*process.*exit|child process.*died`
- **匹配内容**: `worker process exit`
- **分类**: process

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:01:59.466] INFO Database query completed in 22ms
  [2024-06-15 08:01:59.861] INFO Database query completed in 50ms
  [2024-06-15 08:02:00.327] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:02:00.835] INFO Health check passed
  [2024-06-15 08:02:01.205] INFO User alice logged in from 10.0.1.20
>> [2024-06-15 08:02:01.878] ERROR worker process exit with code 137 (SIGKILL) - possible OOM kill
  [2024-06-15 08:02:02.023] INFO Health check passed
  [2024-06-15 08:02:02.862] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:02:03.408] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:02:03.634] INFO Request handled successfully in 440ms
  [2024-06-15 08:02:04.349] INFO API response sent: 200 OK
```
</details>

---

### 7. [FATAL] 致命级别错误

- **文件**: `sample_app.log:254`
- **时间**: 2024-06-15 08:02:05
- **匹配规则**: `(?i)\b(FATAL|PANIC|CRITICAL)\b`
- **匹配内容**: `CRITICAL`
- **分类**: severity

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:02:03.408] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:02:03.634] INFO Request handled successfully in 440ms
  [2024-06-15 08:02:04.349] INFO API response sent: 200 OK
  [2024-06-15 08:02:04.503] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:02:05.053] INFO Health check passed
>> [2024-06-15 08:02:05.602] CRITICAL deadlock detected between thread-pool-3 and thread-pool-7 on resource lock-orders-table
  [2024-06-15 08:02:06.220] INFO API response sent: 200 OK
  [2024-06-15 08:02:06.657] INFO User bob logged in from 192.168.1.100
  [2024-06-15 08:02:07.217] INFO Health check passed
  [2024-06-15 08:02:07.667] INFO Request handled successfully in 141ms
  [2024-06-15 08:02:08.451] INFO Database query completed in 382ms
```
</details>

---

### 8. [ERROR] 数据库复制延迟或失败

- **文件**: `sample_app.log:296`
- **时间**: 2024-06-15 08:02:26
- **匹配规则**: `(?i)replication.*(lag|behind|fail)`
- **匹配内容**: `replication lag detected: slave is 120 seconds behind`
- **分类**: database

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:02:24.334] INFO Cache hit ratio: 71%
  [2024-06-15 08:02:24.818] INFO User charlie logged in from 10.0.1.20
  [2024-06-15 08:02:25.386] INFO Health check passed
  [2024-06-15 08:02:25.647] DEBUG Processing message from queue
  [2024-06-15 08:02:26.320] INFO User alice logged in from 172.16.0.5
>> [2024-06-15 08:02:26.527] ERROR replication lag detected: slave is 120 seconds behind master
  [2024-06-15 08:02:27.229] INFO Cache hit ratio: 77%
  [2024-06-15 08:02:27.554] INFO Request handled successfully in 61ms
  [2024-06-15 08:02:28.274] INFO User alice logged in from 10.0.1.20
  [2024-06-15 08:02:28.960] DEBUG Processing message from queue
  [2024-06-15 08:02:29.005] INFO Health check passed
```
</details>

---

### 9. [ERROR] SSL 握手失败

- **文件**: `sample_app.log:310`
- **时间**: 2024-06-15 08:02:33
- **匹配规则**: `(?i)SSL.*handshake.*(fail|error)`
- **匹配内容**: `SSL handshake fail`
- **分类**: security

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:02:31.142] INFO Request handled successfully in 414ms
  [2024-06-15 08:02:31.643] INFO API response sent: 200 OK
  [2024-06-15 08:02:32.233] INFO Database query completed in 454ms
  [2024-06-15 08:02:32.907] INFO Database query completed in 80ms
  [2024-06-15 08:02:33.295] INFO Cache hit ratio: 88%
>> [2024-06-15 08:02:33.726] ERROR SSL handshake failed: certificate expired on 2024-12-31
  [2024-06-15 08:02:34.386] DEBUG Processing message from queue
  [2024-06-15 08:02:34.938] INFO Request handled successfully in 129ms
  [2024-06-15 08:02:35.268] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:02:35.667] INFO Request handled successfully in 354ms
  [2024-06-15 08:02:36.415] INFO Scheduled task completed: cleanup_sessions
```
</details>

---

### 10. [WARN] 操作超时

- **文件**: `sample_app.log:339`
- **时间**: 2024-06-15 08:02:48
- **匹配规则**: `(?i)timeout|timed?\s*out`
- **匹配内容**: `timeout`
- **分类**: performance

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:02:45.551] INFO Cache hit ratio: 62%
  [2024-06-15 08:02:46.467] INFO Request handled successfully in 385ms
  [2024-06-15 08:02:46.828] INFO Cache hit ratio: 85%
  [2024-06-15 08:02:47.271] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:02:47.855] INFO Health check passed
>> [2024-06-15 08:02:48.141] WARN timeout waiting for response from upstream service payment-api after 30s
  [2024-06-15 08:02:48.528] INFO API response sent: 200 OK
  [2024-06-15 08:02:49.087] DEBUG Processing message from queue
  [2024-06-15 08:02:49.757] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:02:50.143] INFO API response sent: 200 OK
  [2024-06-15 08:02:50.795] INFO Health check passed
```
</details>

---

### 11. [ERROR] 权限被拒绝

- **文件**: `sample_app.log:372`
- **时间**: 2024-06-15 08:03:04
- **匹配规则**: `(?i)permission\s+denied|access\s+denied|EACCES`
- **匹配内容**: `permission denied`
- **分类**: permission

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:03:02.465] INFO Health check passed
  [2024-06-15 08:03:02.532] INFO Cache hit ratio: 87%
  [2024-06-15 08:03:03.032] INFO Health check passed
  [2024-06-15 08:03:03.649] INFO Health check passed
  [2024-06-15 08:03:04.032] INFO Database query completed in 360ms
>> [2024-06-15 08:03:04.894] ERROR permission denied: cannot write to /var/log/app/audit.log - check file ownership
  [2024-06-15 08:03:05.210] INFO User alice logged in from 10.0.1.10
  [2024-06-15 08:03:05.673] INFO User charlie logged in from 10.0.1.20
  [2024-06-15 08:03:06.101] INFO User diana logged in from 10.0.1.20
  [2024-06-15 08:03:06.873] INFO API response sent: 200 OK
  [2024-06-15 08:03:07.423] INFO Database query completed in 105ms
```
</details>

---

### 12. [WARN] 消息队列满/积压

- **文件**: `sample_app.log:474`
- **时间**: 2024-06-15 08:03:55
- **匹配规则**: `(?i)queue.*full|backlog.*exceeded`
- **匹配内容**: `queue full`
- **分类**: performance

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:03:53.366] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:03:53.636] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:03:54.112] DEBUG Processing message from queue
  [2024-06-15 08:03:54.873] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:03:55.288] DEBUG Loading configuration from /etc/app/config.yaml
>> [2024-06-15 08:03:55.733] WARN queue full: message-broker backlog exceeded 10000 messages
  [2024-06-15 08:03:56.259] INFO Database query completed in 9ms
  [2024-06-15 08:03:56.714] INFO Database query completed in 331ms
  [2024-06-15 08:03:57.481] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:03:57.839] INFO Cache hit ratio: 90%
  [2024-06-15 08:03:58.414] INFO Connection pool stats: active=5 idle=15 total=20
```
</details>

---

### 13. [ERROR] 数据库连接错误

- **文件**: `sample_app.log:536`
- **时间**: 2024-06-15 08:04:26
- **匹配规则**: `(?i)ERROR.*database.*connection`
- **匹配内容**: `ERROR database connection refused: Connection`
- **分类**: database

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:04:24.298] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:04:24.795] DEBUG Processing message from queue
  [2024-06-15 08:04:25.274] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:04:25.850] INFO User diana logged in from 172.16.0.5
  [2024-06-15 08:04:26.175] INFO Request handled successfully in 113ms
>> [2024-06-15 08:04:26.788] ERROR database connection refused: Connection timed out after 30000ms to db-primary:5432
  [2024-06-15 08:04:27.241] INFO User eve logged in from 192.168.1.100
  [2024-06-15 08:04:27.950] INFO Cache hit ratio: 63%
  [2024-06-15 08:04:28.114] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:04:28.610] DEBUG Processing message from queue
  [2024-06-15 08:04:29.430] INFO Scheduled task completed: cleanup_sessions
```
</details>

---

### 14. [ERROR] 数据库连接错误

- **文件**: `sample_app.log:660`
- **时间**: 2024-06-15 08:05:28
- **匹配规则**: `(?i)ERROR.*database.*connection`
- **匹配内容**: `ERROR database connection refused: Connection`
- **分类**: database

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:05:26.158] INFO Health check passed
  [2024-06-15 08:05:26.915] INFO Cache hit ratio: 95%
  [2024-06-15 08:05:27.277] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:05:27.673] INFO Cache hit ratio: 85%
  [2024-06-15 08:05:28.282] DEBUG Processing message from queue
>> [2024-06-15 08:05:28.631] ERROR database connection refused: Connection timed out after 30000ms to db-primary:5432
  [2024-06-15 08:05:29.259] INFO Cache hit ratio: 94%
  [2024-06-15 08:05:29.622] INFO API response sent: 200 OK
  [2024-06-15 08:05:30.011] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:05:30.607] INFO Health check passed
  [2024-06-15 08:05:31.465] INFO API response sent: 200 OK
```
</details>

---

### 15. [WARN] 认证失败

- **文件**: `sample_app.log:709`
- **时间**: 2024-06-15 08:05:53
- **匹配规则**: `(?i)authentication (fail|error|denied)`
- **匹配内容**: `authentication fail`
- **分类**: security

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:05:50.655] DEBUG Processing message from queue
  [2024-06-15 08:05:51.317] INFO Health check passed
  [2024-06-15 08:05:51.648] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:05:52.074] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:05:52.588] INFO Database query completed in 161ms
>> [2024-06-15 08:05:53.257] ERROR authentication failed for user admin from 192.168.1.100 - 5 consecutive failures
  [2024-06-15 08:05:53.527] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:05:54.088] INFO Database query completed in 217ms
  [2024-06-15 08:05:54.614] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:05:55.156] INFO Database query completed in 196ms
  [2024-06-15 08:05:55.776] INFO User bob logged in from 10.0.1.10
```
</details>

---

### 16. [ERROR] 空指针异常

- **文件**: `sample_app.log:750`
- **时间**: 2024-06-15 08:06:13
- **匹配规则**: `(?i)(null\s*pointer|NullPointerException|nullptr|nil\s+pointer)`
- **匹配内容**: `NullPointer`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:06:11.484] INFO Request handled successfully in 327ms
  [2024-06-15 08:06:11.914] INFO Health check passed
  [2024-06-15 08:06:12.325] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:06:12.695] INFO User alice logged in from 10.0.1.10
  [2024-06-15 08:06:13.473] INFO Request handled successfully in 400ms
>> [2024-06-15 08:06:13.935] ERROR NullPointerException: Cannot invoke method on null object at com.app.service.UserService.getUser(UserService.java:142)
  [2024-06-15 08:06:14.106] INFO Request handled successfully in 181ms
  [2024-06-15 08:06:14.827] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:06:15.184] INFO API response sent: 200 OK
  [2024-06-15 08:06:15.593] INFO Database query completed in 84ms
  [2024-06-15 08:06:16.470] INFO User charlie logged in from 192.168.1.100
```
</details>

---

### 17. [FATAL] 段错误 / 内存访问违规

- **文件**: `sample_app.log:787`
- **时间**: 2024-06-15 08:06:32
- **匹配规则**: `(?i)segmentation\s+fault|segfault|SIGSEGV`
- **匹配内容**: `segmentation fault`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:06:29.754] INFO API response sent: 200 OK
  [2024-06-15 08:06:30.146] INFO Cache hit ratio: 91%
  [2024-06-15 08:06:30.717] INFO Database query completed in 82ms
  [2024-06-15 08:06:31.325] INFO Health check passed
  [2024-06-15 08:06:31.992] INFO Request handled successfully in 155ms
>> [2024-06-15 08:06:32.075] ERROR segmentation fault in module libcrypto.so.1.1 at address 0x7f3a2b4c1000
  [2024-06-15 08:06:32.821] INFO Database query completed in 343ms
  [2024-06-15 08:06:33.475] INFO Database query completed in 247ms
  [2024-06-15 08:06:33.576] INFO Database query completed in 85ms
  [2024-06-15 08:06:34.415] INFO Request handled successfully in 277ms
  [2024-06-15 08:06:34.889] INFO Request handled successfully in 111ms
```
</details>

---

### 18. [ERROR] 通用异常/错误标记

- **文件**: `sample_app.log:838`
- **时间**: 2024-06-15 08:06:57
- **匹配规则**: `(?i)(?:Exception|Error|Traceback)\s*[:(\[]`
- **匹配内容**: `Traceback (`
- **分类**: exception

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:06:55.284] INFO Health check passed
  [2024-06-15 08:06:55.966] INFO API response sent: 200 OK
  [2024-06-15 08:06:56.196] INFO User bob logged in from 172.16.0.5
  [2024-06-15 08:06:56.623] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:06:57.082] INFO Connection pool stats: active=5 idle=15 total=20
>> [2024-06-15 08:06:57.963] ERROR Traceback (most recent call last):
    File "/app/handlers/order.py", line 89
      raise ValueError("Invalid order state transition")
  [2024-06-15 08:06:58.138] DEBUG Processing message from queue
  [2024-06-15 08:06:58.779] ERROR failed to start service nginx: port 443 already in use by pid 12847
  [2024-06-15 08:06:59.458] DEBUG Loading configuration from /etc/app/config.yaml
```
</details>

---

### 19. [ERROR] 服务启动/停止失败

- **文件**: `sample_app.log:842`
- **时间**: 2024-06-15 08:06:58
- **匹配规则**: `(?i)failed to (start|stop|restart) service`
- **匹配内容**: `failed to start service`
- **分类**: service

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:06:57.082] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:06:57.963] ERROR Traceback (most recent call last):
    File "/app/handlers/order.py", line 89
      raise ValueError("Invalid order state transition")
  [2024-06-15 08:06:58.138] DEBUG Processing message from queue
>> [2024-06-15 08:06:58.779] ERROR failed to start service nginx: port 443 already in use by pid 12847
  [2024-06-15 08:06:59.458] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:06:59.687] ERROR connection reset by peer: 10.0.1.50:8080 - possible network partition
  [2024-06-15 08:07:00.154] INFO Database query completed in 241ms
  [2024-06-15 08:07:00.781] INFO Cache hit ratio: 76%
  [2024-06-15 08:07:01.434] INFO Request handled successfully in 355ms
```
</details>

---

### 20. [ERROR] 连接异常（拒绝/重置/超时）

- **文件**: `sample_app.log:844`
- **时间**: 2024-06-15 08:06:59
- **匹配规则**: `(?i)connection\s+(refused|reset|timed?\s*out)|ECONNREFUSED|ECONNRESET|ETIMEDOUT`
- **匹配内容**: `connection reset`
- **分类**: network

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
    File "/app/handlers/order.py", line 89
      raise ValueError("Invalid order state transition")
  [2024-06-15 08:06:58.138] DEBUG Processing message from queue
  [2024-06-15 08:06:58.779] ERROR failed to start service nginx: port 443 already in use by pid 12847
  [2024-06-15 08:06:59.458] DEBUG Loading configuration from /etc/app/config.yaml
>> [2024-06-15 08:06:59.687] ERROR connection reset by peer: 10.0.1.50:8080 - possible network partition
  [2024-06-15 08:07:00.154] INFO Database query completed in 241ms
  [2024-06-15 08:07:00.781] INFO Cache hit ratio: 76%
  [2024-06-15 08:07:01.434] INFO Request handled successfully in 355ms
  [2024-06-15 08:07:01.553] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:07:02.201] INFO Request handled successfully in 390ms
```
</details>

---

### 21. [FATAL] 致命级别错误

- **文件**: `sample_app.log:872`
- **时间**: 2024-06-15 08:07:13
- **匹配规则**: `(?i)\b(FATAL|PANIC|CRITICAL)\b`
- **匹配内容**: `FATAL`
- **分类**: severity

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:07:11.463] INFO Cache hit ratio: 94%
  [2024-06-15 08:07:11.507] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:07:12.017] INFO Request handled successfully in 59ms
  [2024-06-15 08:07:12.868] INFO API response sent: 200 OK
  [2024-06-15 08:07:13.076] INFO Cache hit ratio: 70%
>> [2024-06-15 08:07:13.523] FATAL Out of memory: Java heap space - requested 512MB, available 128MB
  [2024-06-15 08:07:14.172] INFO Request handled successfully in 257ms
  [2024-06-15 08:07:14.749] DEBUG Processing message from queue
  [2024-06-15 08:07:15.034] INFO Database query completed in 71ms
  [2024-06-15 08:07:15.508] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:07:16.075] DEBUG Processing message from queue
```
</details>

---

### 22. [WARN] 认证失败

- **文件**: `sample_app.log:928`
- **时间**: 2024-06-15 08:07:41
- **匹配规则**: `(?i)authentication (fail|error|denied)`
- **匹配内容**: `authentication fail`
- **分类**: security

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:07:39.084] DEBUG Processing message from queue
  [2024-06-15 08:07:39.872] INFO Database query completed in 461ms
  [2024-06-15 08:07:40.322] INFO Request handled successfully in 436ms
  [2024-06-15 08:07:40.816] INFO Cache hit ratio: 97%
  [2024-06-15 08:07:41.186] INFO Health check passed
>> [2024-06-15 08:07:41.733] ERROR authentication failed for user admin from 192.168.1.100 - 5 consecutive failures
  [2024-06-15 08:07:42.477] INFO API response sent: 200 OK
  [2024-06-15 08:07:42.904] DEBUG Processing message from queue
  [2024-06-15 08:07:43.485] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:07:43.993] INFO Database query completed in 200ms
  [2024-06-15 08:07:44.230] INFO Connection pool stats: active=5 idle=15 total=20
```
</details>

---

### 23. [ERROR] 通用异常/错误标记

- **文件**: `sample_app.log:969`
- **时间**: 2024-06-15 08:08:02
- **匹配规则**: `(?i)(?:Exception|Error|Traceback)\s*[:(\[]`
- **匹配内容**: `Traceback (`
- **分类**: exception

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:07:59.546] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:08:00.352] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:08:00.867] INFO Request handled successfully in 245ms
  [2024-06-15 08:08:01.124] INFO Request handled successfully in 498ms
  [2024-06-15 08:08:01.628] INFO Cache hit ratio: 86%
>> [2024-06-15 08:08:02.389] ERROR Traceback (most recent call last):
    File "/app/handlers/order.py", line 89
      raise ValueError("Invalid order state transition")
  [2024-06-15 08:08:02.737] INFO Health check passed
  [2024-06-15 08:08:03.366] ERROR worker process exit with code 137 (SIGKILL) - possible OOM kill
  [2024-06-15 08:08:03.515] INFO Scheduled task completed: cleanup_sessions
```
</details>

---

### 24. [ERROR] 工作进程异常退出

- **文件**: `sample_app.log:973`
- **时间**: 2024-06-15 08:08:03
- **匹配规则**: `(?i)worker.*process.*exit|child process.*died`
- **匹配内容**: `worker process exit`
- **分类**: process

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:08:01.628] INFO Cache hit ratio: 86%
  [2024-06-15 08:08:02.389] ERROR Traceback (most recent call last):
    File "/app/handlers/order.py", line 89
      raise ValueError("Invalid order state transition")
  [2024-06-15 08:08:02.737] INFO Health check passed
>> [2024-06-15 08:08:03.366] ERROR worker process exit with code 137 (SIGKILL) - possible OOM kill
  [2024-06-15 08:08:03.515] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:08:04.469] INFO Request handled successfully in 379ms
  [2024-06-15 08:08:04.986] INFO Request handled successfully in 480ms
  [2024-06-15 08:08:05.044] INFO User eve logged in from 192.168.1.100
  [2024-06-15 08:08:05.505] INFO Database query completed in 64ms
```
</details>

---

### 25. [ERROR] 数据库连接错误

- **文件**: `sample_app.log:991`
- **时间**: 2024-06-15 08:08:12
- **匹配规则**: `(?i)ERROR.*database.*connection`
- **匹配内容**: `ERROR database connection refused: Connection`
- **分类**: database

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:08:09.813] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:08:10.456] INFO Cache hit ratio: 99%
  [2024-06-15 08:08:10.618] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:08:11.285] DEBUG Processing message from queue
  [2024-06-15 08:08:11.799] INFO Scheduled task completed: cleanup_sessions
>> [2024-06-15 08:08:12.192] ERROR database connection refused: Connection timed out after 30000ms to db-primary:5432
  [2024-06-15 08:08:12.568] INFO API response sent: 200 OK
  [2024-06-15 08:08:13.298] INFO Cache hit ratio: 93%
  [2024-06-15 08:08:13.524] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:08:14.457] INFO User bob logged in from 10.0.1.10
  [2024-06-15 08:08:14.903] INFO Cache hit ratio: 72%
```
</details>

---

### 26. [ERROR] 空指针异常

- **文件**: `sample_app.log:1025`
- **时间**: 2024-06-15 08:08:29
- **匹配规则**: `(?i)(null\s*pointer|NullPointerException|nullptr|nil\s+pointer)`
- **匹配内容**: `NullPointer`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:08:26.729] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:08:27.129] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:08:27.916] INFO Health check passed
  [2024-06-15 08:08:28.253] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:08:28.944] INFO Database query completed in 146ms
>> [2024-06-15 08:08:29.374] ERROR NullPointerException: Cannot invoke method on null object at com.app.service.UserService.getUser(UserService.java:142)
  [2024-06-15 08:08:29.796] INFO Request handled successfully in 367ms
  [2024-06-15 08:08:30.077] INFO Health check passed
  [2024-06-15 08:08:30.635] INFO Request handled successfully in 440ms
  [2024-06-15 08:08:31.385] INFO Database query completed in 216ms
  [2024-06-15 08:08:31.730] INFO Cache hit ratio: 76%
```
</details>

---

### 27. [ERROR] 空指针异常

- **文件**: `sample_app.log:1038`
- **时间**: 2024-06-15 08:08:35
- **匹配规则**: `(?i)(null\s*pointer|NullPointerException|nullptr|nil\s+pointer)`
- **匹配内容**: `NullPointer`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:08:33.302] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:08:33.665] INFO Cache hit ratio: 83%
  [2024-06-15 08:08:34.255] INFO API response sent: 200 OK
  [2024-06-15 08:08:34.756] INFO Database query completed in 125ms
  [2024-06-15 08:08:35.044] DEBUG Loading configuration from /etc/app/config.yaml
>> [2024-06-15 08:08:35.943] ERROR NullPointerException: Cannot invoke method on null object at com.app.service.UserService.getUser(UserService.java:142)
  [2024-06-15 08:08:36.337] INFO User diana logged in from 10.0.1.10
  [2024-06-15 08:08:36.767] INFO API response sent: 200 OK
  [2024-06-15 08:08:37.283] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:08:37.584] DEBUG Processing message from queue
  [2024-06-15 08:08:38.451] INFO Cache hit ratio: 85%
```
</details>

---

### 28. [WARN] 认证失败

- **文件**: `sample_app.log:1071`
- **时间**: 2024-06-15 08:08:52
- **匹配规则**: `(?i)authentication (fail|error|denied)`
- **匹配内容**: `authentication fail`
- **分类**: security

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:08:49.822] INFO API response sent: 200 OK
  [2024-06-15 08:08:50.344] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:08:50.817] INFO Request handled successfully in 62ms
  [2024-06-15 08:08:51.348] INFO Database query completed in 485ms
  [2024-06-15 08:08:51.830] INFO Database query completed in 455ms
>> [2024-06-15 08:08:52.090] ERROR authentication failed for user admin from 192.168.1.100 - 5 consecutive failures
  [2024-06-15 08:08:52.585] INFO Database query completed in 119ms
  [2024-06-15 08:08:53.286] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:08:53.776] CRITICAL deadlock detected between thread-pool-3 and thread-pool-7 on resource lock-orders-table
  [2024-06-15 08:08:54.086] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:08:54.591] INFO API response sent: 200 OK
```
</details>

---

### 29. [FATAL] 致命级别错误

- **文件**: `sample_app.log:1074`
- **时间**: 2024-06-15 08:08:53
- **匹配规则**: `(?i)\b(FATAL|PANIC|CRITICAL)\b`
- **匹配内容**: `CRITICAL`
- **分类**: severity

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:08:51.348] INFO Database query completed in 485ms
  [2024-06-15 08:08:51.830] INFO Database query completed in 455ms
  [2024-06-15 08:08:52.090] ERROR authentication failed for user admin from 192.168.1.100 - 5 consecutive failures
  [2024-06-15 08:08:52.585] INFO Database query completed in 119ms
  [2024-06-15 08:08:53.286] INFO Connection pool stats: active=5 idle=15 total=20
>> [2024-06-15 08:08:53.776] CRITICAL deadlock detected between thread-pool-3 and thread-pool-7 on resource lock-orders-table
  [2024-06-15 08:08:54.086] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:08:54.591] INFO API response sent: 200 OK
  [2024-06-15 08:08:55.207] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:08:55.828] INFO API response sent: 200 OK
  [2024-06-15 08:08:56.208] DEBUG Processing message from queue
```
</details>

---

### 30. [WARN] 消息队列满/积压

- **文件**: `sample_app.log:1144`
- **时间**: 2024-06-15 08:09:28
- **匹配规则**: `(?i)queue.*full|backlog.*exceeded`
- **匹配内容**: `queue full`
- **分类**: performance

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:09:26.313] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:09:26.667] INFO Database query completed in 349ms
  [2024-06-15 08:09:27.218] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:09:27.738] INFO User eve logged in from 192.168.1.100
  [2024-06-15 08:09:28.331] INFO Health check passed
>> [2024-06-15 08:09:28.989] WARN queue full: message-broker backlog exceeded 10000 messages
  [2024-06-15 08:09:29.075] INFO Request handled successfully in 352ms
  [2024-06-15 08:09:29.704] INFO API response sent: 200 OK
  [2024-06-15 08:09:30.081] INFO API response sent: 200 OK
  [2024-06-15 08:09:30.843] INFO Request handled successfully in 127ms
  [2024-06-15 08:09:31.334] INFO API response sent: 200 OK
```
</details>

---

### 31. [FATAL] 段错误 / 内存访问违规

- **文件**: `sample_app.log:1168`
- **时间**: 2024-06-15 08:09:40
- **匹配规则**: `(?i)segmentation\s+fault|segfault|SIGSEGV`
- **匹配内容**: `segmentation fault`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:09:38.241] INFO Database query completed in 62ms
  [2024-06-15 08:09:38.770] INFO API response sent: 200 OK
  [2024-06-15 08:09:39.029] INFO User diana logged in from 192.168.1.100
  [2024-06-15 08:09:39.829] INFO Cache hit ratio: 99%
  [2024-06-15 08:09:40.013] INFO User eve logged in from 172.16.0.5
>> [2024-06-15 08:09:40.545] ERROR segmentation fault in module libcrypto.so.1.1 at address 0x7f3a2b4c1000
  [2024-06-15 08:09:41.395] DEBUG Processing message from queue
  [2024-06-15 08:09:41.909] INFO Request handled successfully in 381ms
  [2024-06-15 08:09:42.365] INFO User diana logged in from 172.16.0.5
  [2024-06-15 08:09:42.947] INFO Database query completed in 380ms
  [2024-06-15 08:09:43.275] INFO Database query completed in 165ms
```
</details>

---

### 32. [FATAL] 致命级别错误

- **文件**: `sample_app.log:1210`
- **时间**: 2024-06-15 08:10:01
- **匹配规则**: `(?i)\b(FATAL|PANIC|CRITICAL)\b`
- **匹配内容**: `FATAL`
- **分类**: severity

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:09:59.016] INFO Database query completed in 284ms
  [2024-06-15 08:09:59.748] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:10:00.109] INFO Database query completed in 328ms
  [2024-06-15 08:10:00.849] INFO Database query completed in 400ms
  [2024-06-15 08:10:01.046] INFO Connection pool stats: active=5 idle=15 total=20
>> [2024-06-15 08:10:01.619] FATAL Out of memory: Java heap space - requested 512MB, available 128MB
  [2024-06-15 08:10:02.329] INFO Request handled successfully in 193ms
  [2024-06-15 08:10:02.857] INFO Request handled successfully in 49ms
  [2024-06-15 08:10:03.304] INFO Database query completed in 259ms
  [2024-06-15 08:10:03.537] DEBUG Processing message from queue
  [2024-06-15 08:10:04.026] DEBUG Processing message from queue
```
</details>

---

### 33. [FATAL] 致命级别错误

- **文件**: `sample_app.log:1222`
- **时间**: 2024-06-15 08:10:07
- **匹配规则**: `(?i)\b(FATAL|PANIC|CRITICAL)\b`
- **匹配内容**: `CRITICAL`
- **分类**: severity

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:10:05.260] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:10:05.852] INFO Health check passed
  [2024-06-15 08:10:06.208] INFO Health check passed
  [2024-06-15 08:10:06.841] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:10:07.313] INFO User alice logged in from 10.0.1.20
>> [2024-06-15 08:10:07.698] CRITICAL deadlock detected between thread-pool-3 and thread-pool-7 on resource lock-orders-table
  [2024-06-15 08:10:08.037] INFO Database query completed in 69ms
  [2024-06-15 08:10:08.613] INFO Request handled successfully in 469ms
  [2024-06-15 08:10:09.321] INFO Request handled successfully in 50ms
  [2024-06-15 08:10:09.892] INFO Health check passed
  [2024-06-15 08:10:10.145] INFO Health check passed
```
</details>

---

### 34. [ERROR] 数据库连接错误

- **文件**: `sample_app.log:1243`
- **时间**: 2024-06-15 08:10:18
- **匹配规则**: `(?i)ERROR.*database.*connection`
- **匹配内容**: `ERROR database connection refused: Connection`
- **分类**: database

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:10:15.871] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:10:16.308] INFO Health check passed
  [2024-06-15 08:10:16.564] INFO User bob logged in from 192.168.1.100
  [2024-06-15 08:10:17.010] INFO Cache hit ratio: 72%
  [2024-06-15 08:10:17.970] DEBUG Loading configuration from /etc/app/config.yaml
>> [2024-06-15 08:10:18.304] ERROR database connection refused: Connection timed out after 30000ms to db-primary:5432
  [2024-06-15 08:10:18.561] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:10:19.300] INFO User bob logged in from 172.16.0.5
  [2024-06-15 08:10:19.881] INFO Database query completed in 349ms
  [2024-06-15 08:10:20.029] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:10:20.765] DEBUG Loading configuration from /etc/app/config.yaml
```
</details>

---

### 35. [WARN] 消息队列满/积压

- **文件**: `sample_app.log:1252`
- **时间**: 2024-06-15 08:10:22
- **匹配规则**: `(?i)queue.*full|backlog.*exceeded`
- **匹配内容**: `queue full`
- **分类**: performance

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:10:20.029] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:10:20.765] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:10:21.074] INFO API response sent: 200 OK
  [2024-06-15 08:10:21.860] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:10:22.364] INFO API response sent: 200 OK
>> [2024-06-15 08:10:22.531] WARN queue full: message-broker backlog exceeded 10000 messages
  [2024-06-15 08:10:23.227] INFO User bob logged in from 192.168.1.100
  [2024-06-15 08:10:23.771] INFO API response sent: 200 OK
  [2024-06-15 08:10:24.419] INFO Health check passed
  [2024-06-15 08:10:24.898] INFO User charlie logged in from 10.0.1.20
  [2024-06-15 08:10:25.090] INFO Cache hit ratio: 84%
```
</details>

---

### 36. [WARN] 认证失败

- **文件**: `sample_app.log:1338`
- **时间**: 2024-06-15 08:11:05
- **匹配规则**: `(?i)authentication (fail|error|denied)`
- **匹配内容**: `authentication fail`
- **分类**: security

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:11:03.209] INFO User diana logged in from 192.168.1.100
  [2024-06-15 08:11:03.842] INFO Health check passed
  [2024-06-15 08:11:04.365] INFO Request handled successfully in 22ms
  [2024-06-15 08:11:04.716] INFO Cache hit ratio: 93%
  [2024-06-15 08:11:05.247] INFO Connection pool stats: active=5 idle=15 total=20
>> [2024-06-15 08:11:05.678] ERROR authentication failed for user admin from 192.168.1.100 - 5 consecutive failures
  [2024-06-15 08:11:06.301] INFO Database query completed in 66ms
  [2024-06-15 08:11:06.668] INFO Cache hit ratio: 89%
  [2024-06-15 08:11:07.474] INFO Health check passed
  [2024-06-15 08:11:07.942] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:11:08.269] INFO Scheduled task completed: cleanup_sessions
```
</details>

---

### 37. [ERROR] 服务启动/停止失败

- **文件**: `sample_app.log:1357`
- **时间**: 2024-06-15 08:11:15
- **匹配规则**: `(?i)failed to (start|stop|restart) service`
- **匹配内容**: `failed to start service`
- **分类**: service

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:11:12.734] INFO User alice logged in from 192.168.1.100
  [2024-06-15 08:11:13.282] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:11:13.723] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:11:14.144] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:11:14.537] INFO Database query completed in 435ms
>> [2024-06-15 08:11:15.148] ERROR failed to start service nginx: port 443 already in use by pid 12847
  [2024-06-15 08:11:15.974] ERROR authentication failed for user admin from 192.168.1.100 - 5 consecutive failures
  [2024-06-15 08:11:16.300] INFO Cache hit ratio: 95%
  [2024-06-15 08:11:16.815] INFO Request handled successfully in 77ms
  [2024-06-15 08:11:17.135] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:11:17.940] INFO Health check passed
```
</details>

---

### 38. [WARN] 认证失败

- **文件**: `sample_app.log:1358`
- **时间**: 2024-06-15 08:11:15
- **匹配规则**: `(?i)authentication (fail|error|denied)`
- **匹配内容**: `authentication fail`
- **分类**: security

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:11:13.282] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:11:13.723] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:11:14.144] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:11:14.537] INFO Database query completed in 435ms
  [2024-06-15 08:11:15.148] ERROR failed to start service nginx: port 443 already in use by pid 12847
>> [2024-06-15 08:11:15.974] ERROR authentication failed for user admin from 192.168.1.100 - 5 consecutive failures
  [2024-06-15 08:11:16.300] INFO Cache hit ratio: 95%
  [2024-06-15 08:11:16.815] INFO Request handled successfully in 77ms
  [2024-06-15 08:11:17.135] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:11:17.940] INFO Health check passed
  [2024-06-15 08:11:18.357] INFO User alice logged in from 172.16.0.5
```
</details>

---

### 39. [ERROR] 权限被拒绝

- **文件**: `sample_app.log:1461`
- **时间**: 2024-06-15 08:12:07
- **匹配规则**: `(?i)permission\s+denied|access\s+denied|EACCES`
- **匹配内容**: `permission denied`
- **分类**: permission

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:12:04.551] INFO Cache hit ratio: 89%
  [2024-06-15 08:12:05.342] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:12:05.765] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:12:06.273] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:12:06.572] INFO Connection pool stats: active=5 idle=15 total=20
>> [2024-06-15 08:12:07.287] ERROR permission denied: cannot write to /var/log/app/audit.log - check file ownership
  [2024-06-15 08:12:07.686] INFO Request handled successfully in 483ms
  [2024-06-15 08:12:08.381] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:12:08.855] INFO User bob logged in from 192.168.1.100
  [2024-06-15 08:12:09.037] INFO Health check passed
  [2024-06-15 08:12:09.954] INFO Database query completed in 168ms
```
</details>

---

### 40. [WARN] 操作超时

- **文件**: `sample_app.log:1543`
- **时间**: 2024-06-15 08:12:48
- **匹配规则**: `(?i)timeout|timed?\s*out`
- **匹配内容**: `timeout`
- **分类**: performance

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:12:45.933] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:12:46.210] INFO Request handled successfully in 407ms
  [2024-06-15 08:12:46.769] INFO Request handled successfully in 354ms
  [2024-06-15 08:12:47.287] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:12:47.923] INFO Request handled successfully in 118ms
>> [2024-06-15 08:12:48.445] WARN timeout waiting for response from upstream service payment-api after 30s
  [2024-06-15 08:12:48.962] ERROR authentication failed for user admin from 192.168.1.100 - 5 consecutive failures
  [2024-06-15 08:12:49.432] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:12:49.636] INFO API response sent: 200 OK
  [2024-06-15 08:12:50.125] INFO Cache hit ratio: 66%
  [2024-06-15 08:12:50.898] INFO Database query completed in 408ms
```
</details>

---

### 41. [WARN] 认证失败

- **文件**: `sample_app.log:1544`
- **时间**: 2024-06-15 08:12:48
- **匹配规则**: `(?i)authentication (fail|error|denied)`
- **匹配内容**: `authentication fail`
- **分类**: security

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:12:46.210] INFO Request handled successfully in 407ms
  [2024-06-15 08:12:46.769] INFO Request handled successfully in 354ms
  [2024-06-15 08:12:47.287] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:12:47.923] INFO Request handled successfully in 118ms
  [2024-06-15 08:12:48.445] WARN timeout waiting for response from upstream service payment-api after 30s
>> [2024-06-15 08:12:48.962] ERROR authentication failed for user admin from 192.168.1.100 - 5 consecutive failures
  [2024-06-15 08:12:49.432] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:12:49.636] INFO API response sent: 200 OK
  [2024-06-15 08:12:50.125] INFO Cache hit ratio: 66%
  [2024-06-15 08:12:50.898] INFO Database query completed in 408ms
  [2024-06-15 08:12:51.037] INFO User bob logged in from 10.0.1.10
```
</details>

---

### 42. [WARN] 认证失败

- **文件**: `sample_app.log:1581`
- **时间**: 2024-06-15 08:13:07
- **匹配规则**: `(?i)authentication (fail|error|denied)`
- **匹配内容**: `authentication fail`
- **分类**: security

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:13:04.923] INFO Database query completed in 127ms
  [2024-06-15 08:13:05.013] INFO Database query completed in 30ms
  [2024-06-15 08:13:05.985] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:13:06.241] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:13:06.643] INFO Request handled successfully in 439ms
>> [2024-06-15 08:13:07.110] ERROR authentication failed for user admin from 192.168.1.100 - 5 consecutive failures
  [2024-06-15 08:13:07.584] INFO Cache hit ratio: 87%
  [2024-06-15 08:13:08.022] INFO Cache hit ratio: 83%
  [2024-06-15 08:13:08.503] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:13:09.295] INFO Cache hit ratio: 61%
  [2024-06-15 08:13:09.661] INFO API response sent: 200 OK
```
</details>

---

### 43. [ERROR] 服务启动/停止失败

- **文件**: `sample_app.log:1594`
- **时间**: 2024-06-15 08:13:13
- **匹配规则**: `(?i)failed to (start|stop|restart) service`
- **匹配内容**: `failed to start service`
- **分类**: service

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:13:11.356] INFO Request handled successfully in 197ms
  [2024-06-15 08:13:11.894] INFO Health check passed
  [2024-06-15 08:13:12.178] INFO API response sent: 200 OK
  [2024-06-15 08:13:12.627] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:13:13.446] INFO Database query completed in 252ms
>> [2024-06-15 08:13:13.749] ERROR failed to start service nginx: port 443 already in use by pid 12847
  [2024-06-15 08:13:14.491] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:13:14.732] INFO Cache hit ratio: 91%
  [2024-06-15 08:13:15.012] INFO Health check passed
  [2024-06-15 08:13:15.562] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:13:16.115] INFO Database query completed in 383ms
```
</details>

---

### 44. [ERROR] 空指针异常

- **文件**: `sample_app.log:1604`
- **时间**: 2024-06-15 08:13:18
- **匹配规则**: `(?i)(null\s*pointer|NullPointerException|nullptr|nil\s+pointer)`
- **匹配内容**: `NullPointer`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:13:16.115] INFO Database query completed in 383ms
  [2024-06-15 08:13:16.923] INFO User bob logged in from 10.0.1.10
  [2024-06-15 08:13:17.335] INFO API response sent: 200 OK
  [2024-06-15 08:13:17.538] INFO Request handled successfully in 28ms
  [2024-06-15 08:13:18.327] DEBUG Loading configuration from /etc/app/config.yaml
>> [2024-06-15 08:13:18.536] ERROR NullPointerException: Cannot invoke method on null object at com.app.service.UserService.getUser(UserService.java:142)
  [2024-06-15 08:13:19.163] INFO Health check passed
  [2024-06-15 08:13:19.589] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:13:20.158] INFO API response sent: 200 OK
  [2024-06-15 08:13:20.759] DEBUG Processing message from queue
  [2024-06-15 08:13:21.041] INFO Scheduled task completed: cleanup_sessions
```
</details>

---

### 45. [FATAL] 段错误 / 内存访问违规

- **文件**: `sample_app.log:1639`
- **时间**: 2024-06-15 08:13:36
- **匹配规则**: `(?i)segmentation\s+fault|segfault|SIGSEGV`
- **匹配内容**: `SIGSEGV`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:13:33.598] INFO Database query completed in 15ms
  [2024-06-15 08:13:34.332] DEBUG Processing message from queue
  [2024-06-15 08:13:34.620] INFO Database query completed in 311ms
  [2024-06-15 08:13:35.027] INFO API response sent: 200 OK
  [2024-06-15 08:13:35.928] DEBUG Processing message from queue
>> [2024-06-15 08:13:36.061] ERROR core dumped: signal 11 (SIGSEGV) in thread main-worker-3
  [2024-06-15 08:13:36.746] DEBUG Processing message from queue
  [2024-06-15 08:13:37.222] INFO Health check passed
  [2024-06-15 08:13:37.962] DEBUG Processing message from queue
  [2024-06-15 08:13:38.091] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:13:38.795] INFO Health check passed
```
</details>

---

### 46. [ERROR] 数据库复制延迟或失败

- **文件**: `sample_app.log:1648`
- **时间**: 2024-06-15 08:13:40
- **匹配规则**: `(?i)replication.*(lag|behind|fail)`
- **匹配内容**: `replication lag detected: slave is 120 seconds behind`
- **分类**: database

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:13:38.091] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:13:38.795] INFO Health check passed
  [2024-06-15 08:13:39.121] INFO Database query completed in 85ms
  [2024-06-15 08:13:39.819] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:13:40.179] INFO Connection pool stats: active=5 idle=15 total=20
>> [2024-06-15 08:13:40.926] ERROR replication lag detected: slave is 120 seconds behind master
  [2024-06-15 08:13:41.328] INFO Database query completed in 198ms
  [2024-06-15 08:13:41.943] DEBUG Processing message from queue
  [2024-06-15 08:13:42.238] INFO Cache hit ratio: 95%
  [2024-06-15 08:13:42.756] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:13:43.017] INFO User eve logged in from 10.0.1.10
```
</details>

---

### 47. [ERROR] 数据库连接错误

- **文件**: `sample_app.log:1674`
- **时间**: 2024-06-15 08:13:53
- **匹配规则**: `(?i)ERROR.*database.*connection`
- **匹配内容**: `ERROR database connection refused: Connection`
- **分类**: database

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:13:51.314] INFO Request handled successfully in 160ms
  [2024-06-15 08:13:51.964] DEBUG Processing message from queue
  [2024-06-15 08:13:52.087] INFO API response sent: 200 OK
  [2024-06-15 08:13:52.588] INFO User alice logged in from 10.0.1.10
  [2024-06-15 08:13:53.438] INFO Connection pool stats: active=5 idle=15 total=20
>> [2024-06-15 08:13:53.844] ERROR database connection refused: Connection timed out after 30000ms to db-primary:5432
  [2024-06-15 08:13:54.103] INFO API response sent: 200 OK
  [2024-06-15 08:13:54.930] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:13:55.006] INFO Request handled successfully in 317ms
  [2024-06-15 08:13:55.547] DEBUG Processing message from queue
  [2024-06-15 08:13:56.365] INFO User charlie logged in from 192.168.1.100
```
</details>

---

### 48. [ERROR] 连接异常（拒绝/重置/超时）

- **文件**: `sample_app.log:1684`
- **时间**: 2024-06-15 08:13:58
- **匹配规则**: `(?i)connection\s+(refused|reset|timed?\s*out)|ECONNREFUSED|ECONNRESET|ETIMEDOUT`
- **匹配内容**: `connection reset`
- **分类**: network

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:13:56.365] INFO User charlie logged in from 192.168.1.100
  [2024-06-15 08:13:56.586] INFO Cache hit ratio: 85%
  [2024-06-15 08:13:57.287] INFO Health check passed
  [2024-06-15 08:13:57.914] DEBUG Processing message from queue
  [2024-06-15 08:13:58.483] INFO Request handled successfully in 149ms
>> [2024-06-15 08:13:58.948] ERROR connection reset by peer: 10.0.1.50:8080 - possible network partition
  [2024-06-15 08:13:59.010] INFO API response sent: 200 OK
  [2024-06-15 08:13:59.811] INFO API response sent: 200 OK
  [2024-06-15 08:14:00.175] INFO Request handled successfully in 185ms
  [2024-06-15 08:14:00.719] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:14:01.048] INFO API response sent: 200 OK
```
</details>

---

### 49. [ERROR] 权限被拒绝

- **文件**: `sample_app.log:1777`
- **时间**: 2024-06-15 08:14:45
- **匹配规则**: `(?i)permission\s+denied|access\s+denied|EACCES`
- **匹配内容**: `permission denied`
- **分类**: permission

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:14:42.841] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:14:43.153] INFO Database query completed in 54ms
  [2024-06-15 08:14:43.820] INFO User diana logged in from 10.0.1.10
  [2024-06-15 08:14:44.318] DEBUG Processing message from queue
  [2024-06-15 08:14:44.765] INFO Scheduled task completed: cleanup_sessions
>> [2024-06-15 08:14:45.160] ERROR permission denied: cannot write to /var/log/app/audit.log - check file ownership
  [2024-06-15 08:14:45.591] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:14:46.403] DEBUG Processing message from queue
  [2024-06-15 08:14:46.506] INFO Cache hit ratio: 65%
  [2024-06-15 08:14:47.207] INFO Cache hit ratio: 97%
  [2024-06-15 08:14:47.878] INFO Scheduled task completed: cleanup_sessions
```
</details>

---

### 50. [WARN] 消息队列满/积压

- **文件**: `sample_app.log:1839`
- **时间**: 2024-06-15 08:15:16
- **匹配规则**: `(?i)queue.*full|backlog.*exceeded`
- **匹配内容**: `queue full`
- **分类**: performance

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:15:13.762] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:15:14.234] INFO API response sent: 200 OK
  [2024-06-15 08:15:14.587] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:15:15.338] INFO Request handled successfully in 203ms
  [2024-06-15 08:15:15.638] INFO Scheduled task completed: cleanup_sessions
>> [2024-06-15 08:15:16.395] WARN queue full: message-broker backlog exceeded 10000 messages
  [2024-06-15 08:15:16.532] INFO API response sent: 200 OK
  [2024-06-15 08:15:17.019] DEBUG Processing message from queue
  [2024-06-15 08:15:17.676] DEBUG Processing message from queue
  [2024-06-15 08:15:18.017] INFO Health check passed
  [2024-06-15 08:15:18.866] INFO Cache hit ratio: 81%
```
</details>

---

### 51. [ERROR] 空指针异常

- **文件**: `sample_app.log:1865`
- **时间**: 2024-06-15 08:15:29
- **匹配规则**: `(?i)(null\s*pointer|NullPointerException|nullptr|nil\s+pointer)`
- **匹配内容**: `NullPointer`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:15:26.666] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:15:27.292] INFO API response sent: 200 OK
  [2024-06-15 08:15:27.693] INFO Cache hit ratio: 78%
  [2024-06-15 08:15:28.244] INFO Health check passed
  [2024-06-15 08:15:28.731] DEBUG Loading configuration from /etc/app/config.yaml
>> [2024-06-15 08:15:29.270] ERROR NullPointerException: Cannot invoke method on null object at com.app.service.UserService.getUser(UserService.java:142)
  [2024-06-15 08:15:29.780] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:15:30.466] INFO User diana logged in from 10.0.1.20
  [2024-06-15 08:15:30.539] INFO User eve logged in from 10.0.1.10
  [2024-06-15 08:15:31.479] INFO API response sent: 200 OK
  [2024-06-15 08:15:31.997] INFO API response sent: 200 OK
```
</details>

---

### 52. [FATAL] 段错误 / 内存访问违规

- **文件**: `sample_app.log:1925`
- **时间**: 2024-06-15 08:15:59
- **匹配规则**: `(?i)segmentation\s+fault|segfault|SIGSEGV`
- **匹配内容**: `segmentation fault`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:15:56.528] INFO API response sent: 200 OK
  [2024-06-15 08:15:57.127] INFO Cache hit ratio: 63%
  [2024-06-15 08:15:57.636] INFO Health check passed
  [2024-06-15 08:15:58.309] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:15:58.818] INFO Scheduled task completed: cleanup_sessions
>> [2024-06-15 08:15:59.426] ERROR segmentation fault in module libcrypto.so.1.1 at address 0x7f3a2b4c1000
  [2024-06-15 08:15:59.897] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:16:00.374] DEBUG Processing message from queue
  [2024-06-15 08:16:00.525] INFO Health check passed
  [2024-06-15 08:16:01.258] INFO Health check passed
  [2024-06-15 08:16:01.986] INFO Cache hit ratio: 82%
```
</details>

---

### 53. [ERROR] 数据库连接错误

- **文件**: `sample_app.log:1947`
- **时间**: 2024-06-15 08:16:10
- **匹配规则**: `(?i)ERROR.*database.*connection`
- **匹配内容**: `ERROR database connection refused: Connection`
- **分类**: database

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:16:07.767] INFO API response sent: 200 OK
  [2024-06-15 08:16:08.092] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:16:08.922] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:16:09.031] INFO API response sent: 200 OK
  [2024-06-15 08:16:09.521] INFO Database query completed in 129ms
>> [2024-06-15 08:16:10.481] ERROR database connection refused: Connection timed out after 30000ms to db-primary:5432
  [2024-06-15 08:16:10.640] INFO User diana logged in from 10.0.1.20
  [2024-06-15 08:16:11.478] INFO Request handled successfully in 41ms
  [2024-06-15 08:16:11.758] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:16:12.113] INFO Health check passed
  [2024-06-15 08:16:12.677] DEBUG Processing message from queue
```
</details>

---

### 54. [ERROR] 空指针异常

- **文件**: `sample_app.log:2011`
- **时间**: 2024-06-15 08:16:42
- **匹配规则**: `(?i)(null\s*pointer|NullPointerException|nullptr|nil\s+pointer)`
- **匹配内容**: `NullPointer`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:16:39.630] INFO Cache hit ratio: 75%
  [2024-06-15 08:16:40.462] INFO Health check passed
  [2024-06-15 08:16:40.581] INFO Database query completed in 283ms
  [2024-06-15 08:16:41.429] INFO User alice logged in from 172.16.0.5
  [2024-06-15 08:16:41.689] INFO Cache hit ratio: 73%
>> [2024-06-15 08:16:42.374] ERROR NullPointerException: Cannot invoke method on null object at com.app.service.UserService.getUser(UserService.java:142)
  [2024-06-15 08:16:42.904] INFO User bob logged in from 172.16.0.5
  [2024-06-15 08:16:43.032] DEBUG Processing message from queue
  [2024-06-15 08:16:43.714] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:16:44.311] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:16:44.740] INFO Connection pool stats: active=5 idle=15 total=20
```
</details>

---

### 55. [ERROR] 服务启动/停止失败

- **文件**: `sample_app.log:2034`
- **时间**: 2024-06-15 08:16:53
- **匹配规则**: `(?i)failed to (start|stop|restart) service`
- **匹配内容**: `failed to start service`
- **分类**: service

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:16:51.191] INFO API response sent: 200 OK
  [2024-06-15 08:16:51.828] DEBUG Processing message from queue
  [2024-06-15 08:16:52.082] INFO Cache hit ratio: 61%
  [2024-06-15 08:16:52.579] INFO API response sent: 200 OK
  [2024-06-15 08:16:53.003] INFO Cache hit ratio: 61%
>> [2024-06-15 08:16:53.952] ERROR failed to start service nginx: port 443 already in use by pid 12847
  [2024-06-15 08:16:54.458] INFO Health check passed
  [2024-06-15 08:16:54.684] INFO User bob logged in from 10.0.1.20
  [2024-06-15 08:16:55.114] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:16:55.654] WARN queue full: message-broker backlog exceeded 10000 messages
  [2024-06-15 08:16:56.402] INFO User diana logged in from 172.16.0.5
```
</details>

---

### 56. [WARN] 消息队列满/积压

- **文件**: `sample_app.log:2038`
- **时间**: 2024-06-15 08:16:55
- **匹配规则**: `(?i)queue.*full|backlog.*exceeded`
- **匹配内容**: `queue full`
- **分类**: performance

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:16:53.003] INFO Cache hit ratio: 61%
  [2024-06-15 08:16:53.952] ERROR failed to start service nginx: port 443 already in use by pid 12847
  [2024-06-15 08:16:54.458] INFO Health check passed
  [2024-06-15 08:16:54.684] INFO User bob logged in from 10.0.1.20
  [2024-06-15 08:16:55.114] DEBUG Loading configuration from /etc/app/config.yaml
>> [2024-06-15 08:16:55.654] WARN queue full: message-broker backlog exceeded 10000 messages
  [2024-06-15 08:16:56.402] INFO User diana logged in from 172.16.0.5
  [2024-06-15 08:16:56.746] INFO API response sent: 200 OK
  [2024-06-15 08:16:57.136] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:16:57.962] WARN queue full: message-broker backlog exceeded 10000 messages
  [2024-06-15 08:16:58.255] INFO Scheduled task completed: cleanup_sessions
```
</details>

---

### 57. [ERROR] 数据库复制延迟或失败

- **文件**: `sample_app.log:2053`
- **时间**: 2024-06-15 08:17:03
- **匹配规则**: `(?i)replication.*(lag|behind|fail)`
- **匹配内容**: `replication lag detected: slave is 120 seconds behind`
- **分类**: database

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:17:00.675] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:17:01.430] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:17:01.750] INFO Request handled successfully in 395ms
  [2024-06-15 08:17:02.187] INFO User bob logged in from 10.0.1.10
  [2024-06-15 08:17:02.700] DEBUG Processing message from queue
>> [2024-06-15 08:17:03.021] ERROR replication lag detected: slave is 120 seconds behind master
  [2024-06-15 08:17:03.610] ERROR authentication failed for user admin from 192.168.1.100 - 5 consecutive failures
  [2024-06-15 08:17:04.152] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:17:04.796] INFO Request handled successfully in 143ms
  [2024-06-15 08:17:05.040] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:17:05.619] INFO Database query completed in 13ms
```
</details>

---

### 58. [WARN] 认证失败

- **文件**: `sample_app.log:2054`
- **时间**: 2024-06-15 08:17:03
- **匹配规则**: `(?i)authentication (fail|error|denied)`
- **匹配内容**: `authentication fail`
- **分类**: security

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:17:01.430] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:17:01.750] INFO Request handled successfully in 395ms
  [2024-06-15 08:17:02.187] INFO User bob logged in from 10.0.1.10
  [2024-06-15 08:17:02.700] DEBUG Processing message from queue
  [2024-06-15 08:17:03.021] ERROR replication lag detected: slave is 120 seconds behind master
>> [2024-06-15 08:17:03.610] ERROR authentication failed for user admin from 192.168.1.100 - 5 consecutive failures
  [2024-06-15 08:17:04.152] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:17:04.796] INFO Request handled successfully in 143ms
  [2024-06-15 08:17:05.040] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:17:05.619] INFO Database query completed in 13ms
  [2024-06-15 08:17:06.132] INFO Scheduled task completed: cleanup_sessions
```
</details>

---

### 59. [WARN] 消息队列满/积压

- **文件**: `sample_app.log:2146`
- **时间**: 2024-06-15 08:17:49
- **匹配规则**: `(?i)queue.*full|backlog.*exceeded`
- **匹配内容**: `queue full`
- **分类**: performance

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:17:47.499] INFO Request handled successfully in 383ms
  [2024-06-15 08:17:47.919] INFO Cache hit ratio: 72%
  [2024-06-15 08:17:48.471] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:17:48.626] INFO Health check passed
  [2024-06-15 08:17:49.150] INFO Request handled successfully in 11ms
>> [2024-06-15 08:17:49.875] WARN queue full: message-broker backlog exceeded 10000 messages
  [2024-06-15 08:17:50.316] INFO User alice logged in from 172.16.0.5
  [2024-06-15 08:17:50.857] INFO Health check passed
  [2024-06-15 08:17:51.432] INFO Cache hit ratio: 97%
  [2024-06-15 08:17:51.907] INFO User diana logged in from 10.0.1.10
  [2024-06-15 08:17:52.113] DEBUG Processing message from queue
```
</details>

---

### 60. [ERROR] 打开文件数超限

- **文件**: `sample_app.log:2167`
- **时间**: 2024-06-15 08:18:00
- **匹配规则**: `(?i)too\s+many\s+open\s+files|EMFILE`
- **匹配内容**: `too many open files`
- **分类**: resource

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:17:57.810] INFO Database query completed in 390ms
  [2024-06-15 08:17:58.029] INFO Request handled successfully in 332ms
  [2024-06-15 08:17:58.527] INFO Cache hit ratio: 62%
  [2024-06-15 08:17:59.063] DEBUG Processing message from queue
  [2024-06-15 08:17:59.986] INFO Cache hit ratio: 96%
>> [2024-06-15 08:18:00.390] ERROR too many open files (EMFILE): current limit 1024, attempted to open fd 1025
  [2024-06-15 08:18:00.834] INFO Health check passed
  [2024-06-15 08:18:01.084] INFO User alice logged in from 172.16.0.5
  [2024-06-15 08:18:01.675] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:18:02.135] INFO Request handled successfully in 393ms
  [2024-06-15 08:18:02.739] INFO Scheduled task completed: cleanup_sessions
```
</details>

---

### 61. [FATAL] 致命级别错误

- **文件**: `sample_app.log:2206`
- **时间**: 2024-06-15 08:18:19
- **匹配规则**: `(?i)\b(FATAL|PANIC|CRITICAL)\b`
- **匹配内容**: `CRITICAL`
- **分类**: severity

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:18:17.187] INFO API response sent: 200 OK
  [2024-06-15 08:18:17.853] INFO Health check passed
  [2024-06-15 08:18:18.106] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:18:18.526] INFO API response sent: 200 OK
  [2024-06-15 08:18:19.295] INFO Health check passed
>> [2024-06-15 08:18:19.528] CRITICAL deadlock detected between thread-pool-3 and thread-pool-7 on resource lock-orders-table
  [2024-06-15 08:18:20.233] INFO Database query completed in 441ms
  [2024-06-15 08:18:20.823] INFO User bob logged in from 172.16.0.5
  [2024-06-15 08:18:21.361] INFO Cache hit ratio: 69%
  [2024-06-15 08:18:21.905] INFO API response sent: 200 OK
  [2024-06-15 08:18:22.402] INFO Health check passed
```
</details>

---

### 62. [WARN] 操作超时

- **文件**: `sample_app.log:2218`
- **时间**: 2024-06-15 08:18:25
- **匹配规则**: `(?i)timeout|timed?\s*out`
- **匹配内容**: `timeout`
- **分类**: performance

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:18:23.429] DEBUG Processing message from queue
  [2024-06-15 08:18:23.726] INFO User alice logged in from 10.0.1.10
  [2024-06-15 08:18:24.237] INFO Cache hit ratio: 64%
  [2024-06-15 08:18:24.753] DEBUG Processing message from queue
  [2024-06-15 08:18:25.253] INFO Health check passed
>> [2024-06-15 08:18:25.695] WARN timeout waiting for response from upstream service payment-api after 30s
  [2024-06-15 08:18:26.454] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:18:26.616] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:18:27.451] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:18:27.631] INFO API response sent: 200 OK
  [2024-06-15 08:18:28.011] DEBUG Processing message from queue
```
</details>

---

### 63. [ERROR] 连接异常（拒绝/重置/超时）

- **文件**: `sample_app.log:2243`
- **时间**: 2024-06-15 08:18:38
- **匹配规则**: `(?i)connection\s+(refused|reset|timed?\s*out)|ECONNREFUSED|ECONNRESET|ETIMEDOUT`
- **匹配内容**: `connection reset`
- **分类**: network

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:18:35.966] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:18:36.379] INFO Cache hit ratio: 92%
  [2024-06-15 08:18:36.539] INFO User eve logged in from 192.168.1.100
  [2024-06-15 08:18:37.271] INFO API response sent: 200 OK
  [2024-06-15 08:18:37.667] INFO Database query completed in 82ms
>> [2024-06-15 08:18:38.250] ERROR connection reset by peer: 10.0.1.50:8080 - possible network partition
  [2024-06-15 08:18:38.687] INFO Cache hit ratio: 86%
  [2024-06-15 08:18:39.159] INFO Health check passed
  [2024-06-15 08:18:39.802] INFO Cache hit ratio: 60%
  [2024-06-15 08:18:40.137] INFO API response sent: 200 OK
  [2024-06-15 08:18:40.639] INFO Request handled successfully in 329ms
```
</details>

---

### 64. [WARN] 磁盘使用率超过 90%

- **文件**: `sample_app.log:2267`
- **时间**: 2024-06-15 08:18:50
- **匹配规则**: `(?i)disk usage.*(9[0-9]|100)%`
- **匹配内容**: `disk usage at 95%`
- **分类**: resource

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:18:47.927] INFO API response sent: 200 OK
  [2024-06-15 08:18:48.416] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:18:48.927] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:18:49.249] INFO Request handled successfully in 225ms
  [2024-06-15 08:18:49.716] INFO Scheduled task completed: cleanup_sessions
>> [2024-06-15 08:18:50.206] ERROR disk usage at 95% on /data volume - immediate attention required
  [2024-06-15 08:18:50.761] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:18:51.252] DEBUG Processing message from queue
  [2024-06-15 08:18:51.958] INFO Request handled successfully in 260ms
  [2024-06-15 08:18:52.437] INFO Request handled successfully in 302ms
  [2024-06-15 08:18:52.511] DEBUG Processing message from queue
```
</details>

---

### 65. [ERROR] 数据库复制延迟或失败

- **文件**: `sample_app.log:2277`
- **时间**: 2024-06-15 08:18:55
- **匹配规则**: `(?i)replication.*(lag|behind|fail)`
- **匹配内容**: `replication lag detected: slave is 120 seconds behind`
- **分类**: database

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:18:52.511] DEBUG Processing message from queue
  [2024-06-15 08:18:53.456] INFO Database query completed in 461ms
  [2024-06-15 08:18:53.928] INFO API response sent: 200 OK
  [2024-06-15 08:18:54.060] INFO Request handled successfully in 448ms
  [2024-06-15 08:18:54.962] INFO Cache hit ratio: 74%
>> [2024-06-15 08:18:55.285] ERROR replication lag detected: slave is 120 seconds behind master
  [2024-06-15 08:18:55.894] INFO Request handled successfully in 63ms
  [2024-06-15 08:18:56.496] INFO User bob logged in from 10.0.1.20
  [2024-06-15 08:18:56.679] DEBUG Processing message from queue
  [2024-06-15 08:18:57.470] INFO Health check passed
  [2024-06-15 08:18:57.596] INFO API response sent: 200 OK
```
</details>

---

### 66. [ERROR] 数据库复制延迟或失败

- **文件**: `sample_app.log:2403`
- **时间**: 2024-06-15 08:19:58
- **匹配规则**: `(?i)replication.*(lag|behind|fail)`
- **匹配内容**: `replication lag detected: slave is 120 seconds behind`
- **分类**: database

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:19:55.811] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:19:56.002] INFO Request handled successfully in 174ms
  [2024-06-15 08:19:56.748] INFO Request handled successfully in 404ms
  [2024-06-15 08:19:57.386] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:19:57.592] INFO Cache hit ratio: 77%
>> [2024-06-15 08:19:58.358] ERROR replication lag detected: slave is 120 seconds behind master
  [2024-06-15 08:19:58.561] DEBUG Processing message from queue
  [2024-06-15 08:19:59.153] INFO Health check passed
  [2024-06-15 08:19:59.955] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:20:00.092] INFO API response sent: 200 OK
  [2024-06-15 08:20:00.865] INFO Health check passed
```
</details>

---

### 67. [ERROR] 数据库复制延迟或失败

- **文件**: `sample_app.log:2421`
- **时间**: 2024-06-15 08:20:07
- **匹配规则**: `(?i)replication.*(lag|behind|fail)`
- **匹配内容**: `replication lag detected: slave is 120 seconds behind`
- **分类**: database

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:20:04.935] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:20:05.439] INFO Health check passed
  [2024-06-15 08:20:05.504] INFO API response sent: 200 OK
  [2024-06-15 08:20:06.282] INFO API response sent: 200 OK
  [2024-06-15 08:20:06.870] INFO Request handled successfully in 71ms
>> [2024-06-15 08:20:07.379] ERROR replication lag detected: slave is 120 seconds behind master
  [2024-06-15 08:20:07.559] INFO Health check passed
  [2024-06-15 08:20:08.243] INFO Cache hit ratio: 63%
  [2024-06-15 08:20:08.764] INFO Request handled successfully in 299ms
  [2024-06-15 08:20:09.265] INFO Database query completed in 417ms
  [2024-06-15 08:20:09.661] INFO Database query completed in 153ms
```
</details>

---

### 68. [ERROR] 打开文件数超限

- **文件**: `sample_app.log:2516`
- **时间**: 2024-06-15 08:20:54
- **匹配规则**: `(?i)too\s+many\s+open\s+files|EMFILE`
- **匹配内容**: `too many open files`
- **分类**: resource

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:20:52.138] INFO Cache hit ratio: 92%
  [2024-06-15 08:20:52.702] INFO User diana logged in from 10.0.1.20
  [2024-06-15 08:20:53.195] INFO Cache hit ratio: 75%
  [2024-06-15 08:20:53.582] DEBUG Processing message from queue
  [2024-06-15 08:20:54.225] DEBUG Loading configuration from /etc/app/config.yaml
>> [2024-06-15 08:20:54.828] ERROR too many open files (EMFILE): current limit 1024, attempted to open fd 1025
  [2024-06-15 08:20:55.225] INFO Health check passed
  [2024-06-15 08:20:55.640] INFO Health check passed
  [2024-06-15 08:20:56.482] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:20:56.648] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:20:57.233] INFO Scheduled task completed: cleanup_sessions
```
</details>

---

### 69. [WARN] 磁盘使用率超过 90%

- **文件**: `sample_app.log:2530`
- **时间**: 2024-06-15 08:21:01
- **匹配规则**: `(?i)disk usage.*(9[0-9]|100)%`
- **匹配内容**: `disk usage at 95%`
- **分类**: resource

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:20:59.033] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:20:59.600] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:21:00.063] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:21:00.781] INFO API response sent: 200 OK
  [2024-06-15 08:21:01.283] INFO Scheduled task completed: cleanup_sessions
>> [2024-06-15 08:21:01.658] ERROR disk usage at 95% on /data volume - immediate attention required
  [2024-06-15 08:21:02.075] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:21:02.622] INFO Cache hit ratio: 67%
  [2024-06-15 08:21:03.349] INFO API response sent: 200 OK
  [2024-06-15 08:21:03.650] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:21:04.367] INFO Connection pool stats: active=5 idle=15 total=20
```
</details>

---

### 70. [ERROR] 工作进程异常退出

- **文件**: `sample_app.log:2539`
- **时间**: 2024-06-15 08:21:06
- **匹配规则**: `(?i)worker.*process.*exit|child process.*died`
- **匹配内容**: `worker process exit`
- **分类**: process

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:21:03.650] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:21:04.367] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:21:04.717] INFO API response sent: 200 OK
  [2024-06-15 08:21:05.389] INFO API response sent: 200 OK
  [2024-06-15 08:21:05.713] INFO Connection pool stats: active=5 idle=15 total=20
>> [2024-06-15 08:21:06.498] ERROR worker process exit with code 137 (SIGKILL) - possible OOM kill
  [2024-06-15 08:21:06.910] INFO Cache hit ratio: 88%
  [2024-06-15 08:21:07.211] INFO Cache hit ratio: 71%
  [2024-06-15 08:21:07.583] INFO Cache hit ratio: 69%
  [2024-06-15 08:21:08.208] INFO API response sent: 200 OK
  [2024-06-15 08:21:08.729] INFO Scheduled task completed: cleanup_sessions
```
</details>

---

### 71. [ERROR] 通用异常/错误标记

- **文件**: `sample_app.log:2599`
- **时间**: 2024-06-15 08:21:36
- **匹配规则**: `(?i)(?:Exception|Error|Traceback)\s*[:(\[]`
- **匹配内容**: `Traceback (`
- **分类**: exception

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:21:33.797] INFO User bob logged in from 10.0.1.20
  [2024-06-15 08:21:34.065] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:21:34.941] INFO API response sent: 200 OK
  [2024-06-15 08:21:35.238] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:21:35.926] INFO Request handled successfully in 305ms
>> [2024-06-15 08:21:36.342] ERROR Traceback (most recent call last):
    File "/app/handlers/order.py", line 89
      raise ValueError("Invalid order state transition")
  [2024-06-15 08:21:36.729] INFO Request handled successfully in 378ms
  [2024-06-15 08:21:37.372] INFO API response sent: 200 OK
  [2024-06-15 08:21:37.515] INFO API response sent: 200 OK
```
</details>

---

### 72. [ERROR] 数据库连接错误

- **文件**: `sample_app.log:2780`
- **时间**: 2024-06-15 08:23:05
- **匹配规则**: `(?i)ERROR.*database.*connection`
- **匹配内容**: `ERROR database connection refused: Connection`
- **分类**: database

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:23:03.149] INFO User charlie logged in from 172.16.0.5
  [2024-06-15 08:23:03.641] INFO Health check passed
  [2024-06-15 08:23:04.459] INFO Request handled successfully in 457ms
  [2024-06-15 08:23:04.618] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:23:05.295] DEBUG Processing message from queue
>> [2024-06-15 08:23:05.878] ERROR database connection refused: Connection timed out after 30000ms to db-primary:5432
  [2024-06-15 08:23:06.325] DEBUG Processing message from queue
  [2024-06-15 08:23:06.600] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:23:07.380] INFO Health check passed
  [2024-06-15 08:23:07.665] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:23:08.249] INFO Scheduled task completed: cleanup_sessions
```
</details>

---

### 73. [FATAL] 致命级别错误

- **文件**: `sample_app.log:2803`
- **时间**: 2024-06-15 08:23:17
- **匹配规则**: `(?i)\b(FATAL|PANIC|CRITICAL)\b`
- **匹配内容**: `CRITICAL`
- **分类**: severity

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:23:14.661] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:23:15.322] INFO User charlie logged in from 10.0.1.20
  [2024-06-15 08:23:15.780] INFO Request handled successfully in 331ms
  [2024-06-15 08:23:16.152] DEBUG Processing message from queue
  [2024-06-15 08:23:16.541] INFO Database query completed in 11ms
>> [2024-06-15 08:23:17.082] CRITICAL deadlock detected between thread-pool-3 and thread-pool-7 on resource lock-orders-table
  [2024-06-15 08:23:17.882] INFO Cache hit ratio: 92%
  [2024-06-15 08:23:18.323] INFO API response sent: 200 OK
  [2024-06-15 08:23:18.740] DEBUG Processing message from queue
  [2024-06-15 08:23:19.249] INFO User bob logged in from 192.168.1.100
  [2024-06-15 08:23:19.581] INFO Connection pool stats: active=5 idle=15 total=20
```
</details>

---

### 74. [ERROR] 通用异常/错误标记

- **文件**: `sample_app.log:2925`
- **时间**: 2024-06-15 08:24:18
- **匹配规则**: `(?i)(?:Exception|Error|Traceback)\s*[:(\[]`
- **匹配内容**: `Traceback (`
- **分类**: exception

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:24:15.643] DEBUG Processing message from queue
  [2024-06-15 08:24:16.140] INFO Request handled successfully in 21ms
  [2024-06-15 08:24:16.669] DEBUG Processing message from queue
  [2024-06-15 08:24:17.048] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:24:17.798] INFO Connection pool stats: active=5 idle=15 total=20
>> [2024-06-15 08:24:18.321] ERROR Traceback (most recent call last):
    File "/app/handlers/order.py", line 89
      raise ValueError("Invalid order state transition")
  [2024-06-15 08:24:18.573] INFO Health check passed
  [2024-06-15 08:24:19.306] INFO API response sent: 200 OK
  [2024-06-15 08:24:19.522] INFO Health check passed
```
</details>

---

### 75. [ERROR] 数据库连接错误

- **文件**: `sample_app.log:2983`
- **时间**: 2024-06-15 08:24:46
- **匹配规则**: `(?i)ERROR.*database.*connection`
- **匹配内容**: `ERROR database connection refused: Connection`
- **分类**: database

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:24:43.763] INFO Cache hit ratio: 85%
  [2024-06-15 08:24:44.254] INFO Database query completed in 87ms
  [2024-06-15 08:24:44.653] INFO Request handled successfully in 20ms
  [2024-06-15 08:24:45.451] INFO API response sent: 200 OK
  [2024-06-15 08:24:45.949] INFO Cache hit ratio: 63%
>> [2024-06-15 08:24:46.420] ERROR database connection refused: Connection timed out after 30000ms to db-primary:5432
  [2024-06-15 08:24:46.608] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:24:47.048] INFO Health check passed
  [2024-06-15 08:24:47.728] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:24:48.092] INFO User diana logged in from 10.0.1.20
  [2024-06-15 08:24:48.917] INFO User bob logged in from 192.168.1.100
```
</details>

---

### 76. [ERROR] 权限被拒绝

- **文件**: `sample_app.log:3060`
- **时间**: 2024-06-15 08:25:24
- **匹配规则**: `(?i)permission\s+denied|access\s+denied|EACCES`
- **匹配内容**: `permission denied`
- **分类**: permission

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:25:22.060] DEBUG Processing message from queue
  [2024-06-15 08:25:22.856] DEBUG Processing message from queue
  [2024-06-15 08:25:23.432] INFO Database query completed in 308ms
  [2024-06-15 08:25:23.913] INFO User charlie logged in from 192.168.1.100
  [2024-06-15 08:25:24.013] INFO Cache hit ratio: 81%
>> [2024-06-15 08:25:24.968] ERROR permission denied: cannot write to /var/log/app/audit.log - check file ownership
  [2024-06-15 08:25:25.445] DEBUG Processing message from queue
  [2024-06-15 08:25:25.634] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:25:26.111] INFO API response sent: 200 OK
  [2024-06-15 08:25:26.570] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:25:27.414] INFO Cache hit ratio: 63%
```
</details>

---

### 77. [ERROR] 连接异常（拒绝/重置/超时）

- **文件**: `sample_app.log:3067`
- **时间**: 2024-06-15 08:25:28
- **匹配规则**: `(?i)connection\s+(refused|reset|timed?\s*out)|ECONNREFUSED|ECONNRESET|ETIMEDOUT`
- **匹配内容**: `connection reset`
- **分类**: network

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:25:25.634] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:25:26.111] INFO API response sent: 200 OK
  [2024-06-15 08:25:26.570] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:25:27.414] INFO Cache hit ratio: 63%
  [2024-06-15 08:25:27.560] INFO Cache hit ratio: 60%
>> [2024-06-15 08:25:28.200] ERROR connection reset by peer: 10.0.1.50:8080 - possible network partition
  [2024-06-15 08:25:28.983] INFO Database query completed in 68ms
  [2024-06-15 08:25:29.397] ERROR database connection refused: Connection timed out after 30000ms to db-primary:5432
  [2024-06-15 08:25:29.665] INFO Health check passed
  [2024-06-15 08:25:30.046] INFO Database query completed in 133ms
  [2024-06-15 08:25:30.946] DEBUG Loading configuration from /etc/app/config.yaml
```
</details>

---

### 78. [ERROR] 数据库连接错误

- **文件**: `sample_app.log:3069`
- **时间**: 2024-06-15 08:25:29
- **匹配规则**: `(?i)ERROR.*database.*connection`
- **匹配内容**: `ERROR database connection refused: Connection`
- **分类**: database

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:25:26.570] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:25:27.414] INFO Cache hit ratio: 63%
  [2024-06-15 08:25:27.560] INFO Cache hit ratio: 60%
  [2024-06-15 08:25:28.200] ERROR connection reset by peer: 10.0.1.50:8080 - possible network partition
  [2024-06-15 08:25:28.983] INFO Database query completed in 68ms
>> [2024-06-15 08:25:29.397] ERROR database connection refused: Connection timed out after 30000ms to db-primary:5432
  [2024-06-15 08:25:29.665] INFO Health check passed
  [2024-06-15 08:25:30.046] INFO Database query completed in 133ms
  [2024-06-15 08:25:30.946] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:25:31.309] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:25:31.801] INFO Connection pool stats: active=5 idle=15 total=20
```
</details>

---

### 79. [ERROR] 连接异常（拒绝/重置/超时）

- **文件**: `sample_app.log:3132`
- **时间**: 2024-06-15 08:26:00
- **匹配规则**: `(?i)connection\s+(refused|reset|timed?\s*out)|ECONNREFUSED|ECONNRESET|ETIMEDOUT`
- **匹配内容**: `connection reset`
- **分类**: network

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:25:58.219] INFO Cache hit ratio: 77%
  [2024-06-15 08:25:58.501] INFO Request handled successfully in 234ms
  [2024-06-15 08:25:59.169] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:25:59.636] INFO Database query completed in 337ms
  [2024-06-15 08:26:00.190] INFO User bob logged in from 10.0.1.20
>> [2024-06-15 08:26:00.611] ERROR connection reset by peer: 10.0.1.50:8080 - possible network partition
  [2024-06-15 08:26:01.287] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:26:01.973] INFO Cache hit ratio: 60%
  [2024-06-15 08:26:02.019] INFO Database query completed in 110ms
  [2024-06-15 08:26:02.578] INFO Request handled successfully in 475ms
  [2024-06-15 08:26:03.008] INFO Cache hit ratio: 80%
```
</details>

---

### 80. [ERROR] SSL 握手失败

- **文件**: `sample_app.log:3155`
- **时间**: 2024-06-15 08:26:12
- **匹配规则**: `(?i)SSL.*handshake.*(fail|error)`
- **匹配内容**: `SSL handshake fail`
- **分类**: security

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:26:09.937] INFO Request handled successfully in 196ms
  [2024-06-15 08:26:10.460] INFO Cache hit ratio: 71%
  [2024-06-15 08:26:10.514] DEBUG Processing message from queue
  [2024-06-15 08:26:11.040] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:26:11.687] DEBUG Loading configuration from /etc/app/config.yaml
>> [2024-06-15 08:26:12.156] ERROR SSL handshake failed: certificate expired on 2024-12-31
  [2024-06-15 08:26:12.958] INFO Request handled successfully in 324ms
  [2024-06-15 08:26:13.429] INFO Cache hit ratio: 91%
  [2024-06-15 08:26:13.902] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:26:14.211] INFO Request handled successfully in 237ms
  [2024-06-15 08:26:14.807] INFO Connection pool stats: active=5 idle=15 total=20
```
</details>

---

### 81. [ERROR] 连接异常（拒绝/重置/超时）

- **文件**: `sample_app.log:3198`
- **时间**: 2024-06-15 08:26:33
- **匹配规则**: `(?i)connection\s+(refused|reset|timed?\s*out)|ECONNREFUSED|ECONNRESET|ETIMEDOUT`
- **匹配内容**: `connection reset`
- **分类**: network

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:26:31.108] INFO Health check passed
  [2024-06-15 08:26:31.788] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:26:32.151] INFO API response sent: 200 OK
  [2024-06-15 08:26:32.969] INFO Request handled successfully in 1ms
  [2024-06-15 08:26:33.436] INFO User alice logged in from 192.168.1.100
>> [2024-06-15 08:26:33.531] ERROR connection reset by peer: 10.0.1.50:8080 - possible network partition
  [2024-06-15 08:26:34.295] INFO API response sent: 200 OK
  [2024-06-15 08:26:34.932] INFO Database query completed in 307ms
  [2024-06-15 08:26:35.372] INFO Request handled successfully in 401ms
  [2024-06-15 08:26:35.701] INFO Request handled successfully in 435ms
  [2024-06-15 08:26:36.368] ERROR NullPointerException: Cannot invoke method on null object at com.app.service.UserService.getUser(UserService.java:142)
```
</details>

---

### 82. [ERROR] 空指针异常

- **文件**: `sample_app.log:3203`
- **时间**: 2024-06-15 08:26:36
- **匹配规则**: `(?i)(null\s*pointer|NullPointerException|nullptr|nil\s+pointer)`
- **匹配内容**: `NullPointer`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:26:33.531] ERROR connection reset by peer: 10.0.1.50:8080 - possible network partition
  [2024-06-15 08:26:34.295] INFO API response sent: 200 OK
  [2024-06-15 08:26:34.932] INFO Database query completed in 307ms
  [2024-06-15 08:26:35.372] INFO Request handled successfully in 401ms
  [2024-06-15 08:26:35.701] INFO Request handled successfully in 435ms
>> [2024-06-15 08:26:36.368] ERROR NullPointerException: Cannot invoke method on null object at com.app.service.UserService.getUser(UserService.java:142)
  [2024-06-15 08:26:36.943] INFO User charlie logged in from 10.0.1.10
  [2024-06-15 08:26:37.159] INFO User eve logged in from 10.0.1.10
  [2024-06-15 08:26:37.543] INFO User eve logged in from 192.168.1.100
  [2024-06-15 08:26:38.404] ERROR segmentation fault in module libcrypto.so.1.1 at address 0x7f3a2b4c1000
  [2024-06-15 08:26:38.643] INFO Cache hit ratio: 79%
```
</details>

---

### 83. [FATAL] 段错误 / 内存访问违规

- **文件**: `sample_app.log:3207`
- **时间**: 2024-06-15 08:26:38
- **匹配规则**: `(?i)segmentation\s+fault|segfault|SIGSEGV`
- **匹配内容**: `segmentation fault`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:26:35.701] INFO Request handled successfully in 435ms
  [2024-06-15 08:26:36.368] ERROR NullPointerException: Cannot invoke method on null object at com.app.service.UserService.getUser(UserService.java:142)
  [2024-06-15 08:26:36.943] INFO User charlie logged in from 10.0.1.10
  [2024-06-15 08:26:37.159] INFO User eve logged in from 10.0.1.10
  [2024-06-15 08:26:37.543] INFO User eve logged in from 192.168.1.100
>> [2024-06-15 08:26:38.404] ERROR segmentation fault in module libcrypto.so.1.1 at address 0x7f3a2b4c1000
  [2024-06-15 08:26:38.643] INFO Cache hit ratio: 79%
  [2024-06-15 08:26:39.016] ERROR too many open files (EMFILE): current limit 1024, attempted to open fd 1025
  [2024-06-15 08:26:39.593] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:26:40.474] INFO User bob logged in from 172.16.0.5
  [2024-06-15 08:26:40.791] INFO Cache hit ratio: 89%
```
</details>

---

### 84. [ERROR] 打开文件数超限

- **文件**: `sample_app.log:3209`
- **时间**: 2024-06-15 08:26:39
- **匹配规则**: `(?i)too\s+many\s+open\s+files|EMFILE`
- **匹配内容**: `too many open files`
- **分类**: resource

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:26:36.943] INFO User charlie logged in from 10.0.1.10
  [2024-06-15 08:26:37.159] INFO User eve logged in from 10.0.1.10
  [2024-06-15 08:26:37.543] INFO User eve logged in from 192.168.1.100
  [2024-06-15 08:26:38.404] ERROR segmentation fault in module libcrypto.so.1.1 at address 0x7f3a2b4c1000
  [2024-06-15 08:26:38.643] INFO Cache hit ratio: 79%
>> [2024-06-15 08:26:39.016] ERROR too many open files (EMFILE): current limit 1024, attempted to open fd 1025
  [2024-06-15 08:26:39.593] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:26:40.474] INFO User bob logged in from 172.16.0.5
  [2024-06-15 08:26:40.791] INFO Cache hit ratio: 89%
  [2024-06-15 08:26:41.286] INFO Health check passed
  [2024-06-15 08:26:41.860] DEBUG Loading configuration from /etc/app/config.yaml
```
</details>

---

### 85. [WARN] 操作超时

- **文件**: `sample_app.log:3216`
- **时间**: 2024-06-15 08:26:42
- **匹配规则**: `(?i)timeout|timed?\s*out`
- **匹配内容**: `timeout`
- **分类**: performance

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:26:40.474] INFO User bob logged in from 172.16.0.5
  [2024-06-15 08:26:40.791] INFO Cache hit ratio: 89%
  [2024-06-15 08:26:41.286] INFO Health check passed
  [2024-06-15 08:26:41.860] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:26:42.259] INFO User alice logged in from 192.168.1.100
>> [2024-06-15 08:26:42.674] WARN timeout waiting for response from upstream service payment-api after 30s
  [2024-06-15 08:26:43.454] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:26:43.800] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:26:44.208] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:26:44.935] INFO Database query completed in 64ms
  [2024-06-15 08:26:45.335] DEBUG Loading configuration from /etc/app/config.yaml
```
</details>

---

### 86. [WARN] 操作超时

- **文件**: `sample_app.log:3230`
- **时间**: 2024-06-15 08:26:49
- **匹配规则**: `(?i)timeout|timed?\s*out`
- **匹配内容**: `timeout`
- **分类**: performance

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:26:47.460] DEBUG Processing message from queue
  [2024-06-15 08:26:47.855] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:26:48.133] INFO Cache hit ratio: 85%
  [2024-06-15 08:26:48.852] INFO Request handled successfully in 408ms
  [2024-06-15 08:26:49.284] INFO Cache hit ratio: 64%
>> [2024-06-15 08:26:49.585] WARN timeout waiting for response from upstream service payment-api after 30s
  [2024-06-15 08:26:50.158] INFO Health check passed
  [2024-06-15 08:26:50.533] DEBUG Processing message from queue
  [2024-06-15 08:26:51.331] INFO User alice logged in from 172.16.0.5
  [2024-06-15 08:26:51.710] INFO Cache hit ratio: 65%
  [2024-06-15 08:26:52.402] INFO Database query completed in 196ms
```
</details>

---

### 87. [WARN] 消息队列满/积压

- **文件**: `sample_app.log:3242`
- **时间**: 2024-06-15 08:26:55
- **匹配规则**: `(?i)queue.*full|backlog.*exceeded`
- **匹配内容**: `queue full`
- **分类**: performance

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:26:53.001] INFO Database query completed in 95ms
  [2024-06-15 08:26:53.915] INFO Health check passed
  [2024-06-15 08:26:54.187] INFO Health check passed
  [2024-06-15 08:26:54.744] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:26:55.235] INFO User alice logged in from 192.168.1.100
>> [2024-06-15 08:26:55.624] WARN queue full: message-broker backlog exceeded 10000 messages
  [2024-06-15 08:26:56.330] INFO User bob logged in from 10.0.1.10
  [2024-06-15 08:26:56.602] INFO Cache hit ratio: 93%
  [2024-06-15 08:26:57.016] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:26:57.809] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:26:58.499] INFO Cache hit ratio: 64%
```
</details>

---

### 88. [ERROR] 工作进程异常退出

- **文件**: `sample_app.log:3259`
- **时间**: 2024-06-15 08:27:04
- **匹配规则**: `(?i)worker.*process.*exit|child process.*died`
- **匹配内容**: `worker process exit`
- **分类**: process

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:27:01.616] INFO Database query completed in 330ms
  [2024-06-15 08:27:02.205] INFO Cache hit ratio: 76%
  [2024-06-15 08:27:02.692] INFO API response sent: 200 OK
  [2024-06-15 08:27:03.408] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:27:03.927] DEBUG Processing message from queue
>> [2024-06-15 08:27:04.373] ERROR worker process exit with code 137 (SIGKILL) - possible OOM kill
  [2024-06-15 08:27:04.885] INFO Database query completed in 95ms
  [2024-06-15 08:27:05.252] INFO User charlie logged in from 10.0.1.20
  [2024-06-15 08:27:05.862] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:27:06.470] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:27:06.893] INFO User diana logged in from 10.0.1.20
```
</details>

---

### 89. [ERROR] 服务启动/停止失败

- **文件**: `sample_app.log:3298`
- **时间**: 2024-06-15 08:27:23
- **匹配规则**: `(?i)failed to (start|stop|restart) service`
- **匹配内容**: `failed to start service`
- **分类**: service

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:27:21.094] INFO Request handled successfully in 193ms
  [2024-06-15 08:27:21.608] INFO User eve logged in from 10.0.1.20
  [2024-06-15 08:27:22.245] DEBUG Processing message from queue
  [2024-06-15 08:27:22.770] INFO Health check passed
  [2024-06-15 08:27:23.460] INFO User alice logged in from 10.0.1.20
>> [2024-06-15 08:27:23.585] ERROR failed to start service nginx: port 443 already in use by pid 12847
  [2024-06-15 08:27:24.279] INFO User charlie logged in from 192.168.1.100
  [2024-06-15 08:27:24.898] INFO Cache hit ratio: 89%
  [2024-06-15 08:27:25.121] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:27:25.832] INFO Health check passed
  [2024-06-15 08:27:26.132] DEBUG Loading configuration from /etc/app/config.yaml
```
</details>

---

### 90. [WARN] 磁盘使用率超过 90%

- **文件**: `sample_app.log:3304`
- **时间**: 2024-06-15 08:27:26
- **匹配规则**: `(?i)disk usage.*(9[0-9]|100)%`
- **匹配内容**: `disk usage at 95%`
- **分类**: resource

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:27:24.279] INFO User charlie logged in from 192.168.1.100
  [2024-06-15 08:27:24.898] INFO Cache hit ratio: 89%
  [2024-06-15 08:27:25.121] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:27:25.832] INFO Health check passed
  [2024-06-15 08:27:26.132] DEBUG Loading configuration from /etc/app/config.yaml
>> [2024-06-15 08:27:26.799] ERROR disk usage at 95% on /data volume - immediate attention required
  [2024-06-15 08:27:27.463] INFO User charlie logged in from 10.0.1.20
  [2024-06-15 08:27:27.809] INFO Request handled successfully in 220ms
  [2024-06-15 08:27:28.344] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:27:28.987] INFO Health check passed
  [2024-06-15 08:27:29.244] INFO Database query completed in 165ms
```
</details>

---

### 91. [ERROR] 工作进程异常退出

- **文件**: `sample_app.log:3323`
- **时间**: 2024-06-15 08:27:36
- **匹配规则**: `(?i)worker.*process.*exit|child process.*died`
- **匹配内容**: `worker process exit`
- **分类**: process

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:27:33.518] INFO User bob logged in from 172.16.0.5
  [2024-06-15 08:27:34.030] DEBUG Processing message from queue
  [2024-06-15 08:27:34.600] INFO User charlie logged in from 172.16.0.5
  [2024-06-15 08:27:35.196] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:27:35.671] INFO Scheduled task completed: cleanup_sessions
>> [2024-06-15 08:27:36.298] ERROR worker process exit with code 137 (SIGKILL) - possible OOM kill
  [2024-06-15 08:27:36.876] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:27:37.298] INFO Cache hit ratio: 82%
  [2024-06-15 08:27:37.697] INFO Database query completed in 381ms
  [2024-06-15 08:27:38.099] INFO User alice logged in from 192.168.1.100
  [2024-06-15 08:27:38.851] INFO Scheduled task completed: cleanup_sessions
```
</details>

---

### 92. [ERROR] 数据库连接错误

- **文件**: `sample_app.log:3398`
- **时间**: 2024-06-15 08:28:13
- **匹配规则**: `(?i)ERROR.*database.*connection`
- **匹配内容**: `ERROR database connection refused: Connection`
- **分类**: database

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:28:11.153] INFO User diana logged in from 10.0.1.10
  [2024-06-15 08:28:11.763] INFO Health check passed
  [2024-06-15 08:28:12.175] DEBUG Processing message from queue
  [2024-06-15 08:28:12.944] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:28:13.390] INFO Health check passed
>> [2024-06-15 08:28:13.565] ERROR database connection refused: Connection timed out after 30000ms to db-primary:5432
  [2024-06-15 08:28:14.222] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:28:14.579] INFO Cache hit ratio: 75%
  [2024-06-15 08:28:15.327] INFO API response sent: 200 OK
  [2024-06-15 08:28:15.834] INFO Cache hit ratio: 85%
  [2024-06-15 08:28:16.192] INFO API response sent: 200 OK
```
</details>

---

### 93. [ERROR] 服务启动/停止失败

- **文件**: `sample_app.log:3404`
- **时间**: 2024-06-15 08:28:16
- **匹配规则**: `(?i)failed to (start|stop|restart) service`
- **匹配内容**: `failed to start service`
- **分类**: service

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:28:14.222] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:28:14.579] INFO Cache hit ratio: 75%
  [2024-06-15 08:28:15.327] INFO API response sent: 200 OK
  [2024-06-15 08:28:15.834] INFO Cache hit ratio: 85%
  [2024-06-15 08:28:16.192] INFO API response sent: 200 OK
>> [2024-06-15 08:28:16.985] ERROR failed to start service nginx: port 443 already in use by pid 12847
  [2024-06-15 08:28:17.404] INFO API response sent: 200 OK
  [2024-06-15 08:28:17.539] DEBUG Processing message from queue
  [2024-06-15 08:28:18.044] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:28:18.904] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:28:19.225] INFO User diana logged in from 10.0.1.20
```
</details>

---

### 94. [WARN] 认证失败

- **文件**: `sample_app.log:3455`
- **时间**: 2024-06-15 08:28:42
- **匹配规则**: `(?i)authentication (fail|error|denied)`
- **匹配内容**: `authentication fail`
- **分类**: security

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:28:39.988] INFO Database query completed in 40ms
  [2024-06-15 08:28:40.485] INFO Health check passed
  [2024-06-15 08:28:40.605] INFO User diana logged in from 172.16.0.5
  [2024-06-15 08:28:41.108] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:28:41.860] INFO API response sent: 200 OK
>> [2024-06-15 08:28:42.174] ERROR authentication failed for user admin from 192.168.1.100 - 5 consecutive failures
  [2024-06-15 08:28:42.759] INFO Database query completed in 214ms
  [2024-06-15 08:28:43.165] DEBUG Processing message from queue
  [2024-06-15 08:28:43.727] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:28:44.122] INFO Health check passed
  [2024-06-15 08:28:44.587] INFO Database query completed in 3ms
```
</details>

---

### 95. [FATAL] 段错误 / 内存访问违规

- **文件**: `sample_app.log:3508`
- **时间**: 2024-06-15 08:29:08
- **匹配规则**: `(?i)segmentation\s+fault|segfault|SIGSEGV`
- **匹配内容**: `SIGSEGV`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:29:06.429] DEBUG Processing message from queue
  [2024-06-15 08:29:06.658] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:29:07.120] DEBUG Processing message from queue
  [2024-06-15 08:29:07.982] DEBUG Processing message from queue
  [2024-06-15 08:29:08.006] INFO Connection pool stats: active=5 idle=15 total=20
>> [2024-06-15 08:29:08.781] ERROR core dumped: signal 11 (SIGSEGV) in thread main-worker-3
  [2024-06-15 08:29:09.023] INFO Cache hit ratio: 72%
  [2024-06-15 08:29:09.856] INFO User alice logged in from 192.168.1.100
  [2024-06-15 08:29:10.098] INFO Request handled successfully in 241ms
  [2024-06-15 08:29:10.816] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:29:11.345] INFO Database query completed in 398ms
```
</details>

---

### 96. [ERROR] 工作进程异常退出

- **文件**: `sample_app.log:3541`
- **时间**: 2024-06-15 08:29:25
- **匹配规则**: `(?i)worker.*process.*exit|child process.*died`
- **匹配内容**: `worker process exit`
- **分类**: process

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:29:22.790] INFO Database query completed in 359ms
  [2024-06-15 08:29:23.104] INFO Request handled successfully in 291ms
  [2024-06-15 08:29:23.530] INFO Request handled successfully in 301ms
  [2024-06-15 08:29:24.482] DEBUG Processing message from queue
  [2024-06-15 08:29:24.757] INFO Request handled successfully in 54ms
>> [2024-06-15 08:29:25.380] ERROR worker process exit with code 137 (SIGKILL) - possible OOM kill
  [2024-06-15 08:29:25.595] INFO API response sent: 200 OK
  [2024-06-15 08:29:26.338] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:29:26.508] INFO User charlie logged in from 192.168.1.100
  [2024-06-15 08:29:27.357] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:29:27.524] INFO Request handled successfully in 116ms
```
</details>

---

### 97. [ERROR] 权限被拒绝

- **文件**: `sample_app.log:3591`
- **时间**: 2024-06-15 08:29:50
- **匹配规则**: `(?i)permission\s+denied|access\s+denied|EACCES`
- **匹配内容**: `permission denied`
- **分类**: permission

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:29:47.559] INFO Health check passed
  [2024-06-15 08:29:48.406] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:29:48.936] INFO User bob logged in from 10.0.1.20
  [2024-06-15 08:29:49.366] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:29:49.617] DEBUG Processing message from queue
>> [2024-06-15 08:29:50.181] ERROR permission denied: cannot write to /var/log/app/audit.log - check file ownership
  [2024-06-15 08:29:50.735] DEBUG Processing message from queue
  [2024-06-15 08:29:51.467] INFO Cache hit ratio: 63%
  [2024-06-15 08:29:51.672] INFO Database query completed in 38ms
  [2024-06-15 08:29:52.319] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:29:52.687] DEBUG Loading configuration from /etc/app/config.yaml
```
</details>

---

### 98. [FATAL] 段错误 / 内存访问违规

- **文件**: `sample_app.log:3602`
- **时间**: 2024-06-15 08:29:55
- **匹配规则**: `(?i)segmentation\s+fault|segfault|SIGSEGV`
- **匹配内容**: `segmentation fault`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:29:53.449] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:29:53.950] INFO User eve logged in from 172.16.0.5
  [2024-06-15 08:29:54.239] INFO Health check passed
  [2024-06-15 08:29:54.897] INFO Health check passed
  [2024-06-15 08:29:55.227] DEBUG Loading configuration from /etc/app/config.yaml
>> [2024-06-15 08:29:55.933] ERROR segmentation fault in module libcrypto.so.1.1 at address 0x7f3a2b4c1000
  [2024-06-15 08:29:56.438] INFO API response sent: 200 OK
  [2024-06-15 08:29:56.639] INFO API response sent: 200 OK
  [2024-06-15 08:29:57.208] INFO User bob logged in from 172.16.0.5
  [2024-06-15 08:29:57.756] INFO Health check passed
  [2024-06-15 08:29:58.430] INFO Database query completed in 73ms
```
</details>

---

### 99. [FATAL] 段错误 / 内存访问违规

- **文件**: `sample_app.log:3611`
- **时间**: 2024-06-15 08:30:00
- **匹配规则**: `(?i)segmentation\s+fault|segfault|SIGSEGV`
- **匹配内容**: `segmentation fault`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:29:57.756] INFO Health check passed
  [2024-06-15 08:29:58.430] INFO Database query completed in 73ms
  [2024-06-15 08:29:58.940] INFO User alice logged in from 10.0.1.20
  [2024-06-15 08:29:59.439] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:29:59.893] INFO Scheduled task completed: cleanup_sessions
>> [2024-06-15 08:30:00.333] ERROR segmentation fault in module libcrypto.so.1.1 at address 0x7f3a2b4c1000
  [2024-06-15 08:30:00.801] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:30:01.232] DEBUG Processing message from queue
  [2024-06-15 08:30:01.885] INFO Health check passed
  [2024-06-15 08:30:02.121] INFO User eve logged in from 10.0.1.10
  [2024-06-15 08:30:02.752] DEBUG Loading configuration from /etc/app/config.yaml
```
</details>

---

### 100. [WARN] 磁盘使用率超过 90%

- **文件**: `sample_app.log:3625`
- **时间**: 2024-06-15 08:30:07
- **匹配规则**: `(?i)disk usage.*(9[0-9]|100)%`
- **匹配内容**: `disk usage at 95%`
- **分类**: resource

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:30:04.768] INFO User eve logged in from 10.0.1.20
  [2024-06-15 08:30:05.197] INFO Request handled successfully in 325ms
  [2024-06-15 08:30:05.530] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:30:06.178] INFO API response sent: 200 OK
  [2024-06-15 08:30:06.502] DEBUG Loading configuration from /etc/app/config.yaml
>> [2024-06-15 08:30:07.496] ERROR disk usage at 95% on /data volume - immediate attention required
  [2024-06-15 08:30:07.734] INFO Database query completed in 177ms
  [2024-06-15 08:30:08.425] INFO Cache hit ratio: 61%
  [2024-06-15 08:30:08.755] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:30:09.373] INFO Request handled successfully in 426ms
  [2024-06-15 08:30:09.989] INFO User charlie logged in from 10.0.1.20
```
</details>

---

### 101. [WARN] 认证失败

- **文件**: `sample_app.log:3766`
- **时间**: 2024-06-15 08:31:17
- **匹配规则**: `(?i)authentication (fail|error|denied)`
- **匹配内容**: `authentication fail`
- **分类**: security

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:31:15.193] INFO Cache hit ratio: 76%
  [2024-06-15 08:31:15.890] INFO User bob logged in from 192.168.1.100
  [2024-06-15 08:31:16.265] INFO Cache hit ratio: 99%
  [2024-06-15 08:31:16.978] INFO Request handled successfully in 386ms
  [2024-06-15 08:31:17.014] INFO API response sent: 200 OK
>> [2024-06-15 08:31:17.890] ERROR authentication failed for user admin from 192.168.1.100 - 5 consecutive failures
  [2024-06-15 08:31:18.358] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:31:18.810] INFO Database query completed in 409ms
  [2024-06-15 08:31:19.220] INFO Health check passed
  [2024-06-15 08:31:19.599] INFO Request handled successfully in 379ms
  [2024-06-15 08:31:20.327] DEBUG Processing message from queue
```
</details>

---

### 102. [WARN] 磁盘使用率超过 90%

- **文件**: `sample_app.log:3826`
- **时间**: 2024-06-15 08:31:47
- **匹配规则**: `(?i)disk usage.*(9[0-9]|100)%`
- **匹配内容**: `disk usage at 95%`
- **分类**: resource

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:31:45.488] INFO Health check passed
  [2024-06-15 08:31:45.691] INFO Health check passed
  [2024-06-15 08:31:46.120] INFO Database query completed in 252ms
  [2024-06-15 08:31:46.566] INFO User bob logged in from 172.16.0.5
  [2024-06-15 08:31:47.445] INFO Scheduled task completed: cleanup_sessions
>> [2024-06-15 08:31:47.609] ERROR disk usage at 95% on /data volume - immediate attention required
  [2024-06-15 08:31:48.098] INFO Request handled successfully in 87ms
  [2024-06-15 08:31:48.973] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:31:49.486] INFO Cache hit ratio: 67%
  [2024-06-15 08:31:49.793] INFO Request handled successfully in 280ms
  [2024-06-15 08:31:50.428] INFO API response sent: 200 OK
```
</details>

---

### 103. [ERROR] 通用异常/错误标记

- **文件**: `sample_app.log:3857`
- **时间**: 2024-06-15 08:32:03
- **匹配规则**: `(?i)(?:Exception|Error|Traceback)\s*[:(\[]`
- **匹配内容**: `Traceback (`
- **分类**: exception

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:32:00.817] INFO User bob logged in from 10.0.1.20
  [2024-06-15 08:32:01.498] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:32:01.722] DEBUG Processing message from queue
  [2024-06-15 08:32:02.096] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:32:02.756] INFO Cache hit ratio: 95%
>> [2024-06-15 08:32:03.026] ERROR Traceback (most recent call last):
    File "/app/handlers/order.py", line 89
      raise ValueError("Invalid order state transition")
  [2024-06-15 08:32:03.641] INFO User alice logged in from 10.0.1.20
  [2024-06-15 08:32:04.032] INFO User bob logged in from 172.16.0.5
  [2024-06-15 08:32:04.641] INFO Scheduled task completed: cleanup_sessions
```
</details>

---

### 104. [ERROR] 打开文件数超限

- **文件**: `sample_app.log:3866`
- **时间**: 2024-06-15 08:32:06
- **匹配规则**: `(?i)too\s+many\s+open\s+files|EMFILE`
- **匹配内容**: `too many open files`
- **分类**: resource

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:32:04.032] INFO User bob logged in from 172.16.0.5
  [2024-06-15 08:32:04.641] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:32:05.111] INFO API response sent: 200 OK
  [2024-06-15 08:32:05.592] INFO Request handled successfully in 259ms
  [2024-06-15 08:32:06.341] DEBUG Loading configuration from /etc/app/config.yaml
>> [2024-06-15 08:32:06.558] ERROR too many open files (EMFILE): current limit 1024, attempted to open fd 1025
  [2024-06-15 08:32:07.005] INFO Database query completed in 148ms
  [2024-06-15 08:32:07.906] INFO Health check passed
  [2024-06-15 08:32:08.144] INFO Database query completed in 465ms
  [2024-06-15 08:32:08.689] DEBUG Processing message from queue
  [2024-06-15 08:32:09.078] INFO Health check passed
```
</details>

---

### 105. [FATAL] 致命级别错误

- **文件**: `sample_app.log:3874`
- **时间**: 2024-06-15 08:32:10
- **匹配规则**: `(?i)\b(FATAL|PANIC|CRITICAL)\b`
- **匹配内容**: `FATAL`
- **分类**: severity

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:32:08.144] INFO Database query completed in 465ms
  [2024-06-15 08:32:08.689] DEBUG Processing message from queue
  [2024-06-15 08:32:09.078] INFO Health check passed
  [2024-06-15 08:32:09.669] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:32:10.215] INFO User eve logged in from 192.168.1.100
>> [2024-06-15 08:32:10.977] FATAL Out of memory: Java heap space - requested 512MB, available 128MB
  [2024-06-15 08:32:11.153] WARN timeout waiting for response from upstream service payment-api after 30s
  [2024-06-15 08:32:11.533] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:32:12.164] INFO Database query completed in 7ms
  [2024-06-15 08:32:12.719] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:32:13.360] INFO Request handled successfully in 12ms
```
</details>

---

### 106. [WARN] 操作超时

- **文件**: `sample_app.log:3875`
- **时间**: 2024-06-15 08:32:11
- **匹配规则**: `(?i)timeout|timed?\s*out`
- **匹配内容**: `timeout`
- **分类**: performance

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:32:08.689] DEBUG Processing message from queue
  [2024-06-15 08:32:09.078] INFO Health check passed
  [2024-06-15 08:32:09.669] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:32:10.215] INFO User eve logged in from 192.168.1.100
  [2024-06-15 08:32:10.977] FATAL Out of memory: Java heap space - requested 512MB, available 128MB
>> [2024-06-15 08:32:11.153] WARN timeout waiting for response from upstream service payment-api after 30s
  [2024-06-15 08:32:11.533] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:32:12.164] INFO Database query completed in 7ms
  [2024-06-15 08:32:12.719] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:32:13.360] INFO Request handled successfully in 12ms
  [2024-06-15 08:32:13.519] INFO Request handled successfully in 38ms
```
</details>

---

### 107. [WARN] 磁盘使用率超过 90%

- **文件**: `sample_app.log:3884`
- **时间**: 2024-06-15 08:32:15
- **匹配规则**: `(?i)disk usage.*(9[0-9]|100)%`
- **匹配内容**: `disk usage at 95%`
- **分类**: resource

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:32:13.360] INFO Request handled successfully in 12ms
  [2024-06-15 08:32:13.519] INFO Request handled successfully in 38ms
  [2024-06-15 08:32:14.372] INFO Request handled successfully in 129ms
  [2024-06-15 08:32:14.599] DEBUG Processing message from queue
  [2024-06-15 08:32:15.493] DEBUG Processing message from queue
>> [2024-06-15 08:32:15.508] ERROR disk usage at 95% on /data volume - immediate attention required
  [2024-06-15 08:32:16.333] INFO API response sent: 200 OK
  [2024-06-15 08:32:16.606] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:32:17.371] INFO API response sent: 200 OK
  [2024-06-15 08:32:17.802] INFO User diana logged in from 192.168.1.100
  [2024-06-15 08:32:18.388] INFO Request handled successfully in 456ms
```
</details>

---

### 108. [ERROR] 通用异常/错误标记

- **文件**: `sample_app.log:3936`
- **时间**: 2024-06-15 08:32:41
- **匹配规则**: `(?i)(?:Exception|Error|Traceback)\s*[:(\[]`
- **匹配内容**: `Traceback (`
- **分类**: exception

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:32:39.391] INFO Cache hit ratio: 75%
  [2024-06-15 08:32:39.755] INFO Request handled successfully in 485ms
  [2024-06-15 08:32:40.292] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:32:40.737] INFO Cache hit ratio: 86%
  [2024-06-15 08:32:41.390] INFO Request handled successfully in 57ms
>> [2024-06-15 08:32:41.786] ERROR Traceback (most recent call last):
    File "/app/handlers/order.py", line 89
      raise ValueError("Invalid order state transition")
  [2024-06-15 08:32:42.128] INFO Cache hit ratio: 83%
  [2024-06-15 08:32:42.896] INFO Request handled successfully in 405ms
  [2024-06-15 08:32:43.357] INFO Cache hit ratio: 84%
```
</details>

---

### 109. [ERROR] 打开文件数超限

- **文件**: `sample_app.log:3957`
- **时间**: 2024-06-15 08:32:51
- **匹配规则**: `(?i)too\s+many\s+open\s+files|EMFILE`
- **匹配内容**: `too many open files`
- **分类**: resource

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:32:48.981] INFO Health check passed
  [2024-06-15 08:32:49.165] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:32:49.665] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:32:50.022] DEBUG Processing message from queue
  [2024-06-15 08:32:50.706] DEBUG Loading configuration from /etc/app/config.yaml
>> [2024-06-15 08:32:51.002] ERROR too many open files (EMFILE): current limit 1024, attempted to open fd 1025
  [2024-06-15 08:32:51.917] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:32:52.423] INFO Cache hit ratio: 88%
  [2024-06-15 08:32:52.914] INFO Request handled successfully in 373ms
  [2024-06-15 08:32:53.275] INFO API response sent: 200 OK
  [2024-06-15 08:32:53.688] INFO Scheduled task completed: cleanup_sessions
```
</details>

---

### 110. [WARN] 认证失败

- **文件**: `sample_app.log:3977`
- **时间**: 2024-06-15 08:33:01
- **匹配规则**: `(?i)authentication (fail|error|denied)`
- **匹配内容**: `authentication fail`
- **分类**: security

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:32:58.962] INFO User eve logged in from 192.168.1.100
  [2024-06-15 08:32:59.454] INFO API response sent: 200 OK
  [2024-06-15 08:32:59.560] INFO API response sent: 200 OK
  [2024-06-15 08:33:00.286] INFO API response sent: 200 OK
  [2024-06-15 08:33:00.858] INFO Scheduled task completed: cleanup_sessions
>> [2024-06-15 08:33:01.349] ERROR authentication failed for user admin from 192.168.1.100 - 5 consecutive failures
  [2024-06-15 08:33:01.502] INFO Request handled successfully in 304ms
  [2024-06-15 08:33:02.367] INFO Health check passed
  [2024-06-15 08:33:02.623] INFO Request handled successfully in 414ms
  [2024-06-15 08:33:03.440] INFO Cache hit ratio: 91%
  [2024-06-15 08:33:03.582] INFO API response sent: 200 OK
```
</details>

---

### 111. [FATAL] 段错误 / 内存访问违规

- **文件**: `sample_app.log:4007`
- **时间**: 2024-06-15 08:33:16
- **匹配规则**: `(?i)segmentation\s+fault|segfault|SIGSEGV`
- **匹配内容**: `segmentation fault`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:33:13.732] INFO Cache hit ratio: 89%
  [2024-06-15 08:33:14.312] DEBUG Processing message from queue
  [2024-06-15 08:33:14.861] DEBUG Processing message from queue
  [2024-06-15 08:33:15.079] INFO Cache hit ratio: 92%
  [2024-06-15 08:33:15.531] INFO Request handled successfully in 479ms
>> [2024-06-15 08:33:16.100] ERROR segmentation fault in module libcrypto.so.1.1 at address 0x7f3a2b4c1000
  [2024-06-15 08:33:16.856] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:33:17.432] INFO API response sent: 200 OK
  [2024-06-15 08:33:17.528] INFO Cache hit ratio: 87%
  [2024-06-15 08:33:18.474] INFO Request handled successfully in 288ms
  [2024-06-15 08:33:18.872] DEBUG Loading configuration from /etc/app/config.yaml
```
</details>

---

### 112. [FATAL] 致命级别错误

- **文件**: `sample_app.log:4070`
- **时间**: 2024-06-15 08:33:47
- **匹配规则**: `(?i)\b(FATAL|PANIC|CRITICAL)\b`
- **匹配内容**: `FATAL`
- **分类**: severity

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:33:45.078] INFO Database query completed in 272ms
  [2024-06-15 08:33:45.567] INFO Health check passed
  [2024-06-15 08:33:46.187] INFO API response sent: 200 OK
  [2024-06-15 08:33:46.924] INFO Cache hit ratio: 98%
  [2024-06-15 08:33:47.187] INFO Request handled successfully in 1ms
>> [2024-06-15 08:33:47.877] FATAL Out of memory: Java heap space - requested 512MB, available 128MB
  [2024-06-15 08:33:48.002] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:33:48.610] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:33:49.141] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:33:49.545] DEBUG Processing message from queue
  [2024-06-15 08:33:50.138] INFO API response sent: 200 OK
```
</details>

---

### 113. [ERROR] 服务启动/停止失败

- **文件**: `sample_app.log:4137`
- **时间**: 2024-06-15 08:34:21
- **匹配规则**: `(?i)failed to (start|stop|restart) service`
- **匹配内容**: `failed to start service`
- **分类**: service

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:34:18.815] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:34:19.402] INFO Health check passed
  [2024-06-15 08:34:19.847] INFO Cache hit ratio: 71%
  [2024-06-15 08:34:20.000] INFO Database query completed in 495ms
  [2024-06-15 08:34:20.505] INFO Connection pool stats: active=5 idle=15 total=20
>> [2024-06-15 08:34:21.014] ERROR failed to start service nginx: port 443 already in use by pid 12847
  [2024-06-15 08:34:21.627] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:34:22.226] DEBUG Processing message from queue
  [2024-06-15 08:34:22.840] INFO API response sent: 200 OK
  [2024-06-15 08:34:23.280] INFO Request handled successfully in 137ms
  [2024-06-15 08:34:23.562] INFO Connection pool stats: active=5 idle=15 total=20
```
</details>

---

### 114. [FATAL] 致命级别错误

- **文件**: `sample_app.log:4157`
- **时间**: 2024-06-15 08:34:31
- **匹配规则**: `(?i)\b(FATAL|PANIC|CRITICAL)\b`
- **匹配内容**: `FATAL`
- **分类**: severity

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:34:28.514] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:34:29.272] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:34:29.672] INFO Health check passed
  [2024-06-15 08:34:30.076] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:34:30.814] INFO Request handled successfully in 353ms
>> [2024-06-15 08:34:31.484] FATAL Out of memory: Java heap space - requested 512MB, available 128MB
  [2024-06-15 08:34:31.537] INFO Health check passed
  [2024-06-15 08:34:32.127] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:34:32.942] DEBUG Processing message from queue
  [2024-06-15 08:34:33.087] INFO Request handled successfully in 311ms
  [2024-06-15 08:34:33.599] INFO Connection pool stats: active=5 idle=15 total=20
```
</details>

---

### 115. [FATAL] 段错误 / 内存访问违规

- **文件**: `sample_app.log:4248`
- **时间**: 2024-06-15 08:35:16
- **匹配规则**: `(?i)segmentation\s+fault|segfault|SIGSEGV`
- **匹配内容**: `SIGSEGV`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:35:14.023] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:35:14.905] INFO Cache hit ratio: 73%
  [2024-06-15 08:35:15.303] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:35:15.601] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:35:16.120] INFO Connection pool stats: active=5 idle=15 total=20
>> [2024-06-15 08:35:16.819] ERROR core dumped: signal 11 (SIGSEGV) in thread main-worker-3
  [2024-06-15 08:35:17.344] DEBUG Processing message from queue
  [2024-06-15 08:35:17.571] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:35:18.296] ERROR too many open files (EMFILE): current limit 1024, attempted to open fd 1025
  [2024-06-15 08:35:18.832] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:35:19.121] INFO Scheduled task completed: cleanup_sessions
```
</details>

---

### 116. [ERROR] 打开文件数超限

- **文件**: `sample_app.log:4251`
- **时间**: 2024-06-15 08:35:18
- **匹配规则**: `(?i)too\s+many\s+open\s+files|EMFILE`
- **匹配内容**: `too many open files`
- **分类**: resource

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:35:15.601] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:35:16.120] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:35:16.819] ERROR core dumped: signal 11 (SIGSEGV) in thread main-worker-3
  [2024-06-15 08:35:17.344] DEBUG Processing message from queue
  [2024-06-15 08:35:17.571] INFO Scheduled task completed: cleanup_sessions
>> [2024-06-15 08:35:18.296] ERROR too many open files (EMFILE): current limit 1024, attempted to open fd 1025
  [2024-06-15 08:35:18.832] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:35:19.121] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:35:19.555] DEBUG Processing message from queue
  [2024-06-15 08:35:20.363] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:35:20.723] INFO User eve logged in from 10.0.1.10
```
</details>

---

### 117. [ERROR] 空指针异常

- **文件**: `sample_app.log:4269`
- **时间**: 2024-06-15 08:35:27
- **匹配规则**: `(?i)(null\s*pointer|NullPointerException|nullptr|nil\s+pointer)`
- **匹配内容**: `NullPointer`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:35:24.808] INFO Cache hit ratio: 84%
  [2024-06-15 08:35:25.239] INFO Cache hit ratio: 76%
  [2024-06-15 08:35:25.551] DEBUG Processing message from queue
  [2024-06-15 08:35:26.175] DEBUG Processing message from queue
  [2024-06-15 08:35:26.601] INFO Health check passed
>> [2024-06-15 08:35:27.027] ERROR NullPointerException: Cannot invoke method on null object at com.app.service.UserService.getUser(UserService.java:142)
  [2024-06-15 08:35:27.526] ERROR Traceback (most recent call last):
    File "/app/handlers/order.py", line 89
      raise ValueError("Invalid order state transition")
  [2024-06-15 08:35:28.223] INFO User charlie logged in from 172.16.0.5
  [2024-06-15 08:35:28.936] DEBUG Processing message from queue
```
</details>

---

### 118. [ERROR] 通用异常/错误标记

- **文件**: `sample_app.log:4270`
- **时间**: 2024-06-15 08:35:27
- **匹配规则**: `(?i)(?:Exception|Error|Traceback)\s*[:(\[]`
- **匹配内容**: `Traceback (`
- **分类**: exception

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:35:25.239] INFO Cache hit ratio: 76%
  [2024-06-15 08:35:25.551] DEBUG Processing message from queue
  [2024-06-15 08:35:26.175] DEBUG Processing message from queue
  [2024-06-15 08:35:26.601] INFO Health check passed
  [2024-06-15 08:35:27.027] ERROR NullPointerException: Cannot invoke method on null object at com.app.service.UserService.getUser(UserService.java:142)
>> [2024-06-15 08:35:27.526] ERROR Traceback (most recent call last):
    File "/app/handlers/order.py", line 89
      raise ValueError("Invalid order state transition")
  [2024-06-15 08:35:28.223] INFO User charlie logged in from 172.16.0.5
  [2024-06-15 08:35:28.936] DEBUG Processing message from queue
  [2024-06-15 08:35:29.252] INFO Health check passed
```
</details>

---

### 119. [FATAL] 致命级别错误

- **文件**: `sample_app.log:4307`
- **时间**: 2024-06-15 08:35:45
- **匹配规则**: `(?i)\b(FATAL|PANIC|CRITICAL)\b`
- **匹配内容**: `CRITICAL`
- **分类**: severity

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:35:42.571] INFO API response sent: 200 OK
  [2024-06-15 08:35:43.067] INFO Request handled successfully in 3ms
  [2024-06-15 08:35:43.527] INFO Request handled successfully in 259ms
  [2024-06-15 08:35:44.233] INFO Database query completed in 239ms
  [2024-06-15 08:35:44.620] DEBUG Loading configuration from /etc/app/config.yaml
>> [2024-06-15 08:35:45.098] CRITICAL deadlock detected between thread-pool-3 and thread-pool-7 on resource lock-orders-table
  [2024-06-15 08:35:45.972] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:35:46.080] INFO Request handled successfully in 85ms
  [2024-06-15 08:35:46.801] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:35:47.292] INFO Request handled successfully in 1ms
  [2024-06-15 08:35:47.580] INFO Database query completed in 411ms
```
</details>

---

### 120. [WARN] 认证失败

- **文件**: `sample_app.log:4353`
- **时间**: 2024-06-15 08:36:08
- **匹配规则**: `(?i)authentication (fail|error|denied)`
- **匹配内容**: `authentication fail`
- **分类**: security

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:36:05.829] INFO Request handled successfully in 109ms
  [2024-06-15 08:36:06.007] INFO Request handled successfully in 239ms
  [2024-06-15 08:36:06.528] INFO User bob logged in from 10.0.1.20
  [2024-06-15 08:36:07.364] INFO User charlie logged in from 192.168.1.100
  [2024-06-15 08:36:07.725] DEBUG Processing message from queue
>> [2024-06-15 08:36:08.079] ERROR authentication failed for user admin from 192.168.1.100 - 5 consecutive failures
  [2024-06-15 08:36:08.822] INFO Request handled successfully in 492ms
  [2024-06-15 08:36:09.114] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:36:09.946] INFO Request handled successfully in 345ms
  [2024-06-15 08:36:10.082] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:36:10.698] DEBUG Processing message from queue
```
</details>

---

### 121. [ERROR] 打开文件数超限

- **文件**: `sample_app.log:4369`
- **时间**: 2024-06-15 08:36:16
- **匹配规则**: `(?i)too\s+many\s+open\s+files|EMFILE`
- **匹配内容**: `too many open files`
- **分类**: resource

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:36:13.611] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:36:14.198] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:36:14.623] INFO Database query completed in 90ms
  [2024-06-15 08:36:15.488] INFO User bob logged in from 10.0.1.10
  [2024-06-15 08:36:15.716] DEBUG Loading configuration from /etc/app/config.yaml
>> [2024-06-15 08:36:16.187] ERROR too many open files (EMFILE): current limit 1024, attempted to open fd 1025
  [2024-06-15 08:36:16.651] INFO Request handled successfully in 127ms
  [2024-06-15 08:36:17.493] INFO Database query completed in 450ms
  [2024-06-15 08:36:17.901] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:36:18.253] INFO Health check passed
  [2024-06-15 08:36:18.551] INFO Cache hit ratio: 70%
```
</details>

---

### 122. [ERROR] 数据库连接错误

- **文件**: `sample_app.log:4489`
- **时间**: 2024-06-15 08:37:16
- **匹配规则**: `(?i)ERROR.*database.*connection`
- **匹配内容**: `ERROR database connection refused: Connection`
- **分类**: database

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:37:13.533] INFO Health check passed
  [2024-06-15 08:37:14.180] INFO User alice logged in from 10.0.1.20
  [2024-06-15 08:37:14.862] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:37:15.453] INFO Health check passed
  [2024-06-15 08:37:15.540] INFO Cache hit ratio: 81%
>> [2024-06-15 08:37:16.270] ERROR database connection refused: Connection timed out after 30000ms to db-primary:5432
  [2024-06-15 08:37:16.520] INFO Health check passed
  [2024-06-15 08:37:17.361] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:37:17.862] INFO Health check passed
  [2024-06-15 08:37:18.470] INFO Health check passed
  [2024-06-15 08:37:18.796] INFO User charlie logged in from 172.16.0.5
```
</details>

---

### 123. [ERROR] 通用异常/错误标记

- **文件**: `sample_app.log:4498`
- **时间**: 2024-06-15 08:37:20
- **匹配规则**: `(?i)(?:Exception|Error|Traceback)\s*[:(\[]`
- **匹配内容**: `Traceback (`
- **分类**: exception

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:37:18.470] INFO Health check passed
  [2024-06-15 08:37:18.796] INFO User charlie logged in from 172.16.0.5
  [2024-06-15 08:37:19.352] INFO User diana logged in from 10.0.1.10
  [2024-06-15 08:37:19.590] INFO Request handled successfully in 51ms
  [2024-06-15 08:37:20.034] INFO Connection pool stats: active=5 idle=15 total=20
>> [2024-06-15 08:37:20.862] ERROR Traceback (most recent call last):
    File "/app/handlers/order.py", line 89
      raise ValueError("Invalid order state transition")
  [2024-06-15 08:37:21.318] INFO User diana logged in from 10.0.1.10
  [2024-06-15 08:37:21.581] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:37:22.253] INFO Health check passed
```
</details>

---

### 124. [WARN] 认证失败

- **文件**: `sample_app.log:4539`
- **时间**: 2024-06-15 08:37:40
- **匹配规则**: `(?i)authentication (fail|error|denied)`
- **匹配内容**: `authentication fail`
- **分类**: security

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:37:37.945] INFO API response sent: 200 OK
  [2024-06-15 08:37:38.154] INFO Cache hit ratio: 89%
  [2024-06-15 08:37:38.785] INFO Cache hit ratio: 90%
  [2024-06-15 08:37:39.189] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:37:39.874] DEBUG Processing message from queue
>> [2024-06-15 08:37:40.127] ERROR authentication failed for user admin from 192.168.1.100 - 5 consecutive failures
  [2024-06-15 08:37:40.879] INFO API response sent: 200 OK
  [2024-06-15 08:37:41.348] INFO API response sent: 200 OK
  [2024-06-15 08:37:41.963] INFO Database query completed in 119ms
  [2024-06-15 08:37:42.314] INFO API response sent: 200 OK
  [2024-06-15 08:37:42.680] INFO Database query completed in 105ms
```
</details>

---

### 125. [ERROR] 权限被拒绝

- **文件**: `sample_app.log:4603`
- **时间**: 2024-06-15 08:38:12
- **匹配规则**: `(?i)permission\s+denied|access\s+denied|EACCES`
- **匹配内容**: `permission denied`
- **分类**: permission

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:38:09.838] INFO Database query completed in 378ms
  [2024-06-15 08:38:10.241] INFO API response sent: 200 OK
  [2024-06-15 08:38:10.799] INFO API response sent: 200 OK
  [2024-06-15 08:38:11.093] INFO User charlie logged in from 172.16.0.5
  [2024-06-15 08:38:11.882] INFO Request handled successfully in 115ms
>> [2024-06-15 08:38:12.020] ERROR permission denied: cannot write to /var/log/app/audit.log - check file ownership
  [2024-06-15 08:38:12.801] DEBUG Processing message from queue
  [2024-06-15 08:38:13.386] ERROR core dumped: signal 11 (SIGSEGV) in thread main-worker-3
  [2024-06-15 08:38:13.900] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:38:14.257] INFO API response sent: 200 OK
  [2024-06-15 08:38:14.982] INFO User bob logged in from 10.0.1.10
```
</details>

---

### 126. [FATAL] 段错误 / 内存访问违规

- **文件**: `sample_app.log:4605`
- **时间**: 2024-06-15 08:38:13
- **匹配规则**: `(?i)segmentation\s+fault|segfault|SIGSEGV`
- **匹配内容**: `SIGSEGV`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:38:10.799] INFO API response sent: 200 OK
  [2024-06-15 08:38:11.093] INFO User charlie logged in from 172.16.0.5
  [2024-06-15 08:38:11.882] INFO Request handled successfully in 115ms
  [2024-06-15 08:38:12.020] ERROR permission denied: cannot write to /var/log/app/audit.log - check file ownership
  [2024-06-15 08:38:12.801] DEBUG Processing message from queue
>> [2024-06-15 08:38:13.386] ERROR core dumped: signal 11 (SIGSEGV) in thread main-worker-3
  [2024-06-15 08:38:13.900] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:38:14.257] INFO API response sent: 200 OK
  [2024-06-15 08:38:14.982] INFO User bob logged in from 10.0.1.10
  [2024-06-15 08:38:15.214] DEBUG Processing message from queue
  [2024-06-15 08:38:15.749] INFO User diana logged in from 10.0.1.10
```
</details>

---

### 127. [FATAL] 致命级别错误

- **文件**: `sample_app.log:4636`
- **时间**: 2024-06-15 08:38:28
- **匹配规则**: `(?i)\b(FATAL|PANIC|CRITICAL)\b`
- **匹配内容**: `FATAL`
- **分类**: severity

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:38:26.265] INFO Health check passed
  [2024-06-15 08:38:26.870] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:38:27.220] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:38:27.798] INFO User eve logged in from 192.168.1.100
  [2024-06-15 08:38:28.098] INFO API response sent: 200 OK
>> [2024-06-15 08:38:28.509] FATAL Out of memory: Java heap space - requested 512MB, available 128MB
  [2024-06-15 08:38:29.055] INFO Cache hit ratio: 96%
  [2024-06-15 08:38:29.897] INFO Cache hit ratio: 88%
  [2024-06-15 08:38:30.402] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:38:30.929] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:38:31.339] INFO API response sent: 200 OK
```
</details>

---

### 128. [ERROR] 数据库连接错误

- **文件**: `sample_app.log:4734`
- **时间**: 2024-06-15 08:39:17
- **匹配规则**: `(?i)ERROR.*database.*connection`
- **匹配内容**: `ERROR database connection refused: Connection`
- **分类**: database

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:39:15.218] INFO User diana logged in from 10.0.1.20
  [2024-06-15 08:39:15.838] INFO User bob logged in from 172.16.0.5
  [2024-06-15 08:39:16.400] INFO User eve logged in from 10.0.1.10
  [2024-06-15 08:39:16.655] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:39:17.442] INFO Database query completed in 490ms
>> [2024-06-15 08:39:17.881] ERROR database connection refused: Connection timed out after 30000ms to db-primary:5432
  [2024-06-15 08:39:18.153] INFO Database query completed in 83ms
  [2024-06-15 08:39:18.875] DEBUG Processing message from queue
  [2024-06-15 08:39:19.410] INFO Database query completed in 38ms
  [2024-06-15 08:39:19.544] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:39:20.048] INFO API response sent: 200 OK
```
</details>

---

### 129. [ERROR] 数据库连接错误

- **文件**: `sample_app.log:4755`
- **时间**: 2024-06-15 08:39:28
- **匹配规则**: `(?i)ERROR.*database.*connection`
- **匹配内容**: `ERROR database connection refused: Connection`
- **分类**: database

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:39:25.734] INFO API response sent: 200 OK
  [2024-06-15 08:39:26.365] DEBUG Processing message from queue
  [2024-06-15 08:39:26.872] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:39:27.416] INFO Health check passed
  [2024-06-15 08:39:27.612] INFO Health check passed
>> [2024-06-15 08:39:28.085] ERROR database connection refused: Connection timed out after 30000ms to db-primary:5432
  [2024-06-15 08:39:28.918] INFO Database query completed in 431ms
  [2024-06-15 08:39:29.080] DEBUG Processing message from queue
  [2024-06-15 08:39:29.960] INFO Request handled successfully in 40ms
  [2024-06-15 08:39:30.329] INFO User alice logged in from 10.0.1.10
  [2024-06-15 08:39:30.638] INFO Database query completed in 124ms
```
</details>

---

### 130. [WARN] 消息队列满/积压

- **文件**: `sample_app.log:4767`
- **时间**: 2024-06-15 08:39:34
- **匹配规则**: `(?i)queue.*full|backlog.*exceeded`
- **匹配内容**: `queue full`
- **分类**: performance

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:39:31.669] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:39:32.378] INFO API response sent: 200 OK
  [2024-06-15 08:39:32.626] INFO API response sent: 200 OK
  [2024-06-15 08:39:33.147] INFO Cache hit ratio: 78%
  [2024-06-15 08:39:33.611] INFO Cache hit ratio: 73%
>> [2024-06-15 08:39:34.452] WARN queue full: message-broker backlog exceeded 10000 messages
  [2024-06-15 08:39:34.629] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:39:35.191] INFO API response sent: 200 OK
  [2024-06-15 08:39:35.575] CRITICAL deadlock detected between thread-pool-3 and thread-pool-7 on resource lock-orders-table
  [2024-06-15 08:39:36.207] INFO Cache hit ratio: 91%
  [2024-06-15 08:39:36.991] INFO Database query completed in 356ms
```
</details>

---

### 131. [FATAL] 致命级别错误

- **文件**: `sample_app.log:4770`
- **时间**: 2024-06-15 08:39:35
- **匹配规则**: `(?i)\b(FATAL|PANIC|CRITICAL)\b`
- **匹配内容**: `CRITICAL`
- **分类**: severity

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:39:33.147] INFO Cache hit ratio: 78%
  [2024-06-15 08:39:33.611] INFO Cache hit ratio: 73%
  [2024-06-15 08:39:34.452] WARN queue full: message-broker backlog exceeded 10000 messages
  [2024-06-15 08:39:34.629] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:39:35.191] INFO API response sent: 200 OK
>> [2024-06-15 08:39:35.575] CRITICAL deadlock detected between thread-pool-3 and thread-pool-7 on resource lock-orders-table
  [2024-06-15 08:39:36.207] INFO Cache hit ratio: 91%
  [2024-06-15 08:39:36.991] INFO Database query completed in 356ms
  [2024-06-15 08:39:37.222] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:39:37.960] INFO Request handled successfully in 86ms
  [2024-06-15 08:39:38.217] INFO API response sent: 200 OK
```
</details>

---

### 132. [ERROR] 空指针异常

- **文件**: `sample_app.log:4801`
- **时间**: 2024-06-15 08:39:51
- **匹配规则**: `(?i)(null\s*pointer|NullPointerException|nullptr|nil\s+pointer)`
- **匹配内容**: `NullPointer`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:39:48.748] INFO Health check passed
  [2024-06-15 08:39:49.356] DEBUG Processing message from queue
  [2024-06-15 08:39:49.637] INFO Cache hit ratio: 75%
  [2024-06-15 08:39:50.431] INFO Cache hit ratio: 98%
  [2024-06-15 08:39:50.869] INFO Request handled successfully in 373ms
>> [2024-06-15 08:39:51.105] ERROR NullPointerException: Cannot invoke method on null object at com.app.service.UserService.getUser(UserService.java:142)
  [2024-06-15 08:39:51.943] DEBUG Processing message from queue
  [2024-06-15 08:39:52.086] INFO User diana logged in from 192.168.1.100
  [2024-06-15 08:39:52.950] ERROR connection reset by peer: 10.0.1.50:8080 - possible network partition
  [2024-06-15 08:39:53.473] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:39:53.873] DEBUG Processing message from queue
```
</details>

---

### 133. [ERROR] 连接异常（拒绝/重置/超时）

- **文件**: `sample_app.log:4804`
- **时间**: 2024-06-15 08:39:52
- **匹配规则**: `(?i)connection\s+(refused|reset|timed?\s*out)|ECONNREFUSED|ECONNRESET|ETIMEDOUT`
- **匹配内容**: `connection reset`
- **分类**: network

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:39:50.431] INFO Cache hit ratio: 98%
  [2024-06-15 08:39:50.869] INFO Request handled successfully in 373ms
  [2024-06-15 08:39:51.105] ERROR NullPointerException: Cannot invoke method on null object at com.app.service.UserService.getUser(UserService.java:142)
  [2024-06-15 08:39:51.943] DEBUG Processing message from queue
  [2024-06-15 08:39:52.086] INFO User diana logged in from 192.168.1.100
>> [2024-06-15 08:39:52.950] ERROR connection reset by peer: 10.0.1.50:8080 - possible network partition
  [2024-06-15 08:39:53.473] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:39:53.873] DEBUG Processing message from queue
  [2024-06-15 08:39:54.239] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:39:54.596] DEBUG Processing message from queue
  [2024-06-15 08:39:55.354] INFO Health check passed
```
</details>

---

### 134. [ERROR] 空指针异常

- **文件**: `sample_app.log:4857`
- **时间**: 2024-06-15 08:40:19
- **匹配规则**: `(?i)(null\s*pointer|NullPointerException|nullptr|nil\s+pointer)`
- **匹配内容**: `NullPointer`
- **分类**: crash

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:40:16.665] INFO Cache hit ratio: 72%
  [2024-06-15 08:40:17.429] INFO Cache hit ratio: 73%
  [2024-06-15 08:40:17.593] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:40:18.332] INFO Database query completed in 401ms
  [2024-06-15 08:40:18.581] INFO Cache hit ratio: 84%
>> [2024-06-15 08:40:19.180] ERROR NullPointerException: Cannot invoke method on null object at com.app.service.UserService.getUser(UserService.java:142)
  [2024-06-15 08:40:19.723] INFO Request handled successfully in 424ms
  [2024-06-15 08:40:20.324] INFO Connection pool stats: active=5 idle=15 total=20
  [2024-06-15 08:40:20.824] DEBUG Processing message from queue
  [2024-06-15 08:40:21.332] DEBUG Loading configuration from /etc/app/config.yaml
  [2024-06-15 08:40:21.875] INFO API response sent: 200 OK
```
</details>

---

### 135. [ERROR] 权限被拒绝

- **文件**: `sample_app.log:4885`
- **时间**: 2024-06-15 08:40:33
- **匹配规则**: `(?i)permission\s+denied|access\s+denied|EACCES`
- **匹配内容**: `permission denied`
- **分类**: permission

<details>
<summary>上下文日志（前后 5+5 行）</summary>

```
  [2024-06-15 08:40:30.759] DEBUG Processing message from queue
  [2024-06-15 08:40:31.076] DEBUG Processing message from queue
  [2024-06-15 08:40:31.729] INFO Scheduled task completed: cleanup_sessions
  [2024-06-15 08:40:32.459] INFO Request handled successfully in 270ms
  [2024-06-15 08:40:32.670] INFO Database query completed in 161ms
>> [2024-06-15 08:40:33.397] ERROR permission denied: cannot write to /var/log/app/audit.log - check file ownership
  [2024-06-15 08:40:33.827] DEBUG Processing message from queue
  [2024-06-15 08:40:34.391] INFO Health check passed
  [2024-06-15 08:40:34.865] INFO Health check passed
  [2024-06-15 08:40:35.045] INFO User diana logged in from 10.0.1.10
  [2024-06-15 08:40:35.914] INFO User alice logged in from 10.0.1.10
```
</details>

---

## 总结与建议

### 需要立即处理 (FATAL)

- `sample_app.log:254` - 致命级别错误
- `sample_app.log:787` - 段错误 / 内存访问违规
- `sample_app.log:872` - 致命级别错误
- `sample_app.log:1074` - 致命级别错误
- `sample_app.log:1168` - 段错误 / 内存访问违规
- `sample_app.log:1210` - 致命级别错误
- `sample_app.log:1222` - 致命级别错误
- `sample_app.log:1639` - 段错误 / 内存访问违规
- `sample_app.log:1925` - 段错误 / 内存访问违规
- `sample_app.log:2206` - 致命级别错误
- `sample_app.log:2803` - 致命级别错误
- `sample_app.log:3207` - 段错误 / 内存访问违规
- `sample_app.log:3508` - 段错误 / 内存访问违规
- `sample_app.log:3602` - 段错误 / 内存访问违规
- `sample_app.log:3611` - 段错误 / 内存访问违规
- `sample_app.log:3874` - 致命级别错误
- `sample_app.log:4007` - 段错误 / 内存访问违规
- `sample_app.log:4070` - 致命级别错误
- `sample_app.log:4157` - 致命级别错误
- `sample_app.log:4248` - 段错误 / 内存访问违规
- `sample_app.log:4307` - 致命级别错误
- `sample_app.log:4605` - 段错误 / 内存访问违规
- `sample_app.log:4636` - 致命级别错误
- `sample_app.log:4770` - 致命级别错误

### 需要关注 (ERROR)

- **exception**: 9 个错误
  - `sample_app.log:51` - 通用异常/错误标记
  - `sample_app.log:838` - 通用异常/错误标记
  - `sample_app.log:969` - 通用异常/错误标记
  - `sample_app.log:2599` - 通用异常/错误标记
  - `sample_app.log:2925` - 通用异常/错误标记
  - ... 及其他 4 个
- **permission**: 8 个错误
  - `sample_app.log:77` - 权限被拒绝
  - `sample_app.log:372` - 权限被拒绝
  - `sample_app.log:1461` - 权限被拒绝
  - `sample_app.log:1777` - 权限被拒绝
  - `sample_app.log:3060` - 权限被拒绝
  - ... 及其他 3 个
- **process**: 8 个错误
  - `sample_app.log:104` - 工作进程异常退出
  - `sample_app.log:227` - 工作进程异常退出
  - `sample_app.log:246` - 工作进程异常退出
  - `sample_app.log:973` - 工作进程异常退出
  - `sample_app.log:2539` - 工作进程异常退出
  - ... 及其他 3 个
- **database**: 19 个错误
  - `sample_app.log:296` - 数据库复制延迟或失败
  - `sample_app.log:536` - 数据库连接错误
  - `sample_app.log:660` - 数据库连接错误
  - `sample_app.log:991` - 数据库连接错误
  - `sample_app.log:1243` - 数据库连接错误
  - ... 及其他 14 个
- **security**: 2 个错误
  - `sample_app.log:310` - SSL 握手失败
  - `sample_app.log:3155` - SSL 握手失败
- **crash**: 10 个错误
  - `sample_app.log:750` - 空指针异常
  - `sample_app.log:1025` - 空指针异常
  - `sample_app.log:1038` - 空指针异常
  - `sample_app.log:1604` - 空指针异常
  - `sample_app.log:1865` - 空指针异常
  - ... 及其他 5 个
- **service**: 7 个错误
  - `sample_app.log:842` - 服务启动/停止失败
  - `sample_app.log:1357` - 服务启动/停止失败
  - `sample_app.log:1594` - 服务启动/停止失败
  - `sample_app.log:2034` - 服务启动/停止失败
  - `sample_app.log:3298` - 服务启动/停止失败
  - ... 及其他 2 个
- **network**: 7 个错误
  - `sample_app.log:844` - 连接异常（拒绝/重置/超时）
  - `sample_app.log:1684` - 连接异常（拒绝/重置/超时）
  - `sample_app.log:2243` - 连接异常（拒绝/重置/超时）
  - `sample_app.log:3067` - 连接异常（拒绝/重置/超时）
  - `sample_app.log:3132` - 连接异常（拒绝/重置/超时）
  - ... 及其他 2 个
- **resource**: 7 个错误
  - `sample_app.log:2167` - 打开文件数超限
  - `sample_app.log:2516` - 打开文件数超限
  - `sample_app.log:3209` - 打开文件数超限
  - `sample_app.log:3866` - 打开文件数超限
  - `sample_app.log:3957` - 打开文件数超限
  - ... 及其他 2 个
