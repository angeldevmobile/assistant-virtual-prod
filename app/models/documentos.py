from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, LargeBinary
from app.database import Base

class Documento(Base):
    __tablename__ = "documentos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    fecha = Column(DateTime, nullable=False)
    validado = Column(Boolean, default=False)
    ruta = Column(String(500), nullable=True)  
    campos_json = Column(Text)
    texto_extraido = Column(Text) 
    id_usuario = Column(Integer, nullable=True)
    archivo = Column(LargeBinary, nullable=False)
