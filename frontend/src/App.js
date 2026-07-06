import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Landing from "./pages/Landing";
import Studio from "./pages/Studio";
import Gallery from "./pages/Gallery";
import GalleryItem from "./pages/GalleryItem";

function App() {
  return (
    <div className="grain min-h-screen">
      <Toaster position="top-right" theme="dark" richColors />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/studio" element={<Studio />} />
          <Route path="/studio/:projectId" element={<Studio />} />
          <Route path="/gallery" element={<Gallery />} />
          <Route path="/gallery/:projectId" element={<GalleryItem />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
