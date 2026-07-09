import { AlertTriangle, CheckCircle2, HelpCircle } from "lucide-react";
import type { Status } from "@/lib/types";

const STATUS_COPY: Record<Status, { text: string; className: string; icon: typeof CheckCircle2 }> = {
  match: {
    text: "Match",
    className: "bg-emerald-50 text-emerald-800 ring-emerald-200",
    icon: CheckCircle2
  },
  review: {
    text: "Needs review",
    className: "bg-amber-50 text-amber-900 ring-amber-200",
    icon: HelpCircle
  },
  fail: {
    text: "Mismatch",
    className: "bg-red-50 text-red-800 ring-red-200",
    icon: AlertTriangle
  }
};

export function StatusPill({ status }: { status: Status }) {
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
