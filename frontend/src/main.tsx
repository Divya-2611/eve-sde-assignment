import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider, AdminRoute, ProtectedRoute } from "./auth";
import Layout from "./components/Layout";
import Bookings from "./pages/Bookings";
import AdminBookings from "./pages/admin/Bookings";
import Catalogue from "./pages/admin/Catalogue";
import Dashboard from "./pages/admin/Dashboard";
import Centres from "./pages/Centres";
import CentreDetail from "./pages/CentreDetail";
import Checkout from "./pages/Checkout";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import "./styles.css";

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/" element={<Centres />} />
        <Route path="/centres/:id" element={<CentreDetail />} />
        <Route path="/bookings" element={<ProtectedRoute><Bookings /></ProtectedRoute>} />
        <Route path="/checkout/:bookingId" element={<ProtectedRoute><Checkout /></ProtectedRoute>} />
        <Route path="/admin" element={<AdminRoute><Dashboard /></AdminRoute>} />
        <Route path="/admin/bookings" element={<AdminRoute><AdminBookings /></AdminRoute>} />
        <Route path="/admin/catalogue" element={<AdminRoute><Catalogue /></AdminRoute>} />
      </Route>
    </Routes>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
