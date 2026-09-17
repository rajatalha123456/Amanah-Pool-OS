import { isAxiosError } from "axios"

function firstStringFromDetails(details: unknown): string | null {
  if (!details) {
    return null
  }

  // `details` can itself be a plain array of message strings (e.g. a
  // ValidationError raised with a single string, like the allocation
  // engine's ValueErrors: {"details": ["No DailyBalance records found..."]}).
  if (Array.isArray(details)) {
    return typeof details[0] === "string" ? details[0] : null
  }

  if (typeof details !== "object") {
    return null
  }

  // Otherwise `details` is field -> [messages] (e.g.
  // {"non_field_errors": ["Effective date range overlaps..."]} or
  // {"code": ["A pool with this code already exists."]}). Prefer
  // non_field_errors first (whole-object validation, e.g. BR-002 overlap
  // checks), then fall back to the first field found.
  const record = details as Record<string, unknown>
  const keys = ["non_field_errors", ...Object.keys(record).filter((k) => k !== "non_field_errors")]
  for (const key of keys) {
    const value = record[key]
    if (Array.isArray(value) && typeof value[0] === "string") {
      return value[0]
    }
  }
  return null
}

export function extractCopilotErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error) && error.response?.status === 503) {
    return "Shariah Copilot service is temporarily unavailable. Please try again in a moment."
  }
  return extractErrorMessage(error, fallback)
}

export function extractErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    const data = error.response?.data

    if (data && typeof data === "object") {
      // Standard shape: {"error": {"code", "message", "details"}}
      if ("error" in data) {
        const errorField = (data as { error: unknown }).error
        if (errorField && typeof errorField === "object") {
          const { message, details, code } = errorField as {
            message?: unknown
            details?: unknown
            code?: unknown
          }

          // For validation errors, "message" is often a generic
          // "Validation failed." while the actually useful text (e.g. a
          // BR-002 overlap message) lives in `details`. Prefer that when
          // available.
          if (code === "validation_error") {
            const detailMessage = firstStringFromDetails(details)
            if (detailMessage) {
              return detailMessage
            }
          }

          if (typeof message === "string") {
            return message
          }
        }
      }

      // Legacy shape used by a few pre-existing endpoints: {"detail": "..."}
      if ("detail" in data) {
        const detail = (data as { detail: unknown }).detail
        if (typeof detail === "string") {
          return detail
        }
      }
    }
  }
  return fallback
}
