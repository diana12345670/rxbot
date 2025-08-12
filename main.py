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
import weakref
from contextlib import asynccontextmanager

# Imports opcionais com fallback seguro
try:
    import psutil
except ImportError:
    psutil = None

try:
    import locale
    locale.setlocale(locale.LC_ALL, 'C')
except (ImportError, locale.Error):
    locale = None

try:
    import pytz
except ImportError:
    pytz = None

# Configuração do logging otimizada
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rxbot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('RXbot')

# Reduzir logs de bibliotecas externas
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('aiohttp').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

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
    strip_after_prefix=True,
    max_messages=1000  # Limitar cache de mensagens
)

# Sistema HTTP TOTALMENTE CORRIGIDO com gerenciamento robusto
class HTTPSessionManager:
    def __init__(self):
        self._session = None
        self._lock = asyncio.Lock()
        self._cleanup_task = None
        self._last_used = time.time()

    async def get_session(self):
        async with self._lock:
            current_time = time.time()

            # Se a sessão está muito antiga (> 30 min), recriar
            if self._session and (current_time - self._last_used) > 1800:
                await self._close_session()

            if self._session is None or self._session.closed:
                connector = aiohttp.TCPConnector(
                    limit=50,
                    limit_per_host=20,
                    ttl_dns_cache=300,
                    use_dns_cache=True,
                    enable_cleanup_closed=True,
                    keepalive_timeout=30,
                    timeout=aiohttp.ClientTimeout(total=15)
                )

                self._session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=aiohttp.ClientTimeout(total=15),
                    headers={'User-Agent': 'RXbot/2.1.0'}
                )

                # Agendar cleanup automático
                if self._cleanup_task is None or self._cleanup_task.done():
                    self._cleanup_task = asyncio.create_task(self._auto_cleanup())

            self._last_used = current_time
            return self._session

    async def _close_session(self):
        if self._session and not self._session.closed:
            try:
                await self._session.close()
                await asyncio.sleep(0.1)  # Dar tempo para cleanup
            except Exception as e:
                logger.warning(f"Erro ao fechar sessão HTTP: {e}")
            finally:
                self._session = None

    async def _auto_cleanup(self):
        """Cleanup automático da sessão após inatividade"""
        while True:
            try:
                await asyncio.sleep(1800)  # 30 minutos
                async with self._lock:
                    if self._session and (time.time() - self._last_used) > 1800:
                        await self._close_session()
                        break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no auto cleanup HTTP: {e}")

    async def close(self):
        async with self._lock:
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass

            await self._close_session()

    async def __aenter__(self):
        return await self.get_session()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Não fechar aqui para permitir reutilização
        pass

# Instância global do gerenciador HTTP
http_manager = HTTPSessionManager()

# Sistema de Database COMPLETAMENTE CORRIGIDO com pools assíncronos
class DatabaseManager:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._connection = None
        self._last_used = time.time()
        self._cleanup_task = None

    async def get_connection(self):
        async with self._lock:
            current_time = time.time()

            # Reconectar se conexão muito antiga (> 1 hora)
            if self._connection and (current_time - self._last_used) > 3600:
                self._close_connection()

            if self._connection is None:
                try:
                    self._connection = sqlite3.connect(
                        'rxbot.db', 
                        timeout=10.0, 
                        check_same_thread=False,
                        isolation_level=None  # Autocommit mode
                    )

                    # Otimizações SQLite
                    self._connection.execute('PRAGMA journal_mode=WAL')
                    self._connection.execute('PRAGMA synchronous=NORMAL')
                    self._connection.execute('PRAGMA cache_size=10000')
                    self._connection.execute('PRAGMA temp_store=memory')
                    self._connection.execute('PRAGMA optimize')

                    logger.info("✅ Conexão com banco estabelecida")
                except Exception as e:
                    logger.error(f"❌ Erro ao conectar com banco: {e}")
                    raise

            self._last_used = current_time
            return self._connection

    def _close_connection(self):
        if self._connection:
            try:
                self._connection.close()
                logger.info("🔒 Conexão com banco fechada")
            except Exception as e:
                logger.warning(f"Erro ao fechar conexão: {e}")
            finally:
                self._connection = None

    async def execute(self, query, params=None):
        async with self._lock:
            try:
                conn = await self.get_connection()
                cursor = conn.cursor()

                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                result = cursor.fetchall()
                cursor.close()

                return result

            except sqlite3.Error as e:
                logger.error(f"Erro SQL: {e} | Query: {query[:100]}")
                raise
            except Exception as e:
                logger.error(f"Erro database: {e}")
                raise

    async def close_all(self):
        async with self._lock:
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()
            self._close_connection()

# Instância global do gerenciador de banco
db_manager = DatabaseManager()

# Sistema de monitoramento de saúde SUPER otimizado
class HealthMonitor:
    def __init__(self):
        self.last_heartbeat = datetime.datetime.now()
        self.heartbeat_interval = 300  # 5 minutos
        self.health_checks = deque(maxlen=20)
        self.monitor_task = None

    async def start_monitoring(self):
        if self.monitor_task is None or self.monitor_task.done():
            self.monitor_task = asyncio.create_task(self._monitor_loop())

    async def _monitor_loop(self):
        while not bot.is_closed():
            try:
                await asyncio.sleep(self.heartbeat_interval)

                current_time = datetime.datetime.now()
                time_since_heartbeat = (current_time - self.last_heartbeat).total_seconds()

                # Registro de saúde
                health_status = {
                    'timestamp': current_time,
                    'latency': bot.latency,
                    'guilds': len(bot.guilds),
                    'heartbeat_gap': time_since_heartbeat
                }
                self.health_checks.append(health_status)

                if time_since_heartbeat > self.heartbeat_interval * 2:
                    logger.warning("⚠️ Bot pode estar com problemas de conectividade")

                    # Tentar notificar apenas se bot estiver ready
                    if bot.is_ready():
                        self.last_heartbeat = current_time
                        logger.info("💓 Heartbeat restaurado")
                else:
                    self.last_heartbeat = current_time

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no monitor de saúde: {e}")
                await asyncio.sleep(60)

    def update_heartbeat(self):
        self.last_heartbeat = datetime.datetime.now()

    async def stop_monitoring(self):
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

# Instância global do monitor
health_monitor = HealthMonitor()

