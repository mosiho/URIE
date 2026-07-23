export type LandingLocale = 'en' | 'ro'

export type LandingCopy = {
  whatsappText: string
  nav: {
    homeAria: string
    enterPilot: string
    langSwitcherAria: string
  }
  hero: {
    imageAlt: string
    kicker: string
    titleBefore: string
    titleEm: string
    lede: string
    requestDemo: string
    enterPilot: string
    scrollCueAria: string
    scrollCue: string
  }
  gap: {
    eyebrow: string
    title: string
    p1: string
    p2: string
    imageAlt: string
    figLabel: string
    figCaption: string
    quote: string
  }
  overlay: {
    eyebrow: string
    title: string
    lede: string
    tableAria: string
    dimHeader: string
    crmHeader: string
    urieHeader: string
    rows: Array<{ dimension: string; crm: string; urie: string }>
    differentiator: string
    differentiatorEm: string
  }
  loop: {
    eyebrow: string
    title: string
    lede: string
    flywheelAria: string
    flywheel: Array<{ index: string; title: string; detail: string; example: string }>
    scriptAria: string
    scriptLabel: string
    scriptBody: string
    scriptMeta: string
    steps: Array<{ title: string; body: string }>
  }
  ghost: {
    eyebrow: string
    title: string
    body: string
    listAria: string
    items: [string, string, string]
  }
  demo: {
    eyebrow: string
    title: string
    body: string
    whatsappCta: string
  }
  footer: {
    tagline: string
    pilotSignIn: string
  }
}

