import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { AuthProvider } from './auth'

function renderApp() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>,
  )
}

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

describe('URIE app', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/')
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('presents an honest private-pilot sign-in', () => {
    renderApp()
    expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
    expect(screen.getByText(/Pilot access uses a temporary identity/)).toBeInTheDocument()
    expect(screen.getByText(/never records client conversations/)).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Discover/ })[0]).toHaveAttribute('href', '/about')
  })

  it('presents the public URIE story and a direct WhatsApp demo path', () => {
    window.history.replaceState({}, '', '/about')
    renderApp()

    expect(
      screen.getByRole('heading', {
        name: /URIE remembers the conversation your CRM never heard/,
      }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', {
        name: /High-value deals turn on details no database ever held/,
      }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', {
        name: /Keep the CRM your brokerage requires/,
      }),
    ).toBeInTheDocument()
    expect(screen.getByText(/client conversations are never recorded/i)).toBeInTheDocument()

    const demoLinks = screen.getAllByRole('link', { name: /free demo/i })
    expect(demoLinks.length).toBeGreaterThanOrEqual(2)
    for (const link of demoLinks) {
      expect(link).toHaveAttribute(
        'href',
        expect.stringContaining('https://wa.me/40734755202'),
      )
    }
    expect(screen.getByText('+40 734 755 202')).toBeInTheDocument()
  })

  it('switches the landing page between English and Romanian', () => {
    window.history.replaceState({}, '', '/about')
    renderApp()

    fireEvent.click(screen.getByRole('button', { name: 'RO' }))

    expect(
      screen.getByRole('heading', {
        name: /URIE își amintește conversația pe care CRM-ul tău nu a auzit-o niciodată/,
      }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Primește demonstrația gratuită pe WhatsApp/i })).toHaveAttribute(
      'href',
      expect.stringContaining('https://wa.me/40734755202?text='),
    )
    expect(screen.getByRole('link', { name: /Primește demonstrația gratuită pe WhatsApp/i })).toHaveAttribute(
      'href',
      expect.stringMatching(/demonstra/),
    )

    fireEvent.click(screen.getByRole('button', { name: 'EN' }))
    expect(
      screen.getByRole('heading', {
        name: /URIE remembers the conversation your CRM never heard/,
      }),
    ).toBeInTheDocument()
  })

  it('signs in and opens the Today experience', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input)
      if (url.includes('/v1/auth/token')) {
        return jsonResponse({ access_token: 'test-token', agent_id: 'agt_demo' })
      }
      if (url.includes('/v1/feed')) return jsonResponse([])
      if (url.includes('/v1/nodes')) return jsonResponse([])
      return jsonResponse({ detail: 'Not found' }, 404)
    })

    renderApp()
    fireEvent.click(screen.getByRole('button', { name: 'Enter URIE' }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Good evening, Demo/ })).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /Begin debrief/ })).toBeInTheDocument()
  })

  it('renders a timely action from the live feed contract', async () => {
    localStorage.setItem(
      'urie_session',
      JSON.stringify({ token: 'test-token', agentId: 'agt_demo', name: 'Maya Chen' }),
    )
    window.history.replaceState({}, '', '/today')
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input)
      if (url.includes('/v1/feed')) {
        return jsonResponse([
          {
            feed_id: 'feed_1',
            agent_id: 'agt_demo',
            subject_node_id: 'node_john',
            script: 'Call John and ask how the family is settling in.',
            rationale: 'His contact window reopened today.',
            status: 'active',
          },
        ])
      }
      if (url.includes('/v1/nodes')) {
        return jsonResponse([
          {
            node_id: 'node_john',
            kind: 'Person',
            name: 'John Mercer',
            aliases: [],
            attrs: {},
          },
        ])
      }
      return jsonResponse({ detail: 'Not found' }, 404)
    })

    renderApp()
    expect(await screen.findByText('Call John and ask how the family is settling in.')).toBeInTheDocument()
    expect(screen.getByText('John Mercer')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Mark done' })).toBeInTheDocument()
  })

  it('starts the real multi-turn debrief contract', async () => {
    localStorage.setItem(
      'urie_session',
      JSON.stringify({ token: 'test-token', agentId: 'agt_demo', name: 'Maya Chen' }),
    )
    window.history.replaceState({}, '', '/debrief')
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input)
      if (url.includes('/v1/debriefs')) {
        return jsonResponse({
          session_id: 'deb_1',
          agent_id: 'agt_demo',
          status: 'interviewing',
          transcript: '',
          staged_mutations: [],
          pending_challenge: null,
          turns: [{ role: 'assistant', content: 'Who stood out in your conversations today?' }],
          covered_gaps: [],
          next_question: 'Who stood out in your conversations today?',
          mode: 'interview',
        })
      }
      return jsonResponse({ detail: 'Not found' }, 404)
    })

    renderApp()
    fireEvent.click(screen.getByRole('button', { name: 'Start conversation' }))

    expect(await screen.findByText('Who stood out in your conversations today?')).toBeInTheDocument()
    expect(screen.getByLabelText('Your answer')).toBeInTheDocument()
  })

  it('turns structured person data into a readable relationship profile', async () => {
    localStorage.setItem(
      'urie_session',
      JSON.stringify({ token: 'test-token', agentId: 'agt_demo', name: 'Maya Chen' }),
    )
    window.history.replaceState({}, '', '/relationships/node_john')
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input)
      if (url.endsWith('/context')) {
        return jsonResponse({ node: {}, neighbors: [], edges: [] })
      }
      if (url.includes('/v1/nodes/node_john')) {
        return jsonResponse({
          node_id: 'node_john',
          kind: 'Person',
          name: 'John Mercer',
          aliases: [],
          attrs: {},
          facts: [
            {
              fact_id: 'fact_budget',
              entity: 'Budget',
              value: { amount: 5000000, currency: 'USD' },
              confidence_score: 0.95,
              is_hypothesis: false,
              is_conflict_resolution: true,
              superseded_by: null,
              created_at: '2026-07-21T10:00:00Z',
            },
          ],
          constraints: [],
        })
      }
      return jsonResponse({ detail: 'Not found' }, 404)
    })

    renderApp()
    expect(await screen.findByRole('heading', { name: 'John Mercer' })).toBeInTheDocument()
    expect(screen.getAllByText('USD 5,000,000')).toHaveLength(2)
    expect(screen.getByText('95% confidence')).toBeInTheDocument()
    expect(screen.queryByText(/^\{/)).not.toBeInTheDocument()
  })
})

