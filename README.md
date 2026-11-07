# Reto 04 · Triaje local y teleconsulta

Simulación educativa de un centro ficticio. Compara medicina FIFO con una cola
por prioridad asignada mediante reglas. Usa pacientes y señales sintéticos:
no es una IA entrenada ni una herramienta con validación clínica.

## Pitch ejecutivo de tres minutos

La aplicación abre en **Pitch**. Sus cinco diapositivas siguen los puntos de la
sección 7.2 de las bases STLC: oportunidad, solución, arquitectura, viabilidad,
e impacto y escala. **Anterior**, **Siguiente** y la navegación superior cambian
de diapositiva. **Laboratorio** presenta un experimento con condiciones fijas y
controles de reproducción.

El anexo para preguntas contiene fórmulas, límites y respuestas de defensa; no
añade diapositivas a la presentación. [PITCH.md](PITCH.md) incluye el guion de
180 segundos, la correspondencia con las bases y la preparación de la demo.
Las bases permiten hasta siete minutos de demo y tres de preguntas; este guion
mantiene los tres minutos solicitados para la exposición ejecutiva.

La evidencia usa 30 turnos con parámetros originales por escenario, semillas
42–71 y diferencias pareadas con intervalos del 95 %. Los controles de la demo
no cambian ese experimento. Se presentan también pendientes de prioridad baja
y errores de clasificación: no se afirma un aumento demostrado de capacidad.

El presupuesto de viabilidad es un **supuesto ilustrativo para evaluación
retrospectiva**, editable y sin cotizaciones: un centro con equipo reutilizado
y 12 meses suma Bs 10672 de inversión inicial y Bs 300 mensuales, total Bs 14272.
No estima ingresos, retorno ni atención médica real. El anexo muestra cada base
de cálculo, exclusiones y proyección por centros; esta última es un prorrateo,
no una validación de escala técnica ni rentabilidad.

Cuando están presentes, los archivos de `pitch_entregable` se descargan desde la
presentación: PDF de cinco diapositivas y PowerPoint editable. Usan el escenario
y presupuesto base, no los cambios interactivos realizados durante una sesión.

## Ejecución

