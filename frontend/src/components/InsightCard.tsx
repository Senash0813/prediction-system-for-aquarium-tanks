import { Thermometer, Droplets, Eye, Activity } from 'lucide-react';
import { type TankMetric, type TankStatus } from '@/data/dummyData';

const icons: Record<string, React.ElementType> = {
  Temperature: Thermometer,
  'pH Level': Droplets,
  Turbidity: Eye,
  'Fish Stress Risk': Activity,
};

const statusText: Record<TankStatus, string> = {
  safe: 'text-safe',
  warning: 'text-warning',
  critical: 'text-critical',
};

// Fallback ranges used when no tank_config safe ranges are available (dummy tanks A–D).
// 5-segment: danger-left / warn-left / safe / warn-right / danger-right
const fallbackRanges: Record<string, { min: number; warnStart: number; safeStart: number; safeEnd: number; warnEnd: number; max: number }> = {
  Temperature:        { min: 18,  warnStart: 20,  safeStart: 22,  safeEnd: 28,  warnEnd: 30,  max: 32  },
  'pH Level':         { min: 5.5, warnStart: 6.0, safeStart: 6.5, safeEnd: 8.5, warnEnd: 9.0, max: 9.5 },
  Turbidity:          { min: 0,   warnStart: 0,   safeStart: 0,   safeEnd: 5,   warnEnd: 10,  max: 15  },
  'Fish Stress Risk': { min: 0,   warnStart: 0,   safeStart: 0,   safeEnd: 40,  warnEnd: 70,  max: 100 },
};

// Build a 5-segment range from tank_config safe_ranges.
// Warning buffer = 30% of the safe span on each side; danger buffer = another 30%.
function buildRangeFromConfig(safeMin: number, safeMax: number) {
  const buf = (safeMax - safeMin) * 0.3;
  return {
    min:       safeMin - buf * 2,
    warnStart: safeMin - buf,
    safeStart: safeMin,
    safeEnd:   safeMax,
    warnEnd:   safeMax + buf,
    max:       safeMax + buf * 2,
  };
}

interface InsightCardProps {
  metric: TankMetric;
  large?: boolean;
}

const InsightCard = ({ metric, large }: InsightCardProps) => {
  const Icon = icons[metric.label] || Activity;

  // Use per-tank safe ranges from tank_config when available; fall back to static defaults.
  const range =
    metric.safeMin != null && metric.safeMax != null
      ? buildRangeFromConfig(metric.safeMin, metric.safeMax)
      : (fallbackRanges[metric.label] ?? { min: 0, warnStart: 0, safeStart: 0, safeEnd: 50, warnEnd: 75, max: 100 });
  const total = range.max - range.min;

  const dangerLeftW  = ((range.warnStart - range.min)      / total) * 100;
  const warnLeftW    = ((range.safeStart - range.warnStart) / total) * 100;
  const safeW        = ((range.safeEnd   - range.safeStart) / total) * 100;
  const warnRightW   = ((range.warnEnd   - range.safeEnd)   / total) * 100;
  const dangerRightW = ((range.max       - range.warnEnd)   / total) * 100;

  const clamped = Math.min(Math.max(metric.value, range.min), range.max);
  const markerPos = ((clamped - range.min) / total) * 100;

  return (
    <div className="flex flex-col gap-3 rounded-xl border bg-card p-5 shadow-sm animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className={`h-4 w-4 ${statusText[metric.status]}`} />
          <span className="text-xs font-medium text-muted-foreground">{metric.label}</span>
        </div>
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold capitalize ${statusText[metric.status]}`}>
          {metric.status}
        </span>
      </div>

      <div className="flex items-baseline gap-1.5">
        <span className={`font-bold text-card-foreground ${large ? 'text-3xl' : 'text-2xl'}`}>
          {metric.value}
        </span>
        <span className="text-sm text-muted-foreground">{metric.unit}</span>
        {metric.trend && metric.trend !== 'stable' && metric.trend !== '↔' && (
          <span className={`text-sm font-medium ${statusText[metric.status]}`}>{metric.trend}</span>
        )}
      </div>

      <div className="relative mt-1">
        <div className="flex h-2.5 w-full overflow-hidden rounded-full">
          {dangerLeftW  > 0 && <div className="bg-critical" style={{ width: `${dangerLeftW}%`  }} />}
          {warnLeftW    > 0 && <div className="bg-warning"  style={{ width: `${warnLeftW}%`    }} />}
          {safeW        > 0 && <div className="bg-safe"     style={{ width: `${safeW}%`        }} />}
          {warnRightW   > 0 && <div className="bg-warning"  style={{ width: `${warnRightW}%`   }} />}
          {dangerRightW > 0 && <div className="bg-critical" style={{ width: `${dangerRightW}%` }} />}
        </div>
        <div
          className="absolute -top-0.5 h-3.5 w-1 rounded-full bg-card-foreground shadow-md transition-all duration-500"
          style={{ left: `calc(${markerPos}% - 2px)` }}
        />
        <div className="mt-1 flex justify-between text-[9px] text-muted-foreground">
          <span>{range.min}{metric.unit}</span>
          <span>{range.max}{metric.unit}</span>
        </div>
      </div>
    </div>
  );
};

export default InsightCard;
