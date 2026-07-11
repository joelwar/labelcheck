"use client";

import { FormEvent, useMemo, useState } from "react";
import { AlertTriangle, Check, ChevronRight, FileText, Loader2, Upload, X } from "lucide-react";
import type { Mode, Status, VerifyResponse } from "@/lib/types";

const FORM_ACCEPT = ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";
const LABEL_ACCEPT = ".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg";
const COMBINED_ACCEPT = ".pdf,application/pdf";

const OVERALL_COPY: Record<Status, { text: string; sub: string }> = {
  match: {
    text: "All fields verified",
    sub: "No discrepancies found between application and label."
  },
  review: {
    text: "Minor discrepancies found",
    sub: "Formatting differences only. Recommend an agent confirms."
  },
  fail: {
    text: "Discrepancies require review",
    sub: "One or more fields do not match the application."
  }
};

function StatusPill({ status }: { status: Status }) {
  const map = {
    match: { icon: Check, text: "Match", cls: "pill-match" },
    review: { icon: AlertTriangle, text: "Needs Review", cls: "pill-review" },
    fail: { icon: X, text: "Mismatch", cls: "pill-fail" }
  };
  const { icon: Icon, text, cls } = map[status];
  return (
    <span className={`pill ${cls}`}>
      <Icon size={14} strokeWidth={2.5} aria-hidden="true" />
      {text}
    </span>
  );
}

function UploadSlot({
  label,
  hint,
  file,
  onFile,
  accept
}: {
  label: string;
  hint: string;
  file: File | null;
  onFile: (file: File | null) => void;
  accept: string;
}) {
  return (
    <label className="lv-upload-slot">
      <input
        type="file"
        accept={accept}
        onChange={(event) => onFile(event.target.files?.[0] || null)}
      />
      <div className="lv-upload-icon">
        {file ? <FileText size={18} aria-hidden="true" /> : <Upload size={18} aria-hidden="true" />}
      </div>
      <div className="lv-upload-text">
        <div className="lv-upload-label">{label}</div>
        <div className="lv-upload-hint">{file ? file.name : hint}</div>
      </div>
    </label>
  );
}

