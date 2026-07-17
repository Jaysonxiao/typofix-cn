import { useEffect, useMemo, useState } from "react";

import { addTermAndRematch, getReport, listTermLibraries } from "../api/client";
import { AddTermDialog } from "../components/AddTermDialog";
import { IssueFilters } from "../components/IssueFilters";
import { IssueList } from "../components/IssueList";
import { ReportSummary } from "../components/ReportSummary";
import type { AnalysisReport, Issue, IssueCategory, IssueStatus, TermLibrary } from "../types";

export function ReportPage({ jobId }: { jobId: string }) {
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [libraries, setLibraries] = useState<TermLibrary[]>([]);
  const [category, setCategory] = useState<IssueCategory | "all">("all");
  const [status, setStatus] = useState<IssueStatus | "all">("all");
  const [selection, setSelection] = useState<{ issue: Issue; term: string } | null>(null);
  const [targetLibrary, setTargetLibrary] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { Promise.all([getReport(jobId), listTermLibraries()]).then(([nextReport, nextLibraries]) => { setReport(nextReport); setLibraries(nextLibraries); setTargetLibrary(nextLibraries[0]?.name ?? ""); }).catch((reason: Error) => setError(reason.message)); }, [jobId]);

  const filtered = useMemo(() => report?.issues.filter((issue) => (category === "all" || issue.category === category) && (status === "all" || issue.status === status)) ?? [], [report, category, status]);

  async function confirmTerm() {
    if (!selection || !targetLibrary) return;
    try { setReport(await addTermAndRematch(jobId, targetLibrary, selection.term)); setSelection(null); } catch (reason) { setError(reason instanceof Error ? reason.message : "术语添加失败"); }
  }

  if (error) return <main className="report-page"><p className="error-copy" role="alert">{error}</p></main>;
  if (!report) return <main className="report-page"><p>正在打开报告……</p></main>;
  return <main className="report-page"><header className="report-header"><div><p className="kicker">报告 / {report.job_id}</p><h1>问题清单</h1><p>每一条判断都保留原文上下文；青色是术语豁免，朱砂色是仍待处理。</p></div><a className="download-link" href={`/api/v1/jobs/${report.job_id}/report.html`} target="_blank" rel="noreferrer">打开 HTML 报告 ↗</a></header><ReportSummary report={report} /><IssueFilters category={category} status={status} onCategoryChange={setCategory} onStatusChange={setStatus} /><IssueList issues={filtered} onSelect={(issue, term) => setSelection({ issue, term })} />{selection && <AddTermDialog term={selection.term} libraries={libraries} selected={targetLibrary} onChange={setTargetLibrary} onConfirm={confirmTerm} onCancel={() => setSelection(null)} />}</main>;
}
