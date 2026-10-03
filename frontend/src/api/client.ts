export type ApiErrorKind = 'network' | 'validation' | 'road_unavailable' | 'server'
export class ApiError extends Error {
  kind: ApiErrorKind
  status?: number
  constructor(kind: ApiErrorKind, message: string, status?: number) { super(message); this.name = 'ApiError'; this.kind = kind; this.status = status }
}
const base = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
function detailMessage(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map(item => typeof item?.msg === 'string' ? item.msg : 'Invalid input').join('; ')
  return 'Please check your input and try again.'
}
export async function request<T>(path: string, body?: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${base}${path}`, { method: body === undefined ? 'GET' : 'POST', headers: body === undefined ? undefined : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) })
  } catch { throw new ApiError('network', 'Cannot reach the backend. Start FastAPI and try again.') }
  let data: unknown
  try { data = await response.json() } catch { data = null }
  if (!response.ok) {
    const detail = (data && typeof data === 'object' && 'detail' in data) ? data.detail : null
    if (response.status === 422) throw new ApiError('validation', detailMessage(detail), 422)
    if (response.status === 503) throw new ApiError('road_unavailable', 'Road graph unavailable. Robot Lab remains available.', 503)
    throw new ApiError('server', `Backend request failed (${response.status}).`, response.status)
  }
  return data as T
}
export function errorText(error: unknown): string { return error instanceof ApiError ? error.message : 'An unexpected error occurred.' }
