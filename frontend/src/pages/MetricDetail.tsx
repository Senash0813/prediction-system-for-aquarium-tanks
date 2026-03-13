import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, TrendingUp, TrendingDown, Minus, ShieldCheck } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from 'recharts';
import { getMetricData, generateData, metricLabels } from '@/data/dummyData';
import { useTanks } from '@/context/TanksContext';

type TimeRange = '24h' | '7d' | '30d';

const MetricDetail = () => {
  const { tankId, metricId } = useParams<{ tankId: string; metricId: string }>();
  const [range, setRange] = useState<TimeRange>('24h');
  const { tanks } = useTanks();

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

  const chartColor =
    info.status === 'critical' ? 'hsl(0, 72%, 55%)' :
    info.status === 'warning' ? 'hsl(38, 92%, 50%)' :
    'hsl(152, 60%, 42%)';

  const avgValue = +(chartData.reduce((s, p) => s + p.value, 0) / chartData.length).toFixed(2);
  const maxValue = Math.max(...chartData.map(p => p.value));
  const minValue = Math.min(...chartData.map(p => p.value));
  const trendDir = chartData.length > 2 && chartData[chartData.length - 1].value > chartData[chartData.length - 2].value ? 'up' : 
    chartData[chartData.length - 1].value < chartData[chartData.length - 2].value ? 'down' : 'flat';

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
          <LineChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
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
            />
            <ReferenceLine y={avgValue} stroke="hsl(var(--muted-foreground))" strokeDasharray="6 3" opacity={0.5} />
            <Tooltip
              contentStyle={{
                background: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              formatter={(value: number) => [`${value}${info.unit}`, label]}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={chartColor}
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 5, fill: chartColor }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <div className="rounded-xl border bg-card p-4 shadow-sm">
          <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Current</p>
          <p className="mt-1 text-xl font-bold text-foreground">{info.value}{info.unit}</p>
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

      {/* Trend Explanation */}
      <div className="rounded-xl border bg-card p-6 shadow-sm">
        <h3 className="mb-2 text-sm font-semibold text-card-foreground">📊 Trend Analysis</h3>
        <p className="text-sm leading-relaxed text-muted-foreground">
          {label} has been {trendDir === 'up' ? 'trending upward' : trendDir === 'down' ? 'trending downward' : 'relatively stable'} over the selected period.
          The current value of <strong>{info.value}{info.unit}</strong> is{' '}
          {info.status === 'safe' ? 'within the safe operating range.' : info.status === 'warning' ? 'approaching the boundary of the safe range. Monitor closely.' : 'outside the safe range. Immediate action recommended.'}
        </p>
      </div>

      {/* Risk Forecast */}
      <div className={`rounded-xl border p-6 shadow-sm ${
        info.status === 'critical' ? 'bg-critical/5 border-critical/20' :
        info.status === 'warning' ? 'bg-warning/5 border-warning/20' :
        'bg-safe/5 border-safe/20'
      }`}>
        <h3 className="mb-2 text-sm font-semibold text-card-foreground">🔮 Risk Forecast</h3>
        <p className="text-sm leading-relaxed text-muted-foreground">
          {info.status === 'critical'
            ? `Based on current trends, ${label.toLowerCase()} is likely to remain in the critical zone. Corrective action should be taken within the next 1-2 hours to prevent fish stress escalation.`
            : info.status === 'warning'
            ? `${label} is projected to reach critical levels within 24-48 hours if the current trend continues. Consider preventive measures.`
            : `${label} is forecasted to remain within safe parameters for the next 72 hours. No action required.`}
        </p>
      </div>

      {/* Recommendations */}
      <div className="rounded-xl border bg-card p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <ShieldCheck className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold text-card-foreground">Recommendations</h3>
        </div>
        <ul className="space-y-2 text-sm text-muted-foreground">
          {info.status === 'critical' && (
            <>
              <li className="flex gap-2"><span className="text-critical">•</span>Perform immediate partial water change (25-30%)</li>
              <li className="flex gap-2"><span className="text-critical">•</span>Check and clean filtration system</li>
              <li className="flex gap-2"><span className="text-critical">•</span>Verify heater/chiller settings</li>
            </>
          )}
          {info.status === 'warning' && (
            <>
              <li className="flex gap-2"><span className="text-warning">•</span>Schedule water testing within 6 hours</li>
              <li className="flex gap-2"><span className="text-warning">•</span>Prepare for partial water change if trend continues</li>
              <li className="flex gap-2"><span className="text-warning">•</span>Monitor every 2 hours until stabilized</li>
            </>
          )}
          {info.status === 'safe' && (
            <>
              <li className="flex gap-2"><span className="text-safe">•</span>Continue routine monitoring schedule</li>
              <li className="flex gap-2"><span className="text-safe">•</span>Next maintenance check in 5 days</li>
            </>
          )}
        </ul>
      </div>
    </div>
  );
};

export default MetricDetail;