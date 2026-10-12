import streamlit as st
from datetime import date, datetime, timedelta
from PIL import Image
import json
import os
import random
import string

DB_FILE = "database_hogares.json"

def cargar_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def guardar_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

st.set_page_config(page_title="Gestor de Tareas y Créditos - Multihogar", page_icon="🧹", layout="wide")

db = cargar_db()

# Inicializar estado de sesión para el acceso
if "codigo_activo" not in st.session_state:
    st.session_state.codigo_activo = None
if "usuario_activo" not in st.session_state:
    st.session_state.usuario_activo = None
if "es_lider" not in st.session_state:
    st.session_state.es_lider = False

# --- PANTALLA DE ACCESO / LOGIN ---
if not st.session_state.codigo_activo:
    st.title("🧹 Gestor de Tareas y Créditos por Hogares")
    st.markdown("Bienvenido. Puedes **crear un nuevo hogar** (si eres líder) o **unirte a un hogar existente** usando el código de acceso.")
    
    tab_crear, tab_unirse = st.tabs(["🏠 Crear Hogar (Líder)", "🔑 Unirse a un Hogar (Miembro / Líder)"])
    
    with tab_crear:
        st.subheader("Crear un Nuevo Hogar")
        with st.form("form_crear_hogar"):
            nombre_hogar = st.text_input("Nombre del Hogar (ej. Casa Principal)")
            nombre_lider = st.text_input("Tu Nombre (Líder)")
            
            modo_juego = st.selectbox("Modo de Juego", ["Normal", "Modo Difícil ⏱️"])
            meta_dificil = 0
            if modo_juego == "Modo Difícil ⏱️":
                st.info("⚠️ **Modo Difícil:** Tendrás una meta de créditos que el hogar debe alcanzar en los primeros 5 días de cada ciclo. Si no se logra, no se podrán pedir permisos. Además, los créditos se reiniciarán a 0 automáticamente cada 7 días.")
                meta_dificil = st.number_input("Meta de créditos a alcanzar en 5 días", min_value=10, max_value=1000, value=50, step=10)
            
            crear_btn = st.form_submit_button("Crear Hogar")
            
            if crear_btn:
                if not nombre_hogar or not nombre_lider:
                    st.error("Por favor completa todos los campos.")
                else:
                    codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    while codigo in db:
                        codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    
                    db[codigo] = {
                        "nombre": nombre_hogar,
                        "lider": nombre_lider,
                        "credits": {nombre_lider: 0},
                        "tasks": [],
                        "permits": [],
                        "modo_dificil": (modo_juego == "Modo Difícil ⏱️"),
                        "meta_dificil": meta_dificil,
                        "fecha_inicio": str(date.today()),
                        "ciclo_actual": 0,
                        "meta_cumplida": False
                    }
                    guardar_db(db)
                    st.success(f"¡Hogar creado con éxito! Tu código de acceso permanente es: **{codigo}**")
                    st.info("Comparte este código con los miembros de tu hogar. Ya puedes iniciar sesión con él.")
    
    with tab_unirse:
        st.subheader("Entrar a un Hogar Existente")
        with st.form("form_unirse_hogar"):
            codigo_ingresado = st.text_input("Código del Hogar").strip().upper()
            nombre_usuario = st.text_input("Tu Nombre de Usuario").strip()
            es_lider_checkbox = st.checkbox("¿Entrar como el Líder de este hogar?")
            entrar_btn = st.form_submit_button("Entrar al Hogar")
            
            if entrar_btn:
                if not codigo_ingresado or not nombre_usuario:
                    st.error("Debes ingresar el código y tu nombre de usuario.")
                elif codigo_ingresado not in db:
                    st.error("El código de hogar ingresado no existe o fue eliminado.")
                else:
                    hogar = db[codigo_ingresado]
                    if es_lider_checkbox:
                        if nombre_usuario != hogar["lider"]:
                            st.error(f"El líder registrado de este hogar es '{hogar['lider']}'. Verifica tu nombre.")
                        else:
                            st.session_state.codigo_activo = codigo_ingresado
                            st.session_state.usuario_activo = nombre_usuario
                            st.session_state.es_lider = True
                            st.rerun()
                    else:
                        st.session_state.codigo_activo = codigo_ingresado
                        st.session_state.usuario_activo = nombre_usuario
                        st.session_state.es_lider = False
                        if nombre_usuario not in hogar["credits"]:
                            hogar["credits"][nombre_usuario] = 0
                            guardar_db(db)
                        st.rerun()
    st.stop()

