# Decisiones de triaje que se pueden auditar

Guion de **3 minutos**, en **cinco diapositivas**, organizado según los cinco contenidos de la sección 7.2 de las bases. Dirigido a directivos públicos y aliados. Las indicaciones de pantalla no se leen. Las cifras describen un experimento sintético, no resultados de atención real. El material después del guion es apoyo del expositor: no añade diapositivas ni capítulos a la presentación.

## 1. Problema y oportunidad · 0:00–0:25

**Pantalla:** una cola y la pregunta «¿Quién sigue esperando al cerrar el turno?».

**Decir:**

Cuando la demanda supera la capacidad de un centro de salud, ordenar la cola cambia quién consigue una consulta y quién sigue esperando. Una conexión inestable también acumula solicitudes remotas. La oportunidad para un gestor público es explorar alternativas con evidencia antes de comprometer recursos o cambiar la operación. Nuestro prototipo hace visibles esas decisiones.

## 2. Solución tecnológica · 0:25–0:55

**Pantalla:** recorrido llegada → enfermería → cola médica → consulta; teleconsulta en paralelo.

**Decir:**

UMBRAL es un laboratorio local que compara orden de llegada y prioridad asignada por reglas transparentes. Permite ensayar demanda, personal y conectividad, y revisar quién recibe atención y quién queda pendiente. Funciona sin conexión después de instalarse. La entrega actual es una herramienta para explorar decisiones con pacientes sintéticos. El clasificador usa una regla fija; entrenar y validar una IA es una fase futura.

## 3. Arquitectura y funcionamiento · 0:55–1:35

**Pantalla:** abrir la demostración de sobrecarga, avanzar el turno y comparar las dos políticas lado a lado. Mostrar los pendientes al cierre. Cambiar después a la vista de cortes compartidos; preparar ambas vistas antes de la exposición.

**Decir:**

La arquitectura conecta un generador de casos, un motor de atención con recursos limitados y un análisis con registros exportables. Aquí cada punto es un paciente sintético que pasa por enfermería y medicina. Comparamos ambas políticas con las mismas llegadas y duraciones. Una consulta iniciada continúa. Al cerrar el turno contamos también a quienes esperan. La teleconsulta está simulada: representa solicitudes pendientes, reintentos cuando vuelve la conexión y una cola de especialistas. Los cortes pueden afectar a todo el centro.

## 4. Viabilidad financiera e implementación · 1:35–2:15

**Pantalla:** presupuesto ilustrativo de un piloto retrospectivo en un centro durante doce meses, reutilizando equipo. Mostrar inversión inicial **Bs 10.672**, operación **Bs 300/mes** y total **Bs 14.272**. Etiqueta visible: «Supuestos, no cotización». Secuencia de implementación: acordar datos y criterios → ajustar → contrastar turnos reservados → decidir continuidad.

**Decir:**

Proponemos comenzar con un piloto retrospectivo en un centro, reutilizando equipo. Bajo supuestos ilustrativos, la inversión inicial sería de 10.672 bolivianos y la operación presupuestada, 300 al mes: 14.272 para doce meses. Son cifras para discutir viabilidad, no una cotización ni salarios verificados. Primero acordaríamos datos completos y criterios de aceptación; después ajustaríamos el modelo y lo contrastaríamos con turnos reservados. El alcance presupuestado es software y revisión del piloto; no estimamos ahorros ni costos de atención real.

## 5. Impacto esperado y escalabilidad · 2:15–3:00

**Pantalla:** comparación de pendientes por prioridad con nota «30 turnos sintéticos; mismas entradas por par». Mostrar beneficio y contrapartida. Cierre: «Centro aliado + registros completos + revisión profesional». La escalabilidad se presenta como plan de evaluación por centro, sin prometer despliegue automático.

**Decir:**

En treinta turnos sintéticos de sobrecarga, la política asistida dejó 16,6 casos altos menos sin iniciar consulta al cierre, pero 23,7 casos bajos más pendientes. No demostramos mayor capacidad: el intervalo de consultas completadas incluye cero. El impacto que esperamos evaluar es una mejor base para decidir, haciendo visibles esas contrapartidas. Para escalar, habría que ajustar y contrastar cada centro; compartir desarrollo no garantiza viabilidad técnica. Buscamos un centro aliado, registros completos y revisión de salud e ingeniería para decidir si continuar, sin dirigir todavía la atención real.

---

## Material del expositor · no son diapositivas adicionales

### Matriz de cumplimiento de la sección 7.2

| Contenido requerido | Diapositiva del pitch | Qué se muestra |
|---|---|---|
| Problema y oportunidad | 1 · 0:00–0:25 | Decisión de cola y capacidad, pendientes al cierre y oportunidad de evaluar alternativas antes de operar. |
| Solución tecnológica | 2 · 0:25–0:55 | Laboratorio local, dos políticas, capacidades actuales y clasificador por reglas. |
| Arquitectura y funcionamiento | 3 · 0:55–1:35 | Generador → motor de recursos y colas → análisis/exportación; demo y teleconsulta simulada. |
| Viabilidad financiera e implementación | 4 · 1:35–2:15 | Presupuesto ilustrativo explícito, alcance retrospectivo, fases y criterio de continuidad. |
| Impacto esperado y escalabilidad | 5 · 2:15–3:00 | Evidencia sintética con contrapartida, impacto pendiente de evaluar, adaptación por centro y solicitud de alianza. |

