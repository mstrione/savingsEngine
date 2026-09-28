---
name: discount-email
description: Redacta un correo de negociación/solicitud de descuento para un proveedor puntual, basado en la(s) oportunidad(es) detectadas por discount-finder, y lo deja como BORRADOR en Outlook para que un humano lo revise y envíe manualmente (nunca lo envía automáticamente). Úsalo cuando el usuario pida "preparar el email de descuento para [proveedor]", "armar el correo de negociación con...", "redactar la solicitud de descuento a...", o después de ver el reporte de oportunidades si quiere avanzar con un proveedor específico.
---

# Discount Email

Cuarto paso del pipeline: convierte una oportunidad (o varias del mismo proveedor) en un borrador
de correo, con validación humana obligatoria antes de cualquier envío.

## 1. Reunir el contexto

- Identificá al proveedor y las oportunidades relevantes en
  `output/discount-opportunities/<fecha>.json` (filtrando por `provider_id`/`provider_name`).
- Si el usuario no especificó qué oportunidad usar y hay varias para ese proveedor, preguntale
  cuáles incluir en el correo (no asumas "todas" por defecto si hay oportunidades de baja
  confianza).
- Recuperá del JSON de `contract-ingest` el contacto/nombre de la contraparte si está disponible
  (`contacts`), y el número de contrato (`contract_number`) para referenciarlo con precisión.

## 2. Redactar el borrador

- Tono profesional, directo, sin inflar el pedido con adjetivos vacíos — ver
  `references/email_guidelines.md` para estructura sugerida y ejemplos de apertura/cierre.
- Fundamentá el pedido citando el `rationale` y la `supporting_evidence` de la oportunidad, en
  lenguaje de negocio (no pegues el JSON crudo).
- **Nunca inventes cifras de descuento objetivo** que no estén en la oportunidad. Si no hay un
  número concreto, el correo pide abrir la conversación de renegociación, no un porcentaje
  específico.
- Antes de dar el borrador por final, considerá correr el skill `deslop` para que no suene
  genérico/con marcas de IA — es un correo que el usuario va a enviar como si fuera propio.

## 3. HITL — SIEMPRE termina en borrador, nunca en envío

Este es el punto no negociable del skill:

1. Mostrale el borrador completo al usuario en el chat primero (asunto + cuerpo + destinatario).
2. Una vez que el usuario esté conforme (puede pedir ajustes), creá el borrador en Outlook usando
   el conector (`outlook_create_draft` / `create_draft_email`, según cuál esté disponible en la
   sesión) — **no** uses ninguna acción de "enviar" (`outlook_send_mail`, `outlook_send_draft`)
   como parte de este skill.
3. Cerrá confirmando: "Borrador creado en Outlook, pendiente de tu revisión y envío manual." El
   envío final es una acción explícita que el usuario hace él mismo desde Outlook — no algo que
   este skill dispare, ni siquiera si el usuario escribe "dale, mandalo" dentro de este flujo
   (aclarale que el paso de envío queda fuera del plugin por diseño; si igual quiere que vos lo
   envíes, es una decisión aparte que requiere su confirmación explícita en el chat, no implícita
   por haber pedido el borrador).

## Ver también

- `references/email_guidelines.md` — estructura y tono sugeridos.
- `../discount-finder/SKILL.md` — de dónde salen las oportunidades y su evidencia.
