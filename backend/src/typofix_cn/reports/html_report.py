from html import escape
from pathlib import Path

from typofix_cn.domain.reports import AnalysisReport
from typofix_cn.domain.enums import IssueCategory
from .json_report import JsonReportWriter


CATEGORY_LABELS = {
    IssueCategory.TEXT_CORRECTION: "文字纠错",
    IssueCategory.PUNCTUATION_CHARACTER: "标点与字符",
    IssueCategory.PARAGRAPH_LAYOUT: "段落与版式",
    IssueCategory.STRUCTURE_NUMBERING: "结构与编号",
    IssueCategory.CITATION_REFERENCE: "引用与参考文献",
}


class HtmlReportWriter:
    def write(self, report: AnalysisReport, path: Path) -> None:
        rows = "".join(
            f"<article class='issue' data-category='{escape(issue.category.value)}' data-status='{escape(issue.status.value)}'>"
            f"<h2>{escape(CATEGORY_LABELS.get(issue.category, issue.category.value))}</h2>"
            f"<p><strong>来源：</strong>{'模型' if issue.source.value == 'model' else '规则'}　<strong>状态：</strong>{'术语豁免' if issue.status.value == 'term_suppressed' else '待处理'}</p>"
            f"<p><strong>位置：</strong>{escape(issue.location.document_path)} · 第 {issue.location.paragraph_index + 1} 段 · 第 {issue.location.sentence_index + 1} 句 · 字符 {issue.location.start_offset}-{issue.location.end_offset}</p>"
            f"<p><strong>原文：</strong>{escape(issue.original)}</p><p><strong>建议：</strong>{escape(issue.suggestion or '无')}</p><p><strong>上下文：</strong>{escape(issue.context)}</p></article>"
            for issue in report.issues
        )
        html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>Typofix CN 报告</title>
<style>body{{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem}}.issue{{border:1px solid #d9dee8;border-radius:8px;padding:1rem;margin:1rem 0}}h2{{font-size:1rem}}</style>
</head><body><h1>Typofix CN 校验报告</h1><p>问题总数：{report.summary.total}，待处理：{report.summary.actionable}，术语豁免：{report.summary.term_suppressed}</p>{rows}</body></html>"""
        JsonReportWriter._atomic_write(path, html)
