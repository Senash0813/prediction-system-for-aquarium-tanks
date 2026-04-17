import { createContext, useContext, useState, ReactNode, useEffect, useRef } from 'react';
import { tanks as initialTanks, Tank, generateTimeSeries, TankStatus } from '@/data/dummyData';
import { saveTankConfig, deleteTankConfig, getTankCollections, getLatestReading, getLatestInsightsByType, getRiskHistory, getReadingsHistory, getTankConfig } from '@/api/client';

interface TankDetails {
  temperatureMin: string; temperatureMax: string;
  phMin: string; phMax: string;
  turbidityMin: string; turbidityMax: string;
  lightMin: string; lightMax: string;
  tdsMin: string; tdsMax: string;
  macAddress: string;
}

interface TanksContextType {
  tanks: Tank[];
  addTank: (name: string, details: TankDetails) => Promise<void>;
  deleteTank: (id: string) => Promise<void>;
}

const TanksContext = createContext<TanksContextType | undefined>(undefined);

export const TanksProvider = ({ children }: { children: ReactNode }) => {
  const [tanks, setTanks] = useState<Tank[]>(initialTanks);
  const [collectionsKey, setCollectionsKey] = useState(0);
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

  // ── Insight-driven status helpers ─────────────────────────────────────────

  // temperature_stability: "alert" → critical, "warning"|"anomaly" → warning, else safe
  const tempStatusFromInsight = (ins: any): TankStatus => {
    const s = typeof ins?.status === 'string' ? ins.status.toLowerCase() : '';
    if (s === 'alert') return 'critical';
    if (s === 'warning' || s === 'anomaly') return 'warning';
    return 'safe';
  };

  // water_chemistry: use ph.severity (0-3) for pH status
  // severity 3 → critical, 2 → warning, ≤1 → safe
  const phStatusFromInsight = (ins: any): TankStatus => {
    const severity = ins?.ph?.severity;
    const num = typeof severity === 'number' ? severity : Number(severity);
    if (!isNaN(num) && num >= 3) return 'critical';
    if (!isNaN(num) && num >= 2) return 'warning';
    // Fallback: use ph.status string
    const s = typeof ins?.ph?.status === 'string' ? ins.ph.status.toLowerCase() : '';
    if (s.includes('critical')) return 'critical';
    if (s.includes('high') || s.includes('low')) return 'warning';
    return 'safe';
  };

  // filter_health: "needs_cleaning" → critical, "warning" → warning, else safe
  const turbidityStatusFromInsight = (ins: any): TankStatus => {
    const s = typeof ins?.status === 'string' ? ins.status.toLowerCase() : '';
    if (s === 'needs_cleaning') return 'critical';
    if (s === 'warning') return 'warning';
    return 'safe';
  };

  // fish_stress_risk: use risk_level field ("HIGH" → critical, "MODERATE" → warning)
  const stressStatusFromInsight = (ins: any): TankStatus => {
    const level = typeof ins?.risk_level === 'string' ? ins.risk_level.toUpperCase() : '';
    if (level === 'HIGH') return 'critical';
    if (level === 'MODERATE') return 'warning';
    return 'safe';
  };

  const worstStatus = (...statuses: TankStatus[]): TankStatus => {
    if (statuses.includes('critical')) return 'critical';
    if (statuses.includes('warning')) return 'warning';
    return 'safe';
  };

  // Extract per-metric statuses from the insights-by-type response.
  // Returns { tempStatus, phStatus, turbStatus, stressStatus, overallStatus, riskScore }
  const deriveStatusesFromInsights = (insightsByType: any) => {
    const list: any[] = Array.isArray(insightsByType?.insights) ? insightsByType.insights : [];

    const byType = (type: string) => list.find((i: any) => i?.insight_type === type) ?? null;

    const tempIns    = byType('temperature_stability');
    const chemIns    = byType('water_chemistry');
    const filterIns  = byType('filter_health');
    const riskIns    = byType('fish_stress_risk');

    const tempStatus   = tempIns   ? tempStatusFromInsight(tempIns)       : 'safe' as TankStatus;
    const phStatus     = chemIns   ? phStatusFromInsight(chemIns)         : 'safe' as TankStatus;
    const turbStatus   = filterIns ? turbidityStatusFromInsight(filterIns) : 'safe' as TankStatus;
    const stressStatus = riskIns   ? stressStatusFromInsight(riskIns)     : 'safe' as TankStatus;
    const overallStatus = worstStatus(tempStatus, phStatus, turbStatus, stressStatus);

    const riskScore = riskIns?.risk_score != null ? Number(riskIns.risk_score) : null;

    return { tempStatus, phStatus, turbStatus, overallStatus, riskScore };
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

  // Per-insight-type severity resolver for notifications.
  // Uses the same type-specific functions as deriveStatusesFromInsights so
  // notification colors always agree with the metric badge colors.
  const severityFromInsight = (ins: any): TankStatus => {
    const type = typeof ins?.insight_type === 'string' ? ins.insight_type : '';
    switch (type) {
      case 'temperature_stability':
        return tempStatusFromInsight(ins);          // alert→critical, warning/anomaly→warning
      case 'water_chemistry': {
        const s = typeof ins?.status === 'string' ? ins.status.toLowerCase() : '';
        if (s === 'alert') return 'critical';
        if (s === 'warning') return 'warning';
        return 'safe';
      }
      case 'filter_health':
        return turbidityStatusFromInsight(ins);     // needs_cleaning→critical, warning→warning
      case 'fish_stress_risk':
        return stressStatusFromInsight(ins);        // HIGH→critical, MODERATE→warning (uses risk_level)
      default:
        return mapInsightStatusToSeverity(ins?.status);
    }
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
          severity: severityFromInsight(ins),
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
            const [reading, insightsByType, tankConfig] = await Promise.all([
              getLatestReading(id).catch(() => null),
              getLatestInsightsByType(id).catch(() => null),
              getTankConfig(id).catch(() => null),
            ]);

            const tempVal = reading && typeof reading.temperature === 'number' ? reading.temperature : Number(reading?.temperature);
            const phVal = reading && typeof reading.ph === 'number' ? reading.ph : Number(reading?.ph);
            const turbVal = reading && (typeof reading.turbidity === 'number')
              ? reading.turbidity
              : (reading && typeof reading.tds === 'number' ? reading.tds : Number(reading?.turbidity ?? reading?.tds));

            return {
              id,
              reading,
              insightsByType,
              tankConfig,
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

            const { tempStatus, phStatus, turbStatus, overallStatus, riskScore } =
              deriveStatusesFromInsights(u.insightsByType);

            const nextRisk = riskScore ?? t.stressScore;

            const safeRanges = u.tankConfig?.safe_ranges ?? {};

            return {
              ...t,
              stressScore: nextRisk,
              status: overallStatus,
              temperature: {
                ...t.temperature,
                value: nextTemp,
                status: tempStatus,
                safeMin: safeRanges.temperature?.min ?? t.temperature.safeMin,
                safeMax: safeRanges.temperature?.max ?? t.temperature.safeMax,
              },
              ph: {
                ...t.ph,
                value: nextPh,
                status: phStatus,
                safeMin: safeRanges.ph?.min ?? t.ph.safeMin,
                safeMax: safeRanges.ph?.max ?? t.ph.safeMax,
              },
              turbidity: {
                ...t.turbidity,
                value: nextTurb,
                status: turbStatus,
                safeMin: safeRanges.turbidity?.min ?? t.turbidity.safeMin,
                safeMax: safeRanges.turbidity?.max ?? t.turbidity.safeMax,
              },
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
        const existingIds = new Set(tanksRef.current.map((t) => t.id));
        const collectionsToFetch = parsed.filter((colName) => !existingIds.has(colName));

        if (collectionsToFetch.length === 0) return;

        // Fetch latest reading and insight for each collection and build tank objects
        Promise.all(
          collectionsToFetch.map(async (colName) => {
            try {
              const [reading, insightsByType, tankConfig] = await Promise.all([
                getLatestReading(colName).catch((e) => {
                  console.warn(`[TanksContext] reading fetch failed for ${colName}:`, e); return null;
                }),
                getLatestInsightsByType(colName).catch((e) => {
                  console.warn(`[TanksContext] insights-by-type fetch failed for ${colName}:`, e); return null;
                }),
                getTankConfig(colName).catch((e) => {
                  console.warn(`[TanksContext] tank config fetch failed for ${colName}:`, e); return null;
                }),
              ]);

              const tempVal = reading && typeof reading.temperature === 'number' ? reading.temperature : Number(reading?.temperature || 0);
              const phVal = reading && typeof reading.ph === 'number' ? reading.ph : Number(reading?.ph || 0);
              const turbVal = reading && (typeof reading.turbidity === 'number')
                ? reading.turbidity
                : (reading && typeof reading.tds === 'number' ? reading.tds : Number(reading?.turbidity ?? reading?.tds ?? 0));

              const id = colName;
              const prettyName = colName.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase());

              const { tempStatus, phStatus, turbStatus, overallStatus, riskScore } =
                deriveStatusesFromInsights(insightsByType);

              const computedScore = Math.round((phVal + tempVal + turbVal) / 3);
              const safeRanges = tankConfig?.safe_ranges ?? {};

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
                status: overallStatus,
                insight: 'Auto-discovered tank from DB',
                temperature: {
                  value: tempVal,
                  status: tempStatus,
                  unit: '°C',
                  trend: 'stable',
                  label: 'Temperature',
                  safeMin: safeRanges.temperature?.min,
                  safeMax: safeRanges.temperature?.max,
                },
                ph: {
                  value: phVal,
                  status: phStatus,
                  unit: '',
                  trend: '↔',
                  label: 'pH Level',
                  safeMin: safeRanges.ph?.min,
                  safeMax: safeRanges.ph?.max,
                },
                turbidity: {
                  value: turbVal,
                  status: turbStatus,
                  unit: 'NTU',
                  trend: 'stable',
                  label: 'Turbidity',
                  safeMin: safeRanges.turbidity?.min,
                  safeMax: safeRanges.turbidity?.max,
                },
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
                temperature: { value: tempBase, status: 'safe' as TankStatus, unit: '°C', trend: 'stable', label: 'Temperature' },
                ph: { value: phBase, status: 'safe' as TankStatus, unit: '', trend: '↔', label: 'pH Level' },
                turbidity: { value: turbBase, status: 'safe' as TankStatus, unit: 'NTU', trend: 'stable', label: 'Turbidity' },
                stressHistory: generateTimeSeries(20 + idxFallback * 5, 4, 24),
                temperatureHistory: generateTimeSeries(tempBase, 0.8, 24),
                phHistory: generateTimeSeries(phBase, 0.2, 24),
                turbidityHistory: generateTimeSeries(turbBase, 0.5, 24),
                notifications: [
                  { id: `${colName}-n1`, en: 'No recent reading available.', si: 'සමීප කියවීමක් නොමැත.', severity: 'warning' as TankStatus, timestamp: 'N/A' },
                ],
              } as Tank;
            }
          })
        ).then((fetchedTanks) => {
          if (!mounted) return;
          if (fetchedTanks.length) {
            setTanks((prev) => [...prev, ...fetchedTanks]);
          }
        });
      })
      .catch((err) => console.error('[TanksContext] Failed to fetch collections:', err));
    return () => {
      mounted = false;
    };
  }, [collectionsKey]);

  const addTank = async (name: string, details: TankDetails) => {
    await saveTankConfig({
      tank_id: name,
      mac_address: details.macAddress,
      safe_ranges: {
        temperature: { min: parseFloat(details.temperatureMin), max: parseFloat(details.temperatureMax) },
        ph:          { min: parseFloat(details.phMin),          max: parseFloat(details.phMax)          },
        turbidity:   { min: parseFloat(details.turbidityMin),   max: parseFloat(details.turbidityMax)   },
        light:       { min: parseFloat(details.lightMin),       max: parseFloat(details.lightMax)       },
        tds:         { min: parseFloat(details.tdsMin),         max: parseFloat(details.tdsMax)         },
      },
    });

    // Re-run the collection fetch after a short delay so the new tank_<n>
    // collection created by the backend is discovered and added to state.
    setTimeout(() => setCollectionsKey(k => k + 1), 1000);
  };

  const deleteTank = async (id: string) => {
    await deleteTankConfig(id);
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
