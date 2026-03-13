import { NavLink } from 'react-router-dom';
import { Home, Plus, Fish, X, Moon, Sun } from 'lucide-react';
import { tanks } from '@/data/dummyData';
import { useTheme } from '@/hooks/useTheme';

const statusDot: Record<string, string> = {
  safe: 'bg-safe',
  warning: 'bg-warning',
  critical: 'bg-critical animate-pulse-soft',
};

interface AppSidebarProps {
  open: boolean;
  onClose: () => void;
}

const DarkModeToggle = () => {
  const { dark, toggle } = useTheme();
  return (
    <button
      onClick={toggle}
      className="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-sm font-medium text-sidebar-foreground transition-colors hover:bg-muted"
    >
      <div className="flex items-center gap-3">
        {dark ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
        <span>{dark ? 'Dark Mode' : 'Light Mode'}</span>
      </div>
      <div className={`relative h-5 w-9 rounded-full transition-colors ${dark ? 'bg-primary' : 'bg-muted-foreground/30'}`}>
        <div className={`absolute top-0.5 h-4 w-4 rounded-full bg-card shadow transition-transform ${dark ? 'translate-x-4' : 'translate-x-0.5'}`} />
      </div>
    </button>
  );
};

const AppSidebar = ({ open, onClose }: AppSidebarProps) => {
  return (
    <>
      {/* Overlay for mobile */}
      {open && (
        <div className="fixed inset-0 z-40 bg-foreground/20 backdrop-blur-sm lg:hidden" onClick={onClose} />
      )}

      <aside
        className={`fixed top-0 left-0 z-50 flex h-screen w-64 flex-col border-r bg-sidebar transition-transform duration-300 lg:sticky lg:top-0 lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Logo */}
        <div className="flex items-center justify-between border-b px-5 py-4">
          <div className="flex items-center gap-2.5">
            <Fish className="h-6 w-6 text-primary" />
            <span className="text-lg font-bold text-sidebar-foreground">AquaGuard</span>
          </div>
          <button onClick={onClose} className="rounded-md p-1 hover:bg-muted lg:hidden">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-4">
          <NavLink
            to="/"
            end
            onClick={onClose}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive ? 'bg-sidebar-accent text-sidebar-accent-foreground' : 'text-sidebar-foreground hover:bg-muted'
              }`
            }
          >
            <Home className="h-4 w-4" />
            Home
          </NavLink>

          <div className="mt-5 mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
            Tanks
          </div>

          {tanks.map(tank => (
            <NavLink
              key={tank.id}
              to={`/tank/${tank.id}`}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors ${
                  isActive ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium' : 'text-sidebar-foreground hover:bg-muted'
                }`
              }
            >
              <div className="flex items-center gap-3">
                <span className={`h-2 w-2 rounded-full ${statusDot[tank.status]}`} />
                <span>{tank.name}</span>
              </div>
              <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-bold ${
                tank.status === 'critical' ? 'bg-critical/10 text-critical' :
                tank.status === 'warning' ? 'bg-warning/10 text-warning' :
                'bg-safe/10 text-safe'
              }`}>
                {tank.stressScore}
              </span>
            </NavLink>
          ))}
        </nav>

        {/* Dark mode toggle + Add Tank */}
        <div className="border-t px-3 py-4 space-y-3">
          <DarkModeToggle />
          <button className="flex w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed border-muted-foreground/30 px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:border-primary hover:text-primary">
            <Plus className="h-4 w-4" />
            Add Tank
          </button>
        </div>
      </aside>
    </>
  );
};

export default AppSidebar;
