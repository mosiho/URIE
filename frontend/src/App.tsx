import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  ArrowUpRight,
  BookOpen,
  CalendarClock,
  Check,
  ChevronRight,
  CirclePause,
  Clock3,
  Copy,
  Ellipsis,
  Gift,
  Home,
  Lightbulb,
  Link2,
  MessageCircle,
  Mic,
  Network,
  Plus,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  Users,
} from 'lucide-react'
import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import {
  Link,
  NavLink,
  Navigate,
  Route,
  Routes,
  useNavigate,
  useParams,
} from 'react-router-dom'
import { api } from './api'
import { useAuth } from './auth'
import LandingPage from './LandingPage'
import type { DebriefSession, FeedItem, Mutation, Person } from './types'
import {
  Avatar,
  Badge,
  Button,
  Dialog,
  EmptyState,
  ErrorState,
  IconButton,
  LoadingCards,
  Logo,
  PageHeader,
  Skeleton,
  SuccessNotice,
} from './ui'

const dateFormatter = new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric' })
const timeFormatter = new Intl.DateTimeFormat('en', { hour: 'numeric', minute: '2-digit' })

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.'
}

function formatDate(value?: string | null) {
  if (!value) return 'No date'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'No date' : dateFormatter.format(date)
}

function formatFactValue(value: unknown): string {
  if (value === null || value === undefined) return 'Not specified'
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  if (Array.isArray(value)) return value.map(formatFactValue).join(', ')
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    const amount = entries.find(([key]) => key === 'amount')
    const currency = entries.find(([key]) => key === 'currency')
    if (amount) {
      const numeric = Number(amount[1])
      const shown = Number.isFinite(numeric) ? numeric.toLocaleString('en') : String(amount[1])
      return `${currency ? `${currency[1]} ` : ''}${shown}`
    }
    return entries.map(([key, item]) => `${key.replaceAll('_', ' ')}: ${formatFactValue(item)}`).join(' · ')
  }
  return String(value)
}

function useOnlineStatus() {
  const [online, setOnline] = useState(navigator.onLine)
  useEffect(() => {
    const connect = () => setOnline(true)
    const disconnect = () => setOnline(false)
    window.addEventListener('online', connect)
    window.addEventListener('offline', disconnect)
    return () => {
      window.removeEventListener('online', connect)
      window.removeEventListener('offline', disconnect)
    }
  }, [])
  return online
}

function SignIn() {
  const { setSession } = useAuth()
  const [agentId, setAgentId] = useState('agt_demo')
  const [name, setName] = useState('Demo Agent')
  const mutation = useMutation({ mutationFn: () => api.signIn(agentId.trim(), name.trim()) })

  async function submit(event: FormEvent) {
    event.preventDefault()
    const session = await mutation.mutateAsync()
    setSession(session)
  }

  return (
    <main className="signin-page">
      <section className="signin-story">
        <Logo />
        <div className="signin-statement">
          <p className="eyebrow">Your private relationship chief of staff</p>
          <h1>Remember what matters. <em>Exactly when it matters.</em></h1>
          <p>
            URIE turns a short daily debrief into timely, thoughtful actions for every
            relationship you care about.
          </p>
        </div>
        <div className="signin-story-footer">
          <div className="privacy-promise">
            <ShieldCheck size={18} />
            <span>URIE listens only to your debrief. It never records client conversations.</span>
          </div>
          <Link className="signin-discover-link story" to="/about" aria-label="Discover how URIE works">
            Discover URIE
            <ArrowUpRight size={16} />
          </Link>
        </div>
      </section>

      <section className="signin-panel">
        <div className="signin-form-wrap">
          <span className="pilot-label">Private pilot</span>
          <h2>Welcome back</h2>
          <p>Enter your pilot identity to open your relationship intelligence.</p>
          <form onSubmit={submit} className="form-stack">
            <label>
              <span>Agent ID</span>
              <input
                value={agentId}
                onChange={(event) => setAgentId(event.target.value)}
                autoComplete="username"
                required
              />
            </label>
            <label>
              <span>Your name</span>
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                autoComplete="name"
                required
              />
            </label>
            {mutation.isError && <ErrorState message={errorMessage(mutation.error)} />}
            <Button type="submit" busy={mutation.isPending} disabled={!agentId.trim() || !name.trim()}>
              Enter URIE
            </Button>
          </form>
          <p className="pilot-footnote">Pilot access uses a temporary identity. No password is required.</p>
          <Link className="signin-discover-link panel" to="/about">
            Discover how URIE works
            <ArrowUpRight size={16} />
          </Link>
        </div>
      </section>
    </main>
  )
}

