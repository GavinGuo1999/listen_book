import type { Dispatch, SetStateAction } from "react";
import { useEffect, useMemo, useState } from "react";

import { fetchAdminUserBooks, fetchAdminUsers, updateAdminUser } from "../api";
import type { AdminBookReviewSummary, AdminUser } from "../types";

export type UserStatusFilter = "all" | "active" | "disabled";
export type UserRoleFilter = "all" | "admin" | "user";
type SetError = Dispatch<SetStateAction<string | null>>;

export function useAdminUsers(isAdmin: boolean, setError: SetError) {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<UserStatusFilter>("all");
  const [roleFilter, setRoleFilter] = useState<UserRoleFilter>("all");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isLoading, setIsLoading] = useState(false);
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null);
  const [expandedUserId, setExpandedUserId] = useState<string | null>(null);
  const [uploadsByUserId, setUploadsByUserId] = useState<
    Record<string, AdminBookReviewSummary[]>
  >({});
  const [loadingUploadsUserId, setLoadingUploadsUserId] = useState<string | null>(null);

  const pageCount = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [total, pageSize]);

  async function refresh(showLoading = true) {
    if (!isAdmin) return [];
    if (showLoading) setIsLoading(true);
    try {
      const result = await fetchAdminUsers({
        query,
        status: statusFilter,
        role: roleFilter,
        page,
        pageSize
      });
      setUsers(result.items);
      setTotal(result.total);
      setPageSize(result.page_size);
      return result.items;
    } catch (error) {
      setError(error instanceof Error ? error.message : "加载用户列表失败");
      return [];
    } finally {
      if (showLoading) setIsLoading(false);
    }
  }

  useEffect(() => setPage(1), [query, statusFilter, roleFilter]);
  useEffect(() => setPage((current) => Math.min(current, pageCount)), [pageCount]);
  useEffect(() => {
    if (!isAdmin) {
      setUsers([]);
      return;
    }
    const timer = window.setTimeout(() => void refresh(), 250);
    return () => window.clearTimeout(timer);
  }, [isAdmin, query, statusFilter, roleFilter, page]);

  async function update(userId: string, changes: { is_admin?: boolean; is_active?: boolean }) {
    setUpdatingUserId(userId);
    setError(null);
    try {
      await updateAdminUser(userId, changes);
      await refresh(false);
      return true;
    } catch (error) {
      setError(error instanceof Error ? error.message : "更新用户失败");
      return false;
    } finally {
      setUpdatingUserId(null);
    }
  }

  async function toggleUploads(userId: string) {
    if (expandedUserId === userId) {
      setExpandedUserId(null);
      return;
    }
    setExpandedUserId(userId);
    if (uploadsByUserId[userId]) return;
    setLoadingUploadsUserId(userId);
    try {
      const uploads = await fetchAdminUserBooks(userId);
      setUploadsByUserId((current) => ({ ...current, [userId]: uploads }));
    } catch (error) {
      setError(error instanceof Error ? error.message : "加载用户上传记录失败");
    } finally {
      setLoadingUploadsUserId(null);
    }
  }

  return {
    expandedUserId,
    isLoading,
    loadingUploadsUserId,
    page,
    pageCount,
    query,
    refresh,
    roleFilter,
    setPage,
    setQuery,
    setRoleFilter,
    setStatusFilter,
    statusFilter,
    toggleUploads,
    total,
    update,
    updatingUserId,
    uploadsByUserId,
    users
  };
}
