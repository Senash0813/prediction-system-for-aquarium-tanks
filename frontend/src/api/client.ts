export const API_BASE = (import.meta.env.VITE_API_BASE as string) || 'http://127.0.0.1:8000';

// Map frontend tank IDs to backend collection names
const TANK_ID_MAP: Record<string, string> = {
  // Map frontend Tank A to the backend test collection
  'tank-a': 'tank_1',
  'tank-b': 'tank_2',
  'tank-c': 'tank_3',
  'tank-d': 'tank_4',
};

export function mapTankId(frontendId: string) {
  return TANK_ID_MAP[frontendId] ?? frontendId;
}

export interface TankConfigPayload {
  tank_id: string;
  mac_address: string;
  safe_ranges: {
    temperature: { min: number; max: number };
    ph: { min: number; max: number };
    turbidity: { min: number; max: number };
    light: { min: number; max: number };
    tds: { min: number; max: number };
  };
}

export async function saveTankConfig(payload: TankConfigPayload): Promise<void> {
  const res = await fetch(`${API_BASE}/api/tank-config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to save tank config: ${text}`);
  }
}

export async function getPhAnalysis(tankFrontendId: string, range: string = '24h') {
  const collectionName = mapTankId(tankFrontendId);
  const url = `${API_BASE}/api/tank/${encodeURIComponent(collectionName)}/ph-analysis?range=${encodeURIComponent(range)}`;
  const res = await fetch(url);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export async function getTankCollections(): Promise<{ tanks: string[] }> {
  const res = await fetch(`${API_BASE}/api/tanks`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to fetch tanks: ${text}`);
  }
  return res.json();
}

export async function getLatestReading(collectionName: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/tanks/${encodeURIComponent(collectionName)}/latest`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to fetch latest reading for ${collectionName}: ${text}`);
  }
  return res.json();
}

export async function getLatestInsight(collectionName: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/tanks/${encodeURIComponent(collectionName)}/latest-insight`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to fetch latest insight for ${collectionName}: ${text}`);
  }
  return res.json();
}

export async function getLatestRiskInsight(collectionName: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/tanks/${encodeURIComponent(collectionName)}/latest-risk`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to fetch latest risk insight for ${collectionName}: ${text}`);
  }
  return res.json();
}

export async function getLatestInsightsByType(collectionName: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/tanks/${encodeURIComponent(collectionName)}/latest-insights-by-type`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to fetch latest insights by type for ${collectionName}: ${text}`);
  }
  return res.json();
}

export async function getRiskHistory(
  collectionName: string,
  range: '24h' | '7d' | '30d' = '24h',
  opts?: { limit?: number }
) {
  const params = new URLSearchParams({ range });
  if (opts?.limit != null) params.set('limit', String(opts.limit));

  const res = await fetch(
    `${API_BASE}/api/tanks/${encodeURIComponent(collectionName)}/risk-history?${params.toString()}`
  );
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to fetch risk history for ${collectionName}: ${text}`);
  }
  return res.json();
}

export async function getReadingsHistory(
  collectionName: string,
  range: '24h' | '7d' | '30d' = '24h',
  opts?: { limit?: number }
) {
  const params = new URLSearchParams({ range });
  if (opts?.limit != null) params.set('limit', String(opts.limit));

  const res = await fetch(
    `${API_BASE}/api/tanks/${encodeURIComponent(collectionName)}/readings-history?${params.toString()}`
  );
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to fetch readings history for ${collectionName}: ${text}`);
  }
  return res.json();
}
