export type TankStatus = 'safe' | 'warning' | 'critical';

export interface TimePoint {
  time: string;
  value: number;
}

export interface TankMetric {
  value: number;
  status: TankStatus;
  unit: string;
  trend: string;
  label: string;
}

export interface Notification {
  id: string;
  en: string;
  si: string;
  severity: TankStatus;
  timestamp: string;
}

export interface Tank {
  id: string;
  name: string;
  stressScore: number;
  status: TankStatus;
  insight: string;
  temperature: TankMetric;
  ph: TankMetric;
  turbidity: TankMetric;
  stressHistory: TimePoint[];
  temperatureHistory: TimePoint[];
  phHistory: TimePoint[];
  turbidityHistory: TimePoint[];
  notifications: Notification[];
}

export const generateTimeSeries = (
  base: number,
  variance: number,
  hours: number,
  intervalMinutes: number = 60
): TimePoint[] => {
  const points: TimePoint[] = [];
  const now = new Date();
  const count = Math.floor((hours * 60) / intervalMinutes);
  for (let i = count; i >= 0; i--) {
    const time = new Date(now.getTime() - i * intervalMinutes * 60 * 1000);
    points.push({
      time: time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }),
      value: +(base + (Math.random() - 0.5) * variance * 2).toFixed(2),
    });
  }
  return points;
};

export const generateData = (base: number, variance: number, range: '24h' | '7d' | '30d') => {
  switch (range) {
    case '24h': return generateTimeSeries(base, variance, 24, 60);
    case '7d': return generateTimeSeries(base, variance, 168, 360);
    case '30d': return generateTimeSeries(base, variance, 720, 1440);
  }
};

