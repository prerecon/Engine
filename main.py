import discord
from discord.ext import commands
from discord.ui import Button, View
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# --- Конфигурация ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Настраиваем Gemini
genai.configure(api_key=GOOGLE_API_KEY)
# Используем актуальную модель, например, gemini-2.5-flash или gemini-1.5-flash
model = genai.GenerativeModel('gemini-2.5-flash')

# --- Настройка бота ---
intents = discord.Intents.default()
intents.message_content = True  # ВАЖНО: включает чтение сообщений

bot = commands.Bot(command_prefix="!", intents=intents)

# --- Команда /панель ---
@bot.tree.command(name="панель", description="Отправляет панель управления с кнопкой")
async def panel(interaction: discord.Interaction):
    # Создаем Embed (красивое встраиваемое сообщение)
    embed = discord.Embed(
        title="🤖 Engine - AI Ассистент",
        description="Нажмите на кнопку ниже, чтобы создать личный чат с нейросетью Gemini.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Powered by Gemini")

    # Создаем кнопку и View
    view = discord.ui.View(timeout=None)  # timeout=None означает, что кнопка не исчезнет
    button = discord.ui.Button(label="Создать чат", style=discord.ButtonStyle.green, custom_id="create_chat")

    # Привязываем функцию-обработчик к кнопке
    button.callback = create_chat_callback
    view.add_item(button)

    await interaction.response.send_message(embed=embed, view=view)

# --- Обработчик нажатия на кнопку ---
async def create_chat_callback(interaction: discord.Interaction):
    guild = interaction.guild
    user = interaction.user

    # Проверяем, есть ли уже канал у пользователя
    channel_name = f"engine-{user.name}".lower().replace(" ", "-")
    existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
    if existing_channel:
        await interaction.response.send_message(f"У вас уже есть чат: {existing_channel.mention}", ephemeral=True)
        return

    # Создаем канал
    # Важно: правильно передавать аргументы в callback (interaction, button)
    # Согласно практике, лучше создавать канал с правами по умолчанию, а затем выдавать доступ.
    # Для простоты создадим публичный канал, но с ограничением по роли everyone.
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    try:
        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            topic=f"Личный чат с Engine для {user.display_name}"
        )
        await interaction.response.send_message(f"Чат создан! Перейдите в {channel.mention}", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("У бота нет прав на создание каналов. Пожалуйста, проверьте права.", ephemeral=True)

# --- Обработка сообщений в личных каналах ---
@bot.event
async def on_message(message):
    # Игнорируем сообщения от самого бота
    if message.author == bot.user:
        return

    # Проверяем, является ли канал личным чатом (по названию)
    if message.channel.name.startswith("engine-"):
        # Показываем, что бот "печатает"
        async with message.channel.typing():
            try:
                # Отправляем запрос в Gemini
                response = await model.generate_content_async(message.content)
                response_text = response.text

                # Оборачиваем ответ в блок кода
                formatted_response = f"```\n{response_text}\n```"

                # Отправляем ответ (если текст длинный, Discord может разбить его)
                if len(formatted_response) <= 2000:
                    await message.channel.send(formatted_response)
                else:
                    # Если текст слишком длинный, отправляем частями
                    for i in range(0, len(formatted_response), 2000):
                        await message.channel.send(formatted_response[i:i+2000])

            except Exception as e:
                # Обработка ошибок API
                await message.channel.send(f"```\nОшибка при обращении к Gemini: {e}\n```")

    # Не забываем обрабатывать команды
    await bot.process_commands(message)

# --- Синхронизация слэш-команд при запуске ---
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Синхронизировано {len(synced)} команд.")
    except Exception as e:
        print(f"Ошибка синхронизации команд: {e}")
    print(f"Бот {bot.user} готов к работе!")

# --- Запуск ---
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
