from app.database import SessionLocal
from app.models.interaccion import Interaccion

def guardar_interaccion(pregunta, respuesta, documento_id=None, id_usuario=None):
    db = SessionLocal()
    nueva_interaccion = Interaccion(
        documento_id=documento_id,
        pregunta=pregunta,
        respuesta=respuesta,
        id_usuario=id_usuario
    )
    db.add(nueva_interaccion)
    db.commit()
    db.close()