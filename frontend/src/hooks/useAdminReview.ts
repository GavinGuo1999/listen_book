import type { Dispatch, SetStateAction } from "react";
import { useEffect, useMemo, useState } from "react";

import {
  batchReviewBooks,
  fetchAdminBookReviews,
  reviewBook as reviewBookRequest
} from "../api";
import type { AdminBookReviewSummary, BookSummary } from "../types";
import type { ReviewQueueFilter, ReviewStatus } from "../review";

const REVIEW_QUEUE_PAGE_SIZE = 5;
type SetError = Dispatch<SetStateAction<string | null>>;

export function useAdminReview(isAdmin: boolean, setError: SetError) {
  const [books, setBooks] = useState<AdminBookReviewSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [reviewingBookId, setReviewingBookId] = useState<string | null>(null);
  const [notesByBookId, setNotesByBookId] = useState<Record<string, string>>({});
  const [filter, setFilter] = useState<ReviewQueueFilter>("pending");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [selectedBookIds, setSelectedBookIds] = useState<Set<string>>(new Set());
  const [batchNote, setBatchNote] = useState("");
  const [isBatchReviewing, setIsBatchReviewing] = useState(false);

  async function refresh(showLoading = true) {
    if (!isAdmin) {
      return [];
    }
    if (showLoading) {
      setIsLoading(true);
    }
    try {
      const nextBooks = await fetchAdminBookReviews();
      setBooks(nextBooks);
      return nextBooks;
    } catch (error) {
      setError(error instanceof Error ? error.message : "加载审批列表失败");
      return [];
    } finally {
      if (showLoading) {
        setIsLoading(false);
      }
    }
  }

  useEffect(() => {
    if (isAdmin) {
      void refresh();
    } else {
      setBooks([]);
      setPage(1);
    }
  }, [isAdmin]);

  const filteredBooks = useMemo(() => {
    let result = books;
    if (filter === "pending") {
      result = result.filter((book) => book.review_status === "pending_review");
    }
    if (filter === "failed") result = result.filter((book) => book.status === "failed");
    if (filter === "rejected") result = result.filter((book) => book.review_status === "rejected");
    const normalizedQuery = query.trim().toLowerCase();
    if (normalizedQuery) {
      result = result.filter((book) =>
        [book.title, book.uploader_username, book.uploader_display_name]
          .filter(Boolean)
          .some((value) => value!.toLowerCase().includes(normalizedQuery))
      );
    }
    return result;
  }, [books, filter, query]);

  const pageCount = Math.max(1, Math.ceil(filteredBooks.length / REVIEW_QUEUE_PAGE_SIZE));
  const pagedBooks = filteredBooks.slice(
    (page - 1) * REVIEW_QUEUE_PAGE_SIZE,
    page * REVIEW_QUEUE_PAGE_SIZE
  );

  useEffect(() => {
    setPage(1);
    setSelectedBookIds(new Set());
  }, [filter, query]);
  useEffect(() => setPage((current) => Math.min(current, pageCount)), [pageCount]);

  async function review(book: BookSummary, status: ReviewStatus, note?: string) {
    setReviewingBookId(book.id);
    setError(null);
    try {
      const updatedBook = await reviewBookRequest(book.id, status, note);
      setNotesByBookId((current) => {
        const next = { ...current };
        delete next[book.id];
        return next;
      });
      await refresh(false);
      return updatedBook;
    } catch (error) {
      setError(error instanceof Error ? error.message : "审批失败");
      return null;
    } finally {
      setReviewingBookId(null);
    }
  }

  function updateNote(bookId: string, note: string) {
    setNotesByBookId((current) => ({ ...current, [bookId]: note }));
  }

  function toggleBookSelection(bookId: string) {
    setSelectedBookIds((current) => {
      const next = new Set(current);
      if (next.has(bookId)) next.delete(bookId);
      else next.add(bookId);
      return next;
    });
  }

  function selectPageBooks() {
    const selectableIds = pagedBooks
      .filter((book) => book.review_status !== "approved")
      .map((book) => book.id);
    const allSelected = selectableIds.every((bookId) => selectedBookIds.has(bookId));
    setSelectedBookIds((current) => {
      const next = new Set(current);
      for (const bookId of selectableIds) {
        if (allSelected) next.delete(bookId);
        else next.add(bookId);
      }
      return next;
    });
  }

  async function batchReview(status: "approved" | "rejected") {
    const bookIds = [...selectedBookIds];
    if (bookIds.length === 0) return [];
    setIsBatchReviewing(true);
    setError(null);
    try {
      const updatedBooks = await batchReviewBooks(bookIds, status, batchNote);
      setSelectedBookIds(new Set());
      setBatchNote("");
      await refresh(false);
      return updatedBooks;
    } catch (error) {
      setError(error instanceof Error ? error.message : "批量审批失败");
      return [];
    } finally {
      setIsBatchReviewing(false);
    }
  }

  return {
    batchNote,
    batchReview,
    filter,
    filteredBooks,
    isBatchReviewing,
    isLoading,
    notesByBookId,
    page,
    pageCount,
    pagedBooks,
    query,
    refresh,
    review,
    reviewingBookId,
    selectedBookIds,
    selectPageBooks,
    setBatchNote,
    setFilter,
    setPage,
    setQuery,
    toggleBookSelection,
    updateNote
  };
}
