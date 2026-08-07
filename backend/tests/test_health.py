from httpx import AsyncClient


async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "accesscore-api"
    assert "X-Request-ID" in response.headers
