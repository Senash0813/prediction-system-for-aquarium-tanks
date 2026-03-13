import AlertBanner from '@/components/AlertBanner';
import TankCard from '@/components/TankCard';
import { tanks } from '@/data/dummyData';

const Index = () => {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Monitor all your aquarium tanks at a glance</p>
      </div>

      <AlertBanner />

      <div>
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">Tank Overview</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {tanks.map(tank => (
            <TankCard key={tank.id} tank={tank} />
          ))}
        </div>
      </div>
    </div>
  );
};

export default Index;
