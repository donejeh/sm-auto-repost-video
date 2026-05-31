import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, AccountStatus } from "../api";

export default function Settings() {
  const [accounts, setAccounts] = useState<AccountStatus[]>([]);
  const [params] = useSearchParams();

  useEffect(() => {
    api.listAccounts().then(setAccounts);
    if (params.get("connected")) {
      setTimeout(() => api.listAccounts().then(setAccounts), 1000);
    }
  }, [params]);

  const meta = accounts.find((a) => a.provider === "meta");
  const google = accounts.find((a) => a.provider === "google");

  return (
    <div>
      <h1>Connected Accounts</h1>
      <p style={{ color: "var(--text-muted)" }}>Connect platforms to publish Reels and Shorts.</p>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <h3>Meta (Instagram + Facebook)</h3>
        {meta?.connected ? (
          <>
            <p><span className="badge badge-success">Connected</span> {meta.account_label}</p>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Status: {meta.status}</p>
            {meta.missing_permissions && meta.missing_permissions.length > 0 && (
              <p style={{ color: "var(--warning)" }}>Missing: {meta.missing_permissions.join(", ")}</p>
            )}
          </>
        ) : (
          <p style={{ color: "var(--text-muted)" }}>Not connected</p>
        )}
        <button type="button" className="btn btn-primary" style={{ marginTop: "0.75rem" }} onClick={() => api.connectMeta()}>
          Connect Meta
        </button>
      </div>

      <div className="card">
        <h3>YouTube</h3>
        {google?.connected ? (
          <p><span className="badge badge-success">Connected</span> {google.account_label}</p>
        ) : (
          <p style={{ color: "var(--text-muted)" }}>Not connected</p>
        )}
        <button type="button" className="btn btn-primary" style={{ marginTop: "0.75rem" }} onClick={() => api.connectGoogle()}>
          Connect YouTube
        </button>
      </div>

      <div className="card" style={{ marginTop: "1rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>
        <p>Configure <code>META_APP_ID</code>, <code>META_APP_SECRET</code>, <code>GOOGLE_CLIENT_ID</code>, and <code>GOOGLE_CLIENT_SECRET</code> in your backend <code>.env</code>.</p>
        <p>Fallback: set <code>INSTAGRAM_GRAPH_ACCESS_TOKEN</code>, <code>INSTAGRAM_BUSINESS_ACCOUNT_ID</code>, and <code>FACEBOOK_PAGE_ID</code> for headless publishing.</p>
      </div>
    </div>
  );
}
