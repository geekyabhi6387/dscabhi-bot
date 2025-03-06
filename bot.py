import discord 
import asyncio
from discord.ext import tasks, commands
from discord import app_commands
from os import environ
import json
from datetime import datetime, timezone, timedelta
import pytz
from dotenv import load_dotenv
from google import genai
from google.genai import types
load_dotenv()

api = environ["api_key"]
token = environ["TOKEN"]
guild_id = environ["guild_id"]
REMINDER_FILE = "reminders.json"

aiclient = genai.Client(api_key=api)
sys_instruct="You are a discord bot which is meant to reply to users chatting in the respective server channels. However you are only allowed to reply in 1800 characters or less because that's the discord chat limit, so always check your response to be in limit"

def load_reminders():
    try:
        with open("reminders.json", "r") as file:
            data = file.read().strip()
            if not data:
                return []
            return json.loads(data)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        print("JSON file is invalid or corrupted. Resetting to empty list.")
        return []


def save_reminders(reminders):
    with open(REMINDER_FILE, "w") as file:
        json.dump(reminders, file, indent=4)


class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')

        try:
            guild = discord.Object(id=guild_id)
            syncedGlobal = await self.tree.sync()
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands to guild {guild.id}')
            print(f'Synced {len(syncedGlobal)} commands globally')

        except Exception as e:
            print(f'Error syncing commands: {e}')
        
        self.reminder_task.start()

    async def on_message(self, message):
        print(f'Message from {message.author}: {message.content}')

        if message.author == client.user:
            return
        
        if message.content.startswith("!"):
            await self.process_commands(message)
            return

        response = aiclient.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
        system_instruction=sys_instruct),
        contents=[message.content]
            )

        gemini_response = response.text

        await message.channel.send(gemini_response)
    
    @tasks.loop(seconds=60)
    async def reminder_task(self):
        now = datetime.now(pytz.UTC)
        reminders = load_reminders()
        to_remove = []

        for index, reminder in enumerate(reminders):
            reminder_time = datetime.fromisoformat(reminder["reminder_time"])

            if now >= reminder_time:
                channel = self.get_channel(reminder["channel_id"])
                if channel:
                    await channel.send(
                        f"⏰ Reminder for <@{reminder['user_id']}>: {reminder['message']}"
                    )
                to_remove.append(index)

        if to_remove:
            reminders = [rem for idx, rem in enumerate(reminders) if idx not in to_remove]
            save_reminders(reminders)


intents  = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix="!", intents=intents)

GUILD_ID = discord.Object(id=guild_id)

@client.tree.command(name="ping", description="Shows Latency", guild=GUILD_ID)
async def ping(interaction: discord.Interaction):
    latency = round(client.latency * 1000, 2)
    await interaction.response.send_message(f'Latency: {latency}ms')

# @client.tree.command(name="remindme", description="Set a reminder")
# async def remindme(interaction: discord.Interaction):
#     await interaction.response.send_message(f'Reminder')

@client.tree.command(name="remind", description="Set a reminder at a specific date/time in a given timezone.",guild=GUILD_ID)
@app_commands.describe(
    date="Date in YYYY-MM-DD format",
    time="Time in HH:MM (24-hour format)",
    timezone_name="Timezone (e.g. Asia/Kolkata, America/New_York)",
    message="Reminder message"
)
async def remind(interaction: discord.Interaction, date: str, time: str, timezone_name: str, message: str):
    date = date.strip()
    time = time.strip()
    timezone_name = timezone_name.strip()
    
    print(f"[DEBUG] Received Date='{date}', Time='{time}', Timezone='{timezone_name}'")

    if timezone_name not in pytz.all_timezones:
        await interaction.response.send_message(
            f"⚠️ Invalid timezone '{timezone_name}'. Check spelling or use a valid IANA timezone name.",
            ephemeral=True
        )
        return

    try:
        user_time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        print(f"[DEBUG] Parsed datetime object: {user_time}")

        user_timezone = pytz.timezone(timezone_name)
        try:
            localized_time = user_timezone.localize(user_time)
        except ValueError as e:
            print(f"[DEBUG] localize() error: {e}")
            await interaction.response.send_message(
                f"⚠️ Timezone error: {e}",
                ephemeral=True
            )
            return

        reminder_time_utc = localized_time.astimezone(pytz.UTC)
        print(f"[DEBUG] Localized time in UTC: {reminder_time_utc.isoformat()}")

        now_utc = datetime.now(pytz.UTC)
        if reminder_time_utc <= now_utc:
            await interaction.response.send_message(
                "⚠️ That time is in the past! Please provide a future date and time.",
                ephemeral=True
            )
            return

        reminder = {
            "user_id": interaction.user.id,
            "channel_id": interaction.channel_id,
            "reminder_time": reminder_time_utc.isoformat(),
            "message": message
        }
        reminders = load_reminders()
        reminders.append(reminder)
        save_reminders(reminders)

        await interaction.response.send_message(
            f"✅ Reminder set for {localized_time.strftime('%Y-%m-%d %H:%M %Z')} - `{message}`",
            ephemeral=True
        )

    except ValueError as e:
        print(f"[DEBUG] Date/time parsing error: {e}")
        await interaction.response.send_message(
            "⚠️ Invalid date/time format! Use `YYYY-MM-DD` and `HH:MM` (24-hour).",
            ephemeral=True
        )