export default function Home() {
  const [mode, setMode] = useState<Mode>("separate");
  const [applicationFile, setApplicationFile] = useState<File | null>(null);
  const [labelFile, setLabelFile] = useState<File | null>(null);
  const [combinedFile, setCombinedFile] = useState<File | null>(null);
  const [result, setResult] = useState<VerifyResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const canSubmit = useMemo(() => {
    return mode === "separate" ? Boolean(applicationFile && labelFile) : Boolean(combinedFile);
  }, [applicationFile, combinedFile, labelFile, mode]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setResult(null);

    if (!canSubmit) {
      setError("Please choose the required file or files before running verification.");
      return;
    }

    const formData = new FormData();
    formData.append("mode", mode);
    if (mode === "separate") {
      formData.append("application_file", applicationFile as File);
      formData.append("label_file", labelFile as File);
    } else {
      formData.append("combined_file", combinedFile as File);
    }

    setLoading(true);
    try {
      const response = await fetch("/api/verify", {
        method: "POST",
        body: formData
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(payload?.detail || "Verification could not be completed. Please try again.");
      }
      setResult(payload as VerifyResponse);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Verification could not be completed.");
    } finally {
      setLoading(false);
    }
  }

  const overallCopy = result ? OVERALL_COPY[result.overall_status] : null;

  return (
    <main className="lv-root">
      <style>{`
        .lv-root {
          --ink: #1c2a24;
          --paper: #f6f4ee;
          --paper-line: #d9d4c6;
          --brass: #8a6d3b;
          --green: #2f6b4f;
          --amber: #a4720f;
          --red: #a3372f;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          background: var(--paper);
          color: var(--ink);
          min-height: 100vh;
          padding: 32px 20px;
          box-sizing: border-box;
        }
        .lv-container { max-width: 760px; margin: 0 auto; }
        .lv-header { margin-bottom: 24px; border-bottom: 2px solid var(--ink); padding-bottom: 16px; }
        .lv-eyebrow {
          font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase;
          color: var(--brass); font-weight: 700; margin-bottom: 6px;
        }
        .lv-title { font-size: 24px; font-weight: 700; margin: 0 0 4px 0; letter-spacing: 0; }
        .lv-subtitle { font-size: 14px; color: #55584f; margin: 0; line-height: 1.45; }

        .lv-section-label {
          font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;
          color: var(--brass); margin: 22px 0 10px 0;
        }

        .lv-mode-toggle { display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }
        .lv-mode-btn {
          font-size: 13px; padding: 7px 12px; border-radius: 6px;
          border: 1.5px solid var(--paper-line); background: #fff; color: #55584f;
          cursor: pointer; font-family: inherit;
        }
        .lv-mode-btn.active { border-color: var(--green); color: var(--green); font-weight: 700; background: #eef4f0; }
        .lv-mode-btn:focus-visible, .lv-run-btn:focus-visible, .lv-upload-slot:focus-within {
          outline: 3px solid rgba(47, 107, 79, 0.28);
          outline-offset: 2px;
        }

        .lv-upload-row { display: flex; gap: 12px; margin-bottom: 8px; flex-wrap: wrap; }
        .lv-upload-slot {
          flex: 1 1 220px; display: flex; align-items: center; gap: 12px;
          border: 1.5px dashed var(--paper-line); border-radius: 8px; background: #fff;
          padding: 14px 16px; cursor: pointer; transition: border-color 0.15s ease;
          min-height: 74px; box-sizing: border-box;
        }
        .lv-upload-slot:hover { border-color: var(--brass); }
        .lv-upload-slot input { position: absolute; opacity: 0; pointer-events: none; }
        .lv-upload-icon {
          width: 34px; height: 34px; border-radius: 6px; background: #f0ede2;
          display: flex; align-items: center; justify-content: center; color: var(--brass); flex-shrink: 0;
        }
        .lv-upload-text { min-width: 0; }
        .lv-upload-label { font-size: 13.5px; font-weight: 700; }
        .lv-upload-hint {
          font-size: 12px; color: #8a8d82; margin-top: 2px;
          overflow-wrap: anywhere; line-height: 1.35;
        }
        .lv-upload-note { font-size: 12px; color: #8a8d82; margin: 10px 0 0 0; font-style: italic; line-height: 1.5; }

        .lv-run-btn {
          display: inline-flex; align-items: center; justify-content: center; gap: 8px;
          font-size: 14px; font-weight: 600; padding: 10px 18px; border-radius: 6px;
          border: none; background: var(--green); color: #fff; cursor: pointer;
          font-family: inherit; margin: 18px 0 24px 0; min-height: 42px;
        }
        .lv-run-btn:hover { opacity: 0.92; }
        .lv-run-btn:disabled { cursor: not-allowed; background: #8a8d82; opacity: 0.8; }

        .lv-alert {
          display: flex; gap: 10px; align-items: flex-start;
          border: 1.5px solid #e0b4ae; background: #fff4f2; color: var(--red);
          padding: 12px 14px; border-radius: 8px; margin: 14px 0 0 0;
          font-size: 13.5px; line-height: 1.45;
        }
        .lv-alert svg { flex-shrink: 0; margin-top: 1px; }

        .lv-summary {
          display: flex; align-items: center; justify-content: space-between; gap: 16px;
          padding: 16px 18px; border-radius: 8px; margin-bottom: 20px;
          border: 1.5px solid var(--paper-line); background: #fff;
        }
        .lv-summary-text { font-size: 15px; font-weight: 700; margin: 0 0 2px 0; }
        .lv-summary-sub { font-size: 13px; color: #6b6e64; margin: 0; line-height: 1.4; }

        .lv-table-wrap { overflow-x: auto; border-radius: 8px; }
        table.lv-table {
          width: 100%; min-width: 700px; border-collapse: collapse; background: #fff;
          border-radius: 8px; overflow: hidden; border: 1.5px solid var(--paper-line);
        }
        .lv-table th {
          text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em;
          color: #6b6e64; padding: 10px 14px; border-bottom: 1.5px solid var(--paper-line); font-weight: 700;
        }
        .lv-table td { padding: 12px 14px; border-bottom: 1px solid var(--paper-line); font-size: 13.5px; vertical-align: top; }
        .lv-table tr:last-child td { border-bottom: none; }
        .lv-field-name { font-weight: 700; white-space: nowrap; }
        .lv-val { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12.5px; color: #33362e; overflow-wrap: anywhere; }

        .pill {
          display: inline-flex; align-items: center; justify-content: center; gap: 5px;
          font-size: 12px; font-weight: 700; padding: 4px 9px; border-radius: 100px;
          white-space: nowrap; min-width: 76px;
        }
        .pill-match { background: #e2ede6; color: var(--green); }
        .pill-review { background: #f3e9d6; color: var(--amber); }
        .pill-fail { background: #f3e0dd; color: var(--red); }

        .lv-footnote { font-size: 12px; color: #8a8d82; margin-top: 20px; line-height: 1.5; }
        .lv-spinner { animation: lv-spin 1s linear infinite; }
        @keyframes lv-spin { to { transform: rotate(360deg); } }

        @media (max-width: 640px) {
          .lv-root { padding: 24px 14px; }
          .lv-summary { align-items: flex-start; flex-direction: column; }
          .lv-run-btn { width: 100%; }
        }
      `}</style>

      <div className="lv-container">
        <div className="lv-header">
          <div className="lv-eyebrow">Label Verification - Prototype</div>
          <h1 className="lv-title">Application Form vs. Submitted Label Image</h1>
          <p className="lv-subtitle">
            Every COLA submission has two parts: the fields the applicant typed in, and the actual
            label artwork they attached. This tool checks that the two agree.
          </p>
        </div>

        <form onSubmit={submit}>
          <div className="lv-section-label">1. Provide the submission</div>
          <div className="lv-mode-toggle">
            <button
              type="button"
              className={`lv-mode-btn ${mode === "separate" ? "active" : ""}`}
              onClick={() => setMode("separate")}
            >
              Two files (form + label image)
            </button>
            <button
              type="button"
              className={`lv-mode-btn ${mode === "combined" ? "active" : ""}`}
              onClick={() => setMode("combined")}
            >
              One combined file (e.g. single PDF)
            </button>
          </div>

          {mode === "separate" ? (
            <div className="lv-upload-row">
              <UploadSlot
                label="Application Form"
                hint="PDF or DOCX with typed field data"
                file={applicationFile}
                onFile={setApplicationFile}
                accept={FORM_ACCEPT}
              />
              <UploadSlot
                label="Label Image"
                hint="Photo or scan of the actual label artwork"
                file={labelFile}
                onFile={setLabelFile}
                accept={LABEL_ACCEPT}
              />
            </div>
          ) : (
            <div className="lv-upload-row">
              <UploadSlot
                label="Combined Submission"
                hint="Single PDF containing both the form data and label image"
                file={combinedFile}
                onFile={setCombinedFile}
                accept={COMBINED_ACCEPT}
              />
            </div>
          )}

          <p className="lv-upload-note">
            Files are sent for this verification only and are not stored after the response is returned.
          </p>

          <div className="lv-section-label">2. Run verification</div>
          {error ? (
            <div className="lv-alert">
              <AlertTriangle size={18} aria-hidden="true" />
              <div>{error}</div>
            </div>
          ) : null}
          <button className="lv-run-btn" type="submit" disabled={!canSubmit || loading}>
            {loading ? (
              <>
                <Loader2 className="lv-spinner" size={16} aria-hidden="true" /> Checking files
              </>
            ) : (
              <>
                <ChevronRight size={16} aria-hidden="true" /> Run Verification
              </>
            )}
          </button>
        </form>

        {result && overallCopy ? (
          <>
            <div className="lv-summary">
              <div>
                <p className="lv-summary-text">{overallCopy.text}</p>
                <p className="lv-summary-sub">{overallCopy.sub}</p>
                <p className="lv-summary-sub">
                  Completed in {(result.processing_time_ms / 1000).toFixed(1)} seconds.
                </p>
              </div>
              <StatusPill status={result.overall_status} />
            </div>

            <div className="lv-table-wrap">
              <table className="lv-table">
                <thead>
                  <tr>
                    <th>Field</th>
                    <th>Application Form</th>
                    <th>Label Image</th>
                    <th>Result</th>
                  </tr>
                </thead>
                <tbody>
                  {result.results.map((row) => (
                    <tr key={row.key}>
                      <td className="lv-field-name">{row.label}</td>
                      <td className="lv-val">{row.appVal || "Not found"}</td>
                      <td className="lv-val">{row.scanVal || "Not found"}</td>
                      <td>
                        <StatusPill status={row.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="lv-footnote">
              Brand and class/type fields tolerate case and punctuation differences as Needs Review.
              The government warning is checked exactly, since capitalization and exact wording are
              compliance requirements.
            </p>
          </>
        ) : null}
      </div>
    </main>
  );
}
