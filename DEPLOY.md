# 部署到 Render

https://render.com/deploy?repo=https://github.com/lamugu/haiguitang

## 环境变量

| Key | 说明 |
|-----|------|
| `JEV_API_KEY` | Vercel AI Gateway key（判决提问；URL/模型有默认值） |
| `AI_API_KEY` | LLM key（导入 / 提交答案） |
| `AI_API_URL` | LLM 基址，chat/completions 协议，如 `https://api.xxx.com/v1` |
| `AI_MODEL` | LLM 模型名 |
| `ADMIN_KEY` | 管理页口令 |
| `SQLITE_PATH` | 建议 `/var/data/puzzles.db`（挂持久盘） |

健康检查：`/api/health`

## 题库持久化（重要）

Render **免费实例没有持久磁盘**：每次 Manual Deploy / 同步代码后，容器文件系统会被清空。  
SQLite 若写在 `/app/data/...`，导入的几十碗汤都会消失，服务只会重新灌入种子题。

### 推荐做法

1. 服务升到 **Starter**（或更高），在 Render Dashboard → Disks 挂载：
   - Mount path: `/var/data`
   - 环境变量：`SQLITE_PATH=/var/data/puzzles.db`
2. 本仓库 `render.yaml` 已按上述配置写好 Disk。
3. 无论是否挂盘，导入后请到管理页 **导出备份**；丢数据时用 **恢复备份**。

### 若暂时留在 Free

- 每次导入后立刻下载 JSON 备份
- Redeploy 后用「恢复备份 → 合并」把题灌回去
