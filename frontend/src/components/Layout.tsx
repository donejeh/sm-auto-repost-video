import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  ChevronLeft,
  ChevronRight,
  History,
  LayoutDashboard,
  LogOut,
  Settings,
} from "lucide-react";
import { api } from "../api";

const STORAGE_KEY = "autovideo-sidebar-collapsed";

export default function Layout() {
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem(STORAGE_KEY) === "1",
  );

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  const logout = async () => {
    await api.logout();
    navigate("/login");
  };

  return (
    <div className={`app-shell ${collapsed ? "app-shell--sidebar-collapsed" : ""}`}>
      <aside className={`sidebar ${collapsed ? "sidebar--collapsed" : ""}`}>
        <div className="sidebar-header">
          <div className="sidebar-brand" title="AutoVideo">
            {collapsed ? "AV" : "AutoVideo"}
          </div>
          <button
            type="button"
            className="sidebar-toggle"
            onClick={() => setCollapsed((c) => !c)}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>

        <nav className="sidebar-nav">
          <NavLink
            to="/"
            className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
            end
            title="Dashboard"
          >
            <LayoutDashboard size={18} />
            <span className="nav-link__label">Dashboard</span>
          </NavLink>
          <NavLink
            to="/history"
            className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
            title="History"
          >
            <History size={18} />
            <span className="nav-link__label">History</span>
          </NavLink>
          <NavLink
            to="/settings"
            className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
            title="Connected Accounts"
          >
            <Settings size={18} />
            <span className="nav-link__label">Connected Accounts</span>
          </NavLink>
        </nav>

        <div style={{ flex: 1 }} />
        <button
          type="button"
          className="nav-link"
          onClick={logout}
          title="Log out"
          style={{ border: "none", background: "none", width: "100%" }}
        >
          <LogOut size={18} />
          <span className="nav-link__label">Log out</span>
        </button>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
