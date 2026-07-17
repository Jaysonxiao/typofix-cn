import { BrowserRouter, Route, Routes, useParams } from "react-router-dom";

import { CheckPage } from "./pages/CheckPage";
import { HistoryPage } from "./pages/HistoryPage";
import { ReportPage } from "./pages/ReportPage";
import { TermsPage } from "./pages/TermsPage";

function ReportRoute() {
  const { jobId } = useParams<{ jobId: string }>();
  return jobId ? <ReportPage jobId={jobId} /> : <CheckPage />;
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/jobs/:jobId" element={<ReportRoute />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="*" element={<CheckPage />} />
      </Routes>
    </BrowserRouter>
  );
}
