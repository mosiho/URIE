import { useEffect, useState } from 'react'
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
import {
  LANDING_COPY,
  LANDING_LOCALE_KEY,
  type LandingLocale,
  resolveLandingLocale,
  whatsappUrlFor,
} from './landingCopy'
import { Logo } from './ui'

export default function LandingPage() {
  const [locale, setLocale] = useState<LandingLocale>(() => {
    try {
      return resolveLandingLocale(localStorage.getItem(LANDING_LOCALE_KEY))
    } catch {
      return 'en'
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem(LANDING_LOCALE_KEY, locale)
    } catch {
      /* ignore persistence failures */
    }
    document.documentElement.lang = locale
  }, [locale])

  const t = LANDING_COPY[locale]
  const whatsappUrl = whatsappUrlFor(t)
  const stepIcons = [Mic, Sparkles, ShieldCheck] as const

  return (
    <main className="landing-page" lang={locale}>
      <section className="landing-hero" aria-labelledby="landing-title">
        <img
          className="landing-hero-image"
          src="/urie-hero-v2.webp"
          alt={t.hero.imageAlt}
        />
        <div className="landing-hero-shade" aria-hidden="true" />

        <header className="landing-nav">
          <Link to="/about" aria-label={t.nav.homeAria}>
            <Logo />
          </Link>
          <div className="landing-nav-actions">
            <div className="landing-lang" role="group" aria-label={t.nav.langSwitcherAria}>
              <button
                type="button"
                className={locale === 'en' ? 'is-active' : undefined}
                aria-pressed={locale === 'en'}
                onClick={() => setLocale('en')}
              >
                EN
              </button>
              <button
                type="button"
                className={locale === 'ro' ? 'is-active' : undefined}
                aria-pressed={locale === 'ro'}
                onClick={() => setLocale('ro')}
              >
                RO
              </button>
            </div>
            <Link className="landing-pilot-link" to="/">
              {t.nav.enterPilot}
              <ArrowRight size={16} />
            </Link>
          </div>
        </header>

        <div className="landing-hero-copy">
          <p className="landing-kicker">{t.hero.kicker}</p>
          <h1 id="landing-title">
            {t.hero.titleBefore}
            <em>{t.hero.titleEm}</em>
          </h1>
          <p className="landing-hero-lede">{t.hero.lede}</p>
          <div className="landing-hero-actions">
            <a className="landing-primary-cta" href={whatsappUrl} target="_blank" rel="noreferrer">
              {t.hero.requestDemo}
              <MessageCircle size={18} />
            </a>
            <Link className="landing-secondary-cta" to="/">
              {t.hero.enterPilot}
            </Link>
          </div>
        </div>

        <a className="landing-scroll-cue" href="#the-gap" aria-label={t.hero.scrollCueAria}>
          <ArrowDown size={17} />
          <span>{t.hero.scrollCue}</span>
        </a>
      </section>

      <section className="landing-gap" id="the-gap" aria-labelledby="gap-title">
        <div className="landing-section-number" aria-hidden="true">01</div>
        <div className="landing-gap-heading">
          <p className="eyebrow">{t.gap.eyebrow}</p>
          <h2 id="gap-title">{t.gap.title}</h2>
        </div>
        <div className="landing-gap-copy">
          <p>{t.gap.p1}</p>
          <p>{t.gap.p2}</p>
        </div>
        <figure className="landing-trust-visual">
          <img
            src="/urie-trust-moment.webp"
            alt={t.gap.imageAlt}
            loading="lazy"
          />
          <figcaption>
            <span>{t.gap.figLabel}</span>
            <p>{t.gap.figCaption}</p>
          </figcaption>
        </figure>
        <blockquote>{t.gap.quote}</blockquote>
      </section>

      <section className="landing-overlay" aria-labelledby="overlay-title">
        <header className="landing-section-heading">
          <p className="eyebrow">{t.overlay.eyebrow}</p>
          <h2 id="overlay-title">{t.overlay.title}</h2>
          <p>{t.overlay.lede}</p>
        </header>

        <div className="landing-comparison" role="table" aria-label={t.overlay.tableAria}>
          <div className="landing-comparison-head" role="row">
            <span role="columnheader" className="landing-comparison-dim">
              {t.overlay.dimHeader}
            </span>
            <span role="columnheader">{t.overlay.crmHeader}</span>
            <span role="columnheader" className="landing-comparison-urie-col">
              {t.overlay.urieHeader}
            </span>
          </div>
          {t.overlay.rows.map((row) => (
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
          {t.overlay.differentiator}
          <em>{t.overlay.differentiatorEm}</em>
        </p>
      </section>

      <section className="landing-loop" aria-labelledby="loop-title">
        <header className="landing-section-heading">
          <p className="eyebrow">{t.loop.eyebrow}</p>
          <h2 id="loop-title">{t.loop.title}</h2>
          <p>{t.loop.lede}</p>
        </header>

        <ol className="landing-flywheel" aria-label={t.loop.flywheelAria}>
          {t.loop.flywheel.map((step, index) => (
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

        <div className="landing-script-preview" aria-label={t.loop.scriptAria}>
          <span className="landing-visual-label">{t.loop.scriptLabel}</span>
          <Sparkles size={18} />
          <p>{t.loop.scriptBody}</p>
          <small>{t.loop.scriptMeta}</small>
        </div>

        <ol className="landing-steps">
          {t.loop.steps.map((step, index) => {
            const Icon = stepIcons[index]
            return (
              <li key={step.title}>
                <span className="landing-step-icon"><Icon size={21} /></span>
                <span className="landing-step-index">0{index + 1}</span>
                <div>
                  <h3>{step.title}</h3>
                  <p>{step.body}</p>
                </div>
              </li>
            )
          })}
        </ol>
      </section>

      <section className="landing-ghost" aria-labelledby="ghost-title">
        <div className="landing-ghost-mark" aria-hidden="true">U</div>
        <div className="landing-ghost-copy">
          <p className="eyebrow">{t.ghost.eyebrow}</p>
          <h2 id="ghost-title">{t.ghost.title}</h2>
          <p>{t.ghost.body}</p>
        </div>
        <ul className="landing-trust-list" aria-label={t.ghost.listAria}>
          <li>
            <ShieldCheck size={18} />
            <span>{t.ghost.items[0]}</span>
          </li>
          <li>
            <Check size={18} />
            <span>{t.ghost.items[1]}</span>
          </li>
          <li>
            <Check size={18} />
            <span>{t.ghost.items[2]}</span>
          </li>
        </ul>
      </section>

      <section className="landing-demo" aria-labelledby="demo-title">
        <div className="landing-demo-inner">
          <p className="eyebrow">{t.demo.eyebrow}</p>
          <h2 id="demo-title">{t.demo.title}</h2>
          <p>{t.demo.body}</p>
          <a className="landing-whatsapp-cta" href={whatsappUrl} target="_blank" rel="noreferrer">
            <MessageCircle size={19} />
            {t.demo.whatsappCta}
            <ArrowRight size={18} />
          </a>
          <a className="landing-phone" href={whatsappUrl} target="_blank" rel="noreferrer">
            +40 734 755 202
          </a>
        </div>
      </section>

      <footer className="landing-footer">
        <Logo />
        <p>{t.footer.tagline}</p>
        <Link to="/">{t.footer.pilotSignIn}</Link>
      </footer>
    </main>
  )
}