export const tanks: Tank[] = [
  {
    id: 'tank-a',
    name: 'Tank A',
    stressScore: 15,
    status: 'safe',
    insight: 'All parameters stable',
    temperature: { value: 24.5, status: 'safe', unit: '°C', trend: 'stable', label: 'Temperature' },
    ph: { value: 7.2, status: 'safe', unit: '', trend: '↔', label: 'pH Level' },
    turbidity: { value: 2.1, status: 'safe', unit: 'NTU', trend: 'stable', label: 'Turbidity' },
    stressHistory: generateTimeSeries(15, 5, 24),
    temperatureHistory: generateTimeSeries(24.5, 0.8, 24),
    phHistory: generateTimeSeries(7.2, 0.2, 24),
    turbidityHistory: generateTimeSeries(2.1, 0.5, 24),
    notifications: [
      { id: 'a1', en: 'Filter cleaning recommended within 5 days.', si: 'දින 5ක් ඇතුළත පෙරහන පිරිසිදු කිරීම නිර්දේශ කෙරේ.', severity: 'safe', timestamp: '2 hours ago' },
      { id: 'a2', en: 'Water temperature stable for the past 12 hours.', si: 'පසුගිය පැය 12 තුළ ජල උෂ්ණත්වය ස්ථාවරයි.', severity: 'safe', timestamp: '4 hours ago' },
    ],
  },
  {
    id: 'tank-b',
    name: 'Tank B',
    stressScore: 52,
    status: 'warning',
    insight: 'pH drifting upward',
    temperature: { value: 25.8, status: 'safe', unit: '°C', trend: 'rising', label: 'Temperature' },
    ph: { value: 8.1, status: 'warning', unit: '', trend: '↑', label: 'pH Level' },
    turbidity: { value: 3.4, status: 'safe', unit: 'NTU', trend: 'stable', label: 'Turbidity' },
    stressHistory: generateTimeSeries(52, 10, 24),
    temperatureHistory: generateTimeSeries(25.8, 1.2, 24),
    phHistory: generateTimeSeries(8.1, 0.4, 24),
    turbidityHistory: generateTimeSeries(3.4, 0.8, 24),
    notifications: [
      { id: 'b1', en: 'pH will exceed safe range within 48 hours.', si: 'pH අගය පැය 48ක් ඇතුළත ආරක්ෂිත පරාසය ඉක්මවනු ඇත.', severity: 'warning', timestamp: '30 min ago' },
      { id: 'b2', en: 'Consider partial water change to stabilize pH.', si: 'pH ස්ථාවර කිරීමට අර්ධ ජල වෙනස්කමක් සලකන්න.', severity: 'warning', timestamp: '1 hour ago' },
      { id: 'b3', en: 'Temperature trending slightly upward.', si: 'උෂ්ණත්වය සුළු වශයෙන් ඉහළ යමින් පවතී.', severity: 'safe', timestamp: '3 hours ago' },
    ],
  },
  {
    id: 'tank-c',
    name: 'Tank C',
    stressScore: 85,
    status: 'critical',
    insight: 'High stress – low oxygen detected',
    temperature: { value: 29.2, status: 'critical', unit: '°C', trend: 'rising', label: 'Temperature' },
    ph: { value: 8.9, status: 'critical', unit: '', trend: '↑', label: 'pH Level' },
    turbidity: { value: 7.8, status: 'warning', unit: 'NTU', trend: 'declining', label: 'Turbidity' },
    stressHistory: generateTimeSeries(85, 8, 24),
    temperatureHistory: generateTimeSeries(29.2, 1.5, 24),
    phHistory: generateTimeSeries(8.9, 0.3, 24),
    turbidityHistory: generateTimeSeries(7.8, 1.2, 24),
    notifications: [
      { id: 'c1', en: 'Fish stress risk increasing due to low oxygen.', si: 'අඩු ඔක්සිජන් නිසා මත්ස්‍ය ආතතිය වැඩිවෙමින් පවතී.', severity: 'critical', timestamp: '5 min ago' },
      { id: 'c2', en: 'Temperature will drop below safe range in 35 minutes.', si: 'උෂ්ණත්වය මිනිත්තු 35කින් ආරක්ෂිත පරාසයෙන් පහළ යා හැක.', severity: 'critical', timestamp: '12 min ago' },
      { id: 'c3', en: 'Turbidity levels are elevated – check filter.', si: 'ටර්බිඩිටි මට්ටම් ඉහළ ගොස් ඇත – පෙරහන පරීක්ෂා කරන්න.', severity: 'warning', timestamp: '45 min ago' },
      { id: 'c4', en: 'Filter cleaning recommended within 2 days.', si: 'දින 2ක් ඇතුළත පෙරහන පිරිසිදු කිරීම නිර්දේශ කෙරේ.', severity: 'warning', timestamp: '2 hours ago' },
    ],
  },
  {
    id: 'tank-d',
    name: 'Tank D',
    stressScore: 8,
    status: 'safe',
    insight: 'Excellent water quality',
    temperature: { value: 23.8, status: 'safe', unit: '°C', trend: 'stable', label: 'Temperature' },
    ph: { value: 7.0, status: 'safe', unit: '', trend: '↔', label: 'pH Level' },
    turbidity: { value: 1.2, status: 'safe', unit: 'NTU', trend: 'improving', label: 'Turbidity' },
    stressHistory: generateTimeSeries(8, 3, 24),
    temperatureHistory: generateTimeSeries(23.8, 0.5, 24),
    phHistory: generateTimeSeries(7.0, 0.15, 24),
    turbidityHistory: generateTimeSeries(1.2, 0.3, 24),
    notifications: [
      { id: 'd1', en: 'All parameters within optimal range.', si: 'සියලුම පරාමිතීන් ප්‍රශස්ත පරාසය තුළ පවතී.', severity: 'safe', timestamp: '1 hour ago' },
    ],
  },
];

export const getTankById = (id: string): Tank | undefined => tanks.find(t => t.id === id);

export const getMetricData = (tank: Tank, metric: string): { history: TimePoint[]; info: TankMetric } => {
  switch (metric) {
    case 'temperature': return { history: tank.temperatureHistory, info: tank.temperature };
    case 'ph': return { history: tank.phHistory, info: tank.ph };
    case 'turbidity': return { history: tank.turbidityHistory, info: tank.turbidity };
    case 'stress': return { history: tank.stressHistory, info: { value: tank.stressScore, status: tank.status, unit: '', trend: '', label: 'Fish Stress Risk' } };
    default: return { history: tank.temperatureHistory, info: tank.temperature };
  }
};

export const metricLabels: Record<string, string> = {
  temperature: 'Temperature',
  ph: 'pH Level',
  turbidity: 'Turbidity',
  stress: 'Fish Stress Risk',
};