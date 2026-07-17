import { BrowserRouter, Route, Routes, useParams } from "react-router-dom";

import { CheckPage } from "./pages/CheckPage";
import { ReportPage } from "./pages/ReportPage";

function ReportRoute() {
  const { jobId } = useParams<{ jobId: string }>();
  return jobId ? <ReportPage jobId={jobId} /> : <CheckPage />;
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/jobs/:jobId" element={<ReportRoute />} />
        <Route path="*" element={<CheckPage />} />
      </Routes>
    </BrowserRouter>
  );
}
