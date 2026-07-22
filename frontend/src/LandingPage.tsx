import {
  ArrowDown,
  ArrowRight,
  BrainCircuit,
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
          <p className="landing-kicker">Relationship Intelligence for exceptional agents</p>
          <h1 id="landing-title">
            URIE remembers the conversation <em>your CRM never heard.</em>
          </h1>
          <p className="landing-hero-lede">
            A private daily debrief becomes a living memory of every high-value relationship—
            and the right words to use when timing matters most.
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
          <p className="eyebrow">The advantage no database can hold</p>
          <h2 id="gap-title">A CRM remembers fields. URIE remembers people.</h2>
        </div>
        <div className="landing-gap-copy">
          <p>
            Your best clients rarely say the most important thing in a form. They mention it
            once—in a car, between meetings, at the end of a call.
          </p>
          <p>
            URIE captures what stayed in your head, gives it context, and keeps it alive until
            the moment remembering becomes extraordinary service.
          </p>
        </div>
        <figure className="landing-trust-visual">
          <img
            src="/urie-trust-moment.webp"
            alt="A real-estate advisor listening closely as clients share personal context"
            loading="lazy"
          />
          <figcaption>
            <span>The moment behind the data</span>
            <p>What matters most is often shared quietly—and only once.</p>
          </figcaption>
        </figure>
        <blockquote>
          “The agent who remembers the detail no one else did becomes the agent no one forgets.”
        </blockquote>
      </section>

      <section className="landing-loop" aria-labelledby="loop-title">
        <header className="landing-section-heading">
          <p className="eyebrow">Effortless by design</p>
          <h2 id="loop-title">Two minutes in. A relationship advantage out.</h2>
          <p>No forms to maintain. No new CRM to migrate to. Just a short conversation with URIE.</p>
        </header>

        <div className="landing-intelligence-visual" aria-label="A debrief becomes living memory and a timely action">
          <div className="landing-voice-signal">
            <span className="landing-visual-label">Private debrief</span>
            <div className="landing-waveform" aria-hidden="true">
              {[18, 32, 46, 27, 58, 72, 43, 64, 38, 54, 29, 42, 20].map((height, index) => (
                <i key={`${height}-${index}`} style={{ blockSize: `${height}px` }} />
              ))}
            </div>
            <small>“John’s busy week ends Friday…”</small>
          </div>
          <div className="landing-memory-engine" aria-hidden="true">
            <span className="landing-memory-orbit orbit-one" />
            <span className="landing-memory-orbit orbit-two" />
            <span className="landing-memory-core">U</span>
            <span className="landing-memory-node node-one" />
            <span className="landing-memory-node node-two" />
            <span className="landing-memory-node node-three" />
          </div>
          <div className="landing-action-preview">
            <span className="landing-visual-label">The right moment</span>
            <Sparkles size={18} />
            <p>Call Friday. Ask how the launch went before discussing the property.</p>
            <small>Context remembered · boundary respected</small>
          </div>
        </div>

        <ol className="landing-steps">
          <li>
            <span className="landing-step-icon"><Mic size={21} /></span>
            <span className="landing-step-index">01</span>
            <div>
              <h3>Debrief privately</h3>
              <p>Tell URIE what happened today. It asks only the questions that close a meaningful gap.</p>
            </div>
          </li>
          <li>
            <span className="landing-step-icon"><BrainCircuit size={21} /></span>
            <span className="landing-step-index">02</span>
            <div>
              <h3>Build living memory</h3>
              <p>People, preferences, boundaries, and life changes become connected context—not scattered notes.</p>
            </div>
          </li>
          <li>
            <span className="landing-step-icon"><Sparkles size={21} /></span>
            <span className="landing-step-index">03</span>
            <div>
              <h3>Act at the right moment</h3>
              <p>Receive a thoughtful script with the reason and timing behind it. You make the human connection.</p>
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
            It quietly prepares you to show up with precision, warmth, and perfect timing.
          </p>
        </div>
        <ul className="landing-trust-list" aria-label="URIE privacy promises">
          <li><ShieldCheck size={18} /><span>Only your debrief is processed</span></li>
          <li><Check size={18} /><span>Your existing CRM stays in place</span></li>
          <li><Check size={18} /><span>You keep every human moment</span></li>
        </ul>
      </section>

      <section className="landing-demo" aria-labelledby="demo-title">
        <div className="landing-demo-inner">
          <p className="eyebrow">A private invitation</p>
          <h2 id="demo-title">See what your relationships could remember.</h2>
          <p>
            Request a free personal demo. We will walk through one real day in your business
            and show you exactly where URIE creates an advantage.
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