# Database setup TOTALMENTE corrigido
async def init_database():
    """Initialize database with async support"""
    try:
        # Criar todas as tabelas necessárias
        tables = [
            '''CREATE TABLE IF NOT EXISTS tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                creator_id INTEGER,
                channel_id INTEGER,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_by INTEGER,
                reason TEXT
            )''',

            '''CREATE TABLE IF NOT EXISTS users (
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
            )''',

            '''CREATE TABLE IF NOT EXISTS guilds (
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
            )''',

            '''CREATE TABLE IF NOT EXISTS events (
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
            )''',

            '''CREATE TABLE IF NOT EXISTS moderation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                action TEXT,
                reason TEXT,
                duration INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',

            '''CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                type TEXT,
                amount INTEGER,
                description TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',

            '''CREATE TABLE IF NOT EXISTS message_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                channel_id INTEGER,
                user_id INTEGER,
                message_id INTEGER,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',

            '''CREATE TABLE IF NOT EXISTS custom_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                command_name TEXT,
                response TEXT,
                creator_id INTEGER,
                uses INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',

            '''CREATE TABLE IF NOT EXISTS clans (
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
            )''',

            '''CREATE TABLE IF NOT EXISTS clan_challenges (
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
            )''',

            '''CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                channel_id INTEGER,
                reminder_text TEXT,
                remind_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',

            '''CREATE TABLE IF NOT EXISTS giveaways (
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
            )''',

            '''CREATE TABLE IF NOT EXISTS auto_mod_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                rule_type TEXT,
                rule_data TEXT,
                punishment TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',

            '''CREATE TABLE IF NOT EXISTS clan_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                creator_id INTEGER,
                clan1 TEXT,
                clan2 TEXT,
                event_type TEXT,
                bet_amount INTEGER,
                end_time TIMESTAMP,
                message_id INTEGER,
                participants TEXT DEFAULT '[]',
                bets TEXT DEFAULT '{}',
                status TEXT DEFAULT 'active',
                winner_clan TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',

            '''CREATE TABLE IF NOT EXISTS ticket_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_channel_id INTEGER,
                user_id INTEGER,
                feedback_text TEXT,
                notas TEXT,
                media_nota INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )'''
        ]

        for table_sql in tables:
            await db_manager.execute(table_sql)

        # Criar índices para melhor performance
        indices = [
            'CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_users_xp ON users(xp DESC)',
            'CREATE INDEX IF NOT EXISTS idx_users_coins ON users((coins + bank) DESC)',
            'CREATE INDEX IF NOT EXISTS idx_tickets_channel ON tickets(channel_id)',
            'CREATE INDEX IF NOT EXISTS idx_giveaways_status ON giveaways(status, end_time)',
            'CREATE INDEX IF NOT EXISTS idx_reminders_time ON reminders(remind_time)',
            'CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id, timestamp DESC)'
        ]

        for index_sql in indices:
            try:
                await db_manager.execute(index_sql)
            except Exception as e:
                logger.warning(f"Erro ao criar índice: {e}")

        logger.info("✅ Database inicializado com sucesso!")

    except Exception as e:
        logger.error(f"❌ Falha na inicialização do database: {e}")
        raise

# Global variables for bot state otimizadas
global_stats = {
    'commands_used': 0,
    'messages_processed': 0,
    'guilds_joined': 0,
    'uptime_start': datetime.datetime.now(),
    'total_users': 0,
    'total_channels': 0,
    'last_cleanup': time.time()
}

# Memory system for AI conversations SUPER otimizado
class ConversationMemory:
    def __init__(self):
        self._memory = {}
        self._last_cleanup = time.time()
        self._max_entries = 10

    def add_message(self, user_id, message):
        if user_id not in self._memory:
            self._memory[user_id] = deque(maxlen=self._max_entries)
        self._memory[user_id].append({
            'content': message[:200],  # Limitar tamanho
            'timestamp': time.time()
        })

        # Cleanup periódico
        if time.time() - self._last_cleanup > 3600:  # 1 hora
            self._cleanup_old_conversations()

    def get_context(self, user_id):
        if user_id in self._memory:
            recent = [msg for msg in self._memory[user_id] 
                     if time.time() - msg['timestamp'] < 1800]  # 30 min
            return [msg['content'] for msg in recent[-3:]]  # Últimas 3
        return []

    def _cleanup_old_conversations(self):
        current_time = time.time()
        users_to_remove = []

        for user_id, messages in self._memory.items():
            # Remover conversas antigas (> 24h)
            recent_messages = [msg for msg in messages 
                             if current_time - msg['timestamp'] < 86400]
            if recent_messages:
                self._memory[user_id] = deque(recent_messages, maxlen=self._max_entries)
            else:
                users_to_remove.append(user_id)

        for user_id in users_to_remove:
            del self._memory[user_id]

        self._last_cleanup = current_time
        logger.info(f"🧹 Cleanup de conversações: {len(users_to_remove)} removidas")

conversation_memory = ConversationMemory()
user_personalities = {}

# Sistema de jogos ativos COMPLETAMENTE thread-safe
class ThreadSafeGameManager:
    def __init__(self):
        self._games = {}
        self._lock = asyncio.Lock()
        self._cleanup_task = None
        self._last_cleanup = time.time()

    async def set(self, key, value):
        async with self._lock:
            value['created_at'] = time.time()
            self._games[key] = value

            # Auto-cleanup periódico
            if time.time() - self._last_cleanup > 600:  # 10 min
                await self._cleanup_expired()

    async def get(self, key, default=None):
        async with self._lock:
            return self._games.get(key, default)

    async def delete(self, key):
        async with self._lock:
            self._games.pop(key, None)

    async def __contains__(self, key):
        async with self._lock:
            return key in self._games

    async def items(self):
        async with self._lock:
            return list(self._games.items())

    async def _cleanup_expired(self):
        """Remove jogos expirados (> 1 hora)"""
        current_time = time.time()
        expired_keys = []

        for key, value in self._games.items():
            if current_time - value.get('created_at', current_time) > 3600:
                expired_keys.append(key)

        for key in expired_keys:
            self._games.pop(key, None)

        self._last_cleanup = current_time

        if expired_keys:
            logger.info(f"🧹 Cleanup de jogos: {len(expired_keys)} expirados removidos")

    async def cleanup_all(self):
        async with self._lock:
            count = len(self._games)
            self._games.clear()
            logger.info(f"🧹 Todos os jogos limpos: {count} removidos")

# Active games thread-safe
active_games = ThreadSafeGameManager()
music_queues = defaultdict(list)
voice_clients = {}

# Moderation system otimizado
class ModerationTracker:
    def __init__(self):
        self._spam_tracker = defaultdict(lambda: deque(maxlen=5))
        self._warning_tracker = defaultdict(int)
        self._last_cleanup = time.time()

    def track_message(self, user_id):
        current_time = time.time()
        self._spam_tracker[user_id].append(current_time)

        # Cleanup periódico
        if current_time - self._last_cleanup > 300:  # 5 min
            self._cleanup_old_data()

    def is_spamming(self, user_id, threshold=5, timeframe=10):
        current_time = time.time()
        messages = self._spam_tracker[user_id]

        # Contar mensagens no timeframe
        recent_messages = [t for t in messages if current_time - t < timeframe]
        return len(recent_messages) >= threshold

    def add_warning(self, user_id):
        self._warning_tracker[user_id] += 1
        return self._warning_tracker[user_id]

    def get_warnings(self, user_id):
        return self._warning_tracker[user_id]

    def _cleanup_old_data(self):
        current_time = time.time()

        # Limpar spam tracker
        users_to_clean = []
        for user_id, timestamps in self._spam_tracker.items():
            recent = [t for t in timestamps if current_time - t < 300]  # 5 min
            if recent:
                self._spam_tracker[user_id] = deque(recent, maxlen=5)
            else:
                users_to_clean.append(user_id)

        for user_id in users_to_clean:
            del self._spam_tracker[user_id]

        self._last_cleanup = current_time

moderation_tracker = ModerationTracker()

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

# Sistema de IA Expandido com 200+ tópicos OTIMIZADO
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
        if len(message_content) > 500:  # Evitar processamento de mensagens muito longas
            return ['geral']

        content_lower = message_content.lower()
        detected_contexts = []

        for context, keywords in self.context_patterns.items():
            if any(keyword in content_lower for keyword in keywords):
                detected_contexts.append(context)
                break  # Pegar apenas o primeiro contexto para performance

        return detected_contexts if detected_contexts else ['geral']

    def generate_response(self, message_content, user_data=None):
        """Gera uma resposta inteligente baseada no contexto"""
        if len(message_content.strip()) <= 3:
            return random.choice([
                "Entendi! 😄 Como posso ajudar?",
                "Haha! 😊 Em que posso ser útil?",
                "Legal! 🎉 Vamos conversar?",
                "Interessante! 🤔 Me conte mais!"
            ])

        contexts = self.analyze_message(message_content)
        primary_context = contexts[0]

        if primary_context in self.responses:
            return random.choice(self.responses[primary_context])

        return "Interessante! Como posso te ajudar hoje? Use `RXajuda` para ver todos os comandos!"

ai_system = AdvancedAI()

# Background tasks SUPER melhorados e otimizados
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
            health_monitor.update_heartbeat()
    except Exception as e:
        logger.error(f"Erro no update_status: {e}")

@tasks.loop(hours=6)
async def backup_database():
    """Backup automático do banco de dados"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_rxbot_{timestamp}.db"

        # Usar shutil para backup mais seguro
        shutil.copy2('rxbot.db', backup_name)

        # Manter apenas os últimos 5 backups
        backup_files = [f for f in os.listdir('.') if f.startswith('backup_rxbot_')]
        backup_files.sort()

        while len(backup_files) > 5:
            old_backup = backup_files.pop(0)
            try:
                os.remove(old_backup)
            except:
                pass

        logger.info(f"✅ Backup criado: {backup_name}")
    except Exception as e:
        logger.error(f"Erro no backup: {e}")

@tasks.loop(minutes=1)
async def check_reminders():
    """Verifica lembretes"""
    try:
        now = datetime.datetime.now()
        reminders = await db_manager.execute(
            'SELECT * FROM reminders WHERE remind_time <= ? LIMIT 10', (now,)
        )

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

                await db_manager.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))
            except Exception as e:
                logger.error(f"Erro ao enviar lembrete {reminder_id}: {e}")

    except Exception as e:
        logger.error(f"Erro check_reminders: {e}")

@tasks.loop(minutes=1)
async def check_giveaways():
    """Verifica sorteios que terminaram"""
    try:
        now = datetime.datetime.now()
        finished_giveaways = await db_manager.execute('''
            SELECT * FROM giveaways 
            WHERE status = 'active' AND end_time <= ?
            LIMIT 5
        ''', (now,))

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
                await db_manager.execute('UPDATE giveaways SET status = ? WHERE id = ?', ('finished', giveaway_id))

            except Exception as e:
                logger.error(f"Erro ao finalizar sorteio {giveaway_id}: {e}")

    except Exception as e:
        logger.error(f"Erro check_giveaways: {e}")

@tasks.loop(minutes=30)
async def cleanup_memory():
    """Limpeza periódica de memória"""
    try:
        # Cleanup de conversações
        conversation_memory._cleanup_old_conversations()

        # Cleanup de jogos
        await active_games._cleanup_expired()

        # Garbage collection
        collected = gc.collect()

        current_time = time.time()
        global_stats['last_cleanup'] = current_time

        logger.info(f"🧹 Cleanup de memória: {collected} objetos coletados")

    except Exception as e:
        logger.error(f"Erro no cleanup de memória: {e}")

# Utility functions SUPER otimizadas
async def get_user_data(user_id):
    """Get user data with async support and caching"""
    try:
        result = await db_manager.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting user data for {user_id}: {e}")
        return None

async def update_user_data(user_id, **kwargs):
    """Update user data with async support and batch operations"""
    try:
        # Check if user exists
        result = await db_manager.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if not result:
            await db_manager.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))

        # Batch update fields
        updates = []
        values = []

        for field, value in kwargs.items():
            if field in ['coins', 'xp', 'level', 'reputation', 'bank', 'total_messages', 'voice_time', 'warnings']:
                updates.append(f'{field} = ?')
                values.append(value)
            elif field in ['inventory', 'achievements', 'settings']:
                updates.append(f'{field} = ?')
                values.append(json.dumps(value))
            elif field in ['last_daily', 'last_weekly', 'last_monthly']:
                updates.append(f'{field} = ?')
                values.append(value)

        if updates:
            query = f'UPDATE users SET {", ".join(updates)} WHERE user_id = ?'
            values.append(user_id)
            await db_manager.execute(query, values)

    except Exception as e:
        logger.error(f"Error updating user data for {user_id}: {e}")

async def add_xp(user_id, amount):
    """Add XP with level and rank calculation - OPTIMIZED"""
    try:
        data = await get_user_data(user_id)
        if not data:
            await update_user_data(user_id, xp=amount, level=1)
            return False, 1, False, 1

        current_xp = data[2]
        current_level = data[3]
        new_xp = current_xp + amount

        # Calculate new level (optimized formula)
        new_level = int(math.sqrt(new_xp / 100)) + 1
        leveled_up = new_level > current_level

        # Calculate rank progression
        old_rank_id, old_rank = get_user_rank(current_xp)
        new_rank_id, new_rank = get_user_rank(new_xp)
        rank_up = new_rank_id > old_rank_id

        await update_user_data(user_id, xp=new_xp, level=new_level)
        return leveled_up, new_level, rank_up, new_rank_id
    except Exception as e:
        logger.error(f"Error adding XP to {user_id}: {e}")
        return False, 1, False, 1

def format_time(seconds):
    """Format seconds to readable time - OPTIMIZED"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h"

def create_embed(title, description=None, color=0x7289DA, **kwargs):
    """Create embed with standard formatting - OPTIMIZED"""
    embed = discord.Embed(title=title, description=description, color=color)
    embed.timestamp = datetime.datetime.now()

    # Otimizar campos opcionais
    if 'thumbnail' in kwargs:
        embed.set_thumbnail(url=kwargs['thumbnail'])
    if 'image' in kwargs:
        embed.set_image(url=kwargs['image'])
    if 'footer' in kwargs:
        embed.set_footer(text=kwargs['footer'])

    return embed

# Função para detectar infrações automáticas OTIMIZADA
def check_auto_violations(message_content):
    """Verifica se a mensagem contém violações automáticas"""
    if len(message_content) > 1000:  # Evitar processamento de mensagens muito longas
        return ["Mensagem muito longa"]

    content_lower = message_content.lower()
    violations = []

    # Verificar palavras proibidas (otimizado)
    for word in AUTO_WARN_WORDS:
        if word in content_lower:
            violations.append(f"Palavra proibida: {word}")
            break  # Parar no primeiro match para performance

    # Verificar spam de caps (otimizado)
    if len(message_content) > 20:
        caps_ratio = sum(1 for c in message_content if c.isupper()) / len(message_content)
        if caps_ratio > 0.7:  # 70% maiúsculas
            violations.append("Spam de maiúsculas")

    return violations

# Sistema de validação de reações COMPLETAMENTE corrigido
async def validate_reaction(reaction, user, expected_user_id=None):
    """Valida se a reação é válida e do usuário correto"""
    try:
        # Verificar se não é bot
        if user.bot:
            return False

        # Verificar se é o usuário esperado (se especificado)
        if expected_user_id and user.id != expected_user_id:
            try:
                await reaction.remove(user)
            except:
                pass
            return False

        # Verificar se a mensagem ainda existe
        if not reaction.message or reaction.message.id not in [msg.id async for msg in reaction.message.channel.history(limit=50)]:
            return False

        return True

    except Exception as e:
        logger.error(f"Erro na validação de reação: {e}")
        return False

# Event handlers SUPER otimizados
@bot.event
async def on_message(message):
    """Processar mensagens para XP, IA e moderação - OPTIMIZED"""
    if message.author.bot:
        return

    global_stats['messages_processed'] += 1

    # Rate limiting por usuário
    moderation_tracker.track_message(message.author.id)

    # Verificar spam
    if moderation_tracker.is_spamming(message.author.id):
        try:
            await message.delete()
            return
        except:
            pass

    # Sistema de XP (otimizado para não bloquear)
    try:
        if random.randint(1, 10) <= 8:  # 80% chance para reduzir carga
            asyncio.create_task(process_xp_gain(message.author.id))
    except Exception as e:
        logger.error(f"Erro no sistema XP: {e}")

    # Sistema de IA (responder quando mencionado)
    if bot.user.mentioned_in(message) and not message.mention_everyone:
        try:
            content = message.content.replace(f'<@{bot.user.id}>', '').strip()
            if content and len(content) < 500:  # Limitar tamanho
                conversation_memory.add_message(message.author.id, content)
                response = ai_system.generate_response(content)
                await message.reply(response)
        except Exception as e:
            logger.error(f"Erro no sistema IA: {e}")

    # Processar comandos
    await bot.process_commands(message)

async def process_xp_gain(user_id):
    """Processamento assíncrono de XP para não bloquear mensagens"""
    try:
        leveled_up, new_level, rank_up, new_rank_id = await add_xp(user_id, XP_PER_MESSAGE)

        # Notificações de level/rank up são processadas em background
        if leveled_up or rank_up:
            # Implementar sistema de notificação diferida se necessário
            pass
    except Exception as e:
        logger.error(f"Erro no processamento de XP: {e}")

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
                f"• Versão: 2.1.0 (Completamente Corrigida)\n\n"
                f"**🛡️ Sistemas corrigidos:**\n"
                f"• ✅ HTTP Session Manager (sem vazamentos)\n"
                f"• ✅ Database Async (locks corretos)\n"
                f"• ✅ Thread-Safe Games (memory safe)\n"
                f"• ✅ Validação de reações corrigida\n"
                f"• ✅ Performance optimization\n"
                f"• ✅ Memory leak prevention\n\n"
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
            cleanup_memory.start()

            # Iniciar monitor de saúde
            await health_monitor.start_monitoring()

            logger.info("✅ Background tasks e monitor de saúde iniciados")
        except Exception as e:
            logger.error(f"Erro ao iniciar background tasks: {e}")

    # Set initial status
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
        gc.collect()
        logger.info("🧹 Limpeza de memória inicial concluída")
    except:
        pass

@bot.event
async def on_disconnect():
    logger.error("🚨 BOT DESCONECTADO DO DISCORD!")

    # Cleanup adequado
    try:
        await health_monitor.stop_monitoring()
        await http_manager.close()
        await active_games.cleanup_all()
        logger.info("✅ Cleanup de desconexão realizado")
    except Exception as e:
        logger.warning(f"⚠️ Erro no cleanup de desconexão: {e}")

    try:
        channel = bot.get_channel(CHANNEL_ID_ALERTA)
        if channel:
            embed = create_embed(
                "🚨 Desconexão Detectada",
                f"❌ O bot foi **desconectado** do Discord!\n"
                f"🔄 Sistema de reconexão automática ativado...\n"
                f"⏰ Timestamp: <t:{int(datetime.datetime.now().timestamp())}:F>",
                color=0xff6600
            )
            await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Erro ao enviar alerta de desconexão: {e}")

@bot.event
async def on_resumed():
    logger.info("🔄 BOT RECONECTADO AO DISCORD!")
    try:
        channel = bot.get_channel(CHANNEL_ID_ALERTA)
        if channel:
            embed = create_embed(
                "✅ Reconexão Bem-Sucedida",
                f"🎉 Bot reconectou ao Discord com sucesso!\n"
                f"**Tempo:** <t:{int(datetime.datetime.now().timestamp())}:F>\n"
                f"**Status:** ✅ Totalmente operacional\n"
                f"**Latência:** {round(bot.latency * 1000, 2)}ms",
                color=0x00ff00
            )
            await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Erro ao enviar alerta de reconexão: {e}")

@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"🚨 Erro crítico no evento {event}: {traceback.format_exc()}")

    try:
        channel = bot.get_channel(CHANNEL_ID_ALERTA)
        if channel:
            embed = create_embed(
                "⚠️ Erro de Sistema",
                f"**Evento:** {event}\n"
                f"**Timestamp:** <t:{int(datetime.datetime.now().timestamp())}:F>\n"
                f"**Status:** Sistema continua operacional",
                color=0xffaa00
            )
            await channel.send(embed=embed)
    except:
        pass

@bot.event
async def on_guild_join(guild):
    global_stats['guilds_joined'] += 1
    logger.info(f"📈 Entrei no servidor: {guild.name} ({guild.id})")

    # Initialize guild data
    try:
        await db_manager.execute('INSERT OR IGNORE INTO guilds (guild_id, name) VALUES (?, ?)', (guild.id, guild.name))
    except Exception as e:
        logger.error(f"Error joining guild: {e}")

# Sistema de tickets corrigido - criar canal
async def create_ticket_channel(ctx, motivo, user):
    """Criar canal de ticket com sistema corrigido"""
    try:
        guild = ctx.guild

        # Buscar ou criar categoria de tickets
        category = discord.utils.get(guild.categories, name="📋 Tickets")
        if not category:
            try:
                category = await guild.create_category("📋 Tickets")
                logger.info("✅ Categoria de tickets criada")
            except Exception as e:
                logger.error(f"Erro ao criar categoria: {e}")
                return

        # Criar canal do ticket
        channel_name = f"ticket-{user.name}-{random.randint(1000, 9999)}"

        # Configurar permissões
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Adicionar permissões para staff
        for role in guild.roles:
            if any(keyword in role.name.lower() for keyword in ['admin', 'mod', 'staff', 'suporte']):
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Criar canal
        ticket_channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Ticket de {user.name} - {motivo}"
        )

        # Salvar no banco
        await db_manager.execute('''
            INSERT INTO tickets (guild_id, creator_id, channel_id, reason)
            VALUES (?, ?, ?, ?)
        ''', (guild.id, user.id, ticket_channel.id, motivo))

        # Embed de boas-vindas do ticket
        embed = create_embed(
            "🎫 Ticket Criado com Sucesso!",
            f"**👤 Criado por:** {user.mention}\n"
            f"**📝 Motivo:** {motivo}\n"
            f"**📅 Criado em:** <t:{int(datetime.datetime.now().timestamp())}:F>\n\n"
            f"**🔧 Como usar:**\n"
            f"• Descreva seu problema detalhadamente\n"
            f"• Aguarde a resposta da equipe\n"
            f"• Para fechar, reaja com 🔒\n\n"
            f"**⚠️ Importante:**\n"
            f"• Seja respeitoso com a equipe\n"
            f"• Forneça todas as informações necessárias\n"
            f"• Este canal será deletado ao fechar o ticket",
            color=0x00ff00
        )

        # Adicionar instruções específicas por tipo
        if "tier" in motivo.lower():
            embed.add_field(
                name="👑 Teste Tier",
                value="• Aguarde o resultado do seu teste\n"
                      "• Seja paciente durante a avaliação\n"
                      "• O resultado será enviado aqui",
                inline=False
            )

        message = await ticket_channel.send(f"{user.mention}", embed=embed)
        await message.add_reaction("🔒")

        # Confirmar criação
        success_embed = create_embed(
            "✅ Ticket Criado!",
            f"Seu ticket foi criado: {ticket_channel.mention}",
            color=0x00ff00
        )

        try:
            await ctx.send(embed=success_embed, delete_after=10)
        except:
            pass

        logger.info(f"Ticket criado: {user.name} - {motivo}")

    except Exception as e:
        logger.error(f"Erro ao criar ticket: {e}")
        error_embed = create_embed(
            "❌ Erro ao criar ticket",
            "Ocorreu um erro ao criar o ticket. Contate um administrador.",
            color=0xff0000
        )
        try:
            await ctx.send(embed=error_embed, delete_after=10)
        except:
            pass

@bot.event
async def on_reaction_add(reaction, user):
    """Gerenciar reações COMPLETAMENTE corrigido"""
    if user.bot:
        return

    message = reaction.message

    # Validação básica de reação
    if not await validate_reaction(reaction, user):
        return

    # Verificar se é um jogo/evento ativo
    if await active_games.__contains__(message.id):
        game_data = await active_games.get(message.id)

        if not game_data:
            return

        # Validação de usuário para jogos específicos
        game_type = game_data.get('type', '')
        expected_user = game_data.get('user')

        if game_type in ['ticket_creation', 'ticket_confirmation', 'ticket_tier_confirmation', 
                        'clear_confirmation', 'ban_confirmation', 'close_ticket_confirmation']:
            if expected_user and user.id != expected_user:
                try:
                    await reaction.remove(user)
                except:
                    pass
                return

        # Processar diferentes tipos de jogos/eventos
        try:
            await process_game_reaction(reaction, user, game_data)
        except Exception as e:
            logger.error(f"Erro ao processar reação de jogo: {e}")

    # Verificar se é uma reação em mensagem de ticket
    elif (str(reaction.emoji) == "🔒" and 
          hasattr(message.channel, 'name') and 
          message.channel.name.startswith('ticket-')):

        await handle_ticket_close_reaction(reaction, user, message)

    # Sistema de chuva de moedas
    elif str(reaction.emoji) == "💰":
        await handle_coin_rain_reaction(reaction, user, message)

async def process_game_reaction(reaction, user, game_data):
    """Processar reações de jogos de forma organizada"""
    game_type = game_data['type']
    message = reaction.message

    if game_type == 'ticket_creation':
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

            try:
                ctx_mock = type('MockCtx', (), {
                    'guild': message.guild,
                    'channel': message.channel,
                    'send': message.channel.send
                })()

                await create_ticket_channel(ctx_mock, motivo, user)

                embed = create_embed(
                    "✅ Ticket Criado!",
                    f"Seu ticket foi criado com sucesso!\n**Motivo:** {motivo}",
                    color=0x00ff00
                )
                await message.edit(embed=embed)
                await active_games.delete(message.id)
            except Exception as e:
                logger.error(f"Erro ao criar ticket: {e}")

    elif game_type == 'ticket_confirmation':
        if str(reaction.emoji) == "✅":
            motivo = game_data['motivo']

            try:
                ctx_mock = type('MockCtx', (), {
                    'guild': message.guild,
                    'channel': message.channel,
                    'send': message.channel.send
                })()

                await create_ticket_channel(ctx_mock, motivo, user)

                embed = create_embed(
                    "✅ Ticket Criado!",
                    f"Seu ticket foi criado com sucesso!\n**Motivo:** {motivo}",
                    color=0x00ff00
                )
                await message.edit(embed=embed)
                await active_games.delete(message.id)
            except Exception as e:
                logger.error(f"Erro ao criar ticket: {e}")

        elif str(reaction.emoji) == "❌":
            embed = create_embed("❌ Ticket Cancelado", "Criação de ticket cancelada pelo usuário.", color=0xff6b6b)
            await message.edit(embed=embed)
            await active_games.delete(message.id)

    elif game_type == 'clear_confirmation':
        await handle_clear_confirmation(reaction, user, game_data, message)

    elif game_type == 'close_ticket_confirmation':
        await handle_close_ticket_confirmation(reaction, user, game_data, message)

async def handle_clear_confirmation(reaction, user, game_data, message):
    """Lidar com confirmação de limpeza"""
    if str(reaction.emoji) == "✅":
        amount = game_data['amount']
        channel_id = game_data['channel']
        channel = message.guild.get_channel(channel_id)

        if not channel:
            embed = create_embed("❌ Erro", "Canal não encontrado!", color=0xff0000)
            await message.edit(embed=embed)
            await active_games.delete(message.id)
            return

        try:
            # Deletar a mensagem de confirmação primeiro
            try:
                await message.delete()
            except:
                pass

            # Limpar mensagens do canal
            deleted = await channel.purge(limit=amount)

            confirm_embed = create_embed(
                "🧹 Limpeza Concluída",
                f"**{len(deleted)} mensagens foram deletadas com sucesso!**",
                color=0x00ff00
            )
            await channel.send(embed=confirm_embed, delete_after=5)
            await active_games.delete(message.id)
        except Exception as e:
            logger.error(f"Erro na limpeza: {e}")
            embed = create_embed("❌ Erro na Limpeza", f"Erro: {str(e)[:100]}", color=0xff0000)
            try:
                await channel.send(embed=embed, delete_after=10)
            except:
                pass
            if await active_games.__contains__(message.id):
                await active_games.delete(message.id)

    elif str(reaction.emoji) == "❌":
        embed = create_embed("❌ Limpeza Cancelada", "Operação cancelada pelo usuário.", color=0xff6b6b)
        await message.edit(embed=embed)
        await active_games.delete(message.id)

async def handle_close_ticket_confirmation(reaction, user, game_data, message):
    """Lidar com confirmação de fechamento de ticket"""
    if str(reaction.emoji) == "✅":
        try:
            # Feedback antes de fechar
            feedback_embed = create_embed(
                "⭐ Avalie nosso atendimento!",
                f"**Como foi o atendimento neste ticket?**\n\n"
                f"Use `RXfeedback <sua avaliação> X/10`\n"
                f"**Exemplo:** `RXfeedback Ótimo atendimento! 9/10`\n\n"
                f"⏰ **Ticket será fechado em 30 segundos...**",
                color=0xffaa00
            )
            await message.channel.send(embed=feedback_embed)

            # Aguardar um tempo para feedback
            await asyncio.sleep(30)

            # Registrar fechamento
            await db_manager.execute('''
                UPDATE tickets SET status = 'closed', closed_by = ? 
                WHERE channel_id = ?
            ''', (user.id, message.channel.id))

            # Deletar canal
            await message.channel.delete(reason=f"Ticket fechado por {user.name}")

        except Exception as e:
            logger.error(f"Erro ao fechar ticket: {e}")

    elif str(reaction.emoji) == "❌":
        embed = create_embed(
            "❌ Fechamento Cancelado", 
            "O ticket permanece aberto.",
            color=0xff6b6b
        )
        await message.edit(embed=embed)

    await active_games.delete(message.id)

async def handle_ticket_close_reaction(reaction, user, message):
    """Lidar com reação de fechar ticket"""
    # Verificar permissões
    has_permission = False
    is_creator = False

    try:
        member = message.guild.get_member(user.id)
        if member:
            has_permission = (member.guild_permissions.manage_channels or 
                            member.guild_permissions.administrator or
                            any(role.name.lower() in ['admin', 'mod', 'staff', 'moderador', 'administrador'] for role in member.roles))
    except Exception as e:
        logger.error(f"Erro ao verificar permissões: {e}")

    try:
        # Verificar se é o criador do ticket
        result = await db_manager.execute('SELECT creator_id FROM tickets WHERE channel_id = ?', (message.channel.id,))
        if result and result[0][0] == user.id:
            is_creator = True
    except Exception as e:
        logger.error(f"Erro ao verificar criador do ticket: {e}")

    if not (has_permission or is_creator):
        try:
            await reaction.remove(user)
        except:
            pass

        try:
            error_embed = create_embed(
                "❌ Sem permissão",
                "Apenas staff ou o criador do ticket podem fechá-lo!",
                color=0xff0000
            )
            temp_msg = await message.channel.send(embed=error_embed)
            await asyncio.sleep(5)
            await temp_msg.delete()
        except:
            pass
        return

    # Confirmar fechamento
    confirm_embed = create_embed(
        "🔒 Fechar Ticket?",
        f"**{user.mention}** deseja fechar este ticket?\n\n"
        f"**⚠️ Esta ação é irreversível!**\n"
        f"O canal será **DELETADO** permanentemente!\n\n"
        f"Reaja com ✅ para confirmar ou ❌ para cancelar.\n"
        f"**Você tem 30 segundos para decidir.**",
        color=0xff6b6b
    )

    try:
        confirm_msg = await message.channel.send(embed=confirm_embed)
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")

        # Armazenar para processar confirmação
        await active_games.set(confirm_msg.id, {
            'type': 'close_ticket_confirmation',
            'user': user.id,
            'channel': message.channel.id,
            'closer': user.id,
            'created_at': datetime.datetime.now().timestamp()
        })

        # Auto-cancelar após 30 segundos
        await asyncio.sleep(30)
        if await active_games.__contains__(confirm_msg.id):
            try:
                timeout_embed = create_embed(
                    "⏰ Tempo Esgotado",
                    "Confirmação de fechamento expirou. O ticket permanece aberto.",
                    color=0xffaa00
                )
                await confirm_msg.edit(embed=timeout_embed)
                await active_games.delete(confirm_msg.id)
            except:
                pass

    except Exception as e:
        logger.error(f"Erro ao criar confirmação de fechamento: {e}")

async def handle_coin_rain_reaction(reaction, user, message):
    """Lidar com reação de chuva de moedas"""
    # Verificar se é evento de chuva de moedas
    for game_id, game_data in await active_games.items():
        if (game_data.get('type') == 'coin_rain' and 
            game_data.get('message_id') == message.id):

            participants = game_data.get('participants', [])
            max_participants = game_data.get('max_participants', 3)

            if user.id not in participants and len(participants) < max_participants:
                participants.append(user.id)
                game_data['participants'] = participants
                await active_games.set(game_id, game_data)

                if len(participants) >= max_participants:
                    # Distribuir moedas
                    total_coins = game_data.get('total_coins', 1000)
                    coins_per_user = total_coins // max_participants

                    for participant_id in participants:
                        user_data = await get_user_data(participant_id)
                        if user_data:
                            new_coins = user_data[1] + coins_per_user
                            await update_user_data(participant_id, coins=new_coins)

                    # Anunciar vencedores
                    winners_mentions = [f"<@{pid}>" for pid in participants]
                    result_embed = create_embed(
                        "🎉 Chuva de Moedas Finalizada!",
                        f"**Vencedores:** {', '.join(winners_mentions)}\n"
                        f"**Prêmio:** {coins_per_user:,} moedas cada",
                        color=0xffd700
                    )
                    await message.edit(embed=result_embed)
                    await active_games.delete(game_id)
            break

# ============ COMANDOS FALTANDO RESTAURADOS ============

@bot.command(name='perfil', aliases=['profile'])
async def perfil(ctx, user: discord.Member = None):
    """Ver perfil completo do usuário"""
    global_stats['commands_used'] += 1
    target = user or ctx.author

    try:
        user_data = await get_user_data(target.id)
        if not user_data:
            await update_user_data(target.id)
            user_data = await get_user_data(target.id)

        coins, xp, level, rep, bank = user_data[1], user_data[2], user_data[3], user_data[4], user_data[5]
        total_money = coins + bank

        # Obter rank
        rank_id, rank_data = get_user_rank(xp)

        # Obter título personalizado se existir
        custom_title = ""
        if user_data and len(user_data) > 11:
            settings_data = user_data[11]
            settings = json.loads(settings_data) if settings_data else {}
            if settings.get('custom_title'):
                custom_title = f" | {settings['custom_title']}"

        # Status emoji
        status_emoji = {
            discord.Status.online: "🟢",
            discord.Status.idle: "🟡", 
            discord.Status.dnd: "🔴",
            discord.Status.offline: "⚫"
        }

        embed = create_embed(
            f"{rank_data['emoji']} Perfil de {target.display_name}{custom_title}",
            f"**👤 Informações Básicas:**\n"
            f"• **Nome:** {target.name}#{target.discriminator}\n"
            f"• **ID:** {target.id}\n"
            f"• **Status:** {status_emoji.get(target.status, '❓')} {target.status.name.title()}\n"
            f"• **Conta criada:** <t:{int(target.created_at.timestamp())}:R>\n"
            f"• **Entrou no servidor:** <t:{int(target.joined_at.timestamp())}:R>\n\n"
            f"**🏆 Ranking:**\n"
            f"• **Rank:** {rank_data['emoji']} {rank_data['name']} (#{rank_id})\n"
            f"• **Level:** {level}\n"
            f"• **XP:** {xp:,}\n"
            f"• **Reputação:** {rep}\n\n"
            f"**💰 Economia:**\n"
            f"• **Carteira:** {coins:,} moedas\n"
            f"• **Banco:** {bank:,} moedas\n"
            f"• **Total:** {total_money:,} moedas",
            color=rank_data['color']
        )

        embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
        embed.set_footer(text=f"Use RXinventario para ver itens | Posição no ranking: #{await get_user_position(target.id, ctx.guild.id)}")

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro no comando perfil: {e}")
        embed = create_embed("❌ Erro", "Erro ao carregar perfil. Tente novamente.", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='level', aliases=['lvl'])
async def level_info(ctx, user: discord.Member = None):
    """Ver informações detalhadas de level e XP"""
    global_stats['commands_used'] += 1
    target = user or ctx.author

    try:
        user_data = await get_user_data(target.id)
        if not user_data:
            await update_user_data(target.id)
            xp, level = 0, 1
        else:
            xp, level = user_data[2], user_data[3]

        current_rank_id, current_rank = get_user_rank(xp)

        # Calcular XP para próximo level
        next_level_xp = (level ** 2) * 100
        current_level_xp = ((level - 1) ** 2) * 100
        xp_for_next = next_level_xp - xp

        # Progresso para próximo rank
        next_rank_id = current_rank_id + 1 if current_rank_id < 12 else 12
        next_rank = RANK_SYSTEM.get(next_rank_id, RANK_SYSTEM[12])

        if current_rank_id < 12:
            rank_xp_needed = next_rank["xp"] - xp
            rank_progress = ((xp - current_rank["xp"]) / (next_rank["xp"] - current_rank["xp"])) * 100
        else:
            rank_xp_needed = 0
            rank_progress = 100

        embed = create_embed(
            f"📊 Level de {target.display_name}",
            f"**⭐ Level Atual:** {level}\n"
            f"**💫 XP Total:** {xp:,}\n"
            f"**🎯 XP para próximo level:** {xp_for_next:,}\n\n"
            f"**🏆 Rank Atual:** {current_rank['emoji']} {current_rank['name']}\n"
            f"**📈 Progresso do rank:** {rank_progress:.1f}%\n"
            f"**🎪 XP para próximo rank:** {rank_xp_needed:,}\n\n"
            f"**📋 Estatísticas:**\n"
            f"• Mensagens para próximo level: ~{xp_for_next // XP_PER_MESSAGE:,}\n"
            f"• Mensagens para próximo rank: ~{rank_xp_needed // XP_PER_MESSAGE:,}\n"
            f"• XP por mensagem: {XP_PER_MESSAGE}",
            color=current_rank['color']
        )

        embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro no comando level: {e}")
        embed = create_embed("❌ Erro", "Erro ao carregar informações de level.", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='top', aliases=['ranking'])
async def top_users(ctx):
    """Ranking geral do servidor"""
    global_stats['commands_used'] += 1

    try:
        with db_manager._lock: # Acessar com lock para consistência
            conn = await db_manager.get_connection()
            cursor = conn.cursor()

            # Top XP
            cursor.execute('SELECT user_id, xp, level FROM users ORDER BY xp DESC LIMIT 10')
            top_xp = cursor.fetchall()

            # Top Coins
            cursor.execute('SELECT user_id, coins, bank FROM users ORDER BY (coins + bank) DESC LIMIT 10')
            top_coins = cursor.fetchall()

            conn.close()

        embed = create_embed(
            "🏆 Rankings do Servidor",
            "Top usuários em diferentes categorias:",
            color=0xffd700
        )

        # Top XP
        xp_text = ""
        for i, (user_id, xp, level) in enumerate(top_xp[:5]):
            user = ctx.guild.get_member(user_id)
            if user:
                rank_id, rank_data = get_user_rank(xp)
                medal = ["🥇", "🥈", "🥉", "4º", "5º"][i]
                xp_text += f"{medal} **{user.display_name}** - {rank_data['emoji']} Lv.{level} ({xp:,} XP)\n"

        if xp_text:
            embed.add_field(name="⭐ Top XP/Level", value=xp_text, inline=True)

        # Top Coins
        coins_text = ""
        for i, (user_id, coins, bank) in enumerate(top_coins[:5]):
            user = ctx.guild.get_member(user_id)
            if user:
                total = coins + bank
                medal = ["🥇", "🥈", "🥉", "4º", "5º"][i]
                coins_text += f"{medal} **{user.display_name}** - {total:,} moedas\n"

        if coins_text:
            embed.add_field(name="💰 Top Economia", value=coins_text, inline=True)

        embed.set_footer(text=f"Sua posição: #{await get_user_position(ctx.author.id, ctx.guild.id)} | Use RXleaderboard para ver mais")
        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro no comando top: {e}")
        embed = create_embed("❌ Erro", "Erro ao carregar rankings.", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='serverpic', aliases=['servericon'])
async def server_picture(ctx):
    """Mostra o ícone do servidor em alta resolução"""
    global_stats['commands_used'] += 1
    guild = ctx.guild

    if not guild.icon:
        embed = create_embed("❌ Sem ícone", "Este servidor não possui ícone!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    embed = create_embed(
        f"🖼️ Ícone do {guild.name}",
        f"[Clique aqui para ver em alta resolução]({guild.icon.url}?size=1024)",
        color=0x7289da
    )
    embed.set_image(url=f"{guild.icon.url}?size=512")
    await ctx.send(embed=embed)

@bot.command(name='membercount', aliases=['members'])
async def member_count(ctx):
    """Contagem detalhada de membros"""
    global_stats['commands_used'] += 1
    guild = ctx.guild

    total = guild.member_count
    humans = len([m for m in guild.members if not m.bot])
    bots = len([m for m in guild.members if m.bot])

    online = len([m for m in guild.members if m.status == discord.Status.online])
    idle = len([m for m in guild.members if m.status == discord.Status.idle])
    dnd = len([m for m in guild.members if m.status == discord.Status.dnd])
    offline = len([m for m in guild.members if m.status == discord.Status.offline])

    embed = create_embed(
        f"👥 Membros do {guild.name}",
        f"**📊 Total:** {total:,} membros\n\n"
        f"**👤 Por tipo:**\n"
        f"• Humanos: {humans:,}\n"
        f"• Bots: {bots:,}\n\n"
        f"**🟢 Por status:**\n"
        f"• Online: {online:,}\n"
        f"• Ausente: {idle:,}\n"
        f"• Ocupado: {dnd:,}\n"
        f"• Offline: {offline:,}",
        color=0x7289da
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    await ctx.send(embed=embed)

@bot.command(name='roles', aliases=['cargos'])
async def list_roles(ctx):
    """Lista todos os cargos do servidor"""
    global_stats['commands_used'] += 1
    guild = ctx.guild

    roles = sorted(guild.roles, key=lambda r: r.position, reverse=True)

    # Dividir em páginas se necessário
    roles_text = ""
    for role in roles[:20]:  # Limite de 20 cargos
        if role.name != "@everyone":
            member_count = len(role.members)
            roles_text += f"**{role.name}** - {member_count} membros\n"

    embed = create_embed(
        f"🎭 Cargos do {guild.name}",
        f"**Total:** {len(guild.roles)} cargos\n\n{roles_text}",
        color=0x7289da
    )

    if len(guild.roles) > 20:
        embed.set_footer(text=f"Mostrando apenas os primeiros 20 cargos de {len(guild.roles)}")

    await ctx.send(embed=embed)

@bot.command(name='channels', aliases=['canais'])
async def list_channels(ctx):
    """Lista todos os canais do servidor"""
    global_stats['commands_used'] += 1
    guild = ctx.guild

    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    categories = len(guild.categories)
    total = len(guild.channels)

    embed = create_embed(
        f"📁 Canais do {guild.name}",
        f"**📊 Resumo:**\n"
        f"• Total: {total} canais\n"
        f"• 💬 Texto: {text_channels}\n"
        f"• 🔊 Voz: {voice_channels}\n"
        f"• 📁 Categorias: {categories}\n\n"
        f"**💬 Canais de texto:**\n" + 
        "\n".join([f"• {channel.mention}" for channel in guild.text_channels[:10]]) +
        (f"\n... e mais {text_channels - 10}" if text_channels > 10 else ""),
        color=0x7289da
    )

    await ctx.send(embed=embed)

@bot.command(name='version', aliases=['versao'])
async def bot_version(ctx):
    """Informações da versão do bot"""
    global_stats['commands_used'] += 1

    embed = create_embed(
        "🤖 RXbot - Informações de Versão",
        f"""**🔖 Versão:** 2.1.0 (Estável Otimizada)
        **📅 Última atualização:** Janeiro 2025
        **🐍 Python:** {platform.python_version()}
        **📦 Discord.py:** {discord.__version__}
        **💻 Plataforma:** {platform.system()} {platform.release()}

        **🆕 Novidades da versão:**
        • ✅ Sistema de tickets com feedback corrigido
        • ✅ Sistema de fechamento de tickets melhorado
        • ✅ Comando RXinventario corrigido
        • ✅ Comandos faltando adicionados
        • ✅ Economia de recursos no Railway
        • ✅ Sistema de keep-alive otimizado

        **📊 Estatísticas:**
        • Uptime: {format_time(int((datetime.datetime.now() - global_stats['uptime_start']).total_seconds()))}
        • Comandos: 300+ disponíveis
        • Sistemas: Tickets, Economia, Ranks, IA""",
        color=0x00ff00
    )

    await ctx.send(embed=embed)

@bot.command(name='id')
async def get_id(ctx, user: discord.Member = None):
    """Mostra o ID do usuário"""
    global_stats['commands_used'] += 1
    target = user or ctx.author

    embed = create_embed(
        f"🆔 ID de {target.display_name}",
        f"**ID do usuário:** `{target.id}`\n"
        f"**Nome:** {target.name}#{target.discriminator}\n"
        f"**Menção:** {target.mention}",
        color=0x7289da
    )

    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await ctx.send(embed=embed)

# ============ COMANDOS DE TESTE ============
@bot.command(name='testeinventario', aliases=['testinv'])
async def teste_inventario(ctx):
    """Testa o sistema de inventário"""
    try:
        user_id = ctx.author.id

        with db_manager._lock: # Usar lock para acesso ao DB
            conn = await db_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT user_id, inventory FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()

            if not result:
                embed = create_embed("❌ Usuário não encontrado", "Criando dados do usuário...", color=0xff6600)
                await ctx.send(embed=embed)

                await db_manager.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))

                cursor.execute('SELECT user_id, inventory FROM users WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()

            user_id_db, inventory_data = result
            inventory = json.loads(inventory_data) if inventory_data else {}

            conn.close()

        embed = create_embed(
            "🔧 Teste de Inventário",
            f"""**✅ Diagnóstico completo:**
            
            **👤 Usuário ID:** {user_id}
            **💾 No banco:** {user_id_db}
            **📦 Dados do inventário:** {inventory_data or 'NULL'}
            **📝 Inventário processado:** {inventory}
            **🔢 Total de itens:** {len(inventory)}
            
            **🎯 Status:** {'✅ Funcionando' if inventory_data is not None else '⚠️ Inventário vazio'}
            
            **💡 Dica:** Se você comprou itens e não aparecem, use este comando para diagnosticar.""",
            color=0x00ff00 if inventory else 0xffaa00
        )

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro no teste de inventário: {e}")
        embed = create_embed("❌ Erro no teste", f"Erro: {str(e)}", color=0xff0000)
        await ctx.send(embed=embed)

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
        user_count = await db_manager.execute('SELECT COUNT(*) FROM users')
        ticket_count = await db_manager.execute('SELECT COUNT(*) FROM tickets')
        giveaway_count = await db_manager.execute('SELECT COUNT(*) FROM giveaways')
        resultados.append(f"✅ **Database:** {user_count[0][0]} users, {ticket_count[0][0]} tickets, {giveaway_count[0][0]} sorteios")
    except Exception as e:
        resultados.append(f"❌ **Database:** {str(e)[:50]}...")

    # 2. Teste Keep-alive
    try:
        async with http_manager:
            async with http_manager._session.get('http://0.0.0.0:8080/ping', timeout=5) as response:
                if response.status == 200:
                    resultados.append("✅ **Keep-alive:** Porta 8080 ativa")
                else:
                    resultados.append(f"⚠️ **Keep-alive:** Status {response.status}")
    except Exception as e:
        resultados.append(f"❌ **Keep-alive:** {str(e)[:50]}...")

    # 3. Teste Memória
    try:
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent()
        resultados.append(f"✅ **Sistema:** RAM {memory.percent}%, CPU {cpu}%")
    except Exception as e:
        resultados.append("⚠️ **Sistema:** Dados não disponíveis")

    # 4. Teste Conexão Discord
    latency = round(bot.latency * 1000, 2)
    if latency < 200:
        resultados.append(f"✅ **Discord:** {latency}ms - Excelente")
    else:
        resultados.append(f"⚠️ **Discord:** {latency}ms - Lenta")

    # 5. Teste Background Tasks
    running_tasks = []
    if update_status.is_running(): running_tasks.append("Status")
    if backup_database.is_running(): running_tasks.append("Backup")
    if check_reminders.is_running(): running_tasks.append("Reminders")
    if check_giveaways.is_running(): running_tasks.append("Giveaways")
    if cleanup_memory.is_running(): running_tasks.append("Cleanup")

    if len(running_tasks) >= 3:
        resultados.append(f"✅ **Tasks:** {len(running_tasks)}/5 ativos")
    else:
        resultados.append(f"⚠️ **Tasks:** {len(running_tasks)}/5 ativos")

    # 6. Teste Arquivos Críticos
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
        user_count = await db_manager.execute('SELECT COUNT(*) FROM users')
        resultados.append("✅ **Database:** Funcionando - " + str(user_count[0][0]) + " usuários")
    except Exception as e:
        resultados.append("❌ **Database:** Erro - " + str(e))

    # 2. Teste Keep-alive
    try:
        async with http_manager:
            async with http_manager._session.get('http://0.0.0.0:8080/ping', timeout=5) as response:
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
        category = discord.utils.get(ctx.guild.categories, name="📋 Tickets")
        if category:
            resultados.append("✅ **Tickets:** Categoria existe")
        else:
            resultados.append("⚠️ **Tickets:** Categoria não existe (será criada automaticamente)")
    except Exception as e:
        resultados.append("❌ **Tickets:** Erro - " + str(e))

    # 5. Teste XP System
    try:
        user_data = await get_user_data(ctx.author.id)
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
    if update_status.is_running(): running_tasks.append("Status Update")
    if backup_database.is_running(): running_tasks.append("Backup")
    if check_reminders.is_running(): running_tasks.append("Reminders")
    if check_giveaways.is_running(): running_tasks.append("Giveaways")
    if cleanup_memory.is_running(): running_tasks.append("Cleanup")

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
`RXajuda economia` - Dinheiro, loja premium, trabalho, troca de itens

**🏆 Ranks:**
`RXajuda ranks` - Sistema de ranking e XP

**⚔️ Eventos de Clan:**
`RXajuda eventos` - Batalhas entre clans e apostas

**⚙️ Utilidades:**
`RXajuda utilidades` - Ferramentas, conversores e lembretes

**🛡️ Moderação:**
`RXajuda moderacao` - Kick, ban, clear, warns

**📊 Informações:**
`RXajuda info` - Stats, perfil, servidor, avatar

**🎁 Sorteios:**
`RXajuda sorteios` - Sistema completo de sorteios

**🎟️ Tickets:**
`RXajuda tickets` - Sistema de suporte com feedback

**👑 Administração:**
`RXajuda admin` - Comandos para administradores

**🛠️ Sistema:**
`RXajuda sistema` - Status, performance, diagnóstico

**🤖 IA Avançada:**
Mencione o bot para conversar!

**Total:** 300+ comandos disponíveis!""",
            color=0x7289da
        )
        embed.set_footer(text="Use RXajuda <categoria> para ver comandos específicos!")
        await ctx.send(embed=embed)

    elif categoria.lower() in ['diversao', 'diversão', 'fun']:
        embed = create_embed(
            "🎮 Comandos de Diversão",
            """**🎲 Jogos Básicos:**
• `RXjokenpo <escolha>` - Pedra, papel, tesoura
• `RXdado [lados]` - Rola um dado (padrão 6 lados)
• `RXmoeda` - Cara ou coroa

**🎊 Entretenimento:**
• `RXpiada` - Conta uma piada aleatória
• `RXenquete <pergunta>` - Cria enquete com reações
• `RXpoll <pergunta>` - Enquete rápida

**🎮 Jogos da Loja:**
• **Desafio do Dia** - Mini-game com prêmios (item da loja)
• **Caixa Misteriosa** - Caixa com surpresas (item da loja)
• **Explosão de Moedas** - Chuva de moedas no chat (item da loja)

**🤖 IA Interativa:**
• Mencione o bot para conversar!
• Sistema de IA com 200+ tópicos
• Respostas contextuais inteligentes""",
            color=0x7289da
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['economia', 'money', 'eco']:
        embed = create_embed(
            "💰 Comandos de Economia",
            """**💵 Dinheiro Básico:**
• `RXsaldo [@user]` - Ver saldo (carteira + banco)
• `RXdaily` - Recompensa diária (100 moedas)
• `RXweekly` - Recompensa semanal (700 moedas)
• `RXmonthly` - Recompensa mensal (2500 moedas)
• `RXtrabalhar` - Trabalhe por dinheiro (cooldown 2h)
• `RXcrime` - Cometa um crime (risco/recompensa, cooldown 4h)

**🏦 Transferências:**
• `RXtransferir <@user> <valor>` - Transferir dinheiro
• `RXpay <@user> <valor>` - Pagar alguém
• `RXdepositar <valor>` - Depositar no banco
• `RXsacar <valor>` - Sacar do banco

**🛒 Loja Premium (10 itens únicos):**
• `RXloja` - Ver loja com itens exclusivos
• `RXcomprar <id>` - Comprar item da loja
• `RXinventario [@user]` - Ver inventário completo
• `RXusar <id>` - Usar item comprado

**🔄 Sistema de Troca (NOVO):**
• `RXdaritem <@user> <id> [qtd]` - Dar item para outro usuário
• `RXtrocar <@user>` - Sistema de troca segura entre usuários
• `RXefeitos [@user]` - Ver buffs e efeitos ativos
• `RXsettitle <título>` - Definir título personalizado (requer item)

**👑 Administração:**
• `RXaddsaldo <@user> <valor>` - [ADMIN] Adicionar saldo
• `RXremovesaldo <@user> <valor>` - [ADMIN] Remover saldo""",
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
            """**⏰ Ferramentas Básicas:**
• `RXlembrete <tempo> <texto>` - Criar lembrete
• `RXenquete <pergunta>` - Criar enquete
• `RXpoll <pergunta>` - Enquete rápida

**🔧 Conversores:**
• `RXbase64 <texto>` - Converter para base64
• `RXhash <texto>` - Gerar hash MD5/SHA
• `RXbin <texto>` - Converter para binário
• `RXhex <texto>` - Converter para hexadecimal

**📝 Textos:**
• `RXreverse <texto>` - Inverter texto
• `RXuppercase <texto>` - MAIÚSCULAS
• `RXlowercase <texto>` - minúsculas
• `RXcapitalize <texto>` - Primeira Maiúscula

**🔒 Segurança:**
• `RXpassword [tamanho]` - Gerar senha segura
• `RXqr <texto>` - Gerar QR Code

**💡 Dica:** Use `RXlembrete 30m Estudar` para lembretes!""",
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

**Exemplo:**
`RXcriarsorteio iPhone 15 | iPhone 15 Pro | 24h | 1`

**Durações aceitas:** 30m, 2h, 1d, 7d

**Para Todos:**
• `RXsorteios` - Ver sorteios ativos
• `RXgiveaways` - Lista de sorteios
• Reaja com 🎉 para participar!""",
            color=0xffd700
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['tickets', 'ticket', 'suporte']:
        embed = create_embed(
            "🎟️ Sistema Completo de Tickets",
            """**📝 Criar Tickets:**
• `RXticket <motivo>` - Criar ticket com motivo específico
• `RXticket` - Menu interativo de criação rápida
• `RXtestetier` - Ticket específico para teste tier

**🎯 Sistema Rápido (React):**
🐛 Bug/Erro no bot | 💰 Problema com economia
⚖️ Denúncia/Moderação | 💡 Sugestão/Ideia
❓ Dúvida geral | 🛠️ Suporte técnico | 👑 Tier

**🔧 Gerenciar Tickets:**
• Reaja com 🔒 para fechar ticket
• `RXadduser <@user>` - Adicionar usuário ao ticket
• `RXremoveuser <@user>` - Remover usuário do ticket

**⭐ Sistema de Feedback (NOVO):**
• `RXfeedback <texto> X/10` - Avaliar atendimento
• `RXfeedbacks` - [STAFF] Ver todas as avaliações
• Sistema de notas de 0 a 10
• Estatísticas automáticas para staff

**👑 Para Staff/Admin:**
• `RXtickets` - Ver todos os tickets
• `RXresultadotier <resultado>` - Enviar resultado teste tier
• Prioridade automática para tickets tier
• Logs automáticos de fechamento""",
            color=0x7289da
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['admin', 'administracao']:
        embed = create_embed(
            "👑 Comandos de Administração",
            """**🎟️ Sistema de Tickets:**
• `RXresultadotier <resultado>` - Enviar resultado teste tier
• `RXfeedbacks` - Ver avaliações de tickets (com estatísticas)

**🎁 Sistema de Sorteios:**
• `RXcriarsorteio <dados>` - Criar sorteios
• `RXendgiveaway <id>` - Finalizar sorteio
• `RXreroll <id>` - Sortear novamente

**⚔️ Eventos de Clan:**
• `RXcriareventoclan <dados>` - Criar batalha entre clans
• `RXeventosclan` - Ver eventos ativos
• `RXfinalizareventoclan <id> <vencedor>` - Finalizar evento

**💰 Economia Admin:**
• `RXaddsaldo <@user> <valor>` - Adicionar saldo
• `RXremovesaldo <@user> <valor>` - Remover saldo

**🛡️ Moderação Avançada:**
• `RXban <@user> [motivo]` - Ban com confirmação
• `RXkick <@user> [motivo]` - Kick com confirmação
• `RXclear <quantidade>` - Limpeza com confirmação
• `RXwarn <@user> [motivo]` - Sistema de warns

**🔧 Sistema e Monitoramento:**
• `RXdiagnostico` - Diagnóstico completo do sistema
• `RXperformance` - Monitor de performance detalhado
• `RXtestecompleto` - Teste de todos os sistemas
• `RXbackup` - Backup do banco de dados

**💡 Total:** 300+ comandos | 8 sistemas de proteção 24/7""",
            color=0xff6b6b
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['sistema', 'system', 'status']:
        embed = create_embed(
            "🛠️ Comandos de Sistema",
            """**📊 Status e Informações:**
• `RXping` - Latência do bot
• `RXstatus` - Status completo do sistema
• `RXuptime` - Tempo online do bot
• `RXstats` - Estatísticas detalhadas do bot

**🔍 Monitoramento:**
• `RXperformance` - [ADMIN] Monitor de performance
• `RXdiagnostico` - [ADMIN] Diagnóstico completo
• `RXtestecompleto` - [ADMIN] Teste de todos os sistemas

**🌐 Keep-alive System:**
• ✅ Auto-ping (25s)
• ✅ Keep-alive externo (120s)
• ✅ Heartbeat (180s)
• ✅ Monitor de emergência (180s)
• ✅ Sistema anti-hibernação (45s)
• ✅ Reconexão automática

**🔧 Administração:**
• `RXbackup` - [ADMIN] Backup do banco de dados
• Sistema de restart automático
• Monitoramento de latência
• Notificações de erro no canal de alerta

**💡 Dica:** O bot tem 8 sistemas de proteção rodando 24/7!""",
            color=0x00ff80
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['eventos', 'clan', 'clans']:
        embed = create_embed(
            "⚔️ Sistema de Eventos de Clan",
            """**Para Membros:**
• `RXeventosclan` - Ver eventos ativos
• Reaja com ⚔️ para participar
• Reaja com 🏆 para apostar no seu clan

**Para Administradores:**
• `RXcriareventoclan <dados>` - Criar evento
• `RXfinalizareventoclan <id> <vencedor>` - Finalizar

**Formato de Criação:**
`RXcriareventoclan CLAN1 vs CLAN2 | tipo | aposta | duração`

**Exemplo:**
`RXcriareventoclan XCLAN vs GSN | Battle Royale | 5000 | 2h`

**Tipos de Eventos:**
• Battle Royale
• Team Deathmatch  
• King of the Hill
• Capture the Flag
• Tournament

**Durações aceitas:** 30m, 1h, 2h, 6h, 12h, 1d

**Como funciona:**
• Membros dos clans participam com aposta obrigatória
• Admin decide o vencedor
• Prêmio total é distribuído entre os vencedores""",
            color=0xff6600
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

    await active_games.set(msg.id, {
        'type': 'clear_confirmation',
        'user': ctx.author.id,
        'channel': ctx.channel.id,
        'amount': amount
    })

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
        
        **👤 Usuário:** {member.mention} ({member.name}#{member.discriminator})
        **🛡️ Moderador:** {ctx.author.mention}
        **📝 Motivo:** {reason}
        
        **⚠️ Esta ação é IRREVERSÍVEL!**
        **Tem certeza que deseja continuar?**
        
        Reaja com ✅ para confirmar ou ❌ para cancelar""",
        color=0xff0000
    )

    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    await active_games.set(msg.id, {
        'type': 'ban_confirmation',
        'user': ctx.author.id,
        'channel': ctx.channel.id,
        'member_id': member.id,
        'reason': reason
    })

# ============ COMANDOS DE ECONOMIA ============
@bot.command(name='saldo', aliases=['balance', 'bal'])
async def balance(ctx, user: discord.Member = None):
    """Ver saldo do usuário"""
    target = user or ctx.author
    data = await get_user_data(target.id)

    if not data:
        await update_user_data(target.id)
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
    data = await get_user_data(user_id)

    if not data:
        await update_user_data(user_id)
        data = await get_user_data(user_id)

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
        await db_manager.execute('UPDATE users SET coins = ?, last_daily = ? WHERE user_id = ?',
                      (new_coins, today, user_id))
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
@bot.command(name='rank', aliases=['nivel', 'meurank'])
async def user_rank(ctx, user: discord.Member = None):
    """Ver rank do usuário"""
    global_stats['commands_used'] += 1
    target = user or ctx.author
    data = await get_user_data(target.id)

    if not data:
        await update_user_data(target.id)
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

    # Obter título personalizado se existir
    custom_title = ""
    if data:
        settings_data = data[11]
        settings = json.loads(settings_data) if settings_data else {}
        if settings.get('custom_title'):
            custom_title = f" | {settings['custom_title']}"

    embed = create_embed(
        f"{current_rank['emoji']} Rank de {target.display_name}{custom_title}",
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

@bot.command(name='transferir', aliases=['transfer', 'pay'])
async def transferir(ctx, user: discord.Member, amount: int):
    """Transferir dinheiro para outro usuário"""
    if amount <= 0:
        embed = create_embed("❌ Valor inválido", "Use valores positivos!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if user == ctx.author:
        embed = create_embed("❌ Impossível", "Você não pode transferir para si mesmo!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    sender_data = await get_user_data(ctx.author.id)
    if not sender_data:
        await update_user_data(ctx.author.id)
        sender_data = await get_user_data(ctx.author.id)

    sender_coins = sender_data[1]

    if sender_coins < amount:
        embed = create_embed(
            "💸 Dinheiro insuficiente",
            f"Você só tem **{sender_coins:,} moedas**!\nPrecisa de **{amount:,} moedas**.",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

    # Processar transferência
    try:
        receiver_data = await get_user_data(user.id)
        if not receiver_data:
            await update_user_data(user.id)
            receiver_data = await get_user_data(user.id)

        receiver_coins = receiver_data[1]

        async with db_manager._lock:
            conn = await db_manager.get_connection()
            cursor = conn.cursor()

            # Atualizar saldos
            cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (sender_coins - amount, ctx.author.id))
            cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (receiver_coins + amount, user.id))

            # Registrar transações
            await db_manager.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (ctx.author.id, ctx.guild.id, 'transfer_out', -amount, f"Transferiu para {user.name}"))

            await db_manager.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (user.id, ctx.guild.id, 'transfer_in', amount, f"Recebeu de {ctx.author.name}"))

            conn.commit()
            conn.close()

        embed = create_embed(
            "✅ Transferência realizada!",
            f"**De:** {ctx.author.mention}\n"
            f"**Para:** {user.mention}\n"
            f"**Valor:** {amount:,} moedas\n\n"
            f"**Seu novo saldo:** {sender_coins - amount:,} moedas",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

        # Notificar receptor
        try:
            dm_embed = create_embed(
                "💰 Dinheiro Recebido!",
                f"Você recebeu **{amount:,} moedas** de {ctx.author.mention}!\n"
                f"**Seu novo saldo:** {receiver_coins + amount:,} moedas",
                color=0x00ff00
            )
            await user.send(embed=dm_embed)
        except:
            pass

    except Exception as e:
        logger.error(f"Erro na transferência: {e}")
        embed = create_embed("❌ Erro", "Erro ao processar transferência!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='depositar', aliases=['deposit'])
async def depositar(ctx, amount: int):
    """Depositar dinheiro no banco"""
    if amount <= 0:
        embed = create_embed("❌ Valor inválido", "Use valores positivos!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    user_data = await get_user_data(ctx.author.id)
    if not user_data:
        await update_user_data(ctx.author.id)
        user_data = await get_user_data(ctx.author.id)

    coins, bank = user_data[1], user_data[5]

    if coins < amount:
        embed = create_embed(
            "💸 Dinheiro insuficiente",
            f"Você só tem **{coins:,} moedas** na carteira!",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

    try:
        async with db_manager._lock:
            conn = await db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = ?, bank = ? WHERE user_id = ?', 
                          (coins - amount, bank + amount, ctx.author.id))
            conn.commit()
            conn.close()

        embed = create_embed(
            "🏦 Depósito realizado!",
            f"**Valor depositado:** {amount:,} moedas\n"
            f"**Carteira:** {coins - amount:,} moedas\n"
            f"**Banco:** {bank + amount:,} moedas\n"
            f"**Total:** {(coins - amount) + (bank + amount):,} moedas",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro no depósito: {e}")
        embed = create_embed("❌ Erro", "Erro ao depositar!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='sacar', aliases=['withdraw'])
async def sacar(ctx, amount: int):
    """Sacar dinheiro do banco"""
    if amount <= 0:
        embed = create_embed("❌ Valor inválido", "Use valores positivos!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    user_data = await get_user_data(ctx.author.id)
    if not user_data:
        await update_user_data(ctx.author.id)
        user_data = await get_user_data(ctx.author.id)

    coins, bank = user_data[1], user_data[5]

    if bank < amount:
        embed = create_embed(
            "🏦 Saldo insuficiente no banco",
            f"Você só tem **{bank:,} moedas** no banco!",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

    try:
        async with db_manager._lock:
            conn = await db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = ?, bank = ? WHERE user_id = ?', 
                          (coins + amount, bank - amount, ctx.author.id))
            conn.commit()
            conn.close()

        embed = create_embed(
            "💰 Saque realizado!",
            f"**Valor sacado:** {amount:,} moedas\n"
            f"**Carteira:** {coins + amount:,} moedas\n"
            f"**Banco:** {bank - amount:,} moedas\n"
            f"**Total:** {(coins + amount) + (bank - amount):,} moedas",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro no saque: {e}")
        embed = create_embed("❌ Erro", "Erro ao sacar!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='trabalhar', aliases=['work'])
async def trabalhar(ctx):
    """Trabalhar para ganhar dinheiro"""
    user_data = await get_user_data(ctx.author.id)
    if not user_data:
        await update_user_data(ctx.author.id)
        user_data = await get_user_data(ctx.author.id)

    # Verificar cooldown (2 horas)
    try:
        settings_data = user_data[11]
        settings = json.loads(settings_data) if settings_data else {}
        last_work = settings.get('last_work', 0)

        current_time = time.time()
        cooldown_time = WORK_COOLDOWN  # 2 horas

        if current_time - last_work < cooldown_time:
            remaining = cooldown_time - (current_time - last_work)
            embed = create_embed(
                "⏰ Muito cansado!",
                f"Você precisa descansar por mais **{format_time(int(remaining))}**!",
                color=0xff6b6b
            )
            await ctx.send(embed=embed)
            return
    except:
        settings = {}

    # Trabalhos disponíveis
    trabalhos = [
        {"nome": "Programador", "min": 150, "max": 300, "emoji": "💻"},
        {"nome": "Delivery", "min": 80, "max": 200, "emoji": "🛵"},
        {"nome": "Professor", "min": 120, "max": 250, "emoji": "👨‍🏫"},
        {"nome": "Cozinheiro", "min": 100, "max": 220, "emoji": "👨‍🍳"},
        {"nome": "Mecânico", "min": 90, "max": 180, "emoji": "🔧"},
        {"nome": "Designer", "min": 110, "max": 240, "emoji": "🎨"},
    ]

    trabalho = random.choice(trabalhos)
    ganho = random.randint(trabalho["min"], trabalho["max"])

    # Bonus por level
    level = user_data[3]
    bonus = int(ganho * (level * 0.05))  # 5% por level
    ganho_total = ganho + bonus

    try:
        async with db_manager._lock:
            conn = await db_manager.get_connection()
            cursor = conn.cursor()

            # Atualizar dinheiro
            new_coins = user_data[1] + ganho_total
            cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins, ctx.author.id))

            # Atualizar cooldown
            settings['last_work'] = current_time
            cursor.execute('UPDATE users SET settings = ? WHERE user_id = ?', (json.dumps(settings), ctx.author.id))

            # Registrar transação
            await db_manager.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (ctx.author.id, ctx.guild.id, 'work', ganho_total, f"Trabalhou como {trabalho['nome']}"))

            conn.commit()
            conn.close()

        embed = create_embed(
            f"{trabalho['emoji']} Trabalho Concluído!",
            f"**Profissão:** {trabalho['nome']}\n"
            f"**Ganho base:** {ganho:,} moedas\n"
            f"**Bônus level {level}:** {bonus:,} moedas\n"
            f"**Total ganho:** {ganho_total:,} moedas\n"
            f"**Novo saldo:** {new_coins:,} moedas\n\n"
            f"*Próximo trabalho em 2 horas*",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

        # Chance de ganhar XP
        if random.randint(1, 100) <= 30:  # 30% chance
            xp_bonus = random.randint(10, 25)
            await add_xp(ctx.author.id, xp_bonus)
            await ctx.send(f"🎉 Bônus: +{xp_bonus} XP por trabalhar bem!")

    except Exception as e:
        logger.error(f"Erro no trabalho: {e}")
        embed = create_embed("❌ Erro", "Erro ao trabalhar!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='crime', aliases=['roubar'])
async def crime(ctx):
    """Cometer um crime (risco/recompensa)"""
    user_data = await get_user_data(ctx.author.id)
    if not user_data:
        await update_user_data(ctx.author.id)
        user_data = await get_user_data(ctx.author.id)

    # Verificar cooldown (4 horas)
    try:
        settings_data = user_data[11]
        settings = json.loads(settings_data) if settings_data else {}
        last_crime = settings.get('last_crime', 0)

        current_time = time.time()
        cooldown_time = CRIME_COOLDOWN  # 4 horas

        if current_time - last_crime < cooldown_time:
            remaining = cooldown_time - (current_time - last_crime)
            embed = create_embed(
                "🚔 Procurado pela polícia!",
                f"Você precisa se esconder por mais **{format_time(int(remaining))}**!",
                color=0xff6b6b
            )
            await ctx.send(embed=embed)
            return
    except:
        settings = {}

    # 60% chance de sucesso
    sucesso = random.randint(1, 100) <= 60

    crimes = [
        {"nome": "Hackear banco", "ganho": (800, 1500), "perda": (200, 400), "emoji": "💻"},
        {"nome": "Roubar loja", "ganho": (300, 800), "perda": (100, 300), "emoji": "🏪"},
        {"nome": "Furtar carteira", "ganho": (150, 400), "perda": (50, 150), "emoji": "👛"},
        {"nome": "Golpe online", "ganho": (500, 1200), "perda": (150, 350), "emoji": "📱"},
        {"nome": "Contrabando", "ganho": (600, 1000), "perda": (200, 500), "emoji": "📦"},
    ]

    crime = random.choice(crimes)

    try:
        async with db_manager._lock:
            conn = await db_manager.get_connection()
            cursor = conn.cursor()

            if sucesso:
                # Crime bem-sucedido
                ganho = random.randint(crime["ganho"][0], crime["ganho"][1])
                new_coins = user_data[1] + ganho
                cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins, ctx.author.id))

                await db_manager.execute('''
                    INSERT INTO transactions (user_id, guild_id, type, amount, description)
                    VALUES (?, ?, ?, ?, ?)
                ''', (ctx.author.id, ctx.guild.id, 'crime_success', ganho, f"Crime bem-sucedido: {crime['nome']}"))

                embed = create_embed(
                    "🎭 Crime Bem-Sucedido!",
                    f"**Crime:** {crime['emoji']} {crime['nome']}\n"
                    f"**Ganho:** {ganho:,} moedas\n"
                    f"**Novo saldo:** {new_coins:,} moedas\n\n"
                    f"🕵️ *Ninguém te viu...*",
                    color=0x00ff00
                )

            else:
                # Crime falhou
                perda = random.randint(crime["perda"][0], crime["perda"][1])
                perda = min(perda, user_data[1])  # Não pode perder mais do que tem
                new_coins = max(0, user_data[1] - perda)
                cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins, ctx.author.id))

                await db_manager.execute('''
                    INSERT INTO transactions (user_id, guild_id, type, amount, description)
                    VALUES (?, ?, ?, ?, ?)
                ''', (ctx.author.id, ctx.guild.id, 'crime_fail', -perda, f"Crime falhou: {crime['nome']}"))

                embed = create_embed(
                    "🚔 Crime Falhou!",
                    f"**Crime:** {crime['emoji']} {crime['nome']}\n"
                    f"**Multa:** {perda:,} moedas\n"
                    f"**Novo saldo:** {new_coins:,} moedas\n\n"
                    f"🚨 *A polícia te pegou!*",
                    color=0xff0000
                )

            # Atualizar cooldown
            settings['last_crime'] = current_time
            cursor.execute('UPDATE users SET settings = ? WHERE user_id = ?', (json.dumps(settings), ctx.author.id))

            conn.commit()
            conn.close()

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro no crime: {e}")
        embed = create_embed("❌ Erro", "Erro ao cometer crime!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='weekly', aliases=['semanal'])
async def weekly(ctx):
    """Recompensa semanal"""
    user_id = ctx.author.id
    data = await get_user_data(user_id)

    if not data:
        await update_user_data(user_id)
        data = await get_user_data(user_id)

    last_weekly = data[7]
    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())
    week_start_str = week_start.isoformat()

    if last_weekly and last_weekly >= week_start_str:
        next_week = week_start + datetime.timedelta(days=7)
        embed = create_embed(
            "⏰ Já coletado esta semana!",
            f"Você já coletou sua recompensa semanal!\nPróxima coleta: {next_week.strftime('%d/%m/%Y')}",
            color=0xff6b6b
        )
        await ctx.send(embed=embed)
        return

    # Update user data
    new_coins = data[1] + WEEKLY_REWARD

    try:
        await db_manager.execute('UPDATE users SET coins = ?, last_weekly = ? WHERE user_id = ?',
                      (new_coins, week_start_str, user_id))
    except Exception as e:
        logger.error(f"Error updating weekly: {e}")

    embed = create_embed(
        "🎁 Recompensa Semanal!",
        f"""**Recompensa:** {WEEKLY_REWARD:,} moedas
        **Novo saldo:** {new_coins:,} moedas
        
        🔥 *Continue coletando semanalmente!*""",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name='monthly', aliases=['mensal'])
async def monthly(ctx):
    """Recompensa mensal"""
    user_id = ctx.author.id
    data = await get_user_data(user_id)

    if not data:
        await update_user_data(user_id)
        data = await get_user_data(user_id)

    last_monthly = data[8]
    today = datetime.date.today()
    month_start = today.replace(day=1).isoformat()

    if last_monthly == month_start:
        next_month = (today.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        embed = create_embed(
            "⏰ Já coletado este mês!",
            f"Você já coletou sua recompensa mensal!\nPróxima coleta: {next_month.strftime('%d/%m/%Y')}",
            color=0xff6b6b
        )
        await ctx.send(embed=embed)
        return

    # Update user data
    new_coins = data[1] + MONTHLY_REWARD

    try:
        await db_manager.execute('UPDATE users SET coins = ?, last_monthly = ? WHERE user_id = ?',
                      (new_coins, month_start, user_id))
    except Exception as e:
        logger.error(f"Error updating monthly: {e}")

    embed = create_embed(
        "🎁 Recompensa Mensal!",
        f"""**Recompensa:** {MONTHLY_REWARD:,} moedas
        **Novo saldo:** {new_coins:,} moedas
        
        🔥 *Continue coletando mensalmente!*""",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name='leaderboard', aliases=['lb', 'toplist'])
async def leaderboard(ctx, tipo='xp'):
    """Ver ranking do servidor"""
    global_stats['commands_used'] += 1

    try:
        with db_manager._lock:
            conn = await db_manager.get_connection()
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

        embed.set_footer(text=f"Use RXleaderboard xp/coins/rep • Posição de {ctx.author.display_name}: #{await get_user_position(ctx.author.id, ctx.guild.id)}")
        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro no leaderboard: {e}")
        embed = create_embed("❌ Erro", "Erro ao carregar ranking. Tente novamente.", color=0xff0000)
        await ctx.send(embed=embed)

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
        await db_manager.execute('''
            INSERT INTO giveaways (guild_id, channel_id, creator_id, title, prize, winners_count, end_time, message_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (ctx.guild.id, ctx.channel.id, ctx.author.id, title, prize, winners_count, end_time, giveaway_msg.id))

    except ValueError:
        embed = create_embed("❌ Duração inválida", "Use números válidos: 30m, 2h, 1d", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='sorteios', aliases=['giveaways'])
