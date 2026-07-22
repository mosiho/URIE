/* oxlint-disable react/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import type { AgentSession } from './types'

const STORAGE_KEY = 'urie_session'

interface AuthValue {
  session: AgentSession | null
  setSession: (session: AgentSession) => void
  signOut: () => void
}

const AuthContext = createContext<AuthValue | null>(null)

function readSession(): AgentSession | null {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (!saved) return null
    const session = JSON.parse(saved) as AgentSession
    return session.token && session.agentId ? session : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<AgentSession | null>(readSession)

  const setSession = useCallback((next: AgentSession) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    setSessionState(next)
  }, [])

  const signOut = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setSessionState(null)
  }, [])

  useEffect(() => {
    window.addEventListener('urie:unauthorized', signOut)
    return () => window.removeEventListener('urie:unauthorized', signOut)
  }, [signOut])

  const value = useMemo(() => ({ session, setSession, signOut }), [session, setSession, signOut])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}

