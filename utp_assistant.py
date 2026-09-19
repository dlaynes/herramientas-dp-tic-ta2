from __future__ import annotations

"""
Lógica base de UTP Assistant usando el endpoint de NVIDIA Chat Completions.
"""

import json
import os
from typing import Any, Callable

from openai import OpenAI

DEFAULT_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_NVIDIA_MODEL = "z-ai/glm-5.3-flash"

SYSTEM_PROMPT = """Eres UTP Assistant, un gestor de proyectos de IA proactivo y eficiente que trabaja para UTPConsult, una consultora de desarrollo de software. Tu misión principal es automatizar el procesamiento de correos electrónicos de clientes potenciales y existentes, extrayendo información clave y ejecutando acciones que agilicen el flujo de trabajo del equipo de gestión de proyectos y ventas.

PERSONA Y TONO:
- Eres un profesional organizado, proactivo y orientado a resultados.
- Tu tono es formal pero cercano, profesional y conciso.
- Comunicas información de manera clara y estructurada.
- Siempre buscas agregar valor anticipándote a las necesidades del equipo.

OBJETIVOS PRINCIPALES:
1. Extraer información relevante de los correos electrónicos entrantes: nombre del cliente, empresa, intereses expresados, requisitos mencionados, plazos indicados y archivos adjuntos.
2. Generar tareas o tickets en el sistema de gestión de proyectos (Jira) cuando se identifiquen entregables o acciones requeridas.
3. Agendar reuniones de seguimiento en Google Calendar cuando se mencionen fechas o se solicite una reunión.
4. Actualizar el CRM con la información de nuevos prospectos o cambios en prospectos existentes.
5. Resumir el contenido del correo y las acciones realizadas para el equipo interno.

REGLAS DE COMPORTAMIENTO:
- Si la información del correo es ambigua o incompleta para realizar una acción, no asumas datos. Indica la información faltante como acción pendiente.
- Nunca inventes datos de clientes, empresas, proyectos o contactos. Si algo no se encuentra en el correo, indícalo explícitamente.
- Para clientes conocidos, verifica en el CRM antes de crear registros duplicados.
- Los tickets en Jira deben incluir título claro, descripción con la información extraída, prioridad y etiquetas relevantes.
- Las reuniones agendadas deben incluir asunto, fecha, hora, duración estimada y participantes.
- Si un correo contiene múltiples solicitudes, procesa cada una y reporta todas las acciones realizadas.
- Cuando se adjunten documentos, usa su contenido preprocesado para extraer requisitos adicionales.

FORMATO DE RESPUESTA AL EQUIPO INTERNO:
[RESUMEN DEL CORREO]
- De: [nombre, empresa]
- Asunto: [asunto del correo]
- Fecha: [fecha]
- Contenido clave: [resumen breve]

[ACCIONES REALIZADAS]
- Ticket creado/actualizado: [referencia]
- Reunión agendada: [detalles]
- CRM actualizado: [registro]

[ACCIONES PENDIENTES]
- [Información faltante o ambigua que requiere atención humana]

SEGURIDAD Y PRIVACIDAD:
- Maneja toda la información de clientes con confidencialidad.
- No compartas datos sensibles fuera del contexto de UTPConsult.
- Registra todas las acciones realizadas para auditoría."""

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "crear_ticket_en_jira",
            "description": "Crea un nuevo ticket de tarea en Jira para seguimiento de proyectos. Se usa cuando un correo menciona requisitos, entregables o acciones que deben registrarse.",
            "parameters": {
                "type": "object",
                "properties": {
                    "proyecto": {"type": "string", "description": "Código del proyecto en Jira (ej. UTPCON, CRM, WEB)."},
                    "resumen": {"type": "string", "description": "Título conciso del ticket.", "maxLength": 200},
                    "descripcion": {"type": "string", "description": "Descripción detallada del ticket."},
                    "prioridad": {"type": "string", "enum": ["lowest", "low", "medium", "high", "highest"], "description": "Prioridad basada en el tono y urgencia del correo."},
                    "tipo": {"type": "string", "enum": ["task", "story", "bug", "subtask"], "description": "Tipo de issue en Jira."},
                    "etiquetas": {"type": "array", "items": {"type": "string"}, "description": "Etiquetas para categorizar el ticket."},
                    "cliente_origen": {"type": "string", "description": "Nombre del cliente o empresa de origen del correo."}
                },
                "required": ["proyecto", "resumen", "descripcion", "prioridad", "tipo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "agendar_reunion_en_google_calendar",
            "description": "Agenda una reunión en Google Calendar para seguimiento de proyecto o discusión técnica.",
            "parameters": {
                "type": "object",
                "properties": {
                    "titulo": {"type": "string", "description": "Título de la reunión."},
                    "fecha_inicio": {"type": "string", "format": "date-time", "description": "Fecha y hora de inicio en ISO 8601."},
                    "fecha_fin": {"type": "string", "format": "date-time", "description": "Fecha y hora de fin en ISO 8601."},
                    "descripcion": {"type": "string", "description": "Descripción y puntos a tratar."},
                    "participantes": {"type": "array", "items": {"type": "string", "format": "email"}, "description": "Correos de los participantes."},
                    "ubicacion": {"type": "string", "description": "Lugar o enlace de videoconferencia."},
                    "cliente": {"type": "string", "description": "Empresa o contacto cliente."}
                },
                "required": ["titulo", "fecha_inicio", "fecha_fin", "descripcion", "participantes"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "actualizar_contacto_en_crm",
            "description": "Crea o actualiza un contacto en el CRM con información extraída del correo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "enum": ["crear", "actualizar"], "description": "Acción a realizar en el CRM."},
                    "nombre_completo": {"type": "string", "description": "Nombre completo del contacto."},
                    "email": {"type": "string", "format": "email", "description": "Correo electrónico del contacto."},
                    "empresa": {"type": "string", "description": "Empresa del contacto."},
                    "cargo": {"type": "string", "description": "Cargo o puesto del contacto."},
                    "telefono": {"type": "string", "description": "Teléfono del contacto si está disponible."},
                    "estado_prospecto": {"type": "string", "enum": ["nuevo", "contactado", "calificado", "propuesta-enviada", "negociacion", "ganado", "perdido"], "description": "Estado del prospecto."},
                    "intereses": {"type": "array", "items": {"type": "string"}, "description": "Intereses o servicios mencionados."},
                    "notas": {"type": "string", "description": "Notas adicionales del correo."},
                    "fuente": {"type": "string", "description": "Origen del contacto."}
                },
                "required": ["accion", "nombre_completo", "email", "empresa", "estado_prospecto"]
            }
        }
    }
]

