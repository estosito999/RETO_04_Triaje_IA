# Reto 04 · Triaje local y teleconsulta

Simulación educativa de un centro ficticio. Compara medicina FIFO con una cola
por prioridad asignada mediante reglas. Usa pacientes y señales sintéticos:
no es una IA entrenada ni una herramienta con validación clínica.

## Ejecución

Desde esta carpeta, con Python 3.11 o superior:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run main.py --server.address 127.0.0.1 --server.port 8504
```

Si Python abre Microsoft Store, usa la ruta completa del intérprete instalado.
El entorno existente puede usarse directamente después de actualizar dependencias.

## Opciones nuevas

Los desplegables del panel lateral permiten activar:

- Demanda por hora y llegadas hasta cierre sin cupo N.
- Medias y formas Gamma de enfermería y medicina; medias médicas por prioridad.
- Cortes de conexión compartidos por todo el centro.
- Cola de especialistas remotos y retención opcional del médico hasta la respuesta.
- Envejecimiento de prioridad en la cola médica, sin interrumpir consultas.
- Seguimiento posterior al cierre de llegadas.
- Pesos, umbrales y mezcla de prioridades configurables.

Los valores predeterminados conservan la cohorte y reglas originales. El escenario
**Demanda variable y cortes compartidos** sirve como ejemplo sintético. Pulsa
**Preparar experimento** para aplicar cambios. La reproducción avanza cinco minutos
por paso y añade el instante final si no es múltiplo de cinco.

## Modelos matemáticos

### Azar y reproducibilidad

Se usa PCG64 explícito de NumPy, no cuadrados medios. SeedSequence separa los
flujos de llegadas, casos, servicios, remoto y conexión. Cada repetición compara
las dos políticas sobre la misma cohorte, duraciones y sorteos por paciente.
Con conexión compartida observan la misma trayectoria en tiempo absoluto, aunque
puedan solicitar envíos a horas distintas. La semilla reproduce una realización
bajo el mismo código y entorno; se registran versiones en los metadatos.

### Llegadas

Sin perfil, los intervalos son exponenciales de media 60/lambda minutos.
Con perfil se usa Poisson no homogéneo por tramos:
lambda_h = llegadas_por_hora × factor_h. El generador integra la intensidad e
invierte tiempos exponenciales unitarios. Hay un factor entre 0 y 5 por cada
hora; vacío significa tasa constante y cero permite horas sin llegadas.

En modo cupo se generan N candidatos y solo ingresan quienes llegan antes del
cierre. Con perfil, un candidato fuera del turno puede tener llegada infinita
y estado no_llego: no entra en denominadores. En modo **Generar llegadas hasta
el cierre**, N se ignora y se genera la cohorte completa del turno. Hay un límite
explícito de seguridad de 100000 pacientes.

### Casos y servicios

Con f = proporcion_prioritarios y g = fraccion_alta_prioritarios, las probabilidades
alta/media/baja son f×g, f×(1-g), 1-f. Por defecto f=0.30 y g=0.40.
Son probabilidades, no cuotas exactas. La referencia deriva de un índice I uniforme
en [0.80,1), [0.55,0.80) o [0,0.55), respectivamente. Las señales sin unidades son
A=clip(I+N(0,0.13²),0,1) y B=clip(0.8I+0.1+N(0,0.15²),0,1).

Los servicios son Gamma de media m y forma k: escala m/k y varianza m²/k.
Enfermería usa por defecto m=4, k=6; medicina m=16, k=8. Una forma mayor reduce
la variabilidad a igual media. Pueden indicarse tres medias médicas en orden
alta/media/baja. El servicio depende de la referencia inicial; una reevaluación
posterior no vuelve a sortearlo.

### Clasificador y colas

El puntaje es w×A+(1-w)×B. Por defecto w=0.70: alta si alcanza 0.78, media si
alcanza 0.54 y baja en otro caso. Pesos y umbrales son configurables; el umbral
medio debe ser menor que el alto. No hay entrenamiento ni diagnósticos reales.

Enfermería siempre es FIFO. Medicina es FIFO o prioridad no preemptiva con
empates por antigüedad de entrada a la cola médica. Si se activa deterioro_cada_min,
cada intervalo esperando promueve un nivel la prioridad asistida hasta alta.
**Es envejecimiento educativo de la cola, no evolución clínica del paciente.**
La referencia y asignación iniciales se conservan para evaluar el clasificador.
Bitácora y reproducción muestran la prioridad vigente sin anticipar reevaluaciones.

### Conexión y teleconsulta

La solicitud se sortea por referencia inicial: 40 % alta, 27 % media, 12 % baja.
Se inicia al comenzar consulta médica y se reintenta el envío cada intervalo
configurado, sin duplicar un envío exitoso.

El modo original es Bernoulli independiente por intento, con probabilidad p.
El modo compartido es una cadena de Markov en tiempo continuo de dos estados,
iniciada estacionaria para todo el centro. Con escala tau:

- Tasa conectado→desconectado: (1-p)/tau.
- Tasa desconectado→conectado: p/tau.
- Disponibilidad estacionaria p y tiempo de autocorrelación tau.
- Permanencias medias tau/(1-p) conectado y tau/p desconectado, si 0<p<1.
- p=0 mantiene desconexión; p=1 mantiene conexión.

Cada intento consulta la conexión a su hora exacta. Hay un máximo explícito
de 100000 transiciones por realización. La duración del servicio remoto es
uniforme entre 0.7 y 1.3 veces la media configurada. Especialistas remotos = 0
significa capacidad ilimitada; un número positivo añade una cola FIFO.
El tiempo envío-respuesta incluye esa cola, registrada separadamente.

Por defecto el remoto funciona en paralelo sin cambiar el fin de consulta local.
**Mantener al médico ocupado hasta la respuesta remota** conserva el recurso
tras el servicio local; si no hay respuesta, sigue ocupado hasta el horizonte.

## Cierre, censura y clasificación

Las llegadas terminan en turno_min; la observación termina en turno_min +
seguimiento_min. El seguimiento no admite pacientes nuevos. Es limitado y puede
dejar pendientes. Los eventos exactamente en el corte no se ejecutan.

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

En **Análisis → Repetir y medir incertidumbre**, repite la configuración actual.
Cada repetición usa una semilla distinta y empareja las políticas. Se calcula
D = métrica_asistida - métrica_FIFO y el IC bilateral puntual del 95 %:
media(D) ± t(0.975,n-1) × s(D)/sqrt(n).

Solo usa pares completos y finitos e informa válidos/ausentes. Con menos de dos,
el intervalo queda vacío. Mide variación entre turnos con parámetros fijos, no
incertidumbre de calibración ni validez clínica. No corrige comparaciones múltiples.
El IC requiere suficientes réplicas o diferencias aproximadamente normales;
revisa especialmente grupos raros. Cambiar parámetros invalida el resumen anterior.

Para todos los escenarios y conexión configurada/100 %:

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
generador real, con la configuración original conocida y sin censura al cierre.

No certifican PCG64, independencia absoluta ni realismo de un centro. No contrastan
todas las opciones avanzadas: sus invariantes se prueban aparte en pytest.
Los valores p son individuales, sin corrección múltiple; pueden aparecer alertas
por azar. No se eligen semillas para aprobar los contrastes.

## Ajuste con registros completos

En **Análisis → Ajustar parámetros con registros de turnos completos**, importa
CSV con llegada_min, duracion_triaje_min, duracion_consulta_min y
prioridad_referencia (1,2,3). Se descarga una cabecera vacía desde la interfaz.
La llegada es relativa al inicio de cada turno. Declara TODOS los turnos completos,
incluidos los vacíos; todos deben durar las horas de la configuración actual.
No se incluyen registros reales ni una muestra ficticia de calibración.

Se ajustan tasas por hora incluyendo horas sin llegadas, mezcla alta/media/baja,
medias y formas Gamma por momentos. La forma médica común usa variación normalizada
dentro de cada clase. Grupos con menos de dos servicios conservan su media previa
con una nota; sin prioritarios, se conserva su mezcla alta/media.

Los registros deben incluir todas las llegadas y sus servicios completamente
observados, también si hubo que seguirlos después del cierre. No selecciones
solo atendidos dentro del turno. Se rechazan faltantes, tiempos inválidos y
estimaciones fuera de rango; no se recortan silenciosamente. Se muestran muestras
y supuestos antes de aplicar. El ajuste describe el CSV, no valida ni entrena IA.

## Exportación y verificación

El ZIP incluye parámetros, versiones, horizontes, pacientes, eventos, series y
métricas; además de repeticiones, diagnósticos y ajuste cuando corresponden a la
configuración actual. En modo compartido incluye la trayectoria de conexión.
**Guardar en resultados** crea un ZIP nuevo; descargar no guarda en disco.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Las pruebas cubren conservación, capacidad, cohortes emparejadas, reproducibilidad,
reevaluación, cortes comunes, extremos de conexión, capacidad remota, seguimiento,
cohortes vacías, censura, intervalos, calibración y controles de la interfaz.
