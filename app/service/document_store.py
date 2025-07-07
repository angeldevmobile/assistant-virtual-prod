from app.database import SessionLocal
from app.models.documentos import Documento
import json

def agregar_documento(nombre, fecha, validado, ruta, campos={}, id_usuario=None, texto_extraido="", archivo=None):
    db = SessionLocal()
    campos_json = json.dumps(campos)
    nuevo_documento = Documento(
        nombre=nombre,
        fecha=fecha,
        validado=validado,
        ruta=ruta,
        campos_json=campos_json,
        texto_extraido=texto_extraido,
        id_usuario=id_usuario,
        archivo=archivo  
    )
    db.add(nuevo_documento)
    db.commit()
    db.close()

def listar_documentos():
    db = SessionLocal()
    documentos = db.query(Documento).order_by(Documento.fecha.desc()).all()
    db.close()
    return documentos