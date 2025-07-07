from google.cloud import documentai_v1 as documentai
from google.api_core.client_options import ClientOptions
import os

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("GCP_LOCATION", "us")
OCR_PROCESSOR_ID = os.getenv("GCP_OCR_PROCESSOR_ID")
EXTRACTOR_PROCESSOR_ID = os.getenv("GCP_EXTRACTOR_PROCESSOR_ID")

GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if GOOGLE_APPLICATION_CREDENTIALS:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS


def procesar_documento_ocr(content_bytes, mimetype):
    client = documentai.DocumentProcessorServiceClient(
        client_options=ClientOptions(
            api_endpoint=f"{LOCATION}-documentai.googleapis.com"
        )
    )
    name = f"projects/{PROJECT_ID}/locations/{LOCATION}/processors/{OCR_PROCESSOR_ID}"

    raw_document = documentai.RawDocument(content=content_bytes, mime_type=mimetype)

    request = documentai.ProcessRequest(name=name, raw_document=raw_document)

    result = client.process_document(request=request)

    texto = result.document.text
    return {"texto": texto, "campos": {}}


def procesar_documento_extractor(content_bytes, mimetype):
    client = documentai.DocumentProcessorServiceClient(
        client_options=ClientOptions(
            api_endpoint=f"{LOCATION}-documentai.googleapis.com"
        )
    )
    name = f"projects/{PROJECT_ID}/locations/{LOCATION}/processors/{EXTRACTOR_PROCESSOR_ID}"

    raw_document = documentai.RawDocument(content=content_bytes, mime_type=mimetype)

    request = documentai.ProcessRequest(name=name, raw_document=raw_document)

    result = client.process_document(request=request)

    texto = result.document.text
    campos = {ent.type_: ent.mention_text for ent in result.document.entities}
    return {"texto": texto, "campos": campos}
