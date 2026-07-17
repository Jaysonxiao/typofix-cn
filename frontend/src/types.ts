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
