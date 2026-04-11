import { createContext, useContext, useState, ReactNode } from 'react';
import { tanks as initialTanks, Tank, generateTimeSeries, TankStatus } from '@/data/dummyData';
import { saveTankConfig } from '@/api/client';

interface TankDetails {
  temperatureMin: string; temperatureMax: string;
  phMin: string; phMax: string;
  turbidityMin: string; turbidityMax: string;
  lightMin: string; lightMax: string;
  tdsMin: string; tdsMax: string;
}

interface TanksContextType {
  tanks: Tank[];
  addTank: (name: string, details: TankDetails) => void;
  deleteTank: (id: string) => void;
}

const TanksContext = createContext<TanksContextType | undefined>(undefined);

export const TanksProvider = ({ children }: { children: ReactNode }) => {
  const [tanks, setTanks] = useState<Tank[]>(initialTanks);

  const addTank = (name: string, details: TankDetails) => {
    const id = `tank-${name.toLowerCase().replace(/\s+/g, '-')}-${Date.now()}`;
    const tempMin = parseFloat(details.temperatureMin);
    const tempMax = parseFloat(details.temperatureMax);
    const phMin = parseFloat(details.phMin);
    const phMax = parseFloat(details.phMax);
    const turbMin = parseFloat(details.turbidityMin);
    const turbMax = parseFloat(details.turbidityMax);
    const tempMid = (tempMin + tempMax) / 2;
    const phMid = (phMin + phMax) / 2;
    const turbMid = (turbMin + turbMax) / 2;

    const newTank: Tank = {
      id,
      name,
      stressScore: 10,
      status: 'safe' as TankStatus,
      insight: 'New tank – monitoring started',
      temperature: { value: tempMid, status: 'safe', unit: '°C', trend: 'stable', label: 'Temperature', safeMin: tempMin, safeMax: tempMax },
      ph: { value: phMid, status: 'safe', unit: '', trend: '↔', label: 'pH Level', safeMin: phMin, safeMax: phMax },
      turbidity: { value: turbMid, status: 'safe', unit: 'NTU', trend: 'stable', label: 'Turbidity', safeMin: turbMin, safeMax: turbMax },
      stressHistory: generateTimeSeries(10, 3, 24),
      temperatureHistory: generateTimeSeries(tempMid, 0.5, 24),
      phHistory: generateTimeSeries(phMid, 0.15, 24),
      turbidityHistory: generateTimeSeries(turbMid, 0.3, 24),
      notifications: [
        { id: `${id}-n1`, en: 'Tank created. Monitoring has begun.', si: 'ටැංකිය සාදන ලදී. නිරීක්ෂණය ආරම්භ කර ඇත.', severity: 'safe', timestamp: 'Just now' },
      ],
    };
    setTanks(prev => [...prev, newTank]);

    saveTankConfig({
      tank_id: name,
      safe_ranges: {
        temperature: { min: tempMin, max: tempMax },
        ph:          { min: phMin,   max: phMax   },
        turbidity:   { min: turbMin, max: turbMax  },
        light:       { min: parseFloat(details.lightMin), max: parseFloat(details.lightMax) },
        tds:         { min: parseFloat(details.tdsMin),   max: parseFloat(details.tdsMax)   },
      },
    }).catch(err => console.error('[TanksContext] Failed to save tank config:', err));
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
