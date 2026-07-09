"use client";

import { ChangeEvent, DragEvent, useId, useState } from "react";
import { FileText, Upload } from "lucide-react";

type FileDropProps = {
  label: string;
  helper: string;
  accept: string;
  file: File | null;
  onFile: (file: File | null) => void;
};

export function FileDrop({ label, helper, accept, file, onFile }: FileDropProps) {
  const id = useId();
  const [dragging, setDragging] = useState(false);

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    onFile(event.target.files?.[0] ?? null);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    onFile(event.dataTransfer.files?.[0] ?? null);
  }

  return (
    <label
      htmlFor={id}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={[
        "flex min-h-44 cursor-pointer flex-col justify-between rounded border-2 border-dashed bg-white p-5 transition",
        dragging ? "border-teal bg-teal/5" : "border-line hover:border-teal"
      ].join(" ")}
    >
      <span className="flex items-start gap-3">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded bg-teal/10 text-teal">
          <Upload aria-hidden="true" size={24} />
        </span>
        <span>
          <span className="block text-lg font-semibold text-ink">{label}</span>
          <span className="mt-1 block text-base leading-6 text-slate-600">{helper}</span>
        </span>
      </span>
      <span className="mt-5 flex items-center gap-2 rounded bg-mist px-3 py-2 text-base text-slate-700">
        <FileText aria-hidden="true" size={20} />
        <span className="min-w-0 truncate">{file ? file.name : "No file selected"}</span>
      </span>
      <input id={id} className="sr-only" type="file" accept={accept} onChange={handleChange} />
    </label>
  );
}
