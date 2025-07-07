from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from app.routes.auth import auth_bp
from dotenv import load_dotenv
import os


def create_app():
    load_dotenv()

    app = Flask(__name__)

    CORS(
        app,
        origins=["https://assistant-virtual-production-d926ccecee28.herokuapp.com"],
        supports_credentials=True,
        expose_headers=["Authorization"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.config["JWT_SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")
    JWTManager(app)

    app.register_blueprint(auth_bp, url_prefix="/api/v1")
    return app
