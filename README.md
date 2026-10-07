# Práctica 2 · Consultas e informes · EnVivo (fase 2)

Punto de partida de la práctica 2 de **Ampliación de Bases de Datos** (u-tad).
Aquí están el esqueleto de las ocho consultas, el juego de datos de referencia
sobre el que se ejecutan y las pruebas con las que puedes comprobarlas mientras
las escribes.

El enunciado completo, con lo que pide cada consulta y la rúbrica, está en el
campus virtual. Esto es solo el código.

## Cómo empezar

1. **Haz un fork** de este repositorio con el botón *Fork* de GitHub. Uno por
   grupo: trabajad los dos sobre el mismo fork.
2. Clónalo en tu máquina:

   ```bash
   git clone https://github.com/<tu-usuario>/abd-p2-consultas.git
   cd abd-p2-consultas
   ```

3. Levanta MongoDB, desde la carpeta donde tengas el `compose.yaml` de la
   asignatura:

   ```bash
   docker compose up -d mongo
   ```

4. Instala las dependencias y comprueba que todo arranca:

   ```bash
   uv sync
   uv run python -m pytest consultas_test.py -q
   ```

Al principio fallan casi todas: eso es lo normal, los ocho *pipelines* están
vacíos y es lo que hay que implementar.

## Qué hay aquí

| Fichero | Qué es |
|---|---|
| `consultas.py` | Los ocho *pipelines*, con los `TODO`. **Es lo que hay que completar** |
| `datos/` | El juego de datos de referencia: un `.json` por colección, en NDJSON |
| `pyproject.toml` | Las dependencias. No hace falta tocarlo |
| `consultas_test.py` | Las pruebas |
| `conftest.py` | Carga los datos para las pruebas. **No lo edites** |

## Los datos de trabajo

Las pruebas cargan los datos por su cuenta, pero para probar las consultas a
mano —en `mongosh`, en Compass o en el notebook— hay que cargarlos en la base
`envivo`. Desde la carpeta del repositorio:

```bash
for c in recinto artista evento asistente; do
    docker cp datos/$c.json abd-mongo-1:/tmp/$c.json
    docker exec abd-mongo-1 mongoimport --db envivo --collection $c \
        --drop --file /tmp/$c.json
done
```

Y el índice que necesita `$geoNear` (C5):

```javascript
db.recinto.createIndex({ "direccion_loc": "2dsphere" })
```

Los ficheros no se modifican: la corrección usa exactamente estos datos.

## Qué se ve al ejecutar las pruebas

Cuando todo está bien, un punto por prueba:

```
..........................                               [100%]
26 passed in 0.6s
```

Mientras no lo esté, cada `F` es una prueba que falla, y abajo sale el nombre
de cada una con el motivo. Los mensajes están escritos para orientar:

```
FAILED consultas_test.py::test_c3_ingresos_por_mes - AssertionError: cada evento cuenta una vez: cuidado con el $unwind de las zonas
1 failed, 25 passed in 0.6s
```

Para trabajar sobre una sola consulta:

```bash
uv run python -m pytest consultas_test.py -k c3 -v
uv run python -m pytest consultas_test.py -x --tb=short   # para en el primer fallo
```

## Qué exige cada prueba

| Prueba | Qué tiene que funcionar |
|---|---|
| `test_estan_las_ocho_consultas` | `CONSULTAS` tiene exactamente C1 … C8 |
| `test_forma_del_contrato[C1…C8]` | Cada *pipeline* es una lista no vacía de etapas, una por diccionario |
| `test_la_consulta_se_ejecuta[C1…C8]` | MongoDB ejecuta el *pipeline* sin error |
| `test_c1_generos` | Nueve géneros, el primero con cuatro artistas y la lista ordenada |
| `test_c2_ocupacion` | Seis recintos, 32 eventos en total, ocupación en porcentaje y ordenada |
| `test_c3_ingresos_por_mes` | Meses en orden y 32 eventos en total: cuenta eventos, no zonas |
| `test_c4_top_tres` | Los tres artistas con cuatro actuaciones |
| `test_c5_geoproximidad` | Los dos recintos a menos de 5 km de Sol, en orden de distancia |
| `test_c6_carteles` | Seis eventos con varios artistas, con `pais` y `generos` en el cartel |
| `test_c7_franjas` | Los 32 eventos clasificados, solo con las cuatro franjas |
| `test_c8_crea_el_informe` | `informe_recintos` con un documento por recinto |
| `test_c8_actualiza_en_lugar_de_sobrescribir` | Una segunda ejecución conserva los campos añadidos por fuera |

## Lo que estas pruebas no dicen

Pasarlas es **necesario, pero no suficiente**. Comprueban la forma y algunos
valores concretos de cada resultado, no el resultado entero. La corrección
compara el resultado **completo** de cada consulta —campos, valores, redondeos
y orden— con el de la solución de referencia.

Lo que sí es buena noticia: se comparan **resultados, no formas**. Cualquier
formulación que produzca la salida pedida puntúa igual.

## Tres cosas que no hay que cambiar

- El fichero se sigue llamando `consultas.py`: las pruebas hacen
  `from consultas import CONSULTAS`.
- El diccionario `CONSULTAS` del final se queda como está: es el contrato con
  el que se ejecuta la corrección. Lo que se rellena son las listas `C1` … `C8`.
- Los *pipelines* son **listas de diccionarios de Python**, no cadenas de texto.

Las pruebas trabajan sobre la base `envivo_test`, que recrean en cada
ejecución, así que **no tocan tus datos** de `envivo`.

## La entrega

El fork es para trabajar. La entrega es la que dice el enunciado: un **ZIP**
con la carpeta del proyecto —`consultas.py`, el notebook con las ocho
consultas ejecutadas a través del ODM de la práctica 1, y el código de esa
práctica necesario para volver a ejecutarlo— nombrado
`P2_G<grupo>_Nombre_Apellido-Nombre_Apellido.zip`.

## Si algo no arranca

El manual **Entorno de trabajo** de la asignatura tiene la tabla de errores
frecuentes. Los más habituales aquí:

- `ServerSelectionTimeoutError` → MongoDB no está levantado: `docker compose up -d mongo`.
- `ModuleNotFoundError: No module named 'consultas'` → ejecutaste `pytest` a
  secas. Tiene que ser `python -m pytest`, desde la carpeta del proyecto.
- `$geoNear requires a 2d or 2dsphere index` → en las pruebas el índice ya se
  crea; en `envivo` hay que crearlo a mano (ver arriba).
- `No such container: abd-mongo-1` → el contenedor se llama distinto en tu
  máquina; mira su nombre con `docker ps`.
