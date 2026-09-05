export type User = {
  id: number;
  email: string;
  full_name: string;
  bio: string;
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
};

export type Metric = {
  comparative?: Pick<Metric, "status" | "value" | "currency_code" | "value_scale" | "reason" | "inputs">;
  metric_code: string;
  display_name: string;
  description: string;
  value_kind: "monetary" | "ratio" | "percentage";
  formula_expression: string;
  formula_version: number;
  status: "computed" | "not_available";
  value: string | number | null;
  currency_code: string | null;
  value_scale: "units" | "thousands" | "millions" | null;
  reason: string | null;
  inputs: Record<string, {
    current: string | number;
    comparative: string | number | null;
    currency_code: string | null;
    scale: "unknown" | "units" | "thousands" | "millions";
    filing_id: number;
  }>;
  calculated_at: string;
};

export type Summary = {
  company: { smv_rpj: string; ruc: string; legal_name: string; sector: string };
  period: { year: number; period_code: string; scope: string };
  metrics: Metric[];
};

export type Company = {
  smv_rpj: string;
  ruc: string | null;
  legal_name: string;
  company_type: string | null;
  sector: string | null;
  ciiu: string | null;
  updated_at: string;
  support_level: "full" | "basic" | "unsupported";
  analysis_status:
    | "not_analyzed"
    | "queued"
    | "processing"
    | "partial"
    | "available"
    | "review_required"
    | "failed"
    | "unsupported";
  preferred_scope: "individual" | "consolidated" | null;
  available_scopes: Array<"individual" | "consolidated">;
  latest_fiscal_year: number | null;
  completed_steps: Array<"statements" | "metrics" | "documents" | "summaries">;
  validation_tier: "automatic" | "verified";
  last_error: string | null;
  last_requested_at: string | null;
  last_completed_at: string | null;
  filings_count: number;
  failed_validations: number;
  has_analysis: boolean;
  job_id: number | null;
  job_status: AnalysisJobStatus | null;
  job_current_step: AnalysisStepCode | "complete" | null;
  job_progress: number | null;
};

export type AnalysisJobStatus =
  | "queued"
  | "running"
  | "retrying"
  | "completed"
  | "review_required"
  | "failed";

export type AnalysisStepCode = "statements" | "metrics" | "documents" | "summaries";

export type AnalysisJobStep = {
  step_code: AnalysisStepCode;
  step_order: number;
  status: "pending" | "running" | "completed" | "skipped" | "failed";
  started_at: string | null;
  completed_at: string | null;
  details: Record<string, unknown>;
  error_message: string | null;
};

export type CompanyAnalysis = {
  company: Omit<
    Company,
    "job_id" | "job_status" | "job_current_step" | "job_progress"
  >;
  job: {
    id: number;
    status: AnalysisJobStatus;
    current_step: AnalysisStepCode | "complete" | null;
    progress: number;
    steps: AnalysisJobStep[];
  } | null;
  deduplicated?: boolean;
};

export type Filing = {
  statement_type: "balance_sheet" | "income_statement" | "cash_flow";
  fiscal_year: number;
  period_code: string;
  scope: "individual" | "consolidated";
  currency_code: string | null;
  reported_scale: "unknown" | "units" | "thousands" | "millions";
  scale_source_url: string | null;
  updated_at: string;
  facts: number;
  mapped_facts: number;
  failed_validations: number;
};

export type FinancialFact = {
  account_code: string;
  original_label: string;
  normalized_concept: string | null;
  current_amount: string | number;
  comparative_amount: string | number | null;
  value_kind: "monetary" | "per_share" | "shares" | "other";
  fact_scale: "unknown" | "units" | "thousands" | "millions";
  normalization_status: "mapped" | "unmapped" | "excluded";
};

export type FinancialStatement = {
  filing: Filing & {
    smv_rpj: string;
    legal_name: string;
    statement_type: Filing["statement_type"];
    currency_raw: string;
    provider: string;
    endpoint: string;
    operation: string;
    retrieved_at: string;
    payload_sha256: string;
  };
  facts: FinancialFact[];
  validations: Array<{
    rule_code: string;
    status: "passed" | "failed" | "not_applicable";
    details: Record<string, unknown>;
    checked_at: string;
  }>;
};

export type CorporateEventCategory =
  | "dividends"
  | "management"
  | "meetings"
  | "debt"
  | "operations"
  | "litigation"
  | "production"
  | "other";

export type CorporateEvent = {
  id: number;
  smv_rpj: string;
  legal_name: string;
  source_provider: string;
  external_id: string;
  version: number;
  category: CorporateEventCategory;
  title: string;
  summary: string;
  published_at: string;
  effective_date: string | null;
  source_url: string;
  source_document_name: string;
  source_sha256: string;
  retrieved_at: string;
};

