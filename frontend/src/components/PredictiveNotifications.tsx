import { useState, useCallback } from 'react';
import { AlertTriangle, AlertCircle, CheckCircle, Clock, Volume2, VolumeX } from 'lucide-react';
import { type Notification, type TankStatus } from '@/data/dummyData';

const severityIcon: Record<TankStatus, React.ElementType> = {
  critical: AlertTriangle,
  warning: AlertCircle,
  safe: CheckCircle,
};

const severityStyle: Record<TankStatus, string> = {
  critical: 'border-l-critical bg-critical/5',
  warning: 'border-l-warning bg-warning/5',
  safe: 'border-l-safe bg-safe/5',
};

const severityOrder: Record<TankStatus, number> = { critical: 0, warning: 1, safe: 2 };

const NotificationCard = ({ notification }: { notification: Notification }) => {
  const [lang, setLang] = useState<'en' | 'si'>('en');
  const [speaking, setSpeaking] = useState(false);
  const Icon = severityIcon[notification.severity];

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
    <div className={`flex flex-col gap-2 rounded-lg border-l-4 border bg-card p-4 shadow-sm animate-fade-in ${severityStyle[notification.severity]}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <Icon className="mt-0.5 h-4 w-4 shrink-0" />
          <p className={`text-sm leading-relaxed text-card-foreground ${lang === 'si' ? 'font-sinhala' : ''}`}>
            {lang === 'en' ? notification.en : notification.si}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <button
            onClick={narrate}
            className={`rounded-md border p-1.5 text-muted-foreground transition-colors hover:bg-muted ${speaking ? 'bg-primary/10 text-primary border-primary/30' : 'bg-muted/50'}`}
            title={speaking ? 'Stop narration' : 'Listen to this notification'}
          >
            {speaking ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
          </button>
          <button
            onClick={() => setLang(l => l === 'en' ? 'si' : 'en')}
            className="rounded-md border bg-muted/50 px-2 py-0.5 text-[10px] font-medium text-muted-foreground hover:bg-muted transition-colors"
          >
            {lang === 'en' ? 'සිංහල' : 'EN'}
          </button>
        </div>
      </div>
      <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
        <Clock className="h-3 w-3" />
        {notification.timestamp}
      </div>
    </div>
  );
};

const PredictiveNotifications = ({ notifications }: { notifications: Notification[] }) => {
  const sorted = [...notifications].sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);

  return (
    <div className="rounded-xl border bg-card p-5 shadow-sm">
      <h4 className="mb-4 text-sm font-semibold text-card-foreground">🔮 Predictive Notifications</h4>
      <div className="flex flex-col gap-3">
        {sorted.map(n => (
          <NotificationCard key={n.id} notification={n} />
        ))}
      </div>
    </div>
  );
};

export default PredictiveNotifications;
