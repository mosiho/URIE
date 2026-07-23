import {
  ArrowDown,
  ArrowRight,
  Check,
  MessageCircle,
  Mic,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { Logo } from './ui'

const WHATSAPP_URL =
  'https://wa.me/40734755202?text=Hello%2C%20I%27d%20like%20to%20see%20a%20free%20demo%20of%20URIE.'

const COMPARISON_ROWS = [
  {
    dimension: 'Friction',
    crm: 'Manual typing, forms, and forgotten follow-ups',
    urie: 'A short voice debrief captures what happened by speech',
  },
  {
    dimension: 'Visibility',
    crm: 'Only what someone took the time to type',
    urie: 'Also what was said once — and never written down',
  },
  {
    dimension: 'Focus',
    crm: 'Pipeline stages, tasks, and contact cards',
    urie: 'Relational health, boundaries, and living memory',
  },
  {
    dimension: 'Output',
    crm: 'Static reminders (“Call John today”)',
    urie: 'Behavioral scripts with timing and the reason why',
  },
] as const

const FLYWHEEL = [
  {
    index: '01',
    title: 'Day accumulates',
    detail: 'Client moments stay in your head — not in a form.',
    example: 'John’s busy week ends Friday.',
  },
  {
    index: '02',
    title: 'Private debrief',
    detail: 'URIE interviews you — never the client. At most once or twice a day.',
    example: 'You speak it in under two minutes.',
  },
  {
    index: '03',
    title: 'Living memory',
    detail: 'Preferences, boundaries, and life changes become connected context.',
    example: 'Busy week · launch · don’t push property yet.',
  },
  {
    index: '04',
    title: 'Ghost-mode script',
    detail: 'You get the right words and timing. You keep every human moment.',
    example: 'Call Friday. Ask how the launch went first.',
  },
] as const

export default function LandingPage() {
  return (
    <main className="landing-page">
      <section className="landing-hero" aria-labelledby="landing-title">
        <img
          className="landing-hero-image"
          src="/urie-hero-v2.webp"
          alt="A real-estate agent recording a private debrief after a client meeting"
        />
        <div className="landing-hero-shade" aria-hidden="true" />

        <header className="landing-nav">
          <Link to="/about" aria-label="URIE home">
            <Logo />
          </Link>
          <Link className="landing-pilot-link" to="/">
            Enter the pilot
            <ArrowRight size={16} />
          </Link>
        </header>

        <div className="landing-hero-copy">
          <p className="landing-kicker">Relationship Intelligence for solo high-value agents</p>
          <h1 id="landing-title">
            URIE remembers the conversation <em>your CRM never heard.</em>
          </h1>
          <p className="landing-hero-lede">
            A private daily debrief turns what stayed in your head into living memory—
            and the exact words to use when timing wins the relationship.
          </p>
          <div className="landing-hero-actions">
            <a className="landing-primary-cta" href={WHATSAPP_URL} target="_blank" rel="noreferrer">
              Request a free demo
              <MessageCircle size={18} />
            </a>
            <Link className="landing-secondary-cta" to="/">
              Enter the private pilot
            </Link>
          </div>
        </div>

        <a className="landing-scroll-cue" href="#the-gap" aria-label="Explore how URIE works">
          <ArrowDown size={17} />
          <span>Discover the difference</span>
        </a>
      </section>

      <section className="landing-gap" id="the-gap" aria-labelledby="gap-title">
        <div className="landing-section-number" aria-hidden="true">01</div>
        <div className="landing-gap-heading">
          <p className="eyebrow">The conversation that never got written down</p>
          <h2 id="gap-title">High-value deals turn on details no database ever held.</h2>
        </div>
        <div className="landing-gap-copy">
          <p>
            Your best clients rarely put the most important thing in a form. They mention it
            once—in a car, between meetings, at the end of a call—and it lives only in your head.
          </p>
          <p>
            Every other tool organizes digital exhaust: email, calendar, MLS, CRM fields.
            They can only see what was already captured somewhere. URIE captures what stayed
            with you, keeps it alive, and surfaces it when remembering becomes extraordinary service.
          </p>
        </div>
        <figure className="landing-trust-visual">
          <img
            src="/urie-trust-moment.webp"
            alt="A real-estate advisor listening closely as clients share personal context"
            loading="lazy"
          />
          <figcaption>
            <span>Face-to-face trust stays yours</span>
            <p>URIE never joins the meeting. It captures what you remember after.</p>
          </figcaption>
        </figure>
        <blockquote>
          “The agent who remembers the detail no one else did becomes the agent no one forgets.”
        </blockquote>
      </section>

      <section className="landing-overlay" aria-labelledby="overlay-title">
        <header className="landing-section-heading">
          <p className="eyebrow">Not a CRM — an intelligence layer</p>
          <h2 id="overlay-title">Keep the CRM your brokerage requires. Use URIE to win the client.</h2>
          <p>
            Traditional tools are systems of record. URIE is a system of intelligence that sits
            on top—zero migration, clean notes written back when you want them.
          </p>
        </header>

        <div className="landing-comparison" role="table" aria-label="Traditional CRM versus URIE">
          <div className="landing-comparison-head" role="row">
            <span role="columnheader" className="landing-comparison-dim">
              Dimension
            </span>
            <span role="columnheader">Traditional CRM</span>
            <span role="columnheader" className="landing-comparison-urie-col">
              URIE
            </span>
          </div>
          {COMPARISON_ROWS.map((row) => (
            <div className="landing-comparison-row" role="row" key={row.dimension}>
              <span role="cell" className="landing-comparison-dim">
                {row.dimension}
              </span>
              <span role="cell">{row.crm}</span>
              <span role="cell" className="landing-comparison-urie-col">
                {row.urie}
              </span>
            </div>
          ))}
        </div>

        <p className="landing-differentiator">
          Everyone else organizes what your CRM already knows.
          <em> We remember what it never even saw.</em>
        </p>
      </section>

      <section className="landing-loop" aria-labelledby="loop-title">
        <header className="landing-section-heading">
          <p className="eyebrow">How URIE works</p>
          <h2 id="loop-title">Two minutes in. A relationship advantage out.</h2>
          <p>
            No forms to maintain. No stack to rip out. Just a bounded, private conversation
            with URIE—then the right moment, ready when you are.
          </p>
        </header>

        <ol className="landing-flywheel" aria-label="From daily moments to a timely script">
          {FLYWHEEL.map((step, index) => (
            <li key={step.index} style={{ animationDelay: `${index * 90}ms` }}>
              {index > 0 && (
                <span className="landing-flywheel-connector" aria-hidden="true">
                  <svg viewBox="0 0 48 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path
                      d="M1 6H39"
                      stroke="currentColor"
                      strokeWidth="1.2"
                      strokeDasharray="3 3"
                    />
                    <path d="M36 1L43 6L36 11" stroke="currentColor" strokeWidth="1.2" fill="none" />
                  </svg>
                </span>
              )}
              <span className="landing-flywheel-index">{step.index}</span>
              <h3>{step.title}</h3>
              <p>{step.detail}</p>
              <small>{step.example}</small>
            </li>
          ))}
        </ol>

        <div className="landing-script-preview" aria-label="Example ghost-mode script">
          <span className="landing-visual-label">Example script</span>
          <Sparkles size={18} />
          <p>Call Friday. Ask how the launch went before discussing the property.</p>
          <small>Context remembered · boundary respected · you deliver it</small>
        </div>

        <ol className="landing-steps">
          <li>
            <span className="landing-step-icon"><Mic size={21} /></span>
            <span className="landing-step-index">01</span>
            <div>
              <h3>Debrief privately</h3>
              <p>
                Tell URIE what happened today. It asks only the questions that close a meaningful
                knowledge gap—never a static questionnaire.
              </p>
            </div>
          </li>
          <li>
            <span className="landing-step-icon"><Sparkles size={21} /></span>
            <span className="landing-step-index">02</span>
            <div>
              <h3>Build living memory</h3>
              <p>
                People, preferences, boundaries, and life changes become connected context—
                not scattered notes that go stale overnight.
              </p>
            </div>
          </li>
          <li>
            <span className="landing-step-icon"><ShieldCheck size={21} /></span>
            <span className="landing-step-index">03</span>
            <div>
              <h3>Act at the right moment</h3>
              <p>
                Receive a thoughtful script with the reason and timing behind it.
                You make the human connection. URIE stays invisible.
              </p>
            </div>
          </li>
        </ol>
      </section>

      <section className="landing-ghost" aria-labelledby="ghost-title">
        <div className="landing-ghost-mark" aria-hidden="true">U</div>
        <div className="landing-ghost-copy">
          <p className="eyebrow">Ghost mode</p>
          <h2 id="ghost-title">The intelligence stays invisible. The relationship stays yours.</h2>
          <p>
            URIE never messages your client, never joins a client call, and never takes credit.
            It quietly prepares you to show up with precision, warmth, and perfect timing—
            so the prestige lands with you.
          </p>
        </div>
        <ul className="landing-trust-list" aria-label="URIE privacy promises">
          <li>
            <ShieldCheck size={18} />
            <span>Only your agent↔URIE debrief is processed — client conversations are never recorded</span>
          </li>
          <li>
            <Check size={18} />
            <span>Your existing CRM stays in place</span>
          </li>
          <li>
            <Check size={18} />
            <span>You keep every human moment</span>
          </li>
        </ul>
      </section>

      <section className="landing-demo" aria-labelledby="demo-title">
        <div className="landing-demo-inner">
          <p className="eyebrow">A private invitation</p>
          <h2 id="demo-title">See what your relationships could remember.</h2>
          <p>
            Request a free personal demo. We will walk through one real day in your book of
            business and show you exactly where URIE creates an advantage.
          </p>
          <a className="landing-whatsapp-cta" href={WHATSAPP_URL} target="_blank" rel="noreferrer">
            <MessageCircle size={19} />
            Get your free demo on WhatsApp
            <ArrowRight size={18} />
          </a>
          <a className="landing-phone" href={WHATSAPP_URL} target="_blank" rel="noreferrer">
            +40 734 755 202
          </a>
        </div>
      </section>

      <footer className="landing-footer">
        <Logo />
        <p>Private relationship intelligence for high-value real estate.</p>
        <Link to="/">Pilot sign in</Link>
      </footer>
    </main>
  )
}
