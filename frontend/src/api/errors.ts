import { isAxiosError } from "axios"

export function extractErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    const data = error.response?.data

    if (data && typeof data === "object") {
      // Standard shape: {"error": {"code", "message", "details"}}
      if ("error" in data) {
        const errorField = (data as { error: unknown }).error
        if (errorField && typeof errorField === "object" && "message" in errorField) {
          const message = (errorField as { message: unknown }).message
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
