import discord
from discord.ext import commands, tasks
import asyncio
import json
import sqlite3
import random
import datetime
import time
import os
import aiohttp
import re
import math
import hashlib
from typing import Optional, List, Dict, Any, Union
import logging
from dataclasses import dataclass
from collections import defaultdict, deque
import threading
import subprocess
import platform
import sys
import gc
import traceback
import io
import uuid
import secrets
import string
import csv
from datetime import timedelta
import calendar
from urllib.parse import quote, unquote
import base64
import tempfile
import shutil
import hmac


# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rxbot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('RXbot')

# Configuração de intents
intents = discord.Intents.all()
intents.message_content = True
intents.members = True
intents.presences = True
intents.guilds = True
intents.reactions = True
intents.voice_states = True

# Bot configuration
bot = commands.Bot(
    command_prefix=['RX', 'rx', '!', '.', '>', '<', '?', 'bot ', 'BOT ', 'Bot '],
    intents=intents,
    help_command=None,
    case_insensitive=True,
    strip_after_prefix=True
)

# Database connection
db_lock = threading.Lock()

def get_db_connection():
    return sqlite3.connect('rxbot.db', timeout=30.0, check_same_thread=False)

# Database setup
def init_database():
    with db_lock:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Tabela de eventos
            cursor.execute('''CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                creator_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                max_participants INTEGER DEFAULT 0,
                participants TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                event_type TEXT DEFAULT 'geral',
                location TEXT
            )''')

            # Tabela de tickets
            cursor.execute('''CREATE TABLE IF NOT EXISTS tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                creator_id INTEGER,
                channel_id INTEGER,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_by INTEGER,
                reason TEXT
            )''')

            # User economy and stats
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                coins INTEGER DEFAULT 50,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                reputation INTEGER DEFAULT 0,
                bank INTEGER DEFAULT 0,
                last_daily DATE,
                last_weekly DATE,
                last_monthly DATE,
                inventory TEXT DEFAULT '{}',
                achievements TEXT DEFAULT '[]',
                settings TEXT DEFAULT '{}',
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_messages INTEGER DEFAULT 0,
                voice_time INTEGER DEFAULT 0,
                warnings INTEGER DEFAULT 0
            )''')

            # Guild settings
            cursor.execute('''CREATE TABLE IF NOT EXISTS guilds (
                guild_id INTEGER PRIMARY KEY,
                name TEXT,
                prefix TEXT DEFAULT 'RX',
                welcome_channel INTEGER,
                goodbye_channel INTEGER,
                log_channel INTEGER,
                mute_role INTEGER,
                auto_role INTEGER,
                settings TEXT DEFAULT '{}',
                economy_settings TEXT DEFAULT '{}',
                moderation_settings TEXT DEFAULT '{}'
            )''')

            # Moderation logs
            cursor.execute('''CREATE TABLE IF NOT EXISTS moderation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                action TEXT,
                reason TEXT,
                duration INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

            # Economy transactions
            cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                type TEXT,
                amount INTEGER,
                description TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

            # Custom commands
            cursor.execute('''CREATE TABLE IF NOT EXISTS custom_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                command_name TEXT,
                response TEXT,
                creator_id INTEGER,
                uses INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

            # Reminders
            cursor.execute('''CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                channel_id INTEGER,
                reminder_text TEXT,
                remind_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

            # Sistema de sorteios
            cursor.execute('''CREATE TABLE IF NOT EXISTS giveaways (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                channel_id INTEGER,
                creator_id INTEGER,
                title TEXT,
                prize TEXT,
                winners_count INTEGER DEFAULT 1,
                end_time TIMESTAMP,
                message_id INTEGER,
                participants TEXT DEFAULT '[]',
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

            conn.commit()
            logger.info("✅ Database initialized successfully!")

        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
        finally:
            if conn:
                conn.close()

# Initialize database
init_database()

# Global variables
global_stats = {
    'commands_used': 0,
    'messages_processed': 0,
    'guilds_joined': 0,
    'uptime_start': datetime.datetime.now(),
    'total_users': 0,
    'total_channels': 0
}

# Memory system for AI conversations
conversation_memory = defaultdict(lambda: deque(maxlen=50))
user_personalities = defaultdict(dict)

# Active games and sessions
active_games = {}

# Moderation system
spam_tracker = defaultdict(lambda: deque(maxlen=10))
warning_tracker = defaultdict(int)

# Economy system constants
DAILY_REWARD = 100
WEEKLY_REWARD = 700
MONTHLY_REWARD = 2500
WORK_COOLDOWN = 7200
CRIME_COOLDOWN = 14400

# XP and leveling system
XP_PER_MESSAGE = 5
XP_MULTIPLIER = 1.2

# Sistema de Ranks
RANK_SYSTEM = {
    1: {"name": "Novato", "xp": 0, "emoji": "🌱", "color": 0x808080},
    2: {"name": "Iniciante", "xp": 500, "emoji": "🔰", "color": 0x00ff00},
    3: {"name": "Aprendiz", "xp": 1500, "emoji": "📚", "color": 0x0099ff},
    4: {"name": "Experiente", "xp": 3500, "emoji": "⭐", "color": 0xffaa00},
    5: {"name": "Veterano", "xp": 7000, "emoji": "🎖️", "color": 0xff6600},
    6: {"name": "Elite", "xp": 15000, "emoji": "💎", "color": 0x00ffff},
    7: {"name": "Mestre", "xp": 30000, "emoji": "👑", "color": 0xffd700},
    8: {"name": "Grão-Mestre", "xp": 60000, "emoji": "🏆", "color": 0xff0080},
    9: {"name": "Lenda", "xp": 120000, "emoji": "🌟", "color": 0x8000ff},
    10: {"name": "Divino", "xp": 250000, "emoji": "✨", "color": 0xff00ff},
    11: {"name": "Transcendente", "xp": 500000, "emoji": "🌠", "color": 0x00ff80},
    12: {"name": "Imortal", "xp": 1000000, "emoji": "🔥", "color": 0xff4000}
}

def get_user_rank(xp):
    current_rank = 1
    for rank_id, rank_data in RANK_SYSTEM.items():
        if xp >= rank_data["xp"]:
            current_rank = rank_id
        else:
            break
    return current_rank, RANK_SYSTEM[current_rank]

# Sistema de IA
class AdvancedAI:
    def __init__(self):
        self.context_patterns = {
            'cumprimento': ['oi', 'olá', 'hey', 'salve', 'fala', 'eae', 'bom dia', 'boa tarde', 'boa noite'],
            'pergunta': ['como', 'por que', 'o que', 'quando', 'onde', 'qual', 'quem', 'quanto'],
            'ajuda': ['ajuda', 'help', 'socorro', 'não sei', 'como fazer', 'me ensina', 'tutorial'],
            'positivo': ['obrigado', 'valeu', 'legal', 'bom', 'ótimo', 'massa', 'show', 'perfeito'],
            'negativo': ['ruim', 'chato', 'não gosto', 'problema', 'erro', 'bug', 'falhou'],
            'comando': ['comando', 'fazer', 'executar', 'rodar', 'usar', 'funcionar'],
            'diversão': ['jogo', 'brincadeira', 'piada', 'diversão', 'entretenimento', 'game'],
            'eventos': ['evento', 'festa', 'torneio', 'competição', 'atividade'],
            'sorteio': ['sorteio', 'giveaway', 'concurso', 'prêmio', 'ganhar']
        }

        self.responses = {
            'cumprimento': [
                "Olá! 👋 Como posso ajudar você hoje?",
                "Oi! 😊 Em que posso ser útil?",
                "Salve! 🔥 Pronto para ajudar você!",
                "Hey! 🚀 O que precisamos fazer hoje?"
            ],
            'pergunta': [
                "Ótima pergunta! Vou explicar de forma clara:",
                "Interessante! Deixe-me esclarecer isso:",
                "Perfeito! Aqui está uma explicação detalhada:"
            ],
            'ajuda': [
                "Claro! Estou aqui para ajudar. Vou te guiar passo a passo:",
                "Sem problemas! Vou explicar tudo detalhadamente:",
                "Pode contar comigo! Aqui está a solução:"
            ]
        }

    def analyze_message(self, message_content):
        content_lower = message_content.lower()
        detected_contexts = []

        for context, keywords in self.context_patterns.items():
            if any(keyword in content_lower for keyword in keywords):
                detected_contexts.append(context)

        return detected_contexts if detected_contexts else ['geral']

    def generate_response(self, message_content, user_data=None):
        contexts = self.analyze_message(message_content)
        primary_context = contexts[0]

        if len(message_content.strip()) <= 3:
            return random.choice([
                "Entendi! 😄 Como posso ajudar?",
                "Haha! 😊 Em que posso ser útil?",
                "Legal! 🎉 Vamos conversar?"
            ])

        if primary_context in self.responses:
            return random.choice(self.responses[primary_context])

        return "Interessante! Como posso te ajudar hoje? Use `RXajuda` para ver todos os comandos!"

ai_system = AdvancedAI()

# Background tasks
@tasks.loop(minutes=5)
async def update_status():
    try:
        if bot.is_ready():
            statuses = [
                f"👥 {len(bot.guilds)} servidores",
                f"💬 {len(set(bot.get_all_members()))} usuários",
                f"⏱️ {format_time(int((datetime.datetime.now() - global_stats['uptime_start']).total_seconds()))} online",
                "💫 RXping para começar!",
                "🤖 RXajuda para comandos"
            ]
            await bot.change_presence(
                status=discord.Status.online,
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=random.choice(statuses)
                )
            )
    except Exception as e:
        logger.error(f"Erro no update_status: {e}")

@tasks.loop(minutes=1)
async def check_reminders():
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            now = datetime.datetime.now()
            cursor.execute('SELECT * FROM reminders WHERE remind_time <= ?', (now,))
            reminders = cursor.fetchall()

            for reminder in reminders:
                reminder_id, user_id, guild_id, channel_id, text, remind_time, created_at = reminder

                try:
                    channel = bot.get_channel(channel_id)
                    user = bot.get_user(user_id)

                    if channel and user:
                        embed = create_embed(
                            "⏰ Lembrete!",
                            f"**{user.mention}** você pediu para eu lembrar:\n\n{text}",
                            color=0xffaa00
                        )
                        await channel.send(embed=embed)

                    cursor.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))
                except Exception as e:
                    logger.error(f"Erro ao enviar lembrete {reminder_id}: {e}")

            conn.commit()
            conn.close()
    except Exception as e:
        logger.error(f"Erro check_reminders: {e}")

@tasks.loop(minutes=1)
async def check_events():
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            now = datetime.datetime.now()
            # Eventos que começam em 10 minutos
            notify_time = now + timedelta(minutes=10)

            cursor.execute('''
                SELECT * FROM events
                WHERE status = 'active'
                AND start_time BETWEEN ? AND ?
                AND start_time > ?
            ''', (now, notify_time, now))

            upcoming_events = cursor.fetchall()

            for event in upcoming_events:
                event_id, guild_id, creator_id, title, description, start_time, end_time, max_participants, participants_json, created_at, status, event_type, location = event

                try:
                    guild = bot.get_guild(guild_id)
                    if not guild:
                        continue

                    # Canal geral ou primeiro canal de texto
                    channel = guild.system_channel or guild.text_channels[0] if guild.text_channels else None
                    if not channel:
                        continue

                    participants = json.loads(participants_json) if participants_json else []

                    embed = create_embed(
                        f"🔔 Evento Começando em 10 minutos!",
                        f"""**🎯 {title}**

**📝 Descrição:** {description or 'Sem descrição'}
**⏰ Início:** <t:{int(datetime.datetime.fromisoformat(start_time).timestamp())}:F>
**📍 Local:** {location or 'Discord'}
**🎭 Tipo:** {event_type.title()}
**👥 Participantes:** {len(participants)}/{max_participants if max_participants > 0 else '∞'}

Prepare-se! O evento está prestes a começar! 🚀""",
                        color=0xff6600
                    )

                    await channel.send(embed=embed)

                except Exception as e:
                    logger.error(f"Erro ao notificar evento {event_id}: {e}")

            conn.close()
    except Exception as e:
        logger.error(f"Erro check_events: {e}")

# Utility functions
def get_user_data(user_id):
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            data = cursor.fetchone()
            conn.close()
            return data
    except Exception as e:
        logger.error(f"Error getting user data: {e}")
        return None

def update_user_data(user_id, **kwargs):
    conn = None
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
            if not cursor.fetchone():
                cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))

            for field, value in kwargs.items():
                if field in ['coins', 'xp', 'level', 'reputation', 'bank', 'total_messages', 'voice_time', 'warnings']:
                    cursor.execute(f'UPDATE users SET {field} = ? WHERE user_id = ?', (value, user_id))
                elif field in ['inventory', 'achievements', 'settings']:
                    cursor.execute(f'UPDATE users SET {field} = ? WHERE user_id = ?', (json.dumps(value), user_id))
                elif field in ['last_daily', 'last_weekly', 'last_monthly']:
                    cursor.execute(f'UPDATE users SET {field} = ? WHERE user_id = ?', (value, user_id))

            conn.commit()
            conn.close()
    except Exception as e:
        logger.error(f"Error updating user data: {e}")
        if conn:
            conn.close()

def add_xp(user_id, amount):
    try:
        data = get_user_data(user_id)
        if not data:
            update_user_data(user_id, xp=amount, level=1)
            return False, 1, False, 1

        current_xp = data[2]
        current_level = data[3]
        new_xp = current_xp + amount

        new_level = int(math.sqrt(new_xp / 100)) + 1
        leveled_up = new_level > current_level

        old_rank_id, old_rank = get_user_rank(current_xp)
        new_rank_id, new_rank = get_user_rank(new_xp)
        rank_up = new_rank_id > old_rank_id

        update_user_data(user_id, xp=new_xp, level=new_level)
        return leveled_up, new_level, rank_up, new_rank_id
    except Exception as e:
        logger.error(f"Error adding XP: {e}")
        return False, 1, False, 1

def format_time(seconds):
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    parts = []
    if days: parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    if seconds: parts.append(f"{seconds}s")

    return " ".join(parts) if parts else "0s"

def create_embed(title, description=None, color=0x7289DA, **kwargs):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.timestamp = datetime.datetime.now()

    for key, value in kwargs.items():
        if key == 'thumbnail':
            embed.set_thumbnail(url=value)
        elif key == 'image':
            embed.set_image(url=value)
        elif key == 'footer':
            embed.set_footer(text=value)

    return embed

# Event handlers
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    global_stats['messages_processed'] += 1

    # Sistema de XP
    try:
        leveled_up, new_level, rank_up, new_rank_id = add_xp(message.author.id, XP_PER_MESSAGE)

        if leveled_up:
            embed = create_embed(
                f"🎉 Level Up!",
                f"{message.author.mention} subiu para o **Level {new_level}**!",
                color=0xffd700
            )
            await message.channel.send(embed=embed, delete_after=10)

        if rank_up:
            rank_data = RANK_SYSTEM[new_rank_id]
            embed = create_embed(
                f"⭐ Rank Up!",
                f"{message.author.mention} alcançou o rank **{rank_data['emoji']} {rank_data['name']}**!",
                color=rank_data['color']
            )
            await message.channel.send(embed=embed, delete_after=15)
    except Exception as e:
        logger.error(f"Erro no sistema XP: {e}")

    # Sistema de IA
    if bot.user.mentioned_in(message) and not message.mention_everyone:
        try:
            content = message.content.replace(f'<@{bot.user.id}>', '').strip()
            if content:
                response = ai_system.generate_response(content)
                await message.reply(response)
        except Exception as e:
            logger.error(f"Erro no sistema IA: {e}")

    await bot.process_commands(message)

@bot.event
async def on_ready():
    logger.info(f"🤖 RXbot está online! Conectado como {bot.user}")
    logger.info(f"📊 Conectado em {len(bot.guilds)} servidores")
    logger.info(f"👥 Servindo {len(set(bot.get_all_members()))} usuários únicos")

    global_stats['total_users'] = len(set(bot.get_all_members()))
    global_stats['total_channels'] = len(list(bot.get_all_channels()))

    if not hasattr(bot, '_tasks_started'):
        bot._tasks_started = True
        try:
            update_status.start()
            check_reminders.start()
            check_events.start()
            logger.info("✅ Background tasks iniciados")
        except Exception as e:
            logger.error(f"Erro ao iniciar background tasks: {e}")

    try:
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"🚀 {len(bot.guilds)} servidores | RXping para começar!"
            )
        )
        logger.info("✅ Status inicial configurado")
    except Exception as e:
        logger.error(f"Erro ao configurar status: {e}")

    print("🔥 RXbot está online! Pronto para comandar!")

@bot.event
async def on_guild_join(guild):
    global_stats['guilds_joined'] += 1
    logger.info(f"📈 Entrei no servidor: {guild.name} ({guild.id})")

    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO guilds (guild_id, name) VALUES (?, ?)', (guild.id, guild.name))
            conn.commit()
            conn.close()
    except Exception as e:
        logger.error(f"Error joining guild: {e}")

@bot.event
async def on_member_join(member):
    if member.bot:
        return

    try:
        # Buscar canal de boas-vindas do servidor
        guild_id = member.guild.id

        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT welcome_channel FROM guilds WHERE guild_id = ?', (guild_id,))
            result = cursor.fetchone()
            conn.close()

        welcome_channel = None
        if result and result[0]:
            welcome_channel = bot.get_channel(result[0])

        # Se não tiver canal configurado, usar canal do sistema ou primeiro canal de texto
        if not welcome_channel:
            welcome_channel = member.guild.system_channel
            if not welcome_channel and member.guild.text_channels:
                welcome_channel = member.guild.text_channels[0]

        if not welcome_channel:
            return

        # Buscar dados do usuário
        user_data = get_user_data(member.id)
        if not user_data:
            update_user_data(member.id)

        # Mensagens de boas-vindas variadas
        welcome_messages = [
            f"🎉 **Bem-vindo(a) ao nosso servidor, {member.mention}!**\n\n"
            f"✨ Esperamos que se divirta muito aqui!\n"
            f"🎮 Use `RXping` para começar a explorar os comandos\n"
            f"💫 Ganhe XP enviando mensagens e suba de rank!\n\n"
            f"*{member.guild.name} agora tem {member.guild.member_count} membros!*",

            f"🚀 **{member.mention} chegou para arrasar!**\n\n"
            f"🎊 Que bom te ver por aqui!\n"
            f"🎯 Explore nossos comandos com `RXajuda`\n"
            f"💰 Comece sua jornada econômica com `RXdaily`\n\n"
            f"*Membro #{member.guild.member_count} do {member.guild.name}!*",

            f"🌟 **Olá {member.mention}! Seja muito bem-vindo(a)!**\n\n"
            f"🎨 Pronto para uma experiência incrível?\n"
            f"🤖 Converse comigo mencionando @RXbot\n"
            f"🏆 Participe dos rankings e ganhe reputação!\n\n"
            f"*Agradecemos por escolher o {member.guild.name}!*"
        ]

        welcome_message = random.choice(welcome_messages)

        embed = create_embed(
            f"🎉 Bem-vindo(a) ao {member.guild.name}!",
            welcome_message,
            color=0x00ff00
        )

        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)

        embed.add_field(
            name="Primeiros Passos",
            value="• `RXping` - Testar o bot\n"
                  "• `RXajuda` - Ver todos os comandos\n"
                  "• `RXdaily` - Ganhar moedas diárias\n"
                  "• `RXrank` - Ver seu progresso",
            inline=True
        )

        embed.add_field(
            name="Informações",
            value=f"• **Membro:** #{member.guild.member_count}\n"
                  f"• **Conta criada:** <t:{int(member.created_at.timestamp())}:R>\n"
                  f"• **Servidor:** {member.guild.name}\n"
                  f"• **Data:** <t:{int(datetime.datetime.now().timestamp())}:F>",
            inline=True
        )

        embed.set_footer(text=f"ID: {member.id} | Desejamos uma ótima experiência!")

        await welcome_channel.send(embed=embed)
        logger.info(f"👋 Boas-vindas enviadas para {member.name} em {member.guild.name}")

        # XP bônus para novos membros
        add_xp(member.id, 25)

    except Exception as e:
        logger.error(f"Erro ao enviar boas-vindas para {member.name}: {e}")

# ============ COMANDOS BÁSICOS ============
@bot.command(name='ping', aliases=['p', 'latencia'])
async def ping(ctx):
    global_stats['commands_used'] += 1

    start_time = time.time()
    message = await ctx.send("🏓 Pong!")
    end_time = time.time()

    api_latency = round(bot.latency * 1000, 2)
    response_time = round((end_time - start_time) * 1000, 2)

    embed = create_embed(
        "🏓 Pong!",
        f"""**Latência da API:** {api_latency}ms
**Tempo de resposta:** {response_time}ms
**Status:** {'🟢 Excelente' if api_latency < 100 else '🟡 Bom' if api_latency < 200 else '🔴 Lento'}

**Uptime:** {format_time(int((datetime.datetime.now() - global_stats['uptime_start']).total_seconds()))}""",
        color=0x00ff00 if api_latency < 100 else 0xffaa00 if api_latency < 200 else 0xff0000
    )

    await message.edit(content=None, embed=embed)

@bot.command(name='ajuda', aliases=['help', 'comandos'])
async def help_command(ctx, categoria=None):
    if not categoria:
        embed = create_embed(
            "📚 Central de Ajuda - RXbot",
            """**🎮 Diversão:**
`RXajuda diversao` - Jogos, piadas, entretenimento

**💰 Economia:**
`RXajuda economia` - Dinheiro, loja, trabalho

**🏆 Ranks:**
`RXajuda ranks` - Sistema de ranking e XP

**⚙️ Utilidades:**
`RXajuda utilidades` - Ferramentas e conversores

**🛡️ Moderação:**
`RXajuda moderacao` - Kick, ban, clear

**📊 Informações:**
`RXajuda info` - Stats, perfil, servidor

**🎁 Sorteios:**
`RXajuda sorteios` - Sistema de sorteios

**🎟️ Tickets:**
`RXajuda tickets` - Sistema de suporte

**📅 Eventos:**
`RXajuda eventos` - Sistema de eventos

**👑 Administração:**
`RXajuda admin` - Comandos para administradores

**🤖 IA Avançada:**
Mencione o bot para conversar!

**Total:** 250+ comandos disponíveis!""",
            color=0x7289da
        )
        embed.set_footer(text="Use RXajuda <categoria> para ver comandos específicos!")
        await ctx.send(embed=embed)

    elif categoria.lower() in ['eventos', 'event', 'events']:
        embed = create_embed(
            "📅 Sistema Completo de Eventos",
            """**Para Administradores:**
• `RXcriarevento <dados>` - Criar novo evento
• `RXevent <dados>` - Criar evento (alias)
• `RXeventinfo <id>` - Ver informações de evento
• `RXcancelarevent <id>` - Cancelar evento
• `RXeventos` - Listar todos os eventos

**Formato do evento:**
`Título | Descrição | Data/Hora | Tipo | Local | Max Participantes`

**Para Todos:**
• `RXeventos` - Ver eventos ativos
• `RXparticipar <id>` - Participar de evento
• `RXsairrevento <id>` - Sair de evento
• `RXmeusventos` - Ver seus eventos

**Tipos de evento:**
• clan, torneio, festa, reunião, competição, geral

**Exemplo:**
`RXcriarevento Guerra de Clans | Batalha épica entre clans | 20:00 | clan | Discord | 50`

**Formatos de data/hora:** 20:00, 14:30, 18h, 21h30""",
            color=0xff6600
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['diversao', 'diversão', 'fun']:
        embed = create_embed(
            "🎮 Comandos de Diversão",
            """**Jogos:**
• `RXjokenpo <escolha>` - Pedra, papel, tesoura
• `RXdado [lados]` - Rola um dado
• `RXmoeda` - Cara ou coroa
• `RX8ball <pergunta>` - Bola mágica 8

**Entretenimento:**
• `RXpiada` - Conta uma piada aleatória
• `RXfato` - Fato interessante
• `RXenquete <pergunta>` - Cria enquete
• `RXmeme` - Meme aleatório""",
            color=0x7289da
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['economia', 'money', 'eco']:
        embed = create_embed(
            "💰 Comandos de Economia",
            """**Dinheiro:**
• `RXsaldo [@user]` - Ver saldo
• `RXdaily` - Recompensa diária (100 moedas)
• `RXweekly` - Recompensa semanal (700 moedas)
• `RXmonthly` - Recompensa mensal (2500 moedas)

**Transferências:**
• `RXtransferir <@user> <valor>` - Transferir dinheiro
• `RXpay <@user> <valor>` - Pagar alguém
• `RXdepositar <valor>` - Depositar no banco
• `RXsacar <valor>` - Sacar do banco""",
            color=0xffd700
        )
        await ctx.send(embed=embed)

# ============ SISTEMA DE EVENTOS ============
@bot.command(name='criarevento', aliases=['event', 'createvent'])
@commands.has_permissions(administrator=True)
async def create_event(ctx, *, event_data=None):
    if not event_data:
        embed = create_embed(
            "📅 Como criar um evento",
            """**Formato:** `Título | Descrição | Data/Hora | Tipo | Local | Max Participantes`

**Exemplo:**
`RXcriarevento Guerra de Clans | Batalha épica entre clans | 20:00 | clan | Discord | 50`

**Tipos de evento:** clan, torneio, festa, reunião, competição, geral
**Formatos de hora:** 20:00, 14:30, 18h, 21h30
**Max participantes:** Número ou 0 para ilimitado""",
            color=0x7289da
        )
        await ctx.send(embed=embed)
        return

    parts = [part.strip() for part in event_data.split('|')]
    if len(parts) < 4:
        embed = create_embed(
            "❌ Formato incorreto",
            "Use: `Título | Descrição | Data/Hora | Tipo | [Local] | [Max Participantes]`",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

    title = parts[0]
    description = parts[1] if len(parts) > 1 else ""
    time_str = parts[2]
    event_type = parts[3].lower() if len(parts) > 3 else "geral"
    location = parts[4] if len(parts) > 4 else "Discord"
    max_participants = 0

    if len(parts) > 5:
        try:
            max_participants = int(parts[5])
        except ValueError:
            max_participants = 0

    # Validar tipo de evento
    valid_types = ['clan', 'torneio', 'festa', 'reunião', 'competição', 'geral']
    if event_type not in valid_types:
        event_type = 'geral'

    # Parse time
    try:
        now = datetime.datetime.now()

        # Diferentes formatos de hora
        if ':' in time_str:
            hour, minute = map(int, time_str.split(':'))
        elif 'h' in time_str.lower():
            time_clean = time_str.lower().replace('h', '')
            if ':' in time_clean or '30' in time_clean:
                parts_time = time_clean.replace(':', '').replace('30', ':30').split(':')
                hour = int(parts_time[0])
                minute = int(parts_time[1]) if len(parts_time) > 1 else 0
            else:
                hour = int(time_clean)
                minute = 0
        else:
            hour = int(time_str)
            minute = 0

        # Criar datetime para hoje ou amanhã
        event_datetime = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Se o horário já passou hoje, agendar para amanhã
        if event_datetime <= now:
            event_datetime += timedelta(days=1)

    except (ValueError, IndexError):
        embed = create_embed(
            "❌ Horário inválido",
            "Use formatos como: 20:00, 14:30, 18h, 21h30",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

    # Salvar evento no banco
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO events (guild_id, creator_id, title, description, start_time, event_type, location, max_participants)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ctx.guild.id, ctx.author.id, title, description, event_datetime, event_type, location, max_participants))

            event_id = cursor.lastrowid
            conn.commit()
            conn.close()

        # Determinar emoji do tipo
        type_emojis = {
            'clan': '⚔️',
            'torneio': '🏆',
            'festa': '🎉',
            'reunião': '📋',
            'competição': '🥇',
            'geral': '📅'
        }

        emoji = type_emojis.get(event_type, '📅')

        embed = create_embed(
            f"✅ Evento Criado! {emoji}",
            f"""**{emoji} {title}**

**📝 Descrição:** {description}
**📅 Data:** <t:{int(event_datetime.timestamp())}:F>
**⏰ Início:** <t:{int(event_datetime.timestamp())}:R>
**🎭 Tipo:** {event_type.title()}
**📍 Local:** {location}
**👥 Participantes:** 0/{max_participants if max_participants > 0 else '∞'}
**👤 Criado por:** {ctx.author.mention}
**🆔 ID do evento:** {event_id}

Use `RXparticipar {event_id}` para participar!""",
            color=0x00ff00
        )

        await ctx.send(embed=embed)

        logger.info(f"Evento criado: {title} por {ctx.author} em {ctx.guild.name}")

    except Exception as e:
        logger.error(f"Erro ao criar evento: {e}")
        embed = create_embed("❌ Erro", "Erro ao criar evento!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='eventos', aliases=['events', 'listeventos'])
async def list_events(ctx):
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title, description, start_time, event_type, location, max_participants, participants, creator_id
                FROM events
                WHERE guild_id = ? AND status = 'active'
                ORDER BY start_time
            ''', (ctx.guild.id,))

            events = cursor.fetchall()
            conn.close()

        if not events:
            embed = create_embed(
                "📅 Nenhum evento ativo",
                "Não há eventos ativos no momento.\nAdministradores podem criar com `RXcriarevento`",
                color=0xffaa00
            )
            await ctx.send(embed=embed)
            return

        embed = create_embed(
            "📅 Eventos Ativos",
            f"Encontrados {len(events)} evento(s) ativo(s):",
            color=0xff6600
        )

        type_emojis = {
            'clan': '⚔️',
            'torneio': '🏆',
            'festa': '🎉',
            'reunião': '📋',
            'competição': '🥇',
            'geral': '📅'
        }

        for event in events[:10]:  # Mostrar até 10 eventos
            event_id, title, description, start_time, event_type, location, max_participants, participants_json, creator_id = event
            participants = json.loads(participants_json) if participants_json else []
            creator = bot.get_user(creator_id)
            emoji = type_emojis.get(event_type, '📅')

            embed.add_field(
                name=f"{emoji} {title} (ID: {event_id})",
                value=f"**📝** {description[:50]}{'...' if len(description) > 50 else ''}\n"
                      f"**⏰** <t:{int(datetime.datetime.fromisoformat(start_time).timestamp())}:R>\n"
                      f"**👥** {len(participants)}/{max_participants if max_participants > 0 else '∞'}\n"
                      f"**👤** {creator.mention if creator else 'Desconhecido'}",
                inline=False
            )

        embed.set_footer(text="Use RXparticipar <id> para participar de um evento!")
        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Error listing events: {e}")

@bot.command(name='participar', aliases=['join', 'joinevento'])
async def join_event(ctx, event_id: int = None):
    if not event_id:
        embed = create_embed("❌ ID necessário", "Use: `RXparticipar <id>`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT title, start_time, max_participants, participants, event_type
                FROM events
                WHERE id = ? AND guild_id = ? AND status = 'active'
            ''', (event_id, ctx.guild.id))

            event = cursor.fetchone()

            if not event:
                embed = create_embed("❌ Evento não encontrado", "Evento não existe ou já foi cancelado.", color=0xff0000)
                await ctx.send(embed=embed)
                return

            title, start_time, max_participants, participants_json, event_type = event
            participants = json.loads(participants_json) if participants_json else []

            if ctx.author.id in participants:
                embed = create_embed("⚠️ Já participando", "Você já está participando deste evento!", color=0xffaa00)
                await ctx.send(embed=embed)
                return

            if max_participants > 0 and len(participants) >= max_participants:
                embed = create_embed("❌ Evento lotado", "Este evento já atingiu o número máximo de participantes!", color=0xff0000)
                await ctx.send(embed=embed)
                return

            participants.append(ctx.author.id)

            cursor.execute('''
                UPDATE events SET participants = ? WHERE id = ?
            ''', (json.dumps(participants), event_id))

            conn.commit()
            conn.close()

        type_emojis = {
            'clan': '⚔️',
            'torneio': '🏆',
            'festa': '🎉',
            'reunião': '📋',
            'competição': '🥇',
            'geral': '📅'
        }

        emoji = type_emojis.get(event_type, '📅')

        embed = create_embed(
            "✅ Participação Confirmada!",
            f"Você se inscreveu no evento **{emoji} {title}**!\n\n"
            f"**⏰ Data:** <t:{int(datetime.datetime.fromisoformat(start_time).timestamp())}:F>\n"
            f"**👥 Participantes:** {len(participants)}/{max_participants if max_participants > 0 else '∞'}\n\n"
            f"Você receberá uma notificação quando o evento estiver prestes a começar! 🚀",
            color=0x00ff00
        )

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro ao participar do evento: {e}")
        embed = create_embed("❌ Erro", "Erro ao se inscrever no evento!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='eventinfo', aliases=['infoevent'])
async def event_info(ctx, event_id: int = None):
    if not event_id:
        embed = create_embed("❌ ID necessário", "Use: `RXeventinfo <id>`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM events
                WHERE id = ? AND guild_id = ?
            ''', (event_id, ctx.guild.id))

            event = cursor.fetchone()
            conn.close()

        if not event:
            embed = create_embed("❌ Evento não encontrado", "Evento não existe.", color=0xff0000)
            await ctx.send(embed=embed)
            return

        event_id, guild_id, creator_id, title, description, start_time, end_time, max_participants, participants_json, created_at, status, event_type, location = event

        participants = json.loads(participants_json) if participants_json else []
        creator = bot.get_user(creator_id)

        type_emojis = {
            'clan': '⚔️',
            'torneio': '🏆',
            'festa': '🎉',
            'reunião': '📋',
            'competição': '🥇',
            'geral': '📅'
        }

        emoji = type_emojis.get(event_type, '📅')

        # Lista de participantes
        participant_list = []
        for user_id in participants[:10]:  # Mostrar até 10
            user = bot.get_user(user_id)
            if user:
                participant_list.append(user.mention)

        participants_text = "\n".join(participant_list) if participant_list else "Nenhum participante ainda"
        if len(participants) > 10:
            participants_text += f"\n... e mais {len(participants) - 10} participante(s)"

        embed = create_embed(
            f"{emoji} {title}",
            f"""**📝 Descrição:** {description or 'Sem descrição'}

**📅 Informações do Evento:**
• **Data de início:** <t:{int(datetime.datetime.fromisoformat(start_time).timestamp())}:F>
• **Início em:** <t:{int(datetime.datetime.fromisoformat(start_time).timestamp())}:R>
• **Tipo:** {event_type.title()}
• **Local:** {location or 'Discord'}
• **Status:** {status.title()}

**👥 Participação:**
• **Participantes:** {len(participants)}/{max_participants if max_participants > 0 else '∞'}
• **Criado por:** {creator.mention if creator else 'Usuário desconhecido'}
• **Criado em:** <t:{int(datetime.datetime.fromisoformat(created_at).timestamp())}:R>

**👤 Lista de Participantes:**
{participants_text}""",
            color=0xff6600
        )

        embed.set_footer(text=f"ID do evento: {event_id}")
        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro ao buscar info do evento: {e}")
        embed = create_embed("❌ Erro", "Erro ao buscar informações do evento!", color=0xff0000)
        await ctx.send(embed=embed)

# ============ COMANDOS DE ECONOMIA ============
@bot.command(name='saldo', aliases=['balance', 'bal'])
async def balance(ctx, user: discord.Member = None):
    target = user or ctx.author
    data = get_user_data(target.id)

    if not data:
        update_user_data(target.id)
        coins, bank = 50, 0
    else:
        coins, bank = data[1], data[5]

    total = coins + bank

    embed = create_embed(
        f"💰 Carteira de {target.display_name}",
        f"""**💵 Dinheiro:** {coins:,} moedas
**🏦 Banco:** {bank:,} moedas
**💎 Total:** {total:,} moedas

*Use `RXdaily` para ganhar moedas diárias!*""",
        color=0xffd700
    )
    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name='daily', aliases=['diario'])
