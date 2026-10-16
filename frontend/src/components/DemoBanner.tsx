/** Shown on every screen of a demo deployment (VITE_DEMO_MODE=true): nobody should take demo figures for real accounts. */
export function DemoBanner() {
  if (import.meta.env.VITE_DEMO_MODE !== "true") return null
  return (
    <div role="note" className="bg-amber-500 px-4 py-1 text-center text-xs font-semibold text-navy-950">
      DEMO SYSTEM: all names and figures are made up. Do not enter real customer data or real money.
    </div>
  )
}