const navigation = [
  { to: '/today', label: 'Today', icon: Home },
  { to: '/debrief', label: 'Debrief', icon: MessageCircle },
  { to: '/relationships', label: 'Relationships', icon: Users },
]

function AppShell({ children }: { children: ReactNode }) {
  const { session, signOut } = useAuth()
  const online = useOnlineStatus()
  const [accountOpen, setAccountOpen] = useState(false)

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <aside className="sidebar">
        <Logo />
        <nav aria-label="Primary navigation">
          {navigation.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
              <Icon size={19} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button className="account-button" onClick={() => setAccountOpen((value) => !value)}>
            <Avatar name={session?.name || 'Agent'} size="sm" />
            <span><strong>{session?.name || 'Agent'}</strong><small>Solo workspace</small></span>
            <Ellipsis size={17} />
          </button>
          {accountOpen && (
            <div className="account-menu">
              <button onClick={signOut}>Sign out</button>
            </div>
          )}
        </div>
      </aside>

      <div className="mobile-topbar">
        <Logo />
        <IconButton label="Account settings" onClick={() => setAccountOpen((value) => !value)}>
          <Settings size={19} />
        </IconButton>
        {accountOpen && <div className="account-menu mobile"><button onClick={signOut}>Sign out</button></div>}
      </div>

      {!online && (
        <div className="offline-banner" role="status">
          You are offline. Your current view is still available.
        </div>
      )}

      <main id="main-content" className="app-main">{children}</main>

      <nav className="bottom-nav" aria-label="Mobile navigation">
        {navigation.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} className={({ isActive }) => (isActive ? 'active' : '')}>
            <Icon size={20} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}

function FeedCard({
  item,
  person,
  onAction,
  busy,
}: {
  item: FeedItem
  person?: Person
  onAction: (action: 'acked' | 'dismissed') => void
  busy: boolean
}) {
  const [copied, setCopied] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const name = person?.name || 'Relationship'

  async function copyScript() {
    await navigator.clipboard.writeText(item.script)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1800)
  }

  return (
    <article className={`action-card ${item.status === 'held' ? 'held' : ''}`}>
      <header className="action-card-header">
        <div className="person-line">
          <Avatar name={name} size="sm" />
          <div>
            <strong>{name}</strong>
            <span>{item.status === 'held' ? `Held until ${formatDate(item.held_until)}` : 'Ready when you are'}</span>
          </div>
        </div>
        <Badge tone={item.status === 'held' ? 'warm' : 'success'}>
          {item.status === 'held' ? <CirclePause size={12} /> : <Sparkles size={12} />}
          {item.status === 'held' ? 'Waiting' : 'Timely'}
        </Badge>
      </header>
      <blockquote>{item.script}</blockquote>
      <button className="rationale-toggle" onClick={() => setExpanded((value) => !value)}>
        <Lightbulb size={15} />
        {expanded ? 'Hide why this matters' : 'Why this matters'}
        <ChevronRight className={expanded ? 'rotated' : ''} size={15} />
      </button>
      {expanded && <p className="rationale">{item.rationale}</p>}
      {item.gifting_suggestion && (
        <div className="gift-note"><Gift size={16} /><span>{item.gifting_suggestion}</span></div>
      )}
      <footer>
        <div className="card-secondary-actions">
          <IconButton label={copied ? 'Copied' : 'Copy script'} onClick={copyScript}>
            {copied ? <Check size={18} /> : <Copy size={18} />}
          </IconButton>
          {person && (
            <Link className="icon-button" aria-label={`Open ${name}'s profile`} to={`/relationships/${person.node_id}`}>
              <ArrowUpRight size={18} />
            </Link>
          )}
        </div>
        {item.status === 'active' && (
          <div className="action-buttons">
            <Button variant="ghost" disabled={busy} onClick={() => onAction('dismissed')}>Not useful</Button>
            <Button busy={busy} onClick={() => onAction('acked')}>Mark done</Button>
          </div>
        )}
      </footer>
    </article>
  )
}

