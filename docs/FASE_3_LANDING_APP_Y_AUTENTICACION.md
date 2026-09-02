# Fase 3: landing, aplicación y autenticación

## Corte alcanzado

Se implementó el primer recorrido visible del producto bajo la marca de trabajo
**Fundamenta**. La landing pública vive en Astro y la aplicación autenticada en
Next.js. FastAPI sigue siendo el único backend de negocio y PostgreSQL conserva
usuarios, sesiones, información financiera y métricas.

## Landing Astro

Incluye:

- CTA visible sin desplazamiento y CTA fijo en móvil.
- Navegación interna, breadcrumbs y títulos/descripciones únicos.
- Caso real de Buenaventura 2025 con enlaces a la fuente primaria.
- Cinco preguntas frecuentes y schema `FAQPage`.
- 404 personalizada, página de gracias, contacto y política de privacidad.
- `robots.txt`, sitemap y tarjeta social PNG de 1200 × 630.
- Google Analytics opcional y condicionado a consentimiento.
- Animaciones adaptadas de Animista y divisor SVG de Shape Divider.
- Vista de ubicación con mapa, indicaciones y schema local condicionados a una
  dirección comercial verificable.
- Sección de reseñas que sólo admite testimonios con autorización registrada.

## Aplicación Next.js

Incluye:

- Registro e inicio de sesión.
- Cookie de sesión `HttpOnly`, `SameSite=Lax`, `Secure` en producción y expiración.
- Rutas de panel y perfil protegidas en servidor.
- Cierre de sesión con revocación en PostgreSQL.
- Edición de nombre y biografía.
- Avatar predeterminado y carga JPG/PNG/WebP de máximo 2 MB.
- Revalidación y recodificación de avatares a WebP en el backend.
- Panel real de Buenaventura con seis indicadores prioritarios, fórmula, insumos y
  referencia en cada tarjeta.

## Seguridad implementada

- Contraseñas con Argon2 mediante `pwdlib`.
- El token de sesión se genera con entropía criptográfica y sólo se almacena como
  SHA-256 en la base.
- Errores de login no revelan si el correo existe.
- Las sesiones pueden revocarse y caducan después de 30 días.
- El navegador nunca recibe el token en JSON: el Route Handler de Next lo transforma
  en una cookie no accesible a JavaScript.

## Verificación ejecutada

- 16 pruebas Python aprobadas.
- Ruff sin hallazgos.
- Astro check y build: nueve páginas, 404, robots y sitemap generados.
- Next.js build y TypeScript aprobados.
- Prueba HTTP real: login `200`, cookie HttpOnly/Lax, panel `200`, perfil `200`,
  logout `204` y ruta protegida redirigida con `307`.
- Carga real de PNG, recodificación WebP y restauración del avatar predeterminado.
- El endpoint de resumen devolvió los 15 indicadores almacenados.

## Datos deliberadamente pendientes

No se inventaron datos para completar requisitos de marketing:

- Reseñas reales: faltan usuarios piloto y autorización de publicación.
- Dirección, mapa e indicaciones: falta una ubicación comercial verificable.
- Schema local: se activa junto con esa dirección; por ahora se usa schema de
  organización, aplicación y contenido.
- Contacto: falta configurar un correo controlado por el proyecto.
- Google Analytics: falta un Measurement ID real.

Estas ausencias se muestran con estados honestos en la interfaz y se controlan por
variables de entorno o configuración de contenido.
