import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

export default function Login() {
  const [email, setEmail] = useState("admin@autovideo.local");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const [isRegister, setIsRegister] = useState(false);
  const navigate = useNavigate();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      if (isRegister) await api.register(email, password);
      await api.login(email, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  };

  return (
    <div className="login-page">
      <div className="card login-card">
        <h1 style={{ marginTop: 0, background: "linear-gradient(135deg, #818cf8, #c084fc)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          AutoVideo Studio
        </h1>
        <p style={{ color: "var(--text-muted)" }}>Download, edit, and publish vertical video.</p>
        <form onSubmit={submit}>
          <label className="label">Email</label>
          <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <label className="label" style={{ marginTop: "0.75rem" }}>Password</label>
          <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
          <button type="submit" className="btn btn-primary" style={{ width: "100%", marginTop: "1rem", justifyContent: "center" }}>
            {isRegister ? "Create account" : "Sign in"}
          </button>
        </form>
        <button type="button" className="btn btn-ghost" style={{ width: "100%", marginTop: "0.5rem" }} onClick={() => setIsRegister(!isRegister)}>
          {isRegister ? "Already have an account?" : "Create account"}
        </button>
      </div>
    </div>
  );
}
