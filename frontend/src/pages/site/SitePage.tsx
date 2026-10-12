import { useEffect, useRef, useState, type ReactNode } from "react"
import { Link } from "react-router-dom"
import { useAuth } from "../../api/auth"
import { AuditChainDemo } from "./AuditChainDemo"
import { CeremonyPlayground } from "./CeremonyPlayground"
import { CountUp } from "./CountUp"
import { DemoRequestForm } from "./DemoRequestForm"
import { HeroVisual } from "./HeroVisual"
import { ModelExplorer } from "./ModelExplorer"
import { Ribbon } from "./Ribbon"
import { BrandMark, SiteIcon } from "./SiteIcons"
import { Spotlight } from "./Spotlight"
import { AI_CAN, AI_CANNOT, CAPABILITIES, CEREMONY, FAQ, GOVERNANCE, NAV_LINKS, ROLES } from "./content"
import { useReveal } from "./useReveal"

const CONTAINER = "mx-auto w-full max-w-7xl px-5 sm:px-8"
const DISPLAY = "font-[family-name:var(--font-display)]"

function Section({ id, className = "", children }: { id?: string; className?: string; children: ReactNode }) {
  return (
    <section id={id} className={`relative scroll-mt-20 py-20 sm:py-28 ${className}`}>
      <div className={CONTAINER}>{children}</div>
    </section>
  )
}

function Heading({ eyebrow, title, lead, center = false }: { eyebrow: string; title: ReactNode; lead?: string; center?: boolean }) {
  return (
    <div className={`site-reveal max-w-3xl ${center ? "mx-auto text-center" : ""}`}>
      <p className="inline-flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.22em] text-gold-400">
        <span className="h-px w-8 bg-gold-500/60" aria-hidden="true" />
        {eyebrow}
      </p>
      <h2 className={`${DISPLAY} mt-4 text-3xl font-semibold leading-[1.1] tracking-tight text-ink-primary sm:text-4xl lg:text-[2.9rem]`}>{title}</h2>
      {lead && <p className="mt-5 text-base leading-relaxed text-ink-secondary sm:text-lg">{lead}</p>}
    </div>
  )
}

const BTN_PRIMARY =
  "group inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-b from-emerald-500 to-emerald-600 px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-emerald-900/40 ring-1 ring-inset ring-white/15 transition hover:from-emerald-400 hover:to-emerald-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
const BTN_GHOST =
  "inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 bg-white/[0.02] px-6 py-3.5 text-sm font-semibold text-ink-primary backdrop-blur transition hover:border-gold-500/60 hover:text-gold-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold-400"

function useActiveSection(ids: string[]) {
  const [active, setActive] = useState("")
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return
    const observer = new IntersectionObserver(
      (entries) => {
        for (const e of entries) if (e.isIntersecting) setActive(e.target.id)
      },
      { rootMargin: "-45% 0px -50% 0px" },
    )
    ids.forEach((id) => {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    })
    return () => observer.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return active
}

