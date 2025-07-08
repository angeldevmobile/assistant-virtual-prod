import base64
import os
from flask import Blueprint, request, jsonify, send_file
from app.database import SessionLocal
from app.models.notifications import NotificationSettings
from app.models.usuarios import Usuario
from app.models.documentos import Documento
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from app.service.gemini_assistant import get_assistant_response
from app.service.interaccion_save import guardar_interaccion
from app.service.sheets_service import buscar_coincidencias
from app.service.update_campos import actualizar_documento_campos
from app.service.process_document import procesar_documento_ocr
from datetime import datetime
import io
import re

from google.cloud import speech
import tempfile
from google.cloud import texttospeech
import colorama
from colorama import Fore, Style

colorama.init(autoreset=True)

from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/registro-usuario", methods=["POST"])
def register_user():
    db = SessionLocal()
    data = request.get_json()

    nombre = data.get("nombre")
    email = data.get("email")
    telefono = data.get("telefono")
    password = data.get("password")

    if not nombre or not email or not password:
        print(Fore.RED + "Faltan campos obligatorios en registro" + Style.RESET_ALL)
        return jsonify({"error": "Faltan campos obligatorios"}), 400

    usuario = Usuario(
        nombre=nombre,
        email=email,
        telefono=telefono,
        password_hash=generate_password_hash(password),
    )

    try:
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
    except IntegrityError:
        db.rollback()
        print(Fore.RED + "Email ya registrado: " + email + Style.RESET_ALL)
        return jsonify({"detail": "Email ya registrado"}), 400
    finally:
        db.close()

    print(Fore.GREEN + f"Usuario registrado: {email}" + Style.RESET_ALL)
    return jsonify(
        {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "telefono": usuario.telefono,
            "rol": usuario.rol,
        }
    )


@auth_bp.route("/login", methods=["POST"])
def login_user():
    db = SessionLocal()
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        print(Fore.RED + "Faltan campos obligatorios en login" + Style.RESET_ALL)
        return jsonify({"error": "Faltan campos obligatorios"}), 400

    usuario = db.query(Usuario).filter_by(email=email).first()
    db.close()

    if usuario and check_password_hash(usuario.password_hash, password):
        print(Fore.GREEN + f"Login exitoso: {email}" + Style.RESET_ALL)
        access_token = create_access_token(identity=email)
        return jsonify(
            {
                "access_token": access_token,
                "id": usuario.id,
                "nombre": usuario.nombre,
                "email": usuario.email,
                "telefono": usuario.telefono,
                "rol": usuario.rol,
            }
        )
    else:
        print(Fore.RED + f"Login fallido: {email}" + Style.RESET_ALL)
        return jsonify({"detail": "Credenciales incorrectas"}), 401


@auth_bp.route("/assistant", methods=["POST"])
def assistant_chat():
    data = request.get_json()
    question = data.get("question")
    user_email = data.get("user_email")
    document_id = data.get("document_id")

    if not question:
        return jsonify({"error": "La pregunta es obligatoria"}), 400

    db = SessionLocal()
    usuario = db.query(Usuario).filter_by(email=user_email).first() if user_email else None
    id_usuario = usuario.id if usuario else None

    contexto = ""
    doc_id_usado = None

    # Si no se especifica document_id, buscar en todos los documentos del usuario
    if not document_id and usuario:
        documentos = db.query(Documento).filter_by(id_usuario=usuario.id).all()
        mejor_doc = None
        mejor_score = 0
        for doc in documentos:
            if doc.texto_extraido:
                # Simple: contar ocurrencias de palabras de la pregunta en el texto
                score = sum(1 for palabra in question.lower().split() if palabra in doc.texto_extraido.lower())
                if score > mejor_score:
                    mejor_score = score
                    mejor_doc = doc
        if mejor_doc and mejor_score > 0:
            contexto = mejor_doc.texto_extraido
            doc_id_usado = mejor_doc.id
    elif document_id:
        documento = db.query(Documento).filter_by(id=document_id).first()
        if documento and documento.texto_extraido:
            contexto = documento.texto_extraido
            doc_id_usado = documento.id

    db.close()

    respuesta = get_assistant_response(question, contexto=contexto)

    guardar_interaccion(
        pregunta=question,
        respuesta=respuesta,
        documento_id=doc_id_usado,
        id_usuario=id_usuario,
    )

    return jsonify({"respuesta": respuesta}), 200


