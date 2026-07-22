import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TermsPage } from "../src/pages/TermsPage";

describe("TermsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/term-libraries") && !init) return new Response(JSON.stringify([{ name: "default", terms: ["麒麟操做系统"] }]));
      if (url.endsWith("/term-libraries/default")) return new Response(JSON.stringify({ name: "default", terms: ["麒麟操做系统"] }));
      if (init?.method === "POST") return new Response(JSON.stringify({ name: "new", terms: [] }), { status: 201 });
      return new Response(JSON.stringify({ name: "default", terms: [] }));
    }));
  });

  it("shows terms and creates a library", async () => {
    const user = userEvent.setup();
    render(<TermsPage />);
    expect(await screen.findByText("麒麟操做系统")).toBeInTheDocument();
    await user.type(screen.getByLabelText("新术语库名称"), "论文");
    await user.click(screen.getByRole("button", { name: "创建术语库" }));
    expect(fetch).toHaveBeenCalledWith("/api/v1/term-libraries", expect.objectContaining({ method: "POST" }));
  });
});
