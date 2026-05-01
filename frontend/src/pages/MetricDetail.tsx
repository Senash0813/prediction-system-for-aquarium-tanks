import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, TrendingUp, TrendingDown, Minus, MessageCircle } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine, ReferenceArea } from 'recharts';
import { getMetricData, generateData, metricLabels } from '@/data/dummyData';
import { getPhAnalysis, getRiskHistory, getReadingsHistory } from '@/api/client';
import { useTanks } from '@/context/TanksContext';
import { useChatContext } from '@/components/chatbot/ChatContext';

type TimeRange = '24h' | '7d' | '30d';

const ZONE_METRICS = new Set(['ph', 'temperature', 'turbidity']);

const FALLBACK_SAFE_RANGES: Record<string, { min: number; max: number }> = {
  ph:          { min: 6.5, max: 8.5 },
  temperature: { min: 22,  max: 28  },
  turbidity:   { min: 0,   max: 5   },
};

const CRITICAL_EXTREMES: Record<string, { min: number; max: number }> = {
  ph:          { min: 5.5, max: 9.5  },
  temperature: { min: 15,  max: 35   },
  turbidity:   { min: 0,   max: 20   },
};

const classifyWithRanges = (value: number, metric: string, sMin: number, sMax: number): 'safe' | 'warn' | 'crit' => {
  if (value >= sMin && value <= sMax) return 'safe';
  const ext = CRITICAL_EXTREMES[metric];
  if (ext && (value < ext.min || value > ext.max)) return 'crit';
  return 'warn';
};

