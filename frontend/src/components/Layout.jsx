import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          Auth<span>RAG</span>
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/" end>Chat</NavLink>
          {user?.role === "admin" && (
            <>
              <NavLink to="/documents">Documents</NavLink>
              <NavLink to="/admin">Admin Dashboard</NavLink>
            </>
          )}
        </nav>
        <div className="sidebar-user">
          <div>{user?.name}</div>
          <div>{user?.email}</div>
          <div className="role-badge">{user?.role}</div>
          <button onClick={handleLogout}>Sign out</button>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