async def daily(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)

    if not data:
        update_user_data(user_id)
        data = get_user_data(user_id)

    last_daily = data[6]
    today = datetime.date.today().isoformat()

    if last_daily == today:
        embed = create_embed(
            "⏰ Já coletado!",
            "Você já coletou sua recompensa diária hoje!\nVolte amanhã para coletar novamente.",
            color=0xff6b6b
        )
        await ctx.send(embed=embed)
        return

    new_coins = data[1] + DAILY_REWARD

    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = ?, last_daily = ? WHERE user_id = ?',
                          (new_coins, today, user_id))
            conn.commit()
            conn.close()
    except Exception as e:
        logger.error(f"Error updating daily: {e}")

    embed = create_embed(
        "🎁 Recompensa Diária!",
        f"""**Recompensa:** {DAILY_REWARD:,} moedas
**Novo saldo:** {new_coins:,} moedas

🔥 *Continue coletando diariamente!*""",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

# ============ COMANDOS DE RANK ============
@bot.command(name='rank', aliases=['ranking', 'nivel'])
async def user_rank(ctx, user: discord.Member = None):
    global_stats['commands_used'] += 1
    target = user or ctx.author
    data = get_user_data(target.id)

    if not data:
        update_user_data(target.id)
        xp, level = 0, 1
    else:
        xp, level = data[2], data[3]

    current_rank_id, current_rank = get_user_rank(xp)

    next_rank_id = current_rank_id + 1 if current_rank_id < 12 else 12
    next_rank = RANK_SYSTEM.get(next_rank_id, RANK_SYSTEM[12])

    if current_rank_id < 12:
        xp_needed = next_rank["xp"] - xp
        progress = ((xp - current_rank["xp"]) / (next_rank["xp"] - current_rank["xp"])) * 100
        progress_bar = "█" * int(progress // 10) + "░" * (10 - int(progress // 10))
    else:
        xp_needed = 0
        progress = 100
        progress_bar = "█" * 10

    embed = create_embed(
        f"{current_rank['emoji']} Rank de {target.display_name}",
        f"""**🏆 Rank Atual:** {current_rank['name']} (#{current_rank_id})
**⭐ Level:** {level}
**💫 XP Total:** {xp:,}

**📊 Progresso para próximo rank:**
{progress_bar} {progress:.1f}%
**{next_rank['emoji']} Próximo:** {next_rank['name']}
**💪 XP Necessário:** {xp_needed:,}

**🎯 Estatísticas:**
• Mensagens para próximo rank: ~{xp_needed // XP_PER_MESSAGE:,}""",
        color=current_rank["color"]
    )

    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await ctx.send(embed=embed)

# ============ COMANDOS DE DIVERSÃO ============
@bot.command(name='jokenpo', aliases=['pedrapapeltesoura'])
async def jokenpo(ctx, escolha=None):
    if not escolha:
        embed = create_embed("❌ Escolha necessária", "Use: `RXjokenpo pedra|papel|tesoura`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    escolhas = ['pedra', 'papel', 'tesoura']
    emojis = {'pedra': '🪨', 'papel': '📄', 'tesoura': '✂️'}

    escolha = escolha.lower()
    if escolha not in escolhas:
        embed = create_embed("❌ Escolha inválida", "Use: pedra, papel ou tesoura", color=0xff0000)
        await ctx.send(embed=embed)
        return

    bot_escolha = random.choice(escolhas)

    if escolha == bot_escolha:
        resultado = "Empate!"
        color = 0xffaa00
    elif (escolha == 'pedra' and bot_escolha == 'tesoura') or \
         (escolha == 'papel' and bot_escolha == 'pedra') or \
         (escolha == 'tesoura' and bot_escolha == 'papel'):
        resultado = "Você ganhou! 🎉"
        color = 0x00ff00
    else:
        resultado = "Você perdeu! 😢"
        color = 0xff0000

    embed = create_embed(
        "🎮 Jokenpô",
        f"**Você:** {emojis[escolha]} {escolha.capitalize()}\n"
        f"**Bot:** {emojis[bot_escolha]} {bot_escolha.capitalize()}\n\n"
        f"**Resultado:** {resultado}",
        color=color
    )
    await ctx.send(embed=embed)

@bot.command(name='dado', aliases=['dice'])
async def dice(ctx, lados: int = 6):
    if lados < 2 or lados > 100:
        embed = create_embed("❌ Número inválido", "Use entre 2 e 100 lados", color=0xff0000)
        await ctx.send(embed=embed)
        return

    resultado = random.randint(1, lados)
    embed = create_embed(
        f"🎲 Dado de {lados} lados",
        f"**Resultado:** {resultado}",
        color=0x7289da
    )
    await ctx.send(embed=embed)

@bot.command(name='piada', aliases=['joke'])
async def piada(ctx):
    piadas = [
        "Por que os pássaros voam para o sul no inverno? Porque é longe demais para ir andando!",
        "O que a impressora falou para a outra impressora? Essa folha é sua ou é impressão minha?",
        "Por que o livro de matemática estava triste? Porque tinha muitos problemas!",
        "O que o pato disse para a pata? Vem quá!",
        "Por que os programadores preferem dark mode? Porque light atrai bugs!"
    ]

    piada = random.choice(piadas)
    embed = create_embed("😂 Piada do RXbot", piada, color=0xffaa00)
    await ctx.send(embed=embed)

# ============ COMANDOS DE UTILIDADES ============
@bot.command(name='lembrete', aliases=['reminder'])
async def create_reminder(ctx, tempo=None, *, texto=None):
    if not tempo or not texto:
        embed = create_embed(
            "⏰ Como usar lembretes",
            """**Formato:** `RXlembrete <tempo> <texto>`

**Exemplos:**
• `RXlembrete 30m Verificar email`
• `RXlembrete 2h Reunião importante`
• `RXlembrete 1d Aniversário do João`

**Tempos aceitos:** m (minutos), h (horas), d (dias)""",
            color=0x7289da
        )
        await ctx.send(embed=embed)
        return

    time_units = {'m': 60, 'h': 3600, 'd': 86400}
    unit = tempo[-1].lower()

    if unit not in time_units:
        embed = create_embed("❌ Tempo inválido", "Use: m (minutos), h (horas), d (dias)", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        amount = int(tempo[:-1])
        seconds = amount * time_units[unit]
        remind_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)

        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO reminders (user_id, guild_id, channel_id, reminder_text, remind_time)
                VALUES (?, ?, ?, ?, ?)
            ''', (ctx.author.id, ctx.guild.id, ctx.channel.id, texto, remind_time))
            conn.commit()
            conn.close()

        embed = create_embed(
            "✅ Lembrete Criado!",
            f"**Texto:** {texto}\n"
            f"**Quando:** <t:{int(remind_time.timestamp())}:F>\n"
            f"**Em:** <t:{int(remind_time.timestamp())}:R>",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

    except ValueError:
        embed = create_embed("❌ Número inválido", "Use números válidos: 30m, 2h, 1d", color=0xff0000)
        await ctx.send(embed=embed)

# ============ COMANDOS DE MODERAÇÃO ============
@bot.command(name='clear', aliases=['limpar'])
@commands.has_permissions(manage_messages=True)
async def clear_messages(ctx, amount: int = 10):
    if amount < 1 or amount > 100:
        embed = create_embed("❌ Quantidade inválida", "Use entre 1 e 100 mensagens", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        embed = create_embed(
            "🧹 Limpeza Concluída",
            f"**{len(deleted) - 1} mensagens foram deletadas com sucesso!**",
            color=0x00ff00
        )
        await ctx.send(embed=embed, delete_after=5)
    except Exception as e:
        logger.error(f"Erro na limpeza: {e}")
        embed = create_embed("❌ Erro", "Erro ao limpar mensagens!", color=0xff0000)
        await ctx.send(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    try:
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = create_embed(
                "❌ Argumento obrigatório",
                f"Você esqueceu de fornecer: `{error.param.name}`\n"
                f"Use `RXajuda` para ver os comandos.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
        elif isinstance(error, commands.MissingPermissions):
            embed = create_embed(
                "❌ Sem permissão",
                "Você não tem permissão para executar este comando!",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=8)
        else:
            logger.error(f"Unexpected error in {ctx.command}: {error}")
    except Exception as handler_error:
        logger.error(f"Erro no error handler: {handler_error}")

# Sistema de inicialização
def run_bot():
    token = os.getenv('TOKEN')
    if not token:
        logger.error("🚨 TOKEN não encontrado nas variáveis de ambiente!")
        print("❌ Configure a variável de ambiente TOKEN com o token do seu bot Discord")
        return

    try:
        keep_alive()
        time.sleep(2)
        logger.info("🚀 Iniciando RXbot...")
        bot.run(token)
    except Exception as e:
        logger.error(f"🚨 Erro fatal: {e}")

if __name__ == "__main__":
    run_bot()