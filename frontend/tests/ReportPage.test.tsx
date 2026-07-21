import { cleanup, fireEvent, render, screen } from "@testing-library/react";
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
    cleanup();
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

  it("offers report navigation and a downloadable JSON export", async () => {
    render(<ReportPage jobId="job-1" />);
    expect(await screen.findByRole("link", { name: /返回首页/ })).toHaveAttribute("href", "/");
    expect(screen.getAllByRole("link", { name: /下载 JSON 报告/ })[0]).toHaveAttribute("href", "/api/v1/jobs/job-1/report.json");
    expect(screen.getByRole("link", { name: /打开 HTML 报告/ })).toHaveAttribute("href", "/api/v1/jobs/job-1/report.html");
  });

  it("shows an empty state when filters have no matching issues", async () => {
    const user = userEvent.setup();
    render(<ReportPage jobId="job-1" />);
    await screen.findAllByTestId("issue-row");
    await user.selectOptions(screen.getByLabelText("来源"), "rule");
    expect(screen.getByText("当前筛选条件下没有问题")).toBeInTheDocument();
    expect(screen.queryByTestId("issue-row")).not.toBeInTheDocument();
  });

  it("enables the term action only after selecting text on a text issue", async () => {
    render(<ReportPage jobId="job-1" />);
    await screen.findAllByTestId("issue-context");
    const issueContext = screen.getAllByTestId("issue-context")[0];
    const termAction = screen.getAllByRole("button", { name: "划词后添加术语" })[0];
    expect(termAction).toBeDisabled();
    vi.stubGlobal("getSelection", () => ({ toString: () => "支持" }));
    fireEvent.mouseUp(issueContext);
    expect(screen.getByRole("button", { name: /添加“支持”为术语/ })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "划词后添加术语" })).not.toBeInTheDocument();
  });

  it("rematches with the library selected in the dialog", async () => {
    render(<ReportPage jobId="job-1" />);
    const context = (await screen.findAllByTestId("issue-context"))[0];
    vi.stubGlobal("getSelection", () => ({ toString: () => "支持" }));
    fireEvent.mouseUp(context);
    fireEvent.click(screen.getByRole("button", { name: /添加“支持”为术语/ }));
    fireEvent.click(screen.getByRole("button", { name: "确认添加" }));
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledWith("/api/v1/jobs/job-1/rematch", expect.objectContaining({ method: "POST", body: JSON.stringify({ library: "default" }) })));
  });
});
