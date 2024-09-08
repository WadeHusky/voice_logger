# voice_logger
Бот, который логгирует голосовые каналы в дискорде. 
## Установка зависимостей:
```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```
## Что требуется для запуска ботов?
Создать файл .env:
```bash
touch .env
```
Заполнить следующие переменные любым текстовым редактором:
* token = "API токен дискорд бота"
* cname = "Название текстового канала, в котором будет работать бот"
* role = "Название роли, у которого будет доступ к командам бота"
---
Запустить бота в фоне командой:
```bash
nohup python3 ds_bot.py &
```
Запустить бота:
```bash
python3 ds_bot.py
```
## Основная команда бота
* !help
