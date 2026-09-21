# 海龟汤

独立的海龟汤网页游戏：玩家通过是非提问还原真相。

## 技术

- 前端：Vue 3 + Vite
- 后端：FastAPI + SQLite
- 主持判决 / 导入 / 判答案：统一走 [Vercel AI Gateway](https://vercel.com/docs/ai-gateway)

## 本地运行

```bash
# 后端
cd backend
pip install -r requirements.txt
cp .env.example .env   # 填写 AI_GATEWAY_API_KEY
python main.py         # http://localhost:8081

# 前端开发
cd frontend
npm install
npm run dev
```

## 部署（Render）

见 [DEPLOY.md](./DEPLOY.md)。

一键：https://render.com/deploy?repo=https://github.com/lamugu/haiguitang

环境变量只需配置 `AI_GATEWAY_API_KEY`（以及可选的 `AI_GATEWAY_MODEL`）。
