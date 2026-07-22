import { CheckSquare, Loader2, Search, Square } from "lucide-react";

import type { useAdminReview } from "../../hooks/useAdminReview";
import {
  formatDateTime,
  reviewerLabel,
  reviewStatusLabel,
  type ReviewQueueFilter,
  type ReviewStatus
} from "../../review";
import type { BookSummary } from "../../types";

type Props = {
  controller: ReturnType<typeof useAdminReview>;
  onBatchReview: (status: "approved" | "rejected") => Promise<void>;
  onReview: (book: BookSummary, status: ReviewStatus, note?: string) => void;
  onSelectBook: (book: BookSummary) => void;
};

const FILTERS: [ReviewQueueFilter, string][] = [
  ["pending", "待审批"],
  ["failed", "解析失败"],
  ["rejected", "已拒绝"],
  ["all", "全部"]
];

export function AdminBooksPanel({ controller, onBatchReview, onReview, onSelectBook }: Props) {
  const selectablePageIds = controller.pagedBooks
    .filter((book) => book.review_status !== "approved")
    .map((book) => book.id);
  const allPageSelected = selectablePageIds.length > 0
    && selectablePageIds.every((bookId) => controller.selectedBookIds.has(bookId));

  return (
    <section className="admin-view" data-testid="admin-review-queue">
      <div className="admin-section-heading">
        <div><p className="eyebrow">书籍审核</p><h3>待处理与历史记录</h3></div>
        <span>{controller.filteredBooks.length}</span>
      </div>
      <div className="admin-toolbar">
        <label className="search-field">
          <Search size={16} />
          <input data-testid="review-search" onChange={(event) => controller.setQuery(event.target.value)} placeholder="搜索书名或上传者" value={controller.query} />
        </label>
        <button className="select-page-button" disabled={selectablePageIds.length === 0} onClick={controller.selectPageBooks} type="button">
          {allPageSelected ? <CheckSquare size={16} /> : <Square size={16} />}
          选择本页
        </button>
      </div>
      <div className="review-filter-tabs" data-testid="review-filter-tabs">
        {FILTERS.map(([value, label]) => (
          <button className={controller.filter === value ? "active" : ""} data-testid={`review-filter-${value}`} key={value} onClick={() => controller.setFilter(value)} type="button">{label}</button>
        ))}
      </div>

      {controller.selectedBookIds.size > 0 ? (
        <div className="bulk-review-bar" data-testid="bulk-review-bar">
          <strong>已选择 {controller.selectedBookIds.size} 本</strong>
          <input aria-label="批量审批备注" onChange={(event) => controller.setBatchNote(event.target.value)} placeholder="批量备注（可选）" value={controller.batchNote} />
          <button data-testid="bulk-approve" disabled={controller.isBatchReviewing} onClick={() => void onBatchReview("approved")} type="button">批量批准</button>
          <button className="reject" data-testid="bulk-reject" disabled={controller.isBatchReviewing} onClick={() => void onBatchReview("rejected")} type="button">批量拒绝</button>
        </div>
      ) : null}

      {controller.isLoading ? <div className="empty-state"><Loader2 className="spin" size={16} /><span>加载审批列表</span></div> : null}
      {!controller.isLoading && controller.filteredBooks.length === 0 ? <p className="review-queue-empty">当前筛选下没有书籍。</p> : null}
      <div className="review-queue-list">
        {controller.pagedBooks.map((book) => (
          <article className="review-queue-item admin-book-item" data-testid="review-queue-item" key={book.id}>
            <label className="row-checkbox" title={book.review_status === "approved" ? "已发布书籍无需重复批量审批" : "选择书籍"}>
              <input checked={controller.selectedBookIds.has(book.id)} disabled={book.review_status === "approved"} onChange={() => controller.toggleBookSelection(book.id)} type="checkbox" />
            </label>
            <div className="admin-book-body">
              <button className="review-queue-title" onClick={() => onSelectBook(book)} type="button"><span>{book.title}</span><span className={`status ${book.status}`}>{book.status}</span></button>
              <dl className="review-book-meta">
                <div><dt>上传者</dt><dd>{reviewerLabel(book)}</dd></div>
                <div><dt>上传时间</dt><dd>{formatDateTime(book.created_at)}</dd></div>
                <div><dt>审核状态</dt><dd>{reviewStatusLabel(book.review_status)}</dd></div>
              </dl>
              {book.review_note ? <p className="review-note-existing">当前备注：{book.review_note}</p> : null}
              {book.review_history.length > 0 ? (
                <details className="review-history" data-testid="review-history"><summary>审批历史 {book.review_history.length}</summary><ol>{book.review_history.map((event) => <li key={event.id}><span>{formatDateTime(event.created_at)} · {event.reviewer_display_name ?? event.reviewer_username ?? "未知管理员"}</span><strong>{reviewStatusLabel(event.from_review_status)} → {reviewStatusLabel(event.to_review_status)}</strong>{event.note ? <em>备注：{event.note}</em> : null}</li>)}</ol></details>
              ) : <p className="review-history-empty">暂无审批历史。</p>}
              <textarea aria-label={`拒绝《${book.title}》的备注`} data-testid="review-note-input" disabled={controller.reviewingBookId === book.id} onChange={(event) => controller.updateNote(book.id, event.target.value)} placeholder="拒绝备注（可选）" value={controller.notesByBookId[book.id] ?? ""} />
              <div className="review-queue-actions">
                {book.review_status !== "approved" ? <button data-testid="review-approve" disabled={controller.reviewingBookId === book.id} onClick={() => onReview(book, "approved")} type="button">批准发布</button> : null}
                {book.review_status !== "rejected" ? <button data-testid="review-reject" disabled={controller.reviewingBookId === book.id} onClick={() => onReview(book, "rejected", controller.notesByBookId[book.id])} type="button">拒绝</button> : null}
              </div>
            </div>
          </article>
        ))}
      </div>
      <div className="review-pagination"><button disabled={controller.page <= 1} onClick={() => controller.setPage(Math.max(1, controller.page - 1))} type="button">上一页</button><span>{controller.page} / {controller.pageCount}</span><button disabled={controller.page >= controller.pageCount} onClick={() => controller.setPage(Math.min(controller.pageCount, controller.page + 1))} type="button">下一页</button></div>
    </section>
  );
}
