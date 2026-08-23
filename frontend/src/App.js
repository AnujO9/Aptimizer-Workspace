import "@/App.css";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Projects from "@/pages/Projects";
import Profile from "@/pages/Profile";
import Workspace from "@/pages/Workspace";
import Admin from "@/pages/Admin";
import PublicCompliance from "@/pages/PublicCompliance";

const Protected = ({ children }) => {
  const { user } = useAuth();
  if (user === null)
    return (
      <div className="min-h-screen grid place-items-center text-sm text-slate-500" data-testid="auth-loading">
        Loading Aptimizer…
      </div>
    );
  if (user === false) return <Navigate to="/login" replace />;
  return children;
};

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/share/compliance/:token" element={<PublicCompliance />} />
            <Route
              path="/projects"
              element={
                <Protected>
                  <Projects />
                </Protected>
              }
            />
            <Route
              path="/projects/:projectId"
              element={
                <Protected>
                  <Workspace />
                </Protected>
              }
            />
            <Route
              path="/profile"
              element={
                <Protected>
                  <Profile />
                </Protected>
              }
            />
            <Route
              path="/admin"
              element={
                <Protected>
                  <Admin />
                </Protected>
              }
            />
            <Route path="*" element={<Navigate to="/projects" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" />
      </AuthProvider>
    </div>
  );
}

export default App;
