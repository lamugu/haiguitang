<template>
  <div class="page-shell chat">
    <header class="chat-top page-inner">
      <button class="icon-btn" type="button" aria-label="返回主页" @click="router.push('/')">
        <HomeOutlined />
      </button>
      <div class="room-meta">
        <img src="/assets/brand-bowl.png" alt="" class="mini-bowl" />
        <div class="titles">
          <strong>海龟汤</strong>
          <span>{{ ended ? '本局已结束' : started ? '进行中' : '准备开汤' }}</span>
        </div>
      </div>
      <div class="actions desktop-only">
        <button class="ghost-btn" type="button" :disabled="!started || ended || busy" @click="handleNext">
          <SwapOutlined />
          下一碗
        </button>
        <button class="danger" type="button" :disabled="ended || busy" @click="handleEnd">
          <PoweroffOutlined />
          结束
        </button>
      </div>
      <div class="actions mobile-only">
        <button
          class="ghost-btn"
          type="button"
          :disabled="ended || busy"
          @click="showAnswerSheet = true"
        >
          <BulbOutlined />
          提交
        </button>
        <button
          ref="moreBtnRef"
          class="icon-btn"
          type="button"
          aria-label="更多"
          :aria-expanded="menuOpen"
          @click="toggleMenu"
        >
          <MoreOutlined />
        </button>
      </div>
    </header>

    <Teleport to="body">
      <div v-if="menuOpen" class="menu-mask" @click="menuOpen = false" />
      <div
        v-if="menuOpen"
        class="menu-pop"
        :style="menuStyle"
        @click.stop
      >
        <button type="button" :disabled="!started || ended || busy" @click="runMenu(handleNext)">
          <SwapOutlined /> 下一碗
        </button>
        <button type="button" :disabled="ended || busy" @click="runMenu(handleEnd)">
          <PoweroffOutlined /> 结束并揭底
        </button>
        <button type="button" @click="runMenu(() => router.push('/'))">
          <HomeOutlined /> 回主页
        </button>
      </div>
    </Teleport>

    <main class="chat-main page-inner" ref="listRef">
      <div v-if="!messages.length" class="empty">
        <img src="/assets/empty-bowl.png" alt="" />
        <p>汤还没上桌，稍候…</p>
      </div>
      <div
        v-for="(msg, index) in messages"
        :key="index"
        class="msg"
        :class="[msg.isAI ? 'ai' : 'user', verdictClass(msg)]"
      >
        <img
          :src="msg.isAI ? '/assets/avatar-host.png' : '/assets/avatar-player.png'"
          alt=""
          class="avatar"
        />
        <div class="bubble">
          <div class="who">{{ msg.isAI ? '主持人' : '你' }}</div>
          <div class="text">{{ msg.content }}</div>
          <span v-if="verdictLabel(msg)" class="verdict-pill">{{ verdictLabel(msg) }}</span>
        </div>
      </div>
    </main>

    <footer class="chat-input page-inner">
      <div v-if="!ended && started" class="chip-row">
        <button
          v-for="chip in chips"
          :key="chip"
          class="chip"
          type="button"
          :disabled="busy"
          @click="askChip(chip)"
        >
          {{ chip }}
        </button>
      </div>

      <div class="input-row">
        <QuestionCircleOutlined class="lead-icon" />
        <input
          v-model="inputMessage"
          :disabled="ended || busy"
          placeholder="输入是非问题…"
          enterkeyhint="send"
          @keydown.enter.prevent="sendMessage"
        />
        <button
          class="solid-btn send"
          type="button"
          :disabled="ended || busy || !inputMessage.trim()"
          @click="sendMessage"
        >
          <SendOutlined />
          <span class="send-label">提问</span>
        </button>
      </div>

      <div class="input-row answer desktop-only">
        <BulbOutlined class="lead-icon" />
        <input
          v-model="answerMessage"
          :disabled="ended || busy"
          placeholder="已还原真相？在此提交最终答案"
          @keydown.enter.prevent="submitFinal"
        />
        <button
          class="ghost-btn"
          type="button"
          :disabled="ended || busy || !answerMessage.trim()"
          @click="submitFinal"
        >
          <CheckCircleOutlined />
          提交答案
        </button>
      </div>
    </footer>

    <Teleport to="body">
      <div v-if="showAnswerSheet" class="sheet-mask" @click="showAnswerSheet = false">
        <div class="sheet" @click.stop>
          <div class="sheet-handle" />
          <h3><BulbOutlined /> 提交最终答案</h3>
          <p>认为已还原真相时，写下你的推断。</p>
          <textarea
            v-model="answerMessage"
            rows="4"
            :disabled="ended || busy"
            placeholder="例如：他以为自己又瞎了所以跳车…"
          />
          <div class="sheet-actions">
            <button class="ghost-btn" type="button" @click="showAnswerSheet = false">取消</button>
            <button
              class="solid-btn"
              type="button"
              :disabled="ended || busy || !answerMessage.trim()"
              @click="submitFromSheet"
            >
              <CheckCircleOutlined />
              提交
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="reveal" class="reveal-mask" @click="closeReveal">
        <div class="reveal-card" @click.stop>
          <div class="pot-lid" />
          <img src="/assets/brand-bowl.png" alt="" class="reveal-bowl" />
          <p class="reveal-eyebrow">{{ reveal.prefix || '汤已揭盖' }}</p>
          <h3>汤底</h3>
          <p class="reveal-truth">{{ reveal.truth }}</p>
          <div class="reveal-actions">
            <button class="solid-btn" type="button" :disabled="busy" @click="replayNext">
              <SwapOutlined />
              再来一碗
            </button>
            <button class="ghost-btn" type="button" @click="router.push('/')">回主页</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  BulbOutlined,
  CheckCircleOutlined,
  HomeOutlined,
  MoreOutlined,
  PoweroffOutlined,
  QuestionCircleOutlined,
  SendOutlined,
  SwapOutlined,
} from '@ant-design/icons-vue'
import { nextPuzzle, sendMessage as apiSend, startGame, submitAnswer } from '../api'

