import { useEffect, useState } from "react";

import { createJob, getJob, listTermLibraries } from "../api/client";
import { FilePicker } from "../components/FilePicker";
import { JobProgress } from "../components/JobProgress";
import type { JobSummary, TermLibrary } from "../types";

export function CheckPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [libraries, setLibraries] = useState<TermLibrary[]>([]);
  const [selectedLibraries, setSelectedLibraries] = useState<string[]>([]);
  const [mode, setMode] = useState<"full" | "rules_only">("full");
  const [job, setJob] = useState<JobSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTermLibraries().then(setLibraries).catch((reason: Error) => setError(reason.message));
  }, []);

  useEffect(() => {
    if (!job || job.status === "completed" || job.status === "completed_with_document_failures" || job.status === "failed" || job.status === "interrupted") return;
    const timer = window.setTimeout(() => getJob(job.job_id).then(setJob).catch((reason: Error) => setError(reason.message)), 1000);
    return () => window.clearTimeout(timer);
  }, [job]);

  async function startCheck() {
    setError(null);
    try {
      const created = await createJob(files, selectedLibraries, mode);
      setJob({ job_id: created.job_id, status: created.status, processed_documents: 0, total_documents: files.length, phase: "queued" });
      const current = await getJob(created.job_id);
      setJob(current);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "任务创建失败");
    }
  }

  return (
    <main className="check-page">
      <section className="hero-panel">
        <p className="kicker">TYPOfix / 中文文档校验</p>
        <h1>把论文里的小毛刺，留在交稿前。</h1>
        <p className="hero-copy">上传 DOCX，先看真正值得处理的问题。术语豁免会被保留，也会和待处理项清楚分开。</p>
      </section>
      <section className="workspace-card">
        <div className="section-heading"><div><p className="eyebrow">01 · 选择材料</p><h2>从一份文档开始</h2></div><span className="quiet-label">仅在本机处理</span></div>
        <FilePicker files={files} onChange={setFiles} />
        <div className="controls-row">
          <fieldset><legend>校验模式</legend><label><input type="radio" checked={mode === "full"} onChange={() => setMode("full")} /> 模型 + 规则</label><label><input type="radio" checked={mode === "rules_only"} onChange={() => setMode("rules_only")} /> 仅规则</label></fieldset>
          <fieldset><legend>术语库</legend><div className="library-list">{libraries.map((library) => <label key={library.name}><input aria-label={library.name} type="checkbox" checked={selectedLibraries.includes(library.name)} onChange={(event) => setSelectedLibraries((current) => event.target.checked ? [...current, library.name] : current.filter((name) => name !== library.name))} /> {library.name}</label>)}</div></fieldset>
        </div>
        <button className="primary-button" disabled={!files.length} onClick={startCheck}>开始校验 <span aria-hidden="true">↗</span></button>
        <JobProgress job={job} />
        {error && <p className="error-copy" role="alert">{error}</p>}
      </section>
    </main>
  );
}
