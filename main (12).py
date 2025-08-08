CHANNEL_ID_ALERTA = 1402658677923774615
CHANNEL_ID_TESTE_TIER = 1400162532055846932
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

# Imports opcionais que podem não estar disponíveis
try:
    import psutil
except ImportError:
    psutil = None

try:
    import xml.etree.ElementTree as ET
except ImportError:
    ET = None

try:
    import yaml
except ImportError:
    yaml = None

try:
    import locale
except ImportError:
    locale = None

try:
    import pytz
except ImportError:
    pytz = None

try:
    import zlib
except ImportError:
    zlib = None

try:
    import gzip
except ImportError:
    gzip = None

try:
    import zipfile
except ImportError:
    zipfile = None

try:
    import tarfile
except ImportError:
    tarfile = None

try:
    import mimetypes
except ImportError:
    mimetypes = None

try:
    import email.utils
except ImportError:
    pass
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot está online!"

@app.route('/status')
def status():
    if not bot.is_ready():
        return {"status": "carregando..."}
    """Endpoint detalhado para monitoramento"""
    uptime_seconds = int((datetime.datetime.now() - global_stats['uptime_start']).total_seconds())

    status_data = {
        "status": "online",
        "bot_name": "RXbot",
        "uptime": format_time(uptime_seconds),
        "uptime_seconds": uptime_seconds,
        "guilds": len(bot.guilds),
        "users": len(set(bot.get_all_members())),
        "latency_ms": round(bot.latency * 1000, 2),
        "commands_used": global_stats['commands_used'],
        "messages_processed": global_stats['messages_processed'],
        "timestamp": datetime.datetime.now().isoformat()
    }

    return status_data

@app.route('/ping')
def ping():
    """Endpoint simples para ping"""
    return "pong"

@app.route('/health')
def health():
    """Health check endpoint"""
    return {"healthy": True, "timestamp": datetime.datetime.now().isoformat()}

@app.route('/monitor')
def monitor():
    """Endpoint específico para UptimeRobot com mais detalhes"""
    try:
        if not bot.is_ready():
            return {"status": "starting", "ready": False}, 503

        uptime_seconds = int((datetime.datetime.now() - global_stats['uptime_start']).total_seconds())

        return {
            "status": "online",
            "ready": True,
            "uptime_seconds": uptime_seconds,
            "latency_ms": round(bot.latency * 1000, 2),
            "guilds": len(bot.guilds),
            "users": len(set(bot.get_all_members())),
            "timestamp": datetime.datetime.now().isoformat(),
            "version": "2.0.0",
            "keep_alive": "active"
        }
    except Exception as e:
        logger.error(f"Erro no endpoint monitor: {e}")
        return {"status": "error", "error": str(e)}, 500

@app.route('/keepalive')
def keepalive():
    """Endpoint específico para manter ativo"""
    return {
        "status": "alive",
        "timestamp": datetime.datetime.now().isoformat(),
        "bot_ready": bot.is_ready() if 'bot' in globals() else False,
        "uptime": format_time(int((datetime.datetime.now() - global_stats['uptime_start']).total_seconds())),
        "auto_ping": "active"
    }

@app.route('/force-alive')
def force_alive():
    """Endpoint para forçar que o bot permaneça ativo"""
    return {
        "forced_alive": True,
        "timestamp": datetime.datetime.now().isoformat(),
        "message": "Keep-alive forçado com sucesso!",
        "bot_status": "online" if bot.is_ready() else "starting"
    }

@app.route('/heartbeat')
def heartbeat():
    """Endpoint de heartbeat para monitoramento externo"""
    return {
        "heartbeat": "alive",
        "timestamp": datetime.datetime.now().isoformat(),
        "bot_online": bot.is_ready(),
        "guild_count": len(bot.guilds) if bot.is_ready() else 0
    }

def run():
    app.run(host='0.0.0.0', port=8080, threaded=True)

def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()

# Sistema de auto-ping ULTRA AGRESSIVO para nunca hibernar
async def auto_ping():
    """Sistema de auto-ping otimizado para nunca hibernar"""
    import aiohttp
    consecutive_failures = 0
    max_failures = 2  # Reduzido para resposta mais rápida
    ping_count = 0

    while True:
        try:
            # Ping mais frequente: 25 segundos
            await asyncio.sleep(25)
            ping_count += 1

            success = False
            # Usar timeout mais baixo e conexão mais rápida
            timeout = aiohttp.ClientTimeout(total=5, connect=2)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Endpoints prioritários primeiro
                priority_endpoints = ['/ping', '/keepalive', '/force-alive']
                
                for endpoint in priority_endpoints:
                    try:
                        async with session.get(f'http://0.0.0.0:8080{endpoint}') as response:
                            if response.status == 200:
                                logger.info(f"✅ Auto-ping #{ping_count} {endpoint} OK")
                                success = True
                                consecutive_failures = 0
                                break
                    except Exception as e:
                        logger.debug(f"Endpoint {endpoint} falhou: {e}")
                        continue

                # Se falhou, tentar endpoints secundários
                if not success:
                    secondary_endpoints = ['/status', '/health', '/monitor', '/heartbeat']
                    for endpoint in secondary_endpoints:
                        try:
                            async with session.get(f'http://0.0.0.0:8080{endpoint}') as response:
                                if response.status == 200:
                                    logger.info(f"✅ Auto-ping #{ping_count} {endpoint} OK (secondary)")
                                    success = True
                                    consecutive_failures = 0
                                    break
                        except:
                            continue

                # Último recurso: localhost
                if not success:
                    try:
                        async with session.get('http://127.0.0.1:8080/ping') as response:
                            if response.status == 200:
                                logger.info(f"✅ Auto-ping #{ping_count} localhost OK")
                                success = True
                                consecutive_failures = 0
                    except:
                        pass

                if not success:
                    consecutive_failures += 1
                    logger.error(f"🚨 Auto-ping #{ping_count} FALHOU! ({consecutive_failures}/{max_failures})")

                    # Recuperação mais agressiva
                    if consecutive_failures >= max_failures:
                        logger.error("💀 RECUPERAÇÃO CRÍTICA!")
                        
                        # Limpeza de memória
                        import gc
                        gc.collect()

                        # Múltiplas tentativas de recuperação simultâneas
                        recovery_tasks = []
                        for i in range(3):
                            task = session.get('http://0.0.0.0:8080/force-alive')
                            recovery_tasks.append(task)
                        
                        try:
                            results = await asyncio.gather(*recovery_tasks, return_exceptions=True)
                            recovery_success = any(hasattr(r, 'status') and r.status == 200 for r in results)
                            
                            if recovery_success:
                                logger.info("🆘 Recuperação simultânea OK!")
                                success = True
                                consecutive_failures = 0
                        except:
                            pass

        except Exception as e:
            logger.error(f"❌ Erro CRÍTICO no auto-ping: {e}")
            # Forçar garbage collection em caso de erro
            import gc
            gc.collect()
            await asyncio.sleep(3)

async def external_keepalive():
    """Sistema de keep-alive externo otimizado"""
    import aiohttp
    ping_count = 0

    while True:
        try:
            # A cada 2 minutos (equilibrio ideal)
            await asyncio.sleep(120)
            ping_count += 1

            async with aiohttp.ClientSession() as session:
                endpoints_to_try = [
                    'http://0.0.0.0:8080/force-alive',
                    'http://0.0.0.0:8080/monitor',
                    'http://0.0.0.0:8080/keepalive', 
                    'http://0.0.0.0:8080/ping',
                    'http://0.0.0.0:8080/status',
                    'http://0.0.0.0:8080/heartbeat'
                ]

                success_count = 0
                for endpoint in endpoints_to_try:
                    try:
                        async with session.get(endpoint, timeout=8) as response:
                            if response.status == 200:
                                success_count += 1
                                logger.info(f"🌐 Keep-alive externo #{ping_count} OK via {endpoint}")

                                # Simular atividade MAIS INTENSA
                                await asyncio.sleep(0.3)

                                # Fazer requests adicionais para simular tráfego real
                                try:
                                    await asyncio.gather(
                                        session.get('http://0.0.0.0:8080/', timeout=2),
                                        session.get('http://0.0.0.0:8080/status', timeout=2),
                                        return_exceptions=True
                                    )
                                except:
                                    pass

                                if success_count >= 2:  # Se 2+ endpoints OK, parar
                                    break
                    except Exception as e:
                        logger.debug(f"Endpoint externo {endpoint} falhou: {e}")
                        continue

                if success_count == 0:
                    logger.error(f"🚨 Keep-alive externo #{ping_count} FALHOU TOTALMENTE!")

                    # Sistema de recuperação AGRESSIVO
                    recovery_attempts = 0
                    while recovery_attempts < 5 and success_count == 0:
                        recovery_attempts += 1
                        logger.warning(f"🆘 Tentativa de recuperação #{recovery_attempts}/5")

                        fallback_endpoints = [
                            'http://127.0.0.1:8080/ping',
                            'http://localhost:8080/ping',
                            'http://0.0.0.0:8080/force-alive'
                        ]

                        for endpoint in fallback_endpoints:
                            try:
                                async with session.get(endpoint, timeout=3) as response:
                                    if response.status == 200:
                                        logger.info(f"🆘 Recuperação via {endpoint} SUCESSO!")
                                        success_count = 1
                                        break
                            except:
                                continue

                        if success_count == 0:
                            await asyncio.sleep(2)

                    if success_count == 0:
                        logger.error("💀 TODOS OS SISTEMAS DE RECUPERAÇÃO FALHARAM!")

        except Exception as e:
            logger.error(f"❌ Keep-alive externo crítico: {e}")
            await asyncio.sleep(20)  # Espera menor para recuperação mais rápida

async def heartbeat_system():
    """Sistema de heartbeat otimizado para máxima disponibilidade"""
    import aiohttp
    heartbeat_count = 0

    while True:
        try:
            # Heartbeat a cada 3 minutos (equilibrio perfeito)
            await asyncio.sleep(180)
            heartbeat_count += 1

            # Simular atividade REAL do bot
            if bot.is_ready():
                # Atualizar status para simular atividade
                try:
                    activity_types = [
                        discord.ActivityType.watching,
                        discord.ActivityType.listening,
                        discord.ActivityType.playing
                    ]

                    await bot.change_presence(
                        status=discord.Status.online,
                        activity=discord.Activity(
                            type=random.choice(activity_types),
                            name=f"Heartbeat #{heartbeat_count} | Online 24/7"
                        )
                    )
                    logger.info(f"💓 Heartbeat #{heartbeat_count} + Status atualizado")

                    # Fazer atividade adicional para simular uso real
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.debug(f"Erro no status heartbeat: {e}")

            # Ping triplo via HTTP para garantir
            ping_success = 0
            try:
                async with aiohttp.ClientSession() as session:
                    endpoints = ['/health', '/heartbeat', '/ping']
                    for endpoint in endpoints:
                        try:
                            async with session.get(f'http://0.0.0.0:8080{endpoint}', timeout=5) as response:
                                if response.status == 200:
                                    ping_success += 1
                                    logger.debug(f"💓 HTTP heartbeat #{heartbeat_count} {endpoint} OK")
                        except:
                            continue

                    if ping_success == 0:
                        logger.warning(f"⚠️ Heartbeat #{heartbeat_count} HTTP falhou!")

            except Exception as e:
                logger.debug(f"Erro no HTTP heartbeat: {e}")

        except Exception as e:
            logger.warning(f"⚠️ Heartbeat system crítico: {e}")
            await asyncio.sleep(60)  # Espera menor para recuperação mais rápida

# Configuração do logging avançado
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
intents.typing = True

# Bot configuration
bot = commands.Bot(
    command_prefix=['RX', 'rx', '!', '.', '>', '<', '?', 'bot ', 'BOT ', 'Bot '],
    intents=intents,
    help_command=None,
    case_insensitive=True,
    strip_after_prefix=True
)

# Database connection pool to avoid locking issues
import threading
db_lock = threading.Lock()

def get_db_connection():
    """Get database connection with proper handling"""
    return sqlite3.connect('rxbot.db', timeout=30.0, check_same_thread=False)

