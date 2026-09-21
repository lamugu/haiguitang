<template>
  <div class="page-shell home">
    <header class="topbar page-inner fade-up">
      <div class="brand-mark">
        <img src="/assets/brand-bowl.png" alt="海龟汤" class="steam-icon" />
        <span>海龟汤</span>
      </div>
      <button class="ghost-btn" type="button" @click="router.push('/admin')">
        <SettingOutlined />
        汤库管理
      </button>
    </header>

    <section class="hero page-inner">
      <div class="hero-copy fade-up" style="animation-delay: 0.08s">
        <p class="eyebrow"><FireOutlined /> 问是与否 · 还原真相</p>
        <h1>海龟汤</h1>
        <p class="lead">
          主持人只回答「是」「否」或「与此无关」。快速开一碗，或按分类挑选你想挑战的汤面。
        </p>
        <div class="cta-row">
          <button class="solid-btn" type="button" :disabled="starting" @click="quickStart()">
            <ThunderboltOutlined />
            {{ starting ? '正在开汤…' : '快速开始' }}
          </button>
          <a class="ghost-btn" href="#catalog">
            <AppstoreOutlined />
            选一碗汤
          </a>
          <button
            v-if="activeTag"
            class="ghost-btn"
            type="button"
            :disabled="starting"
            @click="quickStart(activeTag)"
          >
            <TagsOutlined />
            从「{{ activeTag }}」随机
          </button>
        </div>
        <p class="meta"><CoffeeOutlined /> 题库现有 {{ total }} 道 · {{ tagSummary }}</p>
      </div>
      <div class="hero-visual fade-up" style="animation-delay: 0.16s">
        <img src="/assets/hero-bg.png" alt="" class="hero-img" />
        <div class="hero-glow" />
      </div>
    </section>

    <section id="catalog" class="catalog page-inner fade-up" style="animation-delay: 0.24s">
      <div class="section-head">
        <h2><FilterOutlined /> 按分类选汤</h2>
        <p>汤底不会提前泄露，点选即开局。</p>
      </div>

      <div class="tag-row">
        <button
          class="tag-chip"
          :class="{ active: !activeTag }"
          type="button"
          @click="selectTag('')"
        >
          <TagsOutlined /> 全部 {{ total }}
        </button>
        <button
          v-for="t in tags"
          :key="t.name"
          class="tag-chip"
          :class="{ active: activeTag === t.name }"
          type="button"
          @click="selectTag(t.name)"
        >
          {{ t.name }} {{ t.count }}
        </button>
      </div>

      <div v-if="loading" class="state">加载题库中…</div>
      <div v-else-if="!items.length" class="state empty">
        <img src="/assets/empty-bowl.png" alt="" />
        <p>这个分类还空着，去管理页加几碗吧。</p>
      </div>
      <div v-else class="puzzle-grid">
        <button
          v-for="item in items"
          :key="item.index"
          class="puzzle-card"
          type="button"
          :disabled="starting"
          @click="startSelected(item.index)"
        >
          <div class="card-top">
            <span class="idx">#{{ item.index + 1 }}</span>
            <PlayCircleOutlined class="play" />
          </div>
          <p class="surface">{{ item.surface }}</p>
          <div class="card-tags">
            <span v-for="tag in item.tags" :key="tag">{{ tag }}</span>
          </div>
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  AppstoreOutlined,
  CoffeeOutlined,
  FilterOutlined,
  FireOutlined,
  PlayCircleOutlined,
  SettingOutlined,
  TagsOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons-vue'
import { fetchCatalog, fetchStats, startGame } from '../api'

const router = useRouter()
const total = ref(0)
const tags = ref([])
const items = ref([])
const activeTag = ref('')
const loading = ref(false)
const starting = ref(false)

const tagSummary = computed(() => {
  if (!tags.value.length) return '分类筹备中'
  return tags.value.slice(0, 4).map((t) => t.name).join(' · ')
})

const loadStats = async () => {
  const data = await fetchStats()
  total.value = data.total
  tags.value = data.tags || []
}

const loadCatalog = async () => {
  loading.value = true
  try {
    const data = await fetchCatalog(activeTag.value || undefined)
    items.value = data.items
    tags.value = data.tags || tags.value
    if (!activeTag.value) total.value = data.total
  } finally {
    loading.value = false
  }
}

