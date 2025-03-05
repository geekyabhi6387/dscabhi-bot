import discord 
from discord.ext import commands
from discord import app_commands
from os import environ
from dotenv import load_dotenv
from google import genai
from google.genai import types
load_dotenv()

api = environ["api_key"]

aiclient = genai.Client(api_key=api)
chat = aiclient.chats.create(model="gemini-2.0-flash")
sys_instruct="You are a discord bot which is meant to reply to users chatting in the respective server channels. However you are only allowed to reply in 1800 characters or less because that's the discord chat limit, so always check your response to be in limit"

token = environ["TOKEN"]

class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')

        try:
            guild = discord.Object(id=579995729620369409)
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands to guild {guild.id}')

        except Exception as e:
            print(f'Error syncing commands: {e}')

    async def on_message(self, message):
        print(f'Message from {message.author}: {message.content}')

        if message.author == client.user:
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

GUILD_ID = discord.Object(id=579995729620369409)

client.run(token)