import { Loader2 } from "lucide-react";

import type { JobFilter, useAdminJobs } from "../../hooks/useAdminJobs";
import { formatDateTime } from "../../review";

type Props = { controller: ReturnType<typeof useAdminJobs> };
const FILTERS: [JobFilter, string][] = [["failed", "失败"], ["pending", "等待中"], ["running", "运行中"], ["done", "已完成"], ["all", "全部"]];

export function AdminJobsPanel({ controller }: Props) {
  return (
    <section className="admin-view" data-testid="admin-job-queue">
      <div className="admin-section-heading"><div><p className="eyebrow">后台任务</p><h3>队列状态与失败重试</h3></div><span>{controller.jobs.length}</span></div>
      <div className="review-filter-tabs five" data-testid="job-filter-tabs">
        {FILTERS.map(([value, label]) => <button className={controller.filter === value ? "active" : ""} data-testid={`job-filter-${value}`} key={value} onClick={() => controller.changeFilter(value)} type="button">{label}</button>)}
      </div>
      {controller.isLoading ? <div className="empty-state"><Loader2 className="spin" size={16} /><span>加载任务列表</span></div> : null}
      {!controller.isLoading && controller.jobs.length === 0 ? <p className="review-queue-empty">当前筛选下没有任务。</p> : null}
      <div className="job-list">
        {controller.jobs.map((job) => (
          <article className="job-row" data-testid="admin-job-row" key={job.id}>
            <div className="job-row-main"><strong>{jobTypeLabel(job.job_type)}</strong><span className={`status ${job.status}`}>{jobStatusLabel(job.status)}</span></div>
            <div className="job-row-meta"><span>目标 {job.target_id?.slice(0, 8) ?? "-"}</span><span>尝试 {job.attempts}/{job.max_attempts}</span><span>{formatDateTime(job.created_at)}</span></div>
            {job.error_message ? <p className="job-error">{job.error_message}</p> : null}
            {job.status === "failed" ? <button data-testid="job-retry" disabled={controller.retryingJobId === job.id} onClick={() => controller.retry(job.id)} type="button">{controller.retryingJobId === job.id ? <Loader2 className="spin" size={14} /> : null}重试</button> : null}
          </article>
        ))}
      </div>
    </section>
  );
}

function jobTypeLabel(type: string) {
  if (type === "parse_book") return "解析书籍";
  if (type === "generate_audio") return "生成句子音频";
  if (type === "prefetch_chapter_audio") return "预生成章节音频";
  return type;
}
function jobStatusLabel(status: string) {
  return ({ pending: "等待中", running: "运行中", done: "已完成", failed: "失败" } as Record<string, string>)[status] ?? status;
}
