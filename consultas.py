"""EnVivo · fase 2 · consultas e informes.

Cada consulta es un *pipeline* de agregación declarado como una **lista de
diccionarios de Python**, no como una cadena de texto. Así se ejecuta tal cual:

    from consultas import CONSULTAS
    c = CONSULTAS["C1"]
    resultado = list(db[c["coleccion"]].aggregate(c["pipeline"]))

Hay que rellenar los ocho pipelines. El diccionario `CONSULTAS` del final ya
está escrito y **no debe modificarse**: es el contrato de entrega.

Recordatorio del esquema, tal como quedó en la fase 1:

  recinto    nombre, direccion, direccion_loc (punto GeoJSON), ciudad, aforo,
             zonas [{nombre, asientos}], servicios []
  artista    nombre, generos [], pais, anio_inicio
  evento     titulo, artistas [] (nombres), recinto (nombre), fecha,
             precios_por_zona [{zona, precio, vendidas}], entradas_vendidas,
             estado
  asistente  nombre, email, fecha_alta, direccion, direccion_loc, preferencias []

Atención: `titulo` **no es único** (un mismo artista puede repetir recinto en
otra fecha), así que para contar eventos hay que usar `_id`.
"""

# ── C1 · Artistas por género musical ────────────────────────────────────────
# Colección: artista
# Devuelve, por cada género: genero, n (número de artistas) y artistas (lista
# de nombres, ORDENADA). Ordenado por n descendente y, a igualdad, por genero.
C1 = [
    # TODO
    {"$unwind": "$generos"},
    {
        "$group": {
            "_id": "$generos",
            "n": {"$sum": 1},
            "artistas": {"$push": "$nombre"},
        }
    },
    {
        "$project": {
            "_id": 0,
            "genero": "$_id",
            "n": 1,
            "artistas": {"$sortArray": {"input": "$artistas", "sortBy": 1}},
        }
    },
    {"$sort": {"n": -1, "genero": 1}},
]

# ── C2 · Ocupación media por recinto ────────────────────────────────────────
# Colección: evento
# Devuelve, por cada recinto: recinto, eventos y ocupacion_media, esta última
# en PORCENTAJE del aforo del recinto y redondeada a un decimal. Ordenado por
# ocupacion_media descendente y, a igualdad, por recinto.
C2 = [
    # TODO
    {
        "$lookup": {
            "from": "recinto",
            "localField": "recinto",
            "foreignField": "nombre",
            "as": "info_recinto",
        }
    },
    {
        "$set": {
            "datos_recinto": {"$arrayElemAt": ["$info_recinto", 0]},
        }
    },
    {
        "$project": {
            "recinto": 1,
            "ocupacion": {
                "$multiply": [
                    {"$divide": ["$entradas_vendidas", "$datos_recinto.aforo"]},
                    100,
                ]
            },
        }
    },
    {
        "$group": {
            "_id": "$recinto",
            "eventos": {"$sum": 1},
            "media_ocupacion": {"$avg": "$ocupacion"},
        }
    },
    {
        "$project": {
            "_id": 0,
            "recinto": "$_id",
            "eventos": 1,
            "ocupacion_media": {"$round": ["$media_ocupacion", 1]},
        }
    },
    {"$sort": {"ocupacion_media": -1, "recinto": 1}},
]

# ── C3 · Ingresos por mes ───────────────────────────────────────────────────
# Colección: evento
# El ingreso de un evento es la suma, por zona, de precio x vendidas.
# Devuelve, por cada mes: mes (formato "AAAA-MM"), ingresos redondeados a dos
# decimales y eventos (número de eventos de ese mes). Ordenado por mes.
C3 = [
    # TODO
    {
        "$project": {
            "mes": {"$substrCP": ["$fecha", 0, 7]},
            "ingresos_evento": {
                "$sum": {
                    "$map": {
                        "input": "$precios_por_zona",
                        "as": "pz",
                        "in": {"$multiply": ["$$pz.precio", "$$pz.vendidas"]},
                    }
                }
            },
        }
    },
    {
        "$group": {
            "_id": "$mes",
            "ingresos": {"$sum": "$ingresos_evento"},
            "eventos": {"$sum": 1},
        }
    },
    {
        "$project": {
            "_id": 0,
            "mes": "$_id",
            "ingresos": {"$round": ["$ingresos", 2]},
            "eventos": 1,
        }
    },
    {"$sort": {"mes": 1}},
]


