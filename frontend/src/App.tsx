import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { TanksProvider } from "./context/TanksContext";
import Layout from "./components/Layout";
import Index from "./pages/Index";
import TankDashboard from "./pages/TankDashboard";
import MetricDetail from "./pages/MetricDetail";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <TanksProvider>
          <Layout>
            <Routes>
              <Route path="/" element={<Index />} />
              <Route path="/tank/:tankId" element={<TankDashboard />} />
              <Route path="/tank/:tankId/metric/:metricId" element={<MetricDetail />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Layout>
        </TanksProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;