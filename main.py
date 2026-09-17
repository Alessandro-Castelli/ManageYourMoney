"""CLI interattiva per il tracker di finanze personali.

Avvio: python main.py
Ad ogni avvio aggiorna automaticamente i prezzi di ETF/azioni in portafoglio
e mostra il report aggiornato. Persistenza dati su file CSV in data/.
"""

from __future__ import annotations

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, FloatPrompt, Prompt
from rich.table import Table

from src import portfolio, storage

console = Console()


def mostra_report(dati: dict) -> None:
    posizioni = dati["posizioni"]
    if not posizioni.empty:
        tabella = Table(title="ETF / Azioni", show_lines=False)
        for col in ["Tipo", "Nome", "ISIN", "Ticker", "Quantità", "Prezzo acq.",
                    "Prezzo att.", "Valore (EUR)", "Guad./Perd. (EUR)", "Guad./Perd. (%)"]:
            tabella.add_column(col)
        for _, r in posizioni.iterrows():
            colore = "green" if r["guadagno_assoluto_eur"] >= 0 else "red"
            tabella.add_row(
                r["tipo"], str(r["nome"])[:28], r["isin"], r["ticker"],
                f"{r['quantita']:.4f}", f"{r['prezzo_acquisto']:.2f} {r['valuta']}",
                f"{r['prezzo_attuale']:.2f} {r['valuta_prezzo_attuale']}" if pd.notna(r["prezzo_attuale"]) else "n/d",
                f"{r['valore_attuale_eur']:.2f}",
                f"[{colore}]{r['guadagno_assoluto_eur']:+.2f}[/{colore}]",
                f"[{colore}]{r['guadagno_percentuale']:+.2f}%[/{colore}]",
            )
        console.print(tabella)
    else:
        console.print("[dim]Nessuna posizione ETF/Azione registrata.[/dim]")

    liquidita = dati["liquidita"]
    if not liquidita.empty:
        tabella = Table(title="Liquidità")
        for col in ["ID", "Descrizione", "Importo", "Valuta", "Valore (EUR)"]:
            tabella.add_column(col)
        for _, r in liquidita.iterrows():
            tabella.add_row(str(r["id"]), r["descrizione"], f"{r['importo']:.2f}", r["valuta"], f"{r['valore_eur']:.2f}")
        console.print(tabella)

    conti = dati["conti_deposito"]
    if not conti.empty:
        tabella = Table(title="Conti Deposito")
        for col in ["ID", "Banca", "Importo", "Tasso annuo", "Apertura", "Scadenza",
                    "Interessi maturati (stima)", "Interessi a scadenza (lordi)", "Valore attuale"]:
            tabella.add_column(col)
        for _, r in conti.iterrows():
            tabella.add_row(
                str(r["id"]), r["banca"], f"{r['importo']:.2f}", f"{r['tasso_annuo']:.2f}%",
                r["data_apertura"], r["data_scadenza"],
                f"{r['interessi_maturati_eur']:.2f}", f"{r['interessi_scadenza_eur']:.2f}",
                f"{r['valore_attuale_eur']:.2f}",
            )
        console.print(tabella)

    t = dati["totali"]
    colore = "green" if t["guadagno_assoluto"] >= 0 else "red"
    testo = (
        f"Valore totale portafoglio: [bold]{t['valore_totale']:.2f} EUR[/bold]\n"
        f"  - ETF/Azioni:     {t['valore_posizioni']:.2f} EUR "
        f"(investito {t['valore_investito']:.2f} EUR, "
        f"[{colore}]{t['guadagno_assoluto']:+.2f} EUR / {t['guadagno_percentuale']:+.2f}%[/{colore}])\n"
        f"  - Liquidità:      {t['valore_liquidita']:.2f} EUR\n"
        f"  - Conti Deposito: {t['valore_conti_deposito']:.2f} EUR"
    )
    console.print(Panel(testo, title="Riepilogo", border_style="cyan"))

    if dati["avvisi"]:
        for a in dati["avvisi"]:
            console.print(f"[yellow]Avviso:[/yellow] {a}")


def aggiorna_e_mostra(forza: bool = True) -> None:
    with console.status("[bold cyan]Aggiornamento prezzi in corso..."):
        dati = portfolio.calcola_portafoglio(forza_aggiornamento=forza)
    portfolio.salva_storico(dati["totali"])
    mostra_report(dati)


