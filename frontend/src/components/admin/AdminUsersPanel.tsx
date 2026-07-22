import { BookOpen, Loader2, ShieldCheck, ShieldOff, UserCheck, UserX } from "lucide-react";

import type {
  UserRoleFilter,
  UserStatusFilter,
  useAdminUsers
} from "../../hooks/useAdminUsers";
import { formatDateTime, reviewStatusLabel } from "../../review";

type Props = {
  controller: ReturnType<typeof useAdminUsers>;
  currentUserId: string;
  onUpdate: (userId: string, changes: { is_admin?: boolean; is_active?: boolean }) => void;
};

export function AdminUsersPanel({ controller, currentUserId, onUpdate }: Props) {
  return (
    <section className="admin-view" data-testid="admin-user-management">
      <div className="admin-section-heading"><div><p className="eyebrow">账号与权限</p><h3>用户管理</h3></div><span>{controller.total}</span></div>
      <div className="user-filters">
        <input data-testid="user-search" onChange={(event) => controller.setQuery(event.target.value)} placeholder="搜索用户名或显示名" value={controller.query} />
        <select aria-label="账号状态" onChange={(event) => controller.setStatusFilter(event.target.value as UserStatusFilter)} value={controller.statusFilter}><option value="all">全部状态</option><option value="active">已启用</option><option value="disabled">已停用</option></select>
        <select aria-label="用户角色" onChange={(event) => controller.setRoleFilter(event.target.value as UserRoleFilter)} value={controller.roleFilter}><option value="all">全部角色</option><option value="admin">管理员</option><option value="user">普通用户</option></select>
      </div>
      {controller.isLoading ? <div className="empty-state"><Loader2 className="spin" size={16} /><span>加载用户列表</span></div> : null}
      {!controller.isLoading && controller.users.length === 0 ? <p className="review-queue-empty">没有符合条件的用户。</p> : null}
      <div className="user-list">
        {controller.users.map((user) => {
          const isCurrentUser = user.id === currentUserId;
          const isUpdating = controller.updatingUserId === user.id;
          const uploads = controller.uploadsByUserId[user.id] ?? [];
          return (
            <article className="user-row" data-testid="admin-user-row" key={user.id}>
              <div className="user-main"><strong>{user.display_name}</strong><span>@{user.username} · 注册于 {formatDateTime(user.created_at)}</span></div>
              <div className="user-badges"><span className={`status ${user.is_active ? "done" : "failed"}`}>{user.is_active ? "已启用" : "已停用"}</span>{user.is_admin ? <span className="role-badge">管理员</span> : <span className="role-badge neutral">普通用户</span>}</div>
              <div className="user-actions">
                <button aria-label="查看上传记录" onClick={() => void controller.toggleUploads(user.id)} title={`查看上传记录（${user.uploaded_book_count}）`} type="button"><BookOpen size={16} /></button>
                <button aria-label={user.is_admin ? "撤销管理员" : "设为管理员"} disabled={isCurrentUser || isUpdating} onClick={() => onUpdate(user.id, { is_admin: !user.is_admin })} title={isCurrentUser ? "不能修改当前登录账号" : user.is_admin ? "撤销管理员" : "设为管理员"} type="button">{user.is_admin ? <ShieldOff size={16} /> : <ShieldCheck size={16} />}</button>
                <button aria-label={user.is_active ? "停用账号" : "启用账号"} disabled={isCurrentUser || isUpdating} onClick={() => onUpdate(user.id, { is_active: !user.is_active })} title={isCurrentUser ? "不能修改当前登录账号" : user.is_active ? "停用账号" : "启用账号"} type="button">{isUpdating ? <Loader2 className="spin" size={16} /> : user.is_active ? <UserX size={16} /> : <UserCheck size={16} />}</button>
              </div>
              {controller.expandedUserId === user.id ? (
                <div className="user-uploads" data-testid="user-upload-history">
                  {controller.loadingUploadsUserId === user.id ? <div className="empty-state"><Loader2 className="spin" size={14} /><span>加载上传记录</span></div> : null}
                  {controller.loadingUploadsUserId !== user.id && uploads.length === 0 ? <p>该用户尚未上传书籍。</p> : null}
                  {uploads.map((book) => <div className="user-upload-row" key={book.id}><strong>{book.title}</strong><span>{reviewStatusLabel(book.review_status)}</span><time>{formatDateTime(book.created_at)}</time></div>)}
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
      <div className="review-pagination"><button disabled={controller.page <= 1} onClick={() => controller.setPage(Math.max(1, controller.page - 1))} type="button">上一页</button><span>{controller.page} / {controller.pageCount}</span><button disabled={controller.page >= controller.pageCount} onClick={() => controller.setPage(Math.min(controller.pageCount, controller.page + 1))} type="button">下一页</button></div>
    </section>
  );
}
