
import os
import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from datetime import datetime
from models.bet import Bet
from utils.database import Database

# Detectar ambiente de execução
IS_FLYIO = os.getenv("FLY_APP_NAME") is not None
IS_RAILWAY = os.getenv("RAILWAY_ENVIRONMENT") is not None or os.getenv("RAILWAY_STATIC_URL") is not None

if IS_FLYIO:
    print("✈️ Detectado ambiente Fly.io")
elif IS_RAILWAY:
    print("🚂 Detectado ambiente Railway")
else:
    print("💻 Detectado ambiente Replit/Local")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
db = Database()

# Importar todo o código do bot de nz-apostas/main.py
# (código completo já está no arquivo rag://rag_source_0)
