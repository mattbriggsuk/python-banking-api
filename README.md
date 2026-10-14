# Python Banking API

A FastAPI port of the Java Banking API playground.

## Run locally

Python 3.12 or later is required. From this repository in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn banking.api.main:app --host 127.0.0.1 --port 8080 --reload
```

The API runs at `http://localhost:8080`. Interactive Swagger documentation is at
`http://localhost:8080/docs`, with the OpenAPI schema at `/openapi.json`.
Registration and login return a `sessionToken`; paste that token into Swagger's
**Authorize** dialog to try protected endpoints.

On macOS/Linux use `.venv/bin/python` in place of `.\.venv\Scripts\python.exe`.
For an installation matching the verified dependency versions, add
`-c requirements.lock` to the `pip install` command.

## Separation of concerns

```text
src/banking/
  api/                 FastAPI app, routes, HTTP DTOs, auth dependencies, errors
  business/            Customer, access, and account business services
  repository/          Thread-safe in-memory persistence adapters
  domain/              Dataclasses, enums, exceptions, repository/service Protocols
  utils/               Luhn numbers, PIN hashing, UTC clock, transaction validation
  bootstrap.py         Composition root that connects adapters and services
tests/                 HTTP, business, utility, and architecture tests
.client/http/          Ordered request examples copied from the Java project
```

| Layer | Responsibility and dependencies |
|---|---|
| `api` | Validates HTTP input, maps DTOs to/from domain objects, authenticates requests, invokes service contracts, and maps domain failures to HTTP. |
| `business` | Applies registration, authentication, ownership, account-state, and money-movement rules. Depends on domain contracts and utilities. |
| `repository` | Implements domain persistence contracts for customers, PIN hashes, sessions, and accounts. |
| `domain` | Defines framework-independent models and contracts. Imports only Python's standard library. |
| `utils` | Small shared functions with no HTTP or persistence dependencies. |

Python `Protocol` contracts serve the role of Java interfaces. Constructors inject
repository contracts into services. `bootstrap.py` selects concrete implementations,
and FastAPI dependencies supply service contracts to routes. Routes contain no
balance calculations or direct repository access.

HTTP DTOs live in `api/schemas.py`, keeping Pydantic and HTTP validation out of the
domain. Immutable customer/account dataclasses prevent a failed write from changing
stored objects through a shared reference. A repository transaction context holds
one lock across each account read/validate/write operation; transfers publish both
updated account snapshots together. This protects concurrent requests within one
process and is not a durable database transaction.

`create_app(services=...)` accepts another service container for isolated tests or
alternative implementations. A future database adapter should implement the domain
repository contracts, provide real transactions through `transaction()`, and be
selected in `bootstrap.py`.

## Endpoints

| Method | Route | Success | Authentication |
|---|---|---|---|
| POST | `/api/customer/register` | 201 | Public |
| POST | `/api/access/login` | 200 | Public |
| POST | `/api/access/logout` | 204, empty body | Bearer token |
| GET | `/api/customer/get?customerNumber=...` | 200 | Own customer |
| GET | `/api/customer/accounts?customerNumber=...` | 200 | Own customer |
| POST | `/api/account/create` | 201 | Signed-in customer |
| POST | `/api/account/close` | 202 | Own account |
| POST | `/api/account/deposit` | 200 | Own target account |
| POST | `/api/account/withdraw` | 200 | Own target account |
| POST | `/api/account/transfer` | 200 | Own source account |

Transfers can credit another customer's account. Account creation accepts
`CURRENT`, `SAVINGS`, and `CREDIT`. Omitting `accountType` defaults to `CURRENT`;
explicit `null` or an unknown value returns 400. All types currently use the same
balance rules: no overdraft, and only a zero-balance account can close.

Register a customer:

```json
{
  "customer": {
    "firstName": "Taylor",
    "lastName": "Reed",
    "email": "taylor.reed@example.com"
  }
}
```

The registration response contains `customer`, a six-digit `pin`, and `sessionToken`.
Keep the PIN as a string to preserve leading zeros. Login accepts either the email
or customer number:

```json
{"identifier": "taylor.reed@example.com", "pin": "012345"}
```

Send `Authorization: Bearer <sessionToken>` on protected requests. Sessions expire
after 30 minutes and logout revokes the supplied session. As in Java, a supplied
invalid Authorization header is rejected even on public endpoints. Email addresses
are trimmed, lowercased, and unique without regard to case.

Create an account with `{"accountType": "SAVINGS"}`. Use its returned account number
to deposit:

```json
{
  "transaction": {
    "transactionType": "DEPOSIT",
    "amount": 100.00,
    "targetAccountNumber": "<returned 16-digit account number>"
  }
}
```

Withdraw uses `WITHDRAWAL`; transfer uses `TRANSFER` and also requires
`sourceAccountNumber`. Close accepts `{"accountNumber": "<account number>"}`.
The [HTTP request examples](.client/http) include complete sequences.

## Money, credentials, and errors

Balances and amounts use `Decimal`, including incoming JSON numeric parsing.
Responses preserve Java's JSON **number** representation using a Decimal-aware
serializer; no float conversion occurs on the server. Clients should also use
decimal-safe parsing when working with money. Amounts must be positive, have at
most two decimal places, and contain at most 16 integer digits. Customer/account
numbers have 16 ASCII digits and a valid Luhn checksum. Transaction dates are
assigned by the server in UTC, replacing a client-supplied date.

PINs are generated with `secrets`, returned only at registration, and stored as
salted PBKDF2-HMAC-SHA256 hashes with 600,000 iterations. Hashes use the Java
`base64(salt):base64(hash)` format. Tokens contain 256 random bits. Customer DTOs
contain no credentials, and request validation errors never echo rejected input.

Expected errors use `application/problem+json` with `type`, `title`, `status`,
`detail`, and `instance`. Responses include `Cache-Control: no-store`.

| Condition | Status |
|---|---|
| Invalid request fields, JSON, checksums, or transaction instructions | 400 |
| Missing, invalid, expired, or revoked session; incorrect login credentials | 401 |
| Access to another customer's details or accounts | 403 |
| Missing customer or account | 404 |
| Duplicate email, closed account, insufficient funds, or nonzero balance on close | 409 |

Validation deliberately returns 400 to match Java, overriding FastAPI's default
422. Missing or null login PINs are rejected as invalid requests. Email syntax is
validated with Pydantic's email validator, whose edge cases may differ from Java's
Jakarta validator. Unknown JSON properties are ignored, as in the Java API.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m ruff format --check src tests
```

Tests cover complete HTTP flows, authorization, request/error contracts, session
expiry and revocation, hashing, validation, rejected writes, concurrent balance
updates, exact numeric JSON, and layer dependency boundaries. GitHub Actions runs
these checks on Python 3.12 and 3.14.

## Storage scope

Like the Java playground, this is a demonstration API. All data disappears on
restart or development reload. Run a **single worker**: multiple workers would
each have separate customers, sessions, and balances. Persistent storage, a
ledger, idempotency, rate limiting, and operational banking controls are outside
this port's scope.