# ── C4 · Los tres artistas más programados ──────────────────────────────────
# Colección: evento
# Devuelve, para cada uno de los tres primeros: artista, actuaciones y
# recintos (número de recintos DISTINTOS en los que ha actuado). Ordenado por
# actuaciones descendente y, a igualdad, por artista.
C4 = [
    # TODO
    {"$unwind": "$artistas"},
    {
        "$group": {
            "_id": "$artistas",
            "actuaciones": {"$sum": 1},
            "recintos_set": {"$addToSet": "$recinto"},
        }
    },
    {
        "$project": {
            "_id": 0,
            "artista": "$_id",
            "actuaciones": 1,
            "recintos": {"$size": "$recintos_set"},
        }
    },
    {"$sort": {"actuaciones": -1, "artista": 1}},
    {"$limit": 3},
]


# ── C5 · Recintos a menos de 5 km de la Puerta del Sol ──────────────────────
# Colección: recinto
# El punto de referencia es [-3.7038, 40.4168].
# Devuelve, por cada recinto: recinto, ciudad, distancia_km redondeada a dos
# decimales, y eventos (número de eventos de ese recinto).
C5 = [
    # TODO
    {
        "$geoNear": {
            "near": {
                "type": "Point",
                "coordinates": [-3.7038, 40.4168],
            },
            "distanceField": "distancia_metros",
            "maxDistance": 5000,
            "spherical": True,
        }
    },
    {
        "$lookup": {
            "from": "evento",
            "localField": "nombre",
            "foreignField": "recinto",
            "as": "eventos_recinto",
        }
    },
    {
        "$project": {
            "_id": 0,
            "recinto": "$nombre",
            "ciudad": 1,
            "distancia_km": {
                "$round": [{"$divide": ["$distancia_metros", 1000]}, 2]
            },
            "eventos": {"$size": "$eventos_recinto"},
        }
    },
    {"$sort": {"distancia_km": 1, "recinto": 1}},
]

# ── C6 · Cartel completo de los eventos con varios artistas ─────────────────
# Colección: evento
# Solo los eventos con MÁS DE UN artista. Devuelve: titulo, recinto y cartel,
# una lista con {nombre, pais, generos} de cada artista, ORDENADA por nombre.
# Ordenado por titulo.
C6 = [
    # TODO
]

# ── C7 · Eventos por franja de ocupación ────────────────────────────────────
# Colección: evento
# Clasifica cada evento según su ocupación sobre el aforo del recinto:
#   agotado  >= 0,99      alta  >= 0,85      media  >= 0,70      baja  el resto
# Devuelve, por franja: franja y eventos. Ordenado por eventos descendente y,
# a igualdad, por franja.
C7 = [
    # TODO
]

# ── C8 · Informe materializado por recinto ──────────────────────────────────
# Colección: evento
# Escribe en la colección `informe_recintos` un documento por recinto, con
# _id = nombre del recinto, ingresos, eventos y aforo.
# Requisito: una SEGUNDA ejecución debe ACTUALIZAR la colección, no
# reemplazarla, de modo que se conserven los campos que se le hayan añadido
# por fuera.
C8 = [
    # TODO
]


# ── Contrato de entrega · no modificar ──────────────────────────────────────
CONSULTAS = {
    "C1": {"coleccion": "artista", "pipeline": C1,
           "descripcion": "Artistas por género musical"},
    "C2": {"coleccion": "evento", "pipeline": C2,
           "descripcion": "Ocupación media por recinto"},
    "C3": {"coleccion": "evento", "pipeline": C3,
           "descripcion": "Ingresos por mes"},
    "C4": {"coleccion": "evento", "pipeline": C4,
           "descripcion": "Los tres artistas más programados"},
    "C5": {"coleccion": "recinto", "pipeline": C5,
           "descripcion": "Recintos a menos de 5 km de la Puerta del Sol"},
    "C6": {"coleccion": "evento", "pipeline": C6,
           "descripcion": "Cartel completo de los eventos con varios artistas"},
    "C7": {"coleccion": "evento", "pipeline": C7,
           "descripcion": "Eventos por franja de ocupación"},
    "C8": {"coleccion": "evento", "pipeline": C8,
           "descripcion": "Informe materializado por recinto"},
}
