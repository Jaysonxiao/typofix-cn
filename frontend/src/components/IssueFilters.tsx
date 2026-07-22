import type { IssueCategory, IssueSource, IssueStatus } from "../types";
import { categoryLabel } from "./ReportSummary";

interface IssueFiltersProps {
  category: IssueCategory | "all";
  status: IssueStatus | "all";
  source: IssueSource | "all";
  onCategoryChange: (value: IssueCategory | "all") => void;
  onStatusChange: (value: IssueStatus | "all") => void;
  onSourceChange: (value: IssueSource | "all") => void;
}

export function IssueFilters({ category, status, source, onCategoryChange, onStatusChange, onSourceChange }: IssueFiltersProps) {
  return <div className="issue-filters"><label>错误父类<select aria-label="错误父类" value={category} onChange={(event) => onCategoryChange(event.target.value as IssueCategory | "all")}><option value="all">全部问题</option>{["TEXT_CORRECTION", "PUNCTUATION_CHARACTER", "PARAGRAPH_LAYOUT", "STRUCTURE_NUMBERING", "CITATION_REFERENCE"].map((value) => <option key={value} value={value}>{categoryLabel(value)}</option>)}</select></label><label>状态<select aria-label="状态" value={status} onChange={(event) => onStatusChange(event.target.value as IssueStatus | "all")}><option value="all">全部状态</option><option value="actionable">待处理</option><option value="term_suppressed">术语豁免</option></select></label><label>来源<select aria-label="来源" value={source} onChange={(event) => onSourceChange(event.target.value as IssueSource | "all")}><option value="all">全部来源</option><option value="model">模型异常</option><option value="rule">规则异常</option></select></label></div>;
}
