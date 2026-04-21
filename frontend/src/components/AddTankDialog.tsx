import { useState } from 'react';
import { Plus } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useTanks } from '@/context/TanksContext';
import { toast } from 'sonner';
import '@/styles/responsive.css';

interface AddTankDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const AddTankDialog = ({ open, onOpenChange }: AddTankDialogProps) => {
  const [name, setName] = useState('');
  const [temperatureMin, setTemperatureMin] = useState('24');
  const [temperatureMax, setTemperatureMax] = useState('30');
  const [phMin, setPhMin] = useState('6.5');
  const [phMax, setPhMax] = useState('7.8');
  const [turbidityMin, setTurbidityMin] = useState('');
  const [turbidityMax, setTurbidityMax] = useState('');
  const [lightMin, setLightMin] = useState('');
  const [lightMax, setLightMax] = useState('');
  const [tdsMin, setTdsMin] = useState('150');
  const [tdsMax, setTdsMax] = useState('400');
  const [macAddress, setMacAddress] = useState('');
  const { addTank, tanks } = useTanks();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedName = name.trim();

    if (
      !trimmedName ||
      !macAddress.trim() ||
      !temperatureMin || !temperatureMax ||
      !phMin || !phMax ||
      !turbidityMin || !turbidityMax ||
      !lightMin || !lightMax ||
      !tdsMin || !tdsMax
    ) {
      toast.error('Please fill in all fields');
      return;
    }

    const numericFields = [
      temperatureMin, temperatureMax, phMin, phMax,
      turbidityMin, turbidityMax, lightMin, lightMax, tdsMin, tdsMax,
    ];
    if (numericFields.some(v => isNaN(parseFloat(v)))) {
      toast.error('All parameter values must be valid numbers');
      return;
    }

    if (parseFloat(temperatureMin) >= parseFloat(temperatureMax)) {
      toast.error('Temperature: Min must be less than Max');
      return;
    }
    if (parseFloat(phMin) >= parseFloat(phMax)) {
      toast.error('pH: Min must be less than Max');
      return;
    }
    if (parseFloat(turbidityMin) >= parseFloat(turbidityMax)) {
      toast.error('Turbidity: Min must be less than Max');
      return;
    }
    if (parseFloat(lightMin) >= parseFloat(lightMax)) {
      toast.error('Light: Min must be less than Max');
      return;
    }
    if (parseFloat(tdsMin) >= parseFloat(tdsMax)) {
      toast.error('TDS: Min must be less than Max');
      return;
    }

    const macRegex = /^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$/;
    if (!macRegex.test(macAddress.trim())) {
      toast.error('Please enter a valid MAC address (e.g. A4:CF:12:78:3B:01)');
      return;
    }

    if (tanks.some(t => t.name.toLowerCase() === trimmedName.toLowerCase())) {
      toast.error('A tank with this name already exists');
      return;
    }

    try {
      await addTank(trimmedName, {
        temperatureMin, temperatureMax,
        phMin, phMax,
        turbidityMin, turbidityMax,
        lightMin, lightMax,
        tdsMin, tdsMax,
        macAddress: macAddress.trim().toUpperCase(),
      });
      toast.success(`${trimmedName} has been added`);
      setName('');
      setTemperatureMin('24'); setTemperatureMax('30');
      setPhMin('6.5'); setPhMax('7.8');
      setTurbidityMin(''); setTurbidityMax('');
      setLightMin(''); setLightMax('');
      setTdsMin('150'); setTdsMax('400');
      setMacAddress('');
      onOpenChange(false);
    } catch (err: any) {
      toast.error(`Failed to save tank: ${err?.message ?? 'Unknown error'}`);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Add New Tank</DialogTitle>
          <DialogDescription>Set the safe parameter ranges for your new tank.</DialogDescription>
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

          {/* MAC Address */}
          <div className="space-y-2">
            <Label htmlFor="mac-address">Device MAC Address</Label>
            <Input
              id="mac-address"
              placeholder="e.g. A4:CF:12:78:3B:01"
              value={macAddress}
              onChange={e => setMacAddress(e.target.value)}
            />
          </div>

          {/* Temperature */}
          <div className="space-y-2">
            <Label>Temperature (°C)</Label>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="temp-min" className="text-xs text-muted-foreground mb-1 block">Min</Label>
                <Input id="temp-min"placeholder="e.g. 22" value={temperatureMin} onChange={e => setTemperatureMin(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="temp-max" className="text-xs text-muted-foreground mb-1 block">Max</Label>
                <Input id="temp-max"placeholder="e.g. 28" value={temperatureMax} onChange={e => setTemperatureMax(e.target.value)} />
              </div>
            </div>
          </div>

          {/* pH */}
          <div className="space-y-2">
            <Label>pH Level</Label>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="ph-min" className="text-xs text-muted-foreground mb-1 block">Min</Label>
                <Input id="ph-min"placeholder="e.g. 6.5" value={phMin} onChange={e => setPhMin(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="ph-max" className="text-xs text-muted-foreground mb-1 block">Max</Label>
                <Input id="ph-max"placeholder="e.g. 7.5" value={phMax} onChange={e => setPhMax(e.target.value)} />
              </div>
            </div>
          </div>

          {/* Turbidity */}
          <div className="space-y-2">
            <Label>Turbidity (NTU)</Label>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="turb-min" className="text-xs text-muted-foreground mb-1 block">Min</Label>
                <Input id="turb-min"placeholder="e.g. 0" value={turbidityMin} onChange={e => setTurbidityMin(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="turb-max" className="text-xs text-muted-foreground mb-1 block">Max</Label>
                <Input id="turb-max"placeholder="e.g. 10" value={turbidityMax} onChange={e => setTurbidityMax(e.target.value)} />
              </div>
            </div>
          </div>

          {/* Light */}
          <div className="space-y-2">
            <Label>Light (lux)</Label>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="light-min" className="text-xs text-muted-foreground mb-1 block">Min</Label>
                <Input id="light-min"placeholder="e.g. 100" value={lightMin} onChange={e => setLightMin(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="light-max" className="text-xs text-muted-foreground mb-1 block">Max</Label>
                <Input id="light-max"placeholder="e.g. 500" value={lightMax} onChange={e => setLightMax(e.target.value)} />
              </div>
            </div>
          </div>

          {/* TDS */}
          <div className="space-y-2">
            <Label>TDS (ppm)</Label>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="tds-min" className="text-xs text-muted-foreground mb-1 block">Min</Label>
                <Input id="tds-min"placeholder="e.g. 200" value={tdsMin} onChange={e => setTdsMin(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="tds-max" className="text-xs text-muted-foreground mb-1 block">Max</Label>
                <Input id="tds-max"placeholder="e.g. 600" value={tdsMax} onChange={e => setTdsMax(e.target.value)} />
              </div>
            </div>
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
