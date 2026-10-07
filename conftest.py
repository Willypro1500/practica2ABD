"""Carga el juego de datos de referencia en una base de datos de pruebas.

Las pruebas nunca tocan `envivo`: trabajan sobre `envivo_test`, que se recrea
en cada ejecución a partir de los ficheros de `datos/`.
"""

import os
from pathlib import Path

import pytest
from bson import json_util
from pymongo import MongoClient, GEOSPHERE

URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
BD = "envivo_test"
COLECCIONES = ["recinto", "artista", "evento", "asistente"]



def _localiza_datos():
    """Busca el directorio datos/ junto a las pruebas o en los niveles superiores."""
    aqui = Path(__file__).resolve().parent
    for base in (aqui, *aqui.parents[:3]):
        candidato = base / "datos"
        if (candidato / "recinto.json").exists():
            return candidato
    return aqui / "datos"          # para que el mensaje de error sea util


DATOS = _localiza_datos()


@pytest.fixture(scope="session")
def db():
    cliente = MongoClient(URI, serverSelectionTimeoutMS=5000)
    cliente.admin.command("ping")          # falla pronto si no hay Mongo
    base = cliente[BD]

    for nombre in COLECCIONES:
        fichero = DATOS / f"{nombre}.json"
        if not fichero.exists():
            pytest.fail(f"No se encuentra {fichero}. ¿Falta el directorio datos/?")
        documentos = [
            json_util.loads(linea)
            for linea in fichero.read_text(encoding="utf-8").splitlines()
            if linea.strip()
        ]
        base[nombre].drop()
        base[nombre].insert_many(documentos)

    # $geoNear no funciona sin este indice, y es el unico que lo exige.
    base.recinto.create_index([("direccion_loc", GEOSPHERE)])
    base.evento.create_index([("fecha", 1)])
    base.evento.create_index([("recinto", 1)])

    yield base
    cliente.close()


@pytest.fixture
def ejecuta(db):
    """Ejecuta una consulta del contrato y devuelve la lista de resultados."""
    from consultas import CONSULTAS

    def _ejecuta(cid):
        consulta = CONSULTAS[cid]
        return list(db[consulta["coleccion"]].aggregate(consulta["pipeline"]))

    return _ejecuta
