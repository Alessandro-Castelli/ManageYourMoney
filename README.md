# 💶 Le Mie Finanze

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Streamlit](https://img.shields.io/badge/dashboard-Streamlit-ff4b4b)
![Data](https://img.shields.io/badge/dati-100%25%20locali-lightgrey)
[![GitHub stars](https://img.shields.io/github/stars/Alessandro-Castelli/ManageYourMoney?style=social)](https://github.com/Alessandro-Castelli/ManageYourMoney/stargazers)
![Last commit](https://img.shields.io/github/last-commit/Alessandro-Castelli/ManageYourMoney)

**Tracker di portafoglio personale — ETF, azioni, liquidità e conti deposito.**
Inserisci solo il codice ISIN: prezzo, ticker e valuta vengono risolti in automatico.
Nessun database, nessun account, nessun cloud — solo file CSV sul tuo computer.

> A personal portfolio tracker (ETFs, stocks, cash, term deposits) for Yahoo Finance
> data. Just paste an ISIN — ticker/price/currency are resolved automatically.
> 100% local CSV storage, no account, no cloud. UI and docs are in Italian.

## Perché usarlo

- 🔒 **I tuoi dati restano tuoi**: tutto vive in CSV locali in `data/`, niente viene
  inviato a server esterni (a parte le richieste di prezzo a Yahoo Finance).
- 🔍 **Zero data entry inutile**: basta l'ISIN, il resto (nome, ticker, valuta di
  quotazione) viene risolto e salvato in cache automaticamente.
- 📈 **Pensato per i PAC**: se versi periodicamente sullo stesso ETF, il sistema
  aggiorna quantità e prezzo medio di carico invece di creare righe duplicate.
- 🌍 **Multi-valuta**: gestisce posizioni quotate in valute diverse dall'EUR,
  convertendo al cambio corrente — anche quando il prezzo di acquisto e quello
  attuale sono in valute diverse (stesso ISIN, quotazioni su borse diverse).
- 🏦 **Conti deposito con proiezione interessi**: interesse maturato ad oggi *e*
  stima di quanto maturerà a scadenza.
- 🖥️ **Due interfacce, stessi dati**: dashboard web con grafici (Streamlit) o CLI da
  terminale — scegli quella che preferisci, senza duplicare nulla.
- 💸 **Gratis e senza chiavi API**: usa la ricerca pubblica e `yfinance` di Yahoo
  Finance, nessuna registrazione richiesta.

## Installazione

```powershell
git clone https://github.com/Alessandro-Castelli/ManageYourMoney.git
cd ManageYourMoney
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Uso

Due interfacce equivalenti, stessi dati:

**Dashboard web (raccomandata, con grafici):**

```powershell
streamlit run app.py
```

Si apre nel browser. Nella barra laterale trovi i form per aggiungere ETF/azioni
(basta il codice ISIN), liquidità e conti deposito, oltre alla rimozione di singoli
elementi. Il pulsante "Aggiorna prezzi ora" forza un refresh immediato (i prezzi si
aggiornano comunque in automatico ad ogni apertura, con una cache di 5 minuti per non
interrogare Yahoo Finance ad ogni click).

**CLI da terminale:**

```powershell
python main.py
```

Menu testuale con le stesse operazioni: all'avvio mostra subito il portafoglio
aggiornato, poi permette di aggiungere/rimuovere posizioni e consultare lo storico.

## Come funziona il recupero prezzi

1. Inserisci un **codice ISIN** (es. `IE00B4L5Y983`).
2. Il sistema lo risolve in un ticker Yahoo Finance tramite la ricerca pubblica di
   Yahoo (preferendo, se disponibile, la quotazione su Borsa Italiana `.MI`), e
   salva la corrispondenza in `data/isin_ticker_map.csv` così non serve rifarlo.
3. Ad ogni accesso il prezzo corrente e la valuta di quotazione vengono scaricati
   con `yfinance` e salvati in `data/prezzi_cache.csv` (validi 5 minuti).
4. Se manca la connessione o il prezzo non è raggiungibile, viene usato l'ultimo
   prezzo noto in cache e compare un avviso nel report.
5. Le valute diverse da EUR vengono convertite al cambio corrente per calcolare
   il valore complessivo del portafoglio — la valuta di acquisto e quella del
   prezzo attuale vengono convertite **separatamente**, perché lo stesso ISIN può
   essere quotato in valute diverse su borse diverse.

## Funzionalità principali

| Area | Dettaglio |
|---|---|
| ETF / Azioni | ISIN → ticker automatico, prezzi live, guadagno/perdita per posizione e totale |
| Versamenti periodici (PAC) | Nuovo acquisto sullo stesso ISIN → quantità e prezzo medio aggiornati, non righe duplicate |
| Allocazione | Grafici per tipo di asset, per valuta, per settore economico (ETF/azioni) |
| Liquidità | Conti correnti/contanti multi-valuta |
| Conti deposito | Interesse maturato ad oggi + proiezione interesse lordo a scadenza |
| Storico | Snapshot giornaliero del valore totale, grafico dell'andamento nel tempo |
| Persistenza | Solo CSV locali, editabili anche a mano con Excel/LibreOffice |

## Struttura dati (`data/*.csv`)

| File | Contenuto |
|---|---|
| `posizioni.csv` | ETF e azioni: ISIN, ticker, quantità, prezzo/data/valuta di acquisto |
| `liquidita.csv` | Conti correnti / contanti |
| `conti_deposito.csv` | Capitale, tasso annuo, data apertura/scadenza |
| `storico_valore.csv` | Snapshot giornaliero del valore totale (una riga per giorno, si aggiorna da sola) |
| `isin_ticker_map.csv` | Cache ISIN → ticker (evita di rifare la ricerca) |
| `prezzi_cache.csv` | Cache ultimo prezzo noto per ticker |
| `settori_cache.csv` | Cache composizione settoriale per ticker (validità 1 giorno) |

Per fare un backup del portafoglio basta copiare la cartella `data/`.

## Conti deposito: come vengono calcolati gli interessi

Interesse semplice: `importo × tasso_annuo% × giorni / 365`. Due valori mostrati:
- **Maturati ad oggi**: giorni da apertura a oggi (o a scadenza se già superata).
- **A scadenza (lordi)**: giorni sull'intero periodo apertura→scadenza, quindi quanto
  otterrai lordo se lo tieni fino alla fine.

Sono **stime** al lordo di imposte/costi — non tengono conto di capitalizzazione
composta o condizioni specifiche della banca.

## Roadmap / idee

- [ ] Composizione geografica manuale per ETF (Yahoo Finance non la fornisce)
- [ ] Esportazione report in PDF/Excel
- [ ] Notifiche/alert su soglie di prezzo
- [ ] Grafico storico anche per singola posizione (non solo totale portafoglio)

Contributi e idee sono benvenuti — apri una issue o una pull request.

## Contribuire

Progetto semplice, PR benvenute. Prima di proporre una modifica grossa apri una issue
per discuterne. Nessun processo formale: fork, branch, PR.

## Licenza

[MIT](LICENSE) — usa, modifica e redistribuisci liberamente, anche commercialmente,
mantenendo la nota di copyright.

## Disclaimer

Progetto personale a scopo informativo. I prezzi arrivano da Yahoo Finance (via
`yfinance`) e possono essere ritardati, imprecisi o temporaneamente non disponibili:
non è una fonte ufficiale né uno strumento di consulenza finanziaria. Usalo a tuo
rischio; verifica sempre i dati importanti (es. valore reale del portafoglio) con la
tua banca/broker.

## Note tecniche

- Serve una connessione internet per aggiornare i prezzi; senza connessione il
  programma resta usabile con gli ultimi valori noti in cache.
- Se in console/terminale i caratteri accentati o i bordi delle tabelle appaiono
  come `?` o `�`, usa Windows Terminal o PowerShell (non il vecchio `cmd.exe`),
  oppure lancia `chcp 65001` prima di `python main.py`.
