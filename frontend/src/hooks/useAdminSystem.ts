import type { Dispatch, SetStateAction } from "react";
import { useEffect, useState } from "react";

import { fetchAdminSystemStatus } from "../api";
import type { AdminSystemStatus } from "../types";

type SetError = Dispatch<SetStateAction<string | null>>;

export function useAdminSystem(isAdmin: boolean, setError: SetError) {
  const [status, setStatus] = useState<AdminSystemStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function refresh(showLoading = true) {
    if (!isAdmin) return null;
    if (showLoading) setIsLoading(true);
    try {
      const nextStatus = await fetchAdminSystemStatus();
      setStatus(nextStatus);
      return nextStatus;
    } catch (error) {
      setError(error instanceof Error ? error.message : "加载系统状态失败");
      return null;
    } finally {
      if (showLoading) setIsLoading(false);
    }
  }

  useEffect(() => {
    if (!isAdmin) {
      setStatus(null);
      return;
    }
    void refresh();
    const intervalId = window.setInterval(() => void refresh(false), 15_000);
    return () => window.clearInterval(intervalId);
  }, [isAdmin]);

  return { isLoading, refresh, status };
}
