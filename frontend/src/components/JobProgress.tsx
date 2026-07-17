import type { JobSummary } from "../types";

export function JobProgress({ job }: { job: JobSummary | null }) {
  if (!job) return null;
  const finished = job.status === "completed" || job.status === "completed_with_document_failures";
  const failed = job.status === "failed" || job.status === "interrupted";
  return (
    <div className={`job-status ${finished ? "is-done" : failed ? "is-failed" : "is-running"}`} role="status">
      <span className="status-dot" aria-hidden="true" />
      <div>
        <strong>{finished ? "校验完成" : failed ? "校验未完成" : "正在校验"}</strong>
        <small>{failed ? job.error ?? "请检查任务详情" : `${job.processed_documents}/${job.total_documents} 个文档 · ${job.phase}`}</small>
      </div>
    </div>
  );
}
