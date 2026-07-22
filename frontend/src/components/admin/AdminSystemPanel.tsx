import { CheckCircle2, Loader2, Server, TriangleAlert, XCircle } from "lucide-react";

import type { useAdminSystem } from "../../hooks/useAdminSystem";
import { formatDateTime } from "../../review";

type Props = { controller: ReturnType<typeof useAdminSystem> };

export function AdminSystemPanel({ controller }: Props) {
  const { isLoading, status } = controller;
  if (isLoading && !status) {
    return <div className="empty-state large"><Loader2 className="spin" /><span>正在执行系统诊断</span></div>;
  }
  if (!status) return <p className="review-queue-empty">暂时无法读取系统状态。</p>;

  return (
    <div className="admin-view" data-testid="admin-system-status">
      <div className={`system-summary ${status.status}`}>
        {status.status === "ok" ? <CheckCircle2 size={24} /> : null}
        {status.status === "warning" ? <TriangleAlert size={24} /> : null}
        {status.status === "error" ? <XCircle size={24} /> : null}
        <div>
          <strong>{statusLabel(status.status)}</strong>
          <span>Listen Book v{status.version} · {formatDateTime(status.checked_at)}</span>
        </div>
      </div>

      <section className="admin-section">
        <div className="admin-section-heading"><div><p className="eyebrow">启动诊断</p><h3>关键依赖检查</h3></div></div>
        <div className="system-check-grid">
          {status.checks.map((check) => (
            <article className={`system-check ${check.status}`} key={check.key}>
              <StatusIcon status={check.status} />
              <div><strong>{check.label}</strong><span>{check.message}</span></div>
            </article>
          ))}
        </div>
      </section>

      <section className="admin-section">
        <div className="admin-section-heading"><div><p className="eyebrow">后台进程</p><h3>Worker 心跳</h3></div></div>
        {status.workers.length === 0 ? (
          <p className="review-queue-empty">尚未收到 Worker 心跳，请确认开发启动脚本中的 Worker 窗口正在运行。</p>
        ) : (
          <div className="worker-list">
            {status.workers.map((worker) => (
              <article className="worker-row" key={worker.worker_id}>
                <Server size={18} />
                <div><strong>{worker.hostname}</strong><span>PID {worker.process_id} · 最近心跳 {formatDateTime(worker.last_seen_at)}</span></div>
                <span className={`status ${worker.is_online ? "done" : "failed"}`}>{worker.is_online ? "在线" : "离线"}</span>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function StatusIcon({ status }: { status: "ok" | "warning" | "error" }) {
  if (status === "ok") return <CheckCircle2 size={18} />;
  if (status === "warning") return <TriangleAlert size={18} />;
  return <XCircle size={18} />;
}

function statusLabel(status: "ok" | "warning" | "error") {
  if (status === "ok") return "系统运行正常";
  if (status === "warning") return "系统可用，但有配置需要处理";
  return "系统存在阻断项";
}
