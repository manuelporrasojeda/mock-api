# Mock API

A Python mock API built with FastAPI for local integration.

## Features

- `POST /oauth2/v1/tokens` for systemic token generation
- `POST /customTokenOamCustomerUser/v1/token` for user token generation
- `GET /{path_name}/v5/status` to serve JSON fixtures from disk
- Async endpoints prepared for artificial delays in test scenarios
- Special mocked users such as `noexistinguser` and `slowuser`
- `uv`-based project management
- Docker support
- Basic pytest coverage

## Project structure

```text
.
├── app
│   ├── api
│   │   └── routes.py
│   ├── core
│   │   └── settings.py
│   ├── data
│   │   └── directories to serve data.
│   ├── models
│   │   └── schemas.py
│   ├── services
│   │   ├── data_loader.py
│   │   ├── mock_behavior_service.py
│   │   └── token_service.py
│   └── main.py
├── tests
│   ├── conftest.py
│   ├── test_api.py
│   └── test_services.py
├── Dockerfile
└── pyproject.toml
```

_NOTE_: data directory is able to serve json fixture data to different `path_name` endpoint. Just name the directory as `path_name`, and each json as user_id (`nationalIdentityCardNr`) and it will be delivered as API response,

## Requirements

- Python 3.12+
- `uv`

## Run locally

```bash
uv sync
uv run uvicorn app.main:app --reload
```

The API will be available at:

- `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## Run tests

```bash
uv sync
uv run pytest
```

## Example calls

### 1. System token

```bash
curl --location 'http://127.0.0.1:8000/oauth2/v1/tokens' \
--header 'Authorization: Basic ZGVtbzpkZW1v' \
--header 'Content-Type: application/x-www-form-urlencoded;charset=UTF-8' \
--header 'oam: MDAz' \
--header 'app-key: demo-app' \
--data-raw 'grant_type=password&username=SVC_AGVIRTUAL&password=Vivo@2025&scope=ServiceAccount.Profile'
```

### 2. User token

```bash
curl --location 'http://127.0.0.1:8000/customTokenOamCustomerUser/v1/token' \
--header 'Content-Type: application/json' \
--header 'Authorization: sys_mock_token' \
--data '{"userid":"12345678A"}'
```

### 3. Data payload

```bash
curl --location 'http://127.0.0.1:8000/agreement/v5/status?accountId=ACC-001&newFieldsInd=true&nationalIdentityCardNr=12345678A' \
--header 'Authorization: Bearer user_token'
```

## Special scenarios

The project includes special identities to simulate upstream behaviors.

### User token endpoint

- `userid = noexistinguser` → returns a mocked upstream `500`
- `userid = slowuser` → delays the response before returning a valid token

### Data endpoint

- `nationalIdentityCardNr = slowuser` → delays the response before returning the JSON fixture

You can extend these scenarios in `app/services/mock_behavior_service.py`.

## Configuration

Environment variables use the `MOCK_API_` prefix.

- `MOCK_API_TOKEN_EXPIRATION_SECONDS=3600`
- `MOCK_API_DEFAULT_DELAY_SECONDS=60`

## Docker

Build the image:

```bash
docker build -t mock-api .
```

Run the container:

```bash
docker run --rm -p 8000:8000 mock-api
```