# Database setup with proper error handling
def init_database():
    """Initialize database with proper error handling"""
    with db_lock:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

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

            # Events system
            cursor.execute('''CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                creator_id INTEGER,
                title TEXT,
                description TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                max_participants INTEGER DEFAULT 0,
                participants TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
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

            # Message logs (simplified)
            cursor.execute('''CREATE TABLE IF NOT EXISTS message_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                channel_id INTEGER,
                user_id INTEGER,
                message_id INTEGER,
                content TEXT,
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

            # Sistema de Clans
            cursor.execute('''CREATE TABLE IF NOT EXISTS clans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                name TEXT,
                tag TEXT,
                leader_id INTEGER,
                description TEXT,
                members TEXT DEFAULT '[]',
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                treasury INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

            # Desafios entre Clans
            cursor.execute('''CREATE TABLE IF NOT EXISTS clan_challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                challenger_clan_id INTEGER,
                challenged_clan_id INTEGER,
                challenger_user_id INTEGER,
                challenge_type TEXT,
                bet_amount INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                winner_clan_id INTEGER,
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

            # Auto-moderation rules
            cursor.execute('''CREATE TABLE IF NOT EXISTS auto_mod_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                rule_type TEXT,
                rule_data TEXT,
                punishment TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

            conn.commit()
            logger.info("✅ Database initialized successfully!")

        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
        finally:
            if conn:
                conn.close()

# Sistema EXTREMO anti-hibernação - Último recurso
async def extreme_anti_hibernation():
    """Sistema EXTREMO que impede hibernação usando múltiplas estratégias"""
    count = 0

    while True:
        try:
            await asyncio.sleep(45)  # A cada 45 segundos
            count += 1

            # Estratégia 1: Atividade de rede agressiva
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    # Fazer múltiplos requests simultâneos
                    tasks = []
                    endpoints = ['/ping', '/keepalive', '/monitor', '/force-alive']

                    for endpoint in endpoints:
                        task = session.get(f'http://0.0.0.0:8080{endpoint}', timeout=2)
                        tasks.append(task)

                    # Executar todos em paralelo
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    success_count = sum(1 for r in results if hasattr(r, 'status') and r.status == 200)

                    logger.info(f"🔥 Anti-hibernação extrema #{count}: {success_count}/{len(endpoints)} OK")

                    # Fechar responses
                    for result in results:
                        if hasattr(result, 'close'):
                            await result.close()

            except Exception as e:
                logger.debug(f"Erro na atividade de rede: {e}")

            # Estratégia 2: Atividade de CPU para simular processamento
            try:
                # Simular processamento leve
                _ = sum(i * 2 for i in range(1000))

                # Garbage collection forçado periodicamente
                if count % 10 == 0:
                    import gc
                    gc.collect()
                    logger.info(f"🧹 Limpeza de memória #{count // 10}")

            except Exception as e:
                logger.debug(f"Erro na atividade de CPU: {e}")

            # Estratégia 3: Atualizar status do bot para simular atividade
            try:
                if bot.is_ready() and count % 6 == 0:  # A cada ~4.5 minutos
                    activities = [
                        f"🔥 Sistema anti-hibernação #{count}",
                        f"💪 Uptime: {format_time(int((datetime.datetime.now() - global_stats['uptime_start']).total_seconds()))}",
                        f"🚀 {len(bot.guilds)} servidores | {len(set(bot.get_all_members()))} usuários",
                        f"⚡ Ultra-proteção ativa #{count}",
                        f"🛡️ Sistema imortal online"
                    ]

                    await bot.change_presence(
                        status=discord.Status.online,
                        activity=discord.Activity(
                            type=discord.ActivityType.watching,
                            name=random.choice(activities)
                        )
                    )
                    logger.info(f"🎭 Status atualizado para atividade #{count}")

            except Exception as e:
                logger.debug(f"Erro na atualização de status: {e}")

        except Exception as e:
            logger.error(f"❌ Erro no sistema anti-hibernação extremo: {e}")
            await asyncio.sleep(10)

# Monitor de sistema de emergência com auto-restart
async def emergency_system_monitor():
    """Monitor de emergência que pode reiniciar sistemas críticos"""
    monitor_count = 0
    critical_failures = 0

    while True:
        try:
            await asyncio.sleep(180)  # A cada 3 minutos
            monitor_count += 1

            logger.info(f"🔍 Monitor de emergência #{monitor_count}")

            # Verificar se Flask está respondendo
            flask_ok = False
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get('http://0.0.0.0:8080/ping', timeout=5) as response:
                        if response.status == 200:
                            flask_ok = True
            except:
                pass

            # Verificar se bot está conectado
            bot_ok = bot.is_ready()

            # Verificar latência
            latency_ok = bot.latency < 10.0 if bot_ok else False

            # Avaliar estado geral
            systems_ok = sum([flask_ok, bot_ok, latency_ok])

            if systems_ok >= 2:
                logger.info(f"✅ Monitor #{monitor_count}: {systems_ok}/3 sistemas OK")
                critical_failures = 0
            else:
                critical_failures += 1
                logger.error(f"🚨 Monitor #{monitor_count}: APENAS {systems_ok}/3 sistemas OK! (Falha #{critical_failures})")

                # Se muitas falhas consecutivas, ações drásticas
                if critical_failures >= 3:
                    logger.error("💀 EMERGÊNCIA CRÍTICA! Executando recuperação total...")

                    try:
                        # Força garbage collection agressivo
                        import gc
                        gc.collect()

                        # Tentar "acordar" o sistema com requests externos
                        import requests
                        for i in range(5):
                            try:
                                requests.get('http://0.0.0.0:8080/force-alive', timeout=3)
                                await asyncio.sleep(1)
                            except:
                                pass

                        # Notificar canal de alerta se possível
                        if bot.is_ready():
                            try:
                                channel = bot.get_channel(CHANNEL_ID_ALERTA)
                                if channel:
                                    embed = create_embed(
                                        "🚨 EMERGÊNCIA CRÍTICA DETECTADA",
                                        f"Sistema de emergência acionado!\n"
                                        f"**Monitor:** #{monitor_count}\n"
                                        f"**Falhas consecutivas:** {critical_failures}\n"
                                        f"**Flask OK:** {'✅' if flask_ok else '❌'}\n"
                                        f"**Bot OK:** {'✅' if bot_ok else '❌'}\n"
                                        f"**Latência OK:** {'✅' if latency_ok else '❌'}\n"
                                        f"**Recuperação:** Iniciada automaticamente",
                                        color=0xff0000
                                    )
                                    await channel.send(embed=embed)
                            except:
                                pass

                        logger.info("🆘 Recuperação de emergência executada!")
                        critical_failures = 0

                    except Exception as e:
                        logger.error(f"Erro na recuperação de emergência: {e}")

        except Exception as e:
            logger.error(f"❌ Erro no monitor de emergência: {e}")
            await asyncio.sleep(30)

# Initialize database
init_database()

# Global variables for bot state
global_stats = {
    'commands_used': 0,
    'messages_processed': 0,
    'guilds_joined': 0,
    'uptime_start': datetime.datetime.now(),
    'total_users': 0,
    'total_channels': 0
}

# Memory system for AI conversations - EXPANDIDO
conversation_memory = defaultdict(lambda: deque(maxlen=50))
user_personalities = defaultdict(dict)

# Active games and sessions
active_games = {}
music_queues = defaultdict(list)
voice_clients = {}

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

# Sistema de Ranks - XP necessário para cada rank
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
    """Determina o rank baseado no XP"""
    current_rank = 1
    for rank_id, rank_data in RANK_SYSTEM.items():
        if xp >= rank_data["xp"]:
            current_rank = rank_id
        else:
            break
    return current_rank, RANK_SYSTEM[current_rank]

# Palavras que geram warn automático
AUTO_WARN_WORDS = [
    'spam', 'flood', 'hack', 'cheat', 'trapaça',
    'xingamento', 'ofensa', 'discriminação'
]

# Sistema de IA Expandido com 200+ tópicos
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
            'sorteio': ['sorteio', 'giveaway', 'concurso', 'prêmio', 'ganhar'],
            'tecnologia': ['programação', 'código', 'python', 'javascript', 'html', 'css'],
            'games': ['minecraft', 'fortnite', 'lol', 'valorant', 'csgo', 'free fire'],
            'música': ['música', 'cantando', 'banda', 'artista', 'som', 'playlist']
        }

        self.responses = {
            'cumprimento': [
                "Olá! 👋 Como posso ajudar você hoje?",
                "Oi! 😊 Em que posso ser útil?",
                "Salve! 🔥 Pronto para ajudar você!",
                "Hey! 🚀 O que precisamos fazer hoje?",
                "Olá! 🌟 Como está seu dia?",
                "Oi! 💫 Que bom te ver por aqui!"
            ],
            'pergunta': [
                "Ótima pergunta! Vou explicar de forma clara:",
                "Interessante! Deixe-me esclarecer isso:",
                "Perfeito! Aqui está uma explicação detalhada:",
                "Excelente dúvida! Vou te ajudar:",
                "Que pergunta inteligente! Vou responder:",
                "Adorei sua curiosidade! Aqui vai a resposta:"
            ],
            'ajuda': [
                "Claro! Estou aqui para ajudar. Vou te guiar passo a passo:",
                "Sem problemas! Vou explicar tudo detalhadamente:",
                "Pode contar comigo! Aqui está a solução:",
                "Tranquilo! Vou te mostrar como fazer:",
                "Com certeza! Vou te dar todo suporte necessário:",
                "Sempre à disposição para ajudar! Vamos lá:"
            ],
            'positivo': [
                "Fico feliz em ajudar! 😊",
                "De nada! Sempre à disposição! 💪",
                "Que bom que foi útil! 🎉",
                "Por nada! Pode contar comigo sempre! ✨",
                "Fico contente que gostou! 😄",
                "É sempre um prazer ajudar! 🌟"
            ]
        }

    def analyze_message(self, message_content):
        """Analisa a mensagem e detecta o contexto"""
        content_lower = message_content.lower()
        detected_contexts = []

        for context, keywords in self.context_patterns.items():
            if any(keyword in content_lower for keyword in keywords):
                detected_contexts.append(context)

        return detected_contexts if detected_contexts else ['geral']

    def generate_response(self, message_content, user_data=None):
        """Gera uma resposta inteligente baseada no contexto"""
        contexts = self.analyze_message(message_content)
        primary_context = contexts[0]

        if len(message_content.strip()) <= 3:
            return random.choice([
                "Entendi! 😄 Como posso ajudar?",
                "Haha! 😊 Em que posso ser útil?",
                "Legal! 🎉 Vamos conversar?",
                "Interessante! 🤔 Me conte mais!"
            ])

        if primary_context in self.responses:
            return random.choice(self.responses[primary_context])

        return "Interessante! Como posso te ajudar hoje? Use `RXajuda` para ver todos os comandos!"

ai_system = AdvancedAI()

# Background tasks
@tasks.loop(minutes=5)
async def update_status():
    """Atualiza status do bot periodicamente"""
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

@tasks.loop(hours=6)
async def backup_database():
    """Backup automático do banco de dados"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_rxbot_{timestamp}.db"
        
        with db_lock:
            conn = get_db_connection()
            backup_conn = sqlite3.connect(backup_name)
            conn.backup(backup_conn)
            conn.close()
            backup_conn.close()
        
        logger.info(f"✅ Backup criado: {backup_name}")
    except Exception as e:
        logger.error(f"Erro no backup: {e}")

@tasks.loop(minutes=1)
async def check_reminders():
    """Verifica lembretes"""
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
async def check_giveaways():
    """Verifica sorteios que terminaram"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            now = datetime.datetime.now()
            cursor.execute('''
                SELECT * FROM giveaways 
                WHERE status = 'active' AND end_time <= ?
            ''', (now,))
            
            finished_giveaways = cursor.fetchall()
            
            for giveaway in finished_giveaways:
                giveaway_id, guild_id, channel_id, creator_id, title, prize, winners_count, end_time, message_id, participants_json, status, created_at = giveaway
                
                try:
                    channel = bot.get_channel(channel_id)
                    if not channel:
                        continue
                    
                    message = await channel.fetch_message(message_id)
                    if not message:
                        continue
                    
                    # Obter participantes das reações
                    participants = []
                    for reaction in message.reactions:
                        if str(reaction.emoji) == "🎉":
                            async for user in reaction.users():
                                if not user.bot:
                                    participants.append(user.id)
                    
                    if len(participants) < winners_count:
                        winners = participants
                    else:
                        winners = random.sample(participants, winners_count)
                    
                    # Anunciar vencedores
                    if winners:
                        winner_mentions = [f"<@{winner_id}>" for winner_id in winners]
                        embed = create_embed(
                            f"🎉 Sorteio Finalizado: {title}",
                            f"**Prêmio:** {prize}\n"
                            f"**Vencedor(es):** {', '.join(winner_mentions)}\n"
                            f"**Participantes:** {len(participants)}",
                            color=0xffd700
                        )
                    else:
                        embed = create_embed(
                            f"😢 Sorteio Cancelado: {title}",
                            f"**Prêmio:** {prize}\n"
                            f"**Motivo:** Nenhum participante válido",
                            color=0xff6b6b
                        )
                    
                    await channel.send(embed=embed)
                    
                    # Marcar como finalizado
                    cursor.execute('UPDATE giveaways SET status = ? WHERE id = ?', ('finished', giveaway_id))
                    
                except Exception as e:
                    logger.error(f"Erro ao finalizar sorteio {giveaway_id}: {e}")
            
            conn.commit()
            conn.close()
    except Exception as e:
        logger.error(f"Erro check_giveaways: {e}")

# Utility functions with proper database handling
def get_user_data(user_id):
    """Get user data with proper error handling"""
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
    """Update user data with proper error handling"""
    conn = None
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Check if user exists
            cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
            if not cursor.fetchone():
                cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))

            # Update fields
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
    """Add XP with level and rank calculation"""
    try:
        data = get_user_data(user_id)
        if not data:
            update_user_data(user_id, xp=amount, level=1)
            return False, 1, False, 1

        current_xp = data[2]
        current_level = data[3]
        new_xp = current_xp + amount

        # Calculate new level
        new_level = int(math.sqrt(new_xp / 100)) + 1
        leveled_up = new_level > current_level

        # Calculate rank progression
        old_rank_id, old_rank = get_user_rank(current_xp)
        new_rank_id, new_rank = get_user_rank(new_xp)
        rank_up = new_rank_id > old_rank_id

        update_user_data(user_id, xp=new_xp, level=new_level)
        return leveled_up, new_level, rank_up, new_rank_id
    except Exception as e:
        logger.error(f"Error adding XP: {e}")
        return False, 1, False, 1

def format_time(seconds):
    """Format seconds to readable time"""
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
    """Create embed with standard formatting"""
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

# Função para detectar infrações automáticas
def check_auto_violations(message_content):
    """Verifica se a mensagem contém violações automáticas"""
    content_lower = message_content.lower()
    violations = []

    # Verificar palavras proibidas
    for word in AUTO_WARN_WORDS:
        if word in content_lower:
            violations.append(f"Palavra proibida: {word}")

    # Verificar spam de caps
    if len(message_content) > 20 and message_content.isupper():
        violations.append("Spam de maiúsculas")

    return violations

# Event handlers
@bot.event
async def on_message(message):
    """Processar mensagens para XP, IA e moderação"""
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

    # Sistema de IA (responder quando mencionado)
    if bot.user.mentioned_in(message) and not message.mention_everyone:
        try:
            content = message.content.replace(f'<@{bot.user.id}>', '').strip()
            if content:
                response = ai_system.generate_response(content)
                await message.reply(response)
        except Exception as e:
            logger.error(f"Erro no sistema IA: {e}")

    # Processar comandos
    await bot.process_commands(message)

@bot.event
async def on_ready():
    logger.info(f"🤖 RXbot está online! Conectado como {bot.user}")
    logger.info(f"📊 Conectado em {len(bot.guilds)} servidores")
    logger.info(f"👥 Servindo {len(set(bot.get_all_members()))} usuários únicos")

    try:
        channel = bot.get_channel(CHANNEL_ID_ALERTA)
        if channel:
            embed = create_embed(
                "🚀 RXbot Online!",
                f"Bot reiniciado e totalmente operacional!\n\n"
                f"**📊 Estatísticas:**\n"
                f"• Servidores: {len(bot.guilds)}\n"
                f"• Usuários: {len(set(bot.get_all_members()))}\n"
                f"• Latência: {round(bot.latency * 1000, 2)}ms\n"
                f"• Versão: 2.1.0 (Estável)\n\n"
                f"**🛡️ Sistemas ativos:**\n"
                f"• ✅ Auto-ping\n"
                f"• ✅ Keep-alive\n"
                f"• ✅ Monitor de saúde\n"
                f"• ✅ Sistema anti-crash\n\n"
                f"**Data:** <t:{int(datetime.datetime.now().timestamp())}:F>",
                color=0x00ff00
            )
            await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Erro ao enviar alerta de reinício: {e}")

    # Update global stats
    global_stats['total_users'] = len(set(bot.get_all_members()))
    global_stats['total_channels'] = len(list(bot.get_all_channels()))

    # Start background tasks apenas uma vez
    if not hasattr(bot, '_tasks_started'):
        bot._tasks_started = True
        try:
            update_status.start()
            backup_database.start()
            check_reminders.start()
            check_giveaways.start()
            logger.info("✅ Background tasks iniciados")
        except Exception as e:
            logger.error(f"Erro ao iniciar background tasks: {e}")

    # Iniciar TODOS os sistemas de proteção anti-hibernação apenas uma vez
    if not hasattr(bot, '_protection_started'):
        bot._protection_started = True
        
        # Criar tasks de proteção
        protection_tasks = [
            auto_ping(),
            external_keepalive(), 
            heartbeat_system(),
            health_monitor(),
            emergency_keeper(),
            extreme_anti_hibernation(),
            emergency_system_monitor(),
            auto_reconnect_system()  # Novo sistema de reconexão
        ]
        
        for task in protection_tasks:
            asyncio.create_task(task)
            
        logger.info("🛡️ Sistemas de proteção iniciados")

    # Set initial status com retry
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
    
    # Executar limpeza de memória inicial
    try:
        import gc
        gc.collect()
        logger.info("🧹 Limpeza de memória inicial concluída")
    except:
        pass

@bot.event
async def on_disconnect():
    logger.error("🚨 BOT DESCONECTADO DO DISCORD!")
    try:
        # Tentar notificar antes de perder conexão totalmente
        channel = bot.get_channel(CHANNEL_ID_ALERTA)
        if channel:
            await channel.send("❌ O bot foi **desconectado** do Discord! Tentando reconectar automaticamente...")
    except Exception as e:
        logger.error(f"Erro ao enviar alerta de desconexão: {e}")

@bot.event
async def on_resumed():
    logger.info("🔄 BOT RECONECTADO AO DISCORD!")
    try:
        channel = bot.get_channel(CHANNEL_ID_ALERTA)
        if channel:
            embed = create_embed(
                "🔄 Reconexão Automática",
                f"Bot reconectou ao Discord com sucesso!\n"
                f"**Tempo:** <t:{int(datetime.datetime.now().timestamp())}:F>\n"
                f"**Status:** ✅ Totalmente operacional",
                color=0x00ff00
            )
            await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Erro ao enviar alerta de reconexão: {e}")

# Sistema de reconexão automática melhorado
async def auto_reconnect_system():
    """Sistema que monitora e força reconexão se necessário"""
    disconnect_count = 0
    
    while True:
        try:
            await asyncio.sleep(45)  # Verificar a cada 45 segundos
            
            if not bot.is_ready():
                disconnect_count += 1
                logger.warning(f"⚠️ Bot não está ready! Desconexão #{disconnect_count}")
                
                if disconnect_count >= 3:
                    logger.error("🔄 Múltiplas desconexões detectadas! Forçando reconexão...")
                    
                    try:
                        # Tentar fechar e reconectar
                        await bot.close()
                        await asyncio.sleep(5)
                        
                        # Reiniciar conexão
                        logger.info("🔄 Tentando reconectar...")
                        disconnect_count = 0
                        
                    except Exception as e:
                        logger.error(f"Erro na reconexão forçada: {e}")
                        
            else:
                disconnect_count = 0  # Reset contador se bot está OK
                
        except Exception as e:
            logger.error(f"Erro no sistema de reconexão: {e}")
            await asyncio.sleep(30)

@bot.event
async def on_guild_join(guild):
    global_stats['guilds_joined'] += 1
    logger.info(f"📈 Entrei no servidor: {guild.name} ({guild.id})")

    # Initialize guild data
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
async def on_reaction_add(reaction, user):
    """Gerenciar reações para tickets e outros sistemas"""
    if user.bot:
        return

    message = reaction.message
    
    # Sistema de tickets
    if message.id in active_games:
        game_data = active_games[message.id]
        
        if game_data['user'] != user.id:
            return
        
        if game_data['type'] == 'ticket_creation':
            emoji_to_motivo = {
                "🐛": "Bug/Erro no bot",
                "💰": "Problema com economia", 
                "⚖️": "Denúncia/Moderação",
                "💡": "Sugestão/Ideia",
                "❓": "Dúvida geral",
                "🛠️": "Suporte técnico",
                "👑": "RXticket só para tier"
            }
            
            if str(reaction.emoji) in emoji_to_motivo:
                motivo = emoji_to_motivo[str(reaction.emoji)]
                
                # Criar ticket
                try:
                    ctx_mock = type('MockCtx', (), {
                        'guild': message.guild,
                        'channel': message.channel,
                        'send': message.channel.send
                    })()
                    
                    await create_ticket_channel(ctx_mock, motivo, user)
                    del active_games[message.id]
                except Exception as e:
                    logger.error(f"Erro ao criar ticket: {e}")
        
        elif game_data['type'] == 'ticket_confirmation':
            if str(reaction.emoji) == "✅":
                motivo = game_data['motivo']
                
                try:
                    ctx_mock = type('MockCtx', (), {
                        'guild': message.guild,
                        'channel': message.channel,
                        'send': message.channel.send
                    })()
                    
                    await create_ticket_channel(ctx_mock, motivo, user)
                    del active_games[message.id]
                except Exception as e:
                    logger.error(f"Erro ao criar ticket: {e}")
            
            elif str(reaction.emoji) == "❌":
                embed = create_embed("❌ Ticket Cancelado", "Criação de ticket cancelada pelo usuário.", color=0xff6b6b)
                await message.edit(embed=embed)
                del active_games[message.id]
        
        elif game_data['type'] == 'clear_confirmation':
            if str(reaction.emoji) == "✅":
                amount = game_data['amount']
                channel = message.guild.get_channel(game_data['channel'])
                
                try:
                    await channel.purge(limit=amount + 1)  # +1 para incluir a mensagem de confirmação
                    
                    confirm_embed = create_embed(
                        "🧹 Limpeza Concluída",
                        f"**{amount} mensagens foram deletadas com sucesso!**",
                        color=0x00ff00
                    )
                    await channel.send(embed=confirm_embed, delete_after=5)
                    del active_games[message.id]
                except Exception as e:
                    logger.error(f"Erro na limpeza: {e}")
            
            elif str(reaction.emoji) == "❌":
                embed = create_embed("❌ Limpeza Cancelada", "Operação cancelada pelo usuário.", color=0xff6b6b)
                await message.edit(embed=embed)
                del active_games[message.id]
    
    # Sistema de fechar tickets
    if str(reaction.emoji) == "🔒" and message.channel.name.startswith('ticket-'):
        if not user.guild_permissions.manage_channels:
            return
        
        embed = create_embed(
            "🔒 Ticket Fechado",
            f"Ticket fechado por {user.mention}\n"
            f"**Data:** <t:{int(datetime.datetime.now().timestamp())}:F>",
            color=0xff6b6b
        )
        
        await message.channel.send(embed=embed)
        await asyncio.sleep(3)
        await message.channel.delete()

@bot.event
async def on_member_join(member):
    """Enviar mensagem de boas-vindas personalizada quando alguém entrar no servidor"""
    if member.bot:
        return

    try:
        # Canal específico para boas-vindas
        welcome_channel_id = 1398027575028220013
        welcome_channel = bot.get_channel(welcome_channel_id)

        if not welcome_channel:
            logger.error(f"Canal de boas-vindas {welcome_channel_id} não encontrado!")
            return

        # Buscar dados do usuário para personalizar ainda mais
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
            f"🎯 Explore nossos +250 comandos com `RXajuda`\n"
            f"💰 Comece sua jornada econômica com `RXdaily`\n\n"
            f"*Membro #{member.guild.member_count} do {member.guild.name}!*",

            f"🌟 **Olá {member.mention}! Seja muito bem-vindo(a)!**\n\n"
            f"🎨 Pronto para uma experiência incrível?\n"
            f"🤖 Converse comigo mencionando @RXbot\n"
            f"🏆 Participe dos rankings e ganhe reputação!\n\n"
            f"*Agradecemos por escolher o {member.guild.name}!*",

            f"🎪 **Chegou mais um aventureiro! {member.mention}**\n\n"
            f"🎭 Bem-vindo à nossa comunidade!\n"
            f"🎲 Jogue, se divirta e faça novos amigos\n"
            f"🎁 Participe dos sorteios e ganhe prêmios\n\n"
            f"*{member.guild.name} está ainda melhor com você aqui!*"
        ]

        # Escolher mensagem aleatória
        welcome_message = random.choice(welcome_messages)

        # Criar embed personalizado
        embed = create_embed(
            f"🎉 Bem-vindo(a) ao {member.guild.name}!",
            welcome_message,
            color=0x00ff00
        )

        # Adicionar avatar do membro
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)

        # Adicionar informações adicionais
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

        # Enviar mensagem de boas-vindas
        await welcome_channel.send(embed=embed)

        # Log do evento
        logger.info(f"👋 Boas-vindas enviadas para {member.name} em {member.guild.name}")

        # Dar XP inicial para novos membros
        add_xp(member.id, 25)  # XP bônus para novos membros

    except Exception as e:
        logger.error(f"Erro ao enviar boas-vindas para {member.name}: {e}")

        # Tentar enviar mensagem simples se o embed falhar
        try:
            if welcome_channel:
                await welcome_channel.send(f"🎉 Bem-vindo(a) {member.mention} ao {member.guild.name}! 🎉")
        except:
            pass

# Sistema de monitoramento de saúde para detectar problemas
async def health_monitor():
    """Monitor de saúde que detecta quando o bot está em risco"""
    last_activity = datetime.datetime.now()
    consecutive_issues = 0

    while True:
        try:
            await asyncio.sleep(45)  # Verificar a cada 45 segundos

            current_time = datetime.datetime.now()
            time_since_activity = (current_time - last_activity).total_seconds()

            # Verificar se bot está respondendo
            if bot.is_ready():
                # Verificar latência
                if bot.latency > 10.0:  # 10+ segundos é crítico
                    consecutive_issues += 1
                    logger.warning(f"🩺 Latência crítica: {bot.latency * 1000:.2f}ms ({consecutive_issues}/3)")
                else:
                    consecutive_issues = 0
                    last_activity = current_time

                # Se muitos problemas consecutivos
                if consecutive_issues >= 3:
                    logger.error("🚨 SAÚDE CRÍTICA! Iniciando recuperação de emergência...")

                    # Forçar limpeza de memória
                    import gc
                    gc.collect()

                    # Resetar contador
                    consecutive_issues = 0

                    # Notificar canal de alerta
                    try:
                        channel = bot.get_channel(CHANNEL_ID_ALERTA)
                        if channel:
                            embed = create_embed(
                                "🚨 Sistema de Saúde - Alerta Crítico",
                                f"Problemas detectados no bot!\n"
                                f"**Latência:** {bot.latency * 1000:.2f}ms\n"
                                f"**Ação:** Recuperação automática iniciada\n"
                                f"**Status:** Tentando estabilizar...",
                                color=0xff0000
                            )
                            await channel.send(embed=embed)
                    except:
                        pass
            else:
                consecutive_issues += 1
                logger.error(f"🩺 Bot não está ready! ({consecutive_issues}/5)")

                if consecutive_issues >= 5:
                    logger.error("💀 BOT CRÍTICO! Não está ready há muito tempo!")
                    consecutive_issues = 0

        except Exception as e:
            logger.error(f"❌ Erro no health monitor: {e}")
            await asyncio.sleep(30)

# Sistema de emergência - último recurso
async def emergency_keeper():
    """Sistema de emergência que atua quando tudo mais falha"""
    emergency_count = 0

    while True:
        try:
            # Verificar a cada 5 minutos
            await asyncio.sleep(300)
            emergency_count += 1

            # Verificar se outros sistemas estão funcionando
            try:
                import aiohttp
                systems_ok = 0

                async with aiohttp.ClientSession() as session:
                    # Testar endpoints críticos
                    critical_endpoints = ['/ping', '/status', '/monitor']

                    for endpoint in critical_endpoints:
                        try:
                            async with session.get(f'http://0.0.0.0:8080{endpoint}', timeout=3) as response:
                                if response.status == 200:
                                    systems_ok += 1
                        except:
                            continue

                    # Se menos de 2 sistemas OK = EMERGÊNCIA
                    if systems_ok < 2:
                        logger.error(f"🆘 EMERGÊNCIA #{emergency_count}! Apenas {systems_ok}/3 sistemas OK")

                        # Ações de emergência
                        for i in range(5):
                            try:
                                async with session.get('http://0.0.0.0:8080/force-alive', timeout=2):
                                    pass
                                await asyncio.sleep(1)
                            except:
                                continue

                        logger.info(f"🆘 Emergência #{emergency_count} - Pings forçados enviados")
                    else:
                        logger.info(f"🆘 Emergência #{emergency_count} - Sistemas OK ({systems_ok}/3)")

            except Exception as e:
                logger.error(f"Erro no sistema de emergência: {e}")

        except Exception as e:
            logger.error(f"❌ Erro crítico no emergency keeper: {e}")
            await asyncio.sleep(120)

# ============ SISTEMA DE TICKETS COMPLETO ============
@bot.command(name='testetier', aliases=['rxticketier', 'tickettier'])
async def create_tier_ticket(ctx):
    """Criar ticket específico para tier"""
    motivo = "RXticket só para tier"

    # Sistema de confirmação para ticket tier
    embed = create_embed(
        "🎟️ Confirmação - Ticket Tier",
        f"""**👑 TICKET ESPECÍFICO PARA TIER**

**📋 Detalhes do ticket:**
**Motivo:** {motivo}
**Solicitante:** {ctx.author.mention}
**Tipo:** Suporte especializado tier

**ℹ️ O que vai acontecer:**
• Canal privado será criado automaticamente
• Apenas você e a staff tier poderão ver
• Atendimento prioritário garantido
• Suporte especializado para questões tier

**⚠️ Importante:**
• Este ticket é para assuntos relacionados a tier
• Descreva claramente sua questão
• Aguarde a resposta da equipe especializada

**Deseja realmente criar este ticket tier?**""",
        color=0xffd700
    )

    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    # Armazenar para processar confirmação
    active_games[msg.id] = {
        'type': 'ticket_tier_confirmation',
        'user': ctx.author.id,
        'channel': ctx.channel.id,
        'motivo': motivo
    }

@bot.command(name='ticket', aliases=['rxticket'])
async def create_ticket(ctx, *, motivo=None):
    """Criar ticket de suporte com emoji"""
    if not motivo:
        embed = create_embed(
            "🎟️ Sistema de Tickets",
            """**Como criar um ticket:**
`RXticket <motivo>`

**Exemplos:**
• `RXticket Problema com economia`
• `RXticket Bug no bot`
• `RXticket Sugestão de melhoria`
• `RXticket Denúncia de usuário`

**Ou use o sistema simplificado:**
Digite apenas `RXticket` e escolha uma opção! ⬇️""",
            color=0x7289da
        )

        # Sistema simplificado com emojis
        embed.add_field(
            name="🎯 Criação Rápida",
            value="Reaja com o emoji correspondente:\n"
                  "🐛 - Bug/Erro no bot\n"
                  "💰 - Problema com economia\n"
                  "⚖️ - Denúncia/Moderação\n"
                  "💡 - Sugestão/Ideia\n"
                  "❓ - Dúvida geral\n"
                  "🛠️ - Suporte técnico\n"
                  "👑 - RXticket só para tier",
            inline=False
        )

        msg = await ctx.send(embed=embed)

        # Adicionar reações
        reactions = ["🐛", "💰", "⚖️", "💡", "❓", "🛠️", "👑"]
        for reaction in reactions:
            await msg.add_reaction(reaction)

        # Armazenar para processar depois
        active_games[msg.id] = {
            'type': 'ticket_creation',
            'user': ctx.author.id,
            'channel': ctx.channel.id
        }
        return

    # Sistema de confirmação para ticket com motivo específico
    embed = create_embed(
        "🎟️ Confirmação de Ticket",
        f"""**📋 Você está prestes a criar um ticket:**

**Motivo:** {motivo}
**Solicitante:** {ctx.author.mention}

**ℹ️ O que vai acontecer:**
• Um canal privado será criado
• Apenas você e a staff poderão ver
• A equipe será notificada automaticamente
• Você receberá suporte personalizado

**⚠️ Importante:**
• Descreva seu problema claramente
• Seja respeitoso com a equipe
• Aguarde a resposta da staff

**Deseja realmente criar este ticket?**""",
        color=0xffaa00
    )

    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    # Armazenar para processar confirmação
    active_games[msg.id] = {
        'type': 'ticket_confirmation',
        'user': ctx.author.id,
        'channel': ctx.channel.id,
        'motivo': motivo
    }

async def create_ticket_channel(ctx, motivo, user):
    """Create ticket channel"""
    # Obter guild de forma mais robusta
    guild = None

    # Tentar múltiplas formas de obter o guild
    if hasattr(ctx, 'guild') and ctx.guild:
        guild = ctx.guild
    elif hasattr(ctx, 'channel') and ctx.channel and hasattr(ctx.channel, 'guild'):
        guild = ctx.channel.guild
    else:
        # Fallback: buscar guild onde o usuário está presente
        for g in bot.guilds:
            try:
                member = g.get_member(user.id)
                if member:
                    guild = g
                    break
            except:
                continue

    # Verificar se guild existe e é válido
    if not guild or not hasattr(guild, 'categories'):
        logger.error(f"Guild inválido ou None: {guild}")
        try:
            # Tentar obter guild do contexto da mensagem original se possível
            if hasattr(ctx, 'channel') and hasattr(ctx.channel, 'guild'):
                guild = ctx.channel.guild

            # Se ainda não temos guild válido, erro crítico
            if not guild or not hasattr(guild, 'categories'):
                embed = create_embed("❌ Erro Crítico", "Erro interno: servidor não encontrado ou inválido", color=0xff0000)
                if hasattr(ctx, 'send'):
                    await ctx.send(embed=embed)
                elif hasattr(ctx, 'channel'):
                    await ctx.channel.send(embed=embed)
                return
        except Exception as e:
            logger.error(f"Erro crítico na validação de guild: {e}")
            return

    # Verificar se usuário tem ticket prioritário
    user_data = get_user_data(user.id)
    priority = False
    if user_data:
        try:
            settings = json.loads(user_data[11]) if user_data[11] else {}
            if settings.get('priority_tickets', 0) > 0:
                priority = True
                settings['priority_tickets'] = settings['priority_tickets'] - 1
                update_user_data(user.id, settings=settings)
        except:
            pass

    # Criar categoria se não existir
    category = discord.utils.get(guild.categories, name="📋 Tickets")
    if not category:
        try:
            category = await guild.create_category("📋 Tickets")
        except Exception as e:
            logger.error(f"Erro ao criar categoria de tickets: {e}")
            category = None

    # Criar canal do ticket
    ticket_name = f"ticket-{user.name}-{random.randint(1000, 9999)}"

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    # Adicionar staff aos overwrites
    for role in guild.roles:
        if any(perm_name in role.name.lower() for perm_name in ['admin', 'mod', 'staff']) or role.permissions.administrator:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    try:
        ticket_channel = await guild.create_text_channel(
            ticket_name,
            category=category,
            overwrites=overwrites
        )
    except Exception as e:
        embed = create_embed("❌ Erro", f"Não foi possível criar o ticket: {str(e)}", color=0xff0000)
        await ctx.send(embed=embed)
        return

    # Salvar ticket no banco
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tickets (guild_id, creator_id, channel_id, reason)
                VALUES (?, ?, ?, ?)
            ''', (guild.id, user.id, ticket_channel.id, motivo))
            ticket_id = cursor.lastrowid
            conn.commit()
            conn.close()
    except Exception as e:
        logger.error(f"Error saving ticket: {e}")
        ticket_id = "ERRO"

    # Embed inicial do ticket
    priority_text = "🎫 PRIORITÁRIO " if priority else ""
    embed = create_embed(
        f"🎟️ {priority_text}Ticket #{ticket_id}",
        f"""**Criado por:** {user.mention}
**Motivo:** {motivo}
**Status:** 🟢 Aberto
**Criado em:** <t:{int(datetime.datetime.now().timestamp())}:F>

📋 **Informações:**
• Este ticket foi criado automaticamente
• A staff será notificada em breve
• Para fechar o ticket, reaja com 🔒

{"🎫 **Este ticket tem prioridade!**" if priority else ""}

⚠️ **Regras do ticket:**
• Seja respeitoso e educado
• Descreva seu problema claramente
• Aguarde a resposta da staff
• Não spam ou flood""",
        color=0xffd700 if priority else 0x7289da
    )

    msg = await ticket_channel.send(f"{user.mention}", embed=embed)
    await msg.add_reaction("🔒")  # Para fechar

    # Notificar que ticket foi criado
    confirm_embed = create_embed(
        "✅ Ticket Criado!",
        f"{priority_text}Seu ticket foi criado em {ticket_channel.mention}!\n"
        f"**ID:** #{ticket_id}\n"
        f"A staff será notificada automaticamente.",
        color=0x00ff00
    )

    # Tentar enviar no canal original
    try:
        if hasattr(ctx, 'send'):
            await ctx.send(embed=confirm_embed, delete_after=10)
        elif hasattr(ctx, 'channel'):
            await ctx.channel.send(embed=confirm_embed, delete_after=10)
    except:
        pass

# ============ COMANDOS DE TESTE ============
@bot.command(name='diagnostico', aliases=['diag', 'health'])
@commands.has_permissions(administrator=True)
async def diagnostico_completo(ctx):
    """[ADMIN] Diagnóstico completo do sistema"""
    embed = create_embed(
        "🔍 Iniciando Diagnóstico Completo",
        "Verificando todos os sistemas...",
        color=0xffaa00
    )
    msg = await ctx.send(embed=embed)

    resultados = []

    # 1. Teste Database
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users')
            user_count = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM tickets')
            ticket_count = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM giveaways')
            giveaway_count = cursor.fetchone()[0]
            conn.close()
        resultados.append(f"✅ **Database:** {user_count} users, {ticket_count} tickets, {giveaway_count} sorteios")
    except Exception as e:
        resultados.append(f"❌ **Database:** {str(e)[:50]}...")

    # 2. Teste Keep-alive
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get('http://0.0.0.0:8080/ping', timeout=5) as response:
                if response.status == 200:
                    resultados.append("✅ **Keep-alive:** Porta 8080 ativa")
                else:
                    resultados.append(f"⚠️ **Keep-alive:** Status {response.status}")
    except Exception as e:
        resultados.append(f"❌ **Keep-alive:** {str(e)[:50]}...")

    # 3. Teste Memória
    try:
        import psutil
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent()
        resultados.append(f"✅ **Sistema:** RAM {memory.percent}%, CPU {cpu}%")
    except Exception as e:
        resultados.append(f"⚠️ **Sistema:** Dados não disponíveis")

    # 4. Teste Conexão Discord
    latency = round(bot.latency * 1000, 2)
    if latency < 200:
        resultados.append(f"✅ **Discord:** {latency}ms - Excelente")
    else:
        resultados.append(f"⚠️ **Discord:** {latency}ms - Lenta")

    # 5. Teste Background Tasks
    running_tasks = []
    if update_status.is_running():
        running_tasks.append("Status")
    if backup_database.is_running():
        running_tasks.append("Backup")
    if check_reminders.is_running():
        running_tasks.append("Reminders")
    if check_giveaways.is_running():
        running_tasks.append("Giveaways")

    if len(running_tasks) >= 3:
        resultados.append(f"✅ **Tasks:** {len(running_tasks)}/4 ativos")
    else:
        resultados.append(f"⚠️ **Tasks:** {len(running_tasks)}/4 ativos")

    # 6. Teste Arquivos Críticos
    import os
    arquivos_criticos = ['rxbot.db', 'main.py']
    arquivos_ok = 0
    for arquivo in arquivos_criticos:
        if os.path.exists(arquivo):
            arquivos_ok += 1

    if arquivos_ok == len(arquivos_criticos):
        resultados.append("✅ **Arquivos:** Todos presentes")
    else:
        resultados.append(f"⚠️ **Arquivos:** {arquivos_ok}/{len(arquivos_criticos)} encontrados")

    # Análise final
    sucessos = len([r for r in resultados if r.startswith("✅")])
    avisos = len([r for r in resultados if r.startswith("⚠️")])
    erros = len([r for r in resultados if r.startswith("❌")])

    if erros == 0 and avisos <= 1:
        status = "🎉 SISTEMA PERFEITO!"
        cor = 0x00ff00
    elif erros <= 1:
        status = "⚠️ Sistema funcional com avisos"
        cor = 0xffaa00
    else:
        status = "❌ Sistema com problemas"
        cor = 0xff0000

    embed_final = create_embed(
        "🏥 Diagnóstico Completo - Resultado",
        f"""**{status}**

**📊 Resumo:**
• ✅ OK: {sucessos}
• ⚠️ Avisos: {avisos}
• ❌ Erros: {erros}

**📋 Detalhes:**
""" + "\n".join(resultados) + f"""

**📈 Performance:**
• Uptime: {format_time(int((datetime.datetime.now() - global_stats['uptime_start']).total_seconds()))}
• Comandos: {global_stats['commands_used']:,}
• Mensagens: {global_stats['messages_processed']:,}

**🔧 Recomendações:**
• Monitore regularmente com este comando
• Mantenha backups atualizados
• Configure UptimeRobot para monitoramento externo""",
        color=cor
    )

    await msg.edit(embed=embed_final)

@bot.command(name='testeCompleto', aliases=['testecompleto2', 'testefull'])
@commands.has_permissions(administrator=True)
async def teste_completo(ctx):
    """[ADMIN] Teste completo de todos os sistemas do bot"""
    embed = create_embed(
        "🔧 Iniciando Teste Completo do Sistema",
        "Verificando todos os componentes...",
        color=0xffaa00
    )
    msg = await ctx.send(embed=embed)

    resultados = []

    # 1. Teste Database
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users')
            user_count = cursor.fetchone()[0]
            conn.close()
        resultados.append("✅ **Database:** Funcionando - " + str(user_count) + " usuários")
    except Exception as e:
        resultados.append("❌ **Database:** Erro - " + str(e))

    # 2. Teste Keep-alive
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get('http://0.0.0.0:8080/ping', timeout=5) as response:
                if response.status == 200:
                    resultados.append("✅ **Keep-alive:** Ativo - Porta 8080")
                else:
                    resultados.append("⚠️ **Keep-alive:** Problema - Status " + str(response.status))
    except Exception as e:
        resultados.append("❌ **Keep-alive:** Erro - " + str(e))

    # 3. Teste Guild e Permissions
    try:
        guild = ctx.guild
        if guild and hasattr(guild, 'categories'):
            resultados.append(f"✅ **Guild:** Válido - {guild.name}")
        else:
            resultados.append("❌ **Guild:** Inválido ou sem categorias")
    except Exception as e:
        resultados.append("❌ **Guild:** Erro - " + str(e))

    # 4. Teste Sistema de Tickets
    try:
        # Verificar se pode criar categoria de tickets
        category = discord.utils.get(ctx.guild.categories, name="📋 Tickets")
        if category:
            resultados.append("✅ **Tickets:** Categoria existe")
        else:
            resultados.append("⚠️ **Tickets:** Categoria não existe (será criada automaticamente)")
    except Exception as e:
        resultados.append("❌ **Tickets:** Erro - " + str(e))

    # 5. Teste XP System
    try:
        user_data = get_user_data(ctx.author.id)
        if user_data:
            resultados.append("✅ **Sistema XP:** Funcionando - User encontrado")
        else:
            resultados.append("⚠️ **Sistema XP:** User não existe (será criado)")
    except Exception as e:
        resultados.append("❌ **Sistema XP:** Erro - " + str(e))

    # 6. Teste AI System
    try:
        ai_response = ai_system.generate_response("teste", None)
        if ai_response:
            resultados.append("✅ **Sistema IA:** Funcionando")
        else:
            resultados.append("❌ **Sistema IA:** Sem resposta")
    except Exception as e:
        resultados.append("❌ **Sistema IA:** Erro - " + str(e))

    # 7. Teste Background Tasks
    running_tasks = []
    if update_status.is_running():
        running_tasks.append("Status Update")
    if backup_database.is_running():
        running_tasks.append("Backup")
    if check_reminders.is_running():
        running_tasks.append("Reminders")
    if check_giveaways.is_running():
        running_tasks.append("Giveaways")

    if running_tasks:
        resultados.append(f"✅ **Background Tasks:** {len(running_tasks)} ativos - {', '.join(running_tasks)}")
    else:
        resultados.append("❌ **Background Tasks:** Nenhum ativo")

    # 8. Teste Final - Latência
    start = time.time()
    latency = round(bot.latency * 1000, 2)
    end = time.time()
    response_time = round((end - start) * 1000, 2)

    if latency < 200:
        resultados.append(f"✅ **Latência:** {latency}ms - Excelente")
    else:
        resultados.append(f"⚠️ **Latência:** {latency}ms - Alta")

    # Montar embed final
    sucesso = len([r for r in resultados if r.startswith("✅")])
    avisos = len([r for r in resultados if r.startswith("⚠️")])
    erros = len([r for r in resultados if r.startswith("❌")])

    if erros == 0:
        cor = 0x00ff00
        status = "🎉 SISTEMA 100% FUNCIONAL!"
    elif erros <= 2:
        cor = 0xffaa00  
        status = "⚠️ Sistema funcional com avisos"
    else:
        cor = 0xff0000
        status = "❌ Sistema com problemas críticos"

    embed_final = create_embed(
        "📊 Resultado do Teste Completo",
        f"""**{status}**

**📈 Resumo:**
• ✅ Sucessos: {sucesso}
• ⚠️ Avisos: {avisos}  
• ❌ Erros: {erros}

**📋 Detalhes:**
""" + "\n".join(resultados) + f"""

**⏱️ Uptime:** {format_time(int((datetime.datetime.now() - global_stats['uptime_start']).total_seconds()))}
**💾 Comandos executados:** {global_stats['commands_used']:,}
**📨 Mensagens processadas:** {global_stats['messages_processed']:,}""",
        color=cor
    )

    await msg.edit(embed=embed_final)

# ============ COMANDOS BÁSICOS ============
@bot.command(name='ping', aliases=['p', 'latencia', 'latency'])
async def ping(ctx):
    """Mostra a latência do bot"""
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

@bot.command(name='ajuda', aliases=['help', 'comandos', 'commands'])
async def help_command(ctx, categoria=None):
    """Sistema de ajuda completo"""
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
`RXajuda tickets` - Sistema de suporte e feedback

**👑 Administração:**
`RXajuda admin` - Comandos para administradores

**🤖 IA Avançada:**
Mencione o bot para conversar!

**Total:** 250+ comandos disponíveis!""",
            color=0x7289da
        )
        embed.set_footer(text="Use RXajuda <categoria> para ver comandos específicos!")
        await ctx.send(embed=embed)

    elif categoria.lower() in ['diversao', 'diversão', 'fun']:
        embed = create_embed(
            "🎮 Comandos de Diversão",
            """**Jogos:**
• `RXjokenpo <escolha>` - Pedra, papel, tesoura
• `RXdado [lados]` - Rola um dado (padrão 6 lados)
• `RXmoeda` - Cara ou coroa
• `RX8ball <pergunta>` - Bola mágica 8

**Entretenimento:**
• `RXpiada` - Conta uma piada aleatória
• `RXfato` - Fato interessante
• `RXenquete <pergunta>` - Cria enquete com reações
• `RXmeme` - Meme aleatório
• `RXcuriosidade` - Curiosidade interessante""",
            color=0x7289da
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['economia', 'money', 'eco']:
        embed = create_embed(
            "💰 Comandos de Economia",
            """**Dinheiro:**
• `RXsaldo [@user]` - Ver saldo (carteira + banco)
• `RXdaily` - Recompensa diária (100 moedas)
• `RXweekly` - Recompensa semanal (700 moedas)
• `RXmonthly` - Recompensa mensal (2500 moedas)
• `RXtrabalhar` - Trabalhe por dinheiro
• `RXcrime` - Cometa um crime (risco/recompensa)

**Transferências:**
• `RXtransferir <@user> <valor>` - Transferir dinheiro
• `RXpay <@user> <valor>` - Pagar alguém
• `RXdepositar <valor>` - Depositar no banco
• `RXsacar <valor>` - Sacar do banco

**Loja:**
• `RXloja` - Ver itens da loja
• `RXcomprar <id>` - Comprar item da loja
• `RXinventario` - Ver seu inventário""",
            color=0xffd700
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['ranks', 'rank', 'ranking']:
        embed = create_embed(
            "🏆 Sistema de Ranks",
            """**Comandos de Rank:**
• `RXrank [@user]` - Ver rank de usuário
• `RXranklist` - Lista todos os ranks
• `RXleaderboard [tipo]` - Ranking do servidor
• `RXlb xp` - Top XP/Rank
• `RXlb coins` - Top Economia  
• `RXlb rep` - Top Reputação
• `RXlevel [@user]` - Ver nível e XP
• `RXtop` - Ranking geral

**Sistema:**
• Ganhe 5 XP por mensagem
• 12 ranks disponíveis (Novato → Imortal)
• Rankings por XP, dinheiro e reputação""",
            color=0xffd700
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['moderacao', 'moderação', 'mod']:
        embed = create_embed(
            "🛡️ Comandos de Moderação",
            """**Punições:**
• `RXban <@user> [motivo]` - Banir membro
• `RXkick <@user> [motivo]` - Expulsar membro
• `RXmute <@user> [tempo]` - Mutar membro
• `RXunmute <@user>` - Desmutar membro
• `RXwarn <@user> [motivo]` - Dar advertência
• `RXwarns [@user]` - Ver advertências

**Limpeza:**
• `RXclear <quantidade>` - Limpar mensagens (1-100)
• `RXpurge <@user>` - Limpar mensagens de usuário
• `RXlimpar <numero>` - Limpar mensagens

**Gerenciamento:**
• `RXlockdown` - Bloquear canal
• `RXunlockdown` - Desbloquear canal
• `RXslowmode <segundos>` - Modo lento no canal
• `RXnuke` - Recriar canal completamente""",
            color=0xff6b6b
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['info', 'informações', 'informacoes']:
        embed = create_embed(
            "📊 Comandos de Informações",
            """**Usuário:**
• `RXperfil [@user]` - Ver perfil completo
• `RXavatar [@user]` - Ver avatar em alta resolução  
• `RXuserinfo <@user>` - Info detalhada do usuário
• `RXid [@user]` - Ver ID do usuário
• `RXcreatetime [@user]` - Data de criação da conta

**Servidor:**
• `RXserverinfo` - Informações do servidor
• `RXserverpic` - Ícone do servidor
• `RXmembercount` - Contagem de membros
• `RXroles` - Lista de cargos
• `RXchannels` - Lista de canais

**Sistema:**
• `RXstats` - Estatísticas do bot
• `RXping` - Latência do bot
• `RXuptime` - Tempo online do bot
• `RXversion` - Versão do bot""",
            color=0x7289da
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['utilidades', 'util']:
        embed = create_embed(
            "⚙️ Comandos de Utilidades",
            """**Ferramentas:**
• `RXcalc <expressão>` - Calculadora
• `RXtempo` - Data e hora atual
• `RXlembrete <tempo> <texto>` - Criar lembrete
• `RXenquete <pergunta>` - Criar enquete
• `RXpoll <pergunta>` - Enquete rápida

**Conversores:**
• `RXbase64 <texto>` - Converter para base64
• `RXhash <texto>` - Gerar hash MD5/SHA
• `RXbin <texto>` - Converter para binário
• `RXhex <texto>` - Converter para hexadecimal

**Textos:**
• `RXreverse <texto>` - Inverter texto
• `RXuppercase <texto>` - MAIÚSCULAS
• `RXlowercase <texto>` - minúsculas
• `RXcapitalize <texto>` - Primeira Maiúscula

**Outros:**
• `RXqr <texto>` - Gerar QR Code
• `RXip` - Mostrar IP do servidor
• `RXshorten <url>` - Encurtar URL
• `RXpassword [tamanho]` - Gerar senha""",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['sorteios', 'sorteio', 'giveaway']:
        embed = create_embed(
            "🎁 Sistema Completo de Sorteios",
            """**Para Administradores:**
• `RXcriarsorteio <dados>` - Criar sorteio
• `RXgiveaway <dados>` - Criar sorteio
• `RXendgiveaway <id>` - Finalizar sorteio
• `RXreroll <id>` - Sortear novamente

**Formato do sorteio:**
`Título | Prêmio | Duração | Vencedores`

**Para Todos:**
• `RXsorteios` - Ver sorteios ativos
• `RXgiveaways` - Lista de sorteios
• Reaja com 🎉 para participar!

**Exemplo:**
`RXcriarsorteio iPhone 15 | iPhone novo | 24h | 1`

**Durações aceitas:** 30m, 2h, 1d, 7d""",
            color=0xffd700
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['tickets', 'ticket', 'suporte']:
        embed = create_embed(
            "🎟️ Sistema Completo de Tickets",
            """**Criar Tickets:**
• `RXticket <motivo>` - Criar ticket com motivo
• `RXticket` - Menu de criação rápida
• `RXtestetier` - Ticket específico para tier

**Gerenciar Tickets:**
• `RXcloseticket` - Fechar ticket atual
• `RXadduser <@user>` - Adicionar usuário ao ticket
• `RXremoveuser <@user>` - Remover usuário do ticket
• `RXrename <nome>` - Renomear ticket

**Sistema de Feedback:**
• `RXfeedback <avaliação>` - Avaliar atendimento (X/10)
• `RXfeedbacks` - [STAFF] Ver todas as avaliações

**Para Staff/Admin:**
• `RXtickets` - Ver todos os tickets
• `RXticketinfo <id>` - Info de ticket específico
• `RXresultadotier <resultado>` - [ADMIN] Enviar resultado de teste tier

**Sistema Rápido:**
🐛 Bug/Erro | 💰 Economia | ⚖️ Moderação
💡 Sugestão | ❓ Dúvida | 🛠️ Suporte | 👑 Tier

**Fechar:** Reaja com 🔒 em qualquer ticket""",
            color=0x7289da
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['admin', 'administracao']:
        embed = create_embed(
            "🛡️ Comandos de Administração",
            """**Sistemas Especiais:**
• `RXresultadotier <resultado>` - Enviar resultado de teste tier
• `RXfeedbacks` - Ver avaliações de tickets
• `RXcriarsorteio <dados>` - Criar sorteios
• `RXendgiveaway <id>` - Finalizar sorteio

**Configurações:**
• `RXsetprefix <prefix>` - Alterar prefix do servidor
• `RXconfig <setting>` - Configurações do servidor
• `RXbackup` - Fazer backup do banco de dados

**Logs e Monitoramento:**
• `RXlogs` - Ver logs do servidor
• `RXstats` - Estatísticas detalhadas
• `RXuptime` - Tempo online do bot

**Sistema de Comandos:**
• Total de 250+ comandos disponíveis
• Sistema de IA avançada integrado
• Keep-alive 24/7 ativo""",
            color=0xff6b6b
        )
        await ctx.send(embed=embed)

# ============ COMANDOS DE MODERAÇÃO ============
@bot.command(name='clear', aliases=['limpar', 'purge'])
@commands.has_permissions(manage_messages=True)
async def clear_messages(ctx, amount: int = 10):
    """Limpa mensagens do canal"""
    if amount < 1 or amount > 100:
        embed = create_embed("❌ Quantidade inválida", "Use entre 1 e 100 mensagens", color=0xff0000)
        await ctx.send(embed=embed)
        return

    # Sistema de confirmação para limpeza
    embed = create_embed(
        "🧹 Confirmação de Limpeza",
        f"""**⚠️ ATENÇÃO: Ação Irreversível**

**Você está prestes a deletar {amount} mensagens!**

**📍 Canal:** {ctx.channel.mention}
**👤 Moderador:** {ctx.author.mention}
**📊 Quantidade:** {amount} mensagens

**Deseja realmente continuar?**""",
        color=0xff6b6b
    )

    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    # Armazenar para processar confirmação
    active_games[msg.id] = {
        'type': 'clear_confirmation',
        'user': ctx.author.id,
        'channel': ctx.channel.id,
        'amount': amount
    }

@bot.command(name='ban', aliases=['banir'])
@commands.has_permissions(ban_members=True)
async def ban_member(ctx, member: discord.Member, *, reason="Sem motivo especificado"):
    """Bane um membro"""
    if member == ctx.author:
        embed = create_embed("❌ Impossível", "Você não pode se banir!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if member.top_role >= ctx.author.top_role:
        embed = create_embed("❌ Sem permissão", "Você não pode banir este membro!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    # Sistema de confirmação para ban
    embed = create_embed(
        "🔨 Confirmação de Ban",
        f"""**🚨 AÇÃO EXTREMAMENTE GRAVE**

**Você está prestes a BANIR um membro!**

**👤 Usuário:** {member.mention}
**🛡️ Moderador:** {ctx.author.mention}
**📝 Motivo:** {reason}

**Esta é realmente a melhor solução?**""",
        color=0xff0000
    )

    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    # Armazenar para processar confirmação
    active_games[msg.id] = {
        'type': 'ban_confirmation',
        'user': ctx.author.id,
        'channel': ctx.channel.id,
        'member_id': member.id,
        'reason': reason
    }

# ============ COMANDOS DE ECONOMIA ============
@bot.command(name='saldo', aliases=['balance', 'bal'])
async def balance(ctx, user: discord.Member = None):
    """Ver saldo do usuário"""
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
    """Recompensa diária"""
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

    # Update user data
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
    """Ver rank do usuário"""
    global_stats['commands_used'] += 1
    target = user or ctx.author
    data = get_user_data(target.id)

    if not data:
        update_user_data(target.id)
        xp, level = 0, 1
    else:
        xp, level = data[2], data[3]

    current_rank_id, current_rank = get_user_rank(xp)

    # Calcular progresso para próximo rank
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
• Mensagens para próximo rank: ~{xp_needed // XP_PER_MESSAGE:,}
• Posição no servidor: #{await get_user_position(target.id, ctx.guild.id)}""",
        color=current_rank["color"]
    )

    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name='leaderboard', aliases=['lb', 'toplist'])
