from sqlalchemy import Column, Integer, Boolean, ForeignKey
from app.database import Base

class NotificationSettings(Base):
    __tablename__ = "notification_settings"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"))
    push_enabled = Column(Boolean, default=False)
    email_enabled = Column(Boolean, default=False)