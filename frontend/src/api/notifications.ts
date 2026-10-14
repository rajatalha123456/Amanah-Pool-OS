import { apiClient } from "./axios"
import { pageParams, type Page } from "./pagination"

export interface AppNotification {
  id: string
  category: "approval_required" | "approval_outcome" | "arrears_reminder" | "economics_change" | "system"
  title: string
  body: string
  link: string
  is_read: boolean
  read_at: string | null
  email_status: string
  created_at: string
}

export async function fetchNotifications(
  params?: { unread?: boolean; category?: string },
  page = 1,
  pageSize?: number,
): Promise<Page<AppNotification>> {
  const response = await apiClient.get<Page<AppNotification>>("notifications/", {
    params: {
      ...(params?.unread ? { unread: "true" } : {}),
      ...(params?.category ? { category: params.category } : {}),
      ...pageParams(page, pageSize),
    },
  })
  return response.data
}

export async function fetchUnreadCount(): Promise<number> {
  return (await apiClient.get<{ count: number }>("notifications/unread-count/")).data.count
}

export async function markNotificationRead(id: string): Promise<AppNotification> {
  return (await apiClient.post<AppNotification>(`notifications/${id}/mark-read/`)).data
}

export async function markAllNotificationsRead(): Promise<number> {
  return (await apiClient.post<{ marked: number }>("notifications/mark-all-read/")).data.marked
}
