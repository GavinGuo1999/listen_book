import type { Dispatch, SetStateAction } from "react";
import { useEffect, useMemo, useState } from "react";

import { fetchAdminBookReviews, reviewBook as reviewBookRequest } from "../api";
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
  const [page, setPage] = useState(1);

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
    if (filter === "pending") {
      return books.filter((book) => book.review_status === "pending_review");
    }
    if (filter === "failed") {
      return books.filter((book) => book.status === "failed");
    }
    if (filter === "rejected") {
      return books.filter((book) => book.review_status === "rejected");
    }
    return books;
  }, [books, filter]);

  const pageCount = Math.max(1, Math.ceil(filteredBooks.length / REVIEW_QUEUE_PAGE_SIZE));
  const pagedBooks = filteredBooks.slice(
    (page - 1) * REVIEW_QUEUE_PAGE_SIZE,
    page * REVIEW_QUEUE_PAGE_SIZE
  );

  useEffect(() => setPage(1), [filter]);
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

  return {
    filter,
    filteredBooks,
    isLoading,
    notesByBookId,
    page,
    pageCount,
    pagedBooks,
    refresh,
    review,
    reviewingBookId,
    setFilter,
    setPage,
    updateNote
  };
}
