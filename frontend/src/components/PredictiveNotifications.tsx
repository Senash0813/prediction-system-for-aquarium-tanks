import { useState, useCallback } from 'react';
import { AlertTriangle, AlertCircle, CheckCircle, Clock, Volume2, VolumeX, Bell } from 'lucide-react';
import { type Notification, type TankStatus } from '@/data/dummyData';

const severityIcon: Record<TankStatus, React.ElementType> = {
  critical: AlertTriangle,
  warning: AlertCircle,
  safe: CheckCircle,
};

const severityStyle: Record<TankStatus, { card: string; icon: string; badge: string }> = {
  critical: {
    card: 'border-l-critical bg-critical/5 dark:bg-critical/8',
    icon: 'text-critical',
    badge: 'bg-critical/10 text-critical border-critical/20',
  },
  warning: {
    card: 'border-l-warning bg-warning/5 dark:bg-warning/8',
    icon: 'text-warning',
    badge: 'bg-warning/10 text-warning border-warning/20',
  },
  safe: {
    card: 'border-l-safe bg-safe/5 dark:bg-safe/8',
    icon: 'text-safe',
    badge: 'bg-safe/10 text-safe border-safe/20',
  },
};

const severityOrder: Record<TankStatus, number> = { critical: 0, warning: 1, safe: 2 };

const kindLabel = (kind: string) => kind.replace(/_/g, ' ');

const NotificationCard = ({ notification }: { notification: Notification }) => {
  const [lang, setLang] = useState<'en' | 'si'>('en');
  const [speaking, setSpeaking] = useState(false);
  const Icon = severityIcon[notification.severity];
  const style = severityStyle[notification.severity];

  const narrate = useCallback(() => {
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }
    const text = lang === 'en' ? notification.en : notification.si;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang === 'en' ? 'en-US' : 'si-LK';
    utterance.rate = 0.9;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(utterance);
  }, [lang, notification, speaking]);

  return (
    <div className={`flex flex-col gap-2.5 rounded-xl border-l-4 border bg-card p-4 shadow-sm transition-shadow hover:shadow-md animate-fade-in ${style.card}`}>
      {/* Header row: icon + kind badge + actions */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon className={`h-4 w-4 shrink-0 ${style.icon}`} />
          {notification.kind && (
            <span className={`rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${style.badge}`}>
              {kindLabel(notification.kind)}
            </span>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <button
            onClick={narrate}
            className={`rounded-lg border p-1.5 text-muted-foreground transition-colors hover:bg-muted ${speaking ? 'bg-primary/10 text-primary border-primary/30' : 'bg-muted/40'}`}
            title={speaking ? 'Stop narration' : 'Listen to this notification'}
          >
            {speaking ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
          </button>
          <button
            onClick={() => setLang(l => l === 'en' ? 'si' : 'en')}
            className="rounded-lg border bg-muted/40 px-2.5 py-1 text-[10px] font-semibold text-muted-foreground hover:bg-muted transition-colors"
          >
            {lang === 'en' ? 'සිංහල' : 'EN'}
          </button>
        </div>
      </div>

      {/* Message body */}
      <p className={`text-sm leading-relaxed text-card-foreground pl-6 ${lang === 'si' ? 'font-sinhala' : ''}`}>
        {lang === 'en' ? notification.en : notification.si}
      </p>

      {/* Timestamp */}
      <div className="flex items-center gap-1.5 pl-6 text-[10px] text-muted-foreground/70">
        <Clock className="h-3 w-3" />
        <span>{notification.timestamp}</span>
        <span className="ml-0.5 text-muted-foreground/40">IST</span>
      </div>
    </div>
  );
};

const PredictiveNotifications = ({ notifications }: { notifications: Notification[] }) => {
  const sorted = [...notifications].sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);
  const criticalCount = sorted.filter(n => n.severity === 'critical').length;
  const warningCount = sorted.filter(n => n.severity === 'warning').length;

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Section header */}
      <div className="flex items-center justify-between border-b bg-muted/20 px-5 py-3.5">
        <div className="flex items-center gap-2">
          <Bell className="h-4 w-4 text-muted-foreground" />
          <h4 className="text-sm font-semibold text-card-foreground">Predictive Notifications</h4>
        </div>
        <div className="flex items-center gap-1.5">
          {criticalCount > 0 && (
            <span className="rounded-full bg-critical/10 border border-critical/20 px-2 py-0.5 text-[10px] font-semibold text-critical">
              {criticalCount} critical
            </span>
          )}
          {warningCount > 0 && (
            <span className="rounded-full bg-warning/10 border border-warning/20 px-2 py-0.5 text-[10px] font-semibold text-warning">
              {warningCount} warning
            </span>
          )}
        </div>
      </div>

      {/* Cards */}
      <div className="flex flex-col gap-3 p-4">
        {sorted.map(n => (
          <NotificationCard key={n.id} notification={n} />
        ))}
      </div>
    </div>
  );
};

export default PredictiveNotifications;
