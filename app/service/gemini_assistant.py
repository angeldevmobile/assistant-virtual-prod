import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=API_KEY)

last_question = ""
is_first_question = True


def get_assistant_response(
    question: str, contexto: str = "", more_detail: bool = False
) -> str:
    """
    Asistente conversacional libre. Si se recibe un texto como contexto, responde solo en base a ese documento.
    Si no hay contexto, responde como asistente amable y conversacional.
    """
    global last_question, is_first_question

    if not contexto:
        bienvenida = ""
        if is_first_question:
            bienvenida = "¡Hola! 👋 Es un placer ayudarte. 😊\n\n"
            is_first_question = False

        prompt = (
            f"{bienvenida}"
            "Eres un asistente virtual llamado **Gurú** 😊. Sé siempre amable, usa emojis 🎉📄✅ y da respuestas breves, a menos que el usuario pida más detalle.\n\n"
            "INSTRUCCIONES:\n"
            "- Responde a cualquier consulta general de forma amigable y directa.\n"
            "- Si el usuario sube un documento, deberás limitarte a responder solo basándote en ese documento.\n\n"
            f"PREGUNTA:\n{question}\n"
        )
    else:
        # Sí hay documento cargado: usar solo ese texto como base
        if not more_detail:
            prompt = f"""
Eres un asistente virtual llamado **Gurú** 😊. Sé siempre amable, usa emojis 🎉📄✅ y da respuestas breves (máximo 3-4 líneas).

INSTRUCCIONES:
- Responde exclusivamente basándote en el contenido del documento proporcionado.
- Si la respuesta requiere más detalle, invita al usuario a consultarte: "Si deseas, puedo darte más información. ¿Quieres que te lo explique con más detalle? 🤗"
- Si no encuentras la respuesta en el documento, responde: "Lo siento, esa información no se encuentra en el documento proporcionado. 🙁"

DOCUMENTO:
\"\"\"{contexto}\"\"\"

PREGUNTA:
{question}
"""
            last_question = question
        else:
            prompt = f"""
Eres un asistente virtual llamado **Gurú** 😊. Proporciona ahora una respuesta más detallada y completa, basándote únicamente en el documento proporcionado 📄.

DOCUMENTO:
\"\"\"{contexto}\"\"\"

PREGUNTA:
{last_question}

INSTRUCCIONES:
- Ofrece una respuesta más extensa y explicativa.
- Si no encuentras la respuesta en el documento, di: "Lo siento, esa información no se encuentra en el documento proporcionado. 🙁"
"""

    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)
        print("Prompt enviado a Gemini:\n", prompt)
        print("Respuesta de Gemini:\n", response.text)
        if response.text.strip().lower() == question.strip().lower():
            return "¡Hola! Soy Gurú 😊. ¿En qué puedo ayudarte hoy?"
        return response.text
    except Exception as e:
        return f"Ocurrió un error al consultar Gemini: {e}"