Total: **180 segundos y cinco diapositivas**. Método detallado, tablas de respaldo y preguntas se conservan fuera de la navegación. El máximo de exposición de las bases permite más tiempo, pero este guion mantiene los tres minutos solicitados.

### Preparación de la demo

1. Abrir la presentación y comprobar las cinco diapositivas antes de comenzar. Preparar la demo de **Sobrecarga de llegadas** y su comparación al cierre para la diapositiva 3; las 30 repeticiones se presentan en la 5.
2. Mantener lista la evidencia de 30 repeticiones. Las cifras del guion corresponden a **Conexión del escenario**, con semillas 42–71; no sustituyen una corrida individual. Los controles de la demo son independientes: la evidencia usa los parámetros originales del escenario que se seleccione en su propio capítulo.
3. Preparar la vista de **Demanda variable y cortes compartidos**. Explicar que es otra configuración; no atribuirle las cifras del escenario de sobrecarga.
4. Mostrar los pendientes por prioridad antes que la espera media de quienes sí entraron a consulta. Evitar presentar una media condicionada por atención como si describiera a todos los llegados.
5. Si no alcanza el tiempo, conservar la comparación de pendientes y omitir el cambio de conectividad. La bitácora y los supuestos quedan para preguntas.

### Evidencia de respaldo

Fuente local: `resultados/mejoras_modelo/resumen_pareado.csv` y `experimentos.csv`. Contexto: **Sobrecarga de llegadas / Conexión del escenario / 30 pares completos / semillas 42–71**. Diferencia = triaje asistido − FIFO.

| Métrica por turno sintético | Diferencia media | IC puntual del 95 % |
|---|---:|---:|
| Alta: sin iniciar consulta al cierre | −16,57 casos | [−17,94; −15,19] |
| Baja: sin iniciar consulta al cierre | +23,73 casos | [+22,32; +25,14] |
| Consultas completadas | +0,70 consultas | [−0,21; +1,61] |

Son diferencias de conteos medios por turno, no porcentajes ni efectos en salud. El escenario no tiene seguimiento posterior: el final observado coincide con el cierre. Los intervalos son Student bilaterales por métrica, sin corrección por comparaciones múltiples. No incluyen incertidumbre de calibración ni de selección del modelo. Las versiones y parámetros completos están en `metadatos_experimentos.json` y en las filas de mediciones. Estas cifras deben recalcularse si cambia el escenario o su implementación.

### Presupuesto de respaldo · supuestos ilustrativos en bolivianos

Alcance exclusivo: **piloto retrospectivo de software y revisión**, un centro durante doce meses, con equipo existente. No es una cotización, una propuesta económica aceptada, un estudio salarial ni una estimación de atención sanitaria real. Las horas y tarifas se declaran para que el aliado pueda cuestionarlas y sustituirlas. No se calcula retorno de inversión ni ahorro.

| Concepto | Supuesto del modelo | Importe inicial |
|---|---|---:|
| Desarrollo compartido | 80 h × Bs 80/h | Bs 6.400 |
| Preparación de datos por centro | 12 h × Bs 80/h | Bs 960 |
| Revisión por centro | 16 h × Bs 100/h | Bs 1.600 |
| Capacitación por centro | 4 h × Bs 80/h | Bs 320 |
| Equipo reutilizado | Disponible; adquisición presupuestada = 0 | Bs 0 |
| Base inicial | Desarrollo + Bs 2.880 por centro | Bs 9.280 |
| Contingencia inicial | 15 % de la base | Bs 1.392 |
| **Inversión inicial ilustrativa** | Base + contingencia | **Bs 10.672** |
| Operación presupuestada | Bs 200 fijos + Bs 100 por centro/mes | **Bs 300/mes** |
| Operación de doce meses | 12 × Bs 300 | Bs 3.600 |
| **Total ilustrativo de doce meses** | Inversión + operación | **Bs 14.272** |

Si fuera necesario adquirir equipo, el supuesto alternativo es **Bs 3.500 por centro**, también sujeto al 15 % de contingencia inicial. Para un centro, sumaría Bs 4.025 y llevaría el total de doce meses a **Bs 18.297**. No incluye integrar una plataforma real de teleconsulta, cambiar la dotación asistencial ni demostrar seguridad clínica.

Para N centros, el modelo presupuestario es:

\[
I(N)=1.15\,[6400+2880N+E(N)],\qquad O(N)=200+100N
\]

\[
T_{12}(N)=I(N)+12O(N)
\]

E(N) es cero al reutilizar equipos o 3500N si se adquiere uno por centro. Dividir T por N solo reparte estos supuestos compartidos: **no garantiza economías técnicas, desempeño, adopción ni que un centro replique a otro**. Cada incorporación necesita evaluar datos, infraestructura y recursos disponibles.

