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

健康检查：`/api/health`
