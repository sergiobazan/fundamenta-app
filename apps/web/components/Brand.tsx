export function Brand({ compact = false }: { compact?: boolean }) {
  return <a className="brand" href={process.env.NEXT_PUBLIC_LANDING_URL || "http://localhost:4321"} aria-label="Fundamenta, ir al sitio público">
    <svg viewBox="0 0 38 38" aria-hidden="true"><path d="M4 29.5 14.2 8.2h8.9L34 29.5h-7.6l-2.2-4.7H13.7l-2.1 4.7H4Z" fill="currentColor"/><path d="M16.1 19.1h5.8L19 12.8l-2.9 6.3Z" fill="#ff7657"/></svg>
    {!compact && <span>fundamenta</span>}
  </a>;
}
