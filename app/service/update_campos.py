import json

from app.database import SessionLocal
from app.models.documentos import Documento

def actualizar_documento_campos(documento_id, campos_dict, ruta=None):
    db = SessionLocal()
    documento = db.query(Documento).filter_by(id=documento_id).first()
    if documento:
        documento.campos_json = json.dumps(campos_dict)
        if ruta:
            documento.ruta = ruta
        db.commit()
    db.close()