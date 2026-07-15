import type { AdminBookReviewSummary } from "./types";

export type ReviewStatus = "approved" | "rejected" | "pending_review";
export type ReviewQueueFilter = "pending" | "failed" | "rejected" | "all";

export function reviewStatusLabel(status: string) {
  if (status === "pending_review") {
    return "待审批";
  }
  if (status === "rejected") {
    return "已拒绝";
  }
  return "已发布";
}

export function reviewerLabel(book: AdminBookReviewSummary) {
  if (book.uploader_display_name && book.uploader_username) {
    return `${book.uploader_display_name} @${book.uploader_username}`;
  }
  return book.uploader_username ? `@${book.uploader_username}` : "本地/未知上传者";
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "未知时间";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}
