from app import create_app
import os
from flask import send_from_directory

app = create_app()

# Configuración para servir archivos estáticos del frontend
@app.route("/")
def serve_index():
    return send_from_directory("static", "index.html")

@app.route("/<path:path>")
def serve_static_files(path):
    return send_from_directory("static", path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))