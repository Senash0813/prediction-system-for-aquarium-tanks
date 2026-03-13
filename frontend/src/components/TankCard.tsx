import { useNavigate } from 'react-router-dom';
import CircularGauge from './CircularGauge';
import { type Tank } from '@/data/dummyData';

const statusBorder: Record<string, string> = {
  safe: 'border-safe/50 hover:border-safe',
  warning: 'border-warning/50 hover:border-warning',
  critical: 'border-critical/50 hover:border-critical',
};

const statusBadge: Record<string, string> = {
  safe: 'bg-safe/10 text-safe',
  warning: 'bg-warning/10 text-warning',
  critical: 'bg-critical/10 text-critical',
};

const TankCard = ({ tank }: { tank: Tank }) => {
  const navigate = useNavigate();

  return (
    <button
      onClick={() => navigate(`/tank/${tank.id}`)}
      className={`relative flex flex-col items-center gap-4 rounded-xl border-2 bg-card p-6 text-left shadow-sm card-hover cursor-pointer w-full ${statusBorder[tank.status]}`}
    >
      <div className="flex w-full items-center justify-between">
        <h3 className="text-base font-semibold text-card-foreground">{tank.name}</h3>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${statusBadge[tank.status]}`}>
          {tank.status}
        </span>
      </div>
      <div className="relative">
        <CircularGauge value={tank.stressScore} status={tank.status} showLabel />
      </div>
      <p className="text-xs text-muted-foreground text-center">{tank.insight}</p>
    </button>
  );
};

export default TankCard;
