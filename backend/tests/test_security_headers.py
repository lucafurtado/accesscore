from httpx import AsyncClient


async def test_responses_include_defensive_security_headers(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "max-age=" in response.headers["Strict-Transport-Security"]
