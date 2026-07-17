import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HistoryPage } from "../src/pages/HistoryPage";

describe("HistoryPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify([
      { job_id: "job-1", status: "completed", mode: "full", input_paths: ["论文.docx"], selected_libraries: ["default"], total_documents: 1, processed_documents: 1, phase: "completed" },
    ]))));
  });

  it("lists completed jobs with report links", async () => {
    render(<HistoryPage />);
    expect(await screen.findByText("论文.docx")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /查看报告/ })).toHaveAttribute("href", "/jobs/job-1");
  });
});