async def leaderboard(ctx, tipo='xp'):
    """Ver ranking do servidor"""
    global_stats['commands_used'] += 1

    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            if tipo.lower() in ['xp', 'rank', 'nivel']:
                cursor.execute('''
                    SELECT user_id, xp, level FROM users 
                    ORDER BY xp DESC LIMIT 15
                ''')
                title = "🏆 Top XP/Rank do Servidor"
                field_name = "Ranking por XP"
            elif tipo.lower() in ['coins', 'money', 'dinheiro']:
                cursor.execute('''
                    SELECT user_id, coins, bank FROM users 
                    ORDER BY (coins + bank) DESC LIMIT 15
                ''')
                title = "💰 Top Economia do Servidor"
                field_name = "Ranking por Dinheiro"
            elif tipo.lower() in ['rep', 'reputacao']:
                cursor.execute('''
                    SELECT user_id, reputation FROM users 
                    ORDER BY reputation DESC LIMIT 15
                ''')
                title = "⭐ Top Reputação do Servidor"
                field_name = "Ranking por Reputação"
            else:
                cursor.execute('''
                    SELECT user_id, xp, level FROM users 
                    ORDER BY xp DESC LIMIT 15
                ''')
                title = "🏆 Top XP/Rank do Servidor"
                field_name = "Ranking por XP"

            results = cursor.fetchall()
            conn.close()

        if not results:
            embed = create_embed("📊 Ranking Vazio", "Ainda não há dados suficientes para o ranking!", color=0xffaa00)
            await ctx.send(embed=embed)
            return

        embed = create_embed(title, f"Top {len(results)} usuários do servidor:", color=0xffd700)

        leaderboard_text = ""
        medals = ["🥇", "🥈", "🥉"]

        for i, result in enumerate(results):
            user_id = result[0]
            user = ctx.guild.get_member(user_id)

            if not user:
                continue

            medal = medals[i] if i < 3 else f"{i+1}º"

            if tipo.lower() in ['xp', 'rank', 'nivel']:
                xp, level = result[1], result[2]
                rank_id, rank_data = get_user_rank(xp)
                leaderboard_text += f"{medal} **{user.display_name}**\n"
                leaderboard_text += f"   {rank_data['emoji']} {rank_data['name']} | Level {level} | {xp:,} XP\n\n"

            elif tipo.lower() in ['coins', 'money', 'dinheiro']:
                coins, bank = result[1], result[2]
                total = coins + bank
                leaderboard_text += f"{medal} **{user.display_name}**\n"
                leaderboard_text += f"   💰 {total:,} moedas (💵 {coins:,} + 🏦 {bank:,})\n\n"

            elif tipo.lower() in ['rep', 'reputacao']:
                rep = result[1]
                leaderboard_text += f"{medal} **{user.display_name}**\n"
                leaderboard_text += f"   ⭐ {rep} pontos de reputação\n\n"

        if leaderboard_text:
            embed.add_field(name=field_name, value=leaderboard_text[:1024], inline=False)

        embed.set_footer(text=f"Use: RXleaderboard xp/coins/rep • Posição de {ctx.author.display_name}: #{await get_user_position(ctx.author.id, ctx.guild.id)}")
        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro no leaderboard: {e}")
        embed = create_embed("❌ Erro", "Erro ao carregar ranking. Tente novamente.", color=0xff0000)
        await ctx.send(embed=embed)

async def get_user_position(user_id, guild_id):
    """Obter posição do usuário no ranking"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Contar quantos usuários têm XP maior
            cursor.execute('SELECT COUNT(*) FROM users WHERE xp > (SELECT xp FROM users WHERE user_id = ?)', (user_id,))
            position = cursor.fetchone()[0] + 1

            conn.close()
            return position
    except:
        return "?"

@bot.command(name='ranklist', aliases=['ranks', 'rankinfo'])
async def rank_list(ctx):
    """Lista todos os ranks disponíveis"""
    global_stats['commands_used'] += 1

    embed = create_embed(
        "🏆 Sistema de Ranks do RXbot",
        "Ganhe XP enviando mensagens e suba de rank!",
        color=0xffd700
    )

    rank_text = ""
    for rank_id, rank_data in RANK_SYSTEM.items():
        rank_text += f"{rank_data['emoji']} **{rank_data['name']}** - {rank_data['xp']:,} XP\n"

    embed.add_field(name="📋 Lista de Ranks", value=rank_text, inline=False)
    embed.add_field(name="💡 Dicas", value=f"• Ganhe {XP_PER_MESSAGE} XP por mensagem\n• Use `RXrank` para ver seu progresso\n• Use `RXleaderboard` para ver o ranking", inline=False)

    await ctx.send(embed=embed)

# ============ COMANDOS DE SORTEIO ============
@bot.command(name='criarsorteio', aliases=['giveaway'])
@commands.has_permissions(administrator=True)
async def create_giveaway(ctx, *, giveaway_data=None):
    """[ADMIN] Criar um novo sorteio"""
    if not giveaway_data:
        embed = create_embed(
            "🎁 Como criar um sorteio",
            """**Formato:** `Título | Prêmio | Duração | Vencedores`