# --- ZONA DE USUARIO DENTRO DEL HOGAR ---
codigo_actual = st.session_state.codigo_activo
usuario_actual = st.session_state.usuario_activo
es_lider = st.session_state.es_lider

db = cargar_db()
if codigo_actual not in db:
    st.error("Este hogar ha sido eliminado por el líder.")
    if st.button("Volver al inicio"):
        st.session_state.codigo_activo = None
        st.session_state.usuario_activo = None
        st.rerun()
    st.stop()

hogar_data = db[codigo_actual]

# --- LÓGICA DE MODO DIFÍCIL ---
permisos_bloqueados_por_dificil = False
if hogar_data.get("modo_dificil", False):
    hoy = date.today()
    fecha_ini = date.fromisoformat(hogar_data["fecha_inicio"])
    dias_totales = (hoy - fecha_ini).days
    ciclo_actual = dias_totales // 7
    dias_en_ciclo = dias_totales % 7 # 0 a 6 (Días 0,1,2,3,4 = primeros 5 días)
    
    if "ciclo_actual" not in hogar_data:
        hogar_data["ciclo_actual"] = 0
        hogar_data["meta_cumplida"] = False
        guardar_db(db)
        
    # Si pasaron 7 días, reiniciamos créditos a 0 y avanzamos ciclo
    if ciclo_actual > hogar_data["ciclo_actual"]:
        for m in hogar_data["credits"]:
            hogar_data["credits"][m] = 0
        hogar_data["ciclo_actual"] = ciclo_actual
        hogar_data["meta_cumplida"] = False
        guardar_db(db)
        
    # Evaluar si en los primeros 5 días se cumplió la meta de créditos sumados
    suma_creditos = sum(hogar_data["credits"].values())
    if dias_en_ciclo < 5:
        if suma_creditos >= hogar_data["meta_dificil"]:
            hogar_data["meta_cumplida"] = True
            guardar_db(db)
    else:
        # Si ya pasaron los primeros 5 días y no se cumplió la meta, bloquear permisos
        if not hogar_data.get("meta_cumplida", False):
            permisos_bloqueados_por_dificil = True

# Barra lateral
st.sidebar.title(f"🏠 {hogar_data['nombre']}")
st.sidebar.markdown(f"**Código de acceso:** `{codigo_actual}`")
if hogar_data.get("modo_dificil", False):
    st.sidebar.error("🔥 **MODO DIFÍCIL ACTIVO**")
    st.sidebar.write(f"Meta 5 días: **{hogar_data['meta_dificil']} 🪙**")
    st.sidebar.write(f"Día del ciclo (7 días): **{(dias_totales % 7) + 1}/7**")
    if hogar_data.get("meta_cumplida", False):
        st.sidebar.success("✅ ¡Meta de 5 días cumplida!")
    else:
        if dias_en_ciclo < 5:
            st.sidebar.warning(f"⏳ Faltan {5 - dias_en_ciclo} días para cumplir la meta.")
        else:
            st.sidebar.error("❌ Meta no cumplida: Permisos bloqueados.")

st.sidebar.markdown(f"👤 **Usuario:** {usuario_actual} ({'Líder 👑' if es_lider else 'Miembro'})")

if st.sidebar.button("🚪 Salir del Hogar"):
    st.session_state.codigo_activo = None
    st.session_state.usuario_activo = None
    st.session_state.es_lider = False
    st.rerun()

if es_lider:
    if st.sidebar.button("🗑️ Eliminar Hogar (Permanente)", type="primary"):
        del db[codigo_actual]
        guardar_db(db)
        st.sidebar.success("Hogar eliminado.")
        st.session_state.codigo_activo = None
        st.session_state.usuario_activo = None
        st.session_state.es_lider = False
        st.rerun()

