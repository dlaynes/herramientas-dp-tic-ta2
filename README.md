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

## Instalación en Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip (Paso opcional)
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
NVIDIA_MODEL=openai/gpt-oss-20b
NVIDIA_TIMEOUT_SECONDS=240
```

La primera conexión a NVIDIA puede tardar hasta un minuto. El código usa un timeout de 240 segundos por defecto para evitar bloqueos indefinidos. Si desea reutilizar localmente una clave ya configurada puede copiar los datos del archivo `.env` al archivo correspondiente del proyecto. No lo suba a otros archivos del repositorio.

## Ejecutar

```powershell
python -m streamlit run app.py
```

## Notas de seguridad

- `.env` está excluido en `.gitignore`.
- Las funciones de Jira, Google Calendar y CRM son simuladas. En Producción, reemplace las herramientas indicadas en la variable `TOOL_REGISTRY` por clientes reales con permisos mínimos, control humano y auditoría.
