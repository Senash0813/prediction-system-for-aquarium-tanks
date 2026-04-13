import { createContext, useContext, useState, ReactNode, useEffect, useRef } from 'react';
import { tanks as initialTanks, Tank, generateTimeSeries, TankStatus } from '@/data/dummyData';
import { saveTankConfig, getTankCollections, getLatestReading, getLatestInsightsByType, getLatestRiskInsight, getRiskHistory, getReadingsHistory } from '@/api/client';

interface TankDetails {
  temperatureMin: string; temperatureMax: string;
  phMin: string; phMax: string;
  turbidityMin: string; turbidityMax: string;
  lightMin: string; lightMax: string;
  tdsMin: string; tdsMax: string;
}

interface TanksContextType {
  tanks: Tank[];
  addTank: (name: string, details: TankDetails) => void;
  deleteTank: (id: string) => void;
}

const TanksContext = createContext<TanksContextType | undefined>(undefined);

export const TanksProvider = ({ children }: { children: ReactNode }) => {
  const [tanks, setTanks] = useState<Tank[]>(initialTanks);
  const tanksRef = useRef<Tank[]>(initialTanks);
  const refreshInFlightRef = useRef(false);

  useEffect(() => {
    tanksRef.current = tanks;
  }, [tanks]);

  const mapInsightStatusToSeverity = (status: any): TankStatus => {
    const s = typeof status === 'string' ? status.toLowerCase() : '';
    if (s.includes('critical') || s.includes('danger') || s.includes('high')) return 'critical';
    if (s.includes('warn')) return 'warning';
    return 'safe';
  };

  const formatBackendTimestampUtc = (ts: any): string => {
    if (!ts) return '';
    const raw = String(ts);
    const d = new Date(raw);
    if (isNaN(d.getTime())) return raw;
    // Backend timestamps are ISO w/ timezone; render in UTC to avoid date shifting.
    return d.toLocaleString(undefined, {
      month: '2-digit',
      day: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'UTC',
    });
  };

  const buildNotificationsFromInsights = (tankId: string, insightsByType: any, fallbackTs?: any) => {
    const list = Array.isArray(insightsByType?.insights) ? insightsByType.insights : [];
    const mapped = list
      .map((ins: any, i: number) => {
        const kind = typeof ins?.insight_type === 'string' ? ins.insight_type : undefined;
        const msg = ins?.message != null ? String(ins.message) : '';
        const generatedAt = ins?.generated_at;
        if (!kind && !msg) return null;
        const text = kind ? `${kind}: ${msg || ''}`.trim() : msg;
        return {
          id: `${tankId}-ins-${i}-${kind ?? 'insight'}`,
          kind,
          en: text,
          si: text,
          severity: mapInsightStatusToSeverity(ins?.status),
          timestamp: formatBackendTimestampUtc(generatedAt),
        };
      })
      .filter(Boolean);

    if (mapped.length) return mapped as any;
    return [
      {
        id: `${tankId}-n1`,
        en: 'Live reading from backend.',
        si: 'පසුබැසිනෙන් එන සජීවී කියවීම.',
        severity: 'safe' as TankStatus,
        timestamp: formatBackendTimestampUtc(fallbackTs || Date.now()),
      },
    ];
  };

  // Periodically refresh DB tank values so UI matches MongoDB (values + notifications).
  useEffect(() => {
    let cancelled = false;

    const refreshDbTanks = async () => {
      if (refreshInFlightRef.current) return;
      refreshInFlightRef.current = true;
      try {
        const ids = tanksRef.current.map(t => t.id).filter(id => /^tank_\d+$/.test(id));
        if (!ids.length) return;

        const results = await Promise.all(
          ids.map(async (id) => {
            const [reading, riskInsight, insightsByType] = await Promise.all([
              getLatestReading(id).catch(() => null),
              getLatestRiskInsight(id).catch(() => null),
              getLatestInsightsByType(id).catch(() => null),
            ]);

            const tempVal = reading && typeof reading.temperature === 'number' ? reading.temperature : Number(reading?.temperature);
            const phVal = reading && typeof reading.ph === 'number' ? reading.ph : Number(reading?.ph);
            const turbVal = reading && (typeof reading.turbidity === 'number')
              ? reading.turbidity
              : (reading && typeof reading.tds === 'number' ? reading.tds : Number(reading?.turbidity ?? reading?.tds));

            let riskScore: number | null = null;
            if (riskInsight && ('risk_score' in riskInsight)) {
              const raw = (riskInsight as any).risk_score;
              const parsed = typeof raw === 'number' ? raw : Number(raw);
              if (!isNaN(parsed)) riskScore = parsed;
            }

            return {
              id,
              reading,
              riskScore,
              insightsByType,
              tempVal: isNaN(tempVal) ? null : tempVal,
              phVal: isNaN(phVal) ? null : phVal,
              turbVal: isNaN(turbVal) ? null : turbVal,
            };
          })
        );

        if (cancelled) return;

        const updatesById = new Map(results.map(r => [r.id, r]));
        setTanks((prev) =>
          prev.map((t) => {
            const u = updatesById.get(t.id);
            if (!u) return t;

            const nextTemp = u.tempVal ?? t.temperature.value;
            const nextPh = u.phVal ?? t.ph.value;
            const nextTurb = u.turbVal ?? t.turbidity.value;
            const nextRisk = u.riskScore ?? t.stressScore;

            return {
              ...t,
              stressScore: nextRisk,
              temperature: { ...t.temperature, value: nextTemp },
              ph: { ...t.ph, value: nextPh },
              turbidity: { ...t.turbidity, value: nextTurb },
              notifications: buildNotificationsFromInsights(t.id, u.insightsByType, u.reading?.timestamp),
            };
          })
        );
      } finally {
        refreshInFlightRef.current = false;
      }
    };

    refreshDbTanks();
    const interval = window.setInterval(refreshDbTanks, 30000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  // Fetch backend collections that start with `tank_` and append enough
  // DB tanks to reach 7 tanks total (keeps Tank A-D unchanged)
  useEffect(() => {
    let mounted = true;
    getTankCollections()
      .then((data) => {
        if (!mounted) return;
        const collections: string[] = data.tanks || [];

        // Pick collections that look like 'tank_<number>' and sort numerically
        const parsed = collections
          .filter((c) => /^tank_\d+$/.test(c))
          .sort((a, b) => {
            const na = parseInt(a.split('_')[1], 10);
            const nb = parseInt(b.split('_')[1], 10);
            return (isNaN(na) ? 1 : na) - (isNaN(nb) ? 1 : nb);
          });

        // Build Tank objects for all parsed collections but avoid duplicates
        const existingIds = new Set(initialTanks.map((t) => t.id));
        const collectionsToFetch = parsed.filter((colName) => !existingIds.has(colName));

        if (collectionsToFetch.length === 0) return;

        // Fetch latest reading and insight for each collection and build tank objects
        Promise.all(
          collectionsToFetch.map(async (colName, idx) => {
            try {
              const [reading, riskInsight, insightsByType] = await Promise.all([
                getLatestReading(colName).catch((e) => {
                  console.warn(`[TanksContext] reading fetch failed for ${colName}:`, e); return null;
                }),
                getLatestRiskInsight(colName).catch((e) => {
                  console.warn(`[TanksContext] risk insight fetch failed for ${colName}:`, e); return null;
                }),
                getLatestInsightsByType(colName).catch((e) => {
                  console.warn(`[TanksContext] insights-by-type fetch failed for ${colName}:`, e); return null;
                }),
              ]);

              const tempVal = reading && typeof reading.temperature === 'number' ? reading.temperature : Number(reading?.temperature || 0);
              const phVal = reading && typeof reading.ph === 'number' ? reading.ph : Number(reading?.ph || 0);
              const turbVal = reading && (typeof reading.turbidity === 'number')
                ? reading.turbidity
                : (reading && typeof reading.tds === 'number' ? reading.tds : Number(reading?.turbidity ?? reading?.tds ?? 0));

              const id = colName;
              const prettyName = colName.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase());

              // Parse risk score from insight if available (allow numeric strings)
              let riskScore: number | null = null;
              if (riskInsight && ('risk_score' in riskInsight)) {
                const raw = riskInsight.risk_score;
                const parsed = typeof raw === 'number' ? raw : Number(raw);
                if (!isNaN(parsed)) riskScore = parsed;
              }

              const computedScore = Math.round((phVal + tempVal + turbVal) / 3);

              // Fetch risk score series for the stress chart
              let stressHistory = generateTimeSeries(riskScore ?? computedScore, 4, 24);
              try {
                const series = await getRiskHistory(colName, '24h', { limit: 5000 });
                const pts = Array.isArray(series?.points) ? series.points : [];
                const mapped = pts
                  .map((p: any) => {
                    const v = typeof p.value === 'number' ? p.value : Number(p.value);
                    if (isNaN(v)) return null;
                    return { time: String(p.timestamp), value: v, _iso: String(p.timestamp) };
                  })
                  .filter(Boolean);
                if (mapped.length) stressHistory = mapped as any;
              } catch (e) {
                console.warn(`[TanksContext] risk history fetch failed for ${colName}:`, e);
              }

              // Fetch readings series for temperature + turbidity charts
              let temperatureHistory = generateTimeSeries(tempVal, 0.8, 24);
              let phHistory = generateTimeSeries(phVal, 0.2, 24);
              let turbidityHistory = generateTimeSeries(turbVal, 0.5, 24);
              try {
                const series = await getReadingsHistory(colName, '24h');
                const pts = Array.isArray(series?.points) ? series.points : [];

                const toIso = (ts: any) => String(ts);

                const mappedTemp = pts
                  .map((p: any) => {
                    const v = typeof p.temperature === 'number' ? p.temperature : Number(p.temperature);
                    if (isNaN(v)) return null;
                    const iso = toIso(p.timestamp);
                    return { time: iso, value: v, _iso: iso };
                  })
                  .filter(Boolean);

                const mappedPh = pts
                  .map((p: any) => {
                    const v = typeof p.ph === 'number' ? p.ph : Number(p.ph);
                    if (isNaN(v)) return null;
                    const iso = toIso(p.timestamp);
                    return { time: iso, value: v, _iso: iso };
                  })
                  .filter(Boolean);

                const mappedTurb = pts
                  .map((p: any) => {
                    const v = typeof p.turbidity === 'number' ? p.turbidity : Number(p.turbidity);
                    if (isNaN(v)) return null;
                    const iso = toIso(p.timestamp);
                    return { time: iso, value: v, _iso: iso };
                  })
                  .filter(Boolean);

                if (mappedTemp.length) temperatureHistory = mappedTemp as any;
                if (mappedPh.length) phHistory = mappedPh as any;
                if (mappedTurb.length) turbidityHistory = mappedTurb as any;
              } catch (e) {
                console.warn(`[TanksContext] readings history fetch failed for ${colName}:`, e);
              }

              const notifications = buildNotificationsFromInsights(id, insightsByType, reading?.timestamp);

              const tank: Tank = {
                id,
                name: prettyName,
                stressScore: riskScore ?? computedScore,
                status: 'safe' as TankStatus,
                insight: 'Auto-discovered tank from DB',
                temperature: { value: tempVal, status: 'safe', unit: '°C', trend: 'stable', label: 'Temperature' },
                ph: { value: phVal, status: 'safe', unit: '', trend: '↔', label: 'pH Level' },
                turbidity: { value: turbVal, status: 'safe', unit: 'NTU', trend: 'stable', label: 'Turbidity' },
                stressHistory,
                temperatureHistory,
                phHistory,
                turbidityHistory,
                notifications,
              };

              return tank;
            } catch (err) {
              console.error(`[TanksContext] failed to build tank for ${colName}:`, err);
              const idxFallback = collectionsToFetch.indexOf(colName);
              const tempBase = 24 + idxFallback;
              const phBase = 7 + idxFallback * 0.2;
              const turbBase = 2 + idxFallback * 0.5;
              return {
                id: colName,
                name: colName.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
                stressScore: 20 + idxFallback * 5,
                status: 'safe' as TankStatus,
                insight: 'Auto-discovered tank (no recent reading)',
                temperature: { value: tempBase, status: 'safe', unit: '°C', trend: 'stable', label: 'Temperature' },
                ph: { value: phBase, status: 'safe', unit: '', trend: '↔', label: 'pH Level' },
                turbidity: { value: turbBase, status: 'safe', unit: 'NTU', trend: 'stable', label: 'Turbidity' },
                stressHistory: generateTimeSeries(20 + idxFallback * 5, 4, 24),
                temperatureHistory: generateTimeSeries(tempBase, 0.8, 24),
                phHistory: generateTimeSeries(phBase, 0.2, 24),
                turbidityHistory: generateTimeSeries(turbBase, 0.5, 24),
                notifications: [
                  { id: `${colName}-n1`, en: 'No recent reading available.', si: 'සමීප කියවීමක් නොමැත.', severity: 'warning', timestamp: 'N/A' },
                ],
              } as Tank;
            }
          })
        ).then((fetchedTanks) => {
          if (!mounted) return;
          if (fetchedTanks.length) {
            setTanks((prev) => {
              const merged = [...prev, ...fetchedTanks];
              return merged;
            });

            // Ensure we definitely pick up the latest insight values by updating
            // any `tank_` entries' stressScore after initial append.
            const allDbTankIds = fetchedTanks.map(t => t.id).filter(id => /^tank_\d+$/.test(id));
            if (allDbTankIds.length) {
              Promise.all(allDbTankIds.map(async (col) => {
                try {
                  const insight = await getLatestRiskInsight(col).catch(() => null);
                  if (insight && ('risk_score' in insight)) {
                    const raw = insight.risk_score;
                    const parsed = typeof raw === 'number' ? raw : Number(raw);
                    return { id: col, risk: isNaN(parsed) ? null : parsed };
                  }
                  return { id: col, risk: null };
                } catch (e) {
                  return { id: col, risk: null };
                }
              })).then((insights) => {
                setTanks((prev) => prev.map(t => {
                  const found = insights.find(i => i.id === t.id && i.risk !== null);
                  if (found) return { ...t, stressScore: found.risk };
                  return t;
                }));
              }).catch((e) => console.warn('[TanksContext] failed to refresh insights:', e));
            }
          }
        });
      })
      .catch((err) => console.error('[TanksContext] Failed to fetch collections:', err));
    return () => {
      mounted = false;
    };
  }, []);

  const addTank = (name: string, details: TankDetails) => {
    const id = `tank-${name.toLowerCase().replace(/\s+/g, '-')}-${Date.now()}`;
    const tempMin = parseFloat(details.temperatureMin);
    const tempMax = parseFloat(details.temperatureMax);
    const phMin = parseFloat(details.phMin);
    const phMax = parseFloat(details.phMax);
    const turbMin = parseFloat(details.turbidityMin);
    const turbMax = parseFloat(details.turbidityMax);
    const tempMid = (tempMin + tempMax) / 2;
    const phMid = (phMin + phMax) / 2;
    const turbMid = (turbMin + turbMax) / 2;

    const newTank: Tank = {
      id,
      name,
      stressScore: 10,
      status: 'safe' as TankStatus,
      insight: 'New tank – monitoring started',
      temperature: { value: tempMid, status: 'safe', unit: '°C', trend: 'stable', label: 'Temperature', safeMin: tempMin, safeMax: tempMax },
      ph: { value: phMid, status: 'safe', unit: '', trend: '↔', label: 'pH Level', safeMin: phMin, safeMax: phMax },
      turbidity: { value: turbMid, status: 'safe', unit: 'NTU', trend: 'stable', label: 'Turbidity', safeMin: turbMin, safeMax: turbMax },
      stressHistory: generateTimeSeries(10, 3, 24),
      temperatureHistory: generateTimeSeries(tempMid, 0.5, 24),
      phHistory: generateTimeSeries(phMid, 0.15, 24),
      turbidityHistory: generateTimeSeries(turbMid, 0.3, 24),
      notifications: [
        { id: `${id}-n1`, en: 'Tank created. Monitoring has begun.', si: 'ටැංකිය සාදන ලදී. නිරීක්ෂණය ආරම්භ කර ඇත.', severity: 'safe', timestamp: 'Just now' },
      ],
    };
    setTanks(prev => [...prev, newTank]);

    saveTankConfig({
      tank_id: name,
      safe_ranges: {
        temperature: { min: tempMin, max: tempMax },
        ph:          { min: phMin,   max: phMax   },
        turbidity:   { min: turbMin, max: turbMax  },
        light:       { min: parseFloat(details.lightMin), max: parseFloat(details.lightMax) },
        tds:         { min: parseFloat(details.tdsMin),   max: parseFloat(details.tdsMax)   },
      },
    }).catch(err => console.error('[TanksContext] Failed to save tank config:', err));
  };

  const deleteTank = (id: string) => {
    setTanks(prev => prev.filter(t => t.id !== id));
  };

  return (
    <TanksContext.Provider value={{ tanks, addTank, deleteTank }}>
      {children}
    </TanksContext.Provider>
  );
};

export const useTanks = () => {
  const ctx = useContext(TanksContext);
  if (!ctx) throw new Error('useTanks must be used within TanksProvider');
  return ctx;
};
