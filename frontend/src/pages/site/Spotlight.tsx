import { useRef, type CSSProperties, type ReactNode } from "react"

/** A card with a soft gold light that follows the pointer. Purely decorative: it needs no motion to be usable. */
export function Spotlight({ children, className = "", style }: { children: ReactNode; className?: string; style?: CSSProperties }) {
  const ref = useRef<HTMLDivElement>(null)

  function onMove(e: React.MouseEvent<HTMLDivElement>) {
    const el = ref.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    el.style.setProperty("--mx", `${e.clientX - rect.left}px`)
    el.style.setProperty("--my", `${e.clientY - rect.top}px`)
  }

  return (
    <div ref={ref} onMouseMove={onMove} className={`site-spot ${className}`} style={style}>
      {children}
    </div>
  )
}