const MetricDetail = () => {
  const { tankId, metricId } = useParams<{ tankId: string; metricId: string }>();
  const [range, setRange] = useState<TimeRange>('24h');
  const { tanks } = useTanks();
  const { setPageContext } = useChatContext();

  const tank = tanks.find(t => t.id === (tankId || ''));
  if (!tank || !metricId) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20">
        <p className="text-lg text-muted-foreground">Metric not found</p>
        <Link to="/" className="text-primary underline">Back to dashboard</Link>
      </div>
    );
  }

  const { info } = getMetricData(tank, metricId);
  const label = metricLabels[metricId] || metricId;

  const baseValue = info.value;
  const variance = metricId === 'stress' ? 10 : metricId === 'temperature' ? 1.5 : metricId === 'ph' ? 0.3 : 1;
  const chartData = generateData(baseValue, variance, range);

  const chartColor = 'hsl(217, 91%, 60%)';

  const isIsoLike = (v: any) => {
    if (typeof v !== 'string') return false;
    return /^\d{4}-\d{2}-\d{2}T/.test(v) || v.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(v);
  };

  const formatAxisTimeTick = (ts: any) => {
    if (ts == null) return '';
    const d = new Date(ts);
    if (isNaN(d.getTime())) return String(ts);
    const useUtc = isIsoLike(ts);

    if (range === '24h') {
      return d.toLocaleString(undefined, {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        ...(useUtc ? { timeZone: 'UTC' as const } : {}),
      });
    }

    // For 7d/30d, keep ticks short (date only) to avoid label collisions.
    return d.toLocaleDateString(undefined, {
      month: '2-digit',
      day: '2-digit',
      ...(useUtc ? { timeZone: 'UTC' as const } : {}),
    });
  };

  const formatAxisTimeTooltip = (ts: any) => {
    if (ts == null) return '';
    const d = new Date(ts);
    if (isNaN(d.getTime())) return String(ts);
    const useUtc = isIsoLike(ts);
    return d.toLocaleString(undefined, {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      ...(useUtc ? { timeZone: 'UTC' as const } : {}),
    });
  };

  const formatAxisValue = (v: any) => (info.unit ? `${v}${info.unit}` : String(v));

  // API-backed values
  const [apiData, setApiData] = useState<any | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function fetchData() {
      try {
        // pH metric uses water chemistry API
        if (metricId === 'ph') {
          // DB tanks (tank_1, tank_2, ...) read pH directly from readings history
          if (/^tank_\d+$/.test(tank.id)) {
            const limit = range === '30d' ? 50000 : range === '7d' ? 20000 : 5000;
            const resp = await getReadingsHistory(tank.id, range, { limit });
            if (!mounted) return;
            setApiData(resp);
            setApiError(null);
            return;
          }

          const resp = await getPhAnalysis(tank.id, range);
          if (!mounted) return;
          setApiData(resp);
          setApiError(null);
          return;
        }

        // Stress metric for DB-discovered tanks (tank_1, tank_2, ...) uses generated insights risk history
        if (metricId === 'stress' && /^tank_\d+$/.test(tank.id)) {
          const limit = range === '30d' ? 50000 : range === '7d' ? 20000 : 5000;
          const resp = await getRiskHistory(tank.id, range, { limit });
          if (!mounted) return;
          setApiData(resp);
          setApiError(null);
          return;
        }

        // Temperature/Turbidity for DB tanks uses readings history from aqua_gaurd_db
        if ((metricId === 'temperature' || metricId === 'turbidity') && /^tank_\d+$/.test(tank.id)) {
          const limit = range === '30d' ? 50000 : range === '7d' ? 20000 : 5000;
          const resp = await getReadingsHistory(tank.id, range, { limit });
          if (!mounted) return;
          setApiData(resp);
          setApiError(null);
          return;
        }

        // Other metrics fall back to dummy data
        if (!mounted) return;
        setApiData(null);
        setApiError(null);
      } catch (e: any) {
        if (!mounted) return;
        setApiError(e.message || 'Failed to fetch');
        setApiData(null);
      }
    }
    fetchData();
    return () => { mounted = false; };
  }, [tank.id, metricId, range]);

  // Prefer API chart points when available. Map backend keys to {time, value}.
  const chartPoints = (() => {
    // pH analysis response
    if (apiData?.chart_points) {
      return apiData.chart_points.map((p: any) => ({
        time: p.timestamp_iso ?? p.timestamp ?? p.label ?? p.time,
        value: p.ph ?? p.value,
        _iso: p.timestamp_iso ?? p.timestamp,
      }));
    }

    // Stress risk history response
    if (metricId === 'stress' && Array.isArray(apiData?.points)) {
      return apiData.points.map((p: any) => {
        return {
          time: String(p.timestamp),
          value: typeof p.value === 'number' ? p.value : Number(p.value),
          _iso: p.timestamp,
        };
      }).filter((p: any) => !isNaN(p.value));
    }

    // Readings history response (temperature/turbidity/ph)
    if ((metricId === 'temperature' || metricId === 'turbidity' || metricId === 'ph') && Array.isArray(apiData?.points)) {
      const key = metricId;
      return apiData.points.map((p: any) => {
        const time = String(p.timestamp);
        const raw = key === 'turbidity' ? p?.turbidity : key === 'temperature' ? p?.temperature : p?.ph;
        const value = typeof raw === 'number' ? raw : Number(raw);
        return { time, value, _iso: p.timestamp };
      }).filter((p: any) => !isNaN(p.value));
    }

    return chartData.map(d => ({ time: d.time, value: d.value }));
  })();

  const hasZoneSupport = metricId != null && ZONE_METRICS.has(metricId);

  const effectiveSafeMin = info.safeMin ?? (metricId ? FALLBACK_SAFE_RANGES[metricId]?.min : undefined);
  const effectiveSafeMax = info.safeMax ?? (metricId ? FALLBACK_SAFE_RANGES[metricId]?.max : undefined);

  const crossingIndices = (() => {
    const indices = new Set<number>();
    if (effectiveSafeMin == null || effectiveSafeMax == null || chartPoints.length < 2) return indices;
    const inRange = (v: number) => v >= effectiveSafeMin! && v <= effectiveSafeMax!;
    for (let i = 1; i < chartPoints.length; i++) {
      if (inRange(chartPoints[i].value) !== inRange(chartPoints[i - 1].value)) {
        indices.add(i - 1);
        indices.add(i);
      }
    }
    return indices;
  })();

  const zoneCounts = (() => {
    if (!hasZoneSupport || effectiveSafeMin == null || effectiveSafeMax == null || chartPoints.length === 0) return null;
    let safe = 0, warn = 0, crit = 0;
    for (const p of chartPoints) {
      const z = classifyWithRanges(p.value, metricId!, effectiveSafeMin, effectiveSafeMax);
      if (z === 'safe') safe++;
      else if (z === 'warn') warn++;
      else crit++;
    }
    const total = chartPoints.length;
    return {
      safe: { count: safe, pct: Math.round((safe / total) * 100) },
      warn: { count: warn, pct: Math.round((warn / total) * 100) },
      crit: { count: crit, pct: Math.round((crit / total) * 100) },
    };
  })();

  const periodComparison = (() => {
    if (!hasZoneSupport || effectiveSafeMin == null || effectiveSafeMax == null || chartPoints.length < 4) return null;
    const mid = Math.floor(chartPoints.length / 2);
    const prev = chartPoints.slice(0, mid);
    const curr = chartPoints.slice(mid);
    const prevAvg = +(prev.reduce((s: number, p: any) => s + p.value, 0) / prev.length).toFixed(2);
    const currAvg = +(curr.reduce((s: number, p: any) => s + p.value, 0) / curr.length).toFixed(2);
    const delta = +(currAvg - prevAvg).toFixed(2);
    const safeCenter = (effectiveSafeMin + effectiveSafeMax) / 2;
    const improving = Math.abs(currAvg - safeCenter) < Math.abs(prevAvg - safeCenter);
    return { prevAvg, currAvg, delta, improving };
  })();

  const halfLabel = range === '24h' ? '12 hours' : range === '7d' ? '3.5 days' : '15 days';

  const isStress = metricId === 'stress';

  const stressZones = (() => {
    if (!isStress || chartPoints.length === 0) return null;
    let low = 0, moderate = 0, high = 0;
    for (const p of chartPoints) {
      if (p.value <= 40) low++;
      else if (p.value <= 70) moderate++;
      else high++;
    }
    const total = chartPoints.length;
    return {
      low:      { count: low,      pct: Math.round((low      / total) * 100) },
      moderate: { count: moderate, pct: Math.round((moderate / total) * 100) },
      high:     { count: high,     pct: Math.round((high     / total) * 100) },
    };
  })();

  const { setIsChatOpen, setPendingMessage } = useChatContext();

  const values = chartPoints.map(p => p.value);
  const avgValue = values.length
    ? +(values.reduce((s, v) => s + v, 0) / values.length).toFixed(2)
    : +(chartData.reduce((s, p) => s + p.value, 0) / chartData.length).toFixed(2);
  const maxValue = values.length ? Math.max(...values) : Math.max(...chartData.map(p => p.value));
  const minValue = values.length ? Math.min(...values) : Math.min(...chartData.map(p => p.value));
  const currentValue = values.length ? values[values.length - 1] : (apiData?.current ?? info.value);

  const trendDir = apiData?.trend
    ? (apiData.trend === 'Rising' ? 'up' : apiData.trend === 'Falling' ? 'down' : 'flat')
    : (
      values.length > 1 && values[values.length - 1] > values[values.length - 2] ? 'up' :
      values.length > 1 && values[values.length - 1] < values[values.length - 2] ? 'down' : 'flat'
    );

  useEffect(() => {
    setPageContext({
      page: 'metric_detail',
      tankId: tank.id,
      tankName: tank.name,
      metricDetail: {
        metric: label,
        current: currentValue,
        average: avgValue,
        min: minValue,
        max: maxValue,
        trend: trendDir === 'up' ? 'Rising' : trendDir === 'down' ? 'Falling' : 'Stable',
        status: info.status,
        unit: info.unit ?? '',
        timeRange: range,
      },
    });
    return () => setPageContext(null);
  }, [tank.id, metricId, range, currentValue, avgValue, minValue, maxValue, trendDir, info.status, setPageContext]);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center gap-3">
        <Link to={`/tank/${tank.id}`} className="rounded-lg p-2 hover:bg-muted transition-colors">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-foreground">{tank.name} – {label}</h1>
          <p className="text-sm text-muted-foreground">Detailed analysis and trends</p>
        </div>
      </div>

      {/* Time Range Selector */}
      <div className="flex gap-2">
        {(['24h', '7d', '30d'] as TimeRange[]).map(r => (
          <button
            key={r}
            onClick={() => setRange(r)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              range === r ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'
            }`}
          >
            {r === '24h' ? '24 Hours' : r === '7d' ? '7 Days' : '30 Days'}
          </button>
        ))}
      </div>

      {/* Large Chart */}
      <div className="rounded-xl border bg-card p-6 shadow-sm">
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={chartPoints} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
              interval="preserveStartEnd"
              tickFormatter={(v) => formatAxisTimeTick(v)}
              minTickGap={24}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
              tickFormatter={formatAxisValue}
              tickLine={false}
              axisLine={false}
              domain={
                isStress ? [0, 100] :
                effectiveSafeMin != null && effectiveSafeMax != null
                  ? [
                      (dataMin: number) => +Math.min(dataMin, effectiveSafeMin! * (effectiveSafeMin! >= 0 ? 0.97 : 1.03)).toFixed(2),
                      (dataMax: number) => +Math.max(dataMax, effectiveSafeMax! * (effectiveSafeMax! >= 0 ? 1.03 : 0.97)).toFixed(2),
                    ]
                  : ['auto', 'auto']
              }
            />
            {effectiveSafeMin != null && effectiveSafeMax != null && (
              <ReferenceArea
                y1={effectiveSafeMin}
                y2={effectiveSafeMax}
                fill="hsl(152, 60%, 42%)"
                fillOpacity={0.08}
                stroke="hsl(152, 60%, 42%)"
                strokeOpacity={0.3}
                strokeDasharray="4 2"
              />
            )}
            {isStress && (
              <ReferenceLine y={40} stroke="hsl(38, 92%, 50%)" strokeDasharray="5 3" strokeWidth={1.5}
                label={{ value: 'Moderate', position: 'insideTopRight', fontSize: 10, fill: 'hsl(38, 92%, 50%)' }} />
            )}
            {isStress && (
              <ReferenceLine y={70} stroke="hsl(0, 72%, 55%)" strokeDasharray="5 3" strokeWidth={1.5}
                label={{ value: 'High', position: 'insideTopRight', fontSize: 10, fill: 'hsl(0, 72%, 55%)' }} />
            )}
            <ReferenceLine y={avgValue} stroke="hsl(var(--muted-foreground))" strokeDasharray="6 3" opacity={0.5} />
            <Tooltip
              contentStyle={{
                background: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              labelFormatter={(label: any) => formatAxisTimeTooltip(label)}
              formatter={(value: number) => [`${value}${info.unit}`, label]}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={chartColor}
              strokeWidth={2.5}
              activeDot={{ r: 5, fill: chartColor }}
              dot={(dotProps: any) => {
                const { cx, cy, index } = dotProps;
                if (!crossingIndices.has(index)) return <g key={index} />;
                const v = chartPoints[index]?.value;
                const isAbove = effectiveSafeMax != null && v > effectiveSafeMax;
                const dotColor = isAbove || (effectiveSafeMin != null && v < effectiveSafeMin)
                  ? (info.status === 'critical' ? 'hsl(0, 72%, 55%)' : 'hsl(38, 92%, 50%)')
                  : chartColor;
                return <circle key={index} cx={cx} cy={cy} r={4} fill={dotColor} stroke="hsl(var(--card))" strokeWidth={1.5} />;
              }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <div className="rounded-xl border bg-card p-4 shadow-sm">
          <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Current</p>
          <p className="mt-1 text-xl font-bold text-foreground">{currentValue}{info.unit}</p>
        </div>
        <div className="rounded-xl border bg-card p-4 shadow-sm">
          <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Average</p>
          <p className="mt-1 text-xl font-bold text-foreground">{avgValue}{info.unit}</p>
        </div>
        <div className="rounded-xl border bg-card p-4 shadow-sm">
          <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Min / Max</p>
          <p className="mt-1 text-xl font-bold text-foreground">{minValue.toFixed(1)} – {maxValue.toFixed(1)}</p>
        </div>
        <div className="rounded-xl border bg-card p-4 shadow-sm">
          <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Trend</p>
          <div className="mt-1 flex items-center gap-1.5">
            {trendDir === 'up' ? <TrendingUp className="h-5 w-5 text-warning" /> :
             trendDir === 'down' ? <TrendingDown className="h-5 w-5 text-primary" /> :
             <Minus className="h-5 w-5 text-safe" />}
            <span className="text-sm font-medium capitalize">{trendDir === 'up' ? 'Rising' : trendDir === 'down' ? 'Falling' : 'Stable'}</span>
          </div>
        </div>
      </div>

      {/* Time in Zone */}
      {zoneCounts && (
        <div className="rounded-xl border bg-card p-6 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold text-card-foreground">Time in Zone</h3>
          <div className="flex h-2.5 w-full overflow-hidden rounded-full">
            {zoneCounts.safe.pct > 0 && (
              <div style={{ width: `${zoneCounts.safe.pct}%` }} className="bg-safe" />
            )}
            {zoneCounts.warn.pct > 0 && (
              <div style={{ width: `${zoneCounts.warn.pct}%` }} className="bg-warning" />
            )}
            {zoneCounts.crit.pct > 0 && (
              <div style={{ width: `${zoneCounts.crit.pct}%` }} className="bg-critical" />
            )}
          </div>
          <div className="mt-4 grid grid-cols-3 gap-4">
            <div>
              <div className="flex items-center gap-1.5 mb-1">
                <span className="inline-block h-2 w-2 rounded-full bg-safe" />
                <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Safe</span>
              </div>
              <p className="text-xl font-bold text-foreground">{zoneCounts.safe.pct}%</p>
              <p className="text-xs text-muted-foreground">{zoneCounts.safe.count} readings</p>
            </div>
            <div>
              <div className="flex items-center gap-1.5 mb-1">
                <span className="inline-block h-2 w-2 rounded-full bg-warning" />
                <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Warning</span>
              </div>
              <p className="text-xl font-bold text-foreground">{zoneCounts.warn.pct}%</p>
              <p className="text-xs text-muted-foreground">{zoneCounts.warn.count} readings</p>
            </div>
            <div>
              <div className="flex items-center gap-1.5 mb-1">
                <span className="inline-block h-2 w-2 rounded-full bg-critical" />
                <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Critical</span>
              </div>
              <p className="text-xl font-bold text-foreground">{zoneCounts.crit.pct}%</p>
              <p className="text-xs text-muted-foreground">{zoneCounts.crit.count} readings</p>
            </div>
          </div>
        </div>
      )}

      {/* Period Comparison */}
      {periodComparison && (
        <div className="rounded-xl border bg-card p-6 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold text-card-foreground">Period Comparison</h3>
          <div className="grid grid-cols-3 items-center gap-4">
            <div className="text-center">
              <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground mb-1">Earlier {halfLabel}</p>
              <p className="text-2xl font-bold text-foreground">{periodComparison.prevAvg}{info.unit}</p>
              <p className="text-xs text-muted-foreground mt-0.5">avg</p>
            </div>
            <div className="flex flex-col items-center gap-1">
              {periodComparison.delta > 0 ? (
                <TrendingUp className={`h-6 w-6 ${periodComparison.improving ? 'text-safe' : 'text-warning'}`} />
              ) : periodComparison.delta < 0 ? (
                <TrendingDown className={`h-6 w-6 ${periodComparison.improving ? 'text-safe' : 'text-warning'}`} />
              ) : (
                <Minus className="h-6 w-6 text-muted-foreground" />
              )}
              <span className={`text-xs font-semibold ${periodComparison.improving ? 'text-safe' : 'text-warning'}`}>
                {periodComparison.delta > 0 ? '+' : ''}{periodComparison.delta}{info.unit}
              </span>
              <span className="text-[10px] text-muted-foreground">
                {periodComparison.improving ? 'Improving' : 'Worsening'}
              </span>
            </div>
            <div className="text-center">
              <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground mb-1">Recent {halfLabel}</p>
              <p className="text-2xl font-bold text-foreground">{periodComparison.currAvg}{info.unit}</p>
              <p className="text-xs text-muted-foreground mt-0.5">avg</p>
            </div>
          </div>
        </div>
      )}

      {/* Stress: Risk Level Breakdown */}
      {stressZones && (
        <div className="rounded-xl border bg-card p-6 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold text-card-foreground">Risk Level Breakdown</h3>
          <div className="flex h-2.5 w-full overflow-hidden rounded-full">
            {stressZones.low.pct > 0 && (
              <div style={{ width: `${stressZones.low.pct}%` }} className="bg-safe" />
            )}
            {stressZones.moderate.pct > 0 && (
              <div style={{ width: `${stressZones.moderate.pct}%` }} className="bg-warning" />
            )}
            {stressZones.high.pct > 0 && (
              <div style={{ width: `${stressZones.high.pct}%` }} className="bg-critical" />
            )}
          </div>
          <div className="mt-4 grid grid-cols-3 gap-4">
            <div>
              <div className="flex items-center gap-1.5 mb-1">
                <span className="inline-block h-2 w-2 rounded-full bg-safe" />
                <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Low (0–40)</span>
              </div>
              <p className="text-xl font-bold text-foreground">{stressZones.low.pct}%</p>
              <p className="text-xs text-muted-foreground">{stressZones.low.count} readings</p>
            </div>
            <div>
              <div className="flex items-center gap-1.5 mb-1">
                <span className="inline-block h-2 w-2 rounded-full bg-warning" />
                <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Moderate (40–70)</span>
              </div>
              <p className="text-xl font-bold text-foreground">{stressZones.moderate.pct}%</p>
              <p className="text-xs text-muted-foreground">{stressZones.moderate.count} readings</p>
            </div>
            <div>
              <div className="flex items-center gap-1.5 mb-1">
                <span className="inline-block h-2 w-2 rounded-full bg-critical" />
                <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">High (70–100)</span>
              </div>
              <p className="text-xl font-bold text-foreground">{stressZones.high.pct}%</p>
              <p className="text-xs text-muted-foreground">{stressZones.high.count} readings</p>
            </div>
          </div>
        </div>
      )}

      {/* Stress: Ask AquaBot button */}
      {isStress && (
        <button
          onClick={() => {
            setPendingMessage(
              `What can I do to reduce the fish stress risk score in ${tank.name}? ` +
              `The current score is ${currentValue} (${info.status} risk) and the ${range} average was ${avgValue}. ` +
              `Please give me specific, actionable recommendations.`
            );
            setIsChatOpen(true);
          }}
          className="w-full flex items-center justify-center gap-2.5 rounded-xl border border-primary/40 bg-primary/5 px-6 py-4 text-sm font-semibold text-primary hover:bg-primary/10 active:scale-[0.99] transition-all shadow-sm"
        >
          <MessageCircle className="h-4 w-4" />
          Ask Aqua-Bot for recommendations to reduce stress risk
        </button>
      )}

      {/* Ask AquaBot (non-stress metrics) */}
      {!isStress && (
        <button
          onClick={() => {
            const metricMsg =
              metricId === 'ph'
                ? `The pH level in ${tank.name} is currently ${currentValue} (${info.status}) with a ${range} average of ${avgValue}. What should I do to stabilize it within the safe range?`
                : metricId === 'temperature'
                ? `The water temperature in ${tank.name} is currently ${currentValue}${info.unit} (${info.status}) with a ${range} average of ${avgValue}${info.unit}. What can I do to bring it back to the safe range?`
                : `The turbidity in ${tank.name} is currently ${currentValue}${info.unit} (${info.status}) with a ${range} average of ${avgValue}${info.unit}. What can I do to improve water clarity?`;
            setPendingMessage(metricMsg);
            setIsChatOpen(true);
          }}
          className="w-full flex items-center justify-center gap-2.5 rounded-xl border border-primary/40 bg-primary/5 px-6 py-4 text-sm font-semibold text-primary hover:bg-primary/10 active:scale-[0.99] transition-all shadow-sm"
        >
          <MessageCircle className="h-4 w-4" />
          Ask Aqua-Bot for {metricId === 'ph' ? 'pH stabilisation' : metricId === 'temperature' ? 'temperature control' : 'turbidity reduction'} recommendations
        </button>
      )}
    </div>
  );
};

export default MetricDetail;