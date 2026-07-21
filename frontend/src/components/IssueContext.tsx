import type { Issue } from "../types";

export function IssueContext({ issue, onSelectionChange }: { issue: Issue; onSelectionChange?: (value: string) => void }) {
  const start = Math.max(0, issue.context.indexOf(issue.original));
  const end = start >= 0 ? start + issue.original.length : 0;
  const before = start >= 0 ? issue.context.slice(0, start) : issue.context;
  const after = start >= 0 ? issue.context.slice(end) : "";
  return <div className="issue-context" data-testid="issue-context" onMouseUp={() => { const selection = window.getSelection()?.toString().trim(); onSelectionChange?.(selection ?? ""); }}><span>{before}</span>{start >= 0 && <mark>{issue.original}</mark>}<span>{after}</span></div>;
}
