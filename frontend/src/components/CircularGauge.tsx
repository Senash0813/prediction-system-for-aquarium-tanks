import { type TankStatus } from '@/data/dummyData';

interface CircularGaugeProps {
  value: number;
  max?: number;
  size?: number;
  strokeWidth?: number;
  status: TankStatus;
  label?: string;
  showLabel?: boolean;
}

const statusColors: Record<TankStatus, string> = {
  safe: 'hsl(152, 60%, 42%)',
  warning: 'hsl(38, 92%, 50%)',
  critical: 'hsl(0, 72%, 55%)',
};

const statusLabels: Record<TankStatus, string> = {
  safe: 'LOW',
  warning: 'MEDIUM',
  critical: 'HIGH',
};

const CircularGauge = ({ value, max = 100, size = 90, strokeWidth = 7, status, showLabel = false }: CircularGaugeProps) => {
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.min(Math.max(value, 0), max);
  const progress = (clamped / max) * circumference;
  const center = size / 2;

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={center} cy={center} r={radius}
          fill="none" stroke="hsl(var(--muted))" strokeWidth={strokeWidth}
        />
        <circle
          cx={center} cy={center} r={radius}
          fill="none" stroke={statusColors[status]} strokeWidth={strokeWidth}
          strokeDasharray={circumference} strokeDashoffset={circumference - progress}
          strokeLinecap="round"
          className="transition-all duration-700 ease-out"
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center" style={{ width: size, height: size }}>
        <span className="text-lg font-bold text-foreground">{value}</span>
        {showLabel && (
          <span className="text-[10px] font-semibold tracking-wide" style={{ color: statusColors[status] }}>
            {statusLabels[status]}
          </span>
        )}
      </div>
    </div>
  );
};

export default CircularGauge;
