<template>
  <div class="page-shell admin">
    <div class="page-inner">
      <header class="topbar fade-up">
        <button class="ghost-btn" type="button" @click="router.push('/')">
          <ArrowLeftOutlined />
          返回主页
        </button>
        <div class="brand-mark">
          <img src="/assets/brand-bowl.png" alt="" />
          <span>汤库管理</span>
        </div>
        <div class="stat" v-if="authed">
          <DatabaseOutlined />
          共 {{ total }} 道
          <button class="ghost-btn logout" type="button" @click="logout">退出</button>
        </div>
      </header>

      <section v-if="!authed" class="panel login-panel fade-up">
        <h2><LockOutlined /> 管理员登录</h2>
        <p class="desc">管理端需要密钥。密钥配置在服务端环境变量 <code>ADMIN_KEY</code>。</p>
        <div class="login-row">
          <input
            v-model="adminKeyInput"
            type="password"
            placeholder="输入 ADMIN_KEY"
            @keydown.enter.prevent="doLogin"
          />
          <button class="solid-btn" type="button" :disabled="loggingIn || !adminKeyInput.trim()" @click="doLogin">
            {{ loggingIn ? '验证中…' : '进入' }}
          </button>
        </div>
        <p v-if="loginError" class="hint err">{{ loginError }}</p>
      </section>

      <template v-else>
      <section class="panel fade-up" style="animation-delay: 0.06s">
        <h2><FormOutlined /> 新增单条</h2>
        <div class="form-grid">
          <label>
            <span>汤面</span>
            <textarea v-model="form.surface" rows="3" placeholder="公开的表面故事" />
          </label>
          <label>
            <span>汤底</span>
            <textarea v-model="form.truth" rows="3" placeholder="仅主持人可见的真相" />
          </label>
        </div>
        <div class="tag-picker">
          <span class="label"><TagsOutlined /> 分类标签</span>
          <div class="tag-row">
            <button
              v-for="tag in suggestedTags"
              :key="tag"
              type="button"
              class="tag-chip"
              :class="{ active: form.tags.includes(tag) }"
              @click="toggleTag(form.tags, tag)"
            >
              {{ tag }}
            </button>
          </div>
          <input v-model="customTag" placeholder="自定义标签，回车添加" @keydown.enter.prevent="addCustom(form.tags)" />
        </div>
        <button class="solid-btn" type="button" :disabled="adding || !canAdd" @click="doAdd">
          <PlusOutlined />
          {{ adding ? '加入中…' : '加入题库' }}
        </button>
        <span v-if="addMsg" class="hint">{{ addMsg }}</span>
      </section>

      <section class="panel fade-up" style="animation-delay: 0.12s">
        <h2><ImportOutlined /> 批量添加</h2>
        <p class="desc">每行一碗，格式：`汤面 | 汤底 | 标签1,标签2`（标签可省略）</p>
        <textarea
          v-model="batchText"
          rows="7"
          placeholder="一个人走进餐厅…… | 真相…… | 经典,惊悚"
        />
        <button class="solid-btn" type="button" :disabled="batching || !batchText.trim()" @click="doBatch">
          <CloudUploadOutlined />
          {{ batching ? '提交中…' : '批量写入' }}
        </button>
        <span v-if="batchMsg" class="hint">{{ batchMsg }}</span>
      </section>

      <section class="panel fade-up" style="animation-delay: 0.18s">
        <h2><FileTextOutlined /> 粘贴导入</h2>
        <p class="desc">粘贴网页/笔记原文，服务端自动抽取汤面、汤底与分类（不在前端暴露模型细节）。</p>
        <textarea v-model="importText" rows="6" placeholder="把抓取到的海龟汤内容粘贴到这里" />
        <button class="solid-btn" type="button" :disabled="importing || !importText.trim()" @click="doImport">
          <ThunderboltOutlined />
          {{ importing ? '抽取中…' : '开始导入' }}
        </button>
        <span v-if="importResult && !importResult.done" class="hint progress">
          第 {{ importResult.chunkDone }} / {{ importResult.chunks }} 段，已识别 {{ importResult.extracted }} 条
        </span>
        <span v-else-if="importResult && importResult.done" class="hint ok">
          抽取 {{ importResult.extracted }} 条，新增 {{ importResult.imported }} 条，题库共 {{ importResult.total }} 条
        </span>
      </section>

      <section class="panel list-panel fade-up" style="animation-delay: 0.24s">
        <div class="list-head">
          <h2><UnorderedListOutlined /> 题目列表</h2>
          <button class="ghost-btn" type="button" :disabled="loading" @click="refresh">
            <ReloadOutlined />
            刷新
          </button>
        </div>

        <div class="filter-row">
          <button
            class="tag-chip"
            :class="{ active: !filterTag }"
            type="button"
            @click="filterTag = ''"
          >全部</button>
          <button
            v-for="t in allTags"
            :key="t"
            class="tag-chip"
            :class="{ active: filterTag === t }"
            type="button"
            @click="filterTag = t"
          >{{ t }}</button>
        </div>

        <div v-if="loading" class="state">加载中…</div>
        <div v-else class="table">
          <article v-for="item in filteredItems" :key="item.index" class="row">
            <div class="row-main">
              <div class="row-top">
                <strong>#{{ item.index + 1 }}</strong>
                <div class="row-tags">
                  <span v-for="tag in item.tags" :key="tag">{{ tag }}</span>
                </div>
              </div>
              <p class="surface">{{ item.surface }}</p>
              <p class="truth">{{ item.truth }}</p>
            </div>
            <div class="row-actions">
              <button class="ghost-btn" type="button" @click="openEdit(item)"><EditOutlined /> 编辑</button>
              <button class="danger-btn" type="button" @click="doDelete(item.index)"><DeleteOutlined /> 删除</button>
            </div>
          </article>
        </div>
      </section>
      </template>
    </div>

    <div v-if="editing" class="modal" @click.self="editing = null">
      <div class="modal-card">
        <h3>编辑 #{{ editing.index + 1 }}</h3>
        <label>
          <span>汤面</span>
          <textarea v-model="editing.surface" rows="3" />
        </label>
        <label>
          <span>汤底</span>
          <textarea v-model="editing.truth" rows="3" />
        </label>
        <div class="tag-picker">
          <div class="tag-row">
            <button
              v-for="tag in suggestedTags"
              :key="tag"
              type="button"
              class="tag-chip"
              :class="{ active: editing.tags.includes(tag) }"
              @click="toggleTag(editing.tags, tag)"
            >{{ tag }}</button>
          </div>
        </div>
        <div class="modal-actions">
          <button class="ghost-btn" type="button" @click="editing = null">取消</button>
          <button class="solid-btn" type="button" @click="saveEdit">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowLeftOutlined,
  CloudUploadOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  EditOutlined,
  FileTextOutlined,
  FormOutlined,
  ImportOutlined,
  LockOutlined,
  PlusOutlined,
  ReloadOutlined,
  TagsOutlined,
  ThunderboltOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons-vue'