st.sidebar.markdown("---")
rol_actual = "Líder" if es_lider else "Miembro"

if rol_actual == "Miembro":
    if usuario_actual not in hogar_data["credits"]:
        hogar_data["credits"][usuario_actual] = 0
        guardar_db(db)
    st.sidebar.markdown(f"### Tus Créditos: **{hogar_data['credits'][usuario_actual]} 🪙**")

# --- VISTA DE LÍDER ---
if rol_actual == "Líder":
    st.title(f"👑 Panel del Líder - {hogar_data['nombre']}")
    
    tab1, tab2, tab3 = st.tabs(["Crear Tareas", "Revisar Evidencias", "Gestionar Permisos"])
    
    with tab1:
        st.subheader("Asignar Nueva Tarea")
        miembros_disponibles = list(hogar_data["credits"].keys())
        if not miembros_disponibles:
            st.warning("Aún no hay miembros unidos a este hogar.")
        else:
            with st.form("form_tarea"):
                titulo_tarea = st.text_input("Descripción de la tarea (ej. Limpiar cocina)")
                asignado = st.selectbox("Asignar a:", miembros_disponibles)
                recompensa = st.number_input("Créditos de recompensa / multa", min_value=5, max_value=100, value=10, step=5)
                submitted = st.form_submit_button("Crear Tarea")
                
                if submitted and titulo_tarea:
                    nueva_id = len(hogar_data["tasks"]) + 1
                    hogar_data["tasks"].append({
                        "id": nueva_id,
                        "title": titulo_tarea,
                        "assigned_to": asignado,
                        "status": "Pendiente",
                        "reward": recompensa,
                        "image": None
                    })
                    guardar_db(db)
                    st.success(f"¡Tarea creada y asignada a {asignado}!")
                    st.rerun()

    with tab2:
        st.subheader("Revisar Tareas Completadas (Evidencia Fotográfica)")
        pendientes_revision = [t for t in hogar_data["tasks"] if t["status"] == "En Revisión"]
        
        if not pendientes_revision:
            st.info("No hay tareas pendientes de revisión en este momento.")
        else:
            for tarea in pendientes_revision:
                with st.expander(f"Tarea: {tarea['title']} (Asignado a: {tarea['assigned_to']})"):
                    st.write(f"Recompensa: **{tarea['reward']} créditos**")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"✅ Aprobar (ID {tarea['id']})", key=f"aprob_{tarea['id']}"):
                            tarea["status"] = "Completada"
                            hogar_data["credits"][tarea["assigned_to"]] += tarea["reward"]
                            guardar_db(db)
                            st.success(f"¡Tarea aprobada! Se sumaron {tarea['reward']} créditos a {tarea['assigned_to']}.")
                            st.rerun()
                    with col2:
                        if st.button(f"❌ Rechazar (ID {tarea['id']})", key=f"rech_{tarea['id']}"):
                            tarea["status"] = "Rechazada"
                            hogar_data["credits"][tarea["assigned_to"]] = max(0, hogar_data["credits"][tarea["assigned_to"]] - int(tarea["reward"]/2))
                            guardar_db(db)
                            st.warning("Tarea rechazada. Se aplicó penalización de créditos.")
                            st.rerun()

    with tab3:
        st.subheader("Solicitudes de Permisos de los Miembros")
        if permisos_bloqueados_por_dificil:
            st.error("🚫 **Permisos bloqueados:** En Modo Difícil no se alcanzó la meta de créditos en los primeros 5 días de este ciclo. No se pueden aprobar permisos hasta el próximo reinicio semanal.")
        else:
            if not hogar_data["permits"]:
                st.info("No hay solicitudes de permisos pendientes.")
            else:
                for idx, p in enumerate(hogar_data["permits"]):
                    if p["status"] == "Pendiente":
                        st.write(f"👤 **{p['member']}** solicita permiso para el **{p['date']}** por un costo de **{p['cost']} créditos**.")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Aprobar Permiso", key=f"perm_aprob_{idx}"):
                                p["status"] = "Aprobado"
                                guardar_db(db)
                                st.success("¡Permiso aprobado con éxito!")
                                st.rerun()
                        with col2:
                            if st.button("Rechazar Permiso", key=f"perm_rech_{idx}"):
                                p["status"] = "Rechazada"
                                hogar_data["credits"][p["member"]] += p["cost"]
                                guardar_db(db)
                                st.info("Permiso rechazado. Se devolvieron los créditos al miembro.")
                                st.rerun()

