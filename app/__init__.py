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

    app.config["JWT_SECRET_KEY"] = "b7f$2K!9zQw@1xR8pL#eT6vN3sJ0uY5c"
    JWTManager(app)

    app.register_blueprint(auth_bp, url_prefix="/api/v1")
    return app