import {
  addPuzzle,
  batchAddPuzzles,
  clearAdminKey,
  deletePuzzle,
  fetchStats,
  getAdminKey,
  importPuzzles,
  importStatus,
  listAdminPuzzles,
  updatePuzzle,
  verifyAdminKey,
} from '../api'

const router = useRouter()
const authed = ref(false)
const adminKeyInput = ref('')
const loggingIn = ref(false)
const loginError = ref('')
const total = ref(0)
const items = ref([])
const suggestedTags = ref(['经典', '悬疑', '惊悚', '温情', '烧脑', '奇幻', '日常'])
const loading = ref(false)
const filterTag = ref('')
const form = reactive({ surface: '', truth: '', tags: [] })
const customTag = ref('')
const adding = ref(false)
const addMsg = ref('')
const batchText = ref('')
const batching = ref(false)
const batchMsg = ref('')
const importText = ref('')
const importing = ref(false)
const importResult = ref(null)
const editing = ref(null)

const canAdd = computed(() => form.surface.trim() && form.truth.trim())
const allTags = computed(() => {
  const set = new Set()
  items.value.forEach((i) => (i.tags || []).forEach((t) => set.add(t)))
  return [...set]
})
const filteredItems = computed(() => {
  if (!filterTag.value) return items.value
  return items.value.filter((i) => (i.tags || []).includes(filterTag.value))
})

