import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Runs } from "./pages/Runs";
import { RunDetail } from "./pages/RunDetail";
import { Policies } from "./pages/Policies";
import { Audit } from "./pages/Audit";
import { Agents } from "./pages/Agents";
import { Developers } from "./pages/Developers";
import { Settings } from "./pages/Settings";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/runs" replace />} />
        <Route path="/runs" element={<Runs />} />
        <Route path="/runs/:id" element={<RunDetail />} />
        <Route path="/policies" element={<Policies />} />
        <Route path="/audit" element={<Audit />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/developers" element={<Developers />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/runs" replace />} />
      </Route>
    </Routes>
  );
}
