/**
 * Accessible names for form controls (WCAG 2.2 AA: 1.3.1 Info and relationships, 3.3.2 Labels or instructions, 4.1.2).
 *
 * Many screens put a visible <label> next to a control without linking the two, or have a filter or a select with no
 * visible text. This pass runs over the page and gives every unnamed control a name, in this order:
 *   1. the visible <label> that sits directly before it (or is the only label in its container): linked with for / id;
 *   2. its placeholder;
 *   3. the text of the nearest preceding element (a small caption);
 *   4. for a select, its first option ("All statuses", "Select Member A"); otherwise a generic name for its kind.
 * Controls that already have a name (aria-label, aria-labelledby, a linked or wrapping label) are left untouched.
 */

let counter = 0

const CONTROLS = "input:not([type=hidden]):not([type=submit]):not([type=button]), select, textarea"

function isNamed(el: Element): boolean {
  if (el.getAttribute("aria-label") || el.getAttribute("aria-labelledby")) return true
  const id = el.getAttribute("id")
  if (id && document.querySelector(`label[for="${CSS.escape(id)}"]`)) return true
  return !!el.closest("label")
}

function hasControl(label: Element): boolean {
  return !!label.querySelector("input, select, textarea")
}

function text(el: Element | null): string {
  return (el?.textContent ?? "").replace(/\s+/g, " ").trim().replace(/\s*\*$/, "")
}

function link(control: Element, label: Element) {
  if (label.getAttribute("for")) return
  let id = control.getAttribute("id")
  if (!id) {
    id = `auto-label-${++counter}`
    control.setAttribute("id", id)
  }
  label.setAttribute("for", id)
}

function nameOf(control: Element): string {
  const placeholder = control.getAttribute("placeholder")
  if (placeholder) return placeholder
  const caption = text(control.previousElementSibling)
  if (caption && caption.length <= 60) return caption
  if (control.tagName === "SELECT") {
    const first = text((control as HTMLSelectElement).options?.[0] ?? null)
    if (first) return first
    return "Selection"
  }
  const type = control.getAttribute("type")
  if (type === "date") return "Date"
  if (type === "number") return "Amount or number"
  if (type === "checkbox" || type === "radio") return "Option"
  return "Text"
}

export function labelControls(root: ParentNode = document): void {
  root.querySelectorAll(CONTROLS).forEach((control) => {
    if (isNamed(control)) return

    const prev = control.previousElementSibling
    if (prev?.tagName === "LABEL" && !hasControl(prev) && text(prev)) {
      link(control, prev)
      return
    }
    const parent = control.parentElement
    if (parent) {
      const labels = Array.from(parent.children).filter((c) => c.tagName === "LABEL" && !hasControl(c) && text(c))
      const controls = Array.from(parent.children).filter((c) => c.matches(CONTROLS))
      if (labels.length === 1 && controls.length === 1) {
        link(control, labels[0])
        return
      }
    }
    control.setAttribute("aria-label", nameOf(control))
  })
}

/** Runs once now and again whenever the page changes (screens render their controls after their data loads). */
export function watchLabels(): () => void {
  let pending = false
  const run = () => {
    pending = false
    labelControls()
  }
  const observer = new MutationObserver(() => {
    if (pending) return
    pending = true
    requestAnimationFrame(run)
  })
  observer.observe(document.body, { childList: true, subtree: true })
  run()
  return () => observer.disconnect()
}
