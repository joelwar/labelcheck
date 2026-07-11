"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowLeft, Check, ChevronDown, ChevronRight, Loader2, X } from "lucide-react";
import { AppStyles } from "@/components/AppStyles";
import type { FieldStatus, SubmissionDetail, SubmissionStatus } from "@/lib/types";

const STATUS_COPY: Record<SubmissionStatus, { text: string; cls: string; icon: typeof Check }> = {
  approved: { text: "Approved", cls: "pill-match", icon: Check },
  needs_correction: { text: "Needs Correction", cls: "pill-fail", icon: X },
  to_review: { text: "Needs a Look", cls: "pill-neutral", icon: AlertTriangle }
};

const FIELD_COPY: Record<FieldStatus, { text: string; cls: string; icon: typeof Check }> = {
  match: { text: "Match", cls: "pill-match", icon: Check },
  mismatch: { text: "Mismatch", cls: "pill-fail", icon: X }
};

export default function SubmissionPage({ params }: { params: Promise<{ id: string }> }) {
  const [id, setId] = useState("");
  const [submission, setSubmission] = useState<SubmissionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [newStatus, setNewStatus] = useState<SubmissionStatus>("approved");
  const [reason, setReason] = useState("");

  useEffect(() => {
    params.then(({ id }) => {
      setId(id);
      loadSubmission(id);
    });
  }, [params]);

  async function loadSubmission(submissionId: string) {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`/api/submissions/${submissionId}`, { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload?.detail || "Submission could not be loaded.");
      setSubmission(payload);
      setNewStatus("needs_correction");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Submission could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  async function sendDecision(body: unknown) {
    if (!id) return;
    setSaving(true);
    setError("");
    try {
      const response = await fetch(`/api/submissions/${id}/decision`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body)
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload?.detail || "Decision could not be saved.");
      setSubmission(payload);
      setOverrideOpen(false);
      setReason("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Decision could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  function submitOverride(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    sendDecision({ action: "override", new_status: newStatus, reason });
  }

  function submitManual(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    sendDecision({ action: "manual_decision", new_status: newStatus, reason });
  }

  return (
    <main className="lv-root">
      <AppStyles />
      <div className="lv-container wide">
        <Link className="lv-link" href="/">
          <ArrowLeft size={16} aria-hidden="true" /> Back to queue
        </Link>

        <div className="lv-header" style={{ marginTop: 18 }}>
          <div className="lv-eyebrow">Submission Detail</div>
          <h1 className="lv-title">{submission ? brand(submission) : "Loading submission"}</h1>
          <p className="lv-subtitle">
            Review the system call, inspect source documents, and record the agent decision.
          </p>
        </div>

        {error ? <Alert message={error} /> : null}

        {loading ? (
          <div className="lv-panel">
            <Loader2 className="lv-spinner" size={18} aria-hidden="true" /> Loading submission
          </div>
        ) : submission ? (
          submission.extraction_ok ? (
            <AutomatedReview
              submission={submission}
              saving={saving}
              overrideOpen={overrideOpen}
              newStatus={newStatus}
              reason={reason}
              setOverrideOpen={setOverrideOpen}
              setNewStatus={setNewStatus}
              setReason={setReason}
              confirm={() => sendDecision({ action: "confirm" })}
              submitOverride={submitOverride}
            />
          ) : (
            <ManualReview
              submission={submission}
              saving={saving}
              newStatus={newStatus}
              reason={reason}
              setNewStatus={setNewStatus}
              setReason={setReason}
              submitManual={submitManual}
            />
          )
        ) : null}
      </div>
    </main>
  );
}

function AutomatedReview({
  submission,
  saving,
  overrideOpen,
  newStatus,
  reason,
  setOverrideOpen,
  setNewStatus,
  setReason,
  confirm,
  submitOverride
}: {
  submission: SubmissionDetail;
  saving: boolean;
  overrideOpen: boolean;
  newStatus: SubmissionStatus;
  reason: string;
  setOverrideOpen: (open: boolean) => void;
  setNewStatus: (status: SubmissionStatus) => void;
  setReason: (reason: string) => void;
  confirm: () => void;
  submitOverride: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const copy =
    submission.status === "approved"
      ? "System determined: Approved"
      : "System determined: Needs Correction";

  return (
    <>
      <div className="lv-summary">
        <div>
          <p className="lv-summary-text">{copy}</p>
          <p className="lv-summary-sub">
            Completed in {(submission.processing_time_ms / 1000).toFixed(1)} seconds. Decision source:{" "}
            {decisionCopy(submission.decided_by)}.
          </p>
          {submission.override_reason ? (
            <p className="lv-summary-sub">Reason: {submission.override_reason}</p>
          ) : null}
          <ApplicantMeta submission={submission} />
        </div>
        <StatusPill status={submission.status} />
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
            {submission.field_results.map((row) => (
              <tr className={row.status === "mismatch" ? "lv-mismatch-row" : ""} key={row.key}>
                <td className="lv-field-name">{row.label}</td>
                <td className="lv-val">{row.appVal || "Not found"}</td>
                <td className="lv-val">{row.scanVal || "Not found"}</td>
                <td>
                  <FieldPill status={row.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <DocumentPreview submission={submission} open={sourcesOpen} setOpen={setSourcesOpen} />

      <div className="lv-actions">
        <button className="lv-run-btn" type="button" onClick={confirm} disabled={saving}>
          {saving ? <Loader2 className="lv-spinner" size={16} /> : <Check size={16} />} Confirm
        </button>
        <button className="lv-run-btn secondary" type="button" onClick={() => setOverrideOpen(!overrideOpen)}>
          Override
        </button>
      </div>

      {overrideOpen ? (
        <form className="lv-panel" onSubmit={submitOverride}>
          <div className="lv-section-label flush">Override automated result</div>
          <StatusChoice status={newStatus} setStatus={setNewStatus} />
          <textarea
            className="lv-reason"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Required reason for override"
            required
          />
          <button className="lv-run-btn danger" type="submit" disabled={saving}>
            Save override
          </button>
        </form>
      ) : null}
    </>
  );
}

function ManualReview({
  submission,
  saving,
  newStatus,
  reason,
  setNewStatus,
  setReason,
  submitManual
}: {
  submission: SubmissionDetail;
  saving: boolean;
  newStatus: SubmissionStatus;
  reason: string;
  setNewStatus: (status: SubmissionStatus) => void;
  setReason: (reason: string) => void;
  submitManual: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const [sourcesOpen, setSourcesOpen] = useState(true);

  return (
    <>
      <div className="lv-summary">
        <div>
          <p className="lv-summary-text">Manual review required</p>
          <p className="lv-summary-sub">
            {submission.extraction_error ||
              "The system could not reliably extract the fields from the uploaded documents."}
          </p>
          <ApplicantMeta submission={submission} />
        </div>
        <StatusPill status={submission.status} />
      </div>

      <DocumentPreview submission={submission} open={sourcesOpen} setOpen={setSourcesOpen} />

      <form className="lv-panel" onSubmit={submitManual}>
        <div className="lv-section-label flush">Record manual decision</div>
        <StatusChoice status={newStatus} setStatus={setNewStatus} />
        <textarea
          className="lv-reason"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          placeholder="Optional note for the audit trail"
        />
        <button className="lv-run-btn" type="submit" disabled={saving}>
          {saving ? <Loader2 className="lv-spinner" size={16} /> : <Check size={16} />} Save decision
        </button>
      </form>
    </>
  );
}

function ApplicantMeta({ submission }: { submission: SubmissionDetail }) {
  return (
    <div className="lv-meta-row">
      <span className="lv-meta-item">
        <strong>Applicant:</strong> {submission.applicant_name}
      </span>
      <span className="lv-meta-item">
        <strong>Email:</strong> {submission.applicant_email}
      </span>
    </div>
  );
}

function DocumentPreview({
  submission,
  open,
  setOpen
}: {
  submission: SubmissionDetail;
  open: boolean;
  setOpen: (open: boolean) => void;
}) {
  return (
    <>
      <div className="lv-source-bar">
        <div className="lv-section-label flush">Source documents</div>
        <button className="lv-source-toggle" type="button" onClick={() => setOpen(!open)}>
          {open ? <ChevronDown size={16} aria-hidden="true" /> : <ChevronRight size={16} aria-hidden="true" />}
          {open ? "Hide sources" : "Show sources"}
        </button>
      </div>
      {open ? (
        <div className="lv-doc-grid">
          <PagePreview title="Application Form" images={submission.application_page_images} fallback={submission.application_file_url} />
          <PagePreview title="Label Image" images={submission.label_page_images} fallback={submission.label_file_url} />
        </div>
      ) : null}
    </>
  );
}

function PagePreview({
  title,
  images,
  fallback
}: {
  title: string;
  images: string[];
  fallback: string;
}) {
  return (
    <div className="lv-doc">
      <h3>{title}</h3>
      {images.length ? (
        <div className="lv-page-stack">
          {images.map((src, index) => (
            <img className="lv-page-img" key={src} src={src} alt={`${title} page ${index + 1}`} />
          ))}
        </div>
      ) : (
        <iframe title={title} src={fallback} />
      )}
    </div>
  );
}

function StatusChoice({
  status,
  setStatus
}: {
  status: SubmissionStatus;
  setStatus: (status: SubmissionStatus) => void;
}) {
  return (
    <div className="lv-mode-toggle">
      <button
        type="button"
        className={`lv-mode-btn ${status === "approved" ? "active" : ""}`}
        onClick={() => setStatus("approved")}
      >
        Approved
      </button>
      <button
        type="button"
        className={`lv-mode-btn ${status === "needs_correction" ? "active" : ""}`}
        onClick={() => setStatus("needs_correction")}
      >
        Needs Correction
      </button>
    </div>
  );
}

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

function FieldPill({ status }: { status: FieldStatus }) {
  const config = FIELD_COPY[status];
  const Icon = config.icon;
  return (
    <span className={`pill ${config.cls}`}>
      <Icon size={14} strokeWidth={2.5} aria-hidden="true" />
      {config.text}
    </span>
  );
}

function Alert({ message }: { message: string }) {
  return (
    <div className="lv-alert">
      <AlertTriangle size={18} aria-hidden="true" />
      <div>{message}</div>
    </div>
  );
}

function brand(submission: SubmissionDetail) {
  return submission.application_fields.brand || "Unidentified brand";
}

function decisionCopy(value: string) {
  return value.replace(/_/g, " ");
}