@auth_bp.route("/upload_document", methods=["POST"])
def upload_document():
    db = SessionLocal()
    file = request.files.get("file")
    user_email = request.form.get("user_email")

    if not file or not user_email:
        db.close()
        return jsonify({"error": "Falta archivo o email"}), 400

    usuario = db.query(Usuario).filter_by(email=user_email).first()
    if not usuario:
        db.close()
        return jsonify({"error": "Usuario no encontrado"}), 404

    archivo_binario = file.read()
    mimetype = file.mimetype or "application/pdf"

    # Procesar documento usando los bytes leídos y su MIME type
    resultado = procesar_documento_ocr(archivo_binario, mimetype)
    texto_extraido = resultado.get("texto", "")
    campos_extraidos = resultado.get("campos", {})

    # Guardar en la base de datos, incluyendo el texto extraído
    documento = Documento(
        nombre=file.filename,
        fecha=datetime.now(),
        validado=False,
        ruta="",
        campos_json=None,
        texto_extraido=texto_extraido,
        id_usuario=usuario.id,
        archivo=archivo_binario,
    )
    db.add(documento)
    db.commit()
    db.refresh(documento)
    documento_id = documento.id

    # Actualizar campos extraídos en el documento
    actualizar_documento_campos(documento_id, campos_extraidos)

    db.close()
    return jsonify({"success": True, "document_id": documento_id})


@auth_bp.route("/validar-documento-sheets", methods=["POST"])
def validar_documento_sheets():
    data = request.get_json()
    document_id = data.get("document_id")
    sheet_id = data.get("sheet_id")  # ID del Google Sheet

    if not document_id or not sheet_id:
        return jsonify({"error": "Se requiere ID de documento y de hoja"}), 400

    db = SessionLocal()
    doc = db.query(Documento).filter_by(id=document_id).first()
    db.close()

    if not doc or not doc.campos_json:
        return jsonify({"error": "Documento no encontrado o sin campos extraídos"}), 404

    import json

    campos = json.loads(doc.campos_json)
    resultado = buscar_coincidencias(sheet_id, campos)

    if isinstance(resultado, dict) and "error" in resultado:
        return jsonify({"error": resultado["error"]}), 500

    return jsonify({"coincidencias": resultado}), 200


@auth_bp.route("/listar_documentos", methods=["GET"])
def listar_documentos_endpoint():
    user_email = request.args.get("user_email")
    db = SessionLocal()
    usuario = db.query(Usuario).filter_by(email=user_email).first()
    if not usuario:
        db.close()
        return jsonify({"error": "Usuario no encontrado"}), 404
    documentos = (
        db.query(Documento)
        .filter_by(id_usuario=usuario.id)
        .order_by(Documento.fecha.desc())
        .all()
    )
    db.close()
    docs_list = []
    for doc in documentos:
        docs_list.append(
            {
                "id": doc.id,
                "name": doc.nombre,
                "uploadDate": doc.fecha.isoformat(),
                "type": "pdf" if doc.nombre.lower().endswith(".pdf") else "image",
                "status": "validado" if doc.validado else "cargado",
                "size": f"{round(len(doc.archivo)/1024, 2)} KB",
            }
        )
    return jsonify(docs_list)


@auth_bp.route("/document/<int:doc_id>", methods=["GET"])
def get_document(doc_id):
    user_email = request.args.get("user_email")
    db = SessionLocal()
    usuario = db.query(Usuario).filter_by(email=user_email).first()
    documento = db.query(Documento).filter_by(id=doc_id, id_usuario=usuario.id).first()
    db.close()
    if not documento:
        return jsonify({"error": "Documento no encontrado"}), 404
    mimetype = (
        "application/pdf" if documento.nombre.lower().endswith(".pdf") else "image/*"
    )
    return send_file(
        io.BytesIO(documento.archivo), download_name=documento.nombre, mimetype=mimetype
    )


