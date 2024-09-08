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
bot.remove_command('help')

# Путь к файлу для хранения истории
history_file = 'logs/voice_history.json'
# Устанавливаем временную зону для Киева
kiev_tz = pytz.timezone('Europe/Kiev')
backup_file = f'logs/voice_history_{datetime.datetime.now(kiev_tz).date()}.json'
# Словарь для хранения истории подключений и отключений пользователей по серверам и каналам
voice_history = {}
logging_enabled = False  # Переменная для отслеживания состояния логирования
cname = os.getenv("cname")

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
    scheduler.add_job(backup_voice_history, 'cron', hour=21, minute=00)  # Запланировать на 00:00
    scheduler.start()

@bot.event
async def on_voice_state_update(member, before, after):
    global logging_enabled
    if not logging_enabled: return

    guild_id = str(member.guild.id)  # Получаем ID сервера как строку
    channel_id = str(after.channel.id) if after.channel else str(before.channel.id) if before.channel else None

    # Инициализируем историю для сервера, если её нет
    if guild_id not in voice_history:
        voice_history[guild_id] = {}

    # Инициализируем историю для канала, если её нет
    if channel_id not in voice_history[guild_id]:
        voice_history[guild_id][channel_id] = {}  # Убедитесь, что это словарь
    # Если пользователь подключился к голосовому каналу
    if before.channel is None and after.channel is not None:
        join_time = datetime.datetime.now(kiev_tz)  # Получаем текущее время в Киеве
        user_id_str = str(member.id)
        # Проверяем, есть ли уже запись для этого пользователя
        if user_id_str not in voice_history[guild_id][channel_id]:
            voice_history[guild_id][channel_id][user_id_str] = {
                'user_id': member.id,
                'join_time': join_time.isoformat(),  # Сохраняем время в формате ISO
                'leave_time': None,
                'duration': 0  # Инициализируем продолжительность
            }
        else:
            record = voice_history[guild_id][channel_id][user_id_str]
            if record['leave_time'] is None:  # Если пользователь уже в канале
                # Обновляем duration, сохраняя join time
                ...
            else:
                duration = record["duration"]
                # Если leave_time уже установлен, создаем новую запись
                voice_history[guild_id][channel_id][user_id_str] = {
                    'user_id': member.id,
                    'join_time': join_time.isoformat(),
                    'duration': duration,
                    'leave_time': None,
                }
        save_voice_history()  # Сохраняем историю после обновления

    # Если пользователь отключился от голосового канала
    elif before.channel is not None and after.channel is None:
        leave_time = datetime.datetime.now(kiev_tz)  # Получаем текущее время в Киеве
        user_id_str = str(member.id)
        if user_id_str in voice_history[guild_id][channel_id]:
            record = voice_history[guild_id][channel_id][user_id_str]
            record['leave_time'] = leave_time.isoformat()  # Обновляем время выхода
            # Обновляем продолжительность
            join_time = datetime.datetime.fromisoformat(record['join_time'])
            duration = (leave_time - join_time).total_seconds()  # Вычисляем продолжительность
            record['duration'] += duration  # Суммируем продолжительность
            save_voice_history()  # Сохраняем историю после обновления




@bot.command(name="clear")
@commands.has_role(os.getenv("role"))  # Замените "Admin" на название вашей роли
async def clear_voice_history(ctx):
    """Команда для очистки базы данных голосовой истории."""
    if (ctx.channel).name != cname: return
    global voice_history
    guild_id = str(ctx.guild.id)
    voice_history[guild_id] = {}  # Очищаем историю
    save_voice_history()  # Сохраняем изменения в файл
    await ctx.send("История голосовых подключений очищена.")

# Обработчик ошибок для команды delete
@clear_voice_history.error
async def clear_voice_history_error(ctx, error):
    if (ctx.channel).name != cname: return
    if isinstance(error, commands.MissingRole):
        await ctx.send("У вас нет прав для выполнения этой команды.")

@bot.command(name="start")
async def start_logging(ctx):
    """Команда для начала логирования голосовых каналов."""
    if (ctx.channel).name != cname: return
    global logging_enabled
    logging_enabled = True
    await ctx.send("Логирование голосовых каналов включено.")

@bot.command(name="stop")
async def stop_logging(ctx):
    """Команда для остановки логирования голосовых каналов."""
    if (ctx.channel).name != cname: return
    global logging_enabled
    logging_enabled = False
    await ctx.send("Логирование голосовых каналов отключено.")


@bot.command(name="status")
async def status_logging(ctx):
    """Команда для получения статуса логирования голосовых каналов."""
    if (ctx.channel).name != cname: return
    global logging_enabled
    await ctx.send("Логирование голосовых каналов включено." if logging_enabled else "Логирование голосовых каналов выключено.")

@bot.command(name='help', help="Команда для показа этого сообщения.")
async def custom_help(ctx):
    help_message = "Список доступных команд:\n>>> "
    for command in bot.commands:
        help_message += f"**!{command.name}** - {command.help}\n"
    await ctx.send(help_message)


