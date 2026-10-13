import pytest
from fastapi.testclient import TestClient

from banking.api.main import create_app


@pytest.fixture
def client():
    with TestClient(create_app()) as http:
        yield http


def register(client, email="alice@example.com"):
    response = client.post(
        "/api/customer/register",
        json={"customer": {"firstName": " Alice ", "lastName": " Smith ", "email": email}},
    )
    assert response.status_code == 201, response.text
    return response.json()


def headers(customer):
    return {"Authorization": f"Bearer {customer['sessionToken']}"}


def create_account(client, customer, account_type="CURRENT"):
    response = client.post(
        "/api/account/create", json={"accountType": account_type}, headers=headers(customer)
    )
    assert response.status_code == 201, response.text
    return response.json()["account"]


def move_money(client, customer, operation, target, amount, source=None):
    transaction = {
        "transactionType": {"deposit": "DEPOSIT", "withdraw": "WITHDRAWAL", "transfer": "TRANSFER"}[
            operation
        ],
        "amount": amount,
        "targetAccountNumber": target["accountNumber"],
    }
    if source is not None:
        transaction["sourceAccountNumber"] = source["accountNumber"]
    return client.post(
        f"/api/account/{operation}", json={"transaction": transaction}, headers=headers(customer)
    )
