"use client";

import { useEffect, useState } from "react";

const cards = [
  {
    topic: "LECTURA FINANCIERA",
    title: "Una cifra cuenta más cuando tiene contexto.",
    text: "Antes de comparar dos empresas, revisa que sus cifras correspondan al mismo periodo, moneda y alcance: individual o consolidado.",
    takeaway: "Empieza por el contexto; después, compara los indicadores.",
  },
  {
    topic: "CALIDAD DEL RESULTADO",
    title: "Utilidad y efectivo responden preguntas distintas.",
    text: "Una venta puede reconocerse antes de cobrarse. Leer el resultado junto al flujo de efectivo ayuda a entender cómo se convierte la actividad del negocio en caja.",
    takeaway: "Consulta resultados y flujo de efectivo en conjunto.",
  },
  {
    topic: "TRAZABILIDAD",
    title: "Detrás de cada indicador hay una fórmula.",
    text: "En las tarjetas de métricas puedes abrir «Ver cálculo e insumos» para revisar qué cuentas se utilizaron y cómo se obtuvo el resultado.",
    takeaway: "Abre los insumos cuando una cifra te llame la atención.",
  },
  {
    topic: "NOTAS FINANCIERAS",
    title: "Las notas explican lo que el balance resume.",
    text: "Los vencimientos de deuda, las contingencias y las políticas contables aportan contexto que no siempre se ve en los estados principales.",
    takeaway: "Busca la explicación detrás de los cambios importantes.",
  },
  {
    topic: "UNIDADES Y ESCALA",
    title: "La moneda es solo una parte de la cifra.",
    text: "Un importe puede estar expresado en unidades, miles o millones. Si aparece «Escala no verificada», consulta el documento oficial antes de interpretar su magnitud.",
    takeaway: "La advertencia señala información pendiente de confirmar.",
  },
];

export function AnalysisReadingCards() {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const respectPreference = () => { if (preference.matches) setPaused(true); };
    const visibility = () => setHidden(document.hidden);
    respectPreference();
    visibility();
    preference.addEventListener("change", respectPreference);
    document.addEventListener("visibilitychange", visibility);
    return () => {
      preference.removeEventListener("change", respectPreference);
      document.removeEventListener("visibilitychange", visibility);
    };
  }, []);

  useEffect(() => {
    if (paused || hovered || hidden) return;
    const timer = window.setInterval(() => setIndex((value) => (value + 1) % cards.length), 12000);
    return () => window.clearInterval(timer);
  }, [paused, hovered, hidden]);

  function move(direction: number) {
    setPaused(true);
    setIndex((value) => (value + direction + cards.length) % cards.length);
  }

  const card = cards[index];
  return <section className="analysis-reading" aria-label="Mientras preparamos tu análisis"
    aria-roledescription="carrusel"
    onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
    onFocusCapture={() => setPaused(true)}>
    <div className="analysis-reading-intro">
      <span className="overline">MIENTRAS PREPARAMOS TU ANÁLISIS</span>
      <h2>Una pausa para mirar más allá de las cifras.</h2>
      <p>Claves breves para explorar los resultados cuando estén listos.</p>
      <span className="analysis-reading-category">Guía de lectura · Fundamenta</span>
    </div>
    <div className="analysis-reading-content">
      <div className="analysis-reading-slide" aria-live={paused ? "polite" : "off"} aria-atomic="true">
        <span className="analysis-reading-topic">{card.topic}</span>
        <h3>{card.title}</h3>
        <p>{card.text}</p>
        <div className="analysis-reading-takeaway"><span aria-hidden="true">↗</span>{card.takeaway}</div>
      </div>
      <div className="analysis-reading-controls">
        <span className="analysis-reading-count">{String(index + 1).padStart(2, "0")} <span>/ {String(cards.length).padStart(2, "0")}</span></span>
        <div className="analysis-reading-dots" aria-hidden="true">{cards.map((item, position) => <span key={item.topic} className={position === index ? "active" : ""} />)}</div>
        <button type="button" className="analysis-reading-pause" onClick={() => setPaused((value) => !value)}
          aria-label={paused ? "Activar rotación automática de consejos" : "Pausar rotación de consejos"}>
          {paused ? "Reanudar" : "Pausar"}
        </button>
        <button type="button" onClick={() => move(-1)} aria-label="Consejo anterior">←</button>
        <button type="button" onClick={() => move(1)} aria-label="Consejo siguiente">→</button>
      </div>
    </div>
  </section>;
}
