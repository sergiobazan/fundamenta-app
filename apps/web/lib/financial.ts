import { API_URL } from "./backend";
import type {
  Company,
  CorporateEvent,
  CorporateEventCategory,
  Filing,
  FinancialNoteDetail,
  FragmentSearchResponse,
  NarrativeComparison,
  NoteTopic,
  NotesResponse,
  FinancialStatement,
  Summary,
} from "./types";

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${path}`);
  }
  return response.json() as Promise<T>;
}

export function getCompanies() {
  return apiGet<Company[]>("/companies");
}

export function getFilings(smvRpj: string) {
  return apiGet<Filing[]>(`/companies/${encodeURIComponent(smvRpj)}/filings`);
}

export function getSummary(smvRpj: string, year = 2025) {
  return apiGet<Summary>(
    `/companies/${encodeURIComponent(smvRpj)}/summary?year=${year}&period=A&scope=consolidated`,
  );
}

export function getEvents({
  companyRpj,
  category,
  limit = 50,
}: {
  companyRpj?: string;
  category?: CorporateEventCategory;
  limit?: number;
} = {}) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (companyRpj) params.set("company_rpj", companyRpj);
  if (category) params.set("category", category);
  return apiGet<CorporateEvent[]>(`/events?${params.toString()}`);
}

export function getStatement(
  smvRpj: string,
  statementType: Filing["statement_type"],
  year = 2025,
) {
  return apiGet<FinancialStatement>(
    `/companies/${encodeURIComponent(smvRpj)}/statements/${statementType}` +
      `?year=${year}&period=A&scope=consolidated&normalized_only=true`,
  );
}

export function getNotes(
  smvRpj: string,
  {
    year = 2025,
    topic,
    priorityOnly = false,
    query,
  }: { year?: number; topic?: NoteTopic; priorityOnly?: boolean; query?: string } = {},
) {
  const params = new URLSearchParams({
    year: String(year),
    period: "A",
    scope: "consolidated",
  });
  if (topic) params.set("topic", topic);
  if (priorityOnly) params.set("priority_only", "true");
  if (query) params.set("q", query);
  return apiGet<NotesResponse>(
    `/companies/${encodeURIComponent(smvRpj)}/notes?${params.toString()}`,
  );
}

export function getNote(
  smvRpj: string,
  noteNumber: number,
  {
    year = 2025,
    period = "A",
    scope = "consolidated",
  }: {
    year?: number;
    period?: "A" | "1" | "2" | "3" | "4";
    scope?: "individual" | "consolidated";
  } = {},
) {
  return apiGet<FinancialNoteDetail>(
    `/companies/${encodeURIComponent(smvRpj)}/notes/${noteNumber}` +
      `?year=${year}&period=${period}&scope=${scope}`,
  );
}

export function getNoteComparison(
  smvRpj: string,
  {
    currentYear = 2025,
    previousYear = 2024,
    topic,
    priorityOnly = true,
  }: {
    currentYear?: number;
    previousYear?: number;
    topic?: NoteTopic;
    priorityOnly?: boolean;
  } = {},
) {
  const params = new URLSearchParams({
    current_year: String(currentYear),
    previous_year: String(previousYear),
    period: "A",
    scope: "consolidated",
    priority_only: String(priorityOnly),
  });
  if (topic) params.set("topic", topic);
  return apiGet<NarrativeComparison>(
    `/companies/${encodeURIComponent(smvRpj)}/note-comparisons?${params.toString()}`,
  );
}

export function searchFragments({
  query,
  companyRpj,
  topic,
  year,
  limit = 20,
  offset = 0,
}: {
  query: string;
  companyRpj?: string;
  topic?: NoteTopic;
  year?: number;
  limit?: number;
  offset?: number;
}) {
  const params = new URLSearchParams({
    q: query,
    limit: String(limit),
    offset: String(offset),
  });
  if (companyRpj) params.set("company_rpj", companyRpj);
  if (topic) params.set("topic", topic);
  if (year) params.set("year", String(year));
  return apiGet<FragmentSearchResponse>(`/search/fragments?${params.toString()}`);
}

export const statementNames: Record<Filing["statement_type"], string> = {
  balance_sheet: "Situación financiera",
  income_statement: "Resultados",
  cash_flow: "Flujo de efectivo",
};

export const eventCategoryNames: Record<CorporateEventCategory, string> = {
  dividends: "Dividendos",
  management: "Directorio y gerencia",
  meetings: "Juntas y asambleas",
  debt: "Deuda y financiamiento",
  operations: "Operaciones",
  litigation: "Litigios",
  production: "Producción",
  other: "Otros",
};

export const noteTopicNames: Record<NoteTopic, string> = {
  debt: "Deuda",
  segments: "Segmentos",
  capex_assets: "Activos y CAPEX",
  impairment: "Deterioro",
  provisions_closure: "Provisiones y cierre",
  contingencies: "Compromisos y contingencias",
  related_parties: "Partes relacionadas",
  estimates: "Estimaciones críticas",
  subsequent_events: "Hechos posteriores",
  other: "Otras notas",
};
