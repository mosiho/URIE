import type {
  AgentSession,
  Constraint,
  DebriefSession,
  FeedItem,
  Person,
  RelationshipContext,
} from './types'

export class ApiError extends Error {
  status: number

  constructor(
    message: string,
    status: number,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(
  path: string,
  token?: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let response: Response
  try {
    response = await fetch(path, { ...options, headers })
  } catch {
    throw new ApiError('We could not reach URIE. Check your connection and try again.', 0)
  }

  const text = await response.text()
  let body: unknown = null
  try {
    body = text ? JSON.parse(text) : null
  } catch {
    body = text
  }

  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event('urie:unauthorized'))
    const detail =
      typeof body === 'object' && body && 'detail' in body
        ? (body as { detail: unknown }).detail
        : body
    throw new ApiError(
      typeof detail === 'string' ? detail : 'Something went wrong. Please try again.',
      response.status,
    )
  }

  return body as T
}

export const api = {
  async signIn(agentId: string, name: string): Promise<AgentSession> {
    const result = await request<{ access_token: string; agent_id: string }>(
      '/v1/auth/token',
      undefined,
      {
        method: 'POST',
        body: JSON.stringify({ agent_id: agentId, name }),
      },
    )
    return { token: result.access_token, agentId: result.agent_id, name }
  },

  startDebrief(token: string) {
    return request<DebriefSession>('/v1/debriefs', token, {
      method: 'POST',
      body: JSON.stringify({ mode: 'interview' }),
    })
  },

  submitTurn(token: string, sessionId: string, text: string) {
    return request<DebriefSession>(`/v1/debriefs/${sessionId}/turn`, token, {
      method: 'POST',
      body: JSON.stringify({ text }),
    })
  },

  resolveChallenge(
    token: string,
    sessionId: string,
    body: {
      resolution_note: string
      accepted_value?: unknown
      chosen_node_id?: string
      create_new?: boolean
    },
  ) {
    return request<DebriefSession>(`/v1/debriefs/${sessionId}/resolve`, token, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },

  finishDebrief(token: string, sessionId: string) {
    return request<DebriefSession>(`/v1/debriefs/${sessionId}/finish`, token, {
      method: 'POST',
    })
  },

  listFeed(token: string, includeHeld = true) {
    return request<FeedItem[]>(`/v1/feed?include_held=${includeHeld}`, token)
  },

  acknowledgeFeed(token: string, feedId: string, action: 'acked' | 'dismissed') {
    return request<FeedItem>(`/v1/feed/${feedId}/ack`, token, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
  },

  listPeople(token: string, query = '') {
    const params = new URLSearchParams({ kind: 'Person' })
    if (query.trim()) params.set('q', query.trim())
    return request<Person[]>(`/v1/nodes?${params}`, token)
  },

  getPerson(token: string, nodeId: string) {
    return request<Person>(`/v1/nodes/${nodeId}`, token)
  },

  getContext(token: string, nodeId: string) {
    return request<RelationshipContext>(`/v1/nodes/${nodeId}/context`, token)
  },

  listConstraints(token: string, nodeId: string) {
    return request<Constraint[]>(`/v1/constraints?person_node_id=${encodeURIComponent(nodeId)}`, token)
  },

  createConstraint(
    token: string,
    body: {
      person_node_id: string
      label: string
      window_start?: string
      window_end?: string
    },
  ) {
    return request<Constraint>('/v1/constraints', token, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },

  writeBack(token: string, factId: string, note: string) {
    return request<{ writeback_id: string }>('/v1/crm/writeback', token, {
      method: 'POST',
      body: JSON.stringify({ fact_id: factId, note, crm_target: 'stub' }),
    })
  },
}

