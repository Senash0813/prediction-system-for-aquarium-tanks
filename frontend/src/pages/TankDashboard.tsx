import { useParams, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useTanks } from '@/context/TanksContext';
import InsightCard from '@/components/InsightCard';
import TrendChart from '@/components/TrendChart';
import PredictiveNotifications from '@/components/PredictiveNotifications';
import CircularGauge from '@/components/CircularGauge';

const TankDashboard = () => {
  const { tankId } = useParams<{ tankId: string }>();
  const { tanks } = useTanks();
  const tank = tanks.find(t => t.id === (tankId || ''));

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
      <TrendChart
        data={tank.stressHistory}
        title="Stress Risk Score – Last 24h"
        status={tank.status}
        height={250}
        clickPath={`/tank/${tank.id}/metric/stress`}
      />

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