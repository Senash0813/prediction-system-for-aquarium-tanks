import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { type TimePoint, type TankStatus } from '@/data/dummyData';

const chartColors: Record<TankStatus, string> = {
  safe: 'hsl(152, 60%, 42%)',
  warning: 'hsl(38, 92%, 50%)',
  critical: 'hsl(0, 72%, 55%)',
};

interface TrendChartProps {
  data: TimePoint[];
  title: string;
  status: TankStatus;
  height?: number;
  clickPath?: string;
  unit?: string;
}

const TrendChart = ({ data, title, status, height = 200, clickPath, unit }: TrendChartProps) => {
  const navigate = useNavigate();
  const color = chartColors[status];

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
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
            tickLine={false}
            axisLine={false}
            width={40}
          />
          <Tooltip
            contentStyle={{
              background: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
              fontSize: '12px',
            }}
            formatter={(value: number) => [`${value}${unit || ''}`, title]}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: color }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default TrendChart;
