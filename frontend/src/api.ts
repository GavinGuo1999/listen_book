import type {
  AdminBookReviewSummary,
  AdminJob,
  AudioAsset,
  AudioPrefetchResponse,
  AuthResponse,
  BookSummary,
  Chapter,
  ReadingProgress,
  User
} from "./types";

async function apiFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  return fetch(input, { ...init, credentials: "same-origin", headers });
}

async function readError(response: Response, fallback: string) {
  const message = await response.text();
  if (!message) {
    return fallback;
  }

  try {
    const payload = JSON.parse(message) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (Array.isArray(payload.detail)) {
      return payload.detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) {
            return String(item.msg);
          }
          return String(item);
        })
        .join("；");
    }
  } catch {
    // Fall back to raw text below.
  }

  return message;
}

export async function fetchCurrentUser(): Promise<User> {
  const response = await apiFetch("/api/auth/me");
  if (!response.ok) {
    throw new Error(await readError(response, "Failed to load current user"));
  }
  return response.json();
}

export async function registerUser(
  username: string,
  password: string
): Promise<AuthResponse> {
  const response = await apiFetch("/api/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      username,
      password
    })
  });
  if (!response.ok) {
    throw new Error(await readError(response, "Failed to register"));
  }
  return response.json();
}

export async function loginUser(username: string, password: string): Promise<AuthResponse> {
  const response = await apiFetch("/api/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ username, password })
  });
  if (!response.ok) {
    throw new Error(await readError(response, "Failed to login"));
  }
  return response.json();
}

export async function logoutUser(): Promise<void> {
  const response = await apiFetch("/api/auth/logout", {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(await readError(response, "Failed to logout"));
  }
}

export async function fetchBooks(): Promise<BookSummary[]> {
  const response = await apiFetch("/api/books");
  if (!response.ok) {
    throw new Error("Failed to load books");
  }
  return response.json();
}

export async function fetchAdminBookReviews(): Promise<AdminBookReviewSummary[]> {
  const response = await apiFetch("/api/admin/books/reviews");
  if (!response.ok) {
    throw new Error(await readError(response, "Failed to load admin review books"));
  }
  return response.json();
}

export async function fetchAdminJobs(status?: string): Promise<AdminJob[]> {
  const query = status && status !== "all" ? `?status=${encodeURIComponent(status)}` : "";
  const response = await apiFetch(`/api/admin/jobs${query}`);
  if (!response.ok) {
    throw new Error(await readError(response, "Failed to load jobs"));
  }
  return response.json();
}

export async function retryAdminJob(jobId: string): Promise<AdminJob> {
  const response = await apiFetch(`/api/admin/jobs/${jobId}/retry`, { method: "POST" });
  if (!response.ok) {
    throw new Error(await readError(response, "Failed to retry job"));
  }
  return response.json();
}

export async function uploadBook(file: File): Promise<BookSummary> {
  const body = new FormData();
  body.append("file", file);

  const response = await apiFetch("/api/books", {
    method: "POST",
    body
  });
  if (!response.ok) {
    throw new Error(await readError(response, "Failed to upload book"));
  }
  return response.json();
}

export async function deleteBook(bookId: string): Promise<void> {
  const response = await apiFetch(`/api/books/${bookId}`, {
    method: "DELETE"
  });
  if (!response.ok) {
    throw new Error(await readError(response, "Failed to delete book"));
  }
}

export async function reviewBook(
  bookId: string,
  reviewStatus: "approved" | "rejected" | "pending_review",
  reviewNote?: string
): Promise<BookSummary> {
  const response = await apiFetch(`/api/admin/books/${bookId}/review`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      review_status: reviewStatus,
      review_note: reviewNote || null
    })
  });
  if (!response.ok) {
    throw new Error(await readError(response, "Failed to review book"));
  }
  return response.json();
}

export async function fetchChapters(bookId: string): Promise<Chapter[]> {
  const response = await apiFetch(`/api/books/${bookId}/chapters`);
  if (!response.ok) {
    throw new Error("Failed to load chapters");
  }
  return response.json();
}

export async function fetchBookProgress(bookId: string): Promise<ReadingProgress | null> {
  const response = await apiFetch(`/api/books/${bookId}/progress`);
  if (!response.ok) {
    throw new Error("Failed to load reading progress");
  }
  return response.json();
}

export async function saveBookProgress(
  bookId: string,
  sentenceId: string | null,
  audioPositionMs = 0
): Promise<ReadingProgress> {
  const response = await apiFetch(`/api/books/${bookId}/progress`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      sentence_id: sentenceId,
      audio_position_ms: audioPositionMs
    })
  });
  if (!response.ok) {
    throw new Error(await readError(response, "Failed to save reading progress"));
  }
  return response.json();
}

export async function generateSentenceAudio(sentenceId: string): Promise<AudioAsset> {
  const response = await apiFetch(`/api/audio/sentences/${sentenceId}`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(await readError(response, "Failed to generate audio"));
  }
  return response.json();
}

export async function prefetchSentenceAudio(
  sentenceIds: string[]
): Promise<AudioPrefetchResponse> {
  const response = await apiFetch("/api/audio/sentences/prefetch", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ sentence_ids: sentenceIds })
  });
  if (!response.ok) {
    throw new Error(await readError(response, "Failed to prefetch audio"));
  }
  return response.json();
}

export async function prefetchChapterAudio(chapterId: string): Promise<AudioPrefetchResponse> {
  const response = await apiFetch(`/api/audio/chapters/${chapterId}/prefetch`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(await readError(response, "Failed to prefetch chapter audio"));
  }
  return response.json();
}

export async function fetchSentenceAudioStatuses(sentenceIds: string[]): Promise<AudioAsset[]> {
  const response = await apiFetch("/api/audio/sentences/status", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ sentence_ids: sentenceIds })
  });
  if (!response.ok) {
    throw new Error(await readError(response, "Failed to load audio statuses"));
  }
  return response.json();
}
