import discord
from discord.ext import commands
import json
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz  # Импортируем pytz
import os
from dotenv import load_dotenv
from pathlib import Path
dotenv_path = f"{Path(__file__).parent.resolve()}/.env"
load_dotenv(dotenv_path=dotenv_path)

intents = discord.Intents.default()
intents.voice_states = True  # Включаем интенты для отслеживания голосовых состояний
intents.messages = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Путь к файлу для хранения истории
history_file = 'logs/voice_history.json'
# Устанавливаем временную зону для Москвы
moscow_tz = pytz.timezone('Europe/Moscow')
backup_file = f'logs/voice_history_{datetime.datetime.now(moscow_tz).date()}.json'
# Словарь для хранения истории подключений и отключений пользователей по серверам и каналам
voice_history = {}

#===================[WORK WITH DB]======================================
def load_voice_history():
    """Загружает историю голосовых подключений из файла."""
    global voice_history
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            try:
                voice_history = json.load(f)
            except:
                voice_history = {}

def save_voice_history():
    """Сохраняет историю голосовых подключений в файл."""
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(voice_history, f, ensure_ascii=False, indent=4)

def backup_voice_history():
    """Создает резервную копию истории голосовых подключений."""
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            data = f.read()
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(data)
        with open(history_file, 'w', encoding='utf-8') as f:
            f.write("{}")
#===================[WORK WITH DB]======================================

@bot.event
async def on_ready():
    load_voice_history()  # Загружаем историю при запуске бота
    print(f'Бот {bot.user} запущен!')
    # Настраиваем планировщик
    scheduler = AsyncIOScheduler()
    scheduler.add_job(backup_voice_history, 'cron', hour=17, minute=47)  # Запланировать на 00:00
    scheduler.start()

@bot.event
async def on_voice_state_update(member, before, after):
    guild_id = str(member.guild.id)  # Получаем ID сервера как строку
    channel_id = str(after.channel.id) if after.channel else str(before.channel.id) if before.channel else None

    # Инициализируем историю для сервера, если её нет
    if guild_id not in voice_history:
        voice_history[guild_id] = {}

    # Инициализируем историю для канала, если её нет
    if channel_id not in voice_history[guild_id]:
        voice_history[guild_id][channel_id] = []

    # Если пользователь подключился к голосовому каналу
    if before.channel is None and after.channel is not None:
        join_time = datetime.datetime.now(moscow_tz)  # Получаем текущее время в Москве
        voice_history[guild_id][channel_id].append({
            'user_id': member.id,
            'join_time': join_time.isoformat(),  # Сохраняем время в формате ISO
            'leave_time': None
        })
        save_voice_history()  # Сохраняем историю после обновления

    # Если пользователь отключился от голосового канала
    elif before.channel is not None and after.channel is None:
        leave_time = datetime.datetime.now(moscow_tz)  # Получаем текущее время в Москве
        for record in voice_history[guild_id][channel_id]:
            if record['user_id'] == member.id and record['leave_time'] is None:
                record['leave_time'] = leave_time.isoformat()  # Обновляем последнее подключение
                break
        save_voice_history()  # Сохраняем историю после обновления



@bot.command(name="log")
async def _log(ctx, channel_name: str):
    """Команда для вывода логов о подключениях и отключениях пользователей в определённом голосовом канале за день."""
    load_voice_history()
    guild_id = str(ctx.guild.id)  # Получаем ID сервера как строку

    # Получаем список всех голосовых каналов на сервере
    voice_channels = {channel.name: str(channel.id) for channel in ctx.guild.voice_channels}

    # Проверяем, существует ли канал с таким именем
    channel_id = voice_channels.get(channel_name)
    if not channel_id:
        await ctx.send(f"Канал с именем '{channel_name}' не найден.")
        return

    # Проверяем, есть ли записи для этого канала в истории
    if guild_id not in voice_history or channel_id not in voice_history[guild_id]:
        await ctx.send("Нет записей о подключениях и отключениях.")
        return

    today = datetime.datetime.now(moscow_tz).date()
    log_messages = []

    for record in voice_history[guild_id][channel_id]:
        user_id = record['user_id']
        join_time = datetime.datetime.fromisoformat(record['join_time'])  # Преобразуем обратно в datetime
        leave_time = record['leave_time']

        try:
            member = await ctx.guild.fetch_member(user_id)  # Получаем участника по ID
            member_mention = member.mention
        except discord.NotFound:
            await ctx.send('Пользователь не найден.')
            continue  # Пропускаем, если пользователь не найден
        except discord.Forbidden:
            await ctx.send('У меня нет прав для получения информации о пользователе.')
            continue  # Пропускаем, если нет прав
        except discord.HTTPException:
            await ctx.send('Произошла ошибка при получении информации о пользователе.')
            continue  # Пропускаем, если произошла ошибка

        if leave_time is None:  # Если пользователь все еще в голосовом канале
            duration = datetime.datetime.now(moscow_tz) - join_time      
            log_messages.append(
                f"{member_mention} подключен к каналу с {join_time.strftime('%Y-%m-%d %H:%M:%S')}\n"\
                f"(продолжительность: {duration})\n")
        else:
            leave_time = datetime.datetime.fromisoformat(leave_time)  # Преобразуем обратно в datetime
            if leave_time.date() == today:  # Проверяем, что отключение произошло сегодня
                duration = leave_time - join_time
                log_messages.append(
                    f"{member_mention} подключен к каналу с {join_time.strftime('%Y-%m-%d %H:%M:%S')}\n"\
                    f"отключен с {leave_time.strftime('%Y-%m-%d %H:%M:%S')}"\
                    f"\n(продолжительность: {duration})\n"
                )

    if log_messages:
        await ctx.send("\n".join(log_messages))
    else:
        await ctx.send(f"Нет записей о подключениях и отключениях в канале '{channel_name}' за сегодня.")


bot.run(os.getenv("token"))
