# Preguntas de refinamiento metodológico (obligatorias antes de construir)

Extraídas de `playbooks/02_onepager_categoria.md`. El playbook es explícito:
la construcción del one-pager **no arranca** sin resolver estas decisiones primero
en el chat — no asumas un criterio "razonable" y sigas adelante, porque distintos
criterios (ej. cómo tratar un contrato multi-moneda, o cómo estimar un monto no
explícito) cambian el número final que va a la barra del gráfico, y ese número es
lo que el usuario va a citar en una negociación real.

Preguntale al usuario (podés agruparlas en un solo mensaje si el contexto ya
responde alguna):

1. **Consolidación de moneda.** Si la categoría mezcla UF/USD/CLP: ¿qué tipo de
   cambio usar (spot de qué fecha) y se declara como footnote única para toda la
   categoría? (El playbook exige un solo tipo de cambio, de un solo día, visible
   como nota al pie — nunca convertir contrato por contrato con tasas distintas
   sin decirlo.)
2. **Proveedores con múltiples contratos.** ¿Se agrupan en una sola barra del
   gráfico (manteniendo el conteo de contratos y los montos individuales
   visibles en la tabla/detalle), o se muestran como barras separadas? Cualquiera
   sea la decisión, **nunca se pierde** el número de contrato individual.
3. **Contratos atípicos.** ¿Hay contratos con estructura distinta al resto de la
   categoría (ej. leasing con financiamiento externo, contrato con cláusula de
   opción unilateral en vez de renovación automática)? ¿Cómo se homologan para
   que entren en el mismo gráfico/tabla sin forzar una comparación engañosa?
4. **Montos no explícitos.** Cuando el contrato no declara un monto total único
   (frecuente — ver ejemplos reales de Salfa Rent en Transporte de Personal):
   ¿qué método de estimación se usa (garantía de fiel cumplimiento, tarifa base
   × plazo, otro)? El método debe ser **uno solo, consistente para toda la
   categoría**, marcado con asterisco en el gráfico/tabla y explicado en el
   footnote — nunca una cifra "razonable" sin base documental.
5. **Estado vigente vs. original.** ¿Confirmado que todos los montos/fechas
   reflejan el estado post-modificación más reciente, no el contrato base
   cuando hay una adenda que lo cambió?
6. **Distinción de flota/volumen no especificado.** Si un contrato dice
   "buses eléctricos" sin cantidad fija, ¿se declara explícitamente
   "flota no especificada" en el ítem correspondiente, en vez de inventar o
   inferir un número de unidades a partir de la frecuencia de servicio?

## Regla de disclaimer (no negociable, va siempre en el footnote)

El one-pager debe distinguir explícitamente **"Precio/Renta Total Máximo
Estimado"** (techo contractual referencial, no es una obligación de pago fija)
de un monto que sí es una obligación fija. Si la categoría mezcla ambos tipos,
decilo en el footnote — no dejar que el lector asuma que todas las barras son
"gasto real ejecutado".
