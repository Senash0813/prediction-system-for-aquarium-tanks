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

const OXYGEN_BARS: { status: TankStatus; color: string; bgActive: string; glow: string; label: string }[] = [
  { status: 'safe',     color: 'hsl(152, 60%, 42%)', bgActive: 'rgba(47, 160, 100, 0.15)', glow: 'rgba(47, 160, 100, 0.5)',  label: 'Normal'   },
  { status: 'warning',  color: 'hsl(38, 92%, 50%)',  bgActive: 'rgba(246, 160, 12, 0.15)', glow: 'rgba(246, 160, 12, 0.5)',  label: 'Moderate' },
  { status: 'critical', color: 'hsl(0, 72%, 55%)',   bgActive: 'rgba(220, 50, 47, 0.15)',  glow: 'rgba(220, 50, 47, 0.5)',   label: 'Low'      },
];

const OxygenTrafficLight = ({ status }: { status: TankStatus }) => (
  <div className="rounded-xl border bg-card shadow-sm animate-fade-in flex flex-col px-4 py-5 w-44 shrink-0">
    <h4 className="mb-3 text-sm font-semibold text-card-foreground">Dissolved O₂</h4>
    <div className="flex flex-col gap-2 flex-1 justify-center">
      {OXYGEN_BARS.map(bar => {
        const active = status === bar.status;
        return (
          <div
            key={bar.status}
            className="rounded-lg px-3 py-3 flex items-center justify-center transition-all duration-500"
            style={{
              backgroundColor: active ? bar.bgActive : 'hsl(var(--muted))',
              border: `1px solid ${active ? bar.color : 'transparent'}`,
              boxShadow: active ? `0 0 8px 2px ${bar.glow}` : 'none',
            }}
          >
            <span
              className="text-xs font-semibold transition-colors duration-300"
              style={{ color: active ? bar.color : 'hsl(var(--muted-foreground))' }}
            >
              {bar.label}
            </span>
          </div>
        );
      })}
    </div>
  </div>
);

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
          />
        </div>
        <OxygenTrafficLight status={tank.oxygenStatus ?? 'safe'} />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <TrendChart
          data={tank.temperatureHistory}
          title="Temperature"
          status={tank.temperature.status}
          unit="°C"
          clickPath={`/tank/${tank.id}/metric/temperature`}
        />
        <TrendChart
          data={tank.phHistory}
          title="pH Level"
          status={tank.ph.status}
          clickPath={`/tank/${tank.id}/metric/ph`}
        />
        <TrendChart
          data={tank.turbidityHistory}
          title="Turbidity"
          status={tank.turbidity.status}
          unit=" NTU"
          clickPath={`/tank/${tank.id}/metric/turbidity`}
        />
      </div>

      {/* Predictive Notifications */}
      <PredictiveNotifications notifications={tank.notifications} />
    </div>
  );
};

export default TankDashboard;