@bot.command(name="log")
async def _log(ctx):
    """Команда для вывода логов о подключениях и отключениях пользователей во всех голосовых каналах за день."""
    if (ctx.channel).name != cname: return
    load_voice_history()
    guild_id = str(ctx.guild.id)  # Получаем ID сервера как строку

    # Проверяем, есть ли записи для этого сервера в истории
    if guild_id not in voice_history:
        await ctx.send("Нет записей о подключениях и отключениях.")
        return

    today = datetime.datetime.now(kiev_tz).date()
    log_messages = []

    # Проходим по всем голосовым каналам на сервере
    for channel_id, records in voice_history[guild_id].items():
        for user_id_str, record in records.items():  # Исправлено: итерируем по элементам словаря
            user_id = record['user_id']
            join_time = datetime.datetime.fromisoformat(record['join_time'])  # Преобразуем обратно в datetime
            leave_time = record['leave_time']

            try:
                member = await ctx.guild.fetch_member(user_id)  # Получаем участника по ID
                member_mention = member.mention
            except discord.NotFound:
                continue  # Пропускаем, если пользователь не найден
            except discord.Forbidden:
                continue  # Пропускаем, если нет прав
            except discord.HTTPException:
                continue  # Пропускаем, если произошла ошибка
            channel = bot.get_channel(int(channel_id))
            channel_name = channel.name
            if leave_time is None:  # Если пользователь все еще в голосовом канале
                # Получаем продолжительность из базы данных
                db_duration = record['duration']  # Продолжительность в секундах из базы данных (тип float)
                current_duration = datetime.datetime.now(kiev_tz) - join_time  # Текущая продолжительность
                total_duration = db_duration + current_duration.total_seconds()  # Суммируем продолжительности

                # Округляем общую продолжительность до ближайшей секунды
                rounded_duration = round(total_duration)
                hours, remainder = divmod(rounded_duration, 3600)
                minutes, seconds = divmod(remainder, 60)
                log_messages.append(
                    f"{member_mention} подключен к каналу {channel_name} с {join_time.strftime('%Y-%m-%d %H:%M:%S')}\n"\
                    f"(продолжительность: {hours}ч {minutes}м {seconds}с)\n"
                )
            else:
                leave_time = datetime.datetime.fromisoformat(leave_time)  # Преобразуем обратно в datetime
                if leave_time.date() == today:  # Проверяем, что отключение произошло сегодня
                    duration = record["duration"]
                    # Округляем продолжительность до ближайшей секунды
                    rounded_duration = round(duration)
                    hours, remainder = divmod(rounded_duration, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    log_messages.append(
                        f"{member_mention} подключен к каналу {channel_name} с {join_time.strftime('%Y-%m-%d %H:%M:%S')}\n"\
                        f"(продолжительность: {hours}ч {minutes}м {seconds}с)\n"
                    )

    if log_messages:
        await ctx.send("\n".join(log_messages))
    else:
        await ctx.send("Нет записей о подключениях и отключениях за сегодня.")


@bot.command(name="send")
async def _send(ctx):
    """Команда для отправки файла логов о подключениях и отключениях пользователей во всех голосовых каналах за день."""
    if (ctx.channel).name != cname: return
    load_voice_history()
    guild_id = str(ctx.guild.id)  # Получаем ID сервера как строку

    # Проверяем, есть ли записи для этого сервера в истории
    if guild_id not in voice_history:
        await ctx.send("Нет записей о подключениях и отключениях.")
        return

    today = datetime.datetime.now(kiev_tz).date()
    log_messages = []

    # Проходим по всем голосовым каналам на сервере
    for channel_id, records in voice_history[guild_id].items():
        for user_id_str, record in records.items():  # Исправлено: итерируем по элементам словаря
            user_id = record['user_id']
            join_time = datetime.datetime.fromisoformat(record['join_time'])  # Преобразуем обратно в datetime
            leave_time = record['leave_time']

            try:
                member = await ctx.guild.fetch_member(user_id)  # Получаем участника по ID
                m_name = member.name; m_d_name = member.display_name
            except discord.NotFound:
                continue  # Пропускаем, если пользователь не найден
            except discord.Forbidden:
                continue  # Пропускаем, если нет прав
            except discord.HTTPException:
                continue  # Пропускаем, если произошла ошибка
            channel = bot.get_channel(int(channel_id))
            channel_name = channel.name
            if leave_time is None:  # Если пользователь все еще в голосовом канале
                # Получаем продолжительность из базы данных
                db_duration = record['duration']  # Продолжительность в секундах из базы данных (тип float)
                current_duration = datetime.datetime.now(kiev_tz) - join_time  # Текущая продолжительность
                total_duration = db_duration + current_duration.total_seconds()  # Суммируем продолжительности

                # Округляем общую продолжительность до ближайшей секунды
                rounded_duration = round(total_duration)
                hours, remainder = divmod(rounded_duration, 3600)
                minutes, seconds = divmod(remainder, 60)
                log_messages.append(
                    f"@{m_name} ({m_d_name}) подключен к каналу {channel_name} с {join_time.strftime('%Y-%m-%d %H:%M:%S')}\n"\
                    f"(продолжительность: {hours}ч {minutes}м {seconds}с)\n"
                )
            else:
                leave_time = datetime.datetime.fromisoformat(leave_time)  # Преобразуем обратно в datetime
                if leave_time.date() == today:  # Проверяем, что отключение произошло сегодня
                    duration = record["duration"]
                    # Округляем продолжительность до ближайшей секунды
                    rounded_duration = round(duration)
                    hours, remainder = divmod(rounded_duration, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    log_messages.append(
                        f"@{m_name} ({m_d_name}) подключен к каналу {channel_name} с {join_time.strftime('%Y-%m-%d %H:%M:%S')}\n"\
                        f"(продолжительность: {hours}ч {minutes}м {seconds}с)\n"
                    )

    if log_messages:
        with open(f"logs/{guild_id}.txt", "w", encoding="utf-8") as f:
            f.write("".join(log_messages))
        with open(f"logs/{guild_id}.txt", "r") as f:
            await ctx.send("Вот ваш файл:", file=discord.File(f, 'message.txt'))
        os.system(f"rm logs/{guild_id}.txt")
    else:
        await ctx.send("Нет записей о подключениях и отключениях за сегодня.")
bot.run(os.getenv("token"))
