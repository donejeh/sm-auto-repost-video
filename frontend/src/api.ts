import React from "react";

const API = "/api";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    credentials: "include",
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...options.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export interface Job {
  id: number;
  status: string;
  stage: string;
  source_type: string;
  source_url?: string;
  source_platform?: string;
  title?: string;
  duration_seconds?: number;
  edit_spec: Record<string, unknown>;
  caption?: string;
  publish_targets: string[];
  progress_message?: string;
  last_error?: string;
  proxy_path?: string;
  export_path?: string;
  thumbnail_path?: string;
  created_at?: string;
  updated_at?: string;
  publish_results: {
    platform: string;
    success: boolean;
    platform_post_url?: string;
    error_message?: string;
  }[];
}

export interface AccountStatus {
  provider: string;
  connected: boolean;
  status: string;
  account_label?: string;
  missing_permissions?: string[];
}

export const api = {
  login: (email: string, password: string) =>
    request<{ id: number; email: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (email: string, password: string) =>
    request("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => request<{ id: number; email: string }>("/auth/me"),
  logout: () => request("/auth/logout", { method: "POST" }),

  listJobs: () => request<Job[]>("/jobs"),
  getJob: (id: number) => request<Job>(`/jobs/${id}`),
  createFromUrl: (source_url: string) =>
    request<Job>("/jobs", { method: "POST", body: JSON.stringify({ source_url }) }),
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<Job>("/jobs/upload", { method: "POST", body: fd });
  },
  updateJob: (id: number, data: Partial<{ edit_spec: object; caption: string; publish_targets: string[] }>) =>
    request<Job>(`/jobs/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  exportJob: (id: number) => request<Job>(`/jobs/${id}/export`, { method: "POST" }),
  publishJob: (id: number, platforms: string[], caption?: string) =>
    request<Job>(`/jobs/${id}/publish`, {
      method: "POST",
      body: JSON.stringify({ platforms, caption }),
    }),
  retryPlatform: (id: number, platform: string) =>
    request<Job>(`/jobs/${id}/retry/${platform}`, { method: "POST" }),
  generateCaptions: (id: number) => request(`/jobs/${id}/generate-captions`, { method: "POST" }),
  uploadCaptions: (id: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request(`/jobs/${id}/captions`, { method: "POST", body: fd });
  },
  uploadAudio: (id: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request(`/jobs/${id}/audio-overlay`, { method: "POST", body: fd });
  },
  suggestCaption: (title: string, platform: string) =>
    request<{ available: boolean; caption?: string }>("/ai/suggest-caption", {
      method: "POST",
      body: JSON.stringify({ title, platform, context: "" }),
    }),

  listAccounts: () => request<AccountStatus[]>("/accounts"),
  mediaUrl: (jobId: number, kind: string) => `${API}/jobs/${jobId}/media/${kind}`,
  connectMeta: () => { window.location.href = `${API}/oauth/meta/connect`; },
  connectGoogle: () => { window.location.href = `${API}/oauth/google/connect`; },
  validateJob: (id: number) => request<{ warnings: Record<string, string[]> }>(`/jobs/${id}/validation`),
};

export function useJobEvents(jobId: number | null, onEvent: (data: unknown) => void) {
  React.useEffect(() => {
    if (!jobId) return;
    const es = new EventSource(`${API}/jobs/${jobId}/events`, { withCredentials: true });
    es.onmessage = (e) => {
      try {
        onEvent(JSON.parse(e.data));
      } catch { /* ignore */ }
    };
    return () => es.close();
  }, [jobId, onEvent]);
}
