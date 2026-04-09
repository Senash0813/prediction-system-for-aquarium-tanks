import AlertBanner from '@/components/AlertBanner';
import TankCard from '@/components/TankCard';
import { useTanks } from '@/context/TanksContext';
import { useState } from 'react';
import { TankStatus } from '@/data/dummyData';

const Index = () => {
  const { tanks } = useTanks();
  const [filter, setFilter] = useState<TankStatus | 'all'>('all');

  const filteredTanks = filter === 'all' ? tanks : tanks.filter(tank => tank.status === filter);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Monitor all your aquarium tanks at a glance</p>
      </div>

      <AlertBanner />

      {/* Filter Controls */}
      <div className="flex space-x-4">
        {['all', 'safe', 'warning', 'critical'].map(status => (
          <button
            key={status}
            onClick={() => setFilter(status as TankStatus | 'all')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === status ? 'bg-primary text-white' : 'bg-muted text-foreground hover:bg-muted-foreground'
            }`}
          >
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </button>
        ))}
      </div>

      <div>
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">Tank Overview</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {filteredTanks.map(tank => (
            <TankCard key={tank.id} tank={tank} />
          ))}
        </div>
      </div>
    </div>
  );
};

export default Index;