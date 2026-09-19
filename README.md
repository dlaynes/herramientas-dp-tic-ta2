# Base UTP Assistant con NVIDIA

Este directorio contiene la base de código relacionada con la aplicación UTP_Assistant Usa el endpoint de Chat Completions compatible de NVIDIA y function calling.

## Estructura

```text
base/
├─ app.py                # App Streamlit
├─ utp_assistant.py      # Conexión NVIDIA, prompt, tools y ciclo de herramientas
├─ requirements.txt
├─ .env.example
└─ .editorconfig
```

## Instalación

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Configurar la clave

```powershell
Copy-Item .env.example .env
notepad .env
```

Contenido mínimo:

```env
NVIDIA_API_KEY=tu_clave_de_nvidia
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=z-ai/glm-5.3-flash
NVIDIA_TIMEOUT_SECONDS=120
```

La primera conexión a NVIDIA puede tardar hasta un minuto. El código usa un timeout de 120 segundos por defecto para evitar bloqueos indefinidos. Si desea reutilizar localmente la clave ya configurada en el ejemplo de la semana 6, puede copiar ese archivo `.env` a esta carpeta. No lo suba al repositorio.

## Ejecutar

```powershell
python -m streamlit run app.py
```

## Notas de seguridad

- `.env` está excluido en `.gitignore`.
- Las funciones de Jira, Google Calendar y CRM son simuladas.
- Para producción, reemplace `TOOL_REGISTRY` por clientes reales con permisos mínimos, control humano y auditoría.
