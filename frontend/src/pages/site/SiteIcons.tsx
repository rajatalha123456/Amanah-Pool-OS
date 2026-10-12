const PATHS: Record<string, string> = {
  calc: "M4 4h16v16H4zM8 8h8M8 12h3M13 12h3M8 16h3M13 16h3",
  people: "M9 11a3 3 0 100-6 3 3 0 000 6zM3 20a6 6 0 0112 0M17 11a2.5 2.5 0 100-5M21 20a5 5 0 00-4-4.9",
  scale: "M12 3v18M5 7h14M5 7l-3 7a3 3 0 006 0zM19 7l-3 7a3 3 0 006 0zM8 21h8",
  lock: "M6 11h12v9H6zM8 11V8a4 4 0 018 0v3M12 15v2",
  chain: "M9.5 14.5l5-5M8 11l-2 2a3.5 3.5 0 005 5l2-2M16 13l2-2a3.5 3.5 0 00-5-5l-2 2",
  spark: "M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM18 16l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z",
  user: "M12 12a4 4 0 100-8 4 4 0 000 8zM4 21a8 8 0 0116 0",
  layers: "M12 3l9 5-9 5-9-5zM3 13l9 5 9-5M3 17l9 5 9-5",
  check: "M5 12l4.5 4.5L19 7",
  cross: "M6 6l12 12M18 6L6 18",
  arrow: "M5 12h14M13 6l6 6-6 6",
  menu: "M4 7h16M4 12h16M4 17h16",
}

export function SiteIcon({ name, className = "h-5 w-5" }: { name: string; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      <path d={PATHS[name] ?? PATHS.check} />
    </svg>
  )
}

/** The brand mark: an eight-pointed star in a rounded square. */
export function BrandMark({ className = "h-9 w-9" }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={className} aria-hidden="true">
      <rect width="40" height="40" rx="10" fill="#0b1220" stroke="#d4af37" strokeOpacity="0.5" />
      <path
        d="M20 6l3.8 8.2L32.2 10l-4.2 8.2L36 20l-8 1.8 4.2 8.2-8.4-4.2L20 34l-3.8-8.2L7.8 30l4.2-8.2L4 20l8-1.8L7.8 10l8.4 4.2z"
        fill="none"
        stroke="#e6c65c"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <circle cx="20" cy="20" r="3.2" fill="#34d399" />
    </svg>
  )
}