export type NoteTopic =
  | "debt"
  | "segments"
  | "capex_assets"
  | "impairment"
  | "provisions_closure"
  | "contingencies"
  | "related_parties"
  | "estimates"
  | "subsequent_events"
  | "other";

export type NoteDocument = {
  fiscal_year: number;
  period_code: string;
  scope: "individual" | "consolidated";
  version: number;
  document_name: string;
  source_url: string;
  source_sha256: string;
  page_count: number;
  notes_count: number;
  extraction_status: "extracted" | "reviewed" | "warning";
  retrieved_at: string;
  last_checked_at: string | null;
};

export type FinancialNoteSummary = {
  id: number;
  note_number: number;
  original_title: string;
  topic: NoteTopic;
  is_priority: boolean;
  start_page: number;
  end_page: number;
  extraction_status: "extracted" | "reviewed" | "warning";
  excerpt: string;
};

export type NotesResponse = {
  document: NoteDocument;
  notes: FinancialNoteSummary[];
  sync: {
    status: "queued" | "running" | "retrying" | "completed" | "failed";
    attempts: number;
    completed_at: string | null;
    error_message: string | null;
  } | null;
};

export type FinancialNoteDetail = {
  note: {
    note_number: number;
    original_title: string;
    topic: NoteTopic;
    is_priority: boolean;
    start_page: number;
    end_page: number;
    content_text: string;
    extraction_status: "extracted" | "reviewed" | "warning";
    document_name: string;
    source_url: string;
    source_sha256: string;
    version: number;
    fiscal_year: number;
    period_code: string;
    scope: "individual" | "consolidated";
    retrieved_at: string;
    legal_name: string;
    smv_rpj: string;
  };
  sections: Array<{
    page_number: number;
    section_order: number;
    content_text: string;
  }>;
  summary: CitedSummary | null;
};

export type CitedSummaryItem = {
  text: string;
  item_order: number;
};

export type CitedObservedFact = CitedSummaryItem & {
  citation: {
    source_fragment_id: number;
    page_number: number;
    document_name: string;
    source_url: string;
    document_version: number;
  };
};

export type CitedSummary = {
  generator_name: string;
  generator_version: number;
  generation_method: "extractive" | "ai";
  status: "generated" | "partial" | "insufficient_evidence";
  confidence: "high" | "medium" | "low";
  confidence_reason: string;
  information_cutoff: string;
  input_sha256: string;
  generated_at: string;
  observed_facts: CitedObservedFact[];
  interpretations: CitedSummaryItem[];
  interpretation_status: "not_generated" | "generated";
  missing_data: CitedSummaryItem[];
};

export type NarrativeComparisonNote = {
  note_number: number;
  title: string;
  topic: NoteTopic;
  summary: CitedSummary | null;
};

export type NarrativeComparisonItem = {
  match_status: "matched" | "current_only" | "previous_only";
  match_method: "normalized_title" | "title_similarity" | "none";
  similarity_score: number;
  confidence: "high" | "medium" | "low";
  confidence_reason: string;
  is_priority: boolean;
  current: NarrativeComparisonNote | null;
  previous: NarrativeComparisonNote | null;
};

export type NarrativeComparison = {
  generator_name: string;
  generator_version: number;
  status: "generated" | "partial" | "insufficient_evidence";
  confidence: "high" | "medium" | "low";
  confidence_reason: string;
  information_cutoff: string;
  input_sha256: string;
  generated_at: string;
  smv_rpj: string;
  legal_name: string;
  current_year: number;
  current_document_name: string;
  current_source_url: string;
  current_source_sha256: string;
  current_document_version: number;
  previous_year: number;
  previous_document_name: string;
  previous_source_url: string;
  previous_source_sha256: string;
  previous_document_version: number;
  coverage: {
    matched: number;
    current_only: number;
    previous_only: number;
    current_total: number;
    previous_total: number;
  };
  interpretation_status: "not_generated";
  visible_items: number;
  items: NarrativeComparisonItem[];
};

export type SourceFragment = {
  id: number;
  smv_rpj: string;
  legal_name: string;
  fiscal_year: number;
  period_code: string;
  scope: "individual" | "consolidated";
  document_name: string;
  source_url: string;
  source_sha256: string;
  document_version: number;
  note_number: number;
  original_title: string;
  topic: NoteTopic;
  is_priority: boolean;
  page_number: number;
  fragment_order: number;
  excerpt: string;
  rank: string | number;
};

export type FragmentSearchResponse = {
  query: string;
  total: number;
  limit: number;
  offset: number;
  filters: {
    company_rpj: string | null;
    topic: NoteTopic | null;
    fiscal_year: number | null;
  };
  results: SourceFragment[];
};
