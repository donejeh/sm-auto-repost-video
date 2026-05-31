import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Film, History, LayoutDashboard, LogOut, Settings } from "lucide-react";
import { api } from "../api";

export default function Layout() {
  const navigate = useNavigate();

  const logout = async () => {
    await api.logout();
    navigate("/login");
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">AutoVideo</div>
        <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} end>
          <LayoutDashboard size={18} /> Dashboard
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
          <History size={18} /> History
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
          <Settings size={18} /> Connected Accounts
        </NavLink>
        <div style={{ flex: 1 }} />
        <button type="button" className="nav-link" onClick={logout} style={{ border: "none", background: "none", width: "100%" }}>
          <LogOut size={18} /> Log out
        </button>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}

export function StudioIcon() {
  return <Film size={18} />;
}
