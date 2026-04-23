import { useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useTanks } from '@/context/TanksContext';
import { useChatContext } from '@/components/chatbot/ChatContext';
import InsightCard from '@/components/InsightCard';
import TrendChart from '@/components/TrendChart';
import PredictiveNotifications from '@/components/PredictiveNotifications';
import CircularGauge from '@/components/CircularGauge';
import { type TankStatus } from '@/data/dummyData';

const OXYGEN_RISK_BANDS = [
  { key: 'safe' as TankStatus, label: 'Normal', min: 0, max: 25, color: 'hsl(152, 60%, 42%)' },
  { key: 'warning' as TankStatus, label: 'Moderate', min: 25, max: 50, color: 'hsl(38, 92%, 50%)' },
  { key: 'critical' as TankStatus, label: 'Low', min: 50, max: 100, color: 'hsl(0, 72%, 55%)' },
];

const OXYGEN_THRESHOLD_MARKERS = [25, 50];

const statusTextColor: Record<TankStatus, string> = {
  safe: 'hsl(152, 60%, 42%)',
  warning: 'hsl(38, 92%, 50%)',
  critical: 'hsl(0, 72%, 55%)',
};

const OxygenRiskGaugeCard = ({ status, oxygenRiskScore }: { status: TankStatus; oxygenRiskScore?: number }) => {
  const size = 120;
  const strokeWidth = 10;
  const segmentGap = 4;
  const center = size / 2;
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const clampedRisk = Math.min(Math.max(oxygenRiskScore ?? 0, 0), 100);

  const activeBand = OXYGEN_RISK_BANDS.find((band) => status === band.key) ?? OXYGEN_RISK_BANDS[0];

  return (
    <div className="flex w-56 shrink-0 flex-col items-center justify-center gap-3 rounded-xl border bg-card p-5 shadow-sm animate-fade-in">
      <span className="text-xs font-medium text-muted-foreground">Dissolved O₂</span>

      <div className="relative">
        <svg width={size} height={size} className="-rotate-90">
          {OXYGEN_RISK_BANDS.map((band) => {
            const segmentLength = ((band.max - band.min) / 100) * circumference;
            const dashOffset = -((band.min / 100) * circumference);
            const visibleLength = Math.max(segmentLength - segmentGap, 0);
            return (
              <circle
                key={band.key}
                cx={center}
                cy={center}
                r={radius}
                fill="none"
                stroke="hsl(var(--muted))"
                strokeWidth={strokeWidth}
                strokeDasharray={`${visibleLength} ${circumference}`}
                strokeDashoffset={dashOffset}
                strokeLinecap="butt"
              />
            );
          })}
          {OXYGEN_RISK_BANDS.map((band) => {
            const segmentSpan = band.max - band.min;
            const filledInBand = Math.min(Math.max(clampedRisk - band.min, 0), segmentSpan);
            if (filledInBand <= 0) return null;

            const filledLength = (filledInBand / 100) * circumference;
            const dashOffset = -((band.min / 100) * circumference);
            const visibleLength = Math.max(filledLength - segmentGap, 0);
            return (
              <circle
                key={`${band.key}-fill`}
                cx={center}
                cy={center}
                r={radius}
                fill="none"
                stroke={band.color}
                strokeWidth={strokeWidth}
                strokeDasharray={`${visibleLength} ${circumference}`}
                strokeDashoffset={dashOffset}
                strokeLinecap="butt"
              />
            );
          })}
        </svg>
        {OXYGEN_THRESHOLD_MARKERS.map((threshold) => {
          const angle = (threshold / 100) * 2 * Math.PI - Math.PI / 2;
          const markerRadius = radius + 1;
          const markerX = center + markerRadius * Math.cos(angle);
          const markerY = center + markerRadius * Math.sin(angle);
          return (
            <span
              key={threshold}
              className="pointer-events-none absolute h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-card bg-background shadow-sm"
              style={{ left: markerX, top: markerY }}
              title={threshold === 25 ? 'Normal threshold' : 'Moderate threshold'}
            />
          );
        })}
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center leading-tight">
          <span className="text-lg font-bold text-card-foreground">
            {oxygenRiskScore == null ? '—' : `${oxygenRiskScore.toFixed(1)}%`}
          </span>
          <span className="text-sm font-semibold" style={{ color: statusTextColor[status] }}>
            {activeBand.label}
          </span>
        </div>
      </div>
    </div>
  );
};