const toggleTag = (list, tag) => {
  const idx = list.indexOf(tag)
  if (idx >= 0) list.splice(idx, 1)
  else list.push(tag)
}

const addCustom = (list) => {
  const name = customTag.value.trim()
  if (!name) return
  if (!list.includes(name)) list.push(name)
  if (!suggestedTags.value.includes(name)) suggestedTags.value.push(name)
  customTag.value = ''
}

const doLogin = async () => {
  loggingIn.value = true
  loginError.value = ''
  try {
    await verifyAdminKey(adminKeyInput.value.trim())
    authed.value = true
    adminKeyInput.value = ''
    await refresh()
  } catch (e) {
    loginError.value = e.message || '密钥无效'
    authed.value = false
  } finally {
    loggingIn.value = false
  }
}

const logout = () => {
  clearAdminKey()
  authed.value = false
  items.value = []
  total.value = 0
}

const refresh = async () => {
  loading.value = true
  try {
    const [stats, list] = await Promise.all([fetchStats(), listAdminPuzzles()])
    total.value = list.total
    items.value = list.items
    if (stats.suggestedTags?.length) suggestedTags.value = stats.suggestedTags
  } catch (e) {
    if (String(e.message || '').includes('密钥') || String(e.message || '').includes('401') || String(e.message || '').includes('无效')) {
      logout()
      loginError.value = e.message || '请重新登录'
    } else {
      alert(e.message || '加载失败')
    }
  } finally {
    loading.value = false
  }
}

const doAdd = async () => {
  adding.value = true
  addMsg.value = ''
  try {
    const res = await addPuzzle({
      surface: form.surface,
      truth: form.truth,
      tags: [...form.tags],
    })
    if (!res.ok) {
      addMsg.value = res.message || '添加失败'
      return
    }
    addMsg.value = `已加入，题库共 ${res.total} 道`
    form.surface = ''
    form.truth = ''
    form.tags = []
    await refresh()
  } catch (e) {
    addMsg.value = e.message || '添加失败'
  } finally {
    adding.value = false
  }
}

const parseBatch = (text) => {
  return text
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const parts = line.split('|').map((p) => p.trim())
      return {
        surface: parts[0] || '',
        truth: parts[1] || '',
        tags: (parts[2] || '')
          .split(/[,，]/)
          .map((t) => t.trim())
          .filter(Boolean),
      }
    })
    .filter((p) => p.surface && p.truth)
}

const doBatch = async () => {
  batching.value = true
  batchMsg.value = ''
  try {
    const parsed = parseBatch(batchText.value)
    if (!parsed.length) {
      batchMsg.value = '没有可解析的条目'
      return
    }
    const res = await batchAddPuzzles(parsed)
    batchMsg.value = `新增 ${res.imported} 条，题库共 ${res.total} 条`
    batchText.value = ''
    await refresh()
  } catch (e) {
    batchMsg.value = e.message || '批量失败'
  } finally {
    batching.value = false
  }
}

const doImport = async () => {
  importing.value = true
  importResult.value = null
  try {
    const job = await importPuzzles(importText.value)
    importText.value = ''
    const poll = async () => {
      const status = await importStatus(job.jobId)
      importResult.value = status
      if (!status.done) {
        setTimeout(poll, 1500)
      } else {
        importing.value = false
        if (status.error) alert('导入失败：' + status.error)
        await refresh()
      }
    }
    poll()
  } catch (e) {
    importing.value = false
    alert(e.message || '导入失败')
  }
}

const openEdit = (item) => {
  editing.value = {
    index: item.index,
    surface: item.surface,
    truth: item.truth,
    tags: [...(item.tags || [])],
  }
}

const saveEdit = async () => {
  if (!editing.value) return
  try {
    const res = await updatePuzzle(editing.value.index, {
      surface: editing.value.surface,
      truth: editing.value.truth,
      tags: editing.value.tags,
    })
    if (!res.ok) {
      alert(res.message || '更新失败')
      return
    }
    editing.value = null
    await refresh()
  } catch (e) {
    alert(e.message || '更新失败')
  }
}

