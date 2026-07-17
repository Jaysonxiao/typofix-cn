from html import escape
from pathlib import Path

from typofix_cn.domain.reports import AnalysisReport
from .json_report import JsonReportWriter


class HtmlReportWriter:
    def write(self, report: AnalysisReport, path: Path) -> None:
        rows = "".join(
            f"<article class='issue' data-category='{escape(issue.category.value)}' data-status='{escape(issue.status.value)}'>"
            f"<h2>{escape(issue.category.value)}</h2><p>{escape(issue.message)}</p>"
            f"<p><strong>原文：</strong>{escape(issue.original)}</p><p><strong>上下文：</strong>{escape(issue.context)}</p></article>"
            for issue in report.issues
        )
        html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>Typofix CN 报告</title>
<style>body{{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem}}.issue{{border:1px solid #d9dee8;border-radius:8px;padding:1rem;margin:1rem 0}}h2{{font-size:1rem}}</style>
</head><body><h1>Typofix CN 校验报告</h1><p>问题总数：{report.summary.total}，待处理：{report.summary.actionable}，术语豁免：{report.summary.term_suppressed}</p>{rows}</body></html>"""
        JsonReportWriter._atomic_write(path, html)
