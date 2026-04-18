import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceArea, ReferenceLine } from 'recharts';
import { type TimePoint, type TankStatus } from '@/data/dummyData';

const STATUS_COLORS: Record<TankStatus, string> = {
  safe: 'hsl(152, 60%, 42%)',
  warning: 'hsl(38, 92%, 50%)',
  critical: 'hsl(0, 72%, 55%)',
};

const NEUTRAL_COLOR = 'hsl(217, 91%, 60%)';

interface TrendChartProps {
  data: TimePoint[];
  title: string;
  status: TankStatus;
  height?: number;
  clickPath?: string;
  unit?: string;
  safeMin?: number;
  safeMax?: number;
  stressMode?: boolean;
}

const TrendChart = ({ data, title, status, height = 200, clickPath, unit, safeMin, safeMax, stressMode = false }: TrendChartProps) => {
  const navigate = useNavigate();
  const hasThresholds = safeMin != null && safeMax != null;
  const color = (hasThresholds || stressMode) ? NEUTRAL_COLOR : STATUS_COLORS[status];

  const crossingIndices = (() => {
    const indices = new Set<number>();
    if (!hasThresholds || data.length < 2) return indices;
    const inRange = (v: number) => v >= safeMin! && v <= safeMax!;
    for (let i = 1; i < data.length; i++) {
      if (inRange(data[i].value) !== inRange(data[i - 1].value)) {
        indices.add(i - 1);
        indices.add(i);
      }
    }
    return indices;
  })();

  const isIsoLike = (v: any) => {
    if (typeof v !== 'string') return false;
    return /^\d{4}-\d{2}-\d{2}T/.test(v) || v.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(v);
  };

  const formatTimeTick = (value: any) => {
    if (value == null) return '';
    if (typeof value === 'string') {
      const d = new Date(value);
      if (!isNaN(d.getTime())) {
        const useUtc = isIsoLike(value);
        return d.toLocaleString(undefined, {
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          ...(useUtc ? { timeZone: 'UTC' as const } : {}),
        });
      }
      return value;
    }
    if (value instanceof Date && !isNaN(value.getTime())) {
      return value.toLocaleString(undefined, {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    }
    return String(value);
  };

  const formatValueTick = (value: any) => {
    if (value == null) return '';
    return unit ? `${value}${unit}` : String(value);
  };

  return (
    <div
      className={`rounded-xl border bg-card p-5 shadow-sm animate-fade-in ${clickPath ? 'cursor-pointer card-hover' : ''}`}
      onClick={() => clickPath && navigate(clickPath)}
    >
      <h4 className="mb-3 text-sm font-semibold text-card-foreground">{title}</h4>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis
            dataKey="time"
            tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
            interval="preserveStartEnd"
            tickFormatter={formatTimeTick}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
            tickFormatter={formatValueTick}
            tickLine={false}
            axisLine={false}
            width={40}
            domain={
              stressMode ? [0, 100] :
              hasThresholds
                ? [
                    (dataMin: number) => +Math.min(dataMin, safeMin! * (safeMin! >= 0 ? 0.97 : 1.03)).toFixed(2),
                    (dataMax: number) => +Math.max(dataMax, safeMax! * (safeMax! >= 0 ? 1.03 : 0.97)).toFixed(2),
                  ]
                : ['auto', 'auto']
            }
          />
          {stressMode && (
            <ReferenceLine y={40} stroke="hsl(38, 92%, 50%)" strokeDasharray="5 3" strokeWidth={1.5} />
          )}
          {stressMode && (
            <ReferenceLine y={70} stroke="hsl(0, 72%, 55%)" strokeDasharray="5 3" strokeWidth={1.5} />
          )}
          <Tooltip
            contentStyle={{
              background: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
              fontSize: '12px',
            }}
            formatter={(value: number) => [`${value}${unit || ''}`, title]}
            labelFormatter={(label: any) => formatTimeTick(label)}
          />
          {hasThresholds && (
            <ReferenceArea
              y1={safeMin}
              y2={safeMax}
              fill="hsl(152, 60%, 42%)"
              fillOpacity={0.08}
              stroke="hsl(152, 60%, 42%)"
              strokeOpacity={0.3}
              strokeDasharray="4 2"
            />
          )}
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            activeDot={{ r: 4, fill: color }}
            dot={(dotProps: any) => {
              const { cx, cy, index } = dotProps;
              if (!hasThresholds || !crossingIndices.has(index)) return <g key={index} />;
              const v = data[index]?.value;
              const dotColor = (v > safeMax!) || (v < safeMin!)
                ? (status === 'critical' ? 'hsl(0, 72%, 55%)' : 'hsl(38, 92%, 50%)')
                : color;
              return <circle key={index} cx={cx} cy={cy} r={3} fill={dotColor} stroke="hsl(var(--card))" strokeWidth={1.5} />;
            }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default TrendChart;
