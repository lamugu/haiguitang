# 海龟汤

独立的海龟汤网页游戏：玩家通过是非提问还原真相。

## 技术

- 前端：Vue 3 + Vite
- 后端：FastAPI + SQLite
- **判决提问（jev）**：默认 [Vercel AI Gateway](https://vercel.com/docs/ai-gateway)（一般只配 key）
- **导入 / 提交答案**：任意 OpenAI 兼容 `/chat/completions`

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `JEV_API_KEY` | 是 | 判决用。默认走 `https://ai-gateway.vercel.sh/v1` |
| `AI_API_KEY` | 建议 | LLM key |
| `AI_API_URL` | 建议 | LLM 基址，如 `https://api.atria-asi.ai/v1`（不要带 `/chat/completions`） |
| `AI_MODEL` | 建议 | LLM 模型名 |
| `ADMIN_KEY` | 建议 | 汤库管理页口令 |

可选覆盖 jev（通常不用）：`JEV_API_URL`、`JEV_MODEL`。

## 本地运行

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
python main.py

cd frontend
npm install && npm run dev
```

## 部署

见 [DEPLOY.md](./DEPLOY.md)。  
https://render.com/deploy?repo=https://github.com/lamugu/haiguitang
