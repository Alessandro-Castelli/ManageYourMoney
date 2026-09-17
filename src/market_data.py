"""Recupero dati di mercato: risoluzione ISIN -> ticker e prezzi live.

Usa la search pubblica di Yahoo Finance per risolvere un ISIN in un ticker
(con cache locale su CSV per non richiamarla ogni volta) e yfinance per
scaricare prezzo corrente e valuta. In caso di assenza di connessione
o di errore, ricade sull'ultimo prezzo noto in cache.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import requests
import yfinance as yf

from . import storage

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
_SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"


def _yahoo_search(query: str) -> list[dict]:
    try:
        resp = requests.get(
            _SEARCH_URL,
            params={"q": query, "quotesCount": 6, "newsCount": 0},
            headers=_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("quotes", [])
    except Exception:
        return []


def _scegli_miglior_candidato(candidati: list[dict]) -> dict:
    for q in candidati:
        if str(q.get("symbol", "")).endswith(".MI"):
            return q
    return candidati[0]


def prezzo_e_valuta(ticker: str) -> tuple[float | None, str | None]:
    """Ritorna (prezzo, valuta) correnti per un ticker, o (None, None) se non disponibile."""
    try:
        t = yf.Ticker(ticker)
        info = {}
        try:
            info = dict(t.fast_info)
        except Exception:
            info = {}
        prezzo = info.get("lastPrice")
        valuta = info.get("currency")
        if prezzo is None:
            hist = t.history(period="5d")
            if not hist.empty:
                prezzo = float(hist["Close"].dropna().iloc[-1])
        if valuta is None:
            try:
                valuta = t.info.get("currency")
            except Exception:
                valuta = None
        return (float(prezzo) if prezzo is not None else None, valuta)
    except Exception:
        return (None, None)


def resolve_isin(isin: str) -> dict | None:
    """Risolve un ISIN in ticker/nome/valuta, usando la cache locale se presente."""
    isin = isin.strip().upper()
    cache = storage.load("isin_ticker_map")
    match = cache[cache["isin"] == isin]
    if not match.empty:
        riga = match.iloc[0]
        return {"ticker": riga["ticker"], "nome": riga["nome"], "valuta": riga["valuta"]}

    candidati = [q for q in _yahoo_search(isin) if q.get("symbol")]
    if not candidati:
        return None

    scelto = _scegli_miglior_candidato(candidati)
    ticker = scelto["symbol"]
    nome = scelto.get("shortname") or scelto.get("longname") or ticker
    _, valuta = prezzo_e_valuta(ticker)

    storage.append_row("isin_ticker_map", {
        "isin": isin, "ticker": ticker, "nome": nome, "valuta": valuta or "",
    })
    return {"ticker": ticker, "nome": nome, "valuta": valuta}


def tasso_cambio(da: str, a: str) -> float:
    """Tasso di cambio da -> a. Ritorna 1.0 se le valute coincidono o in caso di errore."""
    da, a = (da or "EUR").upper(), (a or "EUR").upper()
    if da == a:
        return 1.0
    prezzo, _ = prezzo_e_valuta(f"{da}{a}=X")
    if prezzo:
        return prezzo
    prezzo_inv, _ = prezzo_e_valuta(f"{a}{da}=X")
    if prezzo_inv:
        return 1.0 / prezzo_inv
    return 1.0


def aggiorna_prezzi(tickers: list[str], forza: bool = False, validita_minuti: int = 5) -> dict[str, dict]:
    """Aggiorna la cache prezzi per i ticker richiesti e ritorna {ticker: {prezzo, valuta, aggiornato}}."""
    tickers = sorted(set(t for t in tickers if t))
    cache = storage.load("prezzi_cache")
    risultati: dict[str, dict] = {}
    ora = datetime.now()

    for ticker in tickers:
        riga_cache = cache[cache["ticker"] == ticker]
        fresco = False
        if not forza and not riga_cache.empty:
            try:
                ts = datetime.strptime(riga_cache.iloc[0]["data_aggiornamento"], "%Y-%m-%d %H:%M:%S")
                fresco = (ora - ts).total_seconds() < validita_minuti * 60
            except Exception:
                fresco = False

        if fresco:
            r = riga_cache.iloc[0]
            risultati[ticker] = {"prezzo": float(r["prezzo"]), "valuta": r["valuta"], "aggiornato": False}
            continue

        prezzo, valuta = prezzo_e_valuta(ticker)
        if prezzo is None:
            if not riga_cache.empty:
                r = riga_cache.iloc[0]
                risultati[ticker] = {
                    "prezzo": float(r["prezzo"]), "valuta": r["valuta"],
                    "aggiornato": False, "errore": "prezzo non raggiungibile, uso ultima cache",
                }
            else:
                risultati[ticker] = {"prezzo": None, "valuta": None, "aggiornato": False, "errore": "prezzo non disponibile"}
            continue

        cache = cache[cache["ticker"] != ticker]
        cache = pd.concat([cache, pd.DataFrame([{
            "ticker": ticker, "prezzo": prezzo, "valuta": valuta or "", "data_aggiornamento": storage.timestamp(),
        }])], ignore_index=True)
        risultati[ticker] = {"prezzo": prezzo, "valuta": valuta, "aggiornato": True}

    storage.save("prezzi_cache", cache)
    return risultati


def _normalizza_settore(chiave: str) -> str:
    k = str(chiave).strip().lower().replace(" ", "_").replace("-", "_")
    return "real_estate" if k == "realestate" else k


def settori_posizione(ticker: str, tipo: str) -> dict[str, float]:
    """Ritorna {settore_canonico: peso 0-1} per un ticker. Dict vuoto se non disponibile.

    Per un ETF usa la scomposizione settoriale del fondo (yfinance); per un'azione
    usa il settore GICS della singola società (peso 1.0, è tutta in quel settore).
    """
    try:
        t = yf.Ticker(ticker)
        if tipo == "ETF":
            pesi = dict(t.funds_data.sector_weightings or {})
            return {_normalizza_settore(k): float(v) for k, v in pesi.items() if v}
        try:
            settore = t.info.get("sector")
        except Exception:
            settore = None
        return {_normalizza_settore(settore): 1.0} if settore else {}
    except Exception:
        return {}


def aggiorna_settori(posizioni: list[tuple[str, str]], forza: bool = False,
                      validita_minuti: int = 1440) -> dict[str, dict[str, float]]:
    """Aggiorna la cache settori per (ticker, tipo) richiesti e ritorna {ticker: {settore: peso}}.

    Cache valida 1 giorno di default: la composizione di un fondo cambia lentamente,
    a differenza del prezzo non serve rinfrescarla ad ogni accesso.
    """
    posizioni = list({(tk, tp) for tk, tp in posizioni if tk})
    cache = storage.load("settori_cache")
    risultati: dict[str, dict[str, float]] = {}
    ora = datetime.now()

    for ticker, tipo in posizioni:
        righe_cache = cache[cache["ticker"] == ticker]
        fresco = False
        if not forza and not righe_cache.empty:
            try:
                ts = datetime.strptime(righe_cache.iloc[0]["data_aggiornamento"], "%Y-%m-%d %H:%M:%S")
                fresco = (ora - ts).total_seconds() < validita_minuti * 60
            except Exception:
                fresco = False

        if fresco:
            risultati[ticker] = {r["settore"]: float(r["peso"]) for _, r in righe_cache.iterrows()}
            continue

        pesi = settori_posizione(ticker, tipo)
        cache = cache[cache["ticker"] != ticker]
        if pesi:
            nuove = pd.DataFrame([
                {"ticker": ticker, "settore": s, "peso": p, "data_aggiornamento": storage.timestamp()}
                for s, p in pesi.items()
            ])
            cache = pd.concat([cache, nuove], ignore_index=True)
        risultati[ticker] = pesi

    storage.save("settori_cache", cache)
    return risultati