@auth_bp.route("/historial", methods=["GET"])
@jwt_required()
def historial_usuario():
    user_email = get_jwt_identity()
    db = SessionLocal()
    usuario = db.query(Usuario).filter_by(email=user_email).first()
    if not usuario:
        db.close()
        return jsonify({"error": "Usuario no encontrado"}), 404

    from app.models.interaccion import Interaccion

    historial = (
        db.query(Interaccion)
        .filter_by(id_usuario=usuario.id)
        .order_by(Interaccion.fecha.desc())
        .all()
    )
    db.close()
    items = []
    for h in historial:
        items.append(
            {
                "id": h.id,
                "title": h.pregunta[:40] + ("..." if len(h.pregunta) > 40 else ""),
                "date": h.fecha.isoformat() if h.fecha else "",
                "messageCount": 2,
                "type": "document" if h.documento_id else "query",
                "pregunta": h.pregunta,
                "respuesta": h.respuesta,
                "documento_id": h.documento_id,
            }
        )
    return jsonify(items)


@auth_bp.route("/historial/<int:interaccion_id>/messages", methods=["GET"])
def historial_mensajes(interaccion_id):
    from app.models.interaccion import Interaccion

    db = SessionLocal()
    interaccion = db.query(Interaccion).filter_by(id=interaccion_id).first()
    db.close()
    if not interaccion:
        return jsonify([])

    messages = [
        {
            "id": interaccion.id * 2 - 1,
            "type": "user",
            "content": interaccion.pregunta,
            "timestamp": interaccion.fecha.isoformat() if interaccion.fecha else "",
        },
        {
            "id": interaccion.id * 2,
            "type": "assistant",
            "content": interaccion.respuesta,
            "timestamp": interaccion.fecha.isoformat() if interaccion.fecha else "",
        },
    ]

    return jsonify(messages)


@auth_bp.route("/update_user", methods=["POST"])
def update_user():
    db = SessionLocal()
    data = request.get_json()
    email_original = data.get("email_original")
    nombre = data.get("nombre")
    email = data.get("email")
    telefono = data.get("telefono")
    usuario = db.query(Usuario).filter_by(email=email_original).first()
    if not usuario:
        db.close()
        return jsonify({"error": "Usuario no encontrado"}), 404
    usuario.nombre = nombre
    usuario.email = email
    usuario.telefono = telefono
    db.commit()
    db.refresh(usuario)
    db.close()
    return jsonify(
        {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "telefono": usuario.telefono,
            "rol": usuario.rol,
        }
    )


@auth_bp.route("/change_password", methods=["POST"])
def change_password():
    db = SessionLocal()
    data = request.get_json()
    email = data.get("email")
    old = data.get("old")
    new = data.get("new")
    usuario = db.query(Usuario).filter_by(email=email).first()
    if not usuario or not check_password_hash(usuario.password_hash, old):
        db.close()
        return jsonify({"error": "Credenciales incorrectas"}), 400
    usuario.password_hash = generate_password_hash(new)
    db.commit()
    db.close()
    return jsonify({"success": True})


@auth_bp.route("/notification_settings", methods=["POST"])
@jwt_required()
def update_notification_settings():
    db = SessionLocal()
    user_email = get_jwt_identity()
    data = request.get_json()
    push_enabled = data.get("push_enabled", False)
    email_enabled = data.get("email_enabled", False)

    usuario = db.query(Usuario).filter_by(email=user_email).first()
    if not usuario:
        db.close()
        return jsonify({"error": "Usuario no encontrado"}), 404

    settings = db.query(NotificationSettings).filter_by(user_id=usuario.id).first()
    if settings:
        settings.push_enabled = push_enabled
        settings.email_enabled = email_enabled
    else:
        settings = NotificationSettings(
            user_id=usuario.id,
            push_enabled=push_enabled,
            email_enabled=email_enabled,
        )
        db.add(settings)

    db.commit()
    db.close()
    return jsonify({"success": True})


@auth_bp.route("/notification_settings", methods=["GET"])
@jwt_required()
def get_notification_settings():
    db = SessionLocal()
    user_email = get_jwt_identity()
    usuario = db.query(Usuario).filter_by(email=user_email).first()
    if not usuario:
        db.close()
        return jsonify({"error": "Usuario no encontrado"}), 404

    settings = db.query(NotificationSettings).filter_by(user_id=usuario.id).first()
    db.close()
    if not settings:
        return jsonify({"push_enabled": False, "email_enabled": False})
    return jsonify(
        {"push_enabled": settings.push_enabled, "email_enabled": settings.email_enabled}
    )


