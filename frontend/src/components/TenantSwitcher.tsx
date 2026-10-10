import { RegulatoryJurisdictionSwitcher } from "./RegulatoryJurisdictionSwitcher"

export { RegulatoryJurisdictionSwitcher }

/**
 * TenantSwitcher (BRD Foundation Screen 02 & 06)
 * Re-exports the full interactive Cross-Jurisdiction & Regulatory Switcher.
 */
export function TenantSwitcher() {
  return <RegulatoryJurisdictionSwitcher />
}
