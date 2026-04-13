import { createContext, useContext, useState, ReactNode } from 'react';

export interface MetricSnapshot {
  value: number;
  status: string;
  unit: string;
}

export interface PageContext {
  page: 'dashboard' | 'tank_dashboard' | 'metric_detail';
  tankId?: string;
  tankName?: string;
  metrics?: {
    temperature?: MetricSnapshot;
    ph?: MetricSnapshot;
    turbidity?: MetricSnapshot;
    stressScore?: number;
    stressStatus?: string;
  };
  metricDetail?: {
    metric: string;
    current: number;
    average: number;
    min: number;
    max: number;
    trend: string;
    status: string;
    unit: string;
    timeRange: string;
  };
  notifications?: Array<{
    kind?: string;
    message: string;
    severity: string;
    timestamp?: string;
  }>;
  allTanksSummary?: Array<{
    id: string;
    name: string;
    status: string;
    stressScore: number;
  }>;
}

interface ChatContextType {
  pageContext: PageContext | null;
  setPageContext: (ctx: PageContext | null) => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider = ({ children }: { children: ReactNode }) => {
  const [pageContext, setPageContext] = useState<PageContext | null>(null);

  return (
    <ChatContext.Provider value={{ pageContext, setPageContext }}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChatContext = () => {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error('useChatContext must be used within ChatProvider');
  return ctx;
};