function TodayPage() {
  const { session } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [pendingId, setPendingId] = useState<string | null>(null)

  const feedQuery = useQuery({
    queryKey: ['feed'],
    queryFn: () => api.listFeed(session!.token, true),
  })
  const peopleQuery = useQuery({
    queryKey: ['people', ''],
    queryFn: () => api.listPeople(session!.token),
  })
  const peopleById = useMemo(
    () => new Map((peopleQuery.data || []).map((person) => [person.node_id, person])),
    [peopleQuery.data],
  )

  const actionMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'acked' | 'dismissed' }) =>
      api.acknowledgeFeed(session!.token, id, action),
    onMutate: async ({ id }) => {
      setPendingId(id)
      await queryClient.cancelQueries({ queryKey: ['feed'] })
      const previous = queryClient.getQueryData<FeedItem[]>(['feed'])
      queryClient.setQueryData<FeedItem[]>(['feed'], (items = []) => items.filter((item) => item.feed_id !== id))
      return { previous }
    },
    onError: (_error, _variables, context) => queryClient.setQueryData(['feed'], context?.previous),
    onSettled: () => {
      setPendingId(null)
      queryClient.invalidateQueries({ queryKey: ['feed'] })
    },
  })

  const active = (feedQuery.data || []).filter((item) => item.status === 'active')
  const held = (feedQuery.data || []).filter((item) => item.status === 'held')
  const firstName = session?.name.split(' ')[0] || 'there'
  const today = new Intl.DateTimeFormat('en', { weekday: 'long', month: 'long', day: 'numeric' }).format(new Date())

  return (
    <div className="page today-page">
      <PageHeader eyebrow={today} title={`Good evening, ${firstName}.`} description="Here is what deserves your attention today." />

      <section className="debrief-callout">
        <div className="debrief-orbit" aria-hidden="true"><Mic size={25} /></div>
        <div>
          <p className="eyebrow">Daily debrief</p>
          <h2>Turn today’s conversations into memory.</h2>
          <p>A focused, private check-in. Usually under two minutes.</p>
        </div>
        <Button onClick={() => navigate('/debrief')} icon={MessageCircle}>Begin debrief</Button>
      </section>

      <section className="section-block">
        <div className="section-heading">
          <div><p className="eyebrow">Next best actions</p><h2>{active.length ? `${active.length} moments worth acting on` : 'Your action feed'}</h2></div>
          {feedQuery.data && <span className="quiet-meta">Updated just now</span>}
        </div>
        {feedQuery.isPending && <LoadingCards count={2} />}
        {feedQuery.isError && <ErrorState message={errorMessage(feedQuery.error)} onRetry={() => feedQuery.refetch()} />}
        {actionMutation.isError && <ErrorState message={errorMessage(actionMutation.error)} />}
        {!feedQuery.isPending && !feedQuery.isError && active.length === 0 && (
          <EmptyState
            title="Nothing needs your attention"
            description="Complete a debrief and URIE will surface the right relationship moments here."
            action={<Button variant="secondary" onClick={() => navigate('/debrief')}>Start a debrief</Button>}
          />
        )}
        <div className="card-list">
          {active.map((item) => (
            <FeedCard
              key={item.feed_id}
              item={item}
              person={peopleById.get(item.subject_node_id)}
              busy={pendingId === item.feed_id}
              onAction={(action) => actionMutation.mutate({ id: item.feed_id, action })}
            />
          ))}
        </div>
      </section>

      {held.length > 0 && (
        <section className="section-block held-section">
          <div className="section-heading">
            <div><p className="eyebrow">Respecting boundaries</p><h2>Waiting for the right moment</h2></div>
            <Badge tone="quiet">{held.length} held</Badge>
          </div>
          <div className="card-list">
            {held.map((item) => (
              <FeedCard
                key={item.feed_id}
                item={item}
                person={peopleById.get(item.subject_node_id)}
                busy={false}
                onAction={() => undefined}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

function MutationSummary({ mutation }: { mutation: Mutation }) {
  return (
    <li className="memory-item">
      <span className="memory-icon"><BookOpen size={16} /></span>
      <div>
        <strong>{mutation.entity || 'New memory'}</strong>
        <p>{formatFactValue(mutation.value)}</p>
      </div>
      {mutation.is_conflict_resolution && <Badge tone="success">Verified</Badge>}
      {mutation.is_hypothesis && <Badge tone="warm">Hypothesis</Badge>}
    </li>
  )
}

function DebriefPage() {
  const { session: authSession } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [debrief, setDebrief] = useState<DebriefSession | null>(null)
  const [answer, setAnswer] = useState('')
  const [resolution, setResolution] = useState('')
  const [error, setError] = useState<string | null>(null)

  const startMutation = useMutation({
    mutationFn: () => api.startDebrief(authSession!.token),
    onSuccess: (result) => { setDebrief(result); setError(null) },
    onError: (reason) => setError(errorMessage(reason)),
  })
  const turnMutation = useMutation({
    mutationFn: (text: string) => api.submitTurn(authSession!.token, debrief!.session_id, text),
    onSuccess: (result) => { setDebrief(result); setAnswer(''); setError(null) },
    onError: (reason) => setError(errorMessage(reason)),
  })
  const resolveMutation = useMutation({
    mutationFn: (body: Parameters<typeof api.resolveChallenge>[2]) =>
      api.resolveChallenge(authSession!.token, debrief!.session_id, body),
    onSuccess: (result) => { setDebrief(result); setResolution(''); setError(null) },
    onError: (reason) => setError(errorMessage(reason)),
  })
  const finishMutation = useMutation({
    mutationFn: () => api.finishDebrief(authSession!.token, debrief!.session_id),
    onSuccess: (result) => {
      setDebrief(result)
      queryClient.invalidateQueries({ queryKey: ['feed'] })
      queryClient.invalidateQueries({ queryKey: ['people'] })
    },
    onError: (reason) => setError(errorMessage(reason)),
  })

  const busy = startMutation.isPending || turnMutation.isPending || resolveMutation.isPending || finishMutation.isPending

  function submitAnswer(event: FormEvent) {
    event.preventDefault()
    if (answer.trim()) turnMutation.mutate(answer.trim())
  }

  if (!debrief) {
    return (
      <div className="page debrief-intro">
        <PageHeader eyebrow="Private, focused, yours" title="Your daily debrief" />
        <section className="debrief-welcome">
          <div className="voice-sculpture" aria-hidden="true">
            <span /><span /><span /><span /><span /><span /><span />
          </div>
          <h2>Let’s capture what never made it into the CRM.</h2>
          <p>URIE will ask a few focused questions about today’s conversations. Share only what you remember.</p>
          <div className="debrief-trust-row">
            <span><Clock3 size={16} /> About 2 minutes</span>
            <span><ShieldCheck size={16} /> Agent-only debrief</span>
            <span><Sparkles size={16} /> Up to 8 focused turns</span>
          </div>
          {error && <ErrorState message={error} />}
          <Button busy={startMutation.isPending} onClick={() => startMutation.mutate()} icon={MessageCircle}>
            Start conversation
          </Button>
        </section>
      </div>
    )
  }

  if (debrief.status === 'completed') {
    const memories = debrief.staged_mutations || []
    return (
      <div className="page debrief-complete">
        <section className="completion-hero">
          <span className="completion-mark"><Check size={28} /></span>
          <p className="eyebrow">Debrief complete</p>
          <h1>Your memory is up to date.</h1>
          <p>URIE will reason over what you shared and surface the right moment to act.</p>
        </section>
        <section className="memory-summary">
          <div className="section-heading"><div><p className="eyebrow">Captured today</p><h2>{memories.length} relationship memories</h2></div></div>
          {memories.length ? <ul>{memories.map((item, index) => <MutationSummary key={item.fact_id || index} mutation={item} />)}</ul> : (
            <p className="quiet-copy">No new structured memories were needed from this conversation.</p>
          )}
        </section>
        <div className="completion-actions">
          <Button onClick={() => navigate('/today')}>See today’s actions</Button>
          <Button variant="ghost" onClick={() => setDebrief(null)}>Start another debrief</Button>
        </div>
      </div>
    )
  }

  const challenge = debrief.pending_challenge
  return (
    <div className="debrief-session-page">
      <header className="session-topbar">
        <IconButton label="Leave debrief" onClick={() => navigate('/today')}><ArrowLeft size={20} /></IconButton>
        <div><strong>Daily debrief</strong><span>{debrief.turns.filter((turn) => turn.role === 'user').length} of 8 turns</span></div>
        <Button variant="ghost" disabled={busy} onClick={() => finishMutation.mutate()}>Finish</Button>
      </header>
      <div className="session-progress"><span style={{ inlineSize: `${Math.min(100, (debrief.turns.filter((turn) => turn.role === 'user').length / 8) * 100)}%` }} /></div>

      <section className="conversation" aria-live="polite">
        <div className="conversation-intro"><Sparkles size={15} /><span>URIE asks only what helps close a knowledge gap.</span></div>
        {debrief.turns.map((turn, index) => (
          <article className={`message ${turn.role}`} key={`${turn.at || index}-${index}`}>
            {turn.role === 'assistant' && <span className="assistant-mark">U</span>}
            <div>
              <p>{turn.content}</p>
              {turn.at && <time>{timeFormatter.format(new Date(turn.at))}</time>}
            </div>
          </article>
        ))}

        {challenge && (
          <section className="challenge-panel">
            <p className="eyebrow">{challenge.type === 'ambiguity' ? 'A quick distinction' : 'Something changed'}</p>
            <h2>{challenge.vui_prompt || 'Help URIE understand this change.'}</h2>
            {challenge.type === 'ambiguity' && challenge.candidates?.length ? (
              <div className="candidate-list">
                {challenge.candidates.map((candidate) => (
                  <button
                    key={candidate.node_id}
                    disabled={busy}
                    onClick={() => resolveMutation.mutate({
                      resolution_note: `Selected ${candidate.hint || candidate.node_id}`,
                      chosen_node_id: candidate.node_id,
                    })}
                  >
                    <Avatar name={candidate.hint || candidate.node_id} size="sm" />
                    <span><strong>{candidate.hint || candidate.node_id}</strong><small>{Math.round(candidate.score * 100)}% match</small></span>
                    <ChevronRight size={17} />
                  </button>
                ))}
                <button
                  disabled={busy}
                  onClick={() => resolveMutation.mutate({ resolution_note: 'Create new person', create_new: true })}
                >
                  <span className="new-person-icon"><Plus size={18} /></span>
                  <span><strong>This is someone new</strong><small>Create a separate relationship</small></span>
                  <ChevronRight size={17} />
                </button>
              </div>
            ) : (
              <>
                {(challenge.existing_value !== undefined || challenge.candidate_value !== undefined) && (
                  <div className="value-change">
                    <div><small>Previously</small><span>{formatFactValue(challenge.existing_value)}</span></div>
                    <ChevronRight size={17} />
                    <div><small>Now</small><span>{formatFactValue(challenge.candidate_value)}</span></div>
                  </div>
                )}
                <form
                  className="resolution-form"
                  onSubmit={(event) => {
                    event.preventDefault()
                    if (resolution.trim()) resolveMutation.mutate({
                      resolution_note: resolution.trim(),
                      accepted_value: challenge.candidate_value,
                    })
                  }}
                >
                  <label htmlFor="resolution">What explains the change?</label>
                  <textarea id="resolution" value={resolution} onChange={(event) => setResolution(event.target.value)} rows={3} placeholder="Add the human context behind this change…" />
                  <Button type="submit" busy={resolveMutation.isPending} disabled={!resolution.trim()}>Confirm context</Button>
                </form>
              </>
            )}
          </section>
        )}
      </section>

      {error && <div className="conversation-error"><ErrorState message={error} /></div>}
      {!challenge && (
        <form className="composer" onSubmit={submitAnswer}>
          <textarea
            aria-label="Your answer"
            value={answer}
            onChange={(event) => setAnswer(event.target.value)}
            placeholder="Tell URIE what happened…"
            rows={1}
            disabled={busy}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                if (answer.trim()) turnMutation.mutate(answer.trim())
              }
            }}
          />
          <IconButton label="Send answer" type="submit" disabled={!answer.trim() || busy}>
            {turnMutation.isPending ? <span className="mini-spinner" /> : <Send size={19} />}
          </IconButton>
        </form>
      )}
    </div>
  )
}

function RelationshipsPage() {
  const { session } = useAuth()
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(search), 280)
    return () => window.clearTimeout(timer)
  }, [search])

  const peopleQuery = useQuery({
    queryKey: ['people', query],
    queryFn: () => api.listPeople(session!.token, query),
  })

  return (
    <div className="page relationships-page">
      <PageHeader
        eyebrow="Your private book"
        title="Relationships"
        description="Every detail URIE has learned, shaped into living context."
        action={<Badge tone="quiet">{peopleQuery.data?.length || 0} people</Badge>}
      />
      <div className="search-field">
        <Search size={18} />
        <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search a name, place, or detail…" aria-label="Search relationships" />
        {peopleQuery.isFetching && <span className="mini-spinner" />}
      </div>
      {peopleQuery.isPending && <LoadingCards />}
      {peopleQuery.isError && <ErrorState message={errorMessage(peopleQuery.error)} onRetry={() => peopleQuery.refetch()} />}
      {!peopleQuery.isPending && !peopleQuery.isError && !peopleQuery.data?.length && (
        <EmptyState
          icon={Users}
          title={query ? 'No matching relationships' : 'Your relationship memory starts here'}
          description={query ? 'Try a different name or detail.' : 'Complete a debrief and the people you mention will appear here.'}
        />
      )}
      <div className="relationship-list">
        {peopleQuery.data?.map((person) => (
          <Link to={`/relationships/${person.node_id}`} className="relationship-row" key={person.node_id}>
            <Avatar name={person.name} />
            <div className="relationship-primary">
              <strong>{person.name}</strong>
              <span>{person.aliases?.length ? `Also known as ${person.aliases.join(', ')}` : 'Relationship profile'}</span>
            </div>
            <div className="relationship-touch">
              <small>Last updated</small>
              <span>{formatDate(person.last_touched_at || person.created_at)}</span>
            </div>
            <ChevronRight size={19} />
          </Link>
        ))}
      </div>
    </div>
  )
}

