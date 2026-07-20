import { useEffect, useState } from "react";

import { createJob, getJob, listTermLibraries, testMacBert } from "../api/client";
import { FilePicker } from "../components/FilePicker";
import { JobProgress } from "../components/JobProgress";
import type { JobSummary, MacBertRawResult, TermLibrary } from "../types";

export function CheckPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [libraries, setLibraries] = useState<TermLibrary[]>([]);
  const [selectedLibraries, setSelectedLibraries] = useState<string[]>([]);
  const [mode, setMode] = useState<"full" | "rules_only">("full");
  const [job, setJob] = useState<JobSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [testText, setTestText] = useState("");
  const [testThreshold, setTestThreshold] = useState(0.7);
  const [testResult, setTestResult] = useState<MacBertRawResult | null>(null);
  const [testLoading, setTestLoading] = useState(false);
  const [testError, setTestError] = useState<string | null>(null);

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

  async function runModelTest() {
    if (!testText.trim()) return;
    setTestLoading(true);
    setTestError(null);
    try {
      setTestResult(await testMacBert(testText, testThreshold));
    } catch (reason) {
      setTestResult(null);
      setTestError(reason instanceof Error ? reason.message : "模型测试失败");
    } finally {
      setTestLoading(false);
    }
  }

  return (
    <main className="check-page">
      <section className="hero-panel">
        <div className="topline"><p className="kicker">TYPOfix / 中文文档校验</p><nav className="top-nav"><a href="/history">历史任务</a><a href="/terms">术语库</a></nav></div>
        <div className="model-test-panel">
          <div className="model-test-heading">
            <div><p className="eyebrow">MacBERT</p><h1>效果测试</h1></div>
            <span className="quiet-label">原始模型输出</span>
          </div>
          <label className="model-test-input">
            <span>测试文本</span>
            <textarea value={testText} onChange={(event) => setTestText(event.target.value)} placeholder="例如：今天新情很好" />
          </label>
          <label className="model-test-threshold">
            <span>置信度阈值</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={testThreshold}
              onChange={(event) => setTestThreshold(Number(event.target.value))}
            />
            <output>{testThreshold.toFixed(2)}</output>
          </label>
          <button className="primary-button model-test-button" disabled={!testText.trim() || testLoading} onClick={runModelTest}>
            {testLoading ? "测试中…" : "测试模型"}
          </button>
          {testError && <p className="error-copy model-test-message" role="alert">{testError}</p>}
          {testResult && <pre className="model-test-result">{JSON.stringify(testResult, null, 2)}</pre>}
        </div>
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