# --- VISTA DE MIEMBRO ---
else:
    st.title(f"👋 Bienvenido, {usuario_actual}")
    
    tab_mis_tareas, tab_calendario = st.tabs(["Mis Tareas", "Calendario de Permisos"])
    
    with tab_mis_tareas:
        st.subheader("Tareas Asignadas")
        mis_tareas = [t for t in hogar_data["tasks"] if t["assigned_to"] == usuario_actual]
        
        if not mis_tareas:
            st.info("¡No tienes tareas asignadas por ahora!")
        else:
            for tarea in mis_tareas:
                st.markdown(f"---")
                st.write(f"📌 **{tarea['title']}**")
                st.write(f"Recompensa: {tarea['reward']} 🪙 | Estado: **{tarea['status']}**")
                
                if tarea["status"] in ["Pendiente", "Rechazada"]:
                    foto_subida = st.file_uploader(f"Sube foto de evidencia para la tarea {tarea['id']}", type=["jpg", "png", "jpeg"], key=f"file_{tarea['id']}")
                    if foto_subida:
                        img = Image.open(foto_subida)
                        st.image(img, caption="Vista previa de tu evidencia", width=200)
                        if st.button(f"Enviar Evidencia (Tarea {tarea['id']})", key=f"enviar_{tarea['id']}"):
                            tarea["status"] = "En Revisión"
                            guardar_db(db)
                            st.success("¡Evidencia enviada al líder para su revisión!")
                            st.rerun()
                elif tarea["status"] == "En Revisión":
                    st.info("⏳ Tu evidencia está siendo evaluada por el líder.")
                elif tarea["status"] == "Completada":
                    st.success("🎉 ¡Tarea completada y aprobada!")

    with tab_calendario:
        st.subheader("🗓️ Solicitar Permisos usando Créditos")
        st.write(f"Tus créditos disponibles: **{hogar_data['credits'][usuario_actual]} 🪙**")
        
        if permisos_bloqueados_por_dificil:
            st.error("🚫 **Permisos bloqueados en Modo Difícil:** El hogar no alcanzó la meta de créditos establecida en los primeros 5 días de este ciclo. No es posible solicitar nuevos permisos hasta el próximo reinicio de créditos.")
        else:
            with st.form("form_permiso"):
                fecha_tentativa = st.date_input("Fecha deseada", min_value=date.today())
                costo_creditos = st.number_input("Créditos a ofertar por el permiso", min_value=5, max_value=100, value=20, step=5)
                enviar_permiso = st.form_submit_button("Solicitar Permiso")
                
                if enviar_permiso:
                    if hogar_data["credits"][usuario_actual] >= costo_creditos:
                        hogar_data["credits"][usuario_actual] -= costo_creditos
                        hogar_data["permits"].append({
                            "member": usuario_actual,
                            "date": str(fecha_tentativa),
                            "cost": costo_creditos,
                            "status": "Pendiente"
                        })
                        guardar_db(db)
                        st.success("¡Solicitud enviada al líder! Se han descontado los créditos temporalmente.")
                        st.rerun()
                    else:
                        st.error("No tienes suficientes créditos para solicitar este permiso.")
        
        st.markdown("### Historial de tus Permisos")
        mis_permisos = [p for p in hogar_data["permits"] if p["member"] == usuario_actual]
        if not mis_permisos:
            st.info("No has solicitado permisos aún.")
        else:
            for p in mis_permisos:
                st.write(f"- Fecha: **{p['date']}** | Costo: **{p['cost']} créditos** | Estado: **{p['status']}**")
