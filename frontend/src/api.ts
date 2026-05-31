import React from "react";

const API = "/api";

export type JobRef = string | number;

export function jobRef(job: Pick<Job, "slug" | "id">): string {
  return job.slug || String(job.id);
}

export function studioPath(job: Pick<Job, "slug" | "id">): string {
  return `/studio/${jobRef(job)}`;
}

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
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json();
}

export interface JobLogEvent {
  id: number;
  event_type: string;
  message?: string;
  payload?: Record<string, unknown>;
  created_at: string;
}

export interface JobListPage {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Job {
  id: number;
  slug?: string;
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

  listJobs: (page = 1, pageSize = 10) =>
    request<JobListPage>(`/jobs?page=${page}&page_size=${pageSize}`),
  getJob: (ref: JobRef) => request<Job>(`/jobs/${ref}`),
  getJobLogs: (ref: JobRef) => request<{ events: JobLogEvent[]; file_log: string }>(`/jobs/${ref}/logs`),
  deleteJob: (ref: JobRef) => request<{ ok: boolean }>(`/jobs/${ref}`, { method: "DELETE" }),
  retryJob: (ref: JobRef) => request<Job>(`/jobs/${ref}/retry`, { method: "POST" }),
  createFromUrl: (source_url: string) =>
    request<Job>("/jobs", { method: "POST", body: JSON.stringify({ source_url }) }),
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<Job>("/jobs/upload", { method: "POST", body: fd });
  },
  updateJob: (ref: JobRef, data: Partial<{ edit_spec: object; caption: string; publish_targets: string[] }>) =>
    request<Job>(`/jobs/${ref}`, { method: "PATCH", body: JSON.stringify(data) }),
  exportJob: (ref: JobRef) => request<Job>(`/jobs/${ref}/export`, { method: "POST" }),
  publishJob: (ref: JobRef, platforms: string[], caption?: string) =>
    request<Job>(`/jobs/${ref}/publish`, {
      method: "POST",
      body: JSON.stringify({ platforms, caption }),
    }),
  retryPlatform: (ref: JobRef, platform: string) =>
    request<Job>(`/jobs/${ref}/retry/${platform}`, { method: "POST" }),
  generateCaptions: (ref: JobRef) => request(`/jobs/${ref}/generate-captions`, { method: "POST" }),
  uploadCaptions: (ref: JobRef, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request(`/jobs/${ref}/captions`, { method: "POST", body: fd });
  },
  uploadAudio: (ref: JobRef, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request(`/jobs/${ref}/audio-overlay`, { method: "POST", body: fd });
  },
  suggestCaption: (title: string, platform: string) =>
    request<{ available: boolean; caption?: string }>("/ai/suggest-caption", {
      method: "POST",
      body: JSON.stringify({ title, platform, context: "" }),
    }),

  listAccounts: () => request<AccountStatus[]>("/accounts"),
  mediaUrl: (ref: JobRef, kind: string) => `${API}/jobs/${ref}/media/${kind}`,
  connectMeta: () => { window.location.href = `${API}/oauth/meta/connect`; },
  connectGoogle: () => { window.location.href = `${API}/oauth/google/connect`; },
  validateJob: (ref: JobRef) => request<{ warnings: Record<string, string[]> }>(`/jobs/${ref}/validation`),
};

export function useJobEvents(jobRef: JobRef | null, onEvent: (data: unknown) => void) {
  React.useEffect(() => {
    if (jobRef == null || jobRef === "") return;
    const es = new EventSource(`${API}/jobs/${jobRef}/events`, { withCredentials: true });
    es.onmessage = (e) => {
      try {
        onEvent(JSON.parse(e.data));
      } catch { /* ignore */ }
    };
    return () => es.close();
  }, [jobRef, onEvent]);
}