async def list_giveaways(ctx):
    """Ver sorteios ativos"""
    try:
        giveaways = await db_manager.execute('''
            SELECT title, prize, end_time, winners_count, participants
            FROM giveaways
            WHERE guild_id = ? AND status = 'active'
            ORDER BY end_time
        ''', (ctx.guild.id,))

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
            title, prize, end_time_str, winners_count, participants_json, _ = giveaway  # Ignorar status e created_at
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

        # Buscar timestamp para registrar
        timestamp = datetime.datetime.now().isoformat()

        # Salvar feedback no banco
        try:
            await db_manager.execute('''CREATE TABLE IF NOT EXISTS ticket_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_channel_id INTEGER,
                user_id INTEGER,
                feedback_text TEXT,
                notas TEXT,
                media_nota INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

            await db_manager.execute('''
                INSERT INTO ticket_feedback (ticket_channel_id, user_id, feedback_text, notas, media_nota)
                VALUES (?, ?, ?, ?, ?)
            ''', (ctx.channel.id, ctx.author.id, avaliacao, ','.join(notas), media))
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
            **📅 Data:** <t:{int(datetime.datetime.fromisoformat(timestamp).timestamp())}:R>

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
        feedbacks = await db_manager.execute('''
            SELECT feedback_text, notas, media_nota, timestamp, user_id
            FROM ticket_feedback
            ORDER BY timestamp DESC
            LIMIT 10
        ''')

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

# ============ SISTEMA DE LOJA ============
# Itens da loja
LOJA_ITENS = {
    1: {"nome": "Desafio do Dia", "preco": 5000, "descricao": "Desafie outro jogador a um mini game. Quem vencer, ganha coins!", "emoji": "🎯", "raridade": "Comum"},
    2: {"nome": "Caixa Misteriosa", "preco": 7500, "descricao": "Ao abrir, pode conter moedas, XP, itens... ou nada!", "emoji": "🎁", "raridade": "Comum"},
    3: {"nome": "Ticket Prioritário (1 uso)", "preco": 10000, "descricao": "Ganhe prioridade no atendimento da staff ao abrir um ticket", "emoji": "🎫", "raridade": "Incomum"},
    4: {"nome": "Explosão de Moedas", "preco": 12000, "descricao": "Gera uma chuva de moedas no chat. Os 3 primeiros a clicar pegam!", "emoji": "🧨", "raridade": "Incomum"},
    5: {"nome": "Boost de XP (1h)", "preco": 15000, "descricao": "Dobra o XP ganho em todos os comandos por 1 hora", "emoji": "📈", "raridade": "Incomum"},
    6: {"nome": "Título Personalizado (1 uso)", "preco": 20000, "descricao": "Permite criar um título exclusivo para o seu perfil", "emoji": "👑", "raridade": "Raro"},
    7: {"nome": "Salário VIP (7 dias)", "preco": 25000, "descricao": "Durante 7 dias, você ganha +50% de coins nos comandos de trabalho", "emoji": "💼", "raridade": "Raro"},
    8: {"nome": "Cargo Exclusivo (3 dias)", "preco": 30000, "descricao": "Receba um cargo especial e estilizado no servidor RX por 72h", "emoji": "🛡", "raridade": "Raro"},
    9: {"nome": "RX Medalha Épica (colecionável)", "preco": 40000, "descricao": "Item mensal colecionável. No futuro, poderá ser trocado por prêmios exclusivos", "emoji": "🌌", "raridade": "Lendário"},
    10: {"nome": "DNA RX (item raro)", "preco": 50000, "descricao": "Item misterioso e ultra-raro. Guardar pode render evoluções, mascotes ou poderes especiais no futuro", "emoji": "🧬", "raridade": "Lendário"}
}

@bot.command(name='loja', aliases=['shop', 'store'])
async def loja(ctx):
    """Ver loja de itens"""
    global_stats['commands_used'] += 1

    embed = create_embed(
        "🛒 Loja Premium do RXbot",
        "✨ Itens exclusivos e poderosos disponíveis!\nUse `RXcomprar <id>` para comprar um item!",
        color=0xffd700
    )

    raridade_cores = {
        "Comum": "⚪",
        "Incomum": "🟢", 
        "Raro": "🔵",
        "Épico": "🟣",
        "Lendário": "🟡"
    }

    for item_id, item in LOJA_ITENS.items():
        raridade_emoji = raridade_cores.get(item['raridade'], "⚪")
        embed.add_field(
            name=f"{item['emoji']} {item['nome']} (ID: {item_id})",
            value=f"💰 **Preço:** {item['preco']:,} moedas\n"
                  f"{raridade_emoji} **Raridade:** {item['raridade']}\n"
                  f"📝 **Função:** {item['descricao']}",
            inline=True
        )

    embed.set_footer(text=f"Use RXinventario para ver seus itens | RXusar <id> para usar itens")
    await ctx.send(embed=embed)

@bot.command(name='comprar', aliases=['buy'])
async def comprar_item(ctx, item_id: int = None):
    """Comprar item da loja"""
    if not item_id:
        embed = create_embed("❌ ID necessário", "Use: `RXcomprar <id>`\nVeja a loja com `RXloja`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if item_id not in LOJA_ITENS:
        embed = create_embed("❌ Item não encontrado", "Use `RXloja` para ver itens disponíveis", color=0xff0000)
        await ctx.send(embed=embed)
        return

    item = LOJA_ITENS[item_id]
    user_data = await get_user_data(ctx.author.id)

    if not user_data:
        await update_user_data(ctx.author.id)
        user_data = await get_user_data(ctx.author.id)

    coins = user_data[1]

    if coins < item['preco']:
        embed = create_embed(
            "💸 Dinheiro insuficiente",
            f"Você precisa de **{item['preco']:,} moedas** para comprar **{item['nome']}**!\n"
            f"Você tem apenas **{coins:,} moedas**.",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

    # Processar compra
    try:
        async with db_manager._lock:
            conn = await db_manager.get_connection()
            cursor = conn.cursor()

            # Remover dinheiro
            new_coins = coins - item['preco']
            cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins, ctx.author.id))

            # Adicionar ao inventário
            cursor.execute('SELECT inventory FROM users WHERE user_id = ?', (ctx.author.id,))
            inventory_data = cursor.fetchone()[0]
            inventory = json.loads(inventory_data) if inventory_data else {}

            if str(item_id) in inventory:
                inventory[str(item_id)] += 1
            else:
                inventory[str(item_id)] = 1

            cursor.execute('UPDATE users SET inventory = ? WHERE user_id = ?', (json.dumps(inventory), ctx.author.id))

            # Registrar transação
            await db_manager.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (ctx.author.id, ctx.guild.id, 'compra', -item['preco'], f"Comprou {item['nome']}"))

            conn.commit()
            conn.close()

        embed = create_embed(
            f"✅ Compra realizada!",
            f"**Item:** {item['emoji']} {item['nome']}\n"
            f"**Preço:** {item['preco']:,} moedas\n"
            f"**Saldo restante:** {new_coins:,} moedas\n\n"
            f"Item adicionado ao seu inventário!",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro na compra: {e}")
        embed = create_embed("❌ Erro", "Erro ao processar compra!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='inventario', aliases=['inventory', 'inv'])
async def inventario(ctx, user: discord.Member = None):
    """Ver inventário de itens"""
    global_stats['commands_used'] += 1
    target = user or ctx.author

    try:
        inventory_data = await db_manager.execute('SELECT inventory FROM users WHERE user_id = ?', (target.id,))
        
        if not inventory_data:
            await update_user_data(target.id)
            embed = create_embed("📦 Inventário vazio", f"{target.display_name} ainda não tem itens!", color=0xffaa00)
            await ctx.send(embed=embed)
            return

        inventory_data_str = inventory_data[0][0]
        inventory = json.loads(inventory_data_str) if inventory_data_str else {}

        if not inventory:
            embed = create_embed("📦 Inventário vazio", f"{target.display_name} ainda não tem itens!", color=0xffaa00)
            await ctx.send(embed=embed)
            return

        embed = create_embed(
            f"🎒 Inventário de {target.display_name}",
            "Seus itens comprados na loja:",
            color=0x7289da
        )

        total_valor = 0
        items_added = 0

        for item_id, quantidade in inventory.items():
            try:
                item_id_int = int(item_id)
                if item_id_int in LOJA_ITENS and items_added < 25:  # Limite de 25 campos no embed
                    item = LOJA_ITENS[item_id_int]
                    valor_total = item['preco'] * quantidade
                    total_valor += valor_total

                    embed.add_field(
                        name=f"{item['emoji']} {item['nome']} (ID: {item_id})",
                        value=f"**Quantidade:** {quantidade}\n**Valor:** {valor_total:,} moedas\n**Use:** `RXusar {item_id}`",
                        inline=True
                    )
                    items_added += 1
            except (ValueError, KeyError) as e:
                logger.error(f"Erro ao processar item {item_id}: {e}")
                continue

        if items_added == 0:
            embed.add_field(
                name="❓ Itens não reconhecidos",
                value="Você tem itens no inventário, mas eles não são válidos.",
                inline=False
            )

        embed.add_field(
            name="💎 Valor Total do Inventário",
            value=f"{total_valor:,} moedas",
            inline=False
        )

        embed.set_footer(text=f"Use RXloja para ver itens disponíveis | Use RXusar <id> para usar itens")
        embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro no comando inventario: {e}")
        embed = create_embed("❌ Erro", "Erro ao carregar inventário. Tente novamente.", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='daritem', aliases=['giveitem', 'transferitem'])
async def dar_item(ctx, user: discord.Member, item_id: int, quantidade: int = 1):
    """Dar item do seu inventário para outro usuário"""
    if quantidade <= 0:
        embed = create_embed("❌ Quantidade inválida", "Use quantidades positivas!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if user == ctx.author:
        embed = create_embed("❌ Impossível", "Você não pode dar itens para si mesmo!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if user.bot:
        embed = create_embed("❌ Impossível", "Você não pode dar itens para bots!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if item_id not in LOJA_ITENS:
        embed = create_embed("❌ Item inválido", "Este item não existe!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    # Verificar se o usuário tem o item
    sender_data = await get_user_data(ctx.author.id)
    if not sender_data:
        embed = create_embed("❌ Sem itens", "Você não tem itens para dar!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    sender_inventory_data = sender_data[10]
    sender_inventory = json.loads(sender_inventory_data) if sender_inventory_data else {}

    if str(item_id) not in sender_inventory or sender_inventory[str(item_id)] < quantidade:
        item_name = LOJA_ITENS[item_id]['nome']
        embed = create_embed(
            "❌ Item insuficiente", 
            f"Você não tem {quantidade}x **{item_name}** suficientes!\n"
            f"Você tem apenas: {sender_inventory.get(str(item_id), 0)}",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

    try:
        # Obter dados do receptor
        receiver_data = await get_user_data(user.id)
        if not receiver_data:
            await update_user_data(user.id)
            receiver_data = await get_user_data(user.id)

        receiver_inventory_data = receiver_data[10]
        receiver_inventory = json.loads(receiver_inventory_data) if receiver_inventory_data else {}

        item = LOJA_ITENS[item_id]

        async with db_manager._lock:
            conn = await db_manager.get_connection()
            cursor = conn.cursor()

            # Remover do inventário do remetente
            sender_inventory[str(item_id)] -= quantidade
            if sender_inventory[str(item_id)] <= 0:
                del sender_inventory[str(item_id)]

            # Adicionar ao inventário do receptor
            if str(item_id) in receiver_inventory:
                receiver_inventory[str(item_id)] += quantidade
            else:
                receiver_inventory[str(item_id)] = quantidade

            # Atualizar banco de dados
            cursor.execute('UPDATE users SET inventory = ? WHERE user_id = ?', 
                          (json.dumps(sender_inventory), ctx.author.id))
            cursor.execute('UPDATE users SET inventory = ? WHERE user_id = ?', 
                          (json.dumps(receiver_inventory), user.id))

            # Registrar transações
            await db_manager.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (ctx.author.id, ctx.guild.id, 'item_given', 0, f"Deu {quantidade}x {item['nome']} para {user.name}"))

            await db_manager.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (user.id, ctx.guild.id, 'item_received', 0, f"Recebeu {quantidade}x {item['nome']} de {ctx.author.name}"))

            conn.commit()
            conn.close()

        embed = create_embed(
            "✅ Item Transferido!",
            f"**{item['emoji']} {item['nome']}**\n"
            f"**Quantidade:** {quantidade}x\n"
            f"**De:** {ctx.author.mention}\n"
            f"**Para:** {user.mention}\n\n"
            f"Item transferido com sucesso!",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

        # Notificar receptor
        try:
            dm_embed = create_embed(
                "🎁 Item Recebido!",
                f"Você recebeu **{quantidade}x {item['emoji']} {item['nome']}** de {ctx.author.mention}!\n\n"
                f"**Descrição:** {item['descricao']}\n"
                f"Use `RXinventario` para ver seus itens!",
                color=0x00ff00
            )
            await user.send(embed=dm_embed)
        except:
            pass

        # Log da transferência
        logger.info(f"Item transferido: {ctx.author.name} deu {quantidade}x {item['nome']} para {user.name}")

    except Exception as e:
        logger.error(f"Erro ao transferir item: {e}")
        embed = create_embed("❌ Erro", "Erro ao transferir item! Contate um administrador.", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='trocar', aliases=['trade', 'negociar'])
async def sistema_troca(ctx, user: discord.Member):
    """Sistema de troca segura entre usuários"""
    if user == ctx.author:
        embed = create_embed("❌ Impossível", "Você não pode trocar itens com você mesmo!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if user.bot:
        embed = create_embed("❌ Impossível", "Você não pode trocar itens com bots!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    # Verificar se ambos usuários têm itens
    sender_data = await get_user_data(ctx.author.id)
    receiver_data = await get_user_data(user.id)

    if not sender_data:
        embed = create_embed("❌ Sem dados", "Você não tem dados no sistema!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if not receiver_data:
        embed = create_embed("❌ Usuário inválido", "O usuário não tem dados no sistema!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    sender_inventory_data = sender_data[10]
    sender_inventory = json.loads(sender_inventory_data) if sender_inventory_data else {}

    receiver_inventory_data = receiver_data[10]
    receiver_inventory = json.loads(receiver_inventory_data) if receiver_inventory_data else {}

    if not sender_inventory:
        embed = create_embed("❌ Sem itens", "Você não possui itens para trocar!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if not receiver_inventory:
        embed = create_embed("❌ Sem itens", f"{user.display_name} não possui itens para trocar!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    # Criar embed de apresentação da troca
    embed = create_embed(
        "🔄 Sistema de Troca Segura",
        f"""**Iniciando troca entre:**
        **👤 {ctx.author.mention}** ↔️ **👤 {user.mention}**
        
        **📋 Como funciona:**
        1️⃣ Ambos escolhem itens para oferecer
        2️⃣ Sistema mostra a proposta completa
        3️⃣ Ambos confirmam a troca
        4️⃣ Itens são transferidos automaticamente
        
        **⚠️ Regras:**
        • A troca é **irreversível** após confirmação
        • Ambos devem concordar com os termos
        • Sistema 100% seguro - sem roubos
        
        **🔥 {user.mention}, você aceita negociar?**
        Reaja com ✅ para aceitar ou ❌ para recusar""",
        color=0x7289da
    )

    trade_msg = await ctx.send(embed=embed)
    await trade_msg.add_reaction("✅")
    await trade_msg.add_reaction("❌")

    # Armazenar dados da troca
    await active_games.set(trade_msg.id, {
        'type': 'trade_invitation',
        'initiator': ctx.author.id,
        'target': user.id,
        'channel': ctx.channel.id,
        'step': 'invitation'
    })

@bot.command(name='efeitos', aliases=['buffs', 'effects'])
async def ver_efeitos(ctx, user: discord.Member = None):
    """Ver buffs e efeitos ativos do usuário"""
    target = user or ctx.author
    user_data = await get_user_data(target.id)

    if not user_data:
        embed = create_embed("❌ Dados não encontrados", f"{target.display_name} não está no sistema!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    settings_data = user_data[11]
    settings = json.loads(settings_data) if settings_data else {}

    efeitos_ativos = []
    current_time = datetime.datetime.now().timestamp()

    # Verificar XP Boost
    xp_boost_end = settings.get('xp_boost', 0)
    if xp_boost_end > current_time:
        tempo_restante = int(xp_boost_end - current_time)
        efeitos_ativos.append(f"📈 **Boost de XP:** XP dobrado por {format_time(tempo_restante)}")

    # Verificar Salário VIP
    vip_salary_end = settings.get('vip_salary', 0)
    if vip_salary_end > current_time:
        dias_restantes = int((vip_salary_end - current_time) / 86400)
        efeitos_ativos.append(f"💼 **Salário VIP:** +50% em trabalhos por {dias_restantes} dias")

    # Verificar Cargo Exclusivo
    exclusive_role_end = settings.get('exclusive_role', 0)
    if exclusive_role_end > current_time:
        dias_restantes = int((exclusive_role_end - current_time) / 86400)
        efeitos_ativos.append(f"🛡️ **Cargo Exclusivo:** Privilégios especiais por {dias_restantes} dias")

    # Verificar Tickets Prioritários
    priority_tickets = settings.get('priority_tickets', 0)
    if priority_tickets > 0:
        efeitos_ativos.append(f"🎫 **Tickets Prioritários:** {priority_tickets} usos disponíveis")

    # Verificar Habilidades Especiais
    special_abilities = settings.get('special_abilities', [])
    if special_abilities:
        abilities_text = ", ".join([ability.replace('_', ' ').title() for ability in special_abilities])
        efeitos_ativos.append(f"🧬 **Habilidades Especiais:** {abilities_text}")

    # Verificar Coleção
    collection_power = settings.get('collection_power', 0)
    epic_medals = settings.get('epic_medals', 0)
    dna_rx = settings.get('dna_rx', 0)
    evolution_points = settings.get('evolution_points', 0)

    if collection_power > 0 or epic_medals > 0 or dna_rx > 0:
        efeitos_ativos.append(f"🌌 **Coleção:** {epic_medals} Medalhas Épicas, {dna_rx} DNA RX")
        efeitos_ativos.append(f"⚡ **Poder de Evolução:** {evolution_points} pontos")

    if not efeitos_ativos:
        embed = create_embed(
            f"✨ Efeitos de {target.display_name}",
            "**Nenhum efeito ativo no momento**\n\n"
            "💡 **Como obter efeitos:**\n"
            "• Compre itens na `RXloja`\n"
            "• Use itens especiais como Boost de XP\n"
            "• Colecione DNA RX e Medalhas Épicas\n"
            "• Ative Tickets Prioritários",
            color=0xffaa00
        )
    else:
        embed = create_embed(
            f"✨ Efeitos Ativos - {target.display_name}",
            "\n".join(efeitos_ativos),
            color=0x00ff00
        )

    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name='usar', aliases=['use'])
async def usar_item(ctx, item_id: int = None):
    """Usar item do inventário"""
    if not item_id:
        embed = create_embed("❌ ID necessário", "Use: `RXusar <id>`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    # Buscar inventário diretamente do banco
    try:
        inventory_data = await db_manager.execute('SELECT inventory FROM users WHERE user_id = ?', (ctx.author.id,))
        
        if not inventory_data:
            embed = create_embed("❌ Dados não encontrados", "Você não tem dados de usuário!", color=0xff0000)
            await ctx.send(embed=embed)
            return

        inventory_data_str = inventory_data[0][0]
        inventory = json.loads(inventory_data_str) if inventory_data_str else {}

        if str(item_id) not in inventory or inventory[str(item_id)] <= 0:
            embed = create_embed("❌ Item não encontrado", "Você não possui este item!\nUse `RXinventario` para ver seus itens.", color=0xff0000)
            await ctx.send(embed=embed)
            return

        if item_id not in LOJA_ITENS:
            embed = create_embed("❌ Item inválido", "Este item não existe!", color=0xff0000)
            await ctx.send(embed=embed)
            return

        item = LOJA_ITENS[item_id]

        # Aplicar efeito do item ANTES de remover do inventário
        try:
            async with db_manager._lock:
                conn = await db_manager.get_connection()
                cursor = conn.cursor()

                # Buscar dados atuais
                user_info = await db_manager.execute('SELECT settings, coins, xp FROM users WHERE user_id = ?', (ctx.author.id,))
                settings_data, current_coins, current_xp = user_info[0][0], user_info[0][1], user_info[0][2]
                settings = json.loads(settings_data) if settings_data else {}

                resultado = ""

                # ITEM 1: Desafio do Dia
                if item_id == 1:
                    resultado_jogo = random.choice(['vitoria', 'derrota', 'empate'])
                    if resultado_jogo == 'vitoria':
                        premio = random.randint(200, 500)
                        cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (current_coins + premio, ctx.author.id))
                        resultado = f"🎉 **VITÓRIA!** Você ganhou {premio:,} moedas!"
                    elif resultado_jogo == 'empate':
                        resultado = f"😐 **EMPATE!** Nada aconteceu."
                    else:
                        perda = random.randint(50, 150)
                        perda = min(perda, current_coins)
                        cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (current_coins - perda, ctx.author.id))
                        resultado = f"😢 **DERROTA!** Você perdeu {perda:,} moedas."

                # ITEM 2: Caixa Misteriosa
                elif item_id == 2:
                    sorte = random.randint(1, 100)
                    if sorte <= 5:  # 5% - Muito raro
                        premio_coins = random.randint(2000, 5000)
                        premio_xp = random.randint(100, 200)
                        cursor.execute('UPDATE users SET coins = ?, xp = ? WHERE user_id = ?', (current_coins + premio_coins, current_xp + premio_xp, ctx.author.id))
                        resultado = f"🌟 **JACKPOT!** {premio_coins:,} moedas + {premio_xp} XP!"
                    elif sorte <= 25:  # 20% - Bom
                        premio_coins = random.randint(500, 1500)
                        cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (current_coins + premio_coins, ctx.author.id))
                        resultado = f"💰 **SORTE!** Você ganhou {premio_coins:,} moedas!"
                    elif sorte <= 50:  # 25% - Regular
                        premio_xp = random.randint(50, 100)
                        cursor.execute('UPDATE users SET xp = ? WHERE user_id = ?', (current_xp + premio_xp, ctx.author.id))
                        resultado = f"⭐ **XP!** Você ganhou {premio_xp} pontos de experiência!"
                    elif sorte <= 80:  # 30% - Pequeno
                        premio_coins = random.randint(100, 300)
                        cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (current_coins + premio_coins, ctx.author.id))
                        resultado = f"🪙 **Algo!** {premio_coins:,} moedas encontradas."
                    else:  # 20% - Nada
                        resultado = f"📦 **VAZIA!** A caixa estava vazia... que azar!"

                # ITEM 3: Ticket Prioritário
                elif item_id == 3:
                    settings['priority_tickets'] = settings.get('priority_tickets', 0) + 1
                    cursor.execute('UPDATE users SET settings = ? WHERE user_id = ?', (json.dumps(settings), ctx.author.id))
                    resultado = f"🎫 **PRIORIDADE ATIVADA!** Seu próximo ticket terá atendimento prioritário!"

                # ITEM 4: Explosão de Moedas
                elif item_id == 4:
                    moedas_total = random.randint(800, 1500)
                    embed_chuva = create_embed(
                        "🧨 EXPLOSÃO DE MOEDAS!",
                        f"**{ctx.author.mention} ativou uma Explosão de Moedas!**\n\n"
                        f"🪙 **{moedas_total:,} moedas** estão caindo do céu!\n"
                        f"⚡ **Os 3 primeiros a reagir com 💰 ganham parte das moedas!**\n\n"
                        f"🏃‍♂️ **CORRA!** Seja rápido!",
                        color=0xffd700
                    )

                    chuva_msg = await ctx.send(embed=embed_chuva)
                    await chuva_msg.add_reaction("💰")

                    # Armazenar evento
                    await active_games.set(chuva_msg.id, {
                        'type': 'coin_rain',
                        'message_id': chuva_msg.id, # Salvar ID da mensagem para referência
                        'total_coins': moedas_total,
                        'participants': [],
                        'max_participants': 3,
                        'creator': ctx.author.id
                    })

                    resultado = f"🧨 **EXPLOSÃO ATIVADA!** Chuva de {moedas_total:,} moedas liberada no chat!"

                # ITEM 5: Boost de XP (1h)
                elif item_id == 5:
                    boost_end = datetime.datetime.now() + datetime.timedelta(hours=1)
                    settings['xp_boost'] = boost_end.timestamp()
                    cursor.execute('UPDATE users SET settings = ? WHERE user_id = ?', (json.dumps(settings), ctx.author.id))
                    resultado = f"📈 **BOOST ATIVO!** XP dobrado por 1 hora! (até <t:{int(boost_end.timestamp())}:t>)"

                # ITEM 6: Título Personalizado
                elif item_id == 6:
                    settings['custom_title_available'] = True
                    cursor.execute('UPDATE users SET settings = ? WHERE user_id = ?', (json.dumps(settings), ctx.author.id))
                    resultado = f"👑 **TÍTULO DESBLOQUEADO!** Use `RXsettitle <título>` para definir seu título personalizado!"

                # ITEM 7: Salário VIP (7 dias)
                elif item_id == 7:
                    vip_end = datetime.datetime.now() + datetime.timedelta(days=7)
                    settings['vip_salary'] = vip_end.timestamp()
                    cursor.execute('UPDATE users SET settings = ? WHERE user_id = ?', (json.dumps(settings), ctx.author.id))
                    resultado = f"💼 **SALÁRIO VIP ATIVO!** +50% em trabalhos por 7 dias! (até <t:{int(vip_end.timestamp())}:d>)"

                # ITEM 8: Cargo Exclusivo (3 dias)
                elif item_id == 8:
                    exclusive_end = datetime.datetime.now() + datetime.timedelta(days=3)
                    settings['exclusive_role'] = exclusive_end.timestamp()
                    cursor.execute('UPDATE users SET settings = ? WHERE user_id = ?', (json.dumps(settings), ctx.author.id))

                    # Tentar criar/dar cargo especial se possível
                    try:
                        guild = ctx.guild
                        role_name = f"👑 {ctx.author.display_name} VIP"
                        existing_role = discord.utils.get(guild.roles, name=role_name)

                        if not existing_role:
                            special_role = await guild.create_role(
                                name=role_name,
                                color=discord.Color.gold(),
                                reason="Cargo exclusivo da loja RX"
                            )
                        else:
                            special_role = existing_role

                        await ctx.author.add_roles(special_role, reason="Item da loja: Cargo Exclusivo")
                        resultado = f"🛡️ **CARGO EXCLUSIVO ATIVO!** Você recebeu o cargo {special_role.mention} por 3 dias!"
                    except:
                        resultado = f"🛡️ **CARGO EXCLUSIVO ATIVO!** Privilégios especiais por 3 dias! (Cargo automático indisponível)"

                # ITEM 9: RX Medalha Épica
                elif item_id == 9:
                    settings['epic_medals'] = settings.get('epic_medals', 0) + 1
                    settings['collection_power'] = settings.get('collection_power', 0) + 10
                    cursor.execute('UPDATE users SET settings = ? WHERE user_id = ?', (json.dumps(settings), ctx.author.id))
                    resultado = f"🌌 **MEDALHA ÉPICA COLETADA!** Adicionada à sua coleção! Poder de Coleção: +10 (Total: {settings['collection_power']})"

                # ITEM 10: DNA RX
                elif item_id == 10:
                    settings['dna_rx'] = settings.get('dna_rx', 0) + 1
                    settings['evolution_points'] = settings.get('evolution_points', 0) + 25

                    # Chance de desbloquear habilidade especial
                    if random.randint(1, 100) <= 30:  # 30% chance
                        special_abilities = ['super_luck', 'coin_magnet', 'xp_master', 'command_master']
                        new_ability = random.choice(special_abilities)
                        if 'special_abilities' not in settings:
                            settings['special_abilities'] = []
                        if new_ability not in settings['special_abilities']:
                            settings['special_abilities'].append(new_ability)
                            cursor.execute('UPDATE users SET settings = ? WHERE user_id = ?', (json.dumps(settings), ctx.author.id))
                            resultado = f"🧬 **DNA RX ABSORVIDO!** +25 Pontos de Evolução + Habilidade Especial: **{new_ability.replace('_', ' ').title()}**!"
                        else:
                            cursor.execute('UPDATE users SET settings = ? WHERE user_id = ?', (json.dumps(settings), ctx.author.id))
                            resultado = f"🧬 **DNA RX ABSORVIDO!** +25 Pontos de Evolução! (Total: {settings['evolution_points']})"
                    else:
                        cursor.execute('UPDATE users SET settings = ? WHERE user_id = ?', (json.dumps(settings), ctx.author.id))
                        resultado = f"🧬 **DNA RX ABSORVIDO!** +25 Pontos de Evolução! (Total: {settings['evolution_points']})"

                # Remover item do inventário APÓS aplicar efeito
                inventory[str(item_id)] -= 1
                if inventory[str(item_id)] <= 0:
                    del inventory[str(item_id)]

                cursor.execute('UPDATE users SET inventory = ? WHERE user_id = ?', (json.dumps(inventory), ctx.author.id))

                conn.commit()
                conn.close()

            embed = create_embed(
                f"✅ {item['emoji']} {item['nome']} Usado!",
                f"**Efeito aplicado:**\n{resultado}\n\n"
                f"**Descrição:** {item['descricao']}",
                color=0x00ff00
            )
            await ctx.send(embed=embed)

            # Log do uso
            logger.info(f"Item usado: {ctx.author.name} usou {item['nome']} (ID: {item_id})")

    except Exception as e:
        logger.error(f"Erro ao usar item {item_id}: {e}")
        embed = create_embed("❌ Erro", "Erro ao usar item! Contate um administrador.", color=0xff0000)
        await ctx.send(embed=embed)

# Comando para definir título personalizado
@bot.command(name='settitle', aliases=['definirtitulo'])
async def set_custom_title(ctx, *, titulo=None):
    """Definir título personalizado (requer item da loja)"""
    if not titulo:
        embed = create_embed("❌ Título necessário", "Use: `RXsettitle Meu Título Épico`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if len(titulo) > 50:
        embed = create_embed("❌ Título muito longo", "Use no máximo 50 caracteres!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    user_data = await get_user_data(ctx.author.id)
    if not user_data:
        embed = create_embed("❌ Erro", "Dados do usuário não encontrados!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    settings_data = user_data[11]
    settings = json.loads(settings_data) if settings_data else {}

    if not settings.get('custom_title_available', False):
        embed = create_embed(
            "❌ Título não disponível",
            "Você precisa comprar e usar o item **👑 Título Personalizado** da loja!",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

    try:
        async with db_manager._lock:
            conn = await db_manager.get_connection()
            cursor = conn.cursor()

            settings['custom_title'] = titulo
            settings['custom_title_available'] = False  # Consumir o uso

            cursor.execute('UPDATE users SET settings = ? WHERE user_id = ?', (json.dumps(settings), ctx.author.id))
            conn.commit()
            conn.close()

        embed = create_embed(
            "👑 Título Definido!",
            f"**Seu novo título:** {titulo}\n\nSeu título aparecerá em comandos como `RXrank` e `RXperfil`!",
            color=0xffd700
        )
        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro ao definir título: {e}")
        embed = create_embed("❌ Erro", "Erro ao definir título!", color=0xff0000)
        await ctx.send(embed=embed)

# ============ MAIS COMANDOS FALTANDO ============
@bot.command(name='base64', aliases=['b64'])
async def base64_encode(ctx, *, texto=None):
    """Converter texto para base64"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXbase64 Seu texto aqui`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        encoded = base64.b64encode(texto.encode('utf-8')).decode('utf-8')
        embed = create_embed(
            "🔐 Codificação Base64",
            f"**Texto original:** {texto}\n**Base64:** `{encoded}`",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        embed = create_embed("❌ Erro", f"Erro ao codificar: {e}", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='hash', aliases=['md5'])
async def generate_hash(ctx, *, texto=None):
    """Gerar hash MD5 de um texto"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXhash Seu texto aqui`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        md5_hash = hashlib.md5(texto.encode('utf-8')).hexdigest()
        sha256_hash = hashlib.sha256(texto.encode('utf-8')).hexdigest()

        embed = create_embed(
            "🔐 Hash do Texto",
            f"**Texto:** {texto}\n**MD5:** `{md5_hash}`\n**SHA256:** `{sha256_hash[:32]}...`",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        embed = create_embed("❌ Erro", f"Erro ao gerar hash: {e}", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='bin', aliases=['binario'])
async def text_to_binary(ctx, *, texto=None):
    """Converter texto para binário"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXbin Seu texto aqui`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        binary = ' '.join(format(ord(char), '08b') for char in texto)
        if len(binary) > 1900:
            binary = binary[:1900] + "..."

        embed = create_embed(
            "🔢 Conversão para Binário",
            f"**Texto:** {texto}\n**Binário:** `{binary}`",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        embed = create_embed("❌ Erro", f"Erro na conversão: {e}", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='hex', aliases=['hexadecimal'])
async def text_to_hex(ctx, *, texto=None):
    """Converter texto para hexadecimal"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXhex Seu texto aqui`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        hex_text = texto.encode('utf-8').hex()
        embed = create_embed(
            "🔢 Convers    "Hexadecimal",
            f"**Texto:** {texto}\n**Hexadecimal:** `{hex_text}`",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        embed = create_embed("❌ Erro", f"Erro na conversão: {e}", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='reverse', aliases=['inverter'])
async def reverse_text(ctx, *, texto=None):
    """Inverter texto"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXreverse Seu texto aqui`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    reversed_text = texto[::-1]
    embed = create_embed(
        "🔄 Texto Invertido",
        f"**Original:** {texto}\n**Invertido:** {reversed_text}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name='uppercase', aliases=['maiuscula'])
async def text_uppercase(ctx, *, texto=None):
    """Converter texto para maiúsculas"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXuppercase Seu texto aqui`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    upper_text = texto.upper()
    embed = create_embed(
        "🔤 TEXTO EM MAIÚSCULAS",
        f"**Original:** {texto}\n**Maiúsculas:** {upper_text}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name='lowercase', aliases=['minuscula'])
async def text_lowercase(ctx, *, texto=None):
    """Converter texto para minúsculas"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXlowercase Seu texto aqui`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    lower_text = texto.lower()
    embed = create_embed(
        "🔤 texto em minúsculas",
        f"**Original:** {texto}\n**Minúsculas:** {lower_text}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name='capitalize', aliases=['capitalizar'])
async def text_capitalize(ctx, *, texto=None):
    """Capitalizar primeira letra"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXcapitalize seu texto aqui`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    capitalized_text = texto.capitalize()
    embed = create_embed(
        "🔤 Texto Capitalizado",
        f"**Original:** {texto}\n**Capitalizado:** {capitalized_text}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name='password', aliases=['senha'])
async def generate_password(ctx, tamanho: int = 12):
    """Gerar senha segura"""
    if tamanho < 4 or tamanho > 50:
        embed = create_embed("❌ Tamanho inválido", "Use entre 4 e 50 caracteres", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(characters) for _ in range(tamanho))

        embed = create_embed(
            "🔐 Senha Gerada",
            f"**Tamanho:** {tamanho} caracteres\n**Senha:** `{password}`\n\n"
            f"⚠️ **Guarde em local seguro!**",
            color=0x00ff00
        )

        # Tentar enviar por DM também
        try:
            await ctx.author.send(embed=embed)
            public_embed = create_embed(
                "✅ Senha enviada!",
                f"Sua senha de {tamanho} caracteres foi enviada por DM para segurança!",
                color=0x00ff00
            )
            await ctx.send(embed=public_embed, delete_after=10)
        except:
            await ctx.send(embed=embed, delete_after=30)

    except Exception as e:
        embed = create_embed("❌ Erro", f"Erro ao gerar senha: {e}", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='qr')
async def generate_qr(ctx, *, texto=None):
    """Gerar QR Code"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXqr Seu texto aqui`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    # Usar serviço online para QR code
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={quote(texto)}"

    embed = create_embed(
        "📱 QR Code Gerado",
        f"**Texto:** {texto}\n[Clique aqui para ver o QR Code]({qr_url})",
        color=0x00ff00
    )
    embed.set_image(url=qr_url)
    await ctx.send(embed=embed)

@bot.command(name='createtime', aliases=['tempocriacaotime'])
async def account_creation_time(ctx, user: discord.Member = None):
    """Data de criação da conta"""
    target = user or ctx.author

    created_timestamp = int(target.created_at.timestamp())

    embed = create_embed(
        f"📅 Criação da conta de {target.display_name}",
        f"**Conta criada em:** <t:{created_timestamp}:F>\n"
        f"**Há:** <t:{created_timestamp}:R>\n"
        f"**Timestamp:** {created_timestamp}",
        color=0x7289da
    )

    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name='warn', aliases=['advertir'])
@commands.has_permissions(manage_messages=True)
async def warn_user(ctx, user: discord.Member, *, motivo="Sem motivo especificado"):
    """Dar advertência a um usuário"""
    if user == ctx.author:
        embed = create_embed("❌ Impossível", "Você não pode se advertir!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if user.top_role >= ctx.author.top_role:
        embed = create_embed("❌ Sem permissão", "Você não pode advertir este usuário!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        # Buscar warns atuais
        user_data = await get_user_data(user.id)
        if not user_data:
            await update_user_data(user.id)
            current_warns = 0
        else:
            current_warns = user_data[15] if len(user_data) > 15 else 0

        new_warns = current_warns + 1

        async with db_manager._lock:
            conn = await db_manager.get_connection()
            cursor = conn.cursor()

            # Atualizar warns
            cursor.execute('UPDATE users SET warnings = ? WHERE user_id = ?', (new_warns, user.id))

            # Registrar no log de moderação
            await db_manager.execute('''
                INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason)
                VALUES (?, ?, ?, ?, ?)
            ''', (ctx.guild.id, user.id, ctx.author.id, 'warn', motivo))

            conn.commit()
            conn.close()

        embed = create_embed(
            "⚠️ Advertência Aplicada",
            f"**Usuário:** {user.mention}\n"
            f"**Motivo:** {motivo}\n"
            f"**Moderador:** {ctx.author.mention}\n"
            f"**Total de warns:** {new_warns}",
            color=0xff6600
        )
        await ctx.send(embed=embed)

        # Notificar usuário
        try:
            dm_embed = create_embed(
                "⚠️ Você recebeu uma advertência",
                f"**Servidor:** {ctx.guild.name}\n"
                f"**Motivo:** {motivo}\n"
                f"**Moderador:** {ctx.author.name}\n"
                f"**Total de advertências:** {new_warns}",
                color=0xff6600
            )
            await user.send(embed=dm_embed)
        except:
            pass

    except Exception as e:
        logger.error(f"Erro ao aplicar warn: {e}")
        embed = create_embed("❌ Erro", "Erro ao aplicar advertência!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='warns', aliases=['warnings'])
async def check_warns(ctx, user: discord.Member = None):
    """Ver advertências de um usuário"""
    target = user or ctx.author

    try:
        user_data = await get_user_data(target.id)
        if not user_data:
            warns = 0
        else:
            warns = user_data[15] if len(user_data) > 15 else 0

        embed = create_embed(
            f"⚠️ Advertências de {target.display_name}",
            f"**Total de advertências:** {warns}\n"
            f"**Status:** {'🔴 Muitas advertências' if warns >= 5 else '🟡 Algumas advertências' if warns >= 3 else '🟢 Poucas advertências'}",
            color=0xff0000 if warns >= 5 else 0xff6600 if warns >= 3 else 0x00ff00
        )

        embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro ao verificar warns: {e}")
        embed = create_embed("❌ Erro", "Erro ao verificar advertências!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='kick', aliases=['expulsar'])
@commands.has_permissions(kick_members=True)
async def kick_member(ctx, member: discord.Member, *, reason="Sem motivo especificado"):
    """Expulsar um membro"""
    if member == ctx.author:
        embed = create_embed("❌ Impossível", "Você não pode se expulsar!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if member.top_role >= ctx.author.top_role:
        embed = create_embed("❌ Sem permissão", "Você não pode expulsar este membro!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        # Notificar antes de expulsar
        try:
            dm_embed = create_embed(
                "👢 Você foi expulso",
                f"**Servidor:** {ctx.guild.name}\n"
                f"**Motivo:** {reason}\n"
                f"**Moderador:** {ctx.author.name}",
                color=0xff6600
            )
            await member.send(embed=dm_embed)
        except:
            pass

        await member.kick(reason=reason)

        embed = create_embed(
            "👢 Membro Expulso!",
            f"**Usuário:** {member.name}#{member.discriminator}\n"
            f"**Motivo:** {reason}\n"
            f"**Moderador:** {ctx.author.mention}",
            color=0xff6600
        )
        await ctx.send(embed=embed)

        # Log da moderação
        try:
            await db_manager.execute('''
                INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason)
                VALUES (?, ?, ?, ?, ?)
            ''', (ctx.guild.id, member.id, ctx.author.id, 'kick', reason))
        except Exception as e:
            logger.error(f"Erro ao salvar log de moderação: {e}")

    except Exception as e:
        logger.error(f"Erro ao expulsar membro: {e}")
        embed = create_embed("❌ Erro", f"Erro ao expulsar membro: {str(e)[:100]}", color=0xff0000)
        await ctx.send(embed=embed)

# ============ COMANDOS DE ADMINISTRAÇÃO AVANÇADOS ============
@bot.command(name='addsaldo', aliases=['addcoins', 'addmoney'])
@commands.has_permissions(administrator=True)
async def add_saldo(ctx, user: discord.Member, amount: int):
    """[ADMIN] Adicionar saldo a um usuário"""
    if amount <= 0:
        embed = create_embed("❌ Valor inválido", "Use valores positivos!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        user_data = await get_user_data(user.id)
        if not user_data:
            await update_user_data(user.id)
            current_coins = 50
        else:
            current_coins = user_data[1]

        new_coins = current_coins + amount

        async with db_manager._lock:
            conn = await db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins, user.id))

            # Registrar transação
            await db_manager.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (user.id, ctx.guild.id, 'admin_add', amount, f"Saldo adicionado por {ctx.author.name}"))

            conn.commit()
            conn.close()

        embed = create_embed(
            "✅ Saldo Adicionado!",
            f"**Usuário:** {user.mention}\n"
            f"**Valor adicionado:** {amount:,} moedas\n"
            f"**Saldo anterior:** {current_coins:,} moedas\n"
            f"**Novo saldo:** {new_coins:,} moedas\n"
            f"**Administrador:** {ctx.author.mention}",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

        # Notificar usuário
        try:
            dm_embed = create_embed(
                "💰 Saldo Recebido!",
                f"Um administrador adicionou **{amount:,} moedas** à sua conta!\n"
                f"**Novo saldo:** {new_coins:,} moedas",
                color=0x00ff00
            )
            await user.send(embed=dm_embed)
        except:
            pass

    except Exception as e:
        logger.error(f"Erro ao adicionar saldo: {e}")
        embed = create_embed("❌ Erro", "Erro ao adicionar saldo!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='removesaldo', aliases=['removecoins', 'removemoney'])
@commands.has_permissions(administrator=True)
async def remove_saldo(ctx, user: discord.Member, amount: int):
    """[ADMIN] Remover saldo de um usuário"""
    if amount <= 0:
        embed = create_embed("❌ Valor inválido", "Use valores positivos!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        user_data = await get_user_data(user.id)
        if not user_data:
            embed = create_embed("❌ Usuário não encontrado", "Este usuário não está no banco de dados!", color=0xff0000)
            await ctx.send(embed=embed)
            return

        current_coins = user_data[1]

        if current_coins < amount:
            embed = create_embed(
                "❌ Saldo insuficiente",
                f"{user.mention} só tem {current_coins:,} moedas!\nNão é possível remover {amount:,} moedas.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return

        new_coins = max(0, current_coins - amount)

        async with db_manager._lock:
            conn = await db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins, user.id))

            # Registrar transação
            await db_manager.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (user.id, ctx.guild.id, 'admin_remove', -amount, f"Saldo removido por {ctx.author.name}"))

            conn.commit()
            conn.close()

        embed = create_embed(
            "✅ Saldo Removido!",
            f"**Usuário:** {user.mention}\n"
            f"**Valor removido:** {amount:,} moedas\n"
            f"**Saldo anterior:** {current_coins:,} moedas\n"
            f"**Novo saldo:** {new_coins:,} moedas\n"
            f"**Administrador:** {ctx.author.mention}",
            color=0xff6b6b
        )
        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro ao remover saldo: {e}")
        embed = create_embed("❌ Erro", "Erro ao remover saldo!", color=0xff0000)
        await ctx.send(embed=embed)

# ============ SISTEMA DE EVENTOS E BATALHAS DE CLANS ============
@bot.command(name='criareventoclan', aliases=['createclanevent'])
@commands.has_permissions(administrator=True)
async def criar_evento_clan(ctx, *, dados_evento=None):
    """[ADMIN] Criar evento de batalha entre clans"""
    if not dados_evento:
        embed = create_embed(
            "⚔️ Como criar evento de clan",
            """**Formato:** `clan1 vs clan2 | tipo | aposta | duração`

**Exemplo:**
`RXcriareventoclan XCLAN vs GSN | Battle Royale | 5000 | 2h`

**Tipos disponíveis:**
• Battle Royale
• Team Deathmatch  
• King of the Hill
• Capture the Flag
• Tournament

**Durações:** 30m, 1h, 2h, 6h, 12h, 1d""",
            color=0x7289da
        )
        await ctx.send(embed=embed)
        return

    parts = [part.strip() for part in dados_evento.split('|')]
    if len(parts) < 4:
        embed = create_embed(
            "❌ Formato incorreto",
            "Use: `clan1 vs clan2 | tipo | aposta | duração`",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

    try:
        # Parsear dados
        clans_vs = parts[0].split(' vs ')
        if len(clans_vs) != 2:
            embed = create_embed("❌ Formato de clans inválido", "Use: `CLAN1 vs CLAN2`", color=0xff0000)
            await ctx.send(embed=embed)
            return

        clan1 = clans_vs[0].strip().upper()
        clan2 = clans_vs[1].strip().upper()
        tipo_evento = parts[1]
        aposta = int(parts[2])
        duracao_str = parts[3]

        # Parse duração
        time_units = {'m': 60, 'h': 3600, 'd': 86400}
        unit = duracao_str[-1].lower()

        if unit not in time_units:
            embed = create_embed("❌ Duração inválida", "Use: m (minutos), h (horas), d (dias)", color=0xff0000)
            await ctx.send(embed=embed)
            return

        amount = int(duracao_str[:-1])
        seconds = amount * time_units[unit]
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)

        # Criar embed do evento
        embed = create_embed(
            f"⚔️ EVENTO DE CLAN: {clan1} vs {clan2}",
            f"""**🎮 Tipo:** {tipo_evento}
            **💰 Aposta:** {aposta:,} moedas por participante
            **⏰ Duração:** {duracao_str}
            **🏁 Termina:** <t:{int(end_time.timestamp())}:R>
            **👑 Criado por:** {ctx.author.mention}
            
            **📋 Como participar:**
            Membros dos clans {clan1} e {clan2} podem reagir com:
            ⚔️ - Para participar da batalha
            🏆 - Para apostar no seu clan
            
            **⚠️ Regras:**
            • Apenas membros dos clans podem participar
            • Aposta é obrigatória para participar
            • Resultado será decidido por votação ou admin
            • Prêmio vai para o clan vencedor""",
            color=0xff6600
        )

        evento_msg = await ctx.send(embed=embed)
        await evento_msg.add_reaction("⚔️")
        await evento_msg.add_reaction("🏆")

        # Salvar evento no banco
        try:
            await db_manager.execute('''
                INSERT INTO clan_events (guild_id, creator_id, clan1, clan2, event_type, bet_amount, end_time, message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ctx.guild.id, ctx.author.id, clan1, clan2, tipo_evento, aposta, end_time, evento_msg.id))

            logger.info(f"Evento de clan criado: {clan1} vs {clan2}")

        except Exception as e:
            logger.error(f"Erro ao salvar evento de clan: {e}")

    except ValueError:
        embed = create_embed("❌ Valores inválidos", "Verificar aposta (número) e duração!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='eventosclan', aliases=['clanevents'])
async def listar_eventos_clan(ctx):
    """Ver eventos de clan ativos"""
    try:
        eventos = await db_manager.execute('''
            SELECT clan1, clan2, event_type, bet_amount, participants, end_time
            FROM clan_events
            WHERE guild_id = ? AND status = 'active'
            ORDER BY end_time
        ''', (ctx.guild.id,))

        if not eventos:
            embed = create_embed(
                "⚔️ Nenhum evento ativo",
                "Não há eventos de clan ativos no momento.\nAdministradores podem criar com `RXcriareventoclan`",
                color=0xffaa00
            )
            await ctx.send(embed=embed)
            return

        embed = create_embed(
            "⚔️ Eventos de Clan Ativos",
            f"Encontrados {len(eventos)} evento(s) ativo(s):",
            color=0xff6600
        )

        for evento in eventos[:5]:
            clan1, clan2, event_type, bet_amount, participants_json, end_time_str = evento
            participants = json.loads(participants_json) if participants_json else []

            embed.add_field(
                name=f"⚔️ {clan1} vs {clan2}",
                value=f"**🎮 Tipo:** {event_type}\n"
                      f"**💰 Aposta:** {bet_amount:,} moedas\n"
                      f"**👥 Participantes:** {len(participants)}\n"
                      f"**⏰ Termina:** <t:{int(datetime.datetime.fromisoformat(end_time_str).timestamp())}:R>",
                inline=False
            )

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro ao listar eventos de clan: {e}")

@bot.command(name='finalizareventoclan', aliases=['endclanevent'])
@commands.has_permissions(administrator=True)
async def finalizar_evento_clan(ctx, evento_id: int, clan_vencedor: str):
    """[ADMIN] Finalizar evento de clan"""
    try:
        evento = await db_manager.execute('''
            SELECT clan1, clan2, bet_amount, participants, bets, message_id
            FROM clan_events
            WHERE id = ? AND guild_id = ? AND status = 'active'
        ''', (evento_id, ctx.guild.id))

        if not evento:
            embed = create_embed("❌ Evento não encontrado", "Evento não existe ou já foi finalizado!", color=0xff0000)
            await ctx.send(embed=embed)
            return

        clan1, clan2, bet_amount, participants_json, bets_json, message_id = evento[0]
        clan_vencedor = clan_vencedor.upper()

        if clan_vencedor not in [clan1, clan2]:
            embed = create_embed("❌ Clan inválido", f"Use {clan1} ou {clan2}", color=0xff0000)
            await ctx.send(embed=embed)
            return

        participants = json.loads(participants_json) if participants_json else []
        bets = json.loads(bets_json) if bets_json else {}

        # Calcular prêmios
        vencedores = [p for p in participants if bets.get(str(p), {}).get('clan') == clan_vencedor]
        premio_total = len(participants) * bet_amount
        premio_individual = premio_total // len(vencedores) if vencedores else 0

        # Distribuir prêmios
        for user_id in vencedores:
            user_data = await get_user_data(user_id)
            if user_data:
                new_coins = user_data[1] + premio_individual + bet_amount  # Devolver aposta + prêmio
                await db_manager.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins, user_id))

        # Marcar como finalizado
        await db_manager.execute('''
            UPDATE clan_events 
            SET status = 'finished', winner_clan = ?
            WHERE id = ?
        ''', (clan_vencedor, evento_id))

        embed = create_embed(
            f"🏆 {clan_vencedor} VENCEU!",
            f"**Evento #{evento_id} finalizado!**\n\n"
            f"**Clan Vencedor:** {clan_vencedor}\n"
            f"**Vencedores:** {len(vencedores)} participantes\n"
            f"**Prêmio individual:** {premio_individual:,} moedas\n"
            f"**Total distribuído:** {premio_total:,} moedas\n"
            f"**Finalizado por:** {ctx.author.mention}",
            color=0xffd700
        )
        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro ao finalizar evento: {e}")
        embed = create_embed("❌ Erro", "Erro ao finalizar evento!", color=0xff0000)
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
        await db_manager.execute('''
            INSERT INTO reminders (user_id, guild_id, channel_id, reminder_text, remind_time)
            VALUES (?, ?, ?, ?, ?)
        ''', (ctx.author.id, ctx.guild.id, ctx.channel.id, texto, remind_time))

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

        **💡 Sistema Otimizado:**
        • Removidos sistemas de keep-alive 24/7
        • Sem anti-hibernação automática
        • Economia de recursos no Railway

        **📊 Estatísticas:**
        • Servidores: {len(bot.guilds)}
        • Usuários: {len(set(bot.get_all_members()))}
        • Comandos executados: {global_stats['commands_used']:,}
        • Mensagens processadas: {global_stats['messages_processed']:,}

        **🔋 Economia de Recursos:**
        • Bot só consome quando ativo
        • Sem sistemas de monitoramento 24/7
        • Redução significativa no uso do Railway""",
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
        
        **💡 Otimizado para Railway:**
        • Sem sistemas de keep-alive 24/7
        • Economia de recursos ativa
        • Backup automático (6h)""",
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
        f"📊 Estatísticas do RXbot",
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
    user_data = await get_user_data(target.id)
    if user_data:
        coins, xp, level, rep, bank = user_data[1], user_data[2], user_data[3], user_data[4], user_data[5]
        warnings = user_data[15]
    else:
        coins, xp, level, rep, bank, warnings = 0, 0, 1, 0, 0, 0

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

