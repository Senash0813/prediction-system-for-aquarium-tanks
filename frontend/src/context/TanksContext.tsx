import { createContext, useContext, useState, ReactNode } from 'react';
import { tanks as initialTanks, Tank, generateTimeSeries, TankStatus } from '@/data/dummyData';

interface TanksContextType {
  tanks: Tank[];
  addTank: (name: string, details: { temperature: string; ph: string; turbidity: string; light: string; tds: string }) => void;
  deleteTank: (id: string) => void;
}

const TanksContext = createContext<TanksContextType | undefined>(undefined);

export const TanksProvider = ({ children }: { children: ReactNode }) => {
  const [tanks, setTanks] = useState<Tank[]>(initialTanks);

  const addTank = (name: string, details: { temperature: string; ph: string; turbidity: string; light: string; tds: string }) => {
    const id = `tank-${name.toLowerCase().replace(/\s+/g, '-')}-${Date.now()}`;
    const newTank: Tank = {
      id,
      name,
      stressScore: 10,
      status: 'safe' as TankStatus,
      insight: 'New tank – monitoring started',
      temperature: { value: parseFloat(details.temperature), status: 'safe', unit: '°C', trend: 'stable', label: 'Temperature' },
      ph: { value: parseFloat(details.ph), status: 'safe', unit: '', trend: '↔', label: 'pH Level' },
      turbidity: { value: parseFloat(details.turbidity), status: 'safe', unit: 'NTU', trend: 'stable', label: 'Turbidity' },
      stressHistory: generateTimeSeries(10, 3, 24),
      temperatureHistory: generateTimeSeries(parseFloat(details.temperature), 0.5, 24),
      phHistory: generateTimeSeries(parseFloat(details.ph), 0.15, 24),
      turbidityHistory: generateTimeSeries(parseFloat(details.turbidity), 0.3, 24),
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
