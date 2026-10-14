import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Runs } from "./pages/Runs";
import { RunDetail } from "./pages/RunDetail";
import { Policies } from "./pages/Policies";
import { Audit } from "./pages/Audit";
import { Agents } from "./pages/Agents";
import { Developers } from "./pages/Developers";
import { Settings } from "./pages/Settings";
import { Login } from "./pages/Login";
import { getToken } from "./api";

function RequireAuth({ children }: { children: React.ReactNode }) {
  if (!getToken()) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
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