@client.tree.command(name="listreminders", description="List your reminders", guild=GUILD_ID)
async def listreminders(interaction: discord.Interaction):
    reminders = load_reminders()
    user_reminders = [rem for rem in reminders if rem['user_id'] == interaction.user.id]

    if not user_reminders:
        await interaction.response.send_message("📭 You have no active reminders.", ephemeral=True)
        return

    reminder_list = []
    for idx, reminder in enumerate(user_reminders):
        reminder_time = datetime.fromisoformat(reminder["reminder_time"])
        local_time = reminder_time.astimezone(pytz.timezone('UTC'))
        reminder_list.append(f"{idx + 1}. `{local_time.strftime('%Y-%m-%d %H:%M %Z')}` - {reminder['message']}")

    await interaction.response.send_message("\n".join(reminder_list), ephemeral=True)


@client.tree.command(name="cancelreminder", description="Cancel a reminder", guild=GUILD_ID)
@app_commands.describe(index="Reminder number (from listreminders)")
async def cancelreminder(interaction: discord.Interaction, index: int):
    reminders = load_reminders()
    user_reminders = [rem for rem in reminders if rem['user_id'] == interaction.user.id]

    if index < 1 or index > len(user_reminders):
        await interaction.response.send_message("❌ Invalid reminder number.", ephemeral=True)
        return

    reminder_to_remove = user_reminders[index - 1]
    reminders = [rem for rem in reminders if not (
        rem['user_id'] == reminder_to_remove['user_id'] and
        rem['reminder_time'] == reminder_to_remove['reminder_time'] and
        rem['message'] == reminder_to_remove['message']
    )]
    save_reminders(reminders)

    await interaction.response.send_message(
        f"✅ Reminder `{reminder_to_remove['message']}` has been cancelled.", ephemeral=True
    )

@client.tree.command(name="poll", description="Create a poll with up to 5 options", guild=GUILD_ID)
@app_commands.describe(
    question="The poll question",
    option1="Poll option 1",
    option2="Poll option 2",
    option3="Poll option 3 (optional)",
    option4="Poll option 4 (optional)",
    option5="Poll option 5 (optional)"
)
async def poll(interaction: discord.Interaction, question: str, option1: str, option2: str, option3: str = None, option4: str = None, option5: str = None):
    options = [option1, option2]
    if option3:
        options.append(option3)
    if option4:
        options.append(option4)
    if option5:
        options.append(option5)
    
    if len(options) < 2:
        await interaction.response.send_message("You must provide at least two poll options.", ephemeral=True)
        return

    
    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    
    
    poll_description = ""
    for idx, option in enumerate(options):
        poll_description += f"{number_emojis[idx]} {option}\n"

    
    embed = discord.Embed(title=question, description=poll_description, color=discord.Color.blue())
    embed.set_footer(text=f"Poll created by {interaction.user.display_name}")

    
    await interaction.response.send_message(embed=embed)
    
    poll_message = await interaction.original_response()

    
    for idx in range(len(options)):
        await poll_message.add_reaction(number_emojis[idx])

client.run(token)