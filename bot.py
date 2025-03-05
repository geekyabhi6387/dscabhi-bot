import discord 
from discord.ext import commands
from discord import app_commands
from os import environ
from dotenv import load_dotenv
from google import genai
from google.genai import types
load_dotenv()

api = environ["api_key"]
token = environ["TOKEN"]
guild_id = environ["guild_id"]

aiclient = genai.Client(api_key=api)
sys_instruct="You are a discord bot which is meant to reply to users chatting in the respective server channels. However you are only allowed to reply in 1800 characters or less because that's the discord chat limit, so always check your response to be in limit"

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

    async def on_message(self, message):
        print(f'Message from {message.author}: {message.content}')

        if message.author == client.user:
            return
        
        if message.content.startsWith("!"):
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


intents  = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix="!", intents=intents)

GUILD_ID = discord.Object(id=guild_id)

@client.tree.command(name="ping", description="Shows Latency", guild=GUILD_ID)
async def ping(interaction: discord.Interaction):
    latency = round(client.latency * 1000, 2)
    await interaction.response.send_message(f'Latency: {latency}ms')

@client.tree.command(name="remindme", description="Set a reminder")
async def remindme(interaction: discord.Interaction):
    await interaction.response.send_message(f'Reminder')

client.run(token)