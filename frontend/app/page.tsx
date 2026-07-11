"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Check, ChevronRight, Eye, FileText, Loader2, Upload, X } from "lucide-react";
import { AppStyles } from "@/components/AppStyles";
import type { Mode, SubmissionStatus, SubmissionSummary } from "@/lib/types";

const FORM_ACCEPT = ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";
const LABEL_ACCEPT = ".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg";
const COMBINED_ACCEPT = ".pdf,application/pdf";

const STATUS_COPY: Record<SubmissionStatus, { text: string; cls: string; icon: typeof Check }> = {
  approved: { text: "Approved", cls: "pill-match", icon: Check },
  needs_correction: { text: "Needs Correction", cls: "pill-fail", icon: X },
  to_review: { text: "Needs a Look", cls: "pill-neutral", icon: AlertTriangle }
};

function StatusPill({ status }: { status: SubmissionStatus }) {
  const config = STATUS_COPY[status];
  const Icon = config.icon;
  return (
    <span className={`pill ${config.cls}`}>
      <Icon size={14} strokeWidth={2.5} aria-hidden="true" />
      {config.text}
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

export default function QueuePage() {
  const [submissions, setSubmissions] = useState<SubmissionSummary[]>([]);
  const [showUpload, setShowUpload] = useState(false);
  const [mode, setMode] = useState<Mode>("separate");
  const [applicantName, setApplicantName] = useState("");
  const [applicantEmail, setApplicantEmail] = useState("");
  const [applicationFile, setApplicationFile] = useState<File | null>(null);
  const [labelFile, setLabelFile] = useState<File | null>(null);
  const [combinedFile, setCombinedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState("");

  const canSubmit = useMemo(() => {
    const hasApplicant = Boolean(applicantName.trim() && basicEmail(applicantEmail));
    return hasApplicant && (mode === "separate" ? Boolean(applicationFile && labelFile) : Boolean(combinedFile));
  }, [applicantEmail, applicantName, applicationFile, combinedFile, labelFile, mode]);

  useEffect(() => {
    loadSubmissions();
  }, []);

  async function loadSubmissions() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/submissions", { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload?.detail || "Submission queue could not be loaded.");
      setSubmissions(payload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Submission queue could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (!canSubmit) {
      setError("Please enter applicant contact information and choose the required file or files.");
      return;
    }

    const formData = new FormData();
    formData.append("mode", mode);
    formData.append("applicant_name", applicantName.trim());
    formData.append("applicant_email", applicantEmail.trim());
    if (mode === "separate") {
      formData.append("application_file", applicationFile as File);
      formData.append("label_file", labelFile as File);
    } else {
      formData.append("combined_file", combinedFile as File);
    }

    setProcessing(true);
    try {
      const response = await fetch("/api/submissions", {
        method: "POST",
        body: formData
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload?.detail || "Submission could not be processed.");
      window.location.href = `/submissions/${payload.id}`;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Submission could not be processed.");
      setProcessing(false);
    }
  }

  return (
    <main className="lv-root">
      <AppStyles />
      <div className="lv-container wide">
        <div className="lv-header">
          <div className="lv-eyebrow">Label Verification - Agent Queue</div>
          <h1 className="lv-title">TTB Submission Review</h1>
          <p className="lv-subtitle">
            Upload label submissions, review the system result, and confirm or correct the call.
          </p>
        </div>

        <div className="lv-toolbar">
          <div>
            <div className="lv-section-label flush">Queue</div>
            <p className="lv-subtitle">Items needing a look appear first.</p>
          </div>
          <button className="lv-run-btn small" type="button" onClick={() => setShowUpload(!showUpload)}>
            <Upload size={16} aria-hidden="true" /> Upload new submission
          </button>
        </div>

        {showUpload ? (
          <form className="lv-panel" onSubmit={submit}>
            <div className="lv-section-label flush">1. Provide the submission</div>
            <div className="lv-form-grid">
              <label className="lv-field">
                <span>Applicant / company name</span>
                <input
                  className="lv-input"
                  value={applicantName}
                  onChange={(event) => setApplicantName(event.target.value)}
                  required
                />
              </label>
              <label className="lv-field">
                <span>Applicant email</span>
                <input
                  className="lv-input"
                  type="email"
                  value={applicantEmail}
                  onChange={(event) => setApplicantEmail(event.target.value)}
                  required
                />
              </label>
            </div>

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
                One combined file
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
                  hint="Single PDF containing both form data and label image"
                  file={combinedFile}
                  onFile={setCombinedFile}
                  accept={COMBINED_ACCEPT}
                />
              </div>
            )}

            <p className="lv-upload-note">
              Files are processed for this prototype and kept only in the temporary in-memory review queue.
            </p>

            {error ? <Alert message={error} /> : null}
            <button className="lv-run-btn" type="submit" disabled={!canSubmit || processing}>
              {processing ? (
                <>
                  <Loader2 className="lv-spinner" size={16} aria-hidden="true" /> Processing submission
                </>
              ) : (
                <>
                  <ChevronRight size={16} aria-hidden="true" /> Run automation
                </>
              )}
            </button>
          </form>
        ) : null}

        {!showUpload && error ? <Alert message={error} /> : null}

        <div className="lv-table-wrap">
          <table className="lv-table queue">
            <thead>
              <tr>
                <th>Brand</th>
                <th>Applicant</th>
                <th>Submitted</th>
                <th>Status</th>
                <th>Review</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="lv-empty">
                    <Loader2 className="lv-spinner" size={18} aria-hidden="true" /> Loading queue
                  </td>
                </tr>
              ) : submissions.length ? (
                submissions.map((submission) => (
                  <tr key={submission.id}>
                    <td className="lv-field-name">{submission.brand}</td>
                    <td>
                      <div className="lv-field-name">{submission.applicant_name}</div>
                      <div className="lv-subtitle">{submission.applicant_email}</div>
                    </td>
                    <td>{formatDate(submission.submitted_at)}</td>
                    <td>
                      <StatusPill status={submission.status} />
                    </td>
                    <td>
                      <Link className="lv-link" href={`/submissions/${submission.id}`}>
                        <Eye size={16} aria-hidden="true" /> Open
                      </Link>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="lv-empty">
                    No submissions yet. Upload one to start the queue.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}

function basicEmail(value: string) {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value.trim());
}

function Alert({ message }: { message: string }) {
  return (
    <div className="lv-alert">
      <AlertTriangle size={18} aria-hidden="true" />
      <div>{message}</div>
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(new Date(value));
}
