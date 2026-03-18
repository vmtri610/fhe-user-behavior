"""Backend — client-side FHE operations gọi từ Gradio."""

import os
import pickle
import requests
import numpy as np
import pandas as pd
from pathlib import Path
from concrete.ml.deployment import FHEModelClient

import joblib
from backend.app.shared.utils import preprocess_customer_data

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor

SERVER_URL      = os.getenv("SERVER_URL", "http://localhost:8000")
DEPLOYMENT_PATH = Path(os.getenv("DEPLOYMENT_PATH", Path(__file__).parent.parent / "fhe-models"))
KEY_DIR_BASE    = Path(os.getenv("KEY_DIR", Path(__file__).parent / "client_keys"))
PREPROCESSOR    = Path(os.getenv("PREPROCESSOR_PATH", Path(__file__).parent.parent / "models/scaler.pkl"))

KEY_DIR_BASE.mkdir(exist_ok=True)

# Load scaler một lần
if PREPROCESSOR.exists():
    _scaler = joblib.load(PREPROCESSOR)
else:
    _scaler = None

# Configure Jaeger for the client
OTLP_GRPC_ENDPOINT = os.getenv("OTLP_GRPC_ENDPOINT", "jaeger-jaeger.tracing.svc.cluster.local:4317")

def setup_client_tracer():
    try:
        tracer_provider = TracerProvider(
            resource=Resource.create({SERVICE_NAME: "fhe-user-behavior-client"})
        )
        trace.set_tracer_provider(tracer_provider)
        otlp_exporter = OTLPSpanExporter(
            endpoint=OTLP_GRPC_ENDPOINT,
            insecure=True,
        )
        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        RequestsInstrumentor().instrument()
        return trace.get_tracer(__name__)
    except Exception:
        return trace.get_tracer(__name__)

tracer = setup_client_tracer()


# ── Helpers ────────────────────────────────────────────────────────────────
def _shorten(b: bytes, limit: int = 500) -> str:
    """Hiển thị ngắn gọn bytes dưới dạng hex để show trên UI."""
    return b[100: 100 + limit].hex()


def _get_client(client_id: str) -> FHEModelClient:
    key_dir = KEY_DIR_BASE / str(client_id)
    return FHEModelClient(path_dir=DEPLOYMENT_PATH, key_dir=key_dir)


def _send_file(client_id: str, file_name: str, content: bytes) -> bool:
    resp = requests.post(
        f"{SERVER_URL}/send_file",
        data={"client_id": client_id, "file_name": file_name},
        files=[("files", (file_name, content, "application/octet-stream"))],
    )
    return resp.ok


# ── Step 1: Keygen ─────────────────────────────────────────────────────────
def keygen_send(client_id: str):
    """Sinh private key + evaluation key, gửi eval key lên server."""
    client = _get_client(client_id)
    client.generate_private_and_evaluation_keys(force=True)
    eval_key = client.get_serialized_evaluation_keys()

    ok = _send_file(client_id, "evaluation_key", eval_key)
    if not ok:
        raise RuntimeError("Failed to send evaluation key to server.")

    return _shorten(eval_key)   # hiển thị ngắn trên UI


