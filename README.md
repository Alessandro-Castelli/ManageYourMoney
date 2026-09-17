# Le Mie Finanze

Tracker personale di portafoglio: ETF, azioni, liquidità e conti deposito.
I dati sono persistiti in semplici file CSV nella cartella `data/` (nessun database,
nessun servizio esterno oltre al recupero prezzi). Ad ogni avvio i prezzi di
ETF/azioni vengono aggiornati automaticamente da Yahoo Finance.

## Installazione (una tantum)

```powershell
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
(basta il codice ISIN, il resto — nome, ticker, valuta — viene risolto in automatico),
liquidità e conti deposito, oltre alla rimozione di singoli elementi. Il pulsante
"Aggiorna prezzi ora" forza un refresh immediato (i prezzi si aggiornano comunque
in automatico ad ogni apertura, con una cache di 5 minuti per non interrogare
Yahoo Finance ad ogni click).

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
   il valore complessivo del portafoglio.

## Struttura dati (`data/*.csv`)

Puoi anche editare questi file a mano con Excel/LibreOffice se preferisci — sono
CSV semplici, ma occhio a non rompere l'intestazione delle colonne.

| File | Contenuto |
|---|---|
| `posizioni.csv` | ETF e azioni: ISIN, ticker, quantità, prezzo/data/valuta di acquisto |
| `liquidita.csv` | Conti correnti / contanti |
| `conti_deposito.csv` | Capitale, tasso annuo, data apertura/scadenza |
| `storico_valore.csv` | Snapshot giornaliero del valore totale (una riga per giorno, si aggiorna da sola) |
| `isin_ticker_map.csv` | Cache ISIN → ticker (evita di rifare la ricerca) |
| `prezzi_cache.csv` | Cache ultimo prezzo noto per ticker |

Per fare un backup del portafoglio basta copiare la cartella `data/`.

## Conti deposito: come viene calcolato l'interesse

Interesse semplice: `importo × tasso_annuo% × giorni_trascorsi / 365`, calcolato
dalla data di apertura a oggi (o alla data di scadenza se già superata). È una
**stima** al lordo di eventuali imposte/costi — non tiene conto di capitalizzazioni
composte o condizioni specifiche del conto.

## Note

- Serve una connessione internet per aggiornare i prezzi; senza connessione il
  programma resta usabile con gli ultimi valori noti in cache.
- Fonte prezzi: Yahoo Finance (via `yfinance`), a scopo personale/informativo.
- Se in console/terminale i caratteri accentati o i bordi delle tabelle appaiono
  come `?` o `�`, usa Windows Terminal o PowerShell (non il vecchio `cmd.exe`),
  oppure lancia `chcp 65001` prima di `python main.py`.
