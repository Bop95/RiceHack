from backend.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_root_endpoint():
  response = client.get("/")
  assert response.status_code == 200
  assert response.json() == {
      "message": "FinalFlow Backend Search Service Active"
  }


def test_search_endpoint_validation():
  # Query shorter than minLength=2 should fail with 422
  response = client.get("/api/search?q=a")
  assert response.status_code == 422