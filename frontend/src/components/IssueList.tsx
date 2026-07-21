import { useState } from "react";

import type { Issue } from "../types";
import { categoryLabel } from "./ReportSummary";
import { IssueContext } from "./IssueContext";

export function IssueList({ issues, onSelect }: { issues: Issue[]; onSelect: (issue: Issue, term: string) => void }) {
  const [selectedTerms, setSelectedTerms] = useState<Record<string, string>>({});

  return <div className="issue-list">{issues.map((issue) => {
    const isTextCorrection = issue.category === "TEXT_CORRECTION" && issue.status !== "term_suppressed";
    const selectedTerm = selectedTerms[issue.issue_id] ?? "";
    return <article className={`issue-row ${issue.status === "term_suppressed" ? "is-suppressed" : ""}`} data-testid="issue-row" key={issue.issue_id}>
      <div className="issue-row-meta"><span className="category-pill">{categoryLabel(issue.category)}</span><span>{issue.source === "model" ? "模型" : "规则"}</span><span>{issue.status === "term_suppressed" ? "术语豁免" : "待处理"}</span></div>
      <p className="issue-location">{issue.location.document_path} · 第 {issue.location.paragraph_index + 1} 段 · 第 {issue.location.sentence_index + 1} 句 · 字符 {issue.location.start_offset}-{issue.location.end_offset}</p>
      <IssueContext issue={issue} onSelectionChange={isTextCorrection ? (term) => setSelectedTerms((current) => ({ ...current, [issue.issue_id]: term })) : undefined} />
      {isTextCorrection && <button type="button" className={`term-action ${selectedTerm ? "is-ready" : ""}`} disabled={!selectedTerm} onClick={() => onSelect(issue, selectedTerm)}>{selectedTerm ? `添加“${selectedTerm}”为术语` : "划词后添加术语"}</button>}
      <p className="issue-message">{issue.message}{issue.suggestion && <span className="suggestion">建议：{issue.suggestion}</span>}</p>
    </article>;
  })}</div>;
}
