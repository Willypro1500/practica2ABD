"""Pruebas visibles de la fase 2 de EnVivo.

Comprueban el contrato de entrega y algunos resultados concretos. **No cubren
todos los requisitos del enunciado:** que pasen es condición necesaria para
aprobar, no suficiente.

    uv run python -m pytest consultas_test.py -q
"""

import pytest

from consultas import CONSULTAS

IDS = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"]


# ── El contrato de entrega ──────────────────────────────────────────────────

def test_estan_las_ocho_consultas():
    assert sorted(CONSULTAS) == IDS


@pytest.mark.parametrize("cid", IDS)
def test_forma_del_contrato(cid):
    consulta = CONSULTAS[cid]
    assert "coleccion" in consulta, f"{cid}: falta la clave 'coleccion'"
    assert "pipeline" in consulta, f"{cid}: falta la clave 'pipeline'"
    assert isinstance(consulta["pipeline"], list), f"{cid}: el pipeline debe ser una lista"
    assert consulta["pipeline"], f"{cid}: el pipeline está vacío"
    for etapa in consulta["pipeline"]:
        assert isinstance(etapa, dict), f"{cid}: cada etapa debe ser un diccionario"
        assert len(etapa) == 1, f"{cid}: cada etapa tiene un único operador"
        assert next(iter(etapa)).startswith("$"), f"{cid}: el operador empieza por $"


@pytest.mark.parametrize("cid", IDS)
def test_la_consulta_se_ejecuta(cid, ejecuta):
    ejecuta(cid)          # basta con que no lance excepción


# ── Resultados concretos ────────────────────────────────────────────────────

def test_c1_generos(ejecuta):
    filas = ejecuta("C1")
    assert len(filas) == 9, "hay nueve géneros distintos"
    primera = filas[0]
    assert primera["genero"] in ("indie", "pop"), "el género más frecuente"
    assert primera["n"] == 4
    assert primera["artistas"] == sorted(primera["artistas"]), \
        "los artistas deben venir ordenados: $addToSet no garantiza el orden"


def test_c2_ocupacion(ejecuta):
    filas = ejecuta("C2")
    assert len(filas) == 6, "hay seis recintos con eventos"
    assert sum(f["eventos"] for f in filas) == 32, "en total hay 32 eventos"
    ocupaciones = [f["ocupacion_media"] for f in filas]
    assert ocupaciones == sorted(ocupaciones, reverse=True), \
        "ordenado por ocupación descendente"
    assert all(0 < o <= 100 for o in ocupaciones), \
        "la ocupación es un porcentaje: quizá falta multiplicar por 100"


def test_c3_ingresos_por_mes(ejecuta):
    filas = ejecuta("C3")
    meses = [f["mes"] for f in filas]
    assert meses == sorted(meses), "ordenado por mes ascendente"
    assert meses[0] == "2025-02"
    assert sum(f["eventos"] for f in filas) == 32, \
        "cada evento cuenta una vez: cuidado con el $unwind de las zonas"


def test_c4_top_tres(ejecuta):
    filas = ejecuta("C4")
    assert len(filas) == 3
    assert all(f["actuaciones"] == 4 for f in filas)
    assert {f["artista"] for f in filas} == {"Izal", "Vetusta Morla", "C. Tangana"}


def test_c5_geoproximidad(ejecuta):
    filas = ejecuta("C5")
    assert len(filas) == 2, "solo dos recintos están a menos de 5 km de Sol"
    assert [f["recinto"] for f in filas] == ["La Riviera", "WiZink Center"], \
        "$geoNear ya devuelve el resultado ordenado por distancia"
    assert filas[0]["distancia_km"] == pytest.approx(1.24, abs=0.05)


def test_c6_carteles(ejecuta):
    filas = ejecuta("C6")
    assert len(filas) == 6, "seis eventos tienen más de un artista"
    for fila in filas:
        assert len(fila["cartel"]) > 1, "el cartel trae los datos de cada artista"
        assert all("pais" in a and "generos" in a for a in fila["cartel"])


def test_c7_franjas(ejecuta):
    filas = ejecuta("C7")
    assert sum(f["eventos"] for f in filas) == 32, \
        "todo evento cae en una franja: falta el default del $switch"
    assert {f["franja"] for f in filas} <= {"agotado", "alta", "media", "baja"}


# ── El informe materializado ────────────────────────────────────────────────

def test_c8_crea_el_informe(db, ejecuta):
    db.informe_recintos.drop()
    ejecuta("C8")
    assert db.informe_recintos.count_documents({}) == 6
    doc = db.informe_recintos.find_one({"_id": "La Riviera"})
    assert doc is not None
    assert doc["eventos"] == 3
    assert doc["ingresos"] == pytest.approx(180600, abs=1)


def test_c8_actualiza_en_lugar_de_sobrescribir(db, ejecuta):
    """El criterio que distingue $merge de $out."""
    db.informe_recintos.drop()
    ejecuta("C8")
    db.informe_recintos.update_one({"_id": "La Riviera"}, {"$set": {"revisado": True}})

    ejecuta("C8")                                     # segunda pasada

    assert db.informe_recintos.count_documents({}) == 6
    assert db.informe_recintos.count_documents({"revisado": True}) == 1, (
        "la marca ha desaparecido: $out reemplaza la colección entera, "
        "hace falta $merge"
    )
