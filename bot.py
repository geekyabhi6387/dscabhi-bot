import discord 
from os import environ
from dotenv import load_dotenv
from google import genai
load_dotenv()

api = environ["api_key"]

aiclient = genai.Client(api_key=api)
chat = aiclient.chats.create(model="gemini-2.0-flash")


token = environ["TOKEN"]

class Client(discord.Client):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    async def on_message(self, message):
        print(f'Message from {message.author}: {message.content}')


intents  = discord.Intents.default()
intents.message_content = True

client = Client(intents=intents)
client.run(token)