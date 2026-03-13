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
  const { addTank, tanks } = useTanks();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;

    if (tanks.some(t => t.name.toLowerCase() === trimmed.toLowerCase())) {
      toast.error('A tank with this name already exists');
      return;
    }

    addTank(trimmed);
    toast.success(`${trimmed} has been added`);
    setName('');
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
