import { useState } from 'react';
import { Menu } from 'lucide-react';
import AppSidebar from './AppSidebar';

const Layout = ({ children }: { children: React.ReactNode }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex min-h-screen w-full bg-background">
      <AppSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex flex-1 flex-col">
        {/* Mobile header */}
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b bg-card/80 backdrop-blur-sm px-4 py-3 lg:hidden">
          <button onClick={() => setSidebarOpen(true)} className="rounded-md p-1.5 hover:bg-muted">
            <Menu className="h-5 w-5" />
          </button>
          <span className="text-sm font-semibold">AquaGuard</span>
        </header>
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