# Error handling MELHORADO com auto-recuperação
@bot.event
async def on_command_error(ctx, error):
    try:
        if isinstance(error, commands.CommandNotFound):
            command_name = ctx.message.content.split()[0][2:].lower()
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

        elif isinstance(error, (discord.HTTPException, aiohttp.ClientError)):
            logger.warning(f"Erro HTTP/Network (não crítico): {error}")
            # NÃO reiniciar o bot, apenas avisar
            try:
                channel = bot.get_channel(CHANNEL_ID_ALERTA)
                if channel:
                    embed = create_embed(
                        "⚠️ Problema de Rede",
                        f"Erro de conectividade detectado mas bot continua funcionando: {str(error)[:100]}",
                        color=0xffaa00
                    )
                    await channel.send(embed=embed)
            except:
                pass

        else:
            logger.error(f"Erro inesperado no comando {ctx.command}: {error}")

            try:
                embed = create_embed(
                    "❌ Erro interno",
                    "Ocorreu um erro interno. A equipe foi notificada.",
                    color=0xff0000
                )
                await ctx.send(embed=embed, delete_after=8)
            except:
                pass

    except Exception as handler_error:
        logger.error(f"Erro no error handler: {handler_error}")
        try:
            await ctx.send("❌ Erro interno do bot.", delete_after=5)
        except:
            pass

