import { createContext, useContext, useState, ReactNode } from 'react';
import { tanks as initialTanks, Tank, generateTimeSeries, TankStatus } from '@/data/dummyData';

interface TanksContextType {
  tanks: Tank[];
  addTank: (name: string) => void;
  deleteTank: (id: string) => void;
}

const TanksContext = createContext<TanksContextType | undefined>(undefined);

export const TanksProvider = ({ children }: { children: ReactNode }) => {
  const [tanks, setTanks] = useState<Tank[]>(initialTanks);

  const addTank = (name: string) => {
    const id = `tank-${name.toLowerCase().replace(/\s+/g, '-')}-${Date.now()}`;
    const newTank: Tank = {
      id,
      name,
      stressScore: 10,
      status: 'safe' as TankStatus,
      insight: 'New tank – monitoring started',
      temperature: { value: 24.0, status: 'safe', unit: '°C', trend: 'stable', label: 'Temperature' },
      ph: { value: 7.0, status: 'safe', unit: '', trend: '↔', label: 'pH Level' },
      turbidity: { value: 1.5, status: 'safe', unit: 'NTU', trend: 'stable', label: 'Turbidity' },
      stressHistory: generateTimeSeries(10, 3, 24),
      temperatureHistory: generateTimeSeries(24.0, 0.5, 24),
      phHistory: generateTimeSeries(7.0, 0.15, 24),
      turbidityHistory: generateTimeSeries(1.5, 0.3, 24),
      notifications: [
        { id: `${id}-n1`, en: 'Tank created. Monitoring has begun.', si: 'ටැංකිය සාදන ලදී. නිරීක්ෂණය ආරම්භ කර ඇත.', severity: 'safe', timestamp: 'Just now' },
      ],
    };
    setTanks(prev => [...prev, newTank]);
  };

  const deleteTank = (id: string) => {
    setTanks(prev => prev.filter(t => t.id !== id));
  };

  return (
    <TanksContext.Provider value={{ tanks, addTank, deleteTank }}>
      {children}
    </TanksContext.Provider>
  );
};

export const useTanks = () => {
  const ctx = useContext(TanksContext);
  if (!ctx) throw new Error('useTanks must be used within TanksProvider');
  return ctx;
};
