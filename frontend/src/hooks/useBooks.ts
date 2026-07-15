import type { Dispatch, SetStateAction } from "react";
import { useState } from "react";

import {
  deleteBook as deleteBookRequest,
  fetchBooks,
  uploadBook as uploadBookRequest
} from "../api";
import type { BookSummary } from "../types";

type SetError = Dispatch<SetStateAction<string | null>>;

export function useBooks(setError: SetError) {
  const [books, setBooks] = useState<BookSummary[]>([]);
  const [isLoadingBooks, setIsLoadingBooks] = useState(true);
  const [deletingBookId, setDeletingBookId] = useState<string | null>(null);
  const [bookPendingDelete, setBookPendingDelete] = useState<BookSummary | null>(null);

  async function refresh(showLoading = true) {
    if (showLoading) {
      setIsLoadingBooks(true);
    }
    setError(null);
    try {
      const nextBooks = await fetchBooks();
      setBooks(nextBooks);
      return nextBooks;
    } catch (error) {
      setError(error instanceof Error ? error.message : "加载书库失败");
      return [];
    } finally {
      if (showLoading) {
        setIsLoadingBooks(false);
      }
    }
  }

  async function upload(file: File | undefined) {
    if (!file) {
      return null;
    }
    setError(null);
    try {
      const book = await uploadBookRequest(file);
      setBooks((current) => [book, ...current]);
      return book;
    } catch (error) {
      setError(error instanceof Error ? error.message : "上传失败");
      return null;
    }
  }

  async function confirmDelete() {
    if (!bookPendingDelete) {
      return null;
    }

    const book = bookPendingDelete;
    setDeletingBookId(book.id);
    setError(null);
    try {
      await deleteBookRequest(book.id);
      setBooks((current) => current.filter((item) => item.id !== book.id));
      setBookPendingDelete(null);
      await refresh(false);
      return book.id;
    } catch (error) {
      setError(error instanceof Error ? error.message : "删除失败");
      return null;
    } finally {
      setDeletingBookId(null);
    }
  }

  function clear() {
    setBooks([]);
    setBookPendingDelete(null);
  }

  return {
    bookPendingDelete,
    books,
    clear,
    confirmDelete,
    deletingBookId,
    isLoadingBooks,
    refresh,
    setBookPendingDelete,
    setBooks,
    upload
  };
}
