import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Landing from "./pages/Landing";
import Studio from "./pages/Studio";
import Gallery from "./pages/Gallery";
import GalleryItem from "./pages/GalleryItem";
import Login from "./pages/Login";
import AuthCallback from "./pages/AuthCallback";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from "./lib/auth";

function App() {
  return (
    <div className="grain min-h-screen">
      <Toaster position="top-right" theme="dark" richColors />
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Public — landing page & demos */}
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/auth/callback" element={<AuthCallback />} />

            {/* Gated — Studio, Gallery, downloads, share */}
            <Route path="/studio" element={<ProtectedRoute><Studio /></ProtectedRoute>} />
            <Route path="/studio/:projectId" element={<ProtectedRoute><Studio /></ProtectedRoute>} />
            <Route path="/gallery" element={<ProtectedRoute><Gallery /></ProtectedRoute>} />
            <Route path="/gallery/:projectId" element={<ProtectedRoute><GalleryItem /></ProtectedRoute>} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
