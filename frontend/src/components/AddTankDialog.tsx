import { useState } from 'react';
import { Plus } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useTanks } from '@/context/TanksContext';
import { toast } from 'sonner';

interface AddTankDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const AddTankDialog = ({ open, onOpenChange }: AddTankDialogProps) => {
  const [name, setName] = useState('');
  const [temperature, setTemperature] = useState('');
  const [ph, setPh] = useState('');
  const [turbidity, setTurbidity] = useState('');
  const [light, setLight] = useState('');
  const [tds, setTds] = useState('');
  const { addTank, tanks } = useTanks();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedName = name.trim();
    const trimmedTemperature = temperature.trim();
    const trimmedPh = ph.trim();
    const trimmedTurbidity = turbidity.trim();
    const trimmedLight = light.trim();
    const trimmedTds = tds.trim();

    if (!trimmedName || !trimmedTemperature || !trimmedPh || !trimmedTurbidity || !trimmedLight || !trimmedTds) {
      return;
    }

    if (tanks.some(t => t.name.toLowerCase() === trimmedName.toLowerCase())) {
      toast.error('A tank with this name already exists');
      return;
    }

    addTank(trimmedName, {
      temperature: trimmedTemperature,
      ph: trimmedPh,
      turbidity: trimmedTurbidity,
      light: trimmedLight,
      tds: trimmedTds,
    });

    toast.success(`${trimmedName} has been added`);
    setName('');
    setTemperature('');
    setPh('');
    setTurbidity('');
    setLight('');
    setTds('');
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add New Tank</DialogTitle>
          <DialogDescription>Give your new tank a name to start monitoring.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="tank-name">Tank Name</Label>
            <Input
              id="tank-name"
              placeholder="e.g. Tank E"
              value={name}
              onChange={e => setName(e.target.value)}
              autoFocus
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="tank-temperature">Safe Temperature</Label>
            <Input
              id="tank-temperature"
              placeholder="e.g. 25°C"
              value={temperature}
              onChange={e => setTemperature(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="tank-ph">Safe pH</Label>
            <Input
              id="tank-ph"
              placeholder="e.g. 7.5"
              value={ph}
              onChange={e => setPh(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="tank-turbidity">Safe Turbidity</Label>
            <Input
              id="tank-turbidity"
              placeholder="e.g. 5 NTU"
              value={turbidity}
              onChange={e => setTurbidity(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="tank-light">Safe Light</Label>
            <Input
              id="tank-light"
              placeholder="e.g. 300 lux"
              value={light}
              onChange={e => setLight(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="tank-tds">Safe TDS</Label>
            <Input
              id="tank-tds"
              placeholder="e.g. 500 ppm"
              value={tds}
              onChange={e => setTds(e.target.value)}
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!name.trim()}>
              <Plus className="h-4 w-4" />
              Add Tank
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default AddTankDialog;