ToolFunction = Callable[..., dict[str, Any]]
ToolRegistry = dict[str, ToolFunction]


def build_client(api_key: str | None = None, base_url: str | None = None) -> OpenAI:
    """Creates an OpenAI-compatible client pointed to NVIDIA."""
    key = api_key or os.getenv("NVIDIA_API_KEY")
    if not key:
        raise RuntimeError("NVIDIA_API_KEY no está definida. Configúrala en el archivo .env.")
    provider_url = base_url or os.getenv("NVIDIA_BASE_URL", DEFAULT_NVIDIA_BASE_URL)
    timeout_seconds = float(os.getenv("NVIDIA_TIMEOUT_SECONDS", "120"))
    # La primera conexión a NVIDIA puede demorarse alrededor de 1 minuto
    return OpenAI(base_url=provider_url, api_key=key, timeout=timeout_seconds, max_retries=1)


def get_model_name() -> str:
    return os.getenv("NVIDIA_MODEL", DEFAULT_NVIDIA_MODEL)


def build_messages(
    email_text: str,
    *,
    sender: str = "Desconocido",
    subject: str = "Sin asunto",
    attachment_text: str = "",
) -> list[dict[str, Any]]:
    """Construye una conversación local basada en el correo que ingresa."""
    attachments = attachment_text.strip() or "(sin adjuntos)"
    user_content = (
        f"DE: {sender}\n"
        f"ASUNTO: {subject}\n\n"
        "CORREO:\n"
        f"{email_text.strip()}\n\n"
        "CONTENIDO PREPROCESADO DE ADJUNTOS:\n"
        f"{attachments}\n\n"
        "Instrucción: Procesa el correo, extrae los datos y usa las herramientas necesarias. "
        "Si falta información obligatoria, no la inventes: inclúyela en ACCIONES PENDIENTES."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def validate_tool_schemas() -> None:
    """Revisa si las herramientas están correctamente definidas en formato JSON."""
    for tool in TOOLS:
        json.dumps(tool, ensure_ascii=False)


def parse_tool_arguments(tool_call: Any) -> dict[str, Any]:
    raw = tool_call.function.arguments
    if isinstance(raw, dict):
        return raw
    return json.loads(raw or "{}")


def execute_tool_call(tool_call: Any, registry: ToolRegistry) -> dict[str, Any]:
    name = tool_call.function.name
    if name not in registry:
        return {
            "status": "error",
            "tool": name,
            "message": "La herramienta solicitada no está registrada.",
        }
    try:
        args = parse_tool_arguments(tool_call)
        result = registry[name](**args)
        return {"status": "ok", "tool": name, "arguments": args, "result": result}
    except json.JSONDecodeError as exc:
        return {"status": "error", "tool": name, "message": f"Argumentos JSON inválidos: {exc}"}
    except TypeError as exc:
        return {"status": "error", "tool": name, "message": f"Argumentos inválidos: {exc}"}
    except Exception as exc:
        return {"status": "error", "tool": name, "message": str(exc)}


# Ejemplos de uso a ser reemplazados por interacciones reales
def crear_ticket_en_jira(proyecto: str, resumen: str, descripcion: str, prioridad: str, tipo: str, **extra: Any) -> dict[str, Any]:
    return {
        "sistema": "Jira",
        "accion": "ticket_creado",
        "clave": "WEB-1847",
        "proyecto": proyecto,
        "resumen": resumen,
        "prioridad": prioridad,
        "tipo": tipo,
        "detalles": descripcion,
        "extra": extra,
    }


def agendar_reunion_en_google_calendar(titulo: str, fecha_inicio: str, fecha_fin: str, descripcion: str, participantes: list[str], **extra: Any) -> dict[str, Any]:
    return {
        "sistema": "Google Calendar",
        "accion": "reunion_agendada",
        "event_id": "evt_9a8b7c",
        "titulo": titulo,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "descripcion": descripcion,
        "participantes": participantes,
        "extra": extra,
    }


def actualizar_contacto_en_crm(accion: str, nombre_completo: str, email: str, empresa: str, estado_prospecto: str, **extra: Any) -> dict[str, Any]:
    return {
        "sistema": "CRM",
        "accion": f"contacto_{accion}",
        "contacto_id": "CRM-4821",
        "nombre_completo": nombre_completo,
        "email": email,
        "empresa": empresa,
        "estado_prospecto": estado_prospecto,
        "extra": extra,
    }


TOOL_REGISTRY: ToolRegistry = {
    "crear_ticket_en_jira": crear_ticket_en_jira,
    "agendar_reunion_en_google_calendar": agendar_reunion_en_google_calendar,
    "actualizar_contacto_en_crm": actualizar_contacto_en_crm,
}


def process_email(
    email_text: str,
    *,
    sender: str = "Desconocido",
    subject: str = "Sin asunto",
    attachment_text: str = "",
    client: OpenAI | None = None,
    registry: ToolRegistry | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    validate_tool_schemas()
    provider_client = client or build_client()
    selected_model = model or get_model_name()
    active_registry = registry or TOOL_REGISTRY
    messages = build_messages(email_text, sender=sender, subject=subject, attachment_text=attachment_text)

    first_response = provider_client.chat.completions.create(
        model=selected_model,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        temperature=0.2,
        max_tokens=2048,
    )
    first_choice = first_response.choices[0]
    first_message = first_choice.message
    tool_calls = getattr(first_message, "tool_calls", None)

    if not tool_calls:
        return {
            "model": selected_model,
            "finish_reason": first_choice.finish_reason,
            "final_message": first_message.content or "",
            "actions": [],
            "messages": messages,
        }

    messages.append(
        {
            "role": "assistant",
            "content": first_message.content,
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in tool_calls
            ],
        }
    )

    actions = [execute_tool_call(tool_call, active_registry) for tool_call in tool_calls]
    for tool_call, action in zip(tool_calls, actions, strict=True):
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(action, ensure_ascii=False),
            }
        )

    second_response = provider_client.chat.completions.create(
        model=selected_model,
        messages=messages,
        temperature=0.2,
        max_tokens=2048,
    )
    second_choice = second_response.choices[0]
    return {
        "model": selected_model,
        "finish_reason": second_choice.finish_reason,
        "final_message": second_choice.message.content or "",
        "actions": actions,
        "messages": messages,
    }
