export type BookSummary = {
  id: string;
  title: string;
  author: string | null;
  status: string;
  review_status: string;
  review_note: string | null;
  uploader_id: string | null;
  created_at: string;
};

export type BookReviewEvent = {
  id: string;
  reviewer_id: string | null;
  reviewer_username: string | null;
  reviewer_display_name: string | null;
  from_review_status: string;
  to_review_status: string;
  note: string | null;
  created_at: string;
};

export type AdminBookReviewSummary = BookSummary & {
  uploader_username: string | null;
  uploader_display_name: string | null;
  review_history: BookReviewEvent[];
};

export type Sentence = {
  id: string;
  sentence_index: number;
  text: string;
};

export type Paragraph = {
  id: string;
  paragraph_index: number;
  text: string;
  sentences: Sentence[];
};

export type Chapter = {
  id: string;
  title: string;
  chapter_index: number;
  paragraphs: Paragraph[];
};

export type AudioAsset = {
  id: string;
  sentence_id: string;
  status: string;
  audio_url: string | null;
  duration_ms: number | null;
};

export type AudioPrefetchResponse = {
  assets: AudioAsset[];
  queued_sentence_ids: string[];
};

export type AdminJob = {
  id: string;
  job_type: string;
  status: string;
  target_id: string | null;
  attempts: number;
  max_attempts: number;
  error_message: string | null;
  next_retry_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
};

export type ReadingProgress = {
  book_id: string;
  chapter_id: string | null;
  paragraph_id: string | null;
  sentence_id: string | null;
  audio_position_ms: number;
};

export type User = {
  id: string;
  username: string;
  display_name: string;
  is_admin: boolean;
  is_active: boolean;
};

export type AdminUser = User & {
  uploaded_book_count: number;
  created_at: string;
  updated_at: string;
};

export type AdminUserList = {
  items: AdminUser[];
  total: number;
  page: number;
  page_size: number;
};

export type AdminAuditEvent = {
  id: string;
  actor_id: string;
  actor_username: string | null;
  target_user_id: string | null;
  target_username: string | null;
  action: string;
  details: Record<string, unknown>;
  created_at: string;
};

export type SystemCheck = {
  key: string;
  label: string;
  status: "ok" | "warning" | "error";
  message: string;
};

export type WorkerStatus = {
  worker_id: string;
  hostname: string;
  process_id: number;
  started_at: string;
  last_seen_at: string;
  is_online: boolean;
};

export type AdminSystemStatus = {
  status: "ok" | "warning" | "error";
  version: string;
  checked_at: string;
  checks: SystemCheck[];
  workers: WorkerStatus[];
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};
