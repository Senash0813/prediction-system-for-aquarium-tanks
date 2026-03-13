import { useNavigate } from 'react-router-dom';
import { Trash2 } from 'lucide-react';
import CircularGauge from './CircularGauge';
import { type Tank } from '@/data/dummyData';
import { useTanks } from '@/context/TanksContext';
import { toast } from 'sonner';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';

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
  const { deleteTank } = useTanks();

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
  };

  return (
    <div
      onClick={() => navigate(`/tank/${tank.id}`)}
      className={`group relative flex flex-col items-center gap-4 rounded-xl border-2 bg-card p-6 text-left shadow-sm card-hover cursor-pointer w-full ${statusBorder[tank.status]}`}
    >
      {/* Delete button */}
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <button
            onClick={handleDelete}
            className="absolute top-2 right-2 rounded-md p-1.5 text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </AlertDialogTrigger>
        <AlertDialogContent onClick={e => e.stopPropagation()}>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {tank.name}?</AlertDialogTitle>
            <AlertDialogDescription>
              This will remove the tank and all its monitoring data. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                deleteTank(tank.id);
                toast.success(`${tank.name} has been deleted`);
              }}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

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
    </div>
  );
};

export default TankCard;