function Nav() {
  const { isAuthenticated } = useAuth()
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const [progress, setProgress] = useState(0)
  const active = useActiveSection(NAV_LINKS.map((l) => l.href.slice(1)))

  useEffect(() => {
    const onScroll = () => {
      setScrolled(window.scrollY > 12)
      const max = document.documentElement.scrollHeight - window.innerHeight
      setProgress(max > 0 ? Math.min(1, window.scrollY / max) : 0)
    }
    onScroll()
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-colors duration-300 ${
        scrolled || open ? "border-b border-white/8 bg-navy-950/80 backdrop-blur-xl" : "border-b border-transparent"
      }`}
    >
      <div className="absolute inset-x-0 top-0 h-[2px] bg-white/5" aria-hidden="true">
        <div className="h-full origin-left bg-gradient-to-r from-emerald-500 via-gold-400 to-emerald-400" style={{ transform: `scaleX(${progress})` }} />
      </div>
      <div className={`${CONTAINER} flex h-16 items-center justify-between`}>
        <a href="#top" className="flex items-center gap-3" aria-label="Amanah Pool OS - home">
          <BrandMark />
          <span className="leading-tight">
            <span className={`${DISPLAY} block text-lg font-semibold text-ink-primary`}>Amanah Pool OS</span>
            <span className="block text-[10px] uppercase tracking-[0.24em] text-gold-400">by Novu Labs</span>
          </span>
        </a>

        <nav className="hidden items-center gap-1 lg:flex" aria-label="Main">
          {NAV_LINKS.map((l) => {
            const on = active === l.href.slice(1)
            return (
              <a
                key={l.href}
                href={l.href}
                aria-current={on ? "true" : undefined}
                className={`relative rounded-md px-3.5 py-2 text-sm transition ${on ? "text-ink-primary" : "text-ink-secondary hover:text-ink-primary"}`}
              >
                {l.label}
                <span className={`absolute inset-x-3.5 -bottom-0.5 h-px bg-gradient-to-r from-transparent via-gold-400 to-transparent transition-opacity ${on ? "opacity-100" : "opacity-0"}`} />
              </a>
            )
          })}
        </nav>

        <div className="hidden items-center gap-3 lg:flex">
          <a href="#contact" className="text-sm font-medium text-ink-secondary transition hover:text-ink-primary">
            Request a demo
          </a>
          <Link
            to={isAuthenticated ? "/" : "/login"}
            className="rounded-lg border border-gold-500/50 bg-gold-500/10 px-4 py-2 text-sm font-semibold text-gold-400 transition hover:bg-gold-500/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold-400"
          >
            {isAuthenticated ? "Open workspace" : "Sign in"}
          </Link>
        </div>

        <button
          type="button"
          className="rounded-md p-2 text-ink-primary lg:hidden"
          aria-expanded={open}
          aria-controls="mobile-menu"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((v) => !v)}
        >
          <SiteIcon name={open ? "cross" : "menu"} className="h-6 w-6" />
        </button>
      </div>

      {open && (
        <div id="mobile-menu" className="border-t border-white/8 bg-navy-950/95 px-5 pb-6 pt-3 lg:hidden">
          <nav className="flex flex-col" aria-label="Mobile">
            {NAV_LINKS.map((l) => (
              <a key={l.href} href={l.href} onClick={() => setOpen(false)} className="border-b border-white/5 py-3 text-ink-secondary">
                {l.label}
              </a>
            ))}
            <a href="#contact" onClick={() => setOpen(false)} className="border-b border-white/5 py-3 text-ink-secondary">
              Request a demo
            </a>
          </nav>
          <Link
            to={isAuthenticated ? "/" : "/login"}
            className="mt-4 block rounded-lg border border-gold-500/50 bg-gold-500/10 px-4 py-3 text-center text-sm font-semibold text-gold-400"
          >
            {isAuthenticated ? "Open workspace" : "Sign in"}
          </Link>
        </div>
      )}
    </header>
  )
}

function Hero() {
  const { isAuthenticated } = useAuth()
  const ref = useRef<HTMLElement>(null)

  function onMove(e: React.MouseEvent<HTMLElement>) {
    const el = ref.current
    if (!el) return
    const r = el.getBoundingClientRect()
    el.style.setProperty("--hx", `${e.clientX - r.left}px`)
    el.style.setProperty("--hy", `${e.clientY - r.top}px`)
  }

  return (
    <section ref={ref} onMouseMove={onMove} id="top" className="relative overflow-hidden pb-24 pt-32 sm:pb-32 sm:pt-44">
      {/* aurora */}
      <div className="site-aurora-a pointer-events-none absolute -left-40 top-0 h-[34rem] w-[34rem] rounded-full bg-emerald-500/15 blur-[120px]" />
      <div className="site-aurora-b pointer-events-none absolute -right-40 -top-24 h-[34rem] w-[34rem] rounded-full bg-gold-500/15 blur-[120px]" />
      <div className="site-aurora-a pointer-events-none absolute bottom-0 left-1/3 h-72 w-72 rounded-full bg-violet-600/10 blur-[110px]" />
      {/* pattern and pointer light */}
      <div className="site-pattern pointer-events-none absolute inset-0 opacity-60 [mask-image:radial-gradient(ellipse_at_center,black_15%,transparent_70%)]" />
      <div
        className="pointer-events-none absolute inset-0 opacity-70"
        style={{ background: "radial-gradient(520px circle at var(--hx, 30%) var(--hy, 30%), rgba(52,211,153,0.08), transparent 60%)" }}
      />

      <div className={`${CONTAINER} relative grid items-center gap-16 lg:grid-cols-[1.1fr_0.9fr]`}>
        <div>
          <p className="site-rise inline-flex items-center gap-2 rounded-full border border-gold-500/30 bg-gold-500/10 px-3.5 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-gold-400" style={{ animationDelay: "0.05s" }}>
            <span className="h-1.5 w-1.5 rounded-full bg-gold-400" /> Islamic pool management
          </p>
          <div className="site-rise mt-7" style={{ animationDelay: "0.15s" }}>
            <h1 className={`${DISPLAY} site-shine-text text-[2.7rem] font-semibold leading-[1.03] tracking-tight sm:text-6xl lg:text-[4.6rem]`}>
              Run Islamic pools with proof, not promises.
            </h1>
          </div>
          <p className="site-rise mt-7 max-w-xl text-lg leading-relaxed text-ink-secondary sm:text-xl" style={{ animationDelay: "0.3s" }}>
            One platform for Islamic bank pools, Mudarabah and Musharakah investment pools, and community savings
            circles. Every release has four different people behind it, every calculation is sealed, and the audit trail
            can be verified by anyone who checks it.
          </p>
          <div className="site-rise mt-10 flex flex-col gap-3 sm:flex-row" style={{ animationDelay: "0.45s" }}>
            <a href="#contact" className={BTN_PRIMARY}>
              Request a demo <SiteIcon name="arrow" className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </a>
            <Link to={isAuthenticated ? "/" : "/login"} className={BTN_GHOST}>
              {isAuthenticated ? "Open workspace" : "Sign in to your workspace"}
            </Link>
          </div>
          <ul className="site-rise mt-8 flex flex-wrap gap-x-6 gap-y-2 text-xs text-ink-muted" style={{ animationDelay: "0.6s" }}>
            {["Multi-tenant", "Role-separated", "Maker-checker on every release", "AI that advises and never decides"].map((t) => (
              <li key={t} className="flex items-center gap-2">
                <span className="h-1 w-1 rotate-45 bg-gold-500" />
                {t}
              </li>
            ))}
          </ul>
        </div>
        <div className="site-rise" style={{ animationDelay: "0.35s" }}>
          <HeroVisual />
        </div>
      </div>
    </section>
  )
}

function Facts() {
  const items = [
    { node: <CountUp to={3} />, label: "operating models on one ledger" },
    { node: <CountUp to={4} />, label: "separate people to release a profit run" },
    { node: <CountUp to={11} />, label: "role-based workspaces" },
    { node: "SHA-256", label: "seal on runs, reports and the audit chain" },
  ]
  return (
    <div className="relative bg-gradient-to-b from-navy-900/70 to-navy-950">
      <div className={`${CONTAINER} grid grid-cols-2 gap-y-10 py-14 lg:grid-cols-4`}>
        {items.map((f) => (
          <div key={f.label} className="site-reveal px-2 text-center lg:border-l lg:border-white/8 lg:first:border-l-0">
            <p className={`${DISPLAY} text-5xl font-semibold text-gold-400 sm:text-6xl`}>{f.node}</p>
            <p className="mx-auto mt-3 max-w-[14rem] text-sm text-ink-secondary">{f.label}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function Statement() {
  return (
    <section className="relative overflow-hidden py-20 sm:py-28">
      <div className="site-pattern pointer-events-none absolute inset-0 opacity-50 [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]" />
      <div className={`${CONTAINER} relative`}>
        <div className="site-reveal mx-auto max-w-4xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-gold-400">Amanah · أمانة</p>
          <p className={`${DISPLAY} mt-7 text-3xl font-medium leading-[1.2] text-ink-primary sm:text-5xl`}>
            Managing other people&apos;s money is a trust. The platform exists so that trust can be{" "}
            <span className="site-gradient-text">shown, checked and kept</span>.
          </p>
        </div>
      </div>
    </section>
  )
}

function Models() {
  return (
    <Section id="models">
      <Heading
        eyebrow="Operating models"
        title="One ledger. Three ways of pooling."
        lead="The same core, workflow and audit layer runs a bank deposit pool, an investment pool and a community savings circle, each with its own rules."
      />
      <div className="site-reveal">
        <ModelExplorer />
      </div>
    </Section>
  )
}

function Platform() {
  return (
    <Section id="platform" className="bg-navy-900/50">
      <div className="site-pattern pointer-events-none absolute inset-0 opacity-40 [mask-image:linear-gradient(to_bottom,transparent,black_30%,black_70%,transparent)]" />
      <div className="relative">
        <Heading
          eyebrow="The platform"
          title="Controls that are part of the design, not a checklist added later."
          lead="Everything below is enforced by the system itself, so it does not depend on people remembering the rules."
        />
        <div className="mt-14 grid auto-rows-fr gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {CAPABILITIES.map((c, i) => {
            const wide = i === 0 || i === 5
            return (
              <Spotlight
                key={c.title}
                className={`site-reveal group rounded-2xl border border-white/10 bg-navy-800/50 p-6 transition-colors hover:border-emerald-500/40 ${wide ? "lg:col-span-2" : ""}`}
                style={{ transitionDelay: `${(i % 4) * 60}ms` }}
              >
                <span className="flex h-12 w-12 items-center justify-center rounded-xl border border-emerald-500/30 bg-gradient-to-br from-emerald-500/20 to-emerald-500/5 text-emerald-300 transition group-hover:scale-105">
                  <SiteIcon name={c.icon} className="h-5 w-5" />
                </span>
                <h3 className={`${wide ? `${DISPLAY} text-2xl` : "text-base"} mt-5 font-semibold text-ink-primary`}>{c.title}</h3>
                <p className={`mt-2 leading-relaxed text-ink-secondary ${wide ? "max-w-md text-[15px]" : "text-sm"}`}>{c.body}</p>
              </Spotlight>
            )
          })}
        </div>
      </div>
    </Section>
  )
}

function Ceremony() {
  return (
    <Section id="ceremony">
      <div className="grid gap-14 lg:grid-cols-[0.85fr_1.15fr]">
        <div className="space-y-8 lg:sticky lg:top-28 lg:self-start">
          <Heading
            eyebrow="Release ceremony"
            title="From calculation to release, no one acts alone."
            lead="A profit run passes through four different people. The system rejects a second role for the same person, so the control holds even on a busy day."
          />
          <div className="site-reveal">
            <CeremonyPlayground />
          </div>
        </div>
        <div>
          <ol className="relative space-y-5">
            <span className="absolute left-[21px] top-3 h-[calc(100%-1.5rem)] w-px bg-gradient-to-b from-emerald-500/60 via-gold-500/40 to-transparent" aria-hidden="true" />
            {CEREMONY.map((s, i) => (
              <li key={s.title} className="site-reveal relative flex gap-5" style={{ transitionDelay: `${i * 60}ms` }}>
                <span className={`${DISPLAY} z-10 flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-gold-500/50 bg-navy-900 text-lg font-semibold text-gold-400`}>
                  {i + 1}
                </span>
                <Spotlight className="flex-1 rounded-2xl border border-white/10 bg-navy-800/50 p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-400">{s.role}</p>
                  <h3 className="mt-1 text-lg font-semibold text-ink-primary">{s.title}</h3>
                  <p className="mt-1.5 text-sm text-ink-secondary">{s.body}</p>
                </Spotlight>
              </li>
            ))}
          </ol>
          <p className="site-reveal mt-6 rounded-xl border border-gold-500/30 bg-gold-500/10 p-4 text-sm text-gold-100/90">
            If a figure changes after sealing, the seal no longer matches and the release is refused. A signed run is
            corrected only by reversal and a linked rerun.
          </p>
        </div>
      </div>
    </Section>
  )
}

function Governance() {
  return (
    <Section id="governance" className="bg-navy-900/50">
      <Heading
        eyebrow="Governance and security"
        title="Built to be examined."
        lead="Controls an examiner, a Shariah Board or an auditor will ask about are already in the product."
      />
      <div className="site-reveal mt-12">
        <AuditChainDemo />
      </div>
      <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {GOVERNANCE.map((g) => (
          <Spotlight key={g.title} className="site-reveal rounded-2xl border border-white/10 bg-navy-900/80 p-7">
            <h3 className={`${DISPLAY} text-xl font-semibold text-gold-400`}>{g.title}</h3>
            <p className="mt-2.5 text-sm leading-relaxed text-ink-secondary">{g.body}</p>
          </Spotlight>
        ))}
      </div>
    </Section>
  )
}

function AiGuardrails() {
  return (
    <Section id="ai">
      <Heading
        eyebrow="AI guardrails"
        title="AI may recommend. People decide."
        lead="AI is useful for explaining and for spotting what a person should look at. It is never the authority."
      />
      <div className="mt-14 grid gap-6 lg:grid-cols-2">
        <div className="site-reveal rounded-2xl border border-emerald-500/25 bg-gradient-to-br from-emerald-500/10 to-transparent p-7">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-400">What it can do</p>
          <ul className="mt-5 space-y-3.5">
            {AI_CAN.map((t) => (
              <li key={t} className="flex items-start gap-3 text-sm text-ink-primary">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-300">
                  <SiteIcon name="check" className="h-3.5 w-3.5" />
                </span>
                {t}
              </li>
            ))}
          </ul>
        </div>
        <div className="site-reveal rounded-2xl border border-red-500/25 bg-gradient-to-br from-red-500/10 to-transparent p-7">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-red-300">What it can never do</p>
          <ul className="mt-5 space-y-3.5">
            {AI_CANNOT.map((t) => (
              <li key={t} className="flex items-start gap-3 text-sm text-ink-primary">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-red-500/20 text-red-300">
                  <SiteIcon name="cross" className="h-3.5 w-3.5" />
                </span>
                {t}
              </li>
            ))}
          </ul>
        </div>
      </div>
      <p className="site-reveal mt-6 text-sm text-ink-muted">
        Every AI output is stored with its sources, confidence and the decision a person took on it. A model can be switched off at any time.
      </p>
    </Section>
  )
}

function Roles() {
  return (
    <Section id="roles" className="bg-navy-900/50">
      <Heading
        eyebrow="Who sees what"
        title="Every role has its own workspace."
        lead="People see the areas their role works in, and the system enforces the same limits behind the screen."
      />
      <div className="mt-14 grid gap-4 sm:grid-cols-2">
        {ROLES.map((r) => (
          <Spotlight key={r.name} className="site-reveal rounded-xl border border-white/10 bg-navy-800/40 p-5">
            <h3 className="text-sm font-semibold text-ink-primary">{r.name}</h3>
            <p className="mt-1.5 text-sm text-ink-secondary">{r.does}</p>
          </Spotlight>
        ))}
      </div>
    </Section>
  )
}

function Faq() {
  return (
    <Section id="faq">
      <Heading eyebrow="Questions" title="Straight answers." center />
      <div className="mx-auto mt-12 max-w-3xl divide-y divide-white/10 rounded-2xl border border-white/10 bg-navy-800/40">
        {FAQ.map((f) => (
          <details key={f.q} className="group site-reveal p-6">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-base font-semibold text-ink-primary">
              {f.q}
              <span className="text-xl text-gold-400 transition group-open:rotate-45" aria-hidden="true">
                +
              </span>
            </summary>
            <p className="mt-3 text-sm leading-relaxed text-ink-secondary">{f.a}</p>
          </details>
        ))}
      </div>
    </Section>
  )
}

function Contact() {
  return (
    <Section id="contact" className="overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-navy-900/0 via-emerald-950/40 to-navy-900/0" />
      <div className="site-pattern pointer-events-none absolute inset-0 opacity-40 [mask-image:radial-gradient(ellipse_at_center,black,transparent_70%)]" />
      <div className="relative grid items-start gap-12 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="site-reveal">
          <p className="inline-flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.22em] text-gold-400">
            <span className="h-px w-8 bg-gold-500/60" aria-hidden="true" />
            Get started
          </p>
          <h2 className={`${DISPLAY} mt-4 text-4xl font-semibold leading-[1.08] text-ink-primary sm:text-6xl`}>See it work on your own rules.</h2>
          <p className="mt-5 text-lg leading-relaxed text-ink-secondary">
            Tell us what you run and we will walk you through the platform, from setting up a pool to closing a period.
          </p>
          <ul className="mt-8 space-y-3 text-sm text-ink-secondary">
            {[
              "A walk through the release ceremony and the audit trail",
              "Your operating model, your rule pack, your approval limits",
              "Questions from your Shariah, finance and risk teams are welcome",
            ].map((t) => (
              <li key={t} className="flex items-start gap-3">
                <SiteIcon name="check" className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                {t}
              </li>
            ))}
          </ul>
        </div>
        <div className="site-reveal">
          <DemoRequestForm />
        </div>
      </div>
    </Section>
  )
}

function Footer() {
  const { isAuthenticated } = useAuth()
  return (
    <footer className="relative overflow-hidden border-t border-white/8 bg-navy-950">
      <p
        className={`${DISPLAY} pointer-events-none absolute -bottom-6 left-1/2 -translate-x-1/2 select-none whitespace-nowrap text-[18vw] font-semibold leading-none text-white/[0.025]`}
        aria-hidden="true"
      >
        Amanah
      </p>
      <div className={`${CONTAINER} relative grid gap-10 py-16 md:grid-cols-[1.4fr_1fr_1fr]`}>
        <div>
          <div className="flex items-center gap-3">
            <BrandMark />
            <span className={`${DISPLAY} text-lg font-semibold text-ink-primary`}>Amanah Pool OS</span>
          </div>
          <p className="mt-4 max-w-sm text-sm text-ink-secondary">
            AI-based Islamic pool management with maker-checker control, sealed calculations and a verifiable audit trail.
          </p>
        </div>
        <nav aria-label="Footer">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold-400">Explore</p>
          <ul className="mt-4 space-y-2.5 text-sm">
            {NAV_LINKS.map((l) => (
              <li key={l.href}>
                <a href={l.href} className="text-ink-secondary transition hover:text-ink-primary">
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold-400">Access</p>
          <ul className="mt-4 space-y-2.5 text-sm">
            <li>
              <Link to={isAuthenticated ? "/" : "/login"} className="text-ink-secondary transition hover:text-ink-primary">
                {isAuthenticated ? "Open workspace" : "Sign in"}
              </Link>
            </li>
            <li>
              <a href="#contact" className="text-ink-secondary transition hover:text-ink-primary">
                Request a demo
              </a>
            </li>
          </ul>
        </div>
      </div>
      <div className="relative border-t border-white/8">
        <div className={`${CONTAINER} flex flex-col gap-2 py-6 text-xs text-ink-muted sm:flex-row sm:items-center sm:justify-between`}>
          <p>© {new Date().getFullYear()} Novu Labs. All rights reserved.</p>
          <p className="max-w-xl">
            Designed to support SBP, AAOIFI and IFSB frameworks through jurisdiction rule packs. Each implementation needs its own
            legal and Shariah review.
          </p>
        </div>
      </div>
    </footer>
  )
}

/** A bottom call to action on phones once the visitor has scrolled past the hero, hidden while the form is on screen. */
function StickyCta() {
  const [show, setShow] = useState(false)
  const [atForm, setAtForm] = useState(false)

  useEffect(() => {
    const onScroll = () => setShow(window.scrollY > 700)
    onScroll()
    window.addEventListener("scroll", onScroll, { passive: true })
    const form = document.getElementById("contact")
    let observer: IntersectionObserver | undefined
    if (form && typeof IntersectionObserver !== "undefined") {
      observer = new IntersectionObserver(([e]) => setAtForm(e.isIntersecting), { threshold: 0.15 })
      observer.observe(form)
    }
    return () => {
      window.removeEventListener("scroll", onScroll)
      observer?.disconnect()
    }
  }, [])

  return (
    <div
      className={`fixed inset-x-0 bottom-0 z-40 border-t border-white/10 bg-navy-950/90 p-3 backdrop-blur-xl transition-transform duration-300 lg:hidden ${
        show && !atForm ? "translate-y-0" : "translate-y-full"
      }`}
    >
      <a href="#contact" className={`${BTN_PRIMARY} w-full`} tabIndex={show && !atForm ? 0 : -1}>
        Request a demo
      </a>
    </div>
  )
}

export function SitePage() {
  useReveal()
  useEffect(() => {
    const previous = document.title
    document.title = "Amanah Pool OS - Islamic pool management platform"
    return () => {
      document.title = previous
    }
  }, [])

  return (
    <div className="site-grain min-h-screen overflow-x-clip bg-navy-950 font-sans text-ink-primary antialiased" data-testid="site">
      <a
        href="#platform"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded focus:bg-gold-500 focus:px-3 focus:py-2 focus:text-navy-950"
      >
        Skip to content
      </a>
      <Nav />
      <main>
        <Hero />
        <Ribbon />
        <Facts />
        <Statement />
        <Models />
        <Platform />
        <Ceremony />
        <Governance />
        <AiGuardrails />
        <Roles />
        <Faq />
        <Contact />
      </main>
      <Footer />
      <StickyCta />
    </div>
  )
}
