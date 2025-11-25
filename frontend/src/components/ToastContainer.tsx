/**
 * Toast container component for displaying toast notifications.
 */

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, CheckCircle, AlertTriangle, Info, AlertCircle } from "lucide-react";
import { Toast } from "../hooks/useToast";

interface ToastContainerProps {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}

export function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  const getIcon = (type: Toast["type"]) => {
    switch (type) {
      case "success":
        return <CheckCircle size={20} className="text-green-500" />;
      case "error":
        return <AlertCircle size={20} className="text-red-500" />;
      case "warning":
        return <AlertTriangle size={20} className="text-yellow-500" />;
      case "info":
        return <Info size={20} className="text-cyan" />;
    }
  };

  const getBgColor = (type: Toast["type"]) => {
    switch (type) {
      case "success":
        return "bg-green-500/20 border-green-500/50";
      case "error":
        return "bg-red-500/20 border-red-500/50";
      case "warning":
        return "bg-yellow-500/20 border-yellow-500/50";
      case "info":
        return "bg-cyan/20 border-cyan/50";
    }
  };

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, x: 100 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 100 }}
            transition={{ duration: 0.2 }}
            className="pointer-events-auto"
          >
            <div
              className={`
                flex items-center gap-3 p-4 rounded-lg border backdrop-blur-sm
                ${getBgColor(toast.type)}
                shadow-lg min-w-[300px] max-w-[500px]
              `}
            >
              <div className="flex-shrink-0">{getIcon(toast.type)}</div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white font-mono break-words">
                  {toast.message}
                </p>
              </div>
              <button
                onClick={() => onDismiss(toast.id)}
                className="flex-shrink-0 p-1 hover:bg-white/10 rounded text-gray-400 hover:text-white transition-colors"
              >
                <X size={16} />
              </button>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

