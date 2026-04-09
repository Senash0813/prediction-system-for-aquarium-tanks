import { AlertTriangle, CheckCircle } from 'lucide-react';
import { tanks } from '@/data/dummyData';

const AlertBanner = () => {
  const criticalTanks = tanks.filter(t => t.status === 'critical');
  const isCritical = criticalTanks.length > 0;

  return (
    <div
      className={`flex items-center gap-3 rounded-lg px-5 py-3.5 text-sm font-medium animate-fade-in ${
        isCritical
          ? 'bg-critical/20 text-critical border border-critical/30 dark:bg-critical/15 dark:border-critical/30'
          : 'bg-safe/20 text-safe border border-safe/30 dark:bg-safe/15 dark:border-safe/30'
      }`}
    >
      {isCritical ? (
        <>
          <AlertTriangle className="h-5 w-5 shrink-0 animate-pulse-soft" />
          <span>
            {criticalTanks.length} Tank{criticalTanks.length > 1 ? 's' : ''} in Critical Condition – Immediate Attention Required
          </span>
        </>
      ) : (
        <>
          <CheckCircle className="h-5 w-5 shrink-0" />
          <span>All Tanks Operating Within Safe Range</span>
        </>
      )}
    </div>
  );
};

export default AlertBanner;
