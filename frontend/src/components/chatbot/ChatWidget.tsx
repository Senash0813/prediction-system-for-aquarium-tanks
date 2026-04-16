import { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Bot, Trash2 } from 'lucide-react';
import { useChatContext } from './ChatContext';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import { sendChatMessage } from '@/api/client';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

const WELCOME_MESSAGE: Message = {
  id: 'welcome',
  role: 'assistant',
  content: "Hi! I'm your AquaGuard Assistant. Ask me anything about your tanks, metrics, trends, or alerts.",
};

const ChatWidget = () => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [loading, setLoading] = useState(false);
  const { pageContext } = useChatContext();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
    }
  }, [messages, open]);

  const handleSend = async (text: string) => {
    const userMsg: Message = { id: `u-${Date.now()}`, role: 'user', content: text };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setLoading(true);

    try {
      const history = updatedMessages
        .filter(m => m.id !== 'welcome')
        .slice(0, -1)
        .map(m => ({ role: m.role, content: m.content }));

      const reply = await sendChatMessage(text, pageContext, history);
      setMessages(prev => [
        ...prev,
        { id: `a-${Date.now()}`, role: 'assistant', content: reply },
      ]);
    } catch {
      setMessages(prev => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: 'assistant',
          content: 'Sorry, I could not get a response. Please check your connection and try again.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([WELCOME_MESSAGE]);
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
      {open && (
        <div className="flex flex-col w-[420px] h-[620px] rounded-xl border border-border bg-card shadow-2xl overflow-hidden animate-fade-in">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3.5 bg-primary text-primary-foreground shrink-0">
            <div className="flex items-center gap-2.5">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/15">
                <Bot className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-semibold leading-none">AquaGuard Assistant</p>
                <p className="text-[10px] text-primary-foreground/70 mt-0.5">Ask about your tanks</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={handleClear}
                title="Clear chat"
                className="rounded-md p-1.5 hover:bg-white/20 transition-colors"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => setOpen(false)}
                className="rounded-md p-1.5 hover:bg-white/20 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-background">
            {messages.map(msg => (
              <ChatMessage key={msg.id} role={msg.role} content={msg.content} />
            ))}

            {loading && (
              <div className="flex gap-1.5 pl-10 items-center">
                <span
                  className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce"
                  style={{ animationDelay: '0ms' }}
                />
                <span
                  className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce"
                  style={{ animationDelay: '150ms' }}
                />
                <span
                  className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce"
                  style={{ animationDelay: '300ms' }}
                />
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <ChatInput onSend={handleSend} disabled={loading} />
        </div>
      )}

      {/* Toggle button */}
      <button
        onClick={() => setOpen(prev => !prev)}
        className="flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg hover:bg-primary/90 active:scale-95 transition-all"
        aria-label={open ? 'Close chat' : 'Open AquaGuard Assistant'}
      >
        {open ? <X className="h-6 w-6" /> : <MessageCircle className="h-6 w-6" />}
      </button>
    </div>
  );
};

export default ChatWidget;