function AddBoundaryDialog({ person, onClose }: { person: Person; onClose: () => void }) {
  const { session } = useAuth()
  const queryClient = useQueryClient()
  const [label, setLabel] = useState('Do not contact — high workload')
  const [end, setEnd] = useState('')
  const mutation = useMutation({
    mutationFn: () => api.createConstraint(session!.token, {
      person_node_id: person.node_id,
      label,
      window_end: end ? new Date(`${end}T23:59:59`).toISOString() : undefined,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['person', person.node_id] })
      queryClient.invalidateQueries({ queryKey: ['constraints', person.node_id] })
    },
  })

  return (
    <Dialog title={`Protect ${person.name}’s space`} description="URIE will hold every outward suggestion until this boundary ends." onClose={onClose}>
      {mutation.isSuccess ? (
        <div className="dialog-success">
          <SuccessNotice>Boundary added. URIE will respect this timing.</SuccessNotice>
          <Button onClick={onClose}>Done</Button>
        </div>
      ) : (
        <form className="form-stack" onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}>
          <label><span>Reason</span><input value={label} onChange={(event) => setLabel(event.target.value)} required /></label>
          <label><span>Hold suggestions until</span><input type="date" value={end} onChange={(event) => setEnd(event.target.value)} /></label>
          {mutation.isError && <ErrorState message={errorMessage(mutation.error)} />}
          <div className="dialog-actions"><Button variant="ghost" type="button" onClick={onClose}>Cancel</Button><Button type="submit" busy={mutation.isPending}>Add boundary</Button></div>
        </form>
      )}
    </Dialog>
  )
}

