"""Dashboard web locale (Streamlit) per il tracker di finanze personali.

Avvio: streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import portfolio, storage

# Palette categoriale fissa (dataviz skill) - ordine mai ciclato, l'entità mantiene
# sempre lo stesso colore anche se il set di categorie visibili cambia.
COLORI_TIPO = {
    "ETF": "#2a78d6",
    "Azione": "#eb6834",
    "Liquidita": "#1baf7a",
    "Conto Deposito": "#eda100",
}
PALETTE_EXTRA = ["#e87ba4", "#008300", "#4a3aa7", "#e34948"]
BLU_SEQ = "#2a78d6"
ARANCIO_SEQ = "#eb6834"
BUONO = "#006300"
CRITICO = "#d03b3b"

# Settori "primari" con colore fisso; qualsiasi altro settore (o non classificato)
# confluisce sempre nel bucket "Altro" con colore neutro - mai un colore per rank.
COLORI_SETTORE = {
    "technology": "#2a78d6",
    "financial_services": "#eb6834",
    "healthcare": "#1baf7a",
    "consumer_cyclical": "#eda100",
    "industrials": "#e87ba4",
    "communication_services": "#008300",
    "consumer_defensive": "#4a3aa7",
}
COLORE_ALTRO = "#898781"
ETICHETTE_SETTORE = {
    "technology": "Tecnologia",
    "financial_services": "Servizi Finanziari",
    "healthcare": "Salute",
    "consumer_cyclical": "Consumi Ciclici",
    "industrials": "Industria",
    "communication_services": "Comunicazione",
    "consumer_defensive": "Consumi Defensivi",
    "energy": "Energia",
    "utilities": "Utility",
    "real_estate": "Immobiliare",
    "basic_materials": "Materie Prime",
}

st.set_page_config(page_title="Le Mie Finanze", layout="wide", page_icon="💶")
storage.ensure_data_files()


def colore_valuta(valuta: str, assegnati: dict[str, str]) -> str:
    if valuta not in assegnati:
        usati = set(assegnati.values())
        for c in list(COLORI_TIPO.values()) + PALETTE_EXTRA:
            if c not in usati:
                assegnati[valuta] = c
                break
        else:
            assegnati[valuta] = "#898781"
    return assegnati[valuta]


@st.cache_data(ttl=300, show_spinner=False)
def _carica_dati(forza: bool, nonce: int) -> dict:
    return portfolio.calcola_portafoglio(forza_aggiornamento=forza)


st.title("💶 Le Mie Finanze")
st.caption("Portafoglio ETF, azioni, liquidità e conti deposito — dati persistiti su CSV locali in `data/`.")

col_refresh, _ = st.columns([1, 5])
if col_refresh.button("🔄 Aggiorna prezzi ora"):
    st.session_state["nonce"] = st.session_state.get("nonce", 0) + 1
    _carica_dati.clear()

with st.spinner("Recupero prezzi aggiornati..."):
    dati = _carica_dati(False, st.session_state.get("nonce", 0))
portfolio.salva_storico(dati["totali"])

t = dati["totali"]

# --- KPI row -----------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Valore Totale", f"€ {t['valore_totale']:,.2f}")
c2.metric(
    "ETF / Azioni",
    f"€ {t['valore_posizioni']:,.2f}",
    f"{t['guadagno_assoluto']:+,.2f} € ({t['guadagno_percentuale']:+.2f}%)",
)
c3.metric("Liquidità", f"€ {t['valore_liquidita']:,.2f}")
c4.metric("Conti Deposito", f"€ {t['valore_conti_deposito']:,.2f}")

if dati["avvisi"]:
    for a in dati["avvisi"]:
        st.warning(a)

st.divider()

# --- Allocazione ---------------------------------------------------------
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Allocazione per tipo di asset")
    alloc_tipo = dati["allocazione_tipo"]
    if alloc_tipo:
        totale = sum(alloc_tipo.values())
        fig = go.Figure()
        for tipo, valore in alloc_tipo.items():
            pct = valore / totale * 100 if totale else 0
            fig.add_trace(go.Bar(
                y=["Portafoglio"], x=[valore], name=tipo, orientation="h",
                marker_color=COLORI_TIPO.get(tipo, "#898781"),
                text=f"{tipo}<br>€ {valore:,.0f} ({pct:.0f}%)", textposition="inside",
                hovertemplate=f"{tipo}: €%{{x:,.2f}} ({pct:.1f}%)<extra></extra>",
            ))
        fig.update_layout(
            barmode="stack", showlegend=True, height=220,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="EUR", yaxis=dict(visible=False),
            legend=dict(orientation="h", yanchor="bottom", y=-0.4),
        )
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("Nessun dato ancora: aggiungi una posizione, liquidità o un conto deposito.")

with col_b:
    st.subheader("Allocazione per valuta")
    alloc_valuta = dati["allocazione_valuta"]
    if len(alloc_valuta) > 1:
        assegnati: dict[str, str] = {}
        totale = sum(alloc_valuta.values())
        fig = go.Figure()
        for valuta, valore in alloc_valuta.items():
            pct = valore / totale * 100 if totale else 0
            fig.add_trace(go.Bar(
                y=["Portafoglio"], x=[valore], name=valuta, orientation="h",
                marker_color=colore_valuta(valuta, assegnati),
                text=f"{valuta}<br>€ {valore:,.0f} ({pct:.0f}%)", textposition="inside",
                hovertemplate=f"{valuta}: €%{{x:,.2f}} ({pct:.1f}%)<extra></extra>",
            ))
        fig.update_layout(
            barmode="stack", showlegend=True, height=220,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="EUR", yaxis=dict(visible=False),
            legend=dict(orientation="h", yanchor="bottom", y=-0.4),
        )
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("Portafoglio in un'unica valuta: nessuna scomposizione necessaria.")

st.subheader("Allocazione per settore (ETF / Azioni)")
alloc_settore = dati["allocazione_settore"]
if alloc_settore:
    primari = {s: v for s, v in alloc_settore.items() if s in COLORI_SETTORE}
    resto = sum(v for s, v in alloc_settore.items() if s not in COLORI_SETTORE)
    segmenti = sorted(primari.items(), key=lambda x: -x[1])
    if resto:
        segmenti.append(("altro", resto))
    totale = sum(alloc_settore.values())

    fig = go.Figure()
    for settore, valore in segmenti:
        pct = valore / totale * 100 if totale else 0
        etichetta = "Altro" if settore == "altro" else ETICHETTE_SETTORE.get(settore, settore.title())
        colore = COLORE_ALTRO if settore == "altro" else COLORI_SETTORE[settore]
        fig.add_trace(go.Bar(
            y=["Portafoglio"], x=[valore], name=etichetta, orientation="h",
            marker_color=colore,
            text=f"{etichetta}<br>€ {valore:,.0f} ({pct:.0f}%)", textposition="inside",
            hovertemplate=f"{etichetta}: €%{{x:,.2f}} ({pct:.1f}%)<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack", showlegend=True, height=220,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="EUR", yaxis=dict(visible=False),
        legend=dict(orientation="h", yanchor="bottom", y=-0.5),
    )
    st.plotly_chart(fig, width='stretch')
    st.caption("Composizione settoriale dei fondi/azioni in portafoglio (Yahoo Finance). "
               "Non disponibile la scomposizione per area geografica per questi ETF.")
else:
    st.info("Composizione settoriale non disponibile per le posizioni attuali.")

# --- Composizione posizioni ----------------------------------------------
posizioni = dati["posizioni"]
if not posizioni.empty:
    st.subheader("Valore per singola posizione")
    ordinate = posizioni.sort_values("valore_attuale_eur", ascending=True)
    fig = go.Figure()
    for tipo in ordinate["tipo"].unique():
        sotto = ordinate[ordinate["tipo"] == tipo]
        fig.add_trace(go.Bar(
            y=sotto["nome"], x=sotto["valore_attuale_eur"], name=tipo, orientation="h",
            marker_color=COLORI_TIPO.get(tipo, "#898781"),
            customdata=sotto[["guadagno_percentuale", "isin"]],
            hovertemplate="%{y}<br>Valore: €%{x:,.2f}<br>ISIN: %{customdata[1]}<br>Guad./Perd.: %{customdata[0]:+.2f}%<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack", height=max(220, 40 * len(ordinate)),
        margin=dict(l=10, r=10, t=10, b=10), xaxis_title="EUR",
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
    )
    st.plotly_chart(fig, width='stretch')

    st.subheader("Dettaglio ETF / Azioni")
    tabella = posizioni.rename(columns={
        "tipo": "Tipo", "nome": "Nome", "isin": "ISIN", "ticker": "Ticker",
        "quantita": "Quantità", "prezzo_acquisto": "Prezzo acq.", "valuta": "Valuta acq.",
        "prezzo_attuale": "Prezzo att.", "valuta_prezzo_attuale": "Valuta att.",
        "valore_attuale_eur": "Valore (EUR)",
        "guadagno_assoluto_eur": "Guad./Perd. (EUR)", "guadagno_percentuale": "Guad./Perd. (%)",
        "data_acquisto": "Data acquisto",
    })[["Tipo", "Nome", "ISIN", "Ticker", "Quantità", "Prezzo acq.", "Valuta acq.",
        "Prezzo att.", "Valuta att.", "Valore (EUR)", "Guad./Perd. (EUR)", "Guad./Perd. (%)", "Data acquisto"]]
    st.dataframe(
        tabella, hide_index=True, width='stretch',
        column_config={
            "Prezzo acq.": st.column_config.NumberColumn(format="%.2f"),
            "Prezzo att.": st.column_config.NumberColumn(format="%.2f"),
            "Valore (EUR)": st.column_config.NumberColumn(format="€ %.2f"),
            "Guad./Perd. (EUR)": st.column_config.NumberColumn(format="%+.2f"),
            "Guad./Perd. (%)": st.column_config.NumberColumn(format="%+.2f%%"),
        },
    )
else:
    st.info("Nessuna posizione ETF/Azione: aggiungine una dalla barra laterale.")

# --- Liquidità e conti deposito -------------------------------------------
col_liq, col_cd = st.columns(2)
with col_liq:
    st.subheader("Liquidità")
    liquidita = dati["liquidita"]
    if not liquidita.empty:
        st.dataframe(
            liquidita.rename(columns={
                "descrizione": "Descrizione", "importo": "Importo", "valuta": "Valuta",
                "valore_eur": "Valore (EUR)",
            })[["id", "Descrizione", "Importo", "Valuta", "Valore (EUR)"]],
            hide_index=True, width='stretch',
        )
    else:
        st.info("Nessuna liquidità registrata.")

with col_cd:
    st.subheader("Conti Deposito")
    conti = dati["conti_deposito"]
    if not conti.empty:
        st.dataframe(
            conti.rename(columns={
                "banca": "Banca", "importo": "Importo", "tasso_annuo": "Tasso annuo lordo (%)",
                "data_apertura": "Apertura", "data_scadenza": "Scadenza",
                "interessi_maturati_eur": "Interessi maturati (stima)",
                "interessi_scadenza_eur": "Interessi a scadenza (lordi)",
                "valore_attuale_eur": "Valore attuale",
            })[["id", "Banca", "Importo", "Tasso annuo lordo (%)", "Apertura", "Scadenza",
                "Interessi maturati (stima)", "Interessi a scadenza (lordi)", "Valore attuale"]],
            hide_index=True, width='stretch',
        )
    else:
        st.info("Nessun conto deposito registrato.")

# --- Storico valore ---------------------------------------------------------
st.divider()
st.subheader("Andamento storico del valore")
storico = portfolio.carica_storico()
if len(storico) >= 2:
    storico = storico.sort_values("data")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=storico["data"], y=storico["valore_totale"], mode="lines+markers",
        name="Valore Totale", line=dict(color=BLU_SEQ, width=2), marker=dict(size=6),
    ))
    fig.add_trace(go.Scatter(
        x=storico["data"], y=storico["valore_investito"], mode="lines",
        name="Capitale Investito (ETF/Azioni)", line=dict(color=ARANCIO_SEQ, width=2, dash="dot"),
    ))
    fig.update_layout(
        height=350, hovermode="x unified", margin=dict(l=10, r=10, t=10, b=10),
        yaxis_title="EUR", legend=dict(orientation="h", yanchor="bottom", y=-0.3),
    )
    st.plotly_chart(fig, width='stretch')
else:
    st.info("Lo storico si costruisce automaticamente ad ogni accesso: torna qui dopo qualche giorno per vedere l'andamento.")

# ===========================================================================
# Sidebar: inserimento e rimozione dati
# ===========================================================================
st.sidebar.header("Aggiungi dati")

with st.sidebar.form("form_posizione", clear_on_submit=True):
    st.subheader("ETF / Azione")
    tipo = st.selectbox("Tipo", portfolio.TIPI_POSIZIONE)
    isin = st.text_input("Codice ISIN")
    quantita = st.number_input("Quantità", min_value=0.0, step=1.0, format="%.4f")
    prezzo_acquisto = st.number_input("Prezzo di acquisto (per unità)", min_value=0.0, step=0.01, format="%.4f")
    valuta_acq = st.text_input("Valuta di acquisto", value="EUR")
    data_acquisto = st.date_input("Data di acquisto")
    note_pos = st.text_input("Note", key="note_pos")
    if st.form_submit_button("Aggiungi posizione"):
        if not isin or quantita <= 0:
            st.sidebar.error("Inserisci almeno ISIN e quantità > 0.")
        else:
            try:
                riga = portfolio.aggiungi_posizione(
                    tipo, isin, quantita, prezzo_acquisto, str(data_acquisto), valuta_acq, note_pos)
                _carica_dati.clear()
                st.sidebar.success(f"Aggiunta: {riga['nome']} ({riga['ticker']})")
                st.rerun()
            except ValueError as e:
                st.sidebar.error(str(e))

with st.sidebar.form("form_liquidita", clear_on_submit=True):
    st.subheader("Liquidità")
    descrizione = st.text_input("Descrizione (es. Conto corrente)")
    importo_liq = st.number_input("Importo", step=10.0, format="%.2f")
    valuta_liq = st.text_input("Valuta ", value="EUR")
    note_liq = st.text_input("Note ", key="note_liq")
    if st.form_submit_button("Aggiungi liquidità"):
        if not descrizione:
            st.sidebar.error("Inserisci una descrizione.")
        else:
            portfolio.aggiungi_liquidita(descrizione, importo_liq, valuta_liq, note_liq)
            _carica_dati.clear()
            st.sidebar.success("Liquidità aggiunta.")
            st.rerun()

with st.sidebar.form("form_conto_deposito", clear_on_submit=True):
    st.subheader("Conto Deposito")
    banca = st.text_input("Banca")
    importo_cd = st.number_input("Importo depositato", min_value=0.0, step=10.0, format="%.2f")
    tasso = st.number_input("Tasso annuo lordo (%)", min_value=0.0, step=0.1, format="%.2f")
    apertura = st.date_input("Data apertura", key="apertura_cd")
    scadenza = st.date_input("Data scadenza", key="scadenza_cd")
    note_cd = st.text_input("Note  ", key="note_cd")
    if st.form_submit_button("Aggiungi conto deposito"):
        if not banca:
            st.sidebar.error("Inserisci il nome della banca.")
        else:
            portfolio.aggiungi_conto_deposito(banca, importo_cd, tasso, str(apertura), str(scadenza), note_cd)
            _carica_dati.clear()
            st.sidebar.success("Conto deposito aggiunto.")
            st.rerun()

st.sidebar.divider()
st.sidebar.header("Rimuovi")
categoria_rim = st.sidebar.selectbox("Categoria", ["Posizione", "Liquidità", "Conto Deposito"])
mappa_df = {"Posizione": posizioni, "Liquidità": dati["liquidita"], "Conto Deposito": dati["conti_deposito"]}
mappa_nome = {"Posizione": "nome", "Liquidità": "descrizione", "Conto Deposito": "banca"}
mappa_rimuovi = {
    "Posizione": portfolio.rimuovi_posizione,
    "Liquidità": portfolio.rimuovi_liquidita,
    "Conto Deposito": portfolio.rimuovi_conto_deposito,
}
df_rim = mappa_df[categoria_rim]
if not df_rim.empty:
    opzioni = {f"#{r['id']} - {r[mappa_nome[categoria_rim]]}": r["id"] for _, r in df_rim.iterrows()}
    scelta = st.sidebar.selectbox("Elemento", list(opzioni.keys()))
    if st.sidebar.button("🗑️ Rimuovi selezionato"):
        mappa_rimuovi[categoria_rim](opzioni[scelta])
        _carica_dati.clear()
        st.sidebar.success("Rimosso.")
        st.rerun()
else:
    st.sidebar.caption("Nessun elemento da rimuovere in questa categoria.")
