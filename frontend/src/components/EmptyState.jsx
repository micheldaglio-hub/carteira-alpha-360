import { Loader2 } from "lucide-react";

export function LoadingState({ label = "Carregando dados..." }) {
  return (
    <div className="flex h-72 items-center justify-center rounded-lg border border-dashed border-stone-200 bg-white">
      <div className="flex items-center gap-3 text-sm font-medium text-stone-500">
        <Loader2 className="animate-spin text-amber-700" size={18} />
        {label}
      </div>
    </div>
  );
}

export function ErrorState({ message }) {
  return (
    <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
      {message}
    </div>
  );
}
