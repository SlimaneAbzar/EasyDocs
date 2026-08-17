import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { token, logout } = useAuth();

  return (
    <nav className="navbar">
      <Link to="/" className="nav-logo">EasyDocs<span className="accent">.</span></Link>
      <div className="nav-links">
        {token ? (
          <>
            <Link to="/dashboard">Documents</Link>
            <Link to="/history">History</Link>
            <button onClick={logout} className="nav-btn">Log out</button>
          </>
        ) : (
          <>
            <Link to="/login">Log in</Link>
            <Link to="/register" className="nav-btn">Register</Link>
          </>
        )}
      </div>
    </nav>
  );
}
