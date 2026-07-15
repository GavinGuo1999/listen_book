import type { Dispatch, SetStateAction } from "react";
import { useEffect, useState } from "react";

import { fetchAdminJobs, retryAdminJob } from "../api";
import type { AdminJob } from "../types";

export type JobFilter = "all" | "pending" | "running" | "failed" | "done";
type SetError = Dispatch<SetStateAction<string | null>>;

export function useAdminJobs(isAdmin: boolean, setError: SetError) {
  const [jobs, setJobs] = useState<AdminJob[]>([]);
  const [filter, setFilter] = useState<JobFilter>("failed");
  const [isLoading, setIsLoading] = useState(false);
  const [retryingJobId, setRetryingJobId] = useState<string | null>(null);

  async function refresh(showLoading = true, nextFilter = filter) {
    if (!isAdmin) return [];
    if (showLoading) setIsLoading(true);
    try {
      const nextJobs = await fetchAdminJobs(nextFilter);
      setJobs(nextJobs);
      return nextJobs;
    } catch (error) {
      setError(error instanceof Error ? error.message : "加载任务列表失败");
      return [];
    } finally {
      if (showLoading) setIsLoading(false);
    }
  }

  useEffect(() => {
    if (isAdmin) void refresh();
    else setJobs([]);
  }, [isAdmin]);

  async function changeFilter(nextFilter: JobFilter) {
    setFilter(nextFilter);
    await refresh(true, nextFilter);
  }

  async function retry(jobId: string) {
    setRetryingJobId(jobId);
    setError(null);
    try {
      await retryAdminJob(jobId);
      await refresh(false);
    } catch (error) {
      setError(error instanceof Error ? error.message : "任务重试失败");
    } finally {
      setRetryingJobId(null);
    }
  }

  return { changeFilter, filter, isLoading, jobs, refresh, retry, retryingJobId };
}