@auth_bp.route("/tts", methods=["POST"])
def tts():
    data = request.get_json()
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    # Elimina emojis antes de sintetizar
    text = remove_emojis(text)

    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="es-ES", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    try:
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        audio_content = base64.b64encode(response.audio_content).decode("utf-8")
        return jsonify({"audio": audio_content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/speech-to-text", methods=["POST"])
def speech_to_text():
    import os
    print("GOOGLE_APPLICATION_CREDENTIALS:", os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
    if "audio" not in request.files:
        return jsonify({"error": "No se envió archivo de audio"}), 400

    audio_file = request.files["audio"]
    print("Audio recibido:", audio_file.filename, audio_file.content_type, audio_file.content_length)

    # Guarda el archivo temporalmente como .webm
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp:
        audio_file.save(temp.name)
        temp_path = temp.name

    print("Archivo guardado temporalmente en:", temp_path)

    client = speech.SpeechClient()

    with open(temp_path, "rb") as f:
        content = f.read()
    print("Tamaño del archivo leído:", len(content))

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
        sample_rate_hertz=48000,
        language_code="es-PE",
    )

    document_id = request.form.get("document_id") or request.args.get("document_id")
    user_email = request.form.get("user_email") or request.args.get("user_email")
    contexto = ""
    doc_id_usado = None

    try:
        response = client.recognize(config=config, audio=audio)
        os.remove(temp_path)

        if not response.results:
            print("No se detectó voz en el audio.")
            return jsonify({"text": ""})

        transcript = response.results[0].alternatives[0].transcript
        print("Transcripción:", transcript)

        # Buscar contexto en documentos si no se envía document_id
        if document_id:
            db = SessionLocal()
            documento = db.query(Documento).filter_by(id=document_id).first()
            if documento and documento.texto_extraido:
                contexto = documento.texto_extraido
                doc_id_usado = documento.id
            db.close()
        elif user_email:
            db = SessionLocal()
            usuario = db.query(Usuario).filter_by(email=user_email).first()
            if usuario:
                documentos = db.query(Documento).filter_by(id_usuario=usuario.id).order_by(Documento.fecha.desc()).all()
                mejor_doc = None
                mejor_score = 0
                for doc in documentos:
                    if doc.texto_extraido:
                        # Score: contar palabras de la pregunta en el texto del documento
                        score = sum(1 for palabra in transcript.lower().split() if palabra in doc.texto_extraido.lower())
                        if score > mejor_score:
                            mejor_score = score
                            mejor_doc = doc
                # Si hay coincidencias, usa el documento con mayor score
                if mejor_doc and mejor_score > 0:
                    contexto = mejor_doc.texto_extraido
                    doc_id_usado = mejor_doc.id
                # Si no hay coincidencias pero el usuario tiene documentos, usa el más reciente con texto
                elif documentos:
                    for doc in documentos:
                        if doc.texto_extraido:
                            contexto = doc.texto_extraido
                            doc_id_usado = doc.id
                            break
            db.close()

        # Antes de llamar a get_assistant_response
        print("=== CONTEXTO ENVIADO A GEMINI ===")
        print(contexto[:500])  # Muestra los primeros 500 caracteres del contexto
        print("=== FIN DEL CONTEXTO ===")

        respuesta_ia = get_assistant_response(transcript, contexto=contexto)

        respuesta_ia_sin_emojis = remove_emojis(respuesta_ia)

        tts_client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=respuesta_ia_sin_emojis)
        voice = texttospeech.VoiceSelectionParams(
            language_code="es-ES", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        tts_response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        audio_content = base64.b64encode(tts_response.audio_content).decode("utf-8")

        return jsonify({
            "transcript": transcript,
            "text": respuesta_ia_sin_emojis, 
            "audio": audio_content,
            "document_id": doc_id_usado
        })
    except Exception as e:
        import traceback
        print("Error en speech-to-text:", e)
        traceback.print_exc()
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": str(e)}), 500

def remove_emojis(text):
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002700-\U000027BF"  # Dingbats
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub(r'', text)
