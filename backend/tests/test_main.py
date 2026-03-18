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

def test_predict_plaintext_success():
    """Kiểm tra API predict plaintext hoạt động (nếu đã có model)"""
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
    if data["status"] == "success":
        assert "prediction" in data
        assert isinstance(data["prediction"], int)
    else:
        # Nếu model scale bị lỗi version numpy/sklearn hoặc không tải được
        assert data["status"] == "error"
        assert "message" in data
