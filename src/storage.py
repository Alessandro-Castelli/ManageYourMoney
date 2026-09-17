"""Persistenza dati su file CSV locali (cartella data/)."""

from __future__ import annotations

import os
from datetime import datetime

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

SCHEMI = {
    "posizioni": ["id", "tipo", "isin", "ticker", "nome", "quantita", "prezzo_acquisto",
                  "valuta", "data_acquisto", "note"],
    "liquidita": ["id", "descrizione", "importo", "valuta", "data_aggiornamento", "note"],
    "conti_deposito": ["id", "banca", "importo", "tasso_annuo", "data_apertura",
                        "data_scadenza", "note"],
    "isin_ticker_map": ["isin", "ticker", "nome", "valuta"],
    "prezzi_cache": ["ticker", "prezzo", "valuta", "data_aggiornamento"],
    "settori_cache": ["ticker", "settore", "peso", "data_aggiornamento"],
    "storico_valore": ["data", "valore_posizioni", "valore_liquidita",
                        "valore_conti_deposito", "valore_totale", "valore_investito"],
}


def _path(nome: str) -> str:
    return os.path.join(DATA_DIR, f"{nome}.csv")


def ensure_data_files() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    for nome, colonne in SCHEMI.items():
        percorso = _path(nome)
        if not os.path.exists(percorso):
            pd.DataFrame(columns=colonne).to_csv(percorso, index=False)


def load(nome: str) -> pd.DataFrame:
    ensure_data_files()
    df = pd.read_csv(_path(nome), dtype=str)
    return df if df is not None else pd.DataFrame(columns=SCHEMI[nome])


def save(nome: str, df: pd.DataFrame) -> None:
    ensure_data_files()
    df.to_csv(_path(nome), index=False)


def next_id(df: pd.DataFrame) -> int:
    if df.empty:
        return 1
    return int(pd.to_numeric(df["id"]).max()) + 1


def append_row(nome: str, riga: dict) -> None:
    df = load(nome)
    nuova = pd.DataFrame([riga])
    df = pd.concat([df, nuova], ignore_index=True)
    save(nome, df)


def remove_row(nome: str, id_valore) -> bool:
    df = load(nome)
    prima = len(df)
    df = df[df["id"].astype(str) != str(id_valore)]
    save(nome, df)
    return len(df) < prima


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def oggi() -> str:
    return datetime.now().strftime("%Y-%m-%d")
