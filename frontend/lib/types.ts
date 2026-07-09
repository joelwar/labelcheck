export type Mode = "separate" | "combined";
export type Status = "match" | "review" | "fail";

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
  status: Status;
};

export type VerifyResponse = {
  application_fields: ExtractedFields;
  label_fields: ExtractedFields;
  results: FieldResult[];
  overall_status: Status;
  processing_time_ms: number;
};
