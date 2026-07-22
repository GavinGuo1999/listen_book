import { Loader2 } from "lucide-react";

import type { useAdminAudit } from "../../hooks/useAdminAudit";
import { formatDateTime } from "../../review";

type Props = { controller: ReturnType<typeof useAdminAudit> };

export function AdminAuditPanel({ controller }: Props) {
  return (
    <section className="admin-view" data-testid="admin-audit-events">
      <div className="admin-section-heading"><div><p className="eyebrow">权限审计</p><h3>管理员操作记录</h3></div><span>{controller.events.length}</span></div>
      {controller.isLoading ? <div className="empty-state"><Loader2 className="spin" size={16} /><span>加载审计记录</span></div> : null}
      {!controller.isLoading && controller.events.length === 0 ? <p className="review-queue-empty">暂无管理员操作记录。</p> : null}
      <div className="audit-list">
        {controller.events.map((event) => (
          <article className="audit-row" key={event.id}>
            <span className="audit-dot" />
            <div><strong>{actionLabel(event.action)}</strong><span>{event.actor_username ?? "未知管理员"} → {event.target_username ?? "未知用户"}</span></div>
            <time>{formatDateTime(event.created_at)}</time>
          </article>
        ))}
      </div>
    </section>
  );
}

function actionLabel(action: string) {
  return ({ user_enabled: "启用账号", user_disabled: "停用账号", admin_granted: "授予管理员", admin_revoked: "撤销管理员" } as Record<string, string>)[action] ?? action;
}
