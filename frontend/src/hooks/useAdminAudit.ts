import type { Dispatch, SetStateAction } from "react";
import { useEffect, useState } from "react";

import { fetchAdminAuditEvents } from "../api";
import type { AdminAuditEvent } from "../types";

type SetError = Dispatch<SetStateAction<string | null>>;

export function useAdminAudit(isAdmin: boolean, setError: SetError) {
  const [events, setEvents] = useState<AdminAuditEvent[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  async function refresh(showLoading = true) {
    if (!isAdmin) return [];
    if (showLoading) setIsLoading(true);
    try {
      const nextEvents = await fetchAdminAuditEvents();
      setEvents(nextEvents);
      return nextEvents;
    } catch (error) {
      setError(error instanceof Error ? error.message : "加载操作审计失败");
      return [];
    } finally {
      if (showLoading) setIsLoading(false);
    }
  }

  useEffect(() => {
    if (isAdmin) void refresh();
    else setEvents([]);
  }, [isAdmin]);

  return { events, isLoading, refresh };
}