const selectTag = async (name) => {
  activeTag.value = name
  await loadCatalog()
}

const goChat = (roomId) => {
  router.push({ name: 'chat', params: { roomId: String(roomId) } })
}

const quickStart = async (tag) => {
  starting.value = true
  try {
    const roomId = Date.now()
    const reply = await startGame(roomId, tag ? { tag } : undefined)
    sessionStorage.setItem(`room:${roomId}:boot`, reply)
    goChat(roomId)
  } catch (e) {
    alert(e.message || '开局失败')
  } finally {
    starting.value = false
  }
}

const startSelected = async (puzzleIndex) => {
  starting.value = true
  try {
    const roomId = Date.now()
    const reply = await startGame(roomId, { puzzleIndex })
    sessionStorage.setItem(`room:${roomId}:boot`, reply)
    goChat(roomId)
  } catch (e) {
    alert(e.message || '开局失败')
  } finally {
    starting.value = false
  }
}

onMounted(async () => {
  try {
    await loadStats()
    await loadCatalog()
  } catch (e) {
    console.error(e)
  }
})
</script>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 0 0.5rem;
}

.brand-mark {
  font-size: 1.35rem;
  color: var(--foam);
}

.steam-icon {
  animation: steam 3.6s ease-in-out infinite;
}

.hero {
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  gap: 2rem;
  align-items: center;
  min-height: min(72vh, 720px);
  padding: 1.5rem 0 2.5rem;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--amber);
  margin: 0 0 0.8rem;
  font-size: 0.95rem;
}

.hero-copy h1 {
  font-family: var(--font-display);
  font-size: clamp(3.2rem, 8vw, 5.4rem);
  line-height: 1;
  margin: 0 0 1rem;
  letter-spacing: 0.08em;
}

.lead {
  color: var(--muted);
  font-size: 1.05rem;
  line-height: 1.7;
  max-width: 34rem;
  margin: 0 0 1.5rem;
}

.cta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.meta {
  color: rgba(232, 242, 240, 0.5);
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.hero-visual {
  position: relative;
  min-height: 320px;
}

.hero-img {
  width: 100%;
  height: min(58vh, 520px);
  object-fit: cover;
  border-radius: 28px 8px 28px 8px;
  box-shadow: var(--shadow);
  display: block;
}

.hero-glow {
  position: absolute;
  inset: auto 12% -8% 12%;
  height: 40%;
  background: radial-gradient(circle, rgba(212, 163, 92, 0.35), transparent 70%);
  filter: blur(18px);
  pointer-events: none;
}

.catalog {
  padding: 0 0 4rem;
}

.section-head h2 {
  margin: 0 0 0.35rem;
  font-size: 1.45rem;
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.section-head p {
  margin: 0 0 1.1rem;
  color: var(--muted);
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-bottom: 1.25rem;
}

.puzzle-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 1rem;
}

.puzzle-card {
  text-align: left;
  border: 1px solid var(--line);
  background: linear-gradient(180deg, rgba(28, 58, 66, 0.72), rgba(12, 26, 31, 0.88));
  color: inherit;
  border-radius: var(--radius);
  padding: 1rem 1.05rem 1.1rem;
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.puzzle-card:hover {
  transform: translateY(-3px);
  border-color: rgba(212, 163, 92, 0.45);
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.28);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.7rem;
  color: var(--muted);
}

.play {
  color: var(--amber);
  font-size: 1.15rem;
}

.surface {
  margin: 0 0 0.9rem;
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 6.2em;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.card-tags span {
  font-size: 0.75rem;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  background: rgba(212, 163, 92, 0.12);
  color: var(--amber);
}

.state {
  padding: 2.5rem 1rem;
  text-align: center;
  color: var(--muted);
}

.empty img {
  width: 120px;
  height: 120px;
  object-fit: cover;
  border-radius: 50%;
  opacity: 0.85;
  margin-bottom: 0.75rem;
}

@media (max-width: 900px) {
  .hero {
    grid-template-columns: 1fr;
    min-height: auto;
    gap: 1.25rem;
  }

  .hero-img {
    height: 42vw;
    min-height: 220px;
  }
}
</style>
