# NFT Active New Collections Monitor (OpenSea, Blur, Magic Eden) → Telegram

Мониторит активные **новые для системы** NFT‑коллекции на маркетплейсах и шлёт сигнал в Telegram,
если за последнюю минуту у коллекции **≥ 10 продаж** на конкретном маркетплейсе.

Поддержка:
- **OpenSea** и **Blur** через агрегатор **Reservoir API** (EVM сети).
- **Magic Eden (Solana)** — best‑effort через публичный endpoint активностей (может потребовать API key).

> Определение «новая коллекция»: коллекция, которую **ваша система видит впервые** (не была в локальной базе).  
> Это практичнее, чем зависеть от нестабильных «даты создания» у разных маркетплейсов.

## Быстрый старт (Docker)

1) Скопируйте `.env.template` → `.env` и заполните:
```
RESERVOIR_API_KEY=...      # https://docs.reservoir.tools/reference/overview
TELEGRAM_BOT_TOKEN=...     # @BotFather
TELEGRAM_CHAT_ID=...       # ID чата/канала/пользователя
# Для Magic Eden (опц.):
MAGICEDEN_API_KEY=         # если есть ключ; можно оставить пустым
MAGICEDEN_API_URL=https://api-mainnet.magiceden.dev/v2/market/activities
NETWORKS=ethereum,base,polygon   # сети для Reservoir (через запятую)
THRESHOLD_PER_MINUTE=10
POLL_INTERVAL_SECONDS=15
```
2) Запуск:
```bash
docker compose up --build
```
3) Логи:
```bash
docker compose logs -f app
```

## Что именно делает сервис
- Каждые `POLL_INTERVAL_SECONDS` секунд забирает продажи за последнюю минуту.
- Отдельно по источникам (**OpenSea**, **Blur**, **MagicEden**) агрегирует продажи **по коллекциям**.
- Если у коллекции (на конкретном маркетплейсе) ≥ `THRESHOLD_PER_MINUTE` продаж/мин **и коллекция ещё не встречалась** —
  отправляет сообщение в Telegram и помечает коллекцию как виденную, чтобы не спамить повторно.
- Кэш событий защищает от двойных срабатываний при частом опросе.

## Файлы
- `src/main.py` — точка входа, оркестрация.
- `src/adapters/reservoir_adapter.py` — OpenSea/Blur (через Reservoir Sales API).
- `src/adapters/magic_eden_adapter.py` — Magic Eden (best‑effort активности «sold»).
- `src/telegram_notifier.py` — отправка сообщений.
- `src/state.py` — простая локальная БД (SQLite) для «первого появления» и дедупликации событий.
- `docker/Dockerfile`, `docker-compose.yml` — контейнеризация.
- `.env.template` — переменные окружения.

## Ограничения и заметки
- **Reservoir** покрывает OpenSea/Blur на EVM сетях и даёт фильтр `source=opensea.io|blur.io`.
- **Magic Eden (Solana)**: публичные эндпоинты могут меняться/троттлить. При наличии ключа
  укажите `MAGICEDEN_API_KEY` — заголовок `x-api-key` автоматически добавится.
  Эндпоинт в `.env` можно менять без перекомпиляции.
- «Новая коллекция» — относительно локальной БД. Если хотите «сбрасывать» состояние — удалите файл `data/state.db`.
- При желании можно добавить WebSocket‑стримы (OpenSea Stream, Magic Eden WS) — каркас кода позволяет.

## Локальный запуск без Docker
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.template .env  # и заполните
python src/main.py
```

## Лицензия
MIT