const TankDashboard = () => {
  const { tankId } = useParams<{ tankId: string }>();
  const { tanks } = useTanks();
  const { setPageContext } = useChatContext();
  const tank = tanks.find(t => t.id === (tankId || ''));

  useEffect(() => {
    if (!tank) return;
    setPageContext({
      page: 'tank_dashboard',
      tankId: tank.id,
      tankName: tank.name,
      metrics: {
        temperature: { value: tank.temperature.value, status: tank.temperature.status, unit: tank.temperature.unit, safeMin: tank.temperature.safeMin, safeMax: tank.temperature.safeMax },
        ph: { value: tank.ph.value, status: tank.ph.status, unit: tank.ph.unit, safeMin: tank.ph.safeMin, safeMax: tank.ph.safeMax },
        turbidity: { value: tank.turbidity.value, status: tank.turbidity.status, unit: tank.turbidity.unit, safeMin: tank.turbidity.safeMin, safeMax: tank.turbidity.safeMax },
        stressScore: tank.stressScore,
        stressStatus: tank.status,
      },
      notifications: tank.notifications.map(n => ({
        kind: n.kind,
        message: n.en,
        severity: n.severity,
        timestamp: n.timestamp,
      })),
    });
    return () => setPageContext(null);
  }, [tank, setPageContext]);

  if (!tank) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20">
        <p className="text-lg text-muted-foreground">Tank not found</p>
        <Link to="/" className="text-primary underline">Back to dashboard</Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/" className="rounded-lg p-2 hover:bg-muted transition-colors">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-foreground">{tank.name}</h1>
          <p className="text-sm text-muted-foreground">{tank.insight}</p>
        </div>
      </div>

      {/* Insight Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <InsightCard metric={tank.temperature} />
        <InsightCard metric={tank.ph} />
        <InsightCard metric={tank.turbidity} />
        {/* Stress card - special */}
        <div className="flex flex-col items-center justify-center gap-2 rounded-xl border bg-card p-5 shadow-sm animate-fade-in">
          <span className="text-xs font-medium text-muted-foreground">Fish Stress Risk</span>
          <div className="relative">
            <CircularGauge value={tank.stressScore} status={tank.status} size={100} strokeWidth={8} showLabel />
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="flex items-stretch gap-4">
        <div className="flex-1 min-w-0">
          <TrendChart
            data={tank.stressHistory}
            title="Stress Risk Score – Last 24h"
            status={tank.status}
            height={250}
            clickPath={`/tank/${tank.id}/metric/stress`}
            stressMode
          />
        </div>
        <OxygenRiskGaugeCard
          status={tank.oxygenStatus ?? 'safe'}
          oxygenRiskScore={tank.oxygenRiskScore}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <TrendChart
          data={tank.temperatureHistory}
          title="Temperature"
          status={tank.temperature.status}
          unit="°C"
          clickPath={`/tank/${tank.id}/metric/temperature`}
          safeMin={tank.temperature.safeMin}
          safeMax={tank.temperature.safeMax}
        />
        <TrendChart
          data={tank.phHistory}
          title="pH Level"
          status={tank.ph.status}
          clickPath={`/tank/${tank.id}/metric/ph`}
          safeMin={tank.ph.safeMin}
          safeMax={tank.ph.safeMax}
        />
        <TrendChart
          data={tank.turbidityHistory}
          title="Turbidity"
          status={tank.turbidity.status}
          unit=" NTU"
          clickPath={`/tank/${tank.id}/metric/turbidity`}
          safeMin={tank.turbidity.safeMin}
          safeMax={tank.turbidity.safeMax}
        />
      </div>

      {/* Predictive Notifications */}
      <PredictiveNotifications notifications={tank.notifications} />
    </div>
  );
};

export default TankDashboard;