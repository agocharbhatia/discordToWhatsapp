import discord
import asyncio
import threading
from flask import Flask, request, json
import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
ROLE_ID = os.getenv("ROLE_ID")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

app = Flask(__name__)

intents = discord.Intents.all()
client = discord.Client(intents=intents)


async def createChannel(name):
    guild = client.get_guild(GUILD_ID)
    role = guild.get_role(ROLE_ID)

    existing_channel = discord.utils.get(guild.channels, name=name)

    if existing_channel:
        print(f'A channel with the name "{name}" already exists in the guild.')
    else:
        new_channel = await guild.create_text_channel(name)
        await new_channel.set_permissions(guild.default_role, view_channel=False)
        await new_channel.set_permissions(role, view_channel=True)
        print(f'New channel "{name}" created in the guild!')


async def sendMsgToDisc(msg, id):
    guild = client.get_guild(GUILD_ID)

    channel = discord.utils.get(guild.channels, name=id)
    if channel:
        await channel.send(msg)
    else:
        print("Channel not found.")


@client.event
async def on_ready():
    print(f"Logged in as {client.user.name}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    channel_name = message.channel.name

    requests.post(
        f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages",
        headers={
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": channel_name,
            "type": "text",
            "text": {"body": message.content},
        },
    )


@app.route("/")
def test_valid():
    return "hello world"


@app.get("/webhook")
def webhook_get():
    print(request.args.get("hub.verify_token"))
    if request.args.get("hub.verify_token") == WEBHOOK_TOKEN:
        return request.args.get("hub.challenge")
    else:
        return "forbidden", 400


@app.post("/webhook")
async def webhook_post():
    print(request.json)

    try:
        timestamp = request.json["entry"][0]["changes"][0]["value"]["messages"][0][
            "timestamp"
        ]
        currTime = time.time()
        if int(currTime) - int(timestamp) > 5:
            return "ok", 200
    except Exception as e:
        print(e)
        return "ok", 200

    try:
        name = request.json["entry"][0]["changes"][0]["value"]["contacts"][0][
            "profile"
        ]["name"]

        phoneNumber = request.json["entry"][0]["changes"][0]["value"]["messages"][0][
            "from"
        ]

        text = request.json["entry"][0]["changes"][0]["value"]["messages"][0]["text"][
            "body"
        ]

        asyncio.run_coroutine_threadsafe(
            createChannel(phoneNumber), client.loop
        ).result()

        asyncio.run_coroutine_threadsafe(
            sendMsgToDisc(f"**{name} ({phoneNumber}):**\n{text}", phoneNumber),
            client.loop,
        ).result()

    except Exception as e:
        print(e)

    return "ok", 200


def main():
    app.run(debug=True, host="localhost", port=8001)


def client_main():
    client.run(BOT_TOKEN)


threading.Thread(target=client_main).start()
app.run(debug=False)
