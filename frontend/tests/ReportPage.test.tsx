import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ReportPage } from "../src/pages/ReportPage";


const report = {
  schema_version: 1,
  job_id: "job-1",
  mode: "full",
  documents: [{ document_path: "论文.docx", status: "completed", issue_ids: ["a", "b"] }],
  issues: [
    { issue_id: "a", source: "model", category: "TEXT_CORRECTION", type_code: "SPELLING_TYPO", severity: "error", status: "actionable", location: { document_path: "论文.docx", region: "body", paragraph_index: 0, sentence_index: 0, start_offset: 4, end_offset: 5 }, original: "做", suggestion: "作", message: "建议修改", context: "支持麒麟操做系统。", term_hits: [] },
    { issue_id: "b", source: "model", category: "TEXT_CORRECTION", type_code: "SPELLING_TYPO", severity: "error", status: "term_suppressed", location: { document_path: "论文.docx", region: "body", paragraph_index: 1, sentence_index: 0, start_offset: 2, end_offset: 3 }, original: "做", suggestion: "作", message: "术语豁免", context: "麒麟操做系统", term_hits: [{ library: "default", term: "麒麟操做系统", start_offset: 0, end_offset: 7 }] },
  ],
  summary: { total: 2, actionable: 1, term_suppressed: 1, by_category: { TEXT_CORRECTION: 2 }, by_source: { model: 2 } },
};


describe("ReportPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/report.json")) return new Response(JSON.stringify(report), { status: 200 });
      if (url.endsWith("/term-libraries")) return new Response(JSON.stringify([{ name: "default", terms: ["麒麟操做系统"] }]), { status: 200 });
      if (init?.method === "POST") return new Response(JSON.stringify({ terms: ["麒麟操做系统"] }), { status: 200 });
      return new Response(JSON.stringify({ summary: report.summary }), { status: 200 });
    }));
  });

  it("shows only parent categories and filters suppressed model findings", async () => {
    const user = userEvent.setup();
    render(<ReportPage jobId="job-1" />);
    expect(await screen.findByRole("option", { name: "文字纠错" })).toBeInTheDocument();
    expect(screen.queryByText("SPELLING_TYPO")).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("状态"), "term_suppressed");
    expect(screen.getAllByTestId("issue-row")).toHaveLength(1);
    expect(screen.getAllByText("术语豁免").length).toBeGreaterThan(0);
  });
});
