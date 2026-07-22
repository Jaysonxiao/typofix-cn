import { useEffect, useState } from "react";

import { listJobs } from "../api/client";
import type { JobHistoryItem } from "../types";

const statusLabels: Record<string, string> = { queued: "排队中", running: "处理中", completed: "已完成", completed_with_document_failures: "部分失败", failed: "失败", interrupted: "已中断" };

export function HistoryPage() {
  const [jobs, setJobs] = useState<JobHistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { listJobs().then(setJobs).catch((reason: Error) => setError(reason.message)); }, []);
  return <main className="history-page"><header className="page-header"><div><p className="kicker">记录 / HISTORY</p><h1>最近校验过什么？</h1><p>报告保存在本机，随时回来继续处理。</p></div><a className="back-link" href="/">新建校验 ↗</a></header>{error && <p className="error-copy" role="alert">{error}</p>}<section className="history-list">{jobs.map((job) => <article className="history-row" key={job.job_id}><div><p className="eyebrow">{job.created_at ? new Date(job.created_at).toLocaleString("zh-CN") : "本地任务"}</p><h2>{job.input_paths.join("、")}</h2><p>{job.mode === "full" ? "模型 + 规则" : "仅规则"} · {job.selected_libraries.length ? job.selected_libraries.join("、") : "未使用术语库"}</p></div><div className="history-action"><span className={`status-chip status-${job.status}`}>{statusLabels[job.status] ?? job.status}</span>{job.status.startsWith("completed") && <a className="text-link" href={`/jobs/${job.job_id}`}>查看报告 ↗</a>}</div></article>)}{!jobs.length && !error && <p className="empty-copy">还没有校验记录。</p>}</section></main>;
}