El plan inicial sería acordar acceso y calidad de registros, definir criterios de aceptación, ajustar con una muestra y contrastar con turnos reservados. Una evaluación prospectiva en paralelo sería posterior y requeriría un alcance y presupuesto propios. No se propone que el piloto retrospectivo dirija la atención.

### Método de respaldo

SimPy calcula llegadas, ocupación y liberación de recursos como eventos discretos. PCG64 genera las entradas; las semillas y versiones permiten reproducir cada realización. Las políticas se emparejan usando la misma cohorte y duraciones dentro de cada turno. Los intervalos de las diferencias entre turnos son puntuales del 95 %, con parámetros fijos y pares completos. Hay pruebas de conservación, capacidad, extremos de conexión y seguimiento; los diagnósticos estadísticos son parciales y no validan el centro real. La referencia y las señales actuales son sintéticas; acertarlas no es precisión clínica.

### Preguntas difíciles · fuera de los tres minutos

**¿Dónde está la IA?**  
El prototipo actual clasifica con un puntaje y umbrales configurables. Es una línea base transparente para el laboratorio. Entrenar y validar un modelo con una referencia independiente sería una fase posterior; hoy no afirmamos haberla realizado.

**¿Todo es pseudoaleatorio?**  
Las entradas sintéticas se sortean con PCG64. Las esperas y ocupaciones se calculan por eventos, capacidad y política. Repetimos semillas independientes y emparejamos las dos políticas dentro de cada turno. Aprobar diagnósticos del azar no acredita realismo clínico.

**¿Usan cuadrados medios?**  
No. Se usa PCG64 explícito de NumPy y se registra su entorno. Las semillas permiten repetir realizaciones; los flujos separados evitan que los reintentos consuman el azar de las llegadas.

**¿Qué representan las señales A y B?**  
Son dos señales artificiales, sin unidades clínicas, derivadas de un índice sintético con ruido. Permiten estudiar errores de clasificación bajo supuestos controlados. No equivalen a saturación, pulso ni diagnóstico. La concordancia mide recuperación de etiquetas sintéticas.

**¿Qué sucede si el sistema asigna poca prioridad a un caso grave?**  
El laboratorio cuenta subtriaje y sensibilidad por clase, conserva los casos afectados y permite estudiar su espera. No mide daño clínico ni permite fijar un riesgo aceptable. Antes de cualquier uso asistencial se necesitarían referencia clínica independiente, validación y supervisión profesional.

**¿La función de costos mide dinero o daño?**  
No. Sus pesos son educativos y relativos; penalizan errores de forma diferente para hacer explícito el criterio. No son costos monetarios ni estimaciones de daño. Tendrían que justificarse con las personas responsables de un piloto.

**¿Por qué no anuncian una reducción general de la espera?**  
Porque la política cambia quién entra a consulta. Una media menor entre atendidos puede esconder más pendientes. Por eso la demostración usa pendientes por prioridad y también conserva el tiempo observado de todos los llegados, con su censura al cierre.

**¿El intervalo demuestra que la solución funciona en un hospital?**  
No. Describe la media de diferencias entre turnos sintéticos con los mismos parámetros. No cubre errores de los supuestos, incertidumbre del ajuste ni cambios de población. Los 30 pares son evidencia interna reproducible, no validación externa.

**¿La conexión representa una red real?**  
El modo compartido usa dos estados con transiciones Markovianas: conectado y desconectado. Modela persistencia y cortes comunes, pero no ancho de banda, pérdida de paquetes, energía, geografía ni todos los fallos de una red. Su escala temporal y disponibilidad requieren calibración.

**¿El programa hace teleconsultas reales?**  
No. Simula solicitudes, almacenamiento pendiente, reintentos, capacidad remota y respuestas. El funcionamiento local del laboratorio no demuestra que exista una integración operativa con un servicio sanitario.

**¿Cuánto cuesta y quién lo está usando?**  
El modelo ilustrativo de un centro y doce meses, reutilizando equipo, suma Bs 14.272: Bs 10.672 iniciales y Bs 300 mensuales. No es una cotización ni un presupuesto de despliegue sanitario; las horas y tarifas no son salarios verificados. No tenemos contratos ni adopción verificada que presentar. Un aliado tendría que revisar los supuestos y acordar el alcance del piloto retrospectivo.

**¿Se deteriora de verdad el estado del paciente simulado?**  
La opción actual envejece la prioridad de la cola asistida para estudiar esperas: sube niveles por intervalos, sin interrumpir consultas. No modifica una condición clínica validada ni debe presentarse como un modelo de evolución de enfermedad.

**¿Qué sería un resultado aceptable del primer piloto?**  
Antes de analizar resultados, acordaríamos qué precisión necesitan las estimaciones de llegadas, servicios, ocupación y pendientes. Contrastaríamos turnos reservados para evaluación y revisaríamos resultados por prioridad. Los umbrales y la continuidad se decidirían con el centro colaborador; hoy son parte del plan.
