import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Landing from "./pages/Landing";
import Studio from "./pages/Studio";
import Gallery from "./pages/Gallery";
import GalleryItem from "./pages/GalleryItem";
import Login from "./pages/Login";
import AuthCallback from "./pages/AuthCallback";
import Pricing from "./pages/Pricing";
import VerifyIdentity from "./pages/VerifyIdentity";
import ForgotPassword from "./pages/ForgotPassword";
import Admin from "./pages/Admin";
import ProtectedRoute from "./components/ProtectedRoute";
import LicenseGate from "./components/LicenseGate";
import { AuthProvider } from "./lib/auth";

function App() {
  return (
    <div className="grain min-h-screen">
      <Toaster position="top-right" theme="dark" richColors />
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Public — landing page & demos, pricing (view-only) */}
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route path="/pricing" element={<Pricing />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />

            {/* Admin-only route (server-side role check is authoritative) */}
            <Route path="/admin" element={<ProtectedRoute><Admin /></ProtectedRoute>} />

            {/* Auth required — verification page */}
            <Route
              path="/verify"
              element={<ProtectedRoute><VerifyIdentity /></ProtectedRoute>}
            />

            {/* Auth + license required — Studio (creating films) */}
            <Route
              path="/studio"
              element={
                <ProtectedRoute>
                  <LicenseGate><Studio /></LicenseGate>
                </ProtectedRoute>
              }
            />
            <Route
              path="/studio/:projectId"
              element={
                <ProtectedRoute>
                  <LicenseGate><Studio /></LicenseGate>
                </ProtectedRoute>
              }
            />

            {/* Auth only — gallery view (read-only access allowed after expiry) */}
            <Route path="/gallery" element={<ProtectedRoute><Gallery /></ProtectedRoute>} />
            <Route path="/gallery/:projectId" element={<ProtectedRoute><GalleryItem /></ProtectedRoute>} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
