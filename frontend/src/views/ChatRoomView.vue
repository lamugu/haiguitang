<template>
  <div class="page-shell chat">
    <header class="chat-top page-inner">
      <button class="ghost-btn" type="button" @click="router.push('/')">
        <HomeOutlined />
        主页
      </button>
      <div class="room-meta">
        <img src="/assets/brand-bowl.png" alt="" class="mini-bowl" />
        <span>房间 {{ roomId }}</span>
      </div>
      <div class="actions">
        <button class="ghost-btn" type="button" :disabled="!started || ended || busy" @click="handleNext">
          <SwapOutlined />
          下一碗
        </button>
        <button class="danger" type="button" :disabled="ended || busy" @click="handleEnd">
          <PoweroffOutlined />
          结束
        </button>
      </div>
    </header>

    <main class="chat-main page-inner" ref="listRef">
      <div v-if="!messages.length" class="empty">
        <img src="/assets/empty-bowl.png" alt="" />
        <p>汤还没上桌，稍候…</p>
      </div>
      <div v-for="(msg, index) in messages" :key="index" class="msg" :class="{ ai: msg.isAI, user: !msg.isAI }">
        <img :src="msg.isAI ? '/assets/avatar-host.png' : '/assets/avatar-player.png'" alt="" class="avatar" />
        <div class="bubble">
          <div class="who">{{ msg.isAI ? '主持人' : '你' }}</div>
          <div class="text">{{ msg.content }}</div>
        </div>
      </div>
    </main>

    <footer class="chat-input page-inner">
      <div class="input-row">
        <QuestionCircleOutlined class="lead-icon" />
        <input
          v-model="inputMessage"
          :disabled="ended || busy"
          placeholder="输入是非问题，例如：这件事和死亡有关吗？"
          @keydown.enter.prevent="sendMessage"
        />
        <button class="solid-btn" type="button" :disabled="ended || busy || !inputMessage.trim()" @click="sendMessage">
          <SendOutlined />
          提问
        </button>
      </div>
      <div class="input-row answer">
        <BulbOutlined class="lead-icon" />
        <input
          v-model="answerMessage"
          :disabled="ended || busy"
          placeholder="已还原真相？在此提交最终答案"
          @keydown.enter.prevent="submitFinal"
        />
        <button class="ghost-btn" type="button" :disabled="ended || busy || !answerMessage.trim()" @click="submitFinal">
          <CheckCircleOutlined />
          提交答案
        </button>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  BulbOutlined,
  CheckCircleOutlined,
  HomeOutlined,
  PoweroffOutlined,
  QuestionCircleOutlined,
  SendOutlined,
  SwapOutlined,
} from '@ant-design/icons-vue'
import { nextPuzzle, sendMessage as apiSend, submitAnswer } from '../api'

const route = useRoute()
const router = useRouter()
const roomId = ref(route.params.roomId)
const messages = ref([])
const inputMessage = ref('')
const answerMessage = ref('')
const listRef = ref(null)
const started = ref(false)
const ended = ref(false)
const busy = ref(false)

const scrollToBottom = () => {
  nextTick(() => {
    if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
  })
}

const pushReply = (content) => {
  messages.value.push({ content, isAI: true })
  if (String(content).includes('游戏已结束')) {
    ended.value = true
  }
  scrollToBottom()
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || busy.value) return
  busy.value = true
  const text = inputMessage.value
  messages.value.push({ content: text, isAI: false })
  inputMessage.value = ''
  scrollToBottom()
  try {
    const reply = await apiSend(roomId.value, text)
    pushReply(reply)
    started.value = true
  } catch (e) {
    pushReply(e.message || '提问失败')
  } finally {
    busy.value = false
  }
}

const submitFinal = async () => {
  if (!answerMessage.value.trim() || busy.value) return
  busy.value = true
  const text = answerMessage.value
  messages.value.push({ content: '【提交答案】' + text, isAI: false })
  answerMessage.value = ''
  scrollToBottom()
  try {
    pushReply(await submitAnswer(roomId.value, text))
  } catch (e) {
    pushReply(e.message || '提交失败')
  } finally {
    busy.value = false
  }
}

const handleNext = async () => {
  if (busy.value) return
  busy.value = true
  try {
    const reply = await nextPuzzle(roomId.value)
    messages.value = []
    ended.value = false
    pushReply(reply)
  } catch (e) {
    pushReply(e.message || '换汤失败')
  } finally {
    busy.value = false
  }
}

const handleEnd = async () => {
  if (busy.value) return
  busy.value = true
  try {
    pushReply(await apiSend(roomId.value, '退出'))
  } catch (e) {
    pushReply(e.message || '结束失败')
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  const boot = sessionStorage.getItem(`room:${roomId.value}:boot`)
  if (boot) {
    sessionStorage.removeItem(`room:${roomId.value}:boot`)
    started.value = true
    pushReply(boot)
  }
})
</script>

<style scoped>
.chat {
  height: 100vh;
  display: grid;
  grid-template-rows: auto 1fr auto;
}

.chat-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.9rem 0;
}

.room-meta {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--muted);
}

.mini-bowl {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
  animation: steam 3.8s ease-in-out infinite;
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.danger {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: 1px solid rgba(196, 92, 74, 0.45);
  background: rgba(196, 92, 74, 0.14);
  color: #f0b2a8;
  border-radius: 999px;
  padding: 0.7rem 1rem;
  cursor: pointer;
}

.chat-main {
  overflow-y: auto;
  padding: 0.5rem 0 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.empty {
  margin: auto;
  text-align: center;
  color: var(--muted);
}

.empty img {
  width: 110px;
  height: 110px;
  border-radius: 50%;
  object-fit: cover;
  opacity: 0.85;
}

.msg {
  display: flex;
  gap: 0.75rem;
  max-width: min(760px, 100%);
  animation: fadeUp 0.35s ease both;
}

.msg.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
  box-shadow: 0 0 0 2px rgba(212, 163, 92, 0.25);
}

.bubble {
  border: 1px solid var(--line);
  background: rgba(19, 40, 48, 0.88);
  border-radius: 16px;
  padding: 0.75rem 0.9rem;
}

.msg.user .bubble {
  background: linear-gradient(160deg, rgba(47, 111, 115, 0.55), rgba(19, 40, 48, 0.92));
}

.who {
  font-size: 0.75rem;
  color: var(--amber);
  margin-bottom: 0.3rem;
}

.text {
  white-space: pre-wrap;
  line-height: 1.6;
}

.chat-input {
  padding: 0.75rem 0 1.1rem;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.input-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 0.55rem;
  align-items: center;
  border: 1px solid var(--line);
  background: rgba(12, 26, 31, 0.85);
  border-radius: 999px;
  padding: 0.35rem 0.4rem 0.35rem 0.9rem;
}

.input-row.answer {
  border-radius: 16px;
}

.lead-icon {
  color: var(--amber);
}

.input-row input {
  border: 0;
  background: transparent;
  color: var(--foam);
  outline: none;
  padding: 0.55rem 0;
}

@media (max-width: 720px) {
  .chat-top {
    flex-wrap: wrap;
  }

  .input-row {
    grid-template-columns: auto 1fr;
  }

  .input-row button {
    grid-column: 1 / -1;
  }
}
</style>