function WriteBackDialog({ person, factId, defaultNote, onClose }: { person: Person; factId: string; defaultNote: string; onClose: () => void }) {
  const { session } = useAuth()
  const [note, setNote] = useState(defaultNote)
  const mutation = useMutation({ mutationFn: () => api.writeBack(session!.token, factId, note.trim()) })

  return (
    <Dialog title="Prepare CRM note" description={`Create a clean note for ${person.name}. Pilot mode stores the write-back locally.`} onClose={onClose}>
      {mutation.isSuccess ? (
        <div className="dialog-success"><SuccessNotice>CRM note prepared successfully.</SuccessNotice><Button onClick={onClose}>Done</Button></div>
      ) : (
        <form className="form-stack" onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}>
          <label><span>Note</span><textarea rows={5} value={note} onChange={(event) => setNote(event.target.value)} required /></label>
          {mutation.isError && <ErrorState message={errorMessage(mutation.error)} />}
          <div className="dialog-actions"><Button variant="ghost" type="button" onClick={onClose}>Cancel</Button><Button busy={mutation.isPending} disabled={!note.trim()}>Prepare note</Button></div>
        </form>
      )}
    </Dialog>
  )
}

function RelationshipProfilePage() {
  const { nodeId = '' } = useParams()
  const { session } = useAuth()
  const [boundaryOpen, setBoundaryOpen] = useState(false)
  const [writeBack, setWriteBack] = useState<{ factId: string; note: string } | null>(null)
  const personQuery = useQuery({
    queryKey: ['person', nodeId],
    queryFn: () => api.getPerson(session!.token, nodeId),
    enabled: Boolean(nodeId),
  })
  const contextQuery = useQuery({
    queryKey: ['context', nodeId],
    queryFn: () => api.getContext(session!.token, nodeId),
    enabled: Boolean(nodeId),
  })

  if (personQuery.isPending) {
    return <div className="page profile-page"><Skeleton className="profile-hero-skeleton" /><LoadingCards /></div>
  }
  if (personQuery.isError || !personQuery.data) {
    return <div className="page"><ErrorState message={errorMessage(personQuery.error)} onRetry={() => personQuery.refetch()} /></div>
  }

  const person = personQuery.data
  const activeFacts = (person.facts || []).filter((fact) => !fact.superseded_by)
  const history = [...(person.facts || [])].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))
  const neighbors = contextQuery.data?.neighbors || []

  return (
    <div className="page profile-page">
      <Link className="back-link" to="/relationships"><ArrowLeft size={17} /> All relationships</Link>
      <section className="profile-hero">
        <Avatar name={person.name} size="lg" />
        <div className="profile-identity">
          <p className="eyebrow">Relationship profile</p>
          <h1>{person.name}</h1>
          <p>{person.aliases?.length ? `Also known as ${person.aliases.join(', ')}` : 'A living record of what matters in this relationship.'}</p>
        </div>
        <Button variant="secondary" icon={CalendarClock} onClick={() => setBoundaryOpen(true)}>Add boundary</Button>
      </section>

      {person.constraints?.length ? (
        <section className="boundary-banner">
          <CirclePause size={20} />
          <div><strong>Contact boundary active</strong><p>{person.constraints[0].label} {person.constraints[0].window_end ? `until ${formatDate(person.constraints[0].window_end)}` : ''}</p></div>
          <Badge tone="warm">Suggestions held</Badge>
        </section>
      ) : null}

      <div className="profile-grid">
        <section className="profile-main">
          <div className="section-heading"><div><p className="eyebrow">Current understanding</p><h2>What URIE knows</h2></div><Badge tone="quiet">{activeFacts.length} facts</Badge></div>
          {!activeFacts.length ? <EmptyState title="No structured facts yet" description="The next debrief will help build this relationship profile." /> : (
            <div className="fact-grid">
              {activeFacts.map((fact) => (
                <article className="fact-card" key={fact.fact_id}>
                  <header><span>{fact.entity}</span>{fact.is_hypothesis ? <Badge tone="warm">Hypothesis</Badge> : fact.is_conflict_resolution ? <Badge tone="success">Verified</Badge> : null}</header>
                  <strong>{formatFactValue(fact.value)}</strong>
                  <footer>
                    <span className="confidence"><i style={{ inlineSize: `${Math.round(fact.confidence_score * 100)}%` }} />{Math.round(fact.confidence_score * 100)}% confidence</span>
                    <button onClick={() => setWriteBack({ factId: fact.fact_id, note: `${person.name} — ${fact.entity}: ${formatFactValue(fact.value)}` })} aria-label={`Prepare ${fact.entity} CRM note`}><Link2 size={15} /></button>
                  </footer>
                </article>
              ))}
            </div>
          )}

          <div className="section-heading timeline-heading"><div><p className="eyebrow">Memory over time</p><h2>Relationship timeline</h2></div></div>
          <ol className="timeline">
            {history.map((fact) => (
              <li key={fact.fact_id} className={fact.superseded_by ? 'superseded' : ''}>
                <span className="timeline-dot" />
                <time>{formatDate(fact.created_at)}</time>
                <div><strong>{fact.entity}</strong><p>{formatFactValue(fact.value)}</p>{fact.superseded_by && <small>Later updated</small>}</div>
              </li>
            ))}
          </ol>
        </section>

        <aside className="profile-aside">
          <section className="context-card">
            <div className="context-icon"><Network size={19} /></div>
            <p className="eyebrow">Relationship context</p>
            <h2>People around {person.name.split(' ')[0]}</h2>
            {contextQuery.isPending ? <LoadingCards count={1} /> : neighbors.length ? (
              <ul>{neighbors.slice(0, 5).map((neighbor) => <li key={neighbor.node_id}><Avatar name={neighbor.name} size="sm" /><span><strong>{neighbor.name}</strong><small>{neighbor.kind}</small></span></li>)}</ul>
            ) : <p className="quiet-copy">No connected people have been identified yet.</p>}
          </section>
          <section className="privacy-card">
            <ShieldCheck size={19} />
            <div><strong>Private to your workspace</strong><p>URIE never contacts {person.name.split(' ')[0]} or shares this relational context.</p></div>
          </section>
        </aside>
      </div>
      {boundaryOpen && <AddBoundaryDialog person={person} onClose={() => setBoundaryOpen(false)} />}
      {writeBack && <WriteBackDialog person={person} factId={writeBack.factId} defaultNote={writeBack.note} onClose={() => setWriteBack(null)} />}
    </div>
  )
}

function AuthenticatedApp() {
  return (
    <AppShell>
      <Routes>
        <Route path="/today" element={<TodayPage />} />
        <Route path="/debrief" element={<DebriefPage />} />
        <Route path="/relationships" element={<RelationshipsPage />} />
        <Route path="/relationships/:nodeId" element={<RelationshipProfilePage />} />
        <Route path="*" element={<Navigate to="/today" replace />} />
      </Routes>
    </AppShell>
  )
}

export default function App() {
  const { session } = useAuth()
  return (
    <Routes>
      <Route path="/about" element={<LandingPage />} />
      <Route path="/*" element={session ? <AuthenticatedApp /> : <UnauthenticatedApp />} />
    </Routes>
  )
}

function UnauthenticatedApp() {
  return (
    <Routes>
      <Route path="/" element={<SignIn />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
