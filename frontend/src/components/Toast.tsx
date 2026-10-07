import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";

interface ToastAction {
  label: string;
  onClick: () => void;
}

interface ToastItem {
  id: number;
  message: string;
  action?: ToastAction;
}

type Notify = (message: string, action?: ToastAction) => void;

const ToastContext = createContext<Notify>(() => {});

export function useToast(): Notify {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => setItems((all) => all.filter((t) => t.id !== id)), []);

  const notify = useCallback<Notify>(
    (message, action) => {
      const id = nextId.current++;
      setItems((all) => [...all.slice(-2), { id, message, action }]);
      window.setTimeout(() => dismiss(id), action ? 7000 : 4000);
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={notify}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className="toast">
            <span>{t.message}</span>
            {t.action && (
              <button
                type="button"
                className="btn btn-sm"
                onClick={() => {
                  t.action?.onClick();
                  dismiss(t.id);
                }}
              >
                {t.action.label}
              </button>
            )}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
