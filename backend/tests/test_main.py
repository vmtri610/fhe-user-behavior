from fastapi.testclient import TestClient
from backend.app.server.main import app

client = TestClient(app)

def test_read_root():
    """Kiểm tra API root route"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_health_check():
    """Kiểm tra API health status"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

from unittest.mock import patch

class MockModel:
    def predict(self, df):
        import numpy as np
        return np.array([1])

class MockScaler:
    def transform(self, df):
        return df

@patch("backend.app.server.main.load_model_assets")
def test_predict_plaintext_success(mock_load_assets):
    """Kiểm tra API predict plaintext hoạt động, sử dụng Mocking vì model không lưu trên Git/Docker nữa."""
    mock_load_assets.return_value = (MockModel(), MockScaler())

    sample_payload = {
        "Age": 60,
        "Gender": 1,
        "AnnualIncome": 99682.15,
        "NumberOfPurchases": 19,
        "ProductCategory": 3,
        "TimeSpentOnWebsite": 22.59,
        "LoyaltyProgram": 0,
        "DiscountsAvailed": 5
    }
    response = client.post("/predict", json=sample_payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert data["status"] == "success"
    assert "prediction" in data
    assert isinstance(data["prediction"], int)
    assert data["prediction"] == 1