Desde esta carpeta, con Python 3.11 o superior:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run main.py --server.address 127.0.0.1 --server.port 8504
```

Si Python abre Microsoft Store, usa la ruta completa del intérprete instalado.
El entorno existente puede usarse directamente después de actualizar dependencias.

## Laboratorio con condiciones fijas

La pregunta del experimento es: **con el mismo personal y los mismos pacientes,
¿qué cambia al atender por llegada o por prioridad?** Se compara FIFO con triaje
asistido durante 24 horas de un hospital ficticio. Las condiciones se muestran
en una tabla y no son editables desde la interfaz.

| Condición | Valor fijo |
| --- | --- |
| Duración del día observado | 24 horas, de 00:00 a 24:00 |
| Cupo diario | Máximo 100 pacientes |
| Intervalo entre llegadas | Distribución discreta fija de 1 a 5 minutos; media 2,56 minutos |
| Enfermería | 1 puesto simultáneo; evaluación de 4 minutos de media |
| Medicina | 2 médicos simultáneos; consulta discreta de 15 a 35 minutos, media 25 minutos |
| Probabilidad de casos prioritarios | 30 %: 12 % alta y 18 % media; 70 % baja |
| Semilla inicial de la demostración | 42; cada nueva jornada aleatoria registra su propia semilla |
| Repeticiones para medir incertidumbre | 30 jornadas, con semillas distintas |

Las tablas de frecuencias fijan el azar del experimento. **f son pesos sintéticos,
no observaciones de un hospital real**. Cada tabla suma 50; p=f/50 es la
probabilidad de sortear ese tiempo y F es su probabilidad acumulada.

**Tiempo entre llegadas**

| t (min) | f | p | F |
| ---: | ---: | ---: | ---: |
| 1 | 10 | 0,20 | 0,20 |
| 2 | 15 | 0,30 | 0,50 |
| 3 | 15 | 0,30 | 0,80 |
| 4 | 7 | 0,14 | 0,94 |
| 5 | 3 | 0,06 | 1,00 |
| **Total** | **50** | **1,00** | |

Media ponderada: E[A]=(1×10+2×15+3×15+4×7+5×3)/50=**2,56 min**.

**Duración de consulta médica**

| t (min) | f | p | F |
| ---: | ---: | ---: | ---: |
| 15 | 5 | 0,10 | 0,10 |
| 20 | 10 | 0,20 | 0,30 |
| 25 | 20 | 0,40 | 0,70 |
| 30 | 10 | 0,20 | 0,90 |
| 35 | 5 | 0,10 | 1,00 |
| **Total** | **50** | **1,00** | |

Media ponderada: E[S]=(15×5+20×10+25×20+30×10+35×5)/50=**25 min**.

Las frecuencias definen probabilidades, no cantidades obligatorias por jornada.
Por ejemplo, cien pacientes no tienen que incluir exactamente veinte interarribos
de un minuto ni cuarenta consultas de 25 minutos.

**Las admisiones a la cohorte del experimento terminan al alcanzar 100 pacientes
o al finalizar las 24 horas observadas, lo que ocurra primero.** La atención
continúa hasta el minuto 1440 aunque se alcance antes el cupo. Con esta tabla,
los 100 candidatos llegan antes del minuto 500 como máximo y entran en el día
observado. La llegada del paciente 100 tiene una media de 256 minutos; no se
extienden las llegadas durante las 24 horas. No se fuerzan cantidades por prioridad.
El corte de observación no significa que el hospital cierre: los pacientes aún
en cola o en atención se registran como pendientes, sin simular su resolución
posterior ni darlos de alta automáticamente.

Cada jornada empieza con el centro vacío a las 00:00 y sin pacientes arrastrados
del día anterior. Es una hipótesis de experimento finito, no una representación
de continuidad hospitalaria real. Los puestos se mantienen disponibles durante
las 24 horas con relevos implícitos; no se supone que las mismas personas trabajen
todo el día ni se modelan turnos, descansos o ausencias individuales.

Los parámetros son fijos, pero las llegadas y los servicios siguen siendo
aleatorios. Ambas políticas reciben la misma cohorte y duraciones en cada jornada.
Durante el periodo de llegadas, la tasa nominal es 60/2,56 ≈ 23,44 pacientes/h,
frente a una capacidad médica conjunta de 2×60/25=4,8 consultas/h. La relación
nominal es ρ≈4,883. Los interarribos cortos y las consultas largas permiten
observar acumulación en las colas y estudiar el efecto de las prioridades.
Esta carga describe el periodo de llegadas: no es ocupación observada ni una
demanda sostenida durante 24 horas. El cupo detiene las nuevas entradas y el
resto del día permite continuar la atención.

La teleconsulta se mantiene como complemento en paralelo: probabilidad de conexión
del 85 % por intento, respuesta remota media de 45 minutos y reintentos cada
5 minutos. No retiene al médico ni añade una cola de especialistas limitada.

El recorrido es **A · Introducción → B · Condiciones fijas → C · Simulación →
D · Análisis → E · Conclusiones**. No hay panel lateral de parámetros, selector de
escenarios ni importación de datos para cambiar el experimento. **Nueva jornada
aleatoria** cambia únicamente la semilla y prepara otra realización con las mismas
condiciones. La semilla actual se muestra y se incluye en la exportación; no hay
un campo para editarla. Se conservan inicio, pausa, reinicio, paso, velocidad de
visualización, selección de la política en pantalla, repeticiones, diagnósticos
y exportación. Los puntos representan a pacientes que permanecen en el circuito:
desaparecen al terminar su consulta local y el contador de salidos sigue acumulando
las consultas completadas. Los registros de pacientes no se borran del análisis
ni de las exportaciones. La reproducción avanza cinco minutos simulados por paso;
su velocidad no modifica el modelo.

Las tablas, la dotación y el cupo son **supuestos sintéticos de un escenario
educativo de congestión**, sin calibración con datos de un hospital real. La
observación de 24 horas no convierte este lote concentrado de llegadas en una
estimación de demanda hospitalaria diaria.

El motor conserva sus opciones generales y los escenarios del pitch y de los
protocolos por Python. Esas configuraciones son experimentos distintos del
laboratorio fijo y sus resultados no deben atribuirse a este día simulado.

## Modelos matemáticos

### Azar y reproducibilidad

Se usa PCG64 explícito de NumPy, no cuadrados medios. SeedSequence separa los
flujos de llegadas, casos, servicios, remoto y conexión. Cada repetición compara
las dos políticas sobre la misma cohorte, duraciones y sorteos por paciente.
Con conexión compartida observan la misma trayectoria en tiempo absoluto, aunque
puedan solicitar envíos a horas distintas. La semilla reproduce una realización
bajo el mismo código y entorno; se registran versiones en los metadatos.

### Llegadas

En el laboratorio se generan 100 candidatos con interarribos de la tabla discreta
de 1 a 5 minutos. Se obtiene un uniforme U en [0,1) y se elige el primer tiempo
cuya acumulada F alcanza U; es la transformada inversa discreta. Las llegadas
se obtienen acumulando estos intervalos desde t=0. La última llegada ocurre como
máximo en el minuto 500, dentro de las 24 horas de observación. El cupo no puede
desactivarse en la interfaz. Estas llegadas discretas no forman un proceso de
Poisson ni siguen un perfil horario.

El motor general admite intervalos exponenciales de media 60/lambda minutos.
Fuera del laboratorio, con perfil se usa Poisson no homogéneo por tramos:
lambda_h = llegadas_por_hora × factor_h. El generador integra la intensidad e
invierte tiempos exponenciales unitarios. Hay un factor entre 0 y 5 por cada
hora; vacío significa tasa constante y cero permite horas sin llegadas.

En modo cupo se generan N candidatos y solo ingresan quienes llegan antes del
cierre. Con perfil, un candidato fuera del turno puede tener llegada infinita
y estado no_llego: no entra en denominadores. La opción del motor
generar_hasta_cierre ignora N y genera la cohorte completa del turno, con un límite
de seguridad de 100000 pacientes. Está desactivada en el laboratorio fijo.

### Casos y servicios

Con f = proporcion_prioritarios y g = fraccion_alta_prioritarios, las probabilidades
alta/media/baja son f×g, f×(1-g), 1-f. En el laboratorio f=0.30 y g=0.40.
Son probabilidades, no cuotas exactas. La referencia deriva de un índice I uniforme
en [0.80,1), [0.55,0.80) o [0,0.55), respectivamente. Las señales sin unidades son
A=clip(I+N(0,0.13²),0,1) y B=clip(0.8I+0.1+N(0,0.15²),0,1).

En el laboratorio, enfermería conserva un servicio Gamma de media m=4 y forma
k=6: escala m/k y varianza m²/k. Medicina utiliza la tabla discreta fija de
15 a 35 minutos, con media 25, muestreada por transformada inversa como las
llegadas. La consulta tiene la misma distribución para las tres prioridades.
Cada duración se sortea una vez por paciente y se comparte entre ambas políticas.

Fuera del laboratorio, el motor conserva servicios Gamma de media m y forma k,
incluida la consulta base m=16, k=8, y admite tres medias médicas por prioridad.
En esos experimentos el servicio depende de la referencia inicial; una
reevaluación posterior no vuelve a sortearlo.

### Clasificador y colas

El puntaje es w×A+(1-w)×B. En el laboratorio w=0.70: alta si alcanza 0.78, media
si alcanza 0.54 y baja en otro caso. Estos pesos y umbrales son fijos en la
interfaz. El motor permite otros valores por Python; el umbral medio debe ser
menor que el alto. No hay entrenamiento ni diagnósticos reales.

Enfermería siempre es FIFO. Medicina es FIFO o prioridad no preemptiva con
empates por antigüedad de entrada a la cola médica. En el laboratorio la prioridad
asignada no envejece. Fuera de este experimento, activar deterioro_cada_min
promueve un nivel la prioridad asistida hasta alta por cada intervalo de espera.
**Es envejecimiento educativo de la cola, no evolución clínica del paciente.**
La referencia y asignación iniciales se conservan para evaluar el clasificador.
Bitácora y reproducción muestran la prioridad vigente sin anticipar reevaluaciones.

### Conexión y teleconsulta

La solicitud se sortea por referencia inicial: 40 % alta, 27 % media, 12 % baja.
Se inicia al comenzar consulta médica y se reintenta el envío cada 5 minutos en
el laboratorio, sin duplicar un envío exitoso.

El laboratorio usa Bernoulli independiente por intento, con p=0.85. La demora
remota es uniforme entre 0.7 y 1.3 veces la media fija de 45 minutos. La respuesta
funciona en paralelo sin cambiar el fin de la consulta local.

Fuera del laboratorio, el motor también ofrece conexión compartida como una
cadena de Markov en tiempo continuo de dos estados, iniciada estacionaria para
todo el centro. Con escala tau:

- Tasa conectado→desconectado: (1-p)/tau.
- Tasa desconectado→conectado: p/tau.
- Disponibilidad estacionaria p y tiempo de autocorrelación tau.
- Permanencias medias tau/(1-p) conectado y tau/p desconectado, si 0<p<1.
- p=0 mantiene desconexión; p=1 mantiene conexión.

En ese modo cada intento consulta la conexión a su hora exacta. Hay un máximo explícito
de 100000 transiciones por realización. La duración del servicio remoto es
uniforme entre 0.7 y 1.3 veces la media configurada. Especialistas remotos = 0
significa capacidad ilimitada; un número positivo añade una cola FIFO.
El tiempo envío-respuesta incluye esa cola, registrada separadamente.

El motor puede conservar al médico ocupado hasta la respuesta remota; si no hay
respuesta, sigue ocupado hasta el horizonte. Esta opción y la capacidad remota
limitada permanecen desactivadas en el laboratorio fijo.

## Cierre, censura y clasificación

En el laboratorio, la observación termina al minuto 1440; alcanzar el cupo detiene
antes las admisiones a la cohorte, pero la atención continúa hasta ese corte.
Los eventos exactamente en el corte no se ejecutan y los pendientes se conservan
en los resultados. No se modela el cierre de un hospital ni la salida automática
de los pacientes pendientes.

En otros experimentos del motor, la observación termina en turno_min +
seguimiento_min. El seguimiento no admite pacientes nuevos. Es limitado y puede
dejar pendientes.

Las métricas sin sufijo describen el final observado; *_al_cierre se recalculan
cortando los tiempos al cierre original, aunque el seguimiento permita completar
después. La ocupación integra minutos ocupados dentro de cada horizonte.

- Esperas y percentiles P90/P95 usan consultas iniciadas y muestran su muestra.
- Tiempo observado hasta consulta o corte = min(inicio_consulta,corte)-llegada,
  sobre TODOS los llegados. Pendientes aportan tiempo transcurrido. No estima
  su espera completa. La variante médica empieza al terminar enfermería.
- Las tablas por prioridad muestran llegados, iniciados, sin iniciar y sin completar.
- Sensibilidad y subtriaje comparan asignación inicial con referencia inicial.
  Las clases sin muestra quedan vacías, no en cero. FIFO no clasifica.
- Costos educativos: filas referencia, columnas asignación, orden alta/media/baja:
  [[0,5,10],[1,0,3],[2,1,0]]. Son pesos relativos, sin calibración clínica.
- rho = lambda_media × servicio_local_medio / (60 × medicos) usa perfil y mezcla.
  Es carga nominal de servicio local; no ocupación ni retención por teleconsulta.
  Con cupo y turno finito tampoco garantiza un régimen estacionario.
- Los promedios remotos pueden tener distintas muestras observadas: no se suman
  entre sí. Se conservan pendientes y se separan cola y servicio remotos.

## Repeticiones e intervalos

En **Análisis → Repetir y medir incertidumbre**, el botón ejecuta **30 jornadas**
con las mismas condiciones fijas. La cantidad de repeticiones no es editable.
Cada repetición usa una semilla distinta y empareja las políticas. Se muestran
los resultados por jornada y política en una tabla de 60 filas, junto con el
resumen de las diferencias e intervalos. **Nueva jornada aleatoria** invalida el
lote anterior: para analizar la jornada actual hay que repetir el lote. Se calcula
D = métrica_asistida - métrica_FIFO y el IC bilateral puntual del 95 %:
media(D) ± t(0.975,n-1) × s(D)/sqrt(n).

Solo usa pares completos y finitos e informa válidos/ausentes. Con menos de dos,
el intervalo queda vacío. Mide variación entre jornadas con parámetros fijos, no
incertidumbre de calibración ni validez clínica. No corrige comparaciones múltiples.
El IC requiere suficientes réplicas o diferencias aproximadamente normales;
revisa especialmente grupos raros. Treinta repeticiones no garantizan por sí
solas una precisión suficiente para todas las métricas.

El protocolo general por Python es independiente de este botón y recorre los
escenarios originales con conexión configurada/100 %:

```powershell
.\.venv\Scripts\python.exe -m analisis.experimentos --repeticiones 30 --validar-azar --salida resultados/mejoras_modelo
```

También admite --semillas 11 42 2026 o --semilla-base 42. Escribe mediciones,
resumen pareado, metadatos y diagnósticos opcionales, reemplazando esos archivos
en la carpeta indicada. Cada medición conserva sus parámetros completos.

## Diagnósticos estadísticos

En **Análisis → Comprobar el generador y las distribuciones** se ejecutan con
semilla reproducible: KS uniforme, media/varianza, autocorrelación lag 1, rachas
y KS exponencial/Gamma con parámetros conocidos. Los tiempos se obtienen del
generador real, con la configuración base conocida y sin censura al corte.

No certifican PCG64, independencia absoluta ni realismo de un centro. El KS
exponencial/Gamma comprueba el generador base del motor, no las tablas discretas
de llegadas y consultas del laboratorio. Tampoco contrasta todas las opciones
avanzadas: sus invariantes se prueban aparte en pytest.
Los valores p son individuales, sin corrección múltiple; pueden aparecer alertas
por azar. No se eligen semillas para aprobar los contrastes.

## Ajuste con registros completos fuera del laboratorio

El módulo `analisis.calibracion` conserva el ajuste descriptivo para experimentos
por Python. La interfaz del laboratorio no importa CSV ni permite aplicar estos
ajustes a sus condiciones fijas. El módulo recibe registros con llegada_min,
duracion_triaje_min, duracion_consulta_min y prioridad_referencia (1,2,3).
La llegada es relativa al inicio de cada turno. Se deben declarar TODOS los turnos
completos, incluidos los vacíos; todos deben durar las horas de la configuración
que se ajuste. No se incluyen registros reales ni una muestra ficticia de calibración.

Se ajustan tasas por hora incluyendo horas sin llegadas, mezcla alta/media/baja,
medias y formas Gamma por momentos. La forma médica común usa variación normalizada
dentro de cada clase. Grupos con menos de dos servicios conservan su media previa
con una nota; sin prioritarios, se conserva su mezcla alta/media.

Los registros deben incluir todas las llegadas y sus servicios completamente
observados, también si hubo que seguirlos después del cierre. No selecciones
solo atendidos dentro del turno. Se rechazan faltantes, tiempos inválidos y
estimaciones fuera de rango; no se recortan silenciosamente. El ajuste devuelve
muestras y supuestos junto con sus estimaciones. Describe el CSV, no valida ni
entrena IA.

## Exportación y verificación

El ZIP incluye las condiciones fijas, la semilla de la jornada actual, versiones,
horizontes, pacientes, eventos, series y métricas; además de las tablas de
frecuencias en CSV, las repeticiones, su resumen pareado y los diagnósticos que
correspondan a esa jornada. Que un punto haya salido de la visualización no
elimina su fila del registro exportado.
**Guardar en resultados** crea un ZIP nuevo; descargar no guarda en disco.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Las pruebas cubren conservación, capacidad, cohortes emparejadas, reproducibilidad,
reevaluación, cortes comunes, extremos de conexión, capacidad remota, seguimiento,
cohortes vacías, censura, intervalos, calibración del motor, cupo diario y
controles de la interfaz fija.
