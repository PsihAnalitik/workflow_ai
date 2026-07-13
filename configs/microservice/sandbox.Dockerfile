# Образ песочницы и рантайма цеха «микросервис»: workshop-microservice:latest
# Сборка: docker build -t workshop-microservice:latest -f configs/microservice/sandbox.Dockerfile .
# WHY uvicorn: тестам (pytest + TestClient) сервер не нужен, но serve-команда пакета
# (uvicorn api:app) выполняется в ЭТОМ же образе — без uvicorn продукт не стартует
# (дефект найден живым запуском продукта 08.07.2026).
FROM python:3.14-slim
RUN pip install --no-cache-dir pytest fastapi httpx pymorphy3 pymorphy3-dicts-ru uvicorn
