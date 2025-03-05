import discord 
from os import environ
from dotenv import load_dotenv
from google import genai
from google.genai import types
load_dotenv()

api = environ["api_key"]

aiclient = genai.Client(api_key=api)
chat = aiclient.chats.create(model="gemini-2.0-flash")
sys_instruct="You are a discord bot which is meant to reply to users chatting in the respective server channels."

token = environ["TOKEN"]

class Client(discord.Client):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')

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

client = Client(intents=intents)
client.run(token)