const chips = [
  '和死亡有关吗？',
  '是意外吗？',
  '有其他人参与吗？',
  '关键在他看到的东西吗？',
]

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
const menuOpen = ref(false)
const showAnswerSheet = ref(false)
const reveal = ref(null)
const moreBtnRef = ref(null)
const menuPos = ref({ top: 0, right: 12 })

const menuStyle = computed(() => ({
  top: `${menuPos.value.top}px`,
  right: `${menuPos.value.right}px`,
}))

const placeMenu = () => {
  const el = moreBtnRef.value
  const node = el?.$el || el
  if (!node?.getBoundingClientRect) {
    menuPos.value = { top: 64, right: 12 }
    return
  }
  const rect = node.getBoundingClientRect()
  menuPos.value = {
    top: Math.round(rect.bottom + 6),
    right: Math.max(8, Math.round(window.innerWidth - rect.right)),
  }
}

const toggleMenu = async () => {
  if (menuOpen.value) {
    menuOpen.value = false
    return
  }
  menuOpen.value = true
  await nextTick()
  placeMenu()
}

const scrollToBottom = () => {
  nextTick(() => {
    if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
  })
}

const vibrate = (ms = 12) => {
  try {
    if (navigator.vibrate) navigator.vibrate(ms)
  } catch {
    /* ignore */
  }
}

const parseReveal = (content) => {
  const text = String(content || '')
  if (!text.includes('游戏已结束')) return null
  const idx = text.indexOf('汤底：')
  if (idx < 0) return { prefix: text.split('游戏已结束')[0].trim(), truth: text }
  return {
    prefix: text.slice(0, text.indexOf('游戏已结束')).trim() || '汤已揭盖',
    truth: text.slice(idx + 3).trim(),
  }
}

