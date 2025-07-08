from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from app.routes.auth import auth_bp


def create_app():
    app = Flask(__name__)

    CORS(
        app,
        origins=[
            "http://localhost:8080",
            "https://assistant-gem-virtual.onrender.com",  # frontend en producción
        ],
        supports_credentials=True,
    )
    app.config["JWT_SECRET_KEY"] = "b7f$2K!9zQw@1xR8pLeT6vN3sJ0uY5c"
    jwt = JWTManager(app)

    app.register_blueprint(auth_bp, url_prefix="/api/v1")
    return app
