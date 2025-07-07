from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from app.database import Base
from datetime import datetime

class Interaccion(Base):
    __tablename__ = "interacciones"
    id = Column(Integer, primary_key=True, index=True)
    documento_id = Column(Integer, nullable=True)
    pregunta = Column(Text, nullable=False)
    respuesta = Column(Text, nullable=False)
    id_usuario = Column(Integer, nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow)