# Лабораторна №2 — перевірки за методичкою

Працюємо в PowerShell, у каталозі `integration-2`. Для всіх команд використовується `-p integration-lab2`. Не публікуйте значення секретів і JWT у скриншотах.

T1 — `docker compose -p integration-lab2 config`: є лише шляхи до секретів, `forecast-api` без `ports`.
T2 — `docker compose -p integration-lab2 exec orders-api env`: немає паролів і JWT-ключа.
T3 — тимчасово перейменувати `secrets/db_password`, виконати `docker compose -p integration-lab2 up -d` (очікується відмова), повернути файл. Виконувати лише на окремому тестовому проєкті.
T4 — `Invoke-WebRequest http://localhost:8001/health`: з'єднання має бути відхилене.
T5 — `POST /auth/register`: 201.
T6 — `POST /auth/login` із правильними/неправильними даними: 200/401; однаковий текст помилки для невідомого користувача і неправильного пароля.
T7 — `GET /orders` без токена: 401 та `WWW-Authenticate: Bearer`.
T8 — `POST /orders` із Bearer JWT: 201.
T9 — `PATCH /orders/{id}` із новими параметрами: 200, прогноз оновлено.
T10 — `DELETE /orders/{id}` із JWT: 204.
T11 — замінити JWT-ключ, **пересоздати** orders-api, старий токен: 401.
T12 — зупинити forecast-api, створити замовлення з JWT: 201, `predicted_price: null`.

R3.2 — ротація JWT: до/після з 200→401 для старого токена.
R3.3 — відсутній файл секрету: Compose має відмовити у старті.
R3.4 — ротація пароля БД: продемонструвати, що оновлення файлу не змінює пароль існуючої ролі; безпечно повернути робочу конфігурацію.
R3.5 — graceful degradation: зупинений forecast-api, `POST /orders` повертає 201 і `null`.
