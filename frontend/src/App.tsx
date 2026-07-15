import { useEffect, useMemo, useState } from "react";

import { AppSidebar } from "./components/AppSidebar";
import { DeleteBookDialog } from "./components/DeleteBookDialog";
import { useAdminReview } from "./hooks/useAdminReview";
import { useAdminJobs } from "./hooks/useAdminJobs";
import { useAudioPlayer } from "./hooks/useAudioPlayer";
import { useAuth } from "./hooks/useAuth";
import { useBooks } from "./hooks/useBooks";
import { AdminReviewPage } from "./pages/AdminReviewPage";
import { AuthLoadingPage, LoginPage } from "./pages/LoginPage";
import { ReaderPage } from "./pages/ReaderPage";
import type { ReviewStatus } from "./review";
import type { BookSummary } from "./types";

const PROCESSING_STATUSES = new Set(["uploaded", "parsing"]);

export function App() {
  const [currentPath, setCurrentPath] = useState(window.location.pathname);
  const [error, setError] = useState<string | null>(null);
  const auth = useAuth();
  const books = useBooks(setError);
  const player = useAudioPlayer(setError);
  const admin = useAdminReview(auth.currentUser?.is_admin ?? false, setError);
  const adminJobs = useAdminJobs(auth.currentUser?.is_admin ?? false, setError);

  const selectedBook = useMemo(
    () => books.books.find((book) => book.id === player.selectedBookId) ?? null,
    [books.books, player.selectedBookId]
  );
  const isAdminPage = currentPath === "/admin";

  function navigate(path: string, replace = false) {
    if (window.location.pathname === path) {
      setCurrentPath(path);
      return;
    }
    if (replace) {
      window.history.replaceState(null, "", path);
    } else {
      window.history.pushState(null, "", path);
    }
    setCurrentPath(path);
  }

  useEffect(() => {
    void (async () => {
      const user = await auth.bootstrap();
      if (user) {
        await books.refresh();
      } else {
        books.clear();
      }
    })();

    const handlePopState = () => setCurrentPath(window.location.pathname);
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    if (auth.isCheckingAuth) return;
    if (!auth.currentUser && currentPath !== "/login") {
      navigate("/login", true);
      return;
    }
    if (auth.currentUser && (currentPath === "/" || currentPath === "/login")) {
      navigate("/app", true);
      return;
    }
    if (auth.currentUser && currentPath === "/admin" && !auth.currentUser.is_admin) {
      navigate("/app", true);
    }
  }, [auth.currentUser, auth.isCheckingAuth, currentPath]);

  useEffect(() => {
    if (!selectedBook || !PROCESSING_STATUSES.has(selectedBook.status)) return;
    const intervalId = window.setInterval(async () => {
      const nextBooks = await books.refresh(false);
      const updatedBook = nextBooks.find((book) => book.id === selectedBook.id);
      if (updatedBook?.status === "ready") {
        await player.loadChapters(updatedBook.id);
      } else if (updatedBook?.status === "failed") {
        setError("书籍解析失败，请检查文件格式或稍后重试");
      }
    }, 2000);
    return () => window.clearInterval(intervalId);
  }, [selectedBook?.id, selectedBook?.status]);

  async function handleAuthSubmit(event: React.FormEvent<HTMLFormElement>) {
    const user = await auth.submit(event);
    if (!user) return;
    player.clear();
    navigate("/app", true);
    await books.refresh();
  }

  async function handleLogout() {
    await auth.logout();
    books.clear();
    player.clear();
    navigate("/login", true);
  }

  async function handleUpload(file: File | undefined) {
    const book = await books.upload(file);
    if (book) player.selectUploadedBook(book);
  }

  async function handleDelete() {
    const deletedBookId = await books.confirmDelete();
    if (deletedBookId === player.selectedBookId) player.clear();
  }

  async function handleReview(book: BookSummary, status: ReviewStatus, note?: string) {
    const updatedBook = await admin.review(book, status, note);
    if (!updatedBook) return;
    books.setBooks((current) =>
      current.map((item) => (item.id === updatedBook.id ? updatedBook : item))
    );
    await books.refresh(false);
  }

  if (auth.isCheckingAuth) return <AuthLoadingPage />;

  if (!auth.currentUser || currentPath === "/login") {
    return (
      <LoginPage
        authError={auth.authError}
        authMode={auth.authMode}
        authPassword={auth.authPassword}
        authUsername={auth.authUsername}
        isSubmitting={auth.isAuthSubmitting}
        onModeChange={auth.setAuthMode}
        onPasswordChange={auth.setAuthPassword}
        onSubmit={handleAuthSubmit}
        onUsernameChange={auth.setAuthUsername}
      />
    );
  }

  return (
    <main className="app-shell" data-testid="app-shell">
      <AppSidebar
        books={books.books}
        currentUser={auth.currentUser}
        deletingBookId={books.deletingBookId}
        isAdminPage={isAdminPage}
        isLoadingBooks={books.isLoadingBooks}
        onDeleteBook={books.setBookPendingDelete}
        onLogout={handleLogout}
        onNavigate={navigate}
        onReviewBook={handleReview}
        onSelectBook={player.selectBook}
        onUpload={handleUpload}
        reviewingBookId={admin.reviewingBookId}
        selectedBookId={player.selectedBookId}
      />

      {isAdminPage ? (
        <AdminReviewPage
          error={error}
          filter={admin.filter}
          filteredCount={admin.filteredBooks.length}
          isLoading={admin.isLoading}
          jobFilter={adminJobs.filter}
          jobs={adminJobs.jobs}
          jobsLoading={adminJobs.isLoading}
          notesByBookId={admin.notesByBookId}
          onFilterChange={admin.setFilter}
          onJobFilterChange={adminJobs.changeFilter}
          onJobsRefresh={adminJobs.refresh}
          onNoteChange={admin.updateNote}
          onPageChange={admin.setPage}
          onRefresh={admin.refresh}
          onReview={handleReview}
          onRetryJob={adminJobs.retry}
          onSelectBook={player.selectBook}
          page={admin.page}
          pageCount={admin.pageCount}
          pagedBooks={admin.pagedBooks}
          reviewingBookId={admin.reviewingBookId}
          retryingJobId={adminJobs.retryingJobId}
        />
      ) : (
        <ReaderPage
          activePrefetchChapterId={player.activePrefetchChapterId}
          audioRef={player.audioRef}
          chapters={player.chapters}
          currentSentence={player.currentSentence}
          currentSentenceId={player.currentSentenceId}
          error={error}
          getChapterAudioProgress={player.getChapterAudioProgress}
          getSentenceAudioState={player.getSentenceAudioState}
          isGeneratingAudio={player.isGeneratingAudio}
          isLoadingChapters={player.isLoadingChapters}
          isPlaying={player.isPlaying}
          onAudioEnded={player.playNextSentence}
          onAudioPause={() => player.setIsPlaying(false)}
          onAudioPlay={() => player.setIsPlaying(true)}
          onMoveSentence={player.moveSentence}
          onPlayFrom={player.playFrom}
          onPrefetchChapter={player.prefetchChapter}
          onPrefetchSentences={player.prefetchSentences}
          onRefresh={books.refresh}
          onTogglePlayback={player.togglePlayback}
          selectedBook={selectedBook}
        />
      )}

      {books.bookPendingDelete ? (
        <DeleteBookDialog
          book={books.bookPendingDelete}
          deletingBookId={books.deletingBookId}
          onCancel={() => books.setBookPendingDelete(null)}
          onConfirm={handleDelete}
        />
      ) : null}
    </main>
  );
}
