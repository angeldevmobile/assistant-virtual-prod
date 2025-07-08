import os
import json

# 🔐 Manejo de credenciales GCP para Render y local
if "GOOGLE_APPLICATION_CREDENTIALS_JSON" in os.environ:
    json_path = "/tmp/gcp_creds.json"
    with open(json_path, "w") as f:
        f.write(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = json_path

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