**Exemplo:**
`RXcriarsorteio iPhone 15 | iPhone 15 Pro | 24h | 1`

**Durações:** 30m, 2h, 1d, 7d""",
            color=0x7289da
        )
        await ctx.send(embed=embed)
        return

    parts = [part.strip() for part in giveaway_data.split('|')]
    if len(parts) < 4:
        embed = create_embed(
            "❌ Formato incorreto",
            "Use: `Título | Prêmio | Duração | Vencedores`",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

    title = parts[0]
    prize = parts[1]
    duration_str = parts[2]
    try:
        winners_count = int(parts[3])
    except ValueError:
        embed = create_embed("❌ Número inválido", "O número de vencedores deve ser um número!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    # Parse duration
    time_units = {'m': 60, 'h': 3600, 'd': 86400}
    unit = duration_str[-1].lower()

    if unit not in time_units:
        embed = create_embed("❌ Duração inválida", "Use: m (minutos), h (horas), d (dias)", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        amount = int(duration_str[:-1])
        seconds = amount * time_units[unit]
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)

        # Criar embed do sorteio
        embed = create_embed(
            f"🎁 {title}",
            f"""**Prêmio:** {prize}
**Vencedores:** {winners_count}
**Termina:** <t:{int(end_time.timestamp())}:R>
**Criado por:** {ctx.author.mention}