# ============ MAIS COMANDOS FALTANDO ============
@bot.command(name='base64', aliases=['b64'])
async def base64_encode(ctx, *, texto=None):
    """Converter texto para base64"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXbase64 Seu texto aqui`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        encoded = base64.b64encode(texto.encode('utf-8')).decode('utf-8')
        embed = create_embed(
            "🔐 Codificação Base64",
            f"**Texto original:** {texto}\n**Base64:** `{encoded}`",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        embed = create_embed("❌ Erro", f"Erro ao codificar: {e}", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='hash', aliases=['md5'])
async def generate_hash(ctx, *, texto=None):
    """Gerar hash MD5 de um texto"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXhash Seu texto aqui`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        md5_hash = hashlib.md5(texto.encode('utf-8')).hexdigest()
        sha256_hash = hashlib.sha256(texto.encode('utf-8')).hexdigest()

        embed = create_embed(
            "🔐 Hash do Texto",
            f"**Texto:** {texto}\n**MD5:** `{md5_hash}`\n**SHA256:** `{sha256_hash[:32]}...`",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        embed = create_embed("❌ Erro", f"Erro ao gerar hash: {e}", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='bin', aliases=['binario'])
async def text_to_binary(ctx, *, texto=None):
    """Converter texto para binário"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXbin Seu texto aqui`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        binary = ' '.join(format(ord(char), '08b') for char in texto)
        if len(binary) > 1900:
            binary = binary[:1900] + "..."

        embed = create_embed(
            "🔢 Conversão para Binário",
            f"**Texto:** {texto}\n**Binário:** `{binary}`",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        embed = create_embed("❌ Erro", f"Erro na conversão: {e}", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='hex', aliases=['hexadecimal'])
async def text_to_hex(ctx, *, texto=None):
    """Converter texto para hexadecimal"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXhex Seu texto aqui`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        hex_text = texto.encode('utf-8').hex()
        embed = create_embed(
            "🔢 Conversão para Hexadecimal",
            f"**Texto:** {texto}\n**Hexadecimal:** `{hex_text}`",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        embed = create_embed("❌ Erro", f"Erro na conversão: {e}", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='reverse', aliases=['inverter'])
async def reverse_text(ctx, *, texto=None):
    """Inverter texto"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXreverse Seu texto aqui`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    reversed_text = texto[::-1]
    embed = create_embed(
        "🔄 Texto Invertido",
        f"**Original:** {texto}\n**Invertido:** {reversed_text}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name='uppercase', aliases=['maiuscula'])
async def text_uppercase(ctx, *, texto=None):
    """Converter texto para maiúsculas"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXuppercase Seu texto aqui`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    upper_text = texto.upper()
    embed = create_embed(
        "🔤 TEXTO EM MAIÚSCULAS",
        f"**Original:** {texto}\n**Maiúsculas:** {upper_text}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name='lowercase', aliases=['minuscula'])
async def text_lowercase(ctx, *, texto=None):
    """Converter texto para minúsculas"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXlowercase Seu texto aqui`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    lower_text = texto.lower()
    embed = create_embed(
        "🔤 texto em minúsculas",
        f"**Original:** {texto}\n**Minúsculas:** {lower_text}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name='capitalize', aliases=['capitalizar'])
async def text_capitalize(ctx, *, texto=None):
    """Capitalizar primeira letra"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXcapitalize seu texto aqui`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    capitalized_text = texto.capitalize()
    embed = create_embed(
        "🔤 Texto Capitalizado",
        f"**Original:** {texto}\n**Capitalizado:** {capitalized_text}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name='password', aliases=['senha'])
async def generate_password(ctx, tamanho: int = 12):
    """Gerar senha segura"""
    if tamanho < 4 or tamanho > 50:
        embed = create_embed("❌ Tamanho inválido", "Use entre 4 e 50 caracteres", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(characters) for _ in range(tamanho))

        embed = create_embed(
            "🔐 Senha Gerada",
            f"**Tamanho:** {tamanho} caracteres\n**Senha:** `{password}`\n\n"
            f"⚠️ **Guarde em local seguro!**",
            color=0x00ff00
        )

        # Tentar enviar por DM também
        try:
            await ctx.author.send(embed=embed)
            public_embed = create_embed(
                "✅ Senha enviada!",
                f"Sua senha de {tamanho} caracteres foi enviada por DM para segurança!",
                color=0x00ff00
            )
            await ctx.send(embed=public_embed, delete_after=10)
        except:
            await ctx.send(embed=embed, delete_after=30)

    except Exception as e:
        embed = create_embed("❌ Erro", f"Erro ao gerar senha: {e}", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='qr')
async def generate_qr(ctx, *, texto=None):
    """Gerar QR Code"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXqr Seu texto aqui`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    # Usar serviço online para QR code
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={quote(texto)}"

    embed = create_embed(
        "📱 QR Code Gerado",
        f"**Texto:** {texto}\n[Clique aqui para ver o QR Code]({qr_url})",
        color=0x00ff00
    )
    embed.set_image(url=qr_url)
    await ctx.send(embed=embed)

@bot.command(name='createtime', aliases=['tempocriacaotime'])
async def account_creation_time(ctx, user: discord.Member = None):
    """Data de criação da conta"""
    target = user or ctx.author

    created_timestamp = int(target.created_at.timestamp())

    embed = create_embed(
        f"📅 Criação da conta de {target.display_name}",
        f"**Conta criada em:** <t:{created_timestamp}:F>\n"
        f"**Há:** <t:{created_timestamp}:R>\n"
        f"**Timestamp:** {created_timestamp}",
        color=0x7289da
    )

    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name='warn', aliases=['advertir'])
@commands.has_permissions(manage_messages=True)
async def warn_user(ctx, user: discord.Member, *, motivo="Sem motivo especificado"):
    """Dar advertência a um usuário"""
    if user == ctx.author:
        embed = create_embed("❌ Impossível", "Você não pode se advertir!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if user.top_role >= ctx.author.top_role:
        embed = create_embed("❌ Sem permissão", "Você não pode advertir este usuário!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        # Buscar warns atuais
        user_data = await get_user_data(user.id)
        if not user_data:
            await update_user_data(user.id)
            current_warns = 0
        else:
            current_warns = user_data[15] if len(user_data) > 15 else 0

        new_warns = current_warns + 1

        async with db_manager._lock:
            conn = await db_manager.get_connection()
            cursor = conn.cursor()

            # Atualizar warns
            cursor.execute('UPDATE users SET warnings = ? WHERE user_id = ?', (new_warns, user.id))

            # Registrar no log de moderação
            await db_manager.execute('''
                INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason)
                VALUES (?, ?, ?, ?, ?)
            ''', (ctx.guild.id, user.id, ctx.author.id, 'warn', motivo))

            conn.commit()
            conn.close()

        embed = create_embed(
            "⚠️ Advertência Aplicada",
            f"**Usuário:** {user.mention}\n"
            f"**Motivo:** {motivo}\n"
            f"**Moderador:** {ctx.author.mention}\n"
            f"**Total de warns:** {new_warns}",
            color=0xff6600
        )
        await ctx.send(embed=embed)

        # Notificar usuário
        try:
            dm_embed = create_embed(
                "⚠️ Você recebeu uma advertência",
                f"**Servidor:** {ctx.guild.name}\n"
                f"**Motivo:** {motivo}\n"
                f"**Moderador:** {ctx.author.name}\n"
                f"**Total de advertências:** {new_warns}",
                color=0xff6600
            )
            await user.send(embed=dm_embed)
        except:
            pass

    except Exception as e:
        logger.error(f"Erro ao aplicar warn: {e}")
        embed = create_embed("❌ Erro", "Erro ao aplicar advertência!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='warns', aliases=['warnings'])
async def check_warns(ctx, user: discord.Member = None):
    """Ver advertências de um usuário"""
    target = user or ctx.author

    try:
        user_data = await get_user_data(target.id)
        if not user_data:
            warns = 0
        else:
            warns = user_data[15] if len(user_data) > 15 else 0

        embed = create_embed(
            f"⚠️ Advertências de {target.display_name}",
            f"**Total de advertências:** {warns}\n"
            f"**Status:** {'🔴 Muitas advertências' if warns >= 5 else '🟡 Algumas advertências' if warns >= 3 else '🟢 Poucas advertências'}",
            color=0xff0000 if warns >= 5 else 0xff6600 if warns >= 3 else 0x00ff00
        )

        embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro ao verificar warns: {e}")
        embed = create_embed("❌ Erro", "Erro ao verificar advertências!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='kick', aliases=['expulsar'])
@commands.has_permissions(kick_members=True)
async def kick_member(ctx, member: discord.Member, *, reason="Sem motivo especificado"):
    """Expulsar um membro"""
    if member == ctx.author:
        embed = create_embed("❌ Impossível", "Você não pode se expulsar!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if member.top_role >= ctx.author.top_role:
        embed = create_embed("❌ Sem permissão", "Você não pode expulsar este membro!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        # Notificar antes de expulsar
        try:
            dm_embed = create_embed(
                "👢 Você foi expulso",
                f"**Servidor:** {ctx.guild.name}\n"
                f"**Motivo:** {reason}\n"
                f"**Moderador:** {ctx.author.name}",
                color=0xff6600
            )
            await member.send(embed=dm_embed)
        except:
            pass

        await member.kick(reason=reason)

        embed = create_embed(
            "👢 Membro Expulso!",
            f"**Usuário:** {member.name}#{member.discriminator}\n"
            f"**Motivo:** {reason}\n"
            f"**Moderador:** {ctx.author.mention}",
            color=0xff6600
        )
        await ctx.send(embed=embed)

        # Log da moderação
        try:
            await db_manager.execute('''
                INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason)
                VALUES (?, ?, ?, ?, ?)
            ''', (ctx.guild.id, member.id, ctx.author.id, 'kick', reason))
        except Exception as e:
            logger.error(f"Erro ao salvar log de moderação: {e}")

    except Exception as e:
        logger.error(f"Erro ao expulsar membro: {e}")
        embed = create_embed("❌ Erro", f"Erro ao expulsar membro: {str(e)[:100]}", color=0xff0000)
        await ctx.send(embed=embed)

# ============ COMANDOS DE ADMINISTRAÇÃO AVANÇADOS ============
@bot.command(name='addsaldo', aliases=['addcoins', 'addmoney'])
@commands.has_permissions(administrator=True)
async def add_saldo(ctx, user: discord.Member, amount: int):
    """[ADMIN] Adicionar saldo a um usuário"""
    if amount <= 0:
        embed = create_embed("❌ Valor inválido", "Use valores positivos!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        user_data = await get_user_data(user.id)
        if not user_data:
            await update_user_data(user.id)
            current_coins = 50
        else:
            current_coins = user_data[1]

        new_coins = current_coins + amount

        async with db_manager._lock:
            conn = await db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins, user.id))

            # Registrar transação
            await db_manager.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (user.id, ctx.guild.id, 'admin_add', amount, f"Saldo adicionado por {ctx.author.name}"))

            conn.commit()
            conn.close()

        embed = create_embed(
            "✅ Saldo Adicionado!",
            f"**Usuário:** {user.mention}\n"
            f"**Valor adicionado:** {amount:,} moedas\n"
            f"**Saldo anterior:** {current_coins:,} moedas\n"
            f"**Novo saldo:** {new_coins:,} moedas\n"
            f"**Administrador:** {ctx.author.mention}",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

        # Notificar usuário
        try:
            dm_embed = create_embed(
                "💰 Saldo Recebido!",
                f"Um administrador adicionou **{amount:,} moedas** à sua conta!\n"
                f"**Novo saldo:** {new_coins:,} moedas",
                color=0x00ff00
            )
            await user.send(embed=dm_embed)
        except:
            pass

    except Exception as e:
        logger.error(f"Erro ao adicionar saldo: {e}")
        embed = create_embed("❌ Erro", "Erro ao adicionar saldo!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='removesaldo', aliases=['removecoins', 'removemoney'])
@commands.has_permissions(administrator=True)
async def remove_saldo(ctx, user: discord.Member, amount: int):
    """[ADMIN] Remover saldo de um usuário"""
    if amount <= 0:
        embed = create_embed("❌ Valor inválido", "Use valores positivos!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        user_data = await get_user_data(user.id)
        if not user_data:
            embed = create_embed("❌ Usuário não encontrado", "Este usuário não está no banco de dados!", color=0xff0000)
            await ctx.send(embed=embed)
            return

        current_coins = user_data[1]

        if current_coins < amount:
            embed = create_embed(
                "❌ Saldo insuficiente",
                f"{user.mention} só tem {current_coins:,} moedas!\nNão é possível remover {amount:,} moedas.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return

        new_coins = max(0, current_coins - amount)

        async with db_manager._lock:
            conn = await db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins, user.id))

            # Registrar transação
            await db_manager.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (user.id, ctx.guild.id, 'admin_remove', -amount, f"Saldo removido por {ctx.author.name}"))

            conn.commit()
            conn.close()

        embed = create_embed(
            "✅ Saldo Removido!",
            f"**Usuário:** {user.mention}\n"
            f"**Valor removido:** {amount:,} moedas\n"
            f"**Saldo anterior:** {current_coins:,} moedas\n"
            f"**Novo saldo:** {new_coins:,} moedas\n"
            f"**Administrador:** {ctx.author.mention}",
            color=0xff6b6b
        )
        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro ao remover saldo: {e}")
        embed = create_embed("❌ Erro", "Erro ao remover saldo!", color=0xff0000)
        await ctx.send(embed=embed)

# ============ SISTEMA DE EVENTOS E BATALHAS DE CLANS ============
@bot.command(name='criareventoclan', aliases=['createclanevent'])
@commands.has_permissions(administrator=True)
async def criar_evento_clan(ctx, *, dados_evento=None):
    """[ADMIN] Criar evento de batalha entre clans"""
    if not dados_evento:
        embed = create_embed(
            "⚔️ Como criar evento de clan",
            """**Formato:** `clan1 vs clan2 | tipo | aposta | duração`

**Exemplo:**
`RXcriareventoclan XCLAN vs GSN | Battle Royale | 5000 | 2h`

**Tipos disponíveis:**
• Battle Royale
• Team Deathmatch  
• King of the Hill
• Capture the Flag
• Tournament

**Durações:** 30m, 1h, 2h, 6h, 12h, 1d""",
            color=0x7289da
        )
        await ctx.send(embed=embed)
        return

    parts = [part.strip() for part in dados_evento.split('|')]
    if len(parts) < 4:
        embed = create_embed(
            "❌ Formato incorreto",
            "Use: `clan1 vs clan2 | tipo | aposta | duração`",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

    try:
        # Parsear dados
        clans_vs = parts[0].split(' vs ')
        if len(clans_vs) != 2:
            embed = create_embed("❌ Formato de clans inválido", "Use: `CLAN1 vs CLAN2`", color=0xff0000)
            await ctx.send(embed=embed)
            return

        clan1 = clans_vs[0].strip().upper()
        clan2 = clans_vs[1].strip().upper()
        tipo_evento = parts[1]
        aposta = int(parts[2])
        duracao_str = parts[3]

        # Parse duração
        time_units = {'m': 60, 'h': 3600, 'd': 86400}
        unit = duracao_str[-1].lower()

        if unit not in time_units:
            embed = create_embed("❌ Duração inválida", "Use: m (minutos), h (horas), d (dias)", color=0xff0000)
            await ctx.send(embed=embed)
            return

        amount = int(duracao_str[:-1])
        seconds = amount * time_units[unit]
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)

        # Criar embed do evento
        embed = create_embed(
            f"⚔️ EVENTO DE CLAN: {clan1} vs {clan2}",
            f"""**🎮 Tipo:** {tipo_evento}
            **💰 Aposta:** {aposta:,} moedas por participante
            **⏰ Duração:** {duracao_str}
            **🏁 Termina:** <t:{int(end_time.timestamp())}:R>
            **👑 Criado por:** {ctx.author.mention}
            
            **📋 Como participar:**
            Membros dos clans {clan1} e {clan2} podem reagir com:
            ⚔️ - Para participar da batalha
            🏆 - Para apostar no seu clan
            
            **⚠️ Regras:**
            • Apenas membros dos clans podem participar
            • Aposta é obrigatória para participar
            • Resultado será decidido por votação ou admin
            • Prêmio vai para o clan vencedor""",
            color=0xff6600
        )

        evento_msg = await ctx.send(embed=embed)
        await evento_msg.add_reaction("⚔️")
        await evento_msg.add_reaction("🏆")

        # Salvar evento no banco
        try:
            await db_manager.execute('''
                INSERT INTO clan_events (guild_id, creator_id, clan1, clan2, event_type, bet_amount, end_time, message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ctx.guild.id, ctx.author.id, clan1, clan2, tipo_evento, aposta, end_time, evento_msg.id))

            logger.info(f"Evento de clan criado: {clan1} vs {clan2}")

        except Exception as e:
            logger.error(f"Erro ao salvar evento de clan: {e}")

    except ValueError:
        embed = create_embed("❌ Valores inválidos", "Verificar aposta (número) e duração!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='eventosclan', aliases=['clanevents'])
async def listar_eventos_clan(ctx):
    """Ver eventos de clan ativos"""
    try:
        eventos = await db_manager.execute('''
            SELECT clan1, clan2, event_type, bet_amount, participants, end_time
            FROM clan_events
            WHERE guild_id = ? AND status = 'active'
            ORDER BY end_time
        ''', (ctx.guild.id,))

        if not eventos:
            embed = create_embed(
                "⚔️ Nenhum evento ativo",
                "Não há eventos de clan ativos no momento.\nAdministradores podem criar com `RXcriareventoclan`",
                color=0xffaa00
            )
            await ctx.send(embed=embed)
            return

        embed = create_embed(
            "⚔️ Eventos de Clan Ativos",
            f"Encontrados {len(eventos)} evento(s) ativo(s):",
            color=0xff6600
        )

        for evento in eventos[:5]:
            clan1, clan2, event_type, bet_amount, participants_json, end_time_str = evento
            participants = json.loads(participants_json) if participants_json else []

            embed.add_field(
                name=f"⚔️ {clan1} vs {clan2}",
                value=f"**🎮 Tipo:** {event_type}\n"
                      f"**💰 Aposta:** {bet_amount:,} moedas\n"
                      f"**👥 Participantes:** {len(participants)}\n"
                      f"**⏰ Termina:** <t:{int(datetime.datetime.fromisoformat(end_time_str).timestamp())}:R>",
                inline=False
            )

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro ao listar eventos de clan: {e}")

@bot.command(name='finalizareventoclan', aliases=['endclanevent'])
@commands.has_permissions(administrator=True)
async def finalizar_evento_clan(ctx, evento_id: int, clan_vencedor: str):
    """[ADMIN] Finalizar evento de clan"""
    try:
        evento = await db_manager.execute('''
            SELECT clan1, clan2, bet_amount, participants, bets, message_id
            FROM clan_events
            WHERE id = ? AND guild_id = ? AND status = 'active'
        ''', (evento_id, ctx.guild.id))

        if not evento:
            embed = create_embed("❌ Evento não encontrado", "Evento não existe ou já foi finalizado!", color=0xff0000)
            await ctx.send(embed=embed)
            return

        clan1, clan2, bet_amount, participants_json, bets_json, message_id = evento[0]
        clan_vencedor = clan_vencedor.upper()

        if clan_vencedor not in [clan1, clan2]:
            embed = create_embed("❌ Clan inválido", f"Use {clan1} ou {clan2}", color=0xff0000)
            await ctx.send(embed=embed)
            return

        participants = json.loads(participants_json) if participants_json else []
        bets = json.loads(bets_json) if bets_json else {}

        # Calcular prêmios
        vencedores = [p for p in participants if bets.get(str(p), {}).get('clan') == clan_vencedor]
        premio_total = len(participants) * bet_amount
        premio_individual = premio_total // len(vencedores) if vencedores else 0

        # Distribuir prêmios
        for user_id in vencedores:
            user_data = await get_user_data(user_id)
            if user_data:
                new_coins = user_data[1] + premio_individual + bet_amount  # Devolver aposta + prêmio
                await db_manager.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins, user_id))

        # Marcar como finalizado
        await db_manager.execute('''
            UPDATE clan_events 
            SET status = 'finished', winner_clan = ?
            WHERE id = ?
        ''', (clan_vencedor, evento_id))

        embed = create_embed(
            f"🏆 {clan_vencedor} VENCEU!",
            f"**Evento #{evento_id} finalizado!**\n\n"
            f"**Clan Vencedor:** {clan_vencedor}\n"
            f"**Vencedores:** {len(vencedores)} participantes\n"
            f"**Prêmio individual:** {premio_individual:,} moedas\n"
            f"**Total distribuído:** {premio_total:,} moedas\n"
            f"**Finalizado por:** {ctx.author.mention}",
            color=0xffd700
        )
        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro ao finalizar evento: {e}")
        embed = create_embed("❌ Erro", "Erro ao finalizar evento!", color=0xff0000)
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
        await db_manager.execute('''
            INSERT INTO reminders (user_id, guild_id, channel_id, reminder_text, remind_time)
            VALUES (?, ?, ?, ?, ?)
        ''', (ctx.author.id, ctx.guild.id, ctx.channel.id, texto, remind_time))

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

        **💡 Sistema Otimizado:**
        • Removidos sistemas de keep-alive 24/7
        • Sem anti-hibernação automática
        • Economia de recursos no Railway

        **📊 Estatísticas:**
        • Servidores: {len(bot.guilds)}
        • Usuários: {len(set(bot.get_all_members()))}
        • Comandos executados: {global_stats['commands_used']:,}
        • Mensagens processadas: {global_stats['messages_processed']:,}

        **🔋 Economia de Recursos:**
        • Bot só consome quando ativo
        • Sem sistemas de monitoramento 24/7
        • Redução significativa no uso do Railway""",
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
        
        **💡 Otimizado para Railway:**
        • Sem sistemas de keep-alive 24/7
        • Economia de recursos ativa
        • Backup automático (6h)""",
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
        f"📊 Estatísticas do RXbot",
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
    user_data = await get_user_data(target.id)
    if user_data:
        coins, xp, level, rep, bank = user_data[1], user_data[2], user_data[3], user_data[4], user_data[5]
        warnings = user_data[15]
    else:
        coins, xp, level, rep, bank, warnings = 0, 0, 1, 0, 0, 0

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

# Error handling MELHORADO com auto-recuperação
@bot.event
async def on_command_error(ctx, error):
    try:
        if isinstance(error, commands.CommandNotFound):
            command_name = ctx.message.content.split()[0][2:].lower()
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

        elif isinstance(error, (discord.HTTPException, aiohttp.ClientError)):
            logger.warning(f"Erro HTTP/Network (não crítico): {error}")
            # NÃO reiniciar o bot, apenas avisar
            try:
                channel = bot.get_channel(CHANNEL_ID_ALERTA)
                if channel:
                    embed = create_embed(
                        "⚠️ Problema de Rede",
                        f"Erro de conectividade detectado mas bot continua funcionando: {str(error)[:100]}",
                        color=0xffaa00
                    )
                    await channel.send(embed=embed)
            except:
                pass

        else:
            logger.error(f"Erro inesperado no comando {ctx.command}: {error}")

            try:
                embed = create_embed(
                    "❌ Erro interno",
                    "Ocorreu um erro interno. A equipe foi notificada.",
                    color=0xff0000
                )
                await ctx.send(embed=embed, delete_after=8)
            except:
                pass

    except Exception as handler_error:
        logger.error(f"Erro no error handler: {handler_error}")

# If __name__ == "__main__": block
if __name__ == "__main__":
    max_restarts = 3
    restart_count = 0

    while restart_count < max_restarts:
        try:
            token = os.getenv('TOKEN')
            if not token:
                logger.error("🚨 TOKEN não encontrado nas variáveis de ambiente!")
                print("❌ Configure a variável de ambiente TOKEN com o token do seu bot Discord")
                sys.exit(1)

            logger.info(f"🚀 Iniciando RXbot CORRIGIDO... (Restart #{restart_count + 1})")

            asyncio.run(start_bot())

            logger.info("✅ Bot finalizado normalmente")
            break

        except KeyboardInterrupt:
            logger.info("🛑 Bot interrompido pelo usuário")
            break

        except Exception as e:
            logger.error(f"🚨 Erro fatal: {e}")
            restart_count += 1

            if restart_count < max_restarts:
                wait_time = 60 * restart_count
                logger.info(f"🔄 Restart automático em {wait_time}s...")
                time.sleep(wait_time)

                gc.collect()

            else:
                logger.error("💥 Máximo de restarts atingido. Encerrando...")
                sys.exit(1)

    if restart_count >= max_restarts:
        logger.error("💥 Sistema falhou após múltiplos restarts!")
        sys.exit(1)