import { CanvasDocument } from "../types/canvas";

const API_BASE = import.meta.env.VITE_API_BASE || "/api";

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export async function fetchCatalog() {
  const res = await fetch(`${API_BASE}/catalog`);
  if (!res.ok) throw new Error("Catalog fetch failed");
  return res.json();
}

export async function fetchSuites() {
  const res = await fetch(`${API_BASE}/suites`);
  if (!res.ok) throw new Error("Suites fetch failed");
  return res.json();
}

export async function fetchSuite(stem: string) {
  const res = await fetch(`${API_BASE}/suites/${stem}`);
  if (!res.ok) throw new Error("Suite fetch failed");
  return res.json();
}

export async function saveSuite(document: CanvasDocument, stem?: string) {
  const res = await fetch(`${API_BASE}/suites`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document, stem }),
  });
  if (!res.ok) throw new Error("Save failed");
  return res.json();
}

export async function updateSuite(stem: string, document: CanvasDocument) {
  const res = await fetch(`${API_BASE}/suites/${stem}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document }),
  });
  if (!res.ok) throw new Error("Update failed");
  return res.json();
}

export async function deleteSuite(stem: string) {
  const res = await fetch(`${API_BASE}/suites/${stem}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Delete failed");
  return res.json();
}

export async function previewDocument(document: CanvasDocument) {
  const res = await fetch(`${API_BASE}/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document }),
  });
  if (!res.ok) throw new Error("Preview failed");
  return res.json();
}

export async function validateDocument(document: CanvasDocument, dryRun = false) {
  const res = await fetch(`${API_BASE}/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document, dry_run: dryRun }),
  });
  if (!res.ok) throw new Error("Validation failed");
  return res.json();
}

export async function initWorkspace() {
  const res = await fetch(`${API_BASE}/init`, { method: "POST" });
  if (!res.ok) throw new Error("Init failed");
  return res.json();
}

export function catalogToKeywordOptions(catalog: { keywords: Array<{ name: string; library: string; category: string; curated: boolean }> }) {
  return catalog.keywords.map((kw) => ({
    name: kw.name,
    library: kw.library,
    category: kw.category,
    curated: kw.curated,
  }));
}