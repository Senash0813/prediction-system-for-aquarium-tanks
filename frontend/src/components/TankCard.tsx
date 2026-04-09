import { useNavigate } from 'react-router-dom';
import { Trash2 } from 'lucide-react';
import CircularGauge from './CircularGauge';
import { type Tank } from '@/data/dummyData';
import { useTanks } from '@/context/TanksContext';
import { toast } from 'sonner';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
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
  safe: 'border-safe/60 hover:border-safe dark:border-safe/60',
  warning: 'border-warning/60 hover:border-warning dark:border-warning/60',
  critical: 'border-critical/60 hover:border-critical dark:border-critical/60',
};

const statusBadge: Record<string, string> = {
  safe: 'bg-safe/20 text-safe dark:bg-safe/15',
  warning: 'bg-warning/20 text-warning dark:bg-warning/15',
  critical: 'bg-critical/20 text-critical dark:bg-critical/15',
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
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              className="inline-flex rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
              role="button"
              tabIndex={0}
              aria-label="What does the stress score mean?"
              onClick={(e) => e.stopPropagation()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  e.stopPropagation();
                }
              }}
            >
              <CircularGauge value={tank.stressScore} status={tank.status} showLabel />
            </div>
          </TooltipTrigger>
          <TooltipContent side="top" className="max-w-[260px]">
            <div className="space-y-1">
              <p className="text-xs font-semibold">Stress Score</p>
              <p className="text-xs text-muted-foreground">
                A simple 0–100 estimate of fish stress risk from recent readings. Lower is better.
              </p>
              <p className="text-xs text-muted-foreground">LOW = Safe • MEDIUM = Watch • HIGH = Act now</p>
            </div>
          </TooltipContent>
        </Tooltip>
      </div>
      <p className="text-xs text-muted-foreground text-center">{tank.insight}</p>
    </div>
  );
};

export default TankCard;