from fastapi import FastAPI, UploadFile, File, Form, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import os
import shutil
import time
from pathlib import Path
from concrete.ml.deployment import FHEModelServer
from typing import List

from backend.app.shared.utils import preprocess_customer_data, load_model_assets

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from loguru import logger
from starlette.types import ASGIApp

class Customer(BaseModel):
    Age: int = Field(60, description="Age of the customer")
    Gender: int = Field(1, description="Gender of the customer (1: Male, 0: Female)")
    AnnualIncome: float = Field(99682.145724, description="Annual income of the customer")
    NumberOfPurchases: int = Field(19, description="Number of purchases made by the customer")
    ProductCategory: int = Field(3, description="Product category preferred by the customer")
    TimeSpentOnWebsite: float = Field(22.588059, description="Time spent on the website by the customer")
    LoyaltyProgram: int = Field(0, description="Loyalty program status of the customer")
    DiscountsAvailed: int = Field(5, description="Number of discounts availed by the customer")

app = FastAPI(title="FHE User Behavior API")

# ── FHE Configuration ──────────────────────────────────────────────────────────
FHE_MODEL_DIR = Path(__file__).parent.parent / "fhe-models"
SERVER_FILES = Path(__file__).parent / "server_files"
MAX_SESSIONS = int(os.getenv("MAX_SESSIONS", "20"))
SERVER_FILES.mkdir(exist_ok=True)

logger.info(f"Loading FHE server from {FHE_MODEL_DIR} ...")
fhe_server = FHEModelServer(path_dir=FHE_MODEL_DIR)
fhe_server.load()
logger.info("FHE server loaded.")

# ── Telemetry (Jaeger) Configuration ───────────────────────────────────────────
OTLP_GRPC_ENDPOINT = os.getenv("OTLP_GRPC_ENDPOINT", "jaeger-jaeger.tracing.svc.cluster.local:4317")

def setting_jaeger(app: ASGIApp, log_correlation: bool = True) -> None:
    try:
        tracer = TracerProvider(
            resource=Resource.create({SERVICE_NAME: "fhe-user-behavior"})
        )
        trace.set_tracer_provider(tracer)

        otlp_exporter = OTLPSpanExporter(
            endpoint=OTLP_GRPC_ENDPOINT,
            insecure=True,
        )
        logger.info(f"Configuring OTLP exporter with endpoint: {OTLP_GRPC_ENDPOINT}")
        tracer.add_span_processor(BatchSpanProcessor(otlp_exporter))

        if log_correlation:
            LoggingInstrumentor().instrument(set_logging_format=True)
        FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer)
        logger.info("Jaeger instrumentation completed successfully")
    except Exception as e:
        logger.error(f"Failed to set up Jaeger instrumentation: {str(e)}")
        # Không raise lỗi nếu không có Jaeger, tuỳ config.
        # raise

setting_jaeger(app)
tracer = trace.get_tracer(__name__)

# ── Helpers for FHE endpoints ────────────────────────────────────────────────
def _session_path(client_id: str, file_name: str) -> Path:
    dir_path = SERVER_FILES / client_id
    dir_path.mkdir(exist_ok=True)
    return dir_path / file_name

def _clean_old_sessions():
    sessions = sorted(SERVER_FILES.iterdir(), key=os.path.getmtime)
    if len(sessions) > MAX_SESSIONS:
        for old in sessions[: len(sessions) - MAX_SESSIONS]:
            shutil.rmtree(old, ignore_errors=True)
            logger.info(f"Removed old session: {old.name}")

# ── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/")
def read_root():
    return {"message": "Welcome to fhe-user-behavior API! FHE and Plaintext predictors are running."}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict")
def predict(customer: Customer):
    """
    Plaintext Prediction (không mã hoá).
    """
    try:
        with tracer.start_as_current_span("load_model_assets"):
            model, scaler = load_model_assets()
        
        if model is None or scaler is None:
            return {
                "status": "error",
                "message": "Model or Scaler not found. Please ensure they are in the 'models' folder."
            }
        
        customer_dict = customer.dict()
        with tracer.start_as_current_span("preprocess_customer_data"):
            df_processed = preprocess_customer_data(customer_dict, scaler)
        
        with tracer.start_as_current_span("plaintext_inference"):
            prediction = model.predict(df_processed)
        
        return {
            "prediction": int(prediction[0]),
            "status": "success",
            "message": "Dự đoán sẽ mua hàng" if prediction[0] == 1 else "Dự đoán không mua hàng"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/send_file")
async def send_file(
    client_id: str = Form(),
    file_name: str = Form(),
    files: List[UploadFile] = File(),
):
    """
    Bước 1 & 2: Client gửi evaluation_key và encrypted_input lên server.
    """
    with tracer.start_as_current_span("clean_old_sessions"):
        _clean_old_sessions()
        
    with tracer.start_as_current_span("save_client_file"):
        file_path = _session_path(client_id, file_name)
        content = await files[0].read()
        file_path.write_bytes(content)
        logger.info(f"[{client_id}] Saved {file_name} ({len(content)} bytes)")
        
    return {"status": "ok", "file_name": file_name, "size": len(content)}

@app.post("/run_fhe")
async def run_fhe(client_id: str = Form()):
    """
    Bước 3: Chạy FHE inference trên encrypted_input dùng evaluation_key.
    """
    eval_key_path  = _session_path(client_id, "evaluation_key")
    enc_input_path = _session_path(client_id, "encrypted_input")

    if not eval_key_path.exists():
        return JSONResponse(status_code=400,
            content={"status": "error", "message": "evaluation_key not found. Please send it first."})
    if not enc_input_path.exists():
        return JSONResponse(status_code=400,
            content={"status": "error", "message": "encrypted_input not found. Please send it first."})

    with tracer.start_as_current_span("read_fhe_inputs"):
        eval_key  = eval_key_path.read_bytes()
        enc_input = enc_input_path.read_bytes()

    logger.info(f"[{client_id}] Running FHE inference ...")
    t0 = time.time()
    with tracer.start_as_current_span("fhe_inference"):
        enc_output = fhe_server.run(enc_input, serialized_evaluation_keys=eval_key)
    elapsed    = round(time.time() - t0, 2)
    logger.info(f"[{client_id}] FHE done in {elapsed}s")

    with tracer.start_as_current_span("save_fhe_output"):
        _session_path(client_id, "encrypted_output").write_bytes(enc_output)
    return JSONResponse(content=elapsed)

@app.post("/get_output")
async def get_output(client_id: str = Form()):
    """
    Bước 4: Client lấy encrypted_output về để tự decrypt.
    """
    out_path = _session_path(client_id, "encrypted_output")
    if not out_path.exists():
        return JSONResponse(status_code=400,
            content={"status": "error", "message": "Output not ready. Run /run_fhe first."})

    logger.info(f"[{client_id}] Sending encrypted_output")
    with tracer.start_as_current_span("read_encrypted_output"):
        output_bytes = out_path.read_bytes()
    return Response(output_bytes, media_type="application/octet-stream")
