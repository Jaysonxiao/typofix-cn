import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CheckPage } from "../src/pages/CheckPage";


describe("CheckPage", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("uploads files with selected terminology libraries and shows progress", async () => {
    let statusCalls = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/term-libraries")) {
        return new Response(JSON.stringify([{ name: "default", terms: [] }, { name: "computer-science", terms: [] }]), { status: 200 });
      }
      if (url.endsWith("/jobs") && init?.method === "POST") {
        return new Response(JSON.stringify({ job_id: "job-1", status: "queued" }), { status: 202 });
      }
      statusCalls += 1;
      return new Response(JSON.stringify({ job_id: "job-1", status: statusCalls === 1 ? "running" : "completed", phase: "analysis", processed_documents: 0, total_documents: 1 }), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<CheckPage />);
    await userEvent.upload(screen.getByLabelText("上传文件"), new File(["docx"], "论文.docx", { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" }));
    fireEvent.change(screen.getByLabelText("检测阈值"), { target: { value: "0.4" } });
    fireEvent.change(screen.getByLabelText("纠正阈值"), { target: { value: "0.2" } });
    await user.click(await screen.findByLabelText("default"));
    await user.click(screen.getByRole("button", { name: "开始校验" }));
    expect(await screen.findByText("正在校验")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("校验完成")).toBeInTheDocument(), { timeout: 3000 });
    const request = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    expect(request).toBeDefined();
    expect((request?.[1]?.body as FormData).get("term_libraries")).toBe("default");
    expect((request?.[1]?.body as FormData).get("detection_threshold")).toBe("0.4");
    expect((request?.[1]?.body as FormData).get("correction_threshold")).toBe("0.2");
  });

  it("tests plain text with separate MacBERT thresholds and keeps the DOCX entry", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/term-libraries")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      return new Response(JSON.stringify({
        source: "今天新情很好",
        target: "今天心情很好",
        errors: [["新", "心", 2]],
        decisions: [{ start: 2, end: 3, source: "新", suggestion: "心", provider: "model", accepted: true }],
      }), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<CheckPage />);
    await user.type(screen.getByLabelText("测试文本"), "今天新情很好");
    fireEvent.change(screen.getByLabelText("检测阈值"), { target: { value: "0.35" } });
    fireEvent.change(screen.getByLabelText("纠正阈值"), { target: { value: "0.25" } });
    await user.click(screen.getByRole("button", { name: "测试模型" }));

    expect(await screen.findByText(/今天心情很好/)).toBeInTheDocument();
    expect(screen.getByText("0.35")).toBeInTheDocument();
    expect(screen.getByText("0.25")).toBeInTheDocument();
    const modelRequest = fetchMock.mock.calls.find(([input]) => String(input).endsWith("/macbert/test"));
    expect(JSON.parse(String(modelRequest?.[1]?.body))).toEqual({ text: "今天新情很好", detection_threshold: 0.35, correction_threshold: 0.25 });
    expect(screen.getByText("上传文件")).toBeInTheDocument();
    expect(screen.queryByText("把论文里的小毛刺，留在交稿前。")).not.toBeInTheDocument();
  });
});
