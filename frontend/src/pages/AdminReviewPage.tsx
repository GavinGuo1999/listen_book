import { Loader2 } from "lucide-react";

import {
  formatDateTime,
  reviewerLabel,
  reviewStatusLabel,
  type ReviewQueueFilter,
  type ReviewStatus
} from "../review";
import type { AdminBookReviewSummary, BookSummary } from "../types";

type AdminReviewPageProps = {
  error: string | null;
  filter: ReviewQueueFilter;
  filteredCount: number;
  isLoading: boolean;
  notesByBookId: Record<string, string>;
  page: number;
  pageCount: number;
  pagedBooks: AdminBookReviewSummary[];
  reviewingBookId: string | null;
  onFilterChange: (filter: ReviewQueueFilter) => void;
  onNoteChange: (bookId: string, note: string) => void;
  onPageChange: (page: number) => void;
  onRefresh: () => void;
  onReview: (book: BookSummary, status: ReviewStatus, note?: string) => void;
  onSelectBook: (book: BookSummary) => void;
};

const FILTERS: [ReviewQueueFilter, string][] = [
  ["pending", "待审批"],
  ["failed", "解析失败"],
  ["rejected", "已拒绝"],
  ["all", "全部"]
];

export function AdminReviewPage(props: AdminReviewPageProps) {
  const {
    error,
    filter,
    filteredCount,
    isLoading,
    notesByBookId,
    page,
    pageCount,
    pagedBooks,
    reviewingBookId,
    onFilterChange,
    onNoteChange,
    onPageChange,
    onRefresh,
    onReview,
    onSelectBook
  } = props;
  return (
    <section className="admin-panel" data-testid="admin-page">
      <header className="reader-header">
        <div>
          <p className="eyebrow">管理员后台</p>
          <h2>审批中心</h2>
        </div>
        <button className="ghost-button" onClick={onRefresh} type="button">刷新</button>
      </header>
      {error ? <div className="error-banner">{error}</div> : null}
      <div className="admin-content">
        <section className="review-queue-card" data-testid="admin-review-queue">
          <div className="review-queue-header">
            <div><p className="eyebrow">书籍审核</p><h2>待处理与历史记录</h2></div>
            <span>{filteredCount}</span>
          </div>
          <div className="review-filter-tabs" data-testid="review-filter-tabs">
            {FILTERS.map(([value, label]) => (
              <button
                className={filter === value ? "active" : ""}
                data-testid={`review-filter-${value}`}
                key={value}
                onClick={() => onFilterChange(value)}
                type="button"
              >
                {label}
              </button>
            ))}
          </div>
          {isLoading ? (
            <div className="empty-state"><Loader2 className="spin" size={16} /><span>加载审批列表</span></div>
          ) : filteredCount === 0 ? (
            <p className="review-queue-empty">当前筛选下没有书籍。</p>
          ) : (
            <div className="review-queue-list">
              {pagedBooks.map((book) => (
                <article className="review-queue-item" data-testid="review-queue-item" key={book.id}>
                  <button className="review-queue-title" onClick={() => onSelectBook(book)} type="button">
                    <span>{book.title}</span><span className={`status ${book.status}`}>{book.status}</span>
                  </button>
                  <dl className="review-book-meta">
                    <div><dt>上传者</dt><dd>{reviewerLabel(book)}</dd></div>
                    <div><dt>上传时间</dt><dd>{formatDateTime(book.created_at)}</dd></div>
                    <div><dt>审核状态</dt><dd>{reviewStatusLabel(book.review_status)}</dd></div>
                  </dl>
                  {book.review_note ? <p className="review-note-existing">当前备注：{book.review_note}</p> : null}
                  {book.review_history.length > 0 ? (
                    <details className="review-history" data-testid="review-history">
                      <summary>审批历史 {book.review_history.length}</summary>
                      <ol>
                        {book.review_history.map((event) => (
                          <li key={event.id}>
                            <span>{formatDateTime(event.created_at)} · {event.reviewer_display_name ?? event.reviewer_username ?? "未知管理员"}</span>
                            <strong>{reviewStatusLabel(event.from_review_status)} → {reviewStatusLabel(event.to_review_status)}</strong>
                            {event.note ? <em>备注：{event.note}</em> : null}
                          </li>
                        ))}
                      </ol>
                    </details>
                  ) : <p className="review-history-empty">暂无审批历史。</p>}
                  <textarea
                    aria-label={`拒绝《${book.title}》的备注`}
                    data-testid="review-note-input"
                    disabled={reviewingBookId === book.id}
                    onChange={(event) => onNoteChange(book.id, event.target.value)}
                    placeholder="拒绝备注（可选）"
                    value={notesByBookId[book.id] ?? ""}
                  />
                  <div className="review-queue-actions">
                    {book.review_status !== "approved" ? (
                      <button data-testid="review-approve" disabled={reviewingBookId === book.id} onClick={() => onReview(book, "approved")} type="button">批准发布</button>
                    ) : null}
                    {book.review_status !== "rejected" ? (
                      <button data-testid="review-reject" disabled={reviewingBookId === book.id} onClick={() => onReview(book, "rejected", notesByBookId[book.id])} type="button">拒绝</button>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          )}
          <div className="review-pagination">
            <button disabled={page <= 1} onClick={() => onPageChange(Math.max(1, page - 1))} type="button">上一页</button>
            <span>{page} / {pageCount}</span>
            <button disabled={page >= pageCount} onClick={() => onPageChange(Math.min(pageCount, page + 1))} type="button">下一页</button>
          </div>
        </section>
      </div>
    </section>
  );
}
