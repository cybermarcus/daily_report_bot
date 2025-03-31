## Автоматизация отправки ежедневного отчета с помощью Telegram-бота и Airflow
В проекте с помощью Telegram-бота реализована отправка в чат отчета для мониторинга основных метрик приложения:
- показатель среднего количества активных пользователей за всё время и сравнение с показателем предыдущего дня
- какая часть пользователей использует оба сервиса (новостную ленту и мессенджер) и сравнение с показателем предыдущего дня
- сравнение с помощью графика барплот изменения retention 7 дня по типу источника пользователей (органические пользователи и пользователи пришедшие после рекламных компаний)   

### Структура проекта
```
daily_report_bot/
├── config/
├── dags/
│   ├── CH.py
│   └── daily_report.py
├── logs/
├── plugins/
├── .env
├── .gitignore
├── airflow.sh
├── docker-compose.yaml
├── README.md
├── Dockerfile
└── requirements.txt
```
- Перед развертыванием Airflow создаются каталоги:
  -  `config` ─ для конфигурационных файлов
  -  `dags` ─ каталог для хранения файлов с DAG (directed acyclic graph)
  -  `logs` ─ для логов отработки всех задач
  -  `plugins` ─ для расширения функциональных возможностей Airflow
- `CH.py`— в модуле реализован класс Getch, объект которого подключается к базе данных и отправляет запрос, используя в качестве параметров для подключения переменные окружения
- `daily_report.py` — с помощью python-декораторов задается DAG и внутри него несколько task, вычисляющие метрики приложения. Финальный task с помощью Telegram-бота и асинхронной функции отправляет отчёт по приложению.
- `.env` — переменные окружения для подключения к БД и Telegram-боту
- `.gitignore` — описаны файлы, которые должен игнорировать git
- `airflow.sh` — bash-скрипт, с помощью которого можно легко попасть в оболочку bash или python локально развернутого Airflow (команды `airflow.sh bash` или `airflow.sh python`). Скрипт предоставляется разработчиками Airflow. Использовал его для проверки, что на сервер Airflow успешно прокинулись переменные окружения и установились необходимые python-пакеты.
- `docker-compose.yaml` — файл с инструкциями к Docker Compose для развертывания мультиконтейнерного приложения с Airflow. Предоставляется разработчиками Airflow. Для данного проекта дополнен инструкцией built и переменными окружения, которые прокидываются из файла `.env` на сервер Airflow.
- `Dockerfile` — допоняет оригинальный образ инструкцией по установке из файла `requirements.txt` в Airflow нужных зависимостей для работы скрипта `daily_report.py`
- `requirements.txt` — файл с зависимостями

### Развертывание проекта
Для развертывания проекта должен быть установлен Docker и Docker Compose.
1. С помощью BotFather создается Telegram-бот. Token бота и id чата, в который будет отправляться отчет, сохраняются в файл с переменными окружения. Туда же сохраняются параметры для подключения к БД.
2. В директории с проектом запускается команда `docker compose build`, которая собирает образы, определённые в файле docker-compose.yaml и Dockerfile
3. Командой `docker compose up -d` поднимаем контейнеры в фоновом режиме
4. После успешного поднятия контейнеров интерфейс Airflow будет развернут на http://localhost:8080/
5. Авторизуемся (по умолчанию логин и пароль — airflow), находим в списке необходимый DAG и активируем его. Здесь же можно будет следить за выполнением всех task.

![Airflow_interface](https://s329vlx.storage.yandex.net/rdisk/b9332c5722ce6c5d008502aa8a6a8a1721b3c8ea316ebe3f8f8cfc4c8581ce46/67e8793f/bdfbaxGJJwkhYzrYQCLcaxqqjAueNnZGM8802MW-1Hg9-6we_uWFst5JHmKk9vtqpKiOnNlGtb_5bBOHhDm_zQ==?uid=482408657&filename=Airflow_interface.png&disposition=inline&hash=&limit=0&content_type=image%2Fpng&owner_uid=482408657&fsize=193451&hid=df85ab2f86a23441dc508e75a724daf5&media_type=image&tknv=v2&etag=40c4c1504531a797b8d8f9b954ba8a91&ts=6318304118dc0&s=c037ee003b690be7a5248f1fa8033d27d47259f43434427d0f9eaa9e9911250c&pb=U2FsdGVkX1_J0KZNaH_Ep7hKotpV-3BtBBRNcPzkmvCZYroVrVdSrhpXjGeQywMGfKQgR_9gAmuDbe9ageipxrvzBg_N2BVjAOCOId2lh0A)

![Telegram_screenshot](https://s43klg.storage.yandex.net/rdisk/7dd5d1963d186bd72786ae4454c7eb92461aa1a576da43f65d270f2f9460f99c/67eb1d24/bdfbaxGJJwkhYzrYQCLca-5IKwqR9yTVYn81aYbXLMMz5lKXouCv7yi1Wd8Yh3HUE-17vmZpnSeNHv6zhV_HRg==?uid=482408657&filename=Telegram_screenshot.png&disposition=inline&hash=&limit=0&content_type=image%2Fpng&owner_uid=482408657&fsize=212593&hid=e8500de2b6aee2d910d2e496223b8b15&media_type=image&tknv=v2&etag=a4040b41ef6d83768d45c3d476dc3ed5&ts=631ab4d669100&s=4b1e50420eb281bce53ca5c0c45012ceda20afc74ca24b7d5e4819827625e1e6&pb=U2FsdGVkX18YumG514YKyVLeCug4g9Z77JudzV1fyrShLjWSVz7gNc1knAWNfs8YUnM1ko-2ZDQFz3DNZFdGqWLkFOx9-6muDucaVlKKBL0)
### Использованные инструменты
Docker, Airflow 2.0, SQL, ClickHouse, python, pandas, seaborn, asyncio, API Telegram

### Описание данных
Все данные находятся в табличном виде в ClickHouse

**feed_actions**
|Название атрибута|Тип атрибута|
|-|--------|
| user_id | UInt32 |
| post_id | UInt32 |
| action | String |
| time | DATETIME |
| gender | Int8 |
| age | Int16 |
| country | String |
| city | String |
| os | String |
| source | String |
| exp_group | Int8 |

**message_actions**
|Название атрибута|Тип атрибута|
|-|--------|
| user_id | UInt32 |
| receiver_id | UInt32 |
| time | DATETIME |
| source | String |
| exp_group | Int8 |
| gender | Int8 |
| age | Int16 |
| country | String |
| city | String |
| os | String 
