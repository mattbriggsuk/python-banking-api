import json
from decimal import Decimal

import pytest
from conftest import create_account, headers, move_money, register
from fastapi.testclient import TestClient

from banking.api.dependencies import get_customer_service
from banking.api.main import create_app
from banking.utils.numbers import generate_number, is_valid_number


def test_complete_customer_and_account_lifecycle(client):
    customer = register(client, " Alice@Example.com ")
    number = customer["customer"]["customerNumber"]
    assert is_valid_number(number)
    assert len(customer["pin"]) == 6
    assert customer["customer"] == {
        "customerNumber": number,
        "firstName": "Alice",
        "lastName": "Smith",
        "email": "alice@example.com",
    }
    for identifier in (number, " ALICE@EXAMPLE.COM "):
        response = client.post(
            "/api/access/login", json={"identifier": identifier, "pin": customer["pin"]}
        )
        assert response.status_code == 200
        assert response.json()["customer"] == customer["customer"]
        assert "pin" not in response.json()

    profile = client.get(
        "/api/customer/get", params={"customerNumber": number}, headers=headers(customer)
    )
    assert profile.json() == {"customer": customer["customer"]}
    source = create_account(client, customer)
    target = create_account(client, customer, "SAVINGS")
    assert source["closed"] is False and source["balance"] == 0
    assert target["accountType"] == "SAVINGS"
    assert move_money(client, customer, "deposit", source, "100.00").status_code == 200
    assert (
        move_money(client, customer, "withdraw", source, "10.00").json()["account"]["balance"] == 90
    )
    result = move_money(client, customer, "transfer", target, "25.00", source).json()
    assert result["fromAccount"]["balance"] == 65
    assert result["toAccount"]["balance"] == 25
    accounts = client.get(
        "/api/customer/accounts", params={"customerNumber": number}, headers=headers(customer)
    ).json()
    assert accounts["customerNumber"] == number and len(accounts["accounts"]) == 2
    for account, amount in ((source, 65), (target, 25)):
        assert move_money(client, customer, "withdraw", account, amount).status_code == 200
        closed = client.post(
            "/api/account/close",
            json={"accountNumber": account["accountNumber"]},
            headers=headers(customer),
        )
        assert closed.status_code == 202 and closed.json()["account"]["closed"] is True
        assert move_money(client, customer, "deposit", account, 1).status_code == 409
    logout = client.post("/api/access/logout", headers=headers(customer))
    assert logout.status_code == 204 and logout.content == b""
    assert (
        client.get(
            "/api/customer/get", params={"customerNumber": number}, headers=headers(customer)
        ).status_code
        == 401
    )


def test_ownership_and_cross_customer_transfer(client):
    alice = register(client)
    bob = register(client, "bob@example.com")
    source = create_account(client, alice)
    target = create_account(client, bob)
    for route in ("get", "accounts"):
        assert (
            client.get(
                f"/api/customer/{route}",
                params={"customerNumber": bob["customer"]["customerNumber"]},
                headers=headers(alice),
            ).status_code
            == 403
        )
    for operation in ("deposit", "withdraw"):
        assert move_money(client, alice, operation, target, 1).status_code == 403
    assert (
        client.post(
            "/api/account/close",
            json={"accountNumber": target["accountNumber"]},
            headers=headers(alice),
        ).status_code
        == 403
    )
    assert move_money(client, alice, "deposit", source, 10).status_code == 200
    assert move_money(client, bob, "transfer", target, 5, source).status_code == 403
    result = move_money(client, alice, "transfer", target, 5, source)
    assert result.status_code == 200
    assert result.json()["toAccount"]["customerNumber"] == bob["customer"]["customerNumber"]


def test_duplicate_registration_and_generic_login_errors(client):
    customer = register(client)
    duplicate = client.post(
        "/api/customer/register",
        json={"customer": {"firstName": "Other", "lastName": "Name", "email": "ALICE@example.com"}},
    )
    assert duplicate.status_code == 409
    details = []
    wrong_pin = "000000" if customer["pin"] != "000000" else "000001"
    for identifier in ("alice@example.com", "unknown@example.com"):
        response = client.post(
            "/api/access/login", json={"identifier": identifier, "pin": wrong_pin}
        )
        assert response.status_code == 401
        details.append(response.json()["detail"])
    assert details[0] == details[1]
    assert (
        client.post(
            "/api/access/login", json={"identifier": "alice@example.com", "pin": customer["pin"]}
        ).status_code
        == 200
    )


@pytest.mark.parametrize("account_type", ["CURRENT", "SAVINGS", "CREDIT"])
def test_account_types(client, account_type):
    customer = register(client)
    assert create_account(client, customer, account_type)["accountType"] == account_type


def test_default_type_and_session_controls_account_owner(client):
    customer = register(client)
    response = client.post(
        "/api/account/create", json={"customerNumber": generate_number()}, headers=headers(customer)
    )
    assert response.status_code == 201
    account = response.json()["account"]
    assert account["accountType"] == "CURRENT"
    assert account["customerNumber"] == customer["customer"]["customerNumber"]


