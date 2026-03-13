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

const metricRanges: Record<string, { min: number; safeStart: number; safeEnd: number; warnEnd: number; max: number }> = {
  Temperature: { min: 18, safeStart: 22, safeEnd: 26, warnEnd: 28, max: 32 },
  'pH Level': { min: 5.5, safeStart: 6.8, safeEnd: 7.5, warnEnd: 8.5, max: 10 },
  Turbidity: { min: 0, safeStart: 0, safeEnd: 3, warnEnd: 6, max: 10 },
  'Fish Stress Risk': { min: 0, safeStart: 0, safeEnd: 30, warnEnd: 60, max: 100 },
};

interface InsightCardProps {
  metric: TankMetric;
  large?: boolean;
}

const InsightCard = ({ metric, large }: InsightCardProps) => {
  const Icon = icons[metric.label] || Activity;
  const range = metricRanges[metric.label] || { min: 0, safeStart: 0, safeEnd: 50, warnEnd: 75, max: 100 };
  const total = range.max - range.min;

  const dangerLeftW = ((range.safeStart - range.min) / total) * 100;
  const safeW = ((range.safeEnd - range.safeStart) / total) * 100;
  const warnW = ((range.warnEnd - range.safeEnd) / total) * 100;
  const dangerRightW = ((range.max - range.warnEnd) / total) * 100;

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
          {dangerLeftW > 0 && <div className="bg-critical/40" style={{ width: `${dangerLeftW}%` }} />}
          <div className="bg-safe/50" style={{ width: `${safeW}%` }} />
          <div className="bg-warning/50" style={{ width: `${warnW}%` }} />
          <div className="bg-critical/40" style={{ width: `${dangerRightW}%` }} />
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
