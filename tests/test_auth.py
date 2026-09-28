def test_signup_login_and_guard(client):
    assert client.post("/auth/signup/", json={"name": "A", "email": "a@x.com", "password": "secret123"}).status_code == 201
    assert client.post("/auth/signup/", json={"name": "A", "email": "a@x.com", "password": "secret123"}).status_code == 400
    r = client.post("/auth/login/", data={"username": "a@x.com", "password": "secret123"})
    assert r.status_code == 200 and "access_token" in r.json()
    assert client.get("/bookings/").status_code == 401
