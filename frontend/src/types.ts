export type JobStatus = "queued" | "running" | "completed" | "completed_with_document_failures" | "failed" | "interrupted";

export interface TermLibrary {
  name: string;
  terms: string[];
  modified_at?: string;
  content_sha256?: string;
}

export interface JobSummary {
  job_id: string;
  status: JobStatus;
  processed_documents: number;
  total_documents: number;
  phase: string;
  error?: string | null;
}

export interface JobCreated {
  job_id: string;
  status: JobStatus;
}

export type IssueCategory = "TEXT_CORRECTION" | "PUNCTUATION_CHARACTER" | "PARAGRAPH_LAYOUT" | "STRUCTURE_NUMBERING" | "CITATION_REFERENCE";
export type IssueStatus = "actionable" | "term_suppressed";

export interface Issue {
  issue_id: string;
  source: "model" | "rule";
  category: IssueCategory;
  type_code: string;
  severity: "error" | "warning" | "info";
  status: IssueStatus;
  location: { document_path: string; region: string; paragraph_index: number; sentence_index: number; start_offset: number; end_offset: number };
  original: string;
  suggestion?: string | null;
  message: string;
  context: string;
  term_hits: Array<{ library: string; term: string; start_offset: number; end_offset: number }>;
}

export interface AnalysisReport {
  schema_version: 1;
  job_id: string;
  mode: "full" | "rules_only";
  documents: Array<{ document_path: string; status: "completed" | "failed"; issue_ids: string[]; failure?: string | null }>;
  issues: Issue[];
  summary: { total: number; actionable: number; term_suppressed: number; by_category: Record<string, number>; by_source: Record<string, number> };
}
