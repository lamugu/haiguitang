import axios from 'axios'

const ADMIN_KEY_STORAGE = 'haiguitang:adminKey'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 60000,
})

http.interceptors.request.use((config) => {
  const key = sessionStorage.getItem(ADMIN_KEY_STORAGE)
  if (key) {
    config.headers = config.headers || {}
    config.headers['X-Admin-Key'] = key
  }
  return config
})

http.interceptors.response.use(
  (res) => res,
  (err) => {
    const message = err?.response?.data?.message || err?.response?.data?.detail || err.message || '请求失败'
    return Promise.reject(new Error(typeof message === 'string' ? message : '请求失败'))
  },
)

export type TagStat = { name: string; count: number }

export type CatalogItem = {
  index: number
  surface: string
  tags: string[]
}

export type AdminPuzzle = CatalogItem & { truth: string }

export function getAdminKey() {
  return sessionStorage.getItem(ADMIN_KEY_STORAGE) || ''
}

export function setAdminKey(key: string) {
  sessionStorage.setItem(ADMIN_KEY_STORAGE, key)
}

export function clearAdminKey() {
  sessionStorage.removeItem(ADMIN_KEY_STORAGE)
}

export async function verifyAdminKey(key: string) {
  setAdminKey(key)
  try {
    const { data } = await http.post('/admin/verify')
    return data as { ok: boolean }
  } catch (e) {
    clearAdminKey()
    throw e
  }
}

export async function fetchStats() {
  const { data } = await http.get('/puzzles/stats')
  return data as { total: number; tags: TagStat[]; suggestedTags: string[] }
}

export async function fetchCatalog(tag?: string) {
  const { data } = await http.get('/puzzles/catalog', { params: tag ? { tag } : {} })
  return data as { total: number; items: CatalogItem[]; tags: TagStat[] }
}

export async function startGame(roomId: number | string, opts?: { puzzleIndex?: number; tag?: string }) {
  const { data } = await http.post(
    `/chat/${roomId}/start`,
    null,
    { params: { puzzleIndex: opts?.puzzleIndex, tag: opts?.tag } },
  )
  return data as string
}

export async function sendMessage(roomId: number | string, message: string) {
  const { data } = await http.post(`/chat/${roomId}/send`, null, { params: { message } })
  return data as string
}

export async function submitAnswer(roomId: number | string, answer: string) {
  const { data } = await http.post(`/chat/${roomId}/submit`, null, { params: { answer } })
  return data as string
}

export async function nextPuzzle(roomId: number | string, tag?: string) {
  const { data } = await http.post(`/chat/${roomId}/next`, null, { params: tag ? { tag } : {} })
  return data as string
}

export async function listAdminPuzzles() {
  const { data } = await http.get('/puzzles/list')
  return data as { total: number; items: AdminPuzzle[] }
}

export async function addPuzzle(payload: { surface: string; truth: string; tags: string[] }) {
  const { data } = await http.post('/puzzles/add/json', payload)
  return data as { ok: boolean; total?: number; message?: string }
}

export async function batchAddPuzzles(items: { surface: string; truth: string; tags: string[] }[]) {
  const { data } = await http.post('/puzzles/batch', { items })
  return data as { ok: boolean; imported: number; total: number }
}

export async function updatePuzzle(
  index: number,
  payload: { surface?: string; truth?: string; tags?: string[] },
) {
  const { data } = await http.put(`/puzzles/${index}`, payload)
  return data as { ok: boolean; message?: string }
}

export async function deletePuzzle(index: number) {
  const { data } = await http.delete(`/puzzles/${index}`)
  return data as { ok: boolean; total?: number; message?: string }
}

export async function importPuzzles(text: string) {
  const { data } = await http.post('/puzzles/import', null, { params: { text } })
  return data as {
    jobId: string
    chunks: number
    chunkDone: number
    extracted: number
    imported: number
    total: number
    done: boolean
    error: string
  }
}

export async function importStatus(jobId: string) {
  const { data } = await http.get('/puzzles/import/status', { params: { jobId } })
  return data as {
    jobId: string
    chunks: number
    chunkDone: number
    extracted: number
    imported: number
    total: number
    done: boolean
    error: string
  }
}

export type TagPlan = {
  merges: Record<string, string>
  deletes: string[]
  canonical: string[]
  notes: string[]
  source?: string
}

export async function suggestTagCleanup(mode: 'llm' | 'rules' = 'llm') {
  const { data } = await http.post('/puzzles/tags/suggest', null, {
    params: { mode },
    timeout: 120000,
  })
  return data as TagPlan
}

export async function applyTagCleanup(payload: { merges: Record<string, string>; deletes: string[] }) {
  const { data } = await http.post('/puzzles/tags/apply', payload)
  return data as { ok: boolean; updated: number; tags: TagStat[] }
}

export async function renameTag(from: string, to: string) {
  const { data } = await http.post('/puzzles/tags/rename', { from, to })
  return data as { ok: boolean; updated?: number; message?: string; tags?: TagStat[] }
}

export async function deleteTag(name: string) {
  const { data } = await http.post('/puzzles/tags/delete', { name })
  return data as { ok: boolean; updated?: number; message?: string; tags?: TagStat[] }
}