Reaja com 🎉 para participar!""",
            color=0xffd700
        )

        giveaway_msg = await ctx.send(embed=embed)
        await giveaway_msg.add_reaction("🎉")

        # Salvar no banco
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO giveaways (guild_id, channel_id, creator_id, title, prize, winners_count, end_time, message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ctx.guild.id, ctx.channel.id, ctx.author.id, title, prize, winners_count, end_time, giveaway_msg.id))
            conn.commit()
            conn.close()

    except ValueError:
        embed = create_embed("❌ Duração inválida", "Use números válidos: 30m, 2h, 1d", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='sorteios', aliases=['giveaways'])
async def list_giveaways(ctx):
    """Ver sorteios ativos"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT title, prize, end_time, winners_count, participants
                FROM giveaways
                WHERE guild_id = ? AND status = 'active'
                ORDER BY end_time
            ''', (ctx.guild.id,))

            giveaways = cursor.fetchall()
            conn.close()

        if not giveaways:
            embed = create_embed(
                "🎁 Nenhum sorteio ativo",
                "Não há sorteios ativos no momento.\nAdministradores podem criar com `RXcriarsorteio`",
                color=0xffaa00
            )
            await ctx.send(embed=embed)
            return

        embed = create_embed(
            "🎁 Sorteios Ativos",
            f"Encontrados {len(giveaways)} sorteio(s) ativo(s):",
            color=0xffd700
        )

        for giveaway in giveaways[:5]:
            title, prize, end_time_str, winners_count, participants_json = giveaway
            participants = json.loads(participants_json) if participants_json else []

            embed.add_field(
                name=f"🎊 {title}",
                value=f"🎁 **Prêmio:** {prize}\n"
                      f"🏆 **Vencedores:** {winners_count}\n"
                      f"👥 **Participantes:** {len(participants)}",
                inline=False
            )

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Error listing giveaways: {e}")

# ============ SISTEMA DE TESTE TIER E FEEDBACK ============
@bot.command(name='resultadotier', aliases=['testetierresult'])
@commands.has_permissions(administrator=True)
async def resultado_teste_tier(ctx, *, resultado):
    """[ADMIN] Enviar resultado de teste tier para canal específico"""
    try:
        channel = bot.get_channel(CHANNEL_ID_TESTE_TIER)
        if not channel:
            embed = create_embed("❌ Erro", "Canal de teste tier não encontrado!", color=0xff0000)
            await ctx.send(embed=embed)
            return

        embed = create_embed(
            "📋 Resultado - Teste Tier",
            f"""**Resultado do teste tier:**

{resultado}

**Avaliado por:** {ctx.author.mention}
**Data:** <t:{int(datetime.datetime.now().timestamp())}:F>

*Este é um resultado oficial do teste tier.*""",
            color=0xffd700
        )

        await channel.send(embed=embed)

        # Confirmar envio
        confirm_embed = create_embed(
            "✅ Resultado Enviado!",
            f"Resultado do teste tier foi enviado para {channel.mention}",
            color=0x00ff00
        )
        await ctx.send(embed=confirm_embed, delete_after=10)

    except Exception as e:
        logger.error(f"Erro ao enviar resultado tier: {e}")
        embed = create_embed("❌ Erro", "Erro ao enviar resultado!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='feedback', aliases=['avaliar'])
async def feedback_ticket(ctx, *, avaliacao):
    """Dar feedback sobre atendimento de ticket"""
    # Verificar se está em um canal de ticket
    if not ctx.channel.name.startswith('ticket-'):
        embed = create_embed(
            "❌ Comando Inválido",
            "Este comando só pode ser usado dentro de canais de ticket!",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

    try:
        # Extrair nota da avaliação usando regex
        import re
        notas = re.findall(r'(\d{1,2})/10', avaliacao)

        if not notas:
            embed = create_embed(
                "❌ Formato Inválido",
                "Por favor, inclua uma nota no formato X/10\n**Exemplo:** `RXfeedback Ótimo atendimento! Nota 9/10`",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return

        # Converter notas para números
        notas_numericas = [int(nota) for nota in notas if 0 <= int(nota) <= 10]

        if not notas_numericas:
            embed = create_embed(
                "❌ Nota Inválida",
                "Use notas entre 0 e 10!",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return

        # Calcular média arredondada
        media = round(sum(notas_numericas) / len(notas_numericas))

        # Salvar feedback no banco
        try:
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()

                # Criar tabela de feedback se não existir
                cursor.execute('''CREATE TABLE IF NOT EXISTS ticket_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_channel_id INTEGER,
                    user_id INTEGER,
                    feedback_text TEXT,
                    notas TEXT,
                    media_nota INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')

                cursor.execute('''
                    INSERT INTO ticket_feedback (ticket_channel_id, user_id, feedback_text, notas, media_nota)
                    VALUES (?, ?, ?, ?, ?)
                ''', (ctx.channel.id, ctx.author.id, avaliacao, ','.join(notas), media))

                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Erro ao salvar feedback: {e}")

        # Determinar emoji e cor baseado na média
        if media >= 9:
            emoji = "🌟"
            cor = 0x00ff00
            qualidade = "Excelente"
        elif media >= 7:
            emoji = "⭐"
            cor = 0xffaa00
            qualidade = "Bom"
        elif media >= 5:
            emoji = "⚠️"
            cor = 0xff6600
            qualidade = "Regular"
        else:
            emoji = "❌"
            cor = 0xff0000
            qualidade = "Ruim"

        embed = create_embed(
            f"{emoji} Feedback Registrado - {qualidade}",
            f"""**Avaliação:** {avaliacao}

**📊 Análise das notas:**
• **Notas encontradas:** {', '.join([f'{n}/10' for n in notas])}
• **Média arredondada:** {media}/10
• **Qualidade:** {qualidade}

**👤 Por:** {ctx.author.mention}
**📅 Data:** <t:{int(datetime.datetime.now().timestamp())}:R>

*Obrigado pelo seu feedback! Ele nos ajuda a melhorar.*""",
            color=cor
        )

        await ctx.send(embed=embed)

        # Log para staff
        logger.info(f"Feedback registrado: {ctx.author} avaliou ticket {ctx.channel.name} com média {media}/10")

    except Exception as e:
        logger.error(f"Erro no feedback: {e}")
        embed = create_embed("❌ Erro", "Erro ao processar feedback!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='feedbacks', aliases=['avaliacoes'])
@commands.has_permissions(manage_messages=True)
async def ver_feedbacks(ctx):
    """[STAFF] Ver feedbacks de tickets"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT feedback_text, notas, media_nota, timestamp, user_id
                FROM ticket_feedback
                ORDER BY timestamp DESC
                LIMIT 10
            ''')

            feedbacks = cursor.fetchall()
            conn.close()

        if not feedbacks:
            embed = create_embed(
                "📊 Nenhum Feedback",
                "Ainda não há feedbacks registrados.",
                color=0xffaa00
            )
            await ctx.send(embed=embed)
            return

        embed = create_embed(
            "📊 Últimos Feedbacks de Tickets",
            f"Mostrando os {len(feedbacks)} feedbacks mais recentes:",
            color=0x7289da
        )

        for feedback_text, notas, media, timestamp, user_id in feedbacks[:5]:
            user = bot.get_user(user_id)
            user_name = user.name if user else "Usuário desconhecido"

            # Emoji baseado na média
            if media >= 9:
                emoji = "🌟"
            elif media >= 7:
                emoji = "⭐"
            elif media >= 5:
                emoji = "⚠️"
            else:
                emoji = "❌"

            embed.add_field(
                name=f"{emoji} Nota: {media}/10",
                value=f"**{user_name}:** {feedback_text[:100]}{'...' if len(feedback_text) > 100 else ''}\n"
                      f"*<t:{int(datetime.datetime.fromisoformat(timestamp).timestamp())}:R>*",
                inline=False
            )

        # Calcular estatísticas
        todas_medias = [feedback[2] for feedback in feedbacks]
        media_geral = round(sum(todas_medias) / len(todas_medias), 1)

        embed.add_field(
            name="📈 Estatísticas Gerais",
            value=f"**Média geral:** {media_geral}/10\n"
                  f"**Total de avaliações:** {len(feedbacks)}",
            inline=False
        )

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro ao ver feedbacks: {e}")
        embed = create_embed("❌ Erro", "Erro ao carregar feedbacks!", color=0xff0000)
        await ctx.send(embed=embed)

# ============ SISTEMA DE MONITORAMENTO ============
@bot.command(name='performance', aliases=['perf', 'monitor'])
@commands.has_permissions(administrator=True)
async def performance_monitor(ctx):
    """[ADMIN] Monitor de performance do sistema"""
    try:
        if psutil is None:
            embed = create_embed(
                "⚠️ Psutil não disponível",
                "Módulo psutil não está instalado. Mostrando informações básicas.",
                color=0xffaa00
            )
            await ctx.send(embed=embed)
            return

        # Informações do sistema
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_percent = psutil.cpu_percent()

        # Informações do processo do bot
        process = psutil.Process()
        bot_memory = process.memory_info().rss / 1024 / 1024  # MB
        bot_cpu = process.cpu_percent()

        # Calcular uptime
        uptime_seconds = int((datetime.datetime.now() - global_stats['uptime_start']).total_seconds())

        embed = create_embed(
            "📊 Monitor de Performance",
            f"""**💻 Sistema:**
• **CPU:** {cpu_percent}%
• **RAM:** {memory.percent}% ({memory.used // 1024 // 1024} MB / {memory.total // 1024 // 1024} MB)
• **Disco:** {disk.percent}% ({disk.used // 1024 // 1024 // 1024} GB / {disk.total // 1024 // 1024 // 1024} GB)

**🤖 Bot RX:**
• **Uso RAM:** {bot_memory:.1f} MB
• **Uso CPU:** {bot_cpu}%
• **Uptime:** {format_time(uptime_seconds)}
• **Latência:** {round(bot.latency * 1000, 2)}ms

**📈 Estatísticas:**
• **Servidores:** {len(bot.guilds):,}
• **Usuários:** {len(set(bot.get_all_members())):,}
• **Comandos/hora:** {global_stats['commands_used'] * 3600 // max(uptime_seconds, 1):,}
• **Msgs/minuto:** {global_stats['messages_processed'] * 60 // max(uptime_seconds, 1):,}

**🔄 Keep-alive:**
• Auto-ping: ✅ A cada 60s
• External: ✅ A cada 4min
• Heartbeat: ✅ A cada 3min""",
            color=0x00ff00 if cpu_percent < 70 and memory.percent < 80 else 0xffaa00 if cpu_percent < 90 else 0xff0000
        )

        await ctx.send(embed=embed)

    except ImportError:
        embed = create_embed(
            "⚠️ Psutil não disponível",
            "Instale psutil para monitoramento completo:\n`pip install psutil`",
            color=0xffaa00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        embed = create_embed("❌ Erro", f"Erro ao obter dados: {e}", color=0xff0000)
        await ctx.send(embed=embed)

# ============ JOGOS E DIVERSÃO ============
@bot.command(name='jokenpo', aliases=['pedrapapeltesoura'])
async def jokenpo(ctx, escolha=None):
    """Joga pedra, papel ou tesoura"""
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
    """Rola um dado"""
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

@bot.command(name='moeda', aliases=['coin'])
async def coin_flip(ctx):
    """Cara ou coroa"""
    resultado = random.choice(['Cara', 'Coroa'])
    emoji = '🪙' if resultado == 'Cara' else '🥇'

    embed = create_embed(
        "🪙 Cara ou Coroa",
        f"**Resultado:** {emoji} {resultado}!",
        color=0xffd700
    )
    await ctx.send(embed=embed)

@bot.command(name='piada', aliases=['joke'])
async def piada(ctx):
    """Conta uma piada"""
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

@bot.command(name='enquete', aliases=['poll'])
async def poll(ctx, *, pergunta=None):
    """Cria uma enquete"""
    if not pergunta:
        embed = create_embed("❌ Pergunta necessária", "Use: `RXenquete Gostam do bot?`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    embed = create_embed("📊 Enquete", pergunta, color=0x7289da)
    message = await ctx.send(embed=embed)

    await message.add_reaction("👍")
    await message.add_reaction("👎")
    await message.add_reaction("🤷")

@bot.command(name='lembrete', aliases=['reminder', 'lembrar'])
async def create_reminder(ctx, tempo=None, *, texto=None):
    """Criar um lembrete"""
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

    # Parse tempo
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

        # Salvar no banco
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

@bot.command(name='status', aliases=['sistema'])
async def sistema_status(ctx):
    """Status completo do sistema"""
    global_stats['commands_used'] += 1
    
    uptime_seconds = int((datetime.datetime.now() - global_stats['uptime_start']).total_seconds())
    
    embed = create_embed(
        "🔧 Status do Sistema RXbot",
        f"""**⚡ Sistema Principal:**
• Status: 🟢 Online e Estável
• Uptime: {format_time(uptime_seconds)}
• Latência: {round(bot.latency * 1000, 2)}ms

**🛡️ Sistemas de Proteção:**
• ✅ Auto-ping (30s)
• ✅ Keep-alive externo (120s)  
• ✅ Heartbeat (180s)
• ✅ Monitor de emergência (180s)
• ✅ Sistema anti-hibernação (45s)

**📊 Estatísticas:**
• Servidores: {len(bot.guilds)}
• Usuários: {len(set(bot.get_all_members()))}
• Comandos executados: {global_stats['commands_used']:,}
• Mensagens processadas: {global_stats['messages_processed']:,}

**🌐 Keep-alive URLs:**
• `/ping` - Ping básico
• `/keepalive` - Keep-alive principal
• `/monitor` - Monitoramento detalhado
• `/force-alive` - Força ativação

**💡 Dica:** Configure UptimeRobot para máxima proteção!""",
        color=0x00ff00
    )
    
    await ctx.send(embed=embed)

@bot.command(name='uptime')
async def uptime(ctx):
    """Mostra o tempo que o bot está online"""
    global_stats['commands_used'] += 1

    uptime_seconds = int((datetime.datetime.now() - global_stats['uptime_start']).total_seconds())

    embed = create_embed(
        "⏱️ Uptime do RXbot",
        f"""**⏰ Tempo online:** {format_time(uptime_seconds)}
**🚀 Iniciado em:** <t:{int(global_stats['uptime_start'].timestamp())}:F>
**💬 Status:** 🟢 Online e estável
**💬 Comandos executados:** {global_stats['commands_used']:,}
**📨 Mensagens processadas:** {global_stats['messages_processed']:,}

**🔄 Sistemas ativos:**
• ✅ Auto-ping (60s)
• ✅ Keep-alive externo (4min)
• ✅ Heartbeat (3min)
• ✅ Backup automático (6h)""",
        color=0x00ff00
    )

    await ctx.send(embed=embed)

@bot.command(name='stats', aliases=['estatisticas'])
async def bot_stats(ctx):
    """Estatísticas completas do bot"""
    global_stats['commands_used'] += 1

    uptime_seconds = int((datetime.datetime.now() - global_stats['uptime_start']).total_seconds())

    # Contar usuários únicos
    unique_users = len(set(bot.get_all_members()))

    embed = create_embed(
        "📊 Estatísticas do RXbot",
        f"""**🤖 Bot Info:**
• **Nome:** {bot.user.name}#{bot.user.discriminator}
• **ID:** {bot.user.id}
• **Uptime:** {format_time(uptime_seconds)}

**📈 Números:**
• **Servidores:** {len(bot.guilds):,}
• **Usuários únicos:** {unique_users:,}
• **Canais totais:** {len(list(bot.get_all_channels())):,}
• **Comandos executados:** {global_stats['commands_used']:,}
• **Mensagens processadas:** {global_stats['messages_processed']:,}

**🌐 Sistema:**
• **Latência:** {round(bot.latency * 1000, 2)}ms
• **Python:** {platform.python_version()}
• **Discord.py:** {discord.__version__}
• **Plataforma:** {platform.system()} {platform.release()}""",
        color=0x7289da
    )

    await ctx.send(embed=embed)

@bot.command(name='serverinfo', aliases=['infoserver'])
async def server_info(ctx):
    """Informações do servidor"""
    global_stats['commands_used'] += 1
    guild = ctx.guild

    # Contar membros por status
    online = len([m for m in guild.members if m.status == discord.Status.online])
    idle = len([m for m in guild.members if m.status == discord.Status.idle])
    dnd = len([m for m in guild.members if m.status == discord.Status.dnd])
    offline = len([m for m in guild.members if m.status == discord.Status.offline])

    embed = create_embed(
        f"📋 Informações - {guild.name}",
        f"""**🏠 Servidor:**
• **Nome:** {guild.name}
• **ID:** {guild.id}
• **Criado:** <t:{int(guild.created_at.timestamp())}:F>
• **Dono:** {guild.owner.mention if guild.owner else 'Desconhecido'}

**👥 Membros ({guild.member_count}):**
• 🟢 Online: {online}
• 🟡 Ausente: {idle}  
• 🔴 Ocupado: {dnd}
• ⚫ Offline: {offline}

**📊 Canais ({len(guild.channels)}):**
• 💬 Texto: {len(guild.text_channels)}
• 🔊 Voz: {len(guild.voice_channels)}
• 📁 Categorias: {len(guild.categories)}

**🎭 Outros:**
• **Cargos:** {len(guild.roles)}
• **Emojis:** {len(guild.emojis)}
• **Boost:** Nível {guild.premium_tier} ({guild.premium_subscription_count} boosts)""",
        color=0x7289da
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    await ctx.send(embed=embed)

@bot.command(name='userinfo', aliases=['uinfo'])
async def user_info(ctx, user: discord.Member = None):
    """Informações detalhadas do usuário"""
    global_stats['commands_used'] += 1
    target = user or ctx.author

    # Buscar dados do usuário no banco
    user_data = get_user_data(target.id)
    if user_data:
        coins, xp, level, rep, bank = user_data[1], user_data[2], user_data[3], user_data[4], user_data[5]
        warnings = user_data[15]
    else:
        coins = xp = level = rep = bank = warnings = 0

    # Status emoji
    status_emoji = {
        discord.Status.online: "🟢",
        discord.Status.idle: "🟡", 
        discord.Status.dnd: "🔴",
        discord.Status.offline: "⚫"
    }

    embed = create_embed(
        f"👤 {target.display_name}",
        f"""**📋 Informações Básicas:**
• **Nome:** {target.name}#{target.discriminator}
• **ID:** {target.id}
• **Status:** {status_emoji.get(target.status, '❓')} {target.status.name.title()}
• **Criado:** <t:{int(target.created_at.timestamp())}:R>
• **Entrou:** <t:{int(target.joined_at.timestamp())}:R>

**🎮 Gaming:**
• **Level:** {level}
• **XP:** {xp:,}
• **Reputação:** {rep}

**💰 Economia:**
• **Carteira:** {coins:,} moedas
• **Banco:** {bank:,} moedas
• **Total:** {coins + bank:,} moedas

**⚖️ Moderação:**
• **Advertências:** {warnings}
• **Cargo mais alto:** {target.top_role.name}""",
        color=target.color if target.color != discord.Color.default() else 0x7289da
    )

    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name='avatar', aliases=['av'])
async def avatar(ctx, user: discord.Member = None):
    """Mostra o avatar do usuário em alta resolução"""
    global_stats['commands_used'] += 1
    target = user or ctx.author

    avatar_url = target.avatar.url if target.avatar else target.default_avatar.url

    embed = create_embed(
        f"🖼️ Avatar de {target.display_name}",
        f"[Clique aqui para ver em alta resolução]({avatar_url}?size=1024)",
        color=target.color if target.color != discord.Color.default() else 0x7289da
    )

    embed.set_image(url=f"{avatar_url}?size=512")
    await ctx.send(embed=embed)

# Error handling SUPER melhorado com auto-recuperação
@bot.event
async def on_command_error(ctx, error):
    try:
        if isinstance(error, commands.CommandNotFound):
            # Sugerir comando similar
            command_name = ctx.message.content.split()[0][2:].lower()  # Remove prefix
            similar_commands = ['ping', 'ajuda', 'saldo', 'rank', 'daily']
            suggestion = None
            
            for cmd in similar_commands:
                if command_name in cmd or cmd in command_name:
                    suggestion = cmd
                    break
            
            if suggestion:
                embed = create_embed(
                    "❓ Comando não encontrado",
                    f"Você quis dizer `RX{suggestion}`?\nUse `RXajuda` para ver todos os comandos.",
                    color=0xffaa00
                )
                await ctx.send(embed=embed, delete_after=8)
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
            
        elif isinstance(error, commands.BotMissingPermissions):
            embed = create_embed(
                "❌ Bot sem permissão",
                f"Eu preciso das seguintes permissões: {', '.join(error.missing_permissions)}",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            
        elif isinstance(error, commands.CommandOnCooldown):
            embed = create_embed(
                "⏰ Comando em cooldown",
                f"Aguarde {error.retry_after:.1f} segundos para usar novamente.",
                color=0xff6b6b
            )
            await ctx.send(embed=embed, delete_after=5)
            
        elif isinstance(error, discord.HTTPException):
            logger.error(f"Discord HTTP Error: {error}")
            embed = create_embed(
                "🔄 Erro de conexão",
                "Houve um problema de conexão. Tentando novamente...",
                color=0xff6600
            )
            try:
                await ctx.send(embed=embed, delete_after=5)
            except:
                pass
                
        elif isinstance(error, asyncio.TimeoutError):
            logger.error(f"Timeout Error: {error}")
            embed = create_embed(
                "⏱️ Timeout",
                "Operação demorou muito para responder. Tente novamente.",
                color=0xff6600
            )
            try:
                await ctx.send(embed=embed, delete_after=5)
            except:
                pass
                
        else:
            logger.error(f"Unexpected error in {ctx.command}: {error}")
            logger.error(f"Error type: {type(error)}")
            
            # Tentar enviar erro genérico se possível
            try:
                embed = create_embed(
                    "❌ Erro interno",
                    "Ocorreu um erro interno. A equipe foi notificada.",
                    color=0xff0000
                )
                await ctx.send(embed=embed, delete_after=8)
            except:
                pass
            
            # Notificar canal de alerta
            try:
                channel = bot.get_channel(CHANNEL_ID_ALERTA)
                if channel:
                    error_embed = create_embed(
                        "🚨 Erro de Comando",
                        f"**Comando:** {ctx.command}\n"
                        f"**Usuário:** {ctx.author}\n"
                        f"**Canal:** {ctx.channel}\n"
                        f"**Erro:** {str(error)[:500]}",
                        color=0xff0000
                    )
                    await channel.send(embed=error_embed)
            except:
                pass
                
    except Exception as handler_error:
        logger.error(f"Erro no error handler: {handler_error}")
        # Último recurso - resposta simples
        try:
            await ctx.send("❌ Erro interno do bot.", delete_after=5)
        except:
            pass

# Sistema robusto de inicialização
async def maintain_connection():
    """Mantém a conexão do bot estável"""
    while True:
        try:
            if not bot.is_ready():
                logger.warning("🔄 Bot não está pronto, aguardando...")
                await asyncio.sleep(30)
                continue

            # Verificar latência
            if bot.latency > 5.0:
                logger.warning(f"⚠️ Latência alta: {bot.latency * 1000:.2f}ms")

            await asyncio.sleep(60)

        except Exception as e:
            logger.error(f"Erro no maintain_connection: {e}")
            await asyncio.sleep(30)

async def start_bot():
    """Sistema de inicialização ULTRA robusto"""
    reconnect_count = 0
    max_reconnects = 15  # Aumentado para mais tentativas

    while reconnect_count < max_reconnects:
        try:
            logger.info(f"🚀 Iniciando RXbot... (Tentativa {reconnect_count + 1}/{max_reconnects})")

            # Limpeza prévia de memória
            import gc
            gc.collect()

            # Verificar token antes de tentar conectar
            token = os.getenv('TOKEN')
            if not token:
                logger.error("🚨 TOKEN não encontrado!")
                await asyncio.sleep(10)
                continue

            # Iniciar tasks de manutenção apenas uma vez
            if not hasattr(bot, '_maintenance_started'):
                bot._maintenance_started = True
                asyncio.create_task(maintain_connection())

            # Iniciar o bot com timeout
            try:
                await asyncio.wait_for(bot.start(token), timeout=60.0)
            except asyncio.TimeoutError:
                logger.error("⏱️ Timeout na inicialização do bot")
                reconnect_count += 1
                continue

        except discord.LoginFailure as e:
            logger.error(f"❌ Falha de login (token inválido): {e}")
            logger.error("🚨 Verificar TOKEN nas variáveis de ambiente!")
            await asyncio.sleep(60)  # Esperar mais tempo para token issues
            reconnect_count += 1

        except discord.HTTPException as e:
            if e.status == 429:  # Rate limited
                logger.error("🚨 Rate limited! Aguardando...")
                wait_time = 120  # 2 minutos para rate limit
            else:
                logger.error(f"❌ Erro HTTP Discord: {e}")
                wait_time = min(300, 30 * (2 ** min(reconnect_count, 5)))
            
            reconnect_count += 1
            logger.info(f"🔄 Tentando reconectar em {wait_time} segundos...")
            await asyncio.sleep(wait_time)

        except discord.ConnectionClosed as e:
            logger.error(f"🔗 Conexão fechada: {e}")
            reconnect_count += 1
            wait_time = 15  # Reconectar rapidamente para connection closed
            logger.info(f"🔄 Reconectando em {wait_time} segundos...")
            await asyncio.sleep(wait_time)

        except Exception as e:
            logger.error(f"❌ Erro inesperado: {e}")
            logger.error(f"🔍 Tipo do erro: {type(e)}")
            reconnect_count += 1
            
            # Limpeza de memória em caso de erro
            import gc
            gc.collect()
            
            wait_time = min(60, 10 * reconnect_count)
            logger.info(f"🔄 Aguardando {wait_time}s antes da próxima tentativa...")
            await asyncio.sleep(wait_time)

    logger.error("🚨 Máximo de tentativas atingido. Sistema crítico!")
    
    # Último recurso: forçar restart do processo
    import sys
    logger.error("💀 Forçando exit do processo...")
    sys.exit(1)

def run_flask():
    """Executa servidor Flask otimizado"""
    try:
        app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        logger.error(f"Erro no servidor Flask: {e}")

def keep_alive():
    """Sistema de keep-alive melhorado"""
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("🌐 Servidor keep-alive iniciado na porta 8080")

def restart_bot():
    """Sistema de restart automático ULTRA-ROBUSTO"""
    restart_count = 0
    
    while True:
        try:
            restart_count += 1
            logger.info(f"🚀 Iniciando bot (Restart #{restart_count})")
            
            # Verificar token
            token = os.getenv('TOKEN')
            if not token:
                logger.error("🚨 TOKEN não encontrado!")
                time.sleep(30)
                continue

            # Iniciar keep-alive
            keep_alive()

            # Aguardar Flask inicializar
            time.sleep(3)

            # Log detalhado
            logger.info("🌐 Flask iniciado, conectando ao Discord...")

            # Iniciar bot
            asyncio.run(start_bot())
            
        except KeyboardInterrupt:
            logger.info("🛑 Bot interrompido pelo usuário - Saindo definitivamente")
            break
        except discord.HTTPException as e:
            logger.error(f"🚨 Erro Discord HTTP: {e}")
            logger.info(f"🔄 Aguardando 30s para reconectar... (Restart #{restart_count + 1})")
            time.sleep(30)
        except discord.ConnectionClosed as e:
            logger.error(f"🚨 Conexão fechada: {e}")
            logger.info(f"🔄 Reconectando imediatamente... (Restart #{restart_count + 1})")
            time.sleep(5)
        except Exception as e:
            logger.error(f"🚨 Erro fatal: {e}")
            logger.error(f"🔍 Traceback: {traceback.format_exc()}")
            logger.info(f"🔄 Reiniciando em 15 segundos... (Restart #{restart_count + 1})")
            time.sleep(15)
        
        # Log de restart
        logger.warning(f"🔄 BOT PAROU! Executando restart #{restart_count + 1} em 3 segundos...")
        time.sleep(3)

if __name__ == "__main__":
    try:
        # Iniciar keep-alive primeiro
        keep_alive()
        
        # Aguardar Flask inicializar
        time.sleep(2)
        
        # Verificar token
        token = os.getenv('TOKEN')
        if not token:
            logger.error("🚨 TOKEN não encontrado nas variáveis de ambiente!")
            print("❌ Configure a variável de ambiente TOKEN com o token do seu bot Discord")
            sys.exit(1)
        
        logger.info("🚀 Iniciando RXbot...")
        
        # Iniciar bot diretamente
        asyncio.run(start_bot())
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido pelo usuário")
    except Exception as e:
        logger.error(f"🚨 Erro fatal na inicialização: {e}")
        logger.error(f"🔍 Traceback: {traceback.format_exc()}")
        sys.exit(1)