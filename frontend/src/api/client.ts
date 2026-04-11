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