const doDelete = async (index) => {
  if (!confirm('确定删除这碗汤？')) return
  try {
    await deletePuzzle(index)
    await refresh()
  } catch (e) {
    alert(e.message || '删除失败')
  }
}

onMounted(async () => {
  if (getAdminKey()) {
    try {
      await verifyAdminKey(getAdminKey())
      authed.value = true
      await refresh()
    } catch {
      clearAdminKey()
      authed.value = false
    }
  }
})
</script>

<style scoped>
.admin {
  padding-bottom: 3rem;
}

.topbar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 1.2rem 0 1.4rem;
}

.topbar .brand-mark {
  justify-self: center;
  font-size: 1.35rem;
}

.stat {
  justify-self: end;
  color: var(--muted);
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.stat .logout {
  margin-left: 0.5rem;
  padding: 0.35rem 0.75rem;
  font-size: 0.85rem;
}

.login-panel .login-row {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.login-panel input[type='password'] {
  flex: 1;
  min-width: 220px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: rgba(232, 242, 240, 0.04);
  color: var(--foam);
  padding: 0.75rem 0.85rem;
}

.hint.err {
  color: #f0b2a8;
  margin-left: 0;
  margin-top: 0.6rem;
  display: block;
}

.panel {
  border: 1px solid var(--line);
  background: rgba(12, 26, 31, 0.72);
  border-radius: var(--radius);
  padding: 1.2rem 1.25rem 1.35rem;
  margin-bottom: 1rem;
  backdrop-filter: blur(8px);
}

.panel h2 {
  margin: 0 0 0.85rem;
  font-size: 1.15rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.desc {
  margin: -0.35rem 0 0.8rem;
  color: var(--muted);
  font-size: 0.92rem;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.85rem;
}

label {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-bottom: 0.75rem;
}

label span,
.tag-picker .label {
  color: var(--muted);
  font-size: 0.88rem;
}

textarea,
input {
  width: 100%;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: rgba(232, 242, 240, 0.04);
  color: var(--foam);
  padding: 0.75rem 0.85rem;
  resize: vertical;
}

.tag-picker {
  margin: 0.4rem 0 1rem;
}

.tag-row,
.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin: 0.45rem 0 0.7rem;
}

.hint {
  margin-left: 0.75rem;
  color: var(--muted);
}

.hint.ok,
.hint.progress {
  color: var(--amber);
}

.list-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.row {
  display: flex;
  gap: 1rem;
  justify-content: space-between;
  border-top: 1px solid var(--line);
  padding: 1rem 0;
}

.row-top {
  display: flex;
  gap: 0.7rem;
  align-items: center;
  margin-bottom: 0.45rem;
}

.row-tags span {
  font-size: 0.75rem;
  margin-right: 0.3rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  background: rgba(212, 163, 92, 0.12);
  color: var(--amber);
}

.surface {
  margin: 0 0 0.35rem;
  line-height: 1.5;
}

.truth {
  margin: 0;
  color: rgba(232, 242, 240, 0.45);
  font-style: italic;
  line-height: 1.5;
}

.row-actions {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  flex-shrink: 0;
}

.danger-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: 1px solid rgba(196, 92, 74, 0.45);
  background: rgba(196, 92, 74, 0.12);
  color: #f0b2a8;
  border-radius: 999px;
  padding: 0.55rem 0.9rem;
  cursor: pointer;
}

.modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: grid;
  place-items: center;
  z-index: 20;
  padding: 1rem;
}

.modal-card {
  width: min(560px, 100%);
  background: #102228;
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 1.2rem;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
  margin-top: 0.5rem;
}

.state {
  color: var(--muted);
  padding: 1rem 0;
}

@media (max-width: 800px) {
  .form-grid,
  .topbar {
    grid-template-columns: 1fr;
  }

  .topbar .brand-mark,
  .stat,
  .topbar .ghost-btn {
    justify-self: start;
  }

  .row {
    flex-direction: column;
  }

  .row-actions {
    flex-direction: row;
  }
}
</style>
