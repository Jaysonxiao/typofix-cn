import type { AnalysisReport, JobCreated, JobHistoryItem, JobSummary, MacBertRawResult, TermLibrary } from "../types";

const API_ROOT = "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, init);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: { message: "请求失败" } }));
    throw new Error(payload.detail?.message ?? "请求失败");
  }
  return response.json() as Promise<T>;
}

export function listTermLibraries(): Promise<TermLibrary[]> {
  return request<TermLibrary[]>("/term-libraries");
}

export function testMacBert(text: string): Promise<MacBertRawResult> {
  return request<MacBertRawResult>("/macbert/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

export function createJob(files: File[], libraries: string[], mode: "full" | "rules_only"): Promise<JobCreated> {
  const body = new FormData();
  files.forEach((file) => {
    const relativePath = (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name;
    body.append("files", file, relativePath);
  });
  body.set("term_libraries", libraries.join(","));
  body.set("mode", mode);
  return request<JobCreated>("/jobs", { method: "POST", body });
}

export function getJob(jobId: string): Promise<JobSummary> {
  return request<JobSummary>(`/jobs/${encodeURIComponent(jobId)}`);
}

export function listJobs(): Promise<JobHistoryItem[]> {
  return request<JobHistoryItem[]>("/jobs");
}

export function createTermLibrary(name: string): Promise<TermLibrary> {
  return request<TermLibrary>("/term-libraries", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) });
}

export function addTerm(library: string, term: string): Promise<TermLibrary> {
  return request<TermLibrary>(`/term-libraries/${encodeURIComponent(library)}/terms`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ term }) });
}

export function deleteTerm(library: string, term: string): Promise<TermLibrary> {
  return request<TermLibrary>(`/term-libraries/${encodeURIComponent(library)}/terms`, { method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ term }) });
}

export function getReport(jobId: string): Promise<AnalysisReport> {
  return request<AnalysisReport>(`/jobs/${encodeURIComponent(jobId)}/report.json`);
}

export async function addTermAndRematch(jobId: string, library: string, term: string): Promise<AnalysisReport> {
  await request(`/term-libraries/${encodeURIComponent(library)}/terms`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ term }) });
  await request(`/jobs/${encodeURIComponent(jobId)}/rematch`, { method: "POST" });
  return getReport(jobId);
}
