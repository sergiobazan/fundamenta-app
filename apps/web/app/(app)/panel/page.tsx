import { MetricCard } from "@/components/MetricCard";
import { API_URL } from "@/lib/backend";
import type { Summary } from "@/lib/types";

const sourceUrl="https://buenaventura.com/wp-content/uploads/2026/04/Integrated-annual-report-2025_Buenaventura_ENG.pdf";
const priority=['revenue_growth','net_margin','current_ratio','free_cash_flow','return_on_equity','debt_to_equity'];

async function getSummary():Promise<Summary>{const response=await fetch(`${API_URL}/companies/B20003/summary?year=2025&period=A&scope=consolidated`,{cache:'no-store'});if(!response.ok)throw new Error('No se pudo cargar el resumen financiero');return response.json()}

export const metadata={title:'Resumen financiero'};
export default async function Dashboard(){const summary=await getSummary();const metrics=priority.map(code=>summary.metrics.find(metric=>metric.metric_code===code)).filter(Boolean) as Summary['metrics'];return <>
  <header className="app-header"><div><span className="overline">CASO PILOTO · DATOS REALES</span><h1>Resumen financiero</h1></div><div className="period-pill"><span>Periodo</span><b>2025 · Anual</b></div></header>
  <section className="company-banner"><div className="company-mark">BVN</div><div><span>Compañía analizada</span><h2><a href={`/empresas/${summary.company.smv_rpj}`}>{summary.company.legal_name}</a></h2><p>Minería · Consolidado · USD en miles</p></div><div className="quality"><i></i><div><b>Datos verificados</b><span>7 de 7 controles aprobados</span></div></div></section>
  <section className="notice"><span>i</span><p><b>Lectura, no veredicto.</b> Estos indicadores ayudan a formular preguntas. No constituyen una recomendación de compra, venta o mantenimiento.</p></section>
  <section><div className="content-head"><div><h2>Indicadores clave</h2><p>Haz clic en cada fórmula para auditar los insumos.</p></div><a href={sourceUrl} target="_blank" rel="noreferrer">Documento fuente ↗</a></div><div className="metric-grid">{metrics.map((metric,index)=><MetricCard key={metric.metric_code} metric={metric} featured={index===0} sourceUrl={sourceUrl} sourceLabel="Reporte integrado 2025 de Buenaventura"/>)}</div></section>
  <section className="questions"><div><span className="overline">SIGUIENTE LECTURA</span><h2>Preguntas que los números todavía no responden</h2></div><ol><li><b>01</b><span>¿Qué parte del crecimiento provino de precio, volumen o efectos no recurrentes?</span></li><li><b>02</b><span>¿Cómo cambia el flujo libre bajo un ciclo de precios de metales menos favorable?</span></li><li><b>03</b><span>¿Qué compromisos de capex y riesgos operativos aparecen en las notas?</span></li></ol><p className="metric-source">↗ Preguntas de investigación editorial; no son hechos extraídos ni recomendaciones.</p></section>
  <footer className="data-footer"><span>Último cálculo: {new Intl.DateTimeFormat('es-PE',{dateStyle:'long',timeZone:'America/Lima'}).format(new Date(metrics[0].calculated_at))}</span><a href={sourceUrl} target="_blank" rel="noreferrer">Fuente primaria: Buenaventura, Reporte integrado 2025 ↗</a></footer>
  </>}
