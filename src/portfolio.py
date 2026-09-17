"""Logica di business: gestione posizioni/liquidita/conti deposito e calcolo del report."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from . import market_data, storage

VALUTA_BASE = "EUR"
TIPI_POSIZIONE = ["ETF", "Azione"]


# ---------------------------------------------------------------------------
# Inserimento / rimozione
# ---------------------------------------------------------------------------

def aggiungi_posizione(tipo: str, isin: str, quantita: float, prezzo_acquisto: float,
                        data_acquisto: str, valuta: str | None = None, note: str = "") -> dict:
    isin = isin.strip().upper()
    info = market_data.resolve_isin(isin)
    if info is None:
        raise ValueError(f"ISIN '{isin}' non trovato su Yahoo Finance. Verifica il codice.")

    df = storage.load("posizioni")
    riga = {
        "id": storage.next_id(df),
        "tipo": tipo,
        "isin": isin,
        "ticker": info["ticker"],
        "nome": info["nome"],
        "quantita": quantita,
        "prezzo_acquisto": prezzo_acquisto,
        "valuta": valuta or info.get("valuta") or VALUTA_BASE,
        "data_acquisto": data_acquisto,
        "note": note,
    }
    storage.append_row("posizioni", riga)
    return riga


def rimuovi_posizione(id_posizione) -> bool:
    return storage.remove_row("posizioni", id_posizione)


def aggiungi_liquidita(descrizione: str, importo: float, valuta: str = VALUTA_BASE, note: str = "") -> dict:
    df = storage.load("liquidita")
    riga = {
        "id": storage.next_id(df),
        "descrizione": descrizione,
        "importo": importo,
        "valuta": valuta,
        "data_aggiornamento": storage.oggi(),
        "note": note,
    }
    storage.append_row("liquidita", riga)
    return riga


def rimuovi_liquidita(id_liquidita) -> bool:
    return storage.remove_row("liquidita", id_liquidita)


def aggiungi_conto_deposito(banca: str, importo: float, tasso_annuo: float,
                             data_apertura: str, data_scadenza: str, note: str = "") -> dict:
    df = storage.load("conti_deposito")
    riga = {
        "id": storage.next_id(df),
        "banca": banca,
        "importo": importo,
        "tasso_annuo": tasso_annuo,
        "data_apertura": data_apertura,
        "data_scadenza": data_scadenza,
        "note": note,
    }
    storage.append_row("conti_deposito", riga)
    return riga


def rimuovi_conto_deposito(id_conto) -> bool:
    return storage.remove_row("conti_deposito", id_conto)


# ---------------------------------------------------------------------------
# Calcolo report
# ---------------------------------------------------------------------------

def _interessi_maturati(importo: float, tasso_annuo: float, data_apertura: str, data_scadenza: str) -> float:
    try:
        apertura = datetime.strptime(str(data_apertura), "%Y-%m-%d")
    except Exception:
        return 0.0
    oggi = datetime.now()
    try:
        scadenza = datetime.strptime(str(data_scadenza), "%Y-%m-%d")
        riferimento = min(oggi, scadenza)
    except Exception:
        riferimento = oggi
    giorni = max((riferimento - apertura).days, 0)
    return importo * (tasso_annuo / 100.0) * (giorni / 365.0)


def _interessi_a_scadenza(importo: float, tasso_annuo: float, data_apertura: str, data_scadenza: str) -> float:
    try:
        apertura = datetime.strptime(str(data_apertura), "%Y-%m-%d")
        scadenza = datetime.strptime(str(data_scadenza), "%Y-%m-%d")
    except Exception:
        return 0.0
    giorni = max((scadenza - apertura).days, 0)
    return importo * (tasso_annuo / 100.0) * (giorni / 365.0)


def calcola_portafoglio(forza_aggiornamento: bool = False) -> dict:
    avvisi: list[str] = []

    posizioni = storage.load("posizioni")
    for col in ["quantita", "prezzo_acquisto"]:
        posizioni[col] = pd.to_numeric(posizioni[col], errors="coerce").fillna(0.0)

    tickers = posizioni["ticker"].dropna().unique().tolist()
    prezzi = market_data.aggiorna_prezzi(tickers, forza=forza_aggiornamento)

    # La valuta di acquisto (quella scritta a mano) e la valuta in cui il ticker
    # è attualmente quotato su Yahoo Finance possono differire (es. stesso ISIN
    # quotato in USD su una borsa e in EUR su un'altra): vanno convertite separatamente.
    valute_coinvolte = set(posizioni["valuta"].dropna().unique())
    valute_coinvolte |= {info.get("valuta") for info in prezzi.values() if info.get("valuta")}
    valute_coinvolte |= {VALUTA_BASE}
    cambi = {v: market_data.tasso_cambio(v, VALUTA_BASE) for v in valute_coinvolte}

    righe = []
    for _, r in posizioni.iterrows():
        info_prezzo = prezzi.get(r["ticker"], {})
        prezzo_attuale = info_prezzo.get("prezzo")
        valuta_prezzo_attuale = info_prezzo.get("valuta") or r["valuta"]
        if info_prezzo.get("errore"):
            avvisi.append(f"{r['nome']} ({r['ticker']}): {info_prezzo['errore']}")

        cambio_acquisto = cambi.get(r["valuta"], 1.0)
        valore_investito_eur = r["quantita"] * r["prezzo_acquisto"] * cambio_acquisto

        if prezzo_attuale is not None:
            cambio_attuale = cambi.get(valuta_prezzo_attuale, 1.0)
            valore_attuale_eur = r["quantita"] * prezzo_attuale * cambio_attuale
        else:
            valore_attuale_eur = valore_investito_eur  # fallback prudente se prezzo non disponibile

        guadagno_assoluto = valore_attuale_eur - valore_investito_eur
        guadagno_percentuale = (guadagno_assoluto / valore_investito_eur * 100.0) if valore_investito_eur else 0.0

        righe.append({
            **r.to_dict(),
            "prezzo_attuale": prezzo_attuale,
            "valuta_prezzo_attuale": valuta_prezzo_attuale,
            "valore_investito_eur": valore_investito_eur,
            "valore_attuale_eur": valore_attuale_eur,
            "guadagno_assoluto_eur": guadagno_assoluto,
            "guadagno_percentuale": guadagno_percentuale,
        })
    posizioni_calc = pd.DataFrame(righe)

    allocazione_settore: dict[str, float] = {}
    if not posizioni_calc.empty:
        coppie = list(posizioni_calc[["ticker", "tipo"]].drop_duplicates().itertuples(index=False, name=None))
        settori_per_ticker = market_data.aggiorna_settori(coppie, forza=forza_aggiornamento)
        for _, r in posizioni_calc.iterrows():
            for settore, peso in settori_per_ticker.get(r["ticker"], {}).items():
                allocazione_settore[settore] = allocazione_settore.get(settore, 0.0) + r["valore_attuale_eur"] * peso

    liquidita = storage.load("liquidita")
    liquidita["importo"] = pd.to_numeric(liquidita["importo"], errors="coerce").fillna(0.0)
    if not liquidita.empty:
        liquidita["valore_eur"] = liquidita.apply(
            lambda r: r["importo"] * market_data.tasso_cambio(r["valuta"], VALUTA_BASE), axis=1)
    else:
        liquidita["valore_eur"] = []

    conti = storage.load("conti_deposito")
    for col in ["importo", "tasso_annuo"]:
        conti[col] = pd.to_numeric(conti[col], errors="coerce").fillna(0.0)
    if not conti.empty:
        conti["interessi_maturati_eur"] = conti.apply(
            lambda r: _interessi_maturati(r["importo"], r["tasso_annuo"], r["data_apertura"], r["data_scadenza"]),
            axis=1)
        conti["interessi_scadenza_eur"] = conti.apply(
            lambda r: _interessi_a_scadenza(r["importo"], r["tasso_annuo"], r["data_apertura"], r["data_scadenza"]),
            axis=1)
        conti["valore_attuale_eur"] = conti["importo"] + conti["interessi_maturati_eur"]
    else:
        conti["interessi_maturati_eur"] = []
        conti["interessi_scadenza_eur"] = []
        conti["valore_attuale_eur"] = []

    valore_posizioni = posizioni_calc["valore_attuale_eur"].sum() if not posizioni_calc.empty else 0.0
    valore_investito = posizioni_calc["valore_investito_eur"].sum() if not posizioni_calc.empty else 0.0
    valore_liquidita = liquidita["valore_eur"].sum() if not liquidita.empty else 0.0
    valore_conti = conti["valore_attuale_eur"].sum() if not conti.empty else 0.0
    valore_totale = valore_posizioni + valore_liquidita + valore_conti

    guadagno_assoluto_tot = valore_posizioni - valore_investito
    guadagno_percentuale_tot = (guadagno_assoluto_tot / valore_investito * 100.0) if valore_investito else 0.0

    allocazione_tipo = {
        "ETF": posizioni_calc.loc[posizioni_calc["tipo"] == "ETF", "valore_attuale_eur"].sum() if not posizioni_calc.empty else 0.0,
        "Azione": posizioni_calc.loc[posizioni_calc["tipo"] == "Azione", "valore_attuale_eur"].sum() if not posizioni_calc.empty else 0.0,
        "Liquidita": valore_liquidita,
        "Conto Deposito": valore_conti,
    }
    allocazione_tipo = {k: v for k, v in allocazione_tipo.items() if v}

    allocazione_valuta: dict[str, float] = {}
    if not posizioni_calc.empty:
        for _, r in posizioni_calc.iterrows():
            allocazione_valuta[r["valuta"]] = allocazione_valuta.get(r["valuta"], 0.0) + r["valore_attuale_eur"]
    if valore_liquidita:
        allocazione_valuta[VALUTA_BASE] = allocazione_valuta.get(VALUTA_BASE, 0.0) + valore_liquidita
    if valore_conti:
        allocazione_valuta[VALUTA_BASE] = allocazione_valuta.get(VALUTA_BASE, 0.0) + valore_conti

    totali = {
        "valore_posizioni": valore_posizioni,
        "valore_investito": valore_investito,
        "valore_liquidita": valore_liquidita,
        "valore_conti_deposito": valore_conti,
        "valore_totale": valore_totale,
        "guadagno_assoluto": guadagno_assoluto_tot,
        "guadagno_percentuale": guadagno_percentuale_tot,
    }

    return {
        "posizioni": posizioni_calc,
        "liquidita": liquidita,
        "conti_deposito": conti,
        "totali": totali,
        "allocazione_tipo": allocazione_tipo,
        "allocazione_valuta": allocazione_valuta,
        "allocazione_settore": allocazione_settore,
        "avvisi": avvisi,
    }


def salva_storico(totali: dict) -> None:
    storico = storage.load("storico_valore")
    oggi = storage.oggi()
    storico = storico[storico["data"] != oggi]
    nuova = pd.DataFrame([{
        "data": oggi,
        "valore_posizioni": totali["valore_posizioni"],
        "valore_liquidita": totali["valore_liquidita"],
        "valore_conti_deposito": totali["valore_conti_deposito"],
        "valore_totale": totali["valore_totale"],
        "valore_investito": totali["valore_investito"],
    }])
    storico = pd.concat([storico, nuova], ignore_index=True)
    storage.save("storico_valore", storico)


def carica_storico() -> pd.DataFrame:
    df = storage.load("storico_valore")
    for col in ["valore_posizioni", "valore_liquidita", "valore_conti_deposito", "valore_totale", "valore_investito"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df