def azione_aggiungi_posizione() -> None:
    tipo = Prompt.ask("Tipo", choices=["ETF", "Azione"], default="ETF")
    isin = Prompt.ask("Codice ISIN")
    quantita = FloatPrompt.ask("Quantità")
    prezzo_acquisto = FloatPrompt.ask("Prezzo di acquisto (per unità)")
    valuta = Prompt.ask("Valuta di acquisto", default="EUR")
    data_acquisto = Prompt.ask("Data di acquisto (YYYY-MM-DD)", default=storage.oggi())
    note = Prompt.ask("Note (opzionale)", default="")
    try:
        riga = portfolio.aggiungi_posizione(tipo, isin, quantita, prezzo_acquisto, data_acquisto, valuta, note)
        if riga["nuova_posizione"]:
            console.print(f"[green]Aggiunta posizione:[/green] {riga['nome']} ({riga['ticker']})")
        else:
            console.print(
                f"[green]Versamento aggiunto a posizione esistente:[/green] {riga['nome']} — "
                f"quantità totale {float(riga['quantita']):.4f}, prezzo medio di carico "
                f"{float(riga['prezzo_acquisto']):.4f} {riga['valuta']}"
            )
    except ValueError as e:
        console.print(f"[red]Errore:[/red] {e}")


def azione_aggiungi_liquidita() -> None:
    descrizione = Prompt.ask("Descrizione (es. Conto corrente)")
    importo = FloatPrompt.ask("Importo")
    valuta = Prompt.ask("Valuta", default="EUR")
    note = Prompt.ask("Note (opzionale)", default="")
    portfolio.aggiungi_liquidita(descrizione, importo, valuta, note)
    console.print("[green]Liquidità aggiunta.[/green]")


def azione_aggiungi_conto_deposito() -> None:
    banca = Prompt.ask("Banca")
    importo = FloatPrompt.ask("Importo depositato")
    tasso = FloatPrompt.ask("Tasso annuo lordo (%)")
    apertura = Prompt.ask("Data apertura (YYYY-MM-DD)", default=storage.oggi())
    scadenza = Prompt.ask("Data scadenza (YYYY-MM-DD)")
    note = Prompt.ask("Note (opzionale)", default="")
    portfolio.aggiungi_conto_deposito(banca, importo, tasso, apertura, scadenza, note)
    console.print("[green]Conto deposito aggiunto.[/green]")


def azione_rimuovi() -> None:
    categoria = Prompt.ask("Cosa vuoi rimuovere?", choices=["posizione", "liquidita", "conto_deposito"])
    id_valore = Prompt.ask("ID da rimuovere")
    mappa = {
        "posizione": portfolio.rimuovi_posizione,
        "liquidita": portfolio.rimuovi_liquidita,
        "conto_deposito": portfolio.rimuovi_conto_deposito,
    }
    if mappa[categoria](id_valore):
        console.print("[green]Rimosso.[/green]")
    else:
        console.print("[yellow]ID non trovato.[/yellow]")


def azione_storico() -> None:
    storico = portfolio.carica_storico()
    if storico.empty:
        console.print("[dim]Nessuno storico disponibile ancora.[/dim]")
        return
    tabella = Table(title="Storico valore portafoglio")
    for col in ["Data", "Posizioni", "Liquidità", "Conti Deposito", "Totale"]:
        tabella.add_column(col)
    for _, r in storico.sort_values("data").iterrows():
        tabella.add_row(
            r["data"], f"{r['valore_posizioni']:.2f}", f"{r['valore_liquidita']:.2f}",
            f"{r['valore_conti_deposito']:.2f}", f"{r['valore_totale']:.2f}",
        )
    console.print(tabella)


MENU = """
[bold]Cosa vuoi fare?[/bold]
  1) Aggiorna e mostra il portafoglio
  2) Aggiungi ETF/Azione
  3) Aggiungi liquidità
  4) Aggiungi conto deposito
  5) Rimuovi una posizione / liquidità / conto deposito
  6) Mostra storico valore portafoglio
  0) Esci
"""


def main() -> None:
    storage.ensure_data_files()
    console.print(Panel("Le Mie Finanze - tracker di portafoglio", style="bold cyan"))
    aggiorna_e_mostra()

    while True:
        console.print(MENU)
        scelta = Prompt.ask("Scelta", choices=["0", "1", "2", "3", "4", "5", "6"], default="0")
        if scelta == "1":
            aggiorna_e_mostra()
        elif scelta == "2":
            azione_aggiungi_posizione()
        elif scelta == "3":
            azione_aggiungi_liquidita()
        elif scelta == "4":
            azione_aggiungi_conto_deposito()
        elif scelta == "5":
            azione_rimuovi()
        elif scelta == "6":
            azione_storico()
        elif scelta == "0":
            if Confirm.ask("Uscire?", default=True):
                break


if __name__ == "__main__":
    main()
