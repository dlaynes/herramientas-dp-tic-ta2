from __future__ import annotations

"""Demo Streamlit app for UTP Assistant with NVIDIA Chat Completions."""

import json
import os

import streamlit as st
from dotenv import load_dotenv

from utp_assistant import build_client, get_model_name, process_email

load_dotenv()

st.set_page_config(page_title="UTP Assistant — NVIDIA", page_icon="🧭")
st.title("🧭 UTP Assistant")
st.caption("Asistente de correos con NVIDIA Chat Completions compatible con OpenAI")

if not os.getenv("NVIDIA_API_KEY"):
    st.error("No se encontró la variable NVIDIA_API_KEY en el archivo .env.")
    st.info("Crea el archivo .env con la línea: NVIDIA_API_KEY=tu_clave_de_nvidia")
    st.stop()

st.sidebar.header("Configuración")
st.sidebar.write(f"Endpoint: {os.getenv('NVIDIA_BASE_URL', 'https://integrate.api.nvidia.com/v1')}")
st.sidebar.write(f"Modelo: {get_model_name()}")
st.sidebar.caption("Las herramientas Jira, Calendar y CRM se ejecutan de forma simulada.")

with st.form("correo_entrante"):
    st.subheader("Correo entrante")
    sender = st.text_input("Remitente", "Luisa Torres <ltorres@techcorp.com>")
    subject = st.text_input("Asunto", "Propuesta — módulo de pagos")
    email_text = st.text_area(
        "Cuerpo del correo",
        "Hola equipo de UTP Consult, gracias por la propuesta. Nos interesa avanzar. "
        "¿Podríamos tener una reunión la próxima semana para discutir los detalles técnicos "
        "del módulo de pagos? Adjunto un documento con algunos requisitos iniciales. "
        "Saludos, Luisa Torres de TechCorp.",
        height=180,
    )
    attachment_text = st.text_area(
        "Texto extraído de adjuntos (opcional)",
        "Requisitos iniciales: integración con pasarela de pagos, revisión de seguridad y entrega estimada de 8 semanas.",
        height=120,
    )
    submitted = st.form_submit_button("Procesar correo", type="primary")

if submitted:
    if not email_text.strip():
        st.error("El cuerpo del correo es obligatorio.")
    else:
        try:
            with st.spinner("Consultando a NVIDIA y ejecutando herramientas..."):
                client = build_client()
                result = process_email(
                    email_text,
                    sender=sender,
                    subject=subject,
                    attachment_text=attachment_text,
                    client=client,
                )
            st.session_state["last_result"] = result
        except Exception as exc:
            st.error(f"No se pudo procesar el correo: {exc}")

result = st.session_state.get("last_result")
if result:
    st.subheader("Respuesta final")
    st.markdown(result.get("final_message", "(sin respuesta)"))
    st.subheader("Acciones propuestas o simuladas")
    actions = result.get("actions", [])
    if actions:
        for action in actions:
            with st.expander(f"{action['status'].upper()} — {action['tool']}"):
                st.json(action, expanded=True)
    else:
        st.info("El modelo no solicitó llamadas a herramientas.")
    st.download_button(
        "Descargar auditoría JSON",
        data=json.dumps(result, ensure_ascii=False, indent=2),
        file_name="utp_assistant_auditoria.json",
        mime="application/json",
        use_container_width=True,
    )
