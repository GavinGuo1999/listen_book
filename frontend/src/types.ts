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
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};