export const LANDING_COPY: Record<LandingLocale, LandingCopy> = {
  en: {
    whatsappText: "Hello, I'd like to see a free demo of URIE.",
    nav: {
      homeAria: 'URIE home',
      enterPilot: 'Enter the pilot',
      langSwitcherAria: 'Choose language',
    },
    hero: {
      imageAlt: 'A real-estate agent recording a private debrief after a client meeting',
      kicker: 'Relationship Intelligence for solo high-value agents',
      titleBefore: 'URIE remembers the conversation ',
      titleEm: 'your CRM never heard.',
      lede:
        'A private daily debrief turns what stayed in your head into living memory—and the exact words to use when timing wins the relationship.',
      requestDemo: 'Request a free demo',
      enterPilot: 'Enter the private pilot',
      scrollCueAria: 'Explore how URIE works',
      scrollCue: 'Discover the difference',
    },
    gap: {
      eyebrow: 'The conversation that never got written down',
      title: 'High-value deals turn on details no database ever held.',
      p1:
        'Your best clients rarely put the most important thing in a form. They mention it once—in a car, between meetings, at the end of a call—and it lives only in your head.',
      p2:
        'Every other tool organizes digital exhaust: email, calendar, MLS, CRM fields. They can only see what was already captured somewhere. URIE captures what stayed with you, keeps it alive, and surfaces it when remembering becomes extraordinary service.',
      imageAlt: 'A real-estate advisor listening closely as clients share personal context',
      figLabel: 'Face-to-face trust stays yours',
      figCaption: 'URIE never joins the meeting. It captures what you remember after.',
      quote:
        '“The agent who remembers the detail no one else did becomes the agent no one forgets.”',
    },
    overlay: {
      eyebrow: 'Not a CRM — an intelligence layer',
      title: 'Keep the CRM your brokerage requires. Use URIE to win the client.',
      lede:
        'Traditional tools are systems of record. URIE is a system of intelligence that sits on top—zero migration, clean notes written back when you want them.',
      tableAria: 'Traditional CRM versus URIE',
      dimHeader: 'Dimension',
      crmHeader: 'Traditional CRM',
      urieHeader: 'URIE',
      rows: [
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
      ],
      differentiator: 'Everyone else organizes what your CRM already knows.',
      differentiatorEm: ' We remember what it never even saw.',
    },
    loop: {
      eyebrow: 'How URIE works',
      title: 'Two minutes in. A relationship advantage out.',
      lede:
        'No forms to maintain. No stack to rip out. Just a bounded, private conversation with URIE—then the right moment, ready when you are.',
      flywheelAria: 'From daily moments to a timely script',
      flywheel: [
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
      ],
      scriptAria: 'Example ghost-mode script',
      scriptLabel: 'Example script',
      scriptBody: 'Call Friday. Ask how the launch went before discussing the property.',
      scriptMeta: 'Context remembered · boundary respected · you deliver it',
      steps: [
        {
          title: 'Debrief privately',
          body: 'Tell URIE what happened today. It asks only the questions that close a meaningful knowledge gap—never a static questionnaire.',
        },
        {
          title: 'Build living memory',
          body: 'People, preferences, boundaries, and life changes become connected context—not scattered notes that go stale overnight.',
        },
        {
          title: 'Act at the right moment',
          body: 'Receive a thoughtful script with the reason and timing behind it. You make the human connection. URIE stays invisible.',
        },
      ],
    },
    ghost: {
      eyebrow: 'Ghost mode',
      title: 'The intelligence stays invisible. The relationship stays yours.',
      body: 'URIE never messages your client, never joins a client call, and never takes credit. It quietly prepares you to show up with precision, warmth, and perfect timing—so the prestige lands with you.',
      listAria: 'URIE privacy promises',
      items: [
        'Only your agent↔URIE debrief is processed — client conversations are never recorded',
        'Your existing CRM stays in place',
        'You keep every human moment',
      ],
    },
    demo: {
      eyebrow: 'A private invitation',
      title: 'See what your relationships could remember.',
      body: 'Request a free personal demo. We will walk through one real day in your book of business and show you exactly where URIE creates an advantage.',
      whatsappCta: 'Get your free demo on WhatsApp',
    },
    footer: {
      tagline: 'Private relationship intelligence for high-value real estate.',
      pilotSignIn: 'Pilot sign in',
    },
  },
  ro: {
    whatsappText: 'Bună ziua, aș dori o demonstrație gratuită a URIE.',
    nav: {
      homeAria: 'Pagina principală URIE',
      enterPilot: 'Intră în pilot',
      langSwitcherAria: 'Alege limba',
    },
    hero: {
      imageAlt: 'Un agent imobiliar care înregistrează un debrief privat după o întâlnire cu clienții',
      kicker: 'Relationship Intelligence pentru agenți solo de valoare mare',
      titleBefore: 'URIE își amintește conversația pe care ',
      titleEm: 'CRM-ul tău nu a auzit-o niciodată.',
      lede:
        'Un debrief zilnic privat transformă ce a rămas în mintea ta în memorie vie—și în cuvintele exacte de folosit când timing-ul câștigă relația.',
      requestDemo: 'Cere o demonstrație gratuită',
      enterPilot: 'Intră în pilotul privat',
      scrollCueAria: 'Descoperă cum funcționează URIE',
      scrollCue: 'Descoperă diferența',
    },
    gap: {
      eyebrow: 'Conversația care nu a fost scrisă niciodată',
      title: 'Tranzacțiile de valoare mare se decid pe detalii pe care nicio bază de date nu le-a ținut.',
      p1:
        'Cei mai buni clienți rar pun cel mai important lucru într-un formular. Îl menționează o singură dată—în mașină, între întâlniri, la finalul unui apel—și rămâne doar în mintea ta.',
      p2:
        'Orice alt tool organizează resturile digitale: email, calendar, MLS, câmpuri din CRM. Pot vedea doar ce a fost deja capturat undeva. URIE capturează ce a rămas la tine, îl ține viu și îl scoate la lumină când amintirea devine un serviciu extraordinar.',
      imageAlt: 'Un consultant imobiliar care ascultă atent în timp ce clienții împărtășesc context personal',
      figLabel: 'Încrederea față în față rămâne a ta',
      figCaption: 'URIE nu participă la întâlnire. Capturează ce îți amintești după.',
      quote:
        '„Agentul care își amintește detaliul pe care nimeni altcineva nu l-a reținut devine agentul pe care nimeni nu-l uită.”',
    },
    overlay: {
      eyebrow: 'Nu un CRM — un strat de inteligență',
      title: 'Păstrează CRM-ul cerut de brokeraj. Folosește URIE ca să câștigi clientul.',
      lede:
        'Instrumentele tradiționale sunt sisteme de înregistrare. URIE este un sistem de inteligență care stă deasupra—zero migrare, note curate trimise înapoi când vrei tu.',
      tableAria: 'CRM tradițional versus URIE',
      dimHeader: 'Dimensiune',
      crmHeader: 'CRM tradițional',
      urieHeader: 'URIE',
      rows: [
        {
          dimension: 'Fricțiune',
          crm: 'Tastare manuală, formulare și follow-up-uri uitate',
          urie: 'Un scurt debrief vocal capturează ce s-a întâmplat prin vorbire',
        },
        {
          dimension: 'Vizibilitate',
          crm: 'Doar ce a avut cineva timp să tasteze',
          urie: 'Și ce a fost spus o singură dată — și niciodată scris',
        },
        {
          dimension: 'Focus',
          crm: 'Etape de pipeline, task-uri și fișe de contact',
          urie: 'Sănătatea relației, limite și memorie vie',
        },
        {
          dimension: 'Output',
          crm: 'Reminder-e statice („Sună-l pe John azi”)',
          urie: 'Scripturi comportamentale cu timing și motivul din spate',
        },
      ],
      differentiator: 'Toți ceilalți organizează ce știe deja CRM-ul tău.',
      differentiatorEm: ' Noi ne amintim ce nu a văzut niciodată.',
    },
    loop: {
      eyebrow: 'Cum funcționează URIE',
      title: 'Două minute pe intrare. Un avantaj de relație pe ieșire.',
      lede:
        'Fără formulare de întreținut. Fără stivă de înlocuit. Doar o conversație privată, limitată, cu URIE—apoi momentul potrivit, gata când ești tu.',
      flywheelAria: 'De la momentele zilei la un script la timp',
      flywheel: [
        {
          index: '01',
          title: 'Ziua se acumulează',
          detail: 'Momentele cu clienții rămân în mintea ta — nu într-un formular.',
          example: 'Săptămâna aglomerată a lui John se termină vineri.',
        },
        {
          index: '02',
          title: 'Debrief privat',
          detail: 'URIE te intervievează pe tine — niciodată pe client. Cel mult o dată sau de două ori pe zi.',
          example: 'Îl spui în mai puțin de două minute.',
        },
        {
          index: '03',
          title: 'Memorie vie',
          detail: 'Preferințe, limite și schimbări de viață devin context conectat.',
          example: 'Săptămână aglomerată · lansare · nu forța încă proprietatea.',
        },
        {
          index: '04',
          title: 'Script ghost-mode',
          detail: 'Primești cuvintele și timing-ul potrivit. Păstrezi fiecare moment uman.',
          example: 'Sună vineri. Întreabă mai întâi cum a mers lansarea.',
        },
      ],
      scriptAria: 'Exemplu de script ghost-mode',
      scriptLabel: 'Script exemplu',
      scriptBody: 'Sună vineri. Întreabă cum a mers lansarea înainte să discuți proprietatea.',
      scriptMeta: 'Context reținut · limită respectată · tu îl livrezi',
      steps: [
        {
          title: 'Debriefează în privat',
          body: 'Spune-i lui URIE ce s-a întâmplat azi. Întreabă doar întrebările care închid o lacună de cunoaștere importantă—niciodată un chestionar static.',
        },
        {
          title: 'Construiește memoria vie',
          body: 'Oameni, preferințe, limite și schimbări de viață devin context conectat—nu note împrăștiate care se învechesc peste noapte.',
        },
        {
          title: 'Acționează la momentul potrivit',
          body: 'Primești un script atent, cu motivul și timing-ul din spate. Tu faci conexiunea umană. URIE rămâne invizibil.',
        },
      ],
    },
    ghost: {
      eyebrow: 'Ghost mode',
      title: 'Inteligența rămâne invizibilă. Relația rămâne a ta.',
      body: 'URIE nu îi scrie niciodată clientului tău, nu intră într-un apel cu clientul și nu își asumă creditul. Te pregătește în liniște să apari cu precizie, căldură și timing perfect—ca prestigiul să rămână al tău.',
      listAria: 'Promisiunile de confidențialitate URIE',
      items: [
        'Doar debrief-ul agent↔URIE este procesat — conversațiile cu clienții nu sunt niciodată înregistrate',
        'CRM-ul tău existent rămâne pe loc',
        'Păstrezi fiecare moment uman',
      ],
    },
    demo: {
      eyebrow: 'O invitație privată',
      title: 'Vezi ce ar putea ține minte relațiile tale.',
      body: 'Cere o demonstrație personală gratuită. Vom parcurge o zi reală din portofoliul tău și îți vom arăta exact unde URIE creează un avantaj.',
      whatsappCta: 'Primește demonstrația gratuită pe WhatsApp',
    },
    footer: {
      tagline: 'Relationship intelligence privată pentru imobiliare de valoare mare.',
      pilotSignIn: 'Autentificare pilot',
    },
  },
}

export const LANDING_LOCALE_KEY = 'urie_landing_locale'

export function resolveLandingLocale(stored: string | null): LandingLocale {
  return stored === 'ro' ? 'ro' : 'en'
}

export function whatsappUrlFor(copy: LandingCopy): string {
  return `https://wa.me/40734755202?text=${encodeURIComponent(copy.whatsappText)}`
}
