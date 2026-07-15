import { BookOpen, Loader2, LogOut, Trash2, Upload, UserRound } from "lucide-react";

import { reviewStatusLabel, type ReviewStatus } from "../review";
import type { BookSummary, User } from "../types";

type AppSidebarProps = {
  books: BookSummary[];
  currentUser: User;
  deletingBookId: string | null;
  isAdminPage: boolean;
  isLoadingBooks: boolean;
  reviewingBookId: string | null;
  selectedBookId: string | null;
  onDeleteBook: (book: BookSummary) => void;
  onLogout: () => void;
  onNavigate: (path: string) => void;
  onReviewBook: (book: BookSummary, status: ReviewStatus) => void;
  onSelectBook: (book: BookSummary) => void;
  onUpload: (file: File | undefined) => void;
};

export function AppSidebar(props: AppSidebarProps) {
  const {
    books,
    currentUser,
    deletingBookId,
    isAdminPage,
    isLoadingBooks,
    reviewingBookId,
    selectedBookId,
    onDeleteBook,
    onLogout,
    onNavigate,
    onReviewBook,
    onSelectBook,
    onUpload
  } = props;

  function canDeleteBook(book: BookSummary) {
    return (
      currentUser.is_admin ||
      (book.uploader_id === currentUser.id && book.review_status !== "approved")
    );
  }

  return (
    <aside className="library-panel" data-testid="library-panel">
      <div className="brand-row">
        <BookOpen size={22} />
        <h1>Listen Book</h1>
      </div>

      <section className="account-card" data-testid="account-card">
        <div className="account-current">
          <UserRound size={18} />
          <div>
            <span>{currentUser.display_name}</span>
            <small>@{currentUser.username}</small>
          </div>
          <button
            aria-label="退出登录"
            data-testid="auth-logout"
            onClick={onLogout}
            title="退出登录"
            type="button"
          >
            <LogOut size={15} />
          </button>
        </div>
      </section>

      <nav className="side-nav" aria-label="主导航">
        <button
          className={!isAdminPage ? "active" : ""}
          data-testid="nav-app"
          onClick={() => onNavigate("/app")}
          type="button"
        >
          书库
        </button>
        {currentUser.is_admin ? (
          <button
            className={isAdminPage ? "active" : ""}
            data-testid="nav-admin"
            onClick={() => onNavigate("/admin")}
            type="button"
          >
            管理员后台
          </button>
        ) : null}
      </nav>

      {!isAdminPage ? (
        <>
          <label className="upload-button" data-testid="upload-book">
            <Upload size={18} />
            <span>上传书籍</span>
            <input
              accept=".txt,.epub"
              type="file"
              onChange={(event) => onUpload(event.target.files?.[0])}
            />
          </label>
          <p className="upload-hint">当前支持 TXT / EPUB；PDF 暂不接入。</p>
          <div className="book-list" data-testid="book-list">
            {isLoadingBooks ? (
              <div className="empty-state">
                <Loader2 className="spin" size={18} />
                <span>加载中</span>
              </div>
            ) : (
              books.map((book) => (
                <div
                  className={book.id === selectedBookId ? "book-row active" : "book-row"}
                  data-testid="book-row"
                  key={book.id}
                >
                  <button className="book-select-button" onClick={() => onSelectBook(book)} type="button">
                    <span className="book-title">{book.title}</span>
                    <span className="book-badges">
                      <span className={`status ${book.status}`}>{book.status}</span>
                      {book.review_status !== "approved" ? (
                        <span className={`review-status ${book.review_status}`}>
                          {reviewStatusLabel(book.review_status)}
                        </span>
                      ) : null}
                    </span>
                  </button>
                  {currentUser.is_admin && book.review_status !== "approved" ? (
                    <div className="book-review-actions">
                      <button
                        disabled={reviewingBookId === book.id}
                        onClick={() => onReviewBook(book, "approved")}
                        type="button"
                      >
                        批准
                      </button>
                      {book.review_status === "pending_review" ? (
                        <button
                          disabled={reviewingBookId === book.id}
                          onClick={() => onReviewBook(book, "rejected")}
                          type="button"
                        >
                          拒绝
                        </button>
                      ) : null}
                    </div>
                  ) : null}
                  {canDeleteBook(book) ? (
                    <button
                      aria-label={`删除 ${book.title}`}
                      className="book-delete-button"
                      disabled={deletingBookId === book.id}
                      onClick={() => onDeleteBook(book)}
                      title="删除书籍"
                      type="button"
                    >
                      {deletingBookId === book.id ? (
                        <Loader2 className="spin" size={15} />
                      ) : (
                        <Trash2 size={15} />
                      )}
                    </button>
                  ) : null}
                </div>
              ))
            )}
          </div>
        </>
      ) : null}
    </aside>
  );
}
