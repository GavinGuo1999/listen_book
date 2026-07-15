import { Loader2 } from "lucide-react";

import {
  formatDateTime,
  reviewerLabel,
  reviewStatusLabel,
  type ReviewQueueFilter,
  type ReviewStatus
} from "../review";
import type { AdminBookReviewSummary, BookSummary } from "../types";
import type { AdminJob } from "../types";
import type { JobFilter } from "../hooks/useAdminJobs";

type AdminReviewPageProps = {
  error: string | null;
  filter: ReviewQueueFilter;
  filteredCount: number;
  isLoading: boolean;
  jobFilter: JobFilter;
  jobs: AdminJob[];
  jobsLoading: boolean;
  notesByBookId: Record<string, string>;
  page: number;
  pageCount: number;
  pagedBooks: AdminBookReviewSummary[];
  reviewingBookId: string | null;
  retryingJobId: string | null;
  onFilterChange: (filter: ReviewQueueFilter) => void;
  onJobFilterChange: (filter: JobFilter) => void;
  onJobsRefresh: () => void;
  onNoteChange: (bookId: string, note: string) => void;
  onPageChange: (page: number) => void;
  onRefresh: () => void;
  onReview: (book: BookSummary, status: ReviewStatus, note?: string) => void;
  onRetryJob: (jobId: string) => void;
  onSelectBook: (book: BookSummary) => void;
};

const FILTERS: [ReviewQueueFilter, string][] = [
  ["pending", "待审批"],
  ["failed", "解析失败"],
  ["rejected", "已拒绝"],
  ["all", "全部"]
];

const JOB_FILTERS: [JobFilter, string][] = [
  ["failed", "失败"],
  ["pending", "等待中"],
  ["running", "运行中"],
  ["done", "已完成"],
  ["all", "全部"]
];

export function AdminReviewPage(props: AdminReviewPageProps) {
  const {
    error,
    filter,
    filteredCount,
    isLoading,
    jobFilter,
    jobs,
    jobsLoading,
    notesByBookId,
    page,
    pageCount,
    pagedBooks,
    reviewingBookId,
    retryingJobId,
    onFilterChange,
    onJobFilterChange,
    onJobsRefresh,
    onNoteChange,
    onPageChange,
    onRefresh,
    onReview,
    onRetryJob,
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
        <section className="review-queue-card" data-testid="admin-job-queue">
          <div className="review-queue-header">
            <div><p className="eyebrow">后台任务</p><h2>队列状态与失败重试</h2></div>
            <button className="ghost-button" onClick={onJobsRefresh} type="button">刷新</button>
          </div>
          <div className="review-filter-tabs" data-testid="job-filter-tabs">
            {JOB_FILTERS.map(([value, label]) => (
              <button
                className={jobFilter === value ? "active" : ""}
                data-testid={`job-filter-${value}`}
                key={value}
                onClick={() => onJobFilterChange(value)}
                type="button"
              >
                {label}
              </button>
            ))}
          </div>
          {jobsLoading ? (
            <div className="empty-state"><Loader2 className="spin" size={16} /><span>加载任务列表</span></div>
          ) : jobs.length === 0 ? (
            <p className="review-queue-empty">当前筛选下没有任务。</p>
          ) : (
            <div className="job-list">
              {jobs.map((job) => (
                <article className="job-row" data-testid="admin-job-row" key={job.id}>
                  <div className="job-row-main">
                    <strong>{jobTypeLabel(job.job_type)}</strong>
                    <span className={`status ${job.status}`}>{jobStatusLabel(job.status)}</span>
                  </div>
                  <div className="job-row-meta">
                    <span>目标 {job.target_id?.slice(0, 8) ?? "-"}</span>
                    <span>尝试 {job.attempts}/{job.max_attempts}</span>
                    <span>{formatDateTime(job.created_at)}</span>
                  </div>
                  {job.error_message ? <p className="job-error">{job.error_message}</p> : null}
                  {job.status === "failed" ? (
                    <button
                      data-testid="job-retry"
                      disabled={retryingJobId === job.id}
                      onClick={() => onRetryJob(job.id)}
                      type="button"
                    >
                      {retryingJobId === job.id ? <Loader2 className="spin" size={14} /> : null}
                      重试
                    </button>
                  ) : null}
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </section>
  );
}

function jobTypeLabel(jobType: string) {
  if (jobType === "parse_book") return "解析书籍";
  if (jobType === "generate_audio") return "生成句子音频";
  if (jobType === "prefetch_chapter_audio") return "预生成章节音频";
  return jobType;
}

function jobStatusLabel(status: string) {
  if (status === "pending") return "等待中";
  if (status === "running") return "运行中";
  if (status === "done") return "已完成";
  if (status === "failed") return "失败";
  return status;
}