const verdictKind = (msg) => {
  if (!msg?.isAI) return ''
  const t = String(msg.content || '').trim()
  if (t === '是' || t === '是。') return 'yes'
  if (t === '否' || t === '否。') return 'no'
  if (t.startsWith('与此无关')) return 'irrelevant'
  return ''
}

const verdictClass = (msg) => {
  const k = verdictKind(msg)
  return k ? `verdict-${k}` : ''
}

const verdictLabel = (msg) => {
  const map = { yes: '是', no: '否', irrelevant: '无关' }
  return map[verdictKind(msg)] || ''
}

const pushReply = (content) => {
  messages.value.push({ content, isAI: true })
  const kind = verdictKind({ content, isAI: true })
  if (kind === 'yes') vibrate(10)
  if (kind === 'no') vibrate([8, 40, 8])

  const parsed = parseReveal(content)
  if (parsed) {
    ended.value = true
    reveal.value = parsed
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

const askChip = (text) => {
  if (busy.value || ended.value) return
  inputMessage.value = text
  sendMessage()
}

const submitFinal = async () => {
  if (!answerMessage.value.trim() || busy.value) return
  busy.value = true
  const text = answerMessage.value
  messages.value.push({ content: '【提交答案】' + text, isAI: false })
  answerMessage.value = ''
  showAnswerSheet.value = false
  scrollToBottom()
  try {
    pushReply(await submitAnswer(roomId.value, text))
  } catch (e) {
    pushReply(e.message || '提交失败')
  } finally {
    busy.value = false
  }
}

const submitFromSheet = () => submitFinal()

const handleNext = async () => {
  if (busy.value) return
  busy.value = true
  reveal.value = null
  try {
    const reply = await nextPuzzle(roomId.value)
    messages.value = []
    ended.value = false
    pushReply(reply)
    started.value = true
  } catch (e) {
    // 已结束的局无法 next，回到首页重开更稳妥
    if (String(e.message || '').includes('已结束')) {
      router.push('/')
    } else {
      pushReply(e.message || '换汤失败')
    }
  } finally {
    busy.value = false
  }
}

const replayNext = async () => {
  if (busy.value) return
  busy.value = true
  reveal.value = null
  try {
    const newId = Date.now()
    const reply = await startGame(newId)
    roomId.value = String(newId)
    await router.replace({ name: 'chat', params: { roomId: String(newId) } })
    messages.value = []
    ended.value = false
    started.value = true
    pushReply(reply)
  } catch (e) {
    router.push('/')
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

const runMenu = async (fn) => {
  menuOpen.value = false
  await fn()
}

const closeReveal = () => {
  reveal.value = null
}

onMounted(() => {
  const boot = sessionStorage.getItem(`room:${roomId.value}:boot`)
  if (boot) {
    sessionStorage.removeItem(`room:${roomId.value}:boot`)
    started.value = true
    pushReply(boot)
  }
  window.addEventListener('resize', placeMenu)
  window.addEventListener('scroll', placeMenu, true)
})

onUnmounted(() => {
  window.removeEventListener('resize', placeMenu)
  window.removeEventListener('scroll', placeMenu, true)
})
</script>

<style scoped>
.chat {
  height: var(--app-height);
  display: grid;
  grid-template-rows: auto 1fr auto;
  overflow: hidden;
}

.chat-top {
  position: relative;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: calc(0.65rem + var(--safe-top)) 0 0.65rem;
}

.icon-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px solid var(--line);
  background: rgba(232, 242, 240, 0.06);
  color: var(--foam);
  display: inline-grid;
  place-items: center;
  cursor: pointer;
  flex-shrink: 0;
}

.room-meta {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  min-width: 0;
  flex: 1;
  justify-content: center;
}

.titles {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.2;
}

.titles strong {
  font-family: var(--font-display);
  letter-spacing: 0.06em;
}

.titles span {
  font-size: 0.75rem;
  color: var(--muted);
}

.mini-bowl {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
  animation: steam 3.8s ease-in-out infinite;
  flex-shrink: 0;
}

.actions {
  display: flex;
  gap: 0.45rem;
  align-items: center;
  flex-shrink: 0;
}

.danger {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: 1px solid rgba(196, 92, 74, 0.45);
  background: rgba(196, 92, 74, 0.14);
  color: #f0b2a8;
  border-radius: 999px;
  padding: 0.65rem 0.95rem;
  cursor: pointer;
  min-height: 44px;
}

.menu-mask {
  position: fixed;
  inset: 0;
  z-index: 90;
  background: transparent;
}

.menu-pop {
  position: fixed;
  z-index: 95;
  min-width: 168px;
  padding: 0.35rem;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: rgba(12, 26, 31, 0.98);
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.menu-pop button {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  border: 0;
  background: transparent;
  color: var(--foam);
  padding: 0.7rem 0.8rem;
  border-radius: 10px;
  cursor: pointer;
  text-align: left;
  min-height: 44px;
}

.menu-pop button:disabled {
  opacity: 0.4;
}

.menu-pop button:hover:not(:disabled) {
  background: rgba(232, 242, 240, 0.08);
}

.chat-main {
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 0.35rem 0 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  overscroll-behavior: contain;
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
  gap: 0.65rem;
  max-width: min(760px, 100%);
  animation: fadeUp 0.35s ease both;
}

.msg.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
  box-shadow: 0 0 0 2px rgba(212, 163, 92, 0.25);
}

.bubble {
  position: relative;
  border: 1px solid var(--line);
  background: rgba(19, 40, 48, 0.88);
  border-radius: 16px;
  padding: 0.7rem 0.85rem;
  max-width: 100%;
}

.msg.user .bubble {
  background: linear-gradient(160deg, rgba(47, 111, 115, 0.55), rgba(19, 40, 48, 0.92));
}

.msg.verdict-yes .bubble {
  border-color: rgba(111, 191, 138, 0.45);
  box-shadow: 0 0 0 1px rgba(111, 191, 138, 0.12);
}

.msg.verdict-no .bubble {
  border-color: rgba(224, 138, 122, 0.45);
}

.msg.verdict-irrelevant .bubble {
  border-color: rgba(232, 242, 240, 0.18);
  opacity: 0.92;
}

.who {
  font-size: 0.75rem;
  color: var(--amber);
  margin-bottom: 0.25rem;
}

.text {
  white-space: pre-wrap;
  line-height: 1.6;
  word-break: break-word;
}

.verdict-pill {
  display: inline-block;
  margin-top: 0.45rem;
  font-size: 0.72rem;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  letter-spacing: 0.04em;
}

.verdict-yes .verdict-pill {
  background: rgba(111, 191, 138, 0.18);
  color: var(--yes);
}

.verdict-no .verdict-pill {
  background: rgba(224, 138, 122, 0.18);
  color: var(--no);
}

.verdict-irrelevant .verdict-pill {
  background: rgba(232, 242, 240, 0.08);
  color: var(--muted);
}

.chat-input {
  padding: 0.45rem 0 calc(0.75rem + var(--safe-bottom));
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  background: linear-gradient(180deg, transparent, rgba(8, 18, 22, 0.85) 28%);
}

.chip-row {
  display: flex;
  gap: 0.45rem;
  overflow-x: auto;
  padding-bottom: 0.15rem;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}

.chip-row::-webkit-scrollbar {
  display: none;
}

.chip {
  flex-shrink: 0;
  border: 1px solid var(--line);
  background: rgba(47, 111, 115, 0.22);
  color: var(--foam);
  border-radius: 999px;
  padding: 0.4rem 0.75rem;
  font-size: 0.8rem;
  cursor: pointer;
  min-height: 36px;
}

.chip:disabled {
  opacity: 0.45;
}

.input-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 0.45rem;
  align-items: center;
  border: 1px solid var(--line);
  background: rgba(12, 26, 31, 0.92);
  border-radius: 999px;
  padding: 0.3rem 0.35rem 0.3rem 0.85rem;
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
  min-width: 0;
  font-size: 16px; /* 避免 iOS 聚焦缩放 */
}

.send {
  padding: 0.65rem 0.95rem;
}

.sheet-mask,
.reveal-mask {
  position: fixed;
  inset: 0;
  z-index: 80;
  background: rgba(4, 10, 12, 0.62);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: var(--safe-top) var(--safe-right) var(--safe-bottom) var(--safe-left);
  animation: fadeUp 0.25s ease both;
}

.reveal-mask {
  align-items: center;
  padding: 1.25rem;
}

.sheet {
  width: min(520px, 100%);
  background: linear-gradient(180deg, #163038, #0c1a1f);
  border: 1px solid var(--line);
  border-radius: 22px 22px 0 0;
  padding: 0.65rem 1rem calc(1rem + var(--safe-bottom));
  box-shadow: var(--shadow);
}

.sheet-handle {
  width: 42px;
  height: 4px;
  border-radius: 999px;
  background: rgba(232, 242, 240, 0.2);
  margin: 0.2rem auto 0.85rem;
}

.sheet h3 {
  margin: 0 0 0.35rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.sheet p {
  margin: 0 0 0.75rem;
  color: var(--muted);
  font-size: 0.9rem;
}

.sheet textarea {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: rgba(8, 18, 22, 0.7);
  color: var(--foam);
  padding: 0.75rem;
  resize: vertical;
  outline: none;
  font-size: 16px;
}

.sheet-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.55rem;
  margin-top: 0.85rem;
}

.reveal-card {
  width: min(420px, 100%);
  text-align: center;
  background: linear-gradient(165deg, rgba(28, 58, 66, 0.96), rgba(12, 26, 31, 0.98));
  border: 1px solid rgba(212, 163, 92, 0.35);
  border-radius: 22px;
  padding: 1.4rem 1.2rem 1.2rem;
  box-shadow: var(--shadow);
  position: relative;
  animation: fadeUp 0.4s ease both;
}

.pot-lid {
  position: absolute;
  top: -10px;
  left: 50%;
  width: 72px;
  height: 12px;
  border-radius: 999px;
  background: linear-gradient(90deg, #8a6a3d, #e8b86a, #8a6a3d);
  transform: translateX(-50%) rotate(-8deg);
  animation: lidOff 0.7s ease both;
}

.reveal-bowl {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  object-fit: cover;
  margin-bottom: 0.55rem;
  box-shadow: 0 0 0 3px rgba(212, 163, 92, 0.28);
}

.reveal-eyebrow {
  margin: 0;
  color: var(--amber);
  font-size: 0.85rem;
}

.reveal-card h3 {
  font-family: var(--font-display);
  letter-spacing: 0.12em;
  margin: 0.35rem 0 0.75rem;
}

.reveal-truth {
  text-align: left;
  margin: 0 0 1.1rem;
  line-height: 1.65;
  color: var(--foam);
  white-space: pre-wrap;
  background: rgba(8, 18, 22, 0.45);
  border-radius: 14px;
  padding: 0.85rem;
  border: 1px solid var(--line);
}

.reveal-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  justify-content: center;
}

@keyframes lidOff {
  from {
    transform: translateX(-50%) translateY(18px) rotate(0deg);
    opacity: 0.2;
  }
  to {
    transform: translateX(-50%) translateY(0) rotate(-8deg);
    opacity: 1;
  }
}

.mobile-only {
  display: none;
}

.desktop-only {
  display: flex;
}

@media (max-width: 720px) {
  .mobile-only {
    display: flex;
  }

  .desktop-only {
    display: none !important;
  }

  .room-meta {
    justify-content: flex-start;
  }

  .avatar {
    width: 34px;
    height: 34px;
  }

  .send {
    padding: 0.65rem 0.8rem;
  }

  .send-label {
    display: none;
  }
}
</style>
