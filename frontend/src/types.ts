export type DebriefStatus =
  | 'active'
  | 'interviewing'
  | 'awaiting_resolution'
  | 'completed'
  | 'failed'

export interface AgentSession {
  token: string
  agentId: string
  name: string
}

export interface DebriefTurn {
  role: 'assistant' | 'user'
  content: string
  at?: string
  target_gap?: string
  reason?: string
}

export interface ChallengeCandidate {
  node_id: string
  score: number
  hint?: string
}

export interface PendingChallenge {
  type?: 'ambiguity' | 'contradiction'
  entity?: string
  spoken_token?: string
  existing_value?: unknown
  candidate_value?: unknown
  vui_prompt?: string
  candidates?: ChallengeCandidate[]
}

export interface Mutation {
  fact_id?: string
  entity?: string
  value?: unknown
  subject_node_id?: string
  confidence_score?: number
  is_hypothesis?: boolean
  is_conflict_resolution?: boolean
}

export interface DebriefSession {
  session_id: string
  agent_id: string
  status: DebriefStatus
  transcript: string
  staged_mutations: Mutation[]
  pending_challenge: PendingChallenge | null
  turns: DebriefTurn[]
  covered_gaps: string[]
  next_question: string | null
  mode: 'interview' | 'oneshot'
  created_at?: string
}

export interface FeedItem {
  feed_id: string
  agent_id: string
  subject_node_id: string
  script: string
  rationale: string
  gifting_suggestion?: string | null
  status: 'active' | 'held' | 'acked' | 'dismissed'
  held_until?: string | null
  source_event_id?: string | null
  created_at?: string | null
}

export interface Fact {
  fact_id: string
  entity: string
  value: unknown
  confidence_score: number
  is_hypothesis: boolean
  is_conflict_resolution: boolean
  superseded_by?: string | null
  created_at?: string | null
}

export interface Constraint {
  edge_id?: string
  person_node_id?: string
  label: string
  window_start?: string | null
  window_end?: string | null
}

export interface Person {
  node_id: string
  kind: string
  name: string
  aliases: string[]
  attrs: Record<string, unknown>
  last_touched_at?: string
  created_at?: string
  facts?: Fact[]
  constraints?: Constraint[]
  distance?: number
}

export interface RelationshipContext {
  node?: Person
  neighbors?: Person[]
  edges?: Array<{
    edge_id?: string
    src_node_id: string
    dst_node_id: string
    edge_type: string
    rel_label?: string | null
  }>
}

