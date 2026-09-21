# 部署到 Render

https://render.com/deploy?repo=https://github.com/lamugu/haiguitang

## 必填环境变量

| Key | 说明 |
|-----|------|
| `AI_GATEWAY_API_KEY` | Vercel AI Gateway，用于**提问判决** |
| `AI_API_KEY` | 原 LLM，用于**导入 / 提交答案** |
| `ADMIN_KEY` | 管理页口令（汤底列表 / 增删 / 导入） |

可选：`AI_GATEWAY_MODEL`、`AI_API_URL`、`AI_MODEL`

健康检查：`/api/health`（返回 `gatewayConfigured` / `llmConfigured` / `adminConfigured`）
