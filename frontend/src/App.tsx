import { BrowserRouter, Route, Routes } from "react-router-dom";

import { CheckPage } from "./pages/CheckPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="*" element={<CheckPage />} />
      </Routes>
    </BrowserRouter>
  );
}
