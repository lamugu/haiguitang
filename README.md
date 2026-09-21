# 海龟汤

独立的海龟汤网页游戏：玩家通过是非提问还原真相。

## 技术

- 前端：Vue 3 + Vite
- 后端：FastAPI + SQLite
- **判决提问**（原 jev 职责）：[Vercel AI Gateway](https://vercel.com/docs/ai-gateway)
- **导入 / 提交答案**：原 LLM（OpenAI 兼容，默认 Atria）

## 环境变量

| 变量 | 用途 |
|------|------|
| `AI_GATEWAY_API_KEY` | 判决提问（也可用别名 `JEV_API_KEY`） |
| `AI_GATEWAY_MODEL` | Gateway 模型，默认 `openai/gpt-4o-mini` |
| `AI_API_KEY` | 原 LLM：导入抽取、答案语义判定 |
| `AI_API_URL` / `AI_MODEL` | 原 LLM 端点与模型名 |

## 本地运行

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # 分别填写 Gateway key 与 LLM key
python main.py

cd frontend
npm install && npm run dev
```

## 部署

见 [DEPLOY.md](./DEPLOY.md)。  
https://render.com/deploy?repo=https://github.com/lamugu/haiguitang
