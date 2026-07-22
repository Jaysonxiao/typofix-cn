import type { AnalysisReport } from "../types";

const categoryLabels: Record<string, string> = {
  TEXT_CORRECTION: "文字纠错",
  PUNCTUATION_CHARACTER: "标点与字符",
  PARAGRAPH_LAYOUT: "段落与版式",
  STRUCTURE_NUMBERING: "结构与编号",
  CITATION_REFERENCE: "引用与参考文献",
};

export function categoryLabel(category: string) { return categoryLabels[category] ?? category; }

export function ReportSummary({ report }: { report: AnalysisReport }) {
  return <div className="report-summary"><div><strong>{report.summary.actionable}</strong><span>待处理</span></div><div className="summary-suppressed"><strong>{report.summary.term_suppressed}</strong><span>术语豁免</span></div><div><strong>{report.summary.total}</strong><span>全部发现</span></div></div>;
}