@pytest.mark.parametrize("body", [{"accountType": None}, {"accountType": "UNKNOWN"}])
def test_invalid_account_type(client, body):
    customer = register(client)
    assert (
        client.post("/api/account/create", json=body, headers=headers(customer)).status_code == 400
    )


@pytest.mark.parametrize("amount", [0, -1, "0.001", "10000000000000000", "NaN", "Infinity", True])
def test_invalid_amounts_do_not_change_balance(client, amount):
    customer = register(client)
    account = create_account(client, customer)
    response = move_money(client, customer, "deposit", account, amount)
    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"
    assert "pin" not in response.text
    assert move_money(client, customer, "deposit", account, 1).json()["account"]["balance"] == 1


def test_rejected_operations_and_missing_account(client):
    customer = register(client)
    source = create_account(client, customer)
    target = create_account(client, customer)
    assert move_money(client, customer, "withdraw", source, 1).status_code == 409
    assert move_money(client, customer, "transfer", target, 1, source).status_code == 409
    assert move_money(client, customer, "transfer", source, 1, source).status_code == 400
    assert (
        move_money(client, customer, "deposit", {"accountNumber": generate_number()}, 1).status_code
        == 404
    )
    assert (
        move_money(
            client, customer, "deposit", {"accountNumber": "0000000000000001"}, 1
        ).status_code
        == 400
    )
    assert move_money(client, customer, "deposit", source, 5).status_code == 200
    assert (
        client.post(
            "/api/account/close",
            json={"accountNumber": source["accountNumber"]},
            headers=headers(customer),
        ).status_code
        == 409
    )
    malformed = {
        "transaction": {
            "transactionType": "WITHDRAWAL",
            "amount": 1,
            "targetAccountNumber": source["accountNumber"],
        }
    }
    assert (
        client.post("/api/account/deposit", json=malformed, headers=headers(customer)).status_code
        == 400
    )
    assert move_money(client, customer, "deposit", source, 1, target).status_code == 400


def test_large_numeric_amount_keeps_cents_and_numeric_response(client):
    customer = register(client)
    account = create_account(client, customer)
    body = (
        '{"transaction":{"transactionType":"DEPOSIT","amount":9999999999999999.99,'
        f'"targetAccountNumber":"{account["accountNumber"]}"}}}}'
    )
    response = client.post(
        "/api/account/deposit",
        content=body,
        headers={**headers(customer), "Content-Type": "application/json"},
    )
    assert response.status_code == 200, response.text
    parsed = json.loads(response.text, parse_float=Decimal)
    assert parsed["account"]["balance"] == Decimal("9999999999999999.99")
    assert '"balance":9999999999999999.99' in response.text
    assert (
        move_money(client, customer, "withdraw", account, "9999999999999999.99").json()["account"][
            "balance"
        ]
        == 0
    )


@pytest.mark.parametrize("authorization", [None, "Basic abc", "Bearer ", "Bearer unknown"])
def test_invalid_or_missing_session(client, authorization):
    response = client.post(
        "/api/account/create",
        json={},
        headers={"Authorization": authorization} if authorization is not None else {},
    )
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.headers["Cache-Control"] == "no-store"


def test_invalid_supplied_header_rejects_public_route(client):
    response = client.post(
        "/api/access/login",
        json={"identifier": "alice@example.com", "pin": "012345"},
        headers={"Authorization": "Bearer unknown"},
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"customer": None},
        {"customer": {"firstName": " ", "lastName": "Smith", "email": "a@example.com"}},
        {"customer": {"firstName": "Alice", "lastName": "Smith", "email": "invalid"}},
    ],
)
def test_invalid_registration(client, body):
    response = client.post("/api/customer/register", json=body)
    assert response.status_code == 400
    assert response.headers["Cache-Control"] == "no-store"


def test_malformed_json_and_missing_query(client):
    assert (
        client.post(
            "/api/customer/register", content="{", headers={"Content-Type": "application/json"}
        ).status_code
        == 400
    )
    customer = register(client)
    assert client.get("/api/customer/get", headers=headers(customer)).status_code == 400
    assert (
        client.get(
            "/api/customer/get", params={"customerNumber": "bad"}, headers=headers(customer)
        ).status_code
        == 400
    )


def test_openapi_documents_all_routes_and_bearer_auth(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert len(schema["paths"]) == 10
    for path, operations in schema["paths"].items():
        for operation in operations.values():
            assert "422" not in operation["responses"]
            if path not in ("/api/customer/register", "/api/access/login"):
                assert operation["security"] == [{"HTTPBearer": []}]
    assert (
        schema["components"]["schemas"]["AccountDto"]["properties"]["balance"]["type"] == "number"
    )
    assert client.get("/docs").status_code == 200
    assert client.get("/missing").status_code == 404


def test_unexpected_failure_does_not_disclose_internal_error():
    app = create_app()

    def failing_dependency():
        raise RuntimeError("Internal credential or database details")

    app.dependency_overrides[get_customer_service] = failing_dependency
    with TestClient(app, raise_server_exceptions=False) as http:
        response = http.post(
            "/api/customer/register",
            json={
                "customer": {"firstName": "Alice", "lastName": "Smith", "email": "a@example.com"}
            },
        )
    assert response.status_code == 500
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["content-type"] == "application/problem+json"
    assert "Internal credential" not in response.text