# ── Step 2: Preprocess → Encrypt → Send ────────────────────────────────────
def preprocess_encrypt_send(
    client_id: str,
    age: int,
    gender: int,
    annual_income: float,
    num_purchases: int,
    product_category: int,
    time_on_website: float,
    loyalty_program: int,
    discounts_availed: int,
):
    """Nhận raw input, preprocess, encrypt, gửi lên server."""
    if not client_id:
        raise ValueError("Vui lòng sinh khóa trước (Step 1).")

    customer_dict = {
        "Age":                age,
        "Gender":             gender,
        "AnnualIncome":       annual_income,
        "NumberOfPurchases":  num_purchases,
        "ProductCategory":    product_category,
        "TimeSpentOnWebsite": time_on_website,
        "LoyaltyProgram":     loyalty_program,
        "DiscountsAvailed":   discounts_availed,
    }

    if _scaler is None:
        raise RuntimeError("Scaler not found. Please ensure it is in 'models' folder.")

    # Preprocess đúng theo utils (thêm TimePerPurchase)
    df_processed = preprocess_customer_data(customer_dict, _scaler)
    
    # Concrete-ML FHE model quantize sẽ nhận pandas dataframe hoặc numpy array
    # Chuyển sang numpy array để tránh lỗi slice index của pandas
    X = df_processed.values

    # Quantize + encrypt + serialize
    client      = _get_client(client_id)
    enc_input   = client.quantize_encrypt_serialize(X)

    ok = _send_file(client_id, "encrypted_input", enc_input)
    if not ok:
        raise RuntimeError("Failed to send encrypted input to server.")

    return _shorten(enc_input)


# ── Step 3: Run FHE ────────────────────────────────────────────────────────
def run_fhe(client_id: str):
    """Trigger FHE inference trên server."""
    if not client_id:
        raise ValueError("Vui lòng sinh khóa trước (Step 1).")

    resp = requests.post(
        f"{SERVER_URL}/run_fhe",
        data={"client_id": client_id},
    )
    if not resp.ok:
        detail = resp.json().get("message", resp.text)
        raise RuntimeError(f"FHE run failed: {detail}")

    elapsed = resp.json()   # float seconds
    return f"{elapsed}s"


# ── Step 4: Get output + Decrypt ───────────────────────────────────────────
def get_output_decrypt(client_id: str):
    """Lấy encrypted output từ server, decrypt, trả kết quả."""
    if not client_id:
        raise ValueError("Vui lòng sinh khóa trước (Step 1).")

    resp = requests.post(
        f"{SERVER_URL}/get_output",
        data={"client_id": client_id},
    )
    if not resp.ok:
        detail = resp.json().get("message", resp.text)
        raise RuntimeError(f"Get output failed: {detail}")

    enc_output = resp.content
    client     = _get_client(client_id)
    
    # Load keys từ thư mục client cache thay vì báo lỗi chưa khởi tạo keys
    fmt = getattr(client.model.ciphertext_format, "name", client.model.ciphertext_format)
    if fmt != "TFHE_RS":
        client.client.keygen(force=False)
    else:
        # Nếu model là TFHE_RS thì việc recreate client sẽ phức tạp hơn vì nó ko lưu private key
        pass
        
    proba      = client.deserialize_decrypt_dequantize(enc_output)

    predicted = int(np.argmax(proba, axis=1).squeeze())
    label     = "✅ Dự đoán sẽ mua hàng" if predicted == 1 else "❌ Dự đoán không mua hàng"

    return label, _shorten(enc_output)

# ── End-to-End Flow ────────────────────────────────────────────────────────
def run_end_to_end_flow(age, gender, income, purchases, category, time_web, loyalty, discounts):
    """Chạy toàn bộ quy trình FHE từ cấu hình đến dự đoán trong 1 trace duy nhất."""
    new_client_id = str(np.random.randint(0, 2**32))
    
    with tracer.start_as_current_span("Full_FHE_End_to_End_Flow"):
        # Step 1
        with tracer.start_as_current_span("client_step_1_keygen"):
            eval_key_short = keygen_send(new_client_id)
            
        # Step 2
        with tracer.start_as_current_span("client_step_2_encrypt_send"):
            enc_input_short = preprocess_encrypt_send(
                new_client_id, age, gender, income, purchases, category, time_web, loyalty, discounts
            )
            
        # Step 3
        with tracer.start_as_current_span("client_step_3_fhe_inference"):
            elapsed_time = run_fhe(new_client_id)
            
        # Step 4
        with tracer.start_as_current_span("client_step_4_decrypt_output"):
            label, enc_out_short = get_output_decrypt(new_client_id)
            
        return new_client_id, eval_key_short, enc_input_short, elapsed_time, enc_out_short, label
