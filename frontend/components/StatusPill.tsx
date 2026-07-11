import { AlertTriangle, CheckCircle2 } from "lucide-react";
import type { FieldStatus } from "@/lib/types";

const STATUS_COPY: Record<FieldStatus, { text: string; className: string; icon: typeof CheckCircle2 }> = {
  match: {
    text: "Match",
    className: "bg-emerald-50 text-emerald-800 ring-emerald-200",
    icon: CheckCircle2
  },
  mismatch: {
    text: "Mismatch",
    className: "bg-red-50 text-red-800 ring-red-200",
    icon: AlertTriangle
  }
};

export function StatusPill({ status }: { status: FieldStatus }) {
  const config = STATUS_COPY[status];
  const Icon = config.icon;
  return (
    <span
      className={`inline-flex min-w-32 items-center justify-center gap-2 rounded px-3 py-1.5 text-sm font-semibold ring-1 ${config.className}`}
    >
      <Icon aria-hidden="true" size={18} />
      {config.text}
    </span>
  );
}
