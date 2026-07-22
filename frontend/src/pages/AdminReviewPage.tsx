import { Activity, BookCheck, History, ListTodo, Users } from "lucide-react";
import { useState } from "react";

import { AdminAuditPanel } from "../components/admin/AdminAuditPanel";
import { AdminBooksPanel } from "../components/admin/AdminBooksPanel";
import { AdminJobsPanel } from "../components/admin/AdminJobsPanel";
import { AdminSystemPanel } from "../components/admin/AdminSystemPanel";
import { AdminUsersPanel } from "../components/admin/AdminUsersPanel";
import type { useAdminAudit } from "../hooks/useAdminAudit";
import type { useAdminJobs } from "../hooks/useAdminJobs";
import type { useAdminReview } from "../hooks/useAdminReview";
import type { useAdminSystem } from "../hooks/useAdminSystem";
import type { useAdminUsers } from "../hooks/useAdminUsers";
import type { ReviewStatus } from "../review";
import type { BookSummary, User } from "../types";

export type AdminTab = "system" | "books" | "users" | "jobs" | "audit";

type AdminReviewPageProps = {
  audit: ReturnType<typeof useAdminAudit>;
  currentUser: User;
  error: string | null;
  jobs: ReturnType<typeof useAdminJobs>;
  review: ReturnType<typeof useAdminReview>;
  system: ReturnType<typeof useAdminSystem>;
  users: ReturnType<typeof useAdminUsers>;
  onBatchReview: (status: "approved" | "rejected") => Promise<void>;
  onReview: (book: BookSummary, status: ReviewStatus, note?: string) => void;
  onSelectBook: (book: BookSummary) => void;
};

const TABS: { value: AdminTab; label: string; icon: typeof Activity }[] = [
  { value: "system", label: "系统状态", icon: Activity },
  { value: "books", label: "书籍审核", icon: BookCheck },
  { value: "users", label: "用户管理", icon: Users },
  { value: "jobs", label: "任务队列", icon: ListTodo },
  { value: "audit", label: "操作审计", icon: History }
];

export function AdminReviewPage(props: AdminReviewPageProps) {
  const { audit, currentUser, error, jobs, review, system, users } = props;
  const [activeTab, setActiveTab] = useState<AdminTab>("system");

  async function refreshActiveTab() {
    if (activeTab === "system") await system.refresh();
    if (activeTab === "books") await review.refresh();
    if (activeTab === "users") await users.refresh();
    if (activeTab === "jobs") await jobs.refresh();
    if (activeTab === "audit") await audit.refresh();
  }

  async function updateUser(
    userId: string,
    changes: { is_admin?: boolean; is_active?: boolean }
  ) {
    const updated = await users.update(userId, changes);
    if (updated) {
      await Promise.all([audit.refresh(false), system.refresh(false)]);
    }
  }

  return (
    <section className="admin-panel" data-testid="admin-page">
      <header className="reader-header admin-header">
        <div>
          <p className="eyebrow">管理员后台</p>
          <h2>{TABS.find((tab) => tab.value === activeTab)?.label}</h2>
        </div>
        <button className="ghost-button" onClick={() => void refreshActiveTab()} type="button">
          刷新
        </button>
      </header>
      {error ? <div className="error-banner">{error}</div> : null}
      <nav aria-label="后台功能" className="admin-tabs" data-testid="admin-tabs">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              className={activeTab === tab.value ? "active" : ""}
              data-testid={`admin-tab-${tab.value}`}
              key={tab.value}
              onClick={() => setActiveTab(tab.value)}
              type="button"
            >
              <Icon size={16} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>
      <div className="admin-content">
        {activeTab === "system" ? <AdminSystemPanel controller={system} /> : null}
        {activeTab === "books" ? (
          <AdminBooksPanel
            controller={review}
            onBatchReview={props.onBatchReview}
            onReview={props.onReview}
            onSelectBook={props.onSelectBook}
          />
        ) : null}
        {activeTab === "users" ? (
          <AdminUsersPanel
            controller={users}
            currentUserId={currentUser.id}
            onUpdate={updateUser}
          />
        ) : null}
        {activeTab === "jobs" ? <AdminJobsPanel controller={jobs} /> : null}
        {activeTab === "audit" ? <AdminAuditPanel controller={audit} /> : null}
      </div>
    </section>
  );
}
