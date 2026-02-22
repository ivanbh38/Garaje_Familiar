import streamlit as st
import pandas as pd
from datetime import datetime, time
import os
import json
import pytz

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Garajes Pontika/Beraun", page_icon="🅿️", layout="wide")
TZ_MADRID = pytz.timezone('Europe/Madrid')
RELACION = {"Furgoneta": "Pontika Furgoneta", "Zafira": "Beraun", "Astra": "Pontika Astra"}
ARCHIVO_DB = 'reservas.csv'
ARCHIVO_ESTADO = 'estado_actual.json'

def obtener_hora_madrid():
    return datetime.now(TZ_MADRID).replace(tzinfo=None)

def cargar_estado():
    if os.path.exists(ARCHIVO_ESTADO):
        with open(ARCHIVO_ESTADO, 'r') as f:
            return json.load(f)
    return {c: {"en_calle": False, "ubicacion": ""} for c in RELACION.keys()}

def guardar_estado(estado):
    with open(ARCHIVO_ESTADO, 'w') as f:
        json.dump(estado, f)

def cargar_reservas():
    if os.path.exists(ARCHIVO_DB):
        df = pd.read_csv(ARCHIVO_DB)
        df['Inicio'] = pd.to_datetime(df['Inicio'])
        df['Fin'] = pd.to_datetime(df['Fin'])
        return df
    return pd.DataFrame(columns=["Coche", "Usuario", "Inicio", "Fin", "Llegado"])

def guardar_reservas(df):
    df.to_csv(ARCHIVO_DB, index=False)

df = cargar_reservas()
estado = cargar_estado()
ahora = obtener_hora_madrid()

# --- DIÁLOGO MODAL ---
@st.dialog("¿Dónde está el coche?")
def modal_fuera(idx, coche_id):
    st.write(f"Confirmar que la **{coche_id}** se queda en la calle.")
    ubi = st.text_input("Ubicación exacta:", placeholder="Ej: En el frontón")
    if st.button("Confirmar y Finalizar"):
        if ubi.strip():
            df.at[idx, 'Llegado'] = True
            guardar_reservas(df)
            estado[coche_id] = {"en_calle": True, "ubicacion": ubi.strip()}
            guardar_estado(estado)
            st.rerun()
        else:
            st.error("Escribe la calle.")

# --- 1. CABECERA ---
st.title("🅿️ Panel de Control v1.2.2")

# --- 2. ESTADO DE GARAJES ---
st.subheader("Estado de los Garajes")
cols = st.columns(3)

for i, (c_id, nombre_garaje) in enumerate(RELACION.items()):
    en_uso = df[(df['Coche'] == c_id) & (df['Llegado'] == False) & (df['Inicio'] <= ahora) & (df['Fin'] >= ahora)]
    est = estado.get(c_id, {"en_calle": False, "ubicacion": ""})

    with cols[i]:
        if est["en_calle"]:
            st.success(f"🟢 **{nombre_garaje}**\n\n**GARAJE LIBRE**")
            with st.container(border=True):
                st.write(f"📍 **En :** {est['ubicacion']}")
                if st.button(f"🅿️ Aparcado en Garaje", key=f"ret_{c_id}", use_container_width=True):
                    estado[c_id] = {"en_calle": False, "ubicacion": ""}
                    guardar_estado(estado)
                    st.rerun()
        elif not en_uso.empty:
            st.success(f"🟢 **{nombre_garaje}**\n\n**GARAJE LIBRE**")
            st.info(f"👤 {en_uso.iloc[0]['Usuario']} lo tiene")
        else:
            st.error(f"🔴 **{nombre_garaje}**\n\n**GARAJE OCUPADO**")
            prox = df[(df['Coche'] == c_id) & (df['Llegado'] == False) & (df['Inicio'] > ahora)].sort_values('Inicio').head(1)
            if not prox.empty:
                st.caption(f"Próxima: {prox.iloc[0]['Inicio'].strftime('%H:%M')}")

# --- 3. LLEGADAS PENDIENTES ---
pendientes = df[(df['Llegado'] == False) & (df['Inicio'] <= ahora)]
if not pendientes.empty:
    st.divider()
    st.subheader("🏁 Confirmar Llegada")
    for idx, row in pendientes.iterrows():
        with st.container(border=True):
            st.write(f"**{row['Coche']}** - {row['Usuario']}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button(f"✅ En Garaje", key=f"in_{idx}", use_container_width=True):
                    df.at[idx, 'Llegado'] = True
                    guardar_reservas(df)
                    estado[row['Coche']] = {"en_calle": False, "ubicacion": ""}
                    guardar_estado(estado)
                    st.rerun()
            with c2:
                if st.button(f"🅿️ En la Calle", key=f"out_{idx}", use_container_width=True):
                    modal_fuera(idx, row['Coche'])

# --- 4. GESTIÓN DE RESERVAS ---
st.divider()
st.subheader("📅 Reservas")

# Pestañas para organizar mejor el espacio
tab1, tab2 = st.tabs(["➕ Nueva Reserva", "🗑️ Borrar Reserva"])

with tab1:
    with st.form("form_nueva"):
        u = st.selectbox("Usuario", ["Sergio", "Sylvia", "Iván", "Maider"])
        c = st.selectbox("Coche", list(RELACION.keys()))
        f = st.date_input("Día", value=ahora.date())
        h1 = st.time_input("Inicio", value=time(9, 0))
        h2 = st.time_input("Fin", value=time(10, 0))
        if st.form_submit_button("Guardar Reserva"):
            nueva = {"Coche": c, "Usuario": u, "Inicio": datetime.combine(f, h1), "Fin": datetime.combine(f, h2), "Llegado": False}
            df = pd.concat([df, pd.DataFrame([nueva])], ignore_index=True)
            guardar_reservas(df)
            st.rerun()

with tab2:
    reservas_activas = df[df['Llegado'] == False]
    if not reservas_activas.empty:
        opciones = {f"{r['Coche']} - {r['Usuario']} ({r['Inicio'].strftime('%d/%m %H:%M')})": idx for idx, r in reservas_activas.iterrows()}
        seleccion = st.selectbox("Selecciona la reserva que quieres eliminar:", list(opciones.keys()))
        if st.button("Eliminar", type="primary"):
            df = df.drop(opciones[seleccion])
            guardar_reservas(df)
            st.success("Reserva eliminada correctamente.")
            st.rerun()
    else:
        st.info("No hay reservas pendientes para borrar.")

# --- 5. LISTADO VISUAL ---
reservas_v = df[df['Llegado'] == False].sort_values('Inicio')
if not reservas_v.empty:
    st.write("### 📝 Listado de Próximas Reservas")
    df_ver = reservas_v.copy()
    df_ver['Fecha'] = df_ver['Inicio'].dt.strftime('%d/%m')
    df_ver['Horario'] = df_ver['Inicio'].dt.strftime('%H:%M') + " a " + df_ver['Fin'].dt.strftime('%H:%M')
    st.table(df_ver[['Coche', 'Usuario', 'Fecha', 'Horario']])
