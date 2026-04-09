export const API_BASE = (import.meta.env.VITE_API_BASE as string) || 'http://127.0.0.1:8000';

// Map frontend tank IDs to backend collection names
const TANK_ID_MAP: Record<string, string> = {
  // Map frontend Tank A to the backend test collection
  'tank-a': 'tank_1_test',
  'tank-b': 'tank_2',
  'tank-c': 'tank_3',
  'tank-d': 'tank_4',
};

export function mapTankId(frontendId: string) {
  return TANK_ID_MAP[frontendId] ?? frontendId;
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
