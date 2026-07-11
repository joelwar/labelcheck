export type Mode = "separate" | "combined";
export type FieldStatus = "match" | "mismatch";
export type SubmissionStatus = "approved" | "needs_correction" | "to_review";
export type DecidedBy = "system" | "agent_confirmed" | "agent_override" | "agent_manual";

export type ExtractedFields = {
  brand: string;
  classType: string;
  abv: string;
  netContents: string;
  warning: string;
};

export type FieldResult = {
  key: string;
  label: string;
  appVal: string;
  scanVal: string;
  status: FieldStatus;
};

export type SubmissionSummary = {
  id: string;
  brand: string;
  submitted_at: string;
  status: SubmissionStatus;
  decided_by: DecidedBy;
};

export type SubmissionDetail = {
  id: string;
  submitted_at: string;
  status: SubmissionStatus;
  decided_by: DecidedBy;
  override_reason: string | null;
  decided_at: string | null;
  extraction_ok: boolean;
  extraction_error: string | null;
  application_fields: ExtractedFields;
  label_fields: ExtractedFields;
  field_results: FieldResult[];
  application_file_url: string;
  label_file_url: string;
  processing_time_ms: number;
};
