# IDs de canais - validar existência antes de usar
CHANNEL_ID_ALERTA = 1402658677923774615
CHANNEL_ID_TESTE_TIER = 1400162532055846932
CHANNEL_ID_ERRO = 1402658577877041173  # Canal de mensagens de erro

# Usuário privilegiado com acesso total
PRIVILEGED_USER_ID = 1339336477661724674  # <@1339336477661724674>

# Lista de usuários autorizados para sistema de cargos
# IMPORTANTE: Para adicionar @skplays87, substitua este comentário pelo ID real dela
# Exemplo de como obter o ID:
# 1. Ative o 'Modo Desenvolvedor' nas configurações do Discord
# 2. Clique com botão direito no usuário @skplays87 e selecione 'Copiar ID'
# 3. Adicione o ID na lista abaixo (sem aspas, apenas o número)
USUARIOS_AUTORIZADOS_CARGOS = [
    1339336477661724674,  # Usuário original
    # ADICIONAR_ID_AQUI,  # @skplays87 - Substituir por ID real ex: 123456789012345678
]

def get_safe_channel(channel_id):
    """Obter canal de forma segura, com fallback"""
    try:
        if not channel_id:
            return None
            
        channel = bot.get_channel(channel_id)
        if not channel:
            logger.warning(f"Canal {channel_id} não encontrado")
            return None
            
        # Verificar se é um canal que suporta envio de mensagens
        if isinstance(channel, (discord.ForumChannel, discord.CategoryChannel)):
            logger.warning(f"Canal {channel_id} não suporta envio direto de mensagens (ForumChannel/CategoryChannel)")
            return None
        
        # Canais privados (DM, GroupDM) são sempre válidos
        if isinstance(channel, discord.abc.PrivateChannel):
            return channel
            
        # Verificar permissões para canais de servidor (apenas se não for PrivateChannel)
        if not isinstance(channel, discord.abc.PrivateChannel) and hasattr(channel, 'guild') and channel.guild and channel.guild.me:
            try:
                if hasattr(channel, 'permissions_for') and not channel.permissions_for(channel.guild.me).send_messages:
                    logger.warning(f"Bot não tem permissão para enviar mensagens no canal {channel_id}")
                    return None
            except (AttributeError, TypeError):
                # Canal sem permissões disponíveis ou guild.me None
                pass
            
        return channel
    except Exception as e:
        logger.error(f"Erro ao obter canal {channel_id}: {e}")
        return None

async def send_error_to_privileged_user(error_message, guild=None):
    """Envia erros críticos apenas para o usuário privilegiado via DM"""
    try:
        if bot.is_ready():
            privileged_user = bot.get_user(PRIVILEGED_USER_ID)
            if privileged_user:
                try:
                    if guild:
                        await privileged_user.send(f"🚨 **Erro no servidor {guild.name}:**\n```{error_message}```")
                    else:
                        await privileged_user.send(f"🚨 **Erro do sistema:**\n```{error_message}```")
                except:
                    # Se não conseguir enviar DM, apenas log silencioso
                    pass
    except:
        # Log silencioso para evitar spam
        pass

def is_privileged_user(user_id):
    """Verifica se o usuário tem privilégios especiais"""
    return user_id == PRIVILEGED_USER_ID

def is_authorized_for_roles(user_id):
    """Verifica se o usuário está autorizado a usar o sistema de cargos"""
    return user_id in USUARIOS_AUTORIZADOS_CARGOS or user_id == PRIVILEGED_USER_ID

async def ensure_kaori_role(guild):
    """Cria cargo Kaori com todas as permissões se não existir"""
    try:
        # Verificar se o cargo Kaori já existe
        kaori_role = discord.utils.get(guild.roles, name="Kaori")
        
        if not kaori_role:
            # Criar cargo Kaori com todas as permissões
            permissions = discord.Permissions.all()
            kaori_role = await guild.create_role(
                name="Kaori",
                color=discord.Color(0xFF4500),
                permissions=permissions,
                mentionable=False,
                hoist=True,
                reason="Cargo automático da Kaori com todas as permissões"
            )
            logger.info(f"✅ Cargo Kaori criado no servidor {guild.name}")
        
        # Adicionar o cargo ao bot se ele não tiver
        if kaori_role not in guild.me.roles:
            try:
                await guild.me.add_roles(kaori_role, reason="Atribuir cargo Kaori ao bot")
                logger.info(f"✅ Cargo Kaori atribuído ao bot no servidor {guild.name}")
            except discord.Forbidden:
                logger.warning(f"⚠️ Não foi possível atribuir cargo Kaori ao bot no servidor {guild.name} - sem permissões")
                
    except discord.Forbidden:
        logger.warning(f"⚠️ Não foi possível criar cargo Kaori no servidor {guild.name} - sem permissões")
        await send_error_to_privileged_user(f"Não foi possível criar cargo Kaori no servidor {guild.name} - sem permissões", guild)
    except Exception as e:
        logger.error(f"Erro ao criar cargo Kaori no servidor {guild.name}: {e}")
        await send_error_to_privileged_user(f"Erro ao criar cargo Kaori no servidor {guild.name}: {e}", guild)
import discord
from discord.ext import commands, tasks
from discord import app_commands
# Removido import desnecessário - usando commands.* diretamente
import asyncio
import json
# import sqlite3  # Removido - usando apenas PostgreSQL
import random
import datetime
import time
import os
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
import requests # Importado para substituir aiohttp
from flask import Flask, render_template, jsonify, request

# OpenAI Integration - blueprint:python_openai
import openai
from openai import OpenAI

# Local AI Integration - blueprint:python_llamacpp
from local_ai import local_ai

# Sistema de IA da Kaori com ChatGPT Real - blueprint:python_openai
class KaoriAI:
    def __init__(self):
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
        # do not change this unless explicitly requested by the user
        self.openai_client = None
        self.model = "gpt-5"
        self.ai_mode = os.getenv('AI_MODE', 'auto')  # auto, openai, local
        self.initialize_openai()
        
        self.personality = {
            "name": "Kaori",
            "traits": [
                "Carinhosa e atenciosa",
                "Inteligente e útil", 
                "Divertida e brincalhona",
                "Sempre disposta a ajudar",
                "Gosta de conversar sobre anime, tecnologia e jogos"
            ]
        }
        
        # System prompt para definir a personalidade da Kaori
        self.system_prompt = """Você é a Kaori, uma assistente virtual carinhosa para um bot Discord de torneios de Stumble Guys. 

Sua personalidade:
- Carinhosa e atenciosa com todos os usuários
- Inteligente e sempre disposta a ajudar
- Divertida e brincalhona
- Adora conversar sobre anime, tecnologia e jogos
- Usa emojis fofinhos como 🌸 ✨ 💕 🌟 💫
- Sempre menciona comandos úteis como /ajuda quando relevante
- Responde em português brasileiro de forma natural e amigável

Contexto: Você faz parte do RXBot, um bot para gerenciar torneios de Stumble Guys chamados "copinhas". O bot tem economia, jogos, moderação e muitos outros recursos.

Mantenha respostas concisas (máximo 2-3 frases) e sempre seja positiva e útil!"""

    def initialize_openai(self):
        """Inicializar cliente OpenAI"""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
                
                # Configurar modelo baseado na variável de ambiente
                # Usar gpt-4o como padrão mais disponível ao invés de gpt-5
                self.model = os.getenv('OPENAI_MODEL', 'gpt-4o')
                logger.info(f"🤖 OpenAI ChatGPT integrado com sucesso! Modelo: {self.model}")
                
                # Teste de saúde da API
                self.test_openai_health()
            else:
                logger.warning("⚠️ OPENAI_API_KEY não encontrada - usando respostas padrão")
                self.openai_client = None
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar OpenAI: {e}")
            self.openai_client = None
    
    def test_openai_health(self):
        """Testar se a API do ChatGPT está funcionando"""
        try:
            if self.openai_client:
                # Fazer uma chamada de teste pequena
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Responda apenas 'OK' para confirmar que está funcionando."},
                        {"role": "user", "content": "teste"}
                    ],
                    max_tokens=5
                )
                
                if response and response.choices:
                    logger.info("✅ Teste ChatGPT: API funcionando corretamente")
                    return True
                else:
                    logger.warning("⚠️ Teste ChatGPT: Resposta vazia - usando fallback")
                    
        except Exception as e:
            logger.error(f"❌ Teste ChatGPT falhou: {e} - usando fallback")
            # Se o teste falhar, desabilitar OpenAI para este processo
            self.openai_client = None
        
        return False

    async def get_response(self, user_message, user_name=""):
        """Gera resposta da Kaori usando ChatGPT, IA Local ou fallback para respostas simples"""
        
        # Modo auto: tenta OpenAI primeiro, depois IA local
        if self.ai_mode == "auto":
            # Tentar OpenAI primeiro
            if self.openai_client:
                try:
                    # Preparar mensagem com contexto do usuário
                    user_context = f"Usuário: {user_name}\n" if user_name else ""
                    full_message = f"{user_context}Mensagem: {user_message}"
                    
                    response = self.openai_client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": full_message}
                        ],
                        max_tokens=150  # Manter respostas concisas
                    )
                    
                    ai_response = response.choices[0].message.content.strip()
                    logger.info(f"🤖 OpenAI respondeu para {user_name or 'usuário'}")
                    return ai_response
                    
                except Exception as e:
                    logger.error(f"❌ Erro no OpenAI: {e}")
                    # Continua para tentar IA local
            
            # Tentar IA Local se OpenAI falhar
            if local_ai.is_initialized:
                try:
                    local_response = await local_ai.responder_ia(user_message)
                    if local_response:
                        logger.info(f"🤖 IA Local respondeu para {user_name or 'usuário'}")
                        return local_response
                except Exception as e:
                    logger.error(f"❌ Erro na IA Local: {e}")
        
        # Modo OpenAI apenas
        elif self.ai_mode == "openai" and self.openai_client:
            try:
                user_context = f"Usuário: {user_name}\n" if user_name else ""
                full_message = f"{user_context}Mensagem: {user_message}"
                
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": full_message}
                    ],
                    max_tokens=150
                )
                
                ai_response = response.choices[0].message.content.strip()
                logger.info(f"🤖 OpenAI respondeu para {user_name or 'usuário'}")
                return ai_response
                
            except Exception as e:
                logger.error(f"❌ Erro no OpenAI: {e}")
        
        # Modo IA Local apenas
        elif self.ai_mode == "local" and local_ai.is_initialized:
            try:
                local_response = await local_ai.responder_ia(user_message)
                if local_response:
                    logger.info(f"🤖 IA Local respondeu para {user_name or 'usuário'}")
                    return local_response
            except Exception as e:
                logger.error(f"❌ Erro na IA Local: {e}")
        
        # Fallback: respostas simples se todas as IAs falharem
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ["oi", "olá", "hello", "hi", "ola", "oii"]):
            responses = [
                "Oi! 🌸 Como posso ajudar você hoje?",
                "Olá! ✨ Em que posso ser útil?",
                "Oi querido! 💕 O que você gostaria de saber?"
            ]
            response = random.choice(responses)
            if user_name:
                response = response.replace("você", user_name)
            return response
            
        elif any(word in message_lower for word in ["ajuda", "help", "como", "o que"]):
            return "Claro! 💫 Posso ajudar com comandos, jogos, economia e muito mais! Use `/ajuda` para ver todas as opções! ✨"
            
        elif any(word in message_lower for word in ["obrigado", "obrigada", "thanks", "valeu"]):
            return "De nada! 💕 Fico feliz em ajudar!"
            
        elif any(word in message_lower for word in ["quem é você", "quem você é", "seu nome"]):
            return "Eu sou a Kaori! 🌸 Sou sua assistente virtual carinhosa e estou aqui para tornar este servidor mais divertido! ✨"
        
        else:
            return "Interessante! 🤔 Me conte mais sobre isso, ou use `/ajuda` para ver o que posso fazer! 💫"
    
    def set_ai_mode(self, mode: str):
        """Define o modo de IA (auto, openai, local)"""
        if mode in ["auto", "openai", "local"]:
            self.ai_mode = mode
            logger.info(f"🔄 Modo de IA alterado para: {mode}")
        else:
            logger.warning(f"❌ Modo de IA inválido: {mode}")

# Import PostgreSQL (obrigatório)
import psycopg2
import psycopg2.extras
HAS_POSTGRESQL = True

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

# Função helper para envio seguro de mensagens Discord
async def safe_send_response(interaction: discord.Interaction, embed=None, content=None, ephemeral=False, view=None):
    """Envia resposta de forma segura, verificando se já foi respondida"""
    try:
        # Verificar se a interação ainda é válida
        if not interaction:
            logger.warning("Interação é None")
            return None
            
        # Verificar se embed e content são válidos
        if embed is None and content is None:
            logger.warning("Embed e content são None")
            return None
            
        # Verificar timeout da interação (15 minutos)
        import time
        if hasattr(interaction, 'created_at') and interaction.created_at:
            age = time.time() - interaction.created_at.timestamp()
            if age > 900:  # 15 minutos
                logger.warning("Interação expirou (mais de 15 minutos)")
                return None
        
        # Verificar se response existe e não é None
        if hasattr(interaction, 'response') and interaction.response is not None:
            try:
                if not interaction.response.is_done():
                    # Se ainda não respondeu, usa response.send_message
                    return await interaction.response.send_message(embed=embed, content=content, ephemeral=ephemeral, view=view)
                else:
                    # Se já respondeu, usa followup.send
                    return await interaction.followup.send(embed=embed, content=content, ephemeral=ephemeral, view=view)
            except AttributeError:
                # response.is_done() não existe ou response é None
                logger.warning("interaction.response é None ou não tem is_done()")
                pass
        
        # Fallback: tentar canal direto
        if hasattr(interaction, 'channel') and interaction.channel:
            if hasattr(interaction.channel, 'send') and not isinstance(interaction.channel, (discord.ForumChannel, discord.CategoryChannel)):
                return await interaction.channel.send(embed=embed, content=content, view=view)
        
        logger.warning("Não foi possível enviar resposta - todos os métodos falharam")
        return None
            
    except discord.errors.InteractionResponded:
        # Interação já foi respondida, tentar followup
        try:
            return await interaction.followup.send(embed=embed, content=content, ephemeral=ephemeral, view=view)
        except Exception as followup_error:
            logger.info(f"Followup falhou, tentando canal direto: {followup_error}")
            if hasattr(interaction, 'channel') and interaction.channel:
                # Verificar se o canal suporta envio de mensagens
                if hasattr(interaction.channel, 'send') and not isinstance(interaction.channel, (discord.ForumChannel, discord.CategoryChannel)):
                    try:
                        return await interaction.channel.send(embed=embed, content=content, view=view)
                    except Exception as channel_error:
                        logger.error(f"Erro ao enviar no canal: {channel_error}")
            return None
            
    except (discord.errors.NotFound, discord.errors.HTTPException):
        # Se a interação expirou ou token inválido, tenta enviar no canal como último recurso
        if hasattr(interaction, 'channel') and interaction.channel:
            # Verificar se o canal suporta envio de mensagens
            if hasattr(interaction.channel, 'send') and not isinstance(interaction.channel, (discord.ForumChannel, discord.CategoryChannel)):
                try:
                    return await interaction.channel.send(embed=embed, content=content, view=view)
                except Exception as channel_error:
                    logger.info(f"Canal direto falhou: {channel_error}")
        return None
        
    except Exception as e:
        logger.error(f"Erro geral ao enviar resposta: {e}")
        # Última tentativa: enviar erro simples no canal se possível
        try:
            if (hasattr(interaction, 'channel') and 
                interaction.channel and 
                hasattr(interaction.channel, 'send') and 
                not isinstance(interaction.channel, (discord.ForumChannel, discord.CategoryChannel))):
                await interaction.channel.send("❌ Erro interno do bot. Tente novamente.")
        except Exception as fallback_error:
            logger.error(f"Erro no fallback de envio: {fallback_error}")
        return None

try:
    import zipfile
except ImportError:
    zipfile = None


# Sistema de monitoramento de saúde do bot
last_heartbeat = datetime.datetime.now()
heartbeat_interval = 600  # 10 minutos (menos frequente)

async def health_monitor():
    """Monitor de saúde do bot"""
    global last_heartbeat

    while True:
        try:
            await asyncio.sleep(heartbeat_interval)

            current_time = datetime.datetime.now()
            time_since_heartbeat = (current_time - last_heartbeat).total_seconds()

            # Só alertar se realmente houver problema (20 minutos sem heartbeat)
            if time_since_heartbeat > heartbeat_interval * 2:
                # Verificar se o bot está realmente com problemas
                if not bot.is_ready() or bot.latency > 5.0:  # Latência muito alta
                    logger.warning("⚠️ Bot com problemas detectados")
                
                # Tentar ping mais robusto
                try:
                    # Testar comando simples
                    await asyncio.wait_for(asyncio.sleep(0.1), timeout=5.0)
                    if bot.is_ready() and bot.latency < 5.0:
                        last_heartbeat = current_time
                        logger.info("💓 Heartbeat restaurado")
                    else:
                        logger.error("💔 Bot com problemas de conectividade confirmados")
                except asyncio.TimeoutError:
                    logger.error("💔 Timeout no teste de conectividade")

        except Exception as e:
            logger.error(f"Erro no monitor de saúde: {e}")
            await asyncio.sleep(60)


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
# Sistemas de keep-alive removidos para economizar recursos no Railway

# Configuração do logging avançado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rxbot.log'),
        logging.StreamHandler(sys.stdout)  # Force stdout para gunicorn ver
    ]
)

# Log adicional para gunicorn
if os.getenv('GUNICORN_CMD_ARGS'):
    print("🚀 Executando via Gunicorn - Logs detalhados do bot aparecerão aqui")
    # Forçar flush do stdout para gunicorn
    import sys
    sys.stdout.flush()

# Remover todos os handlers existentes para evitar conflitos
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Configurar logging do zero para funcionar com gunicorn
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Forçar para stdout
    ],
    force=True  # Forçar reconfiguração
)

# Configurar logger principal
logger = logging.getLogger('Kaori')
logger.setLevel(logging.INFO)

# Garantir que todos os loggers importantes sejam configurados
important_loggers = ['discord', 'httpx', 'asyncio']
for logger_name in important_loggers:
    temp_logger = logging.getLogger(logger_name)
    temp_logger.setLevel(logging.INFO)

# Instanciar a IA da Kaori (depois do logger)
kaori_ai = KaoriAI()

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
    command_prefix=['RX', 'rx', '/', 'Rx', '!', '.', '>', '<', '?', 'bot ', 'BOT ', 'Bot '],
    intents=intents,
    help_command=None,
    case_insensitive=True,
    strip_after_prefix=True
)

# Sistema HTTP simplificado usando requests quando necessário
def make_http_request(url, method='GET', **kwargs):
    """Fazer requisição HTTP simples usando requests"""
    try:
        if method.upper() == 'GET':
            response = requests.get(url, timeout=10, **kwargs)
        elif method.upper() == 'POST':
            response = requests.post(url, timeout=10, **kwargs)
        else:
            response = requests.request(method, url, timeout=10, **kwargs)

        return response
    except Exception as e:
        logger.info(f"ℹ️ Requisição HTTP: {e}")  # Mudado para info
        return None

# Database connection pool to avoid locking issues
import threading
db_lock = threading.RLock()  # Usar RLock para permitir múltiplas aquisições pela mesma thread

# Track database connection state to avoid spam logging
_db_connection_logged = False
_db_connection_error_state = False

# Detectar se está no Railway ou ambiente de produção
def is_production():
    """Detectar se está rodando em produção (Railway)"""
    return bool(os.getenv('DATABASE_URL') or os.getenv('RAILWAY_ENVIRONMENT'))

def get_db_connection():
    """Get PostgreSQL database connection with schema normalization"""
    global _db_connection_logged, _db_connection_error_state
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL não encontrada. PostgreSQL é obrigatório.")
    
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        
        # Normalize schema to 'public' and log connection details
        cursor = conn.cursor()
        cursor.execute("SET search_path TO public;")
        
        # Log diagnostic information (mask credentials) - only log once or after error recovery
        
        if not _db_connection_logged or _db_connection_error_state:
            cursor.execute("SELECT current_database(), current_user, current_setting('search_path');")
            db_name, db_user, search_path = cursor.fetchone()
            
            # Mask user details for security
            masked_user = db_user[:3] + "***" if len(db_user) > 3 else "***"
            
            if _db_connection_error_state:
                logger.info(f"🔄 DB Reconnected: {db_name} | User: {masked_user} | Schema: {search_path}")
            else:
                logger.info(f"🔗 DB Connected: {db_name} | User: {masked_user} | Schema: {search_path}")
            
            _db_connection_logged = True
            _db_connection_error_state = False
        
        conn.commit()
        return conn
    except Exception as e:
        _db_connection_error_state = True
        logger.error(f"Erro ao conectar PostgreSQL: {e}")
        raise e

def execute_query(query, params=None, fetch_one=False, fetch_all=False, timeout=10):
    """Executar query PostgreSQL com melhor tratamento de erros"""
    max_retries = 3
    
    # All queries now use native PostgreSQL %s placeholders
    # Validate no SQLite placeholders remain
    if '?' in query:
        raise ValueError(f"SQLite placeholder '?' detected in query. Use '%s' instead: {query}")
    
    # Validar parâmetros
    if params is None:
        params = []
    elif not isinstance(params, (list, tuple)):
        params = [params]
    
    for attempt in range(max_retries):
        conn = None
        try:
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                try:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)

                    result = None
                    if fetch_one:
                        result = cursor.fetchone()
                    elif fetch_all:
                        result = cursor.fetchall()

                    conn.commit()
                    return result

                except psycopg2.Error as e:
                    conn.rollback()
                    # Log silencioso - apenas na última tentativa
                    if attempt == max_retries - 1:
                        # Apenas registros críticos
                        pass
                except Exception as e:
                    conn.rollback()
                    # Log silencioso - apenas na última tentativa
                    if attempt == max_retries - 1:
                        pass
                finally:
                    if conn:
                        conn.close()
                        
        except Exception as e:
            # Log silencioso para evitar spam
            if attempt == max_retries - 1:
                return None
            
        # Pausa progressiva antes de tentar novamente
        import time
        time.sleep(0.1 * (attempt + 1))
    
    return None

# Database setup with proper error handling
def init_database():
    """Initialize PostgreSQL database"""
    with db_lock:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # PostgreSQL types
            auto_increment = "SERIAL PRIMARY KEY"
            integer_type = "BIGINT"
            text_type = "TEXT"
            timestamp_type = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            date_type = "DATE"

            # Tabela de tickets
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS tickets (
                ticket_id {auto_increment},
                guild_id {integer_type},
                creator_id {integer_type},
                channel_id {integer_type},
                status {text_type} DEFAULT 'open',
                created_at {timestamp_type},
                closed_by {integer_type},
                reason {text_type}
            )''')

            # User economy and stats
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS users (
                user_id {integer_type} PRIMARY KEY,
                coins {integer_type} DEFAULT 50,
                xp {integer_type} DEFAULT 0,
                level {integer_type} DEFAULT 1,
                reputation {integer_type} DEFAULT 0,
                bank {integer_type} DEFAULT 0,
                last_daily {date_type},
                last_weekly {date_type},
                last_monthly {date_type},
                inventory {text_type} DEFAULT '{{}}',
                achievements {text_type} DEFAULT '[]',
                settings {text_type} DEFAULT '{{}}',
                join_date {timestamp_type},
                total_messages {integer_type} DEFAULT 0,
                voice_time {integer_type} DEFAULT 0,
                warnings {integer_type} DEFAULT 0
            )''')

            # Guild settings
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS guilds (
                guild_id {integer_type} PRIMARY KEY,
                name {text_type},
                prefix {text_type} DEFAULT 'RX',
                welcome_channel {integer_type},
                goodbye_channel {integer_type},
                log_channel {integer_type},
                mute_role {integer_type},
                auto_role {integer_type},
                settings {text_type} DEFAULT '{{}}',
                economy_settings {text_type} DEFAULT '{{}}',
                moderation_settings {text_type} DEFAULT '{{}}'
            )''')

            # Events system
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS events (
                id {auto_increment},
                guild_id {integer_type},
                creator_id {integer_type},
                title {text_type},
                description {text_type},
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                max_participants {integer_type} DEFAULT 0,
                participants {text_type} DEFAULT '[]',
                created_at {timestamp_type},
                status {text_type} DEFAULT 'active'
            )''')

            # Moderation logs
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS moderation_logs (
                id {auto_increment},
                guild_id {integer_type},
                user_id {integer_type},
                moderator_id {integer_type},
                action {text_type},
                reason {text_type},
                duration {integer_type},
                timestamp {timestamp_type}
            )''')

            # Economy transactions
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS transactions (
                id {auto_increment},
                user_id {integer_type},
                guild_id {integer_type},
                type {text_type},
                amount {integer_type},
                description {text_type},
                timestamp {timestamp_type}
            )''')

            # Message logs (simplified)
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS message_logs (
                id {auto_increment},
                guild_id {integer_type},
                channel_id {integer_type},
                user_id {integer_type},
                message_id {integer_type},
                content {text_type},
                timestamp {timestamp_type}
            )''')

            # Custom commands
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS custom_commands (
                id {auto_increment},
                guild_id {integer_type},
                command_name {text_type},
                response {text_type},
                creator_id {integer_type},
                uses {integer_type} DEFAULT 0,
                created_at {timestamp_type}
            )''')

            # Sistema de Clans
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS clans (
                id {auto_increment},
                guild_id {integer_type},
                name {text_type},
                tag {text_type},
                leader_id {integer_type},
                description {text_type},
                members {text_type} DEFAULT '[]',
                level {integer_type} DEFAULT 1,
                xp {integer_type} DEFAULT 0,
                wins {integer_type} DEFAULT 0,
                losses {integer_type} DEFAULT 0,
                treasury {integer_type} DEFAULT 0,
                created_at {timestamp_type}
            )''')

            # Desafios entre Clans
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS clan_challenges (
                id {auto_increment},
                guild_id {integer_type},
                challenger_clan_id {integer_type},
                challenged_clan_id {integer_type},
                challenger_user_id {integer_type},
                challenge_type {text_type},
                bet_amount {integer_type} DEFAULT 0,
                status {text_type} DEFAULT 'pending',
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                winner_clan_id {integer_type},
                created_at {timestamp_type}
            )''')

            # Reminders
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS reminders (
                id {auto_increment},
                user_id {integer_type},
                guild_id {integer_type},
                channel_id {integer_type},
                reminder_text {text_type},
                remind_time TIMESTAMP,
                created_at {timestamp_type}
            )''')

            # Sistema de sorteios
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS giveaways (
                id {auto_increment},
                guild_id {integer_type},
                channel_id {integer_type},
                creator_id {integer_type},
                title {text_type},
                prize {text_type},
                winners_count {integer_type} DEFAULT 1,
                bet_amount {integer_type} DEFAULT 0,
                end_time TIMESTAMP,
                message_id {integer_type},
                participants {text_type} DEFAULT '[]',
                status {text_type} DEFAULT 'active',
                created_at {timestamp_type}
            )''')

            # Auto-moderation rules
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS auto_mod_rules (
                id {auto_increment},
                guild_id {integer_type},
                rule_type {text_type},
                rule_data {text_type},
                punishment {text_type},
                enabled {integer_type} DEFAULT 1,
                created_at {timestamp_type}
            )''')

            # Tabela de eventos de clan
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS clan_events (
                id {auto_increment},
                guild_id {integer_type},
                creator_id {integer_type},
                clan1 {text_type},
                clan2 {text_type},
                event_type {text_type},
                bet_amount {integer_type},
                end_time TIMESTAMP,
                message_id {integer_type},
                participants {text_type} DEFAULT '[]',
                bets {text_type} DEFAULT '{{}}',
                status {text_type} DEFAULT 'active',
                winner_clan {text_type},
                created_at {timestamp_type}
            )''')

            # Tabela de feedback de tickets
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS ticket_feedback (
                id {auto_increment},
                ticket_channel_id {integer_type},
                user_id {integer_type},
                feedback_text {text_type},
                notas {text_type},
                media_nota {integer_type},
                timestamp {timestamp_type}
            )''')

            # Tabela de logs de comandos
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS command_logs (
                id {auto_increment},
                user_id {integer_type},
                command {text_type},
                guild_id {integer_type},
                timestamp {timestamp_type}
            )''')

            # Tabela de copinhas Stumble Guys
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS copinhas (
                id {auto_increment},
                guild_id {integer_type},
                creator_id {integer_type},
                channel_id {integer_type},
                message_id {integer_type},
                title {text_type},
                map_name {text_type},
                team_format {text_type},
                max_players {integer_type},
                participants {text_type} DEFAULT '[]',
                current_round {text_type} DEFAULT 'inscricoes',
                matches {text_type} DEFAULT '[]',
                status {text_type} DEFAULT 'active',
                created_at {timestamp_type}
            )''')

            # Tabela para mensagens interativas persistentes
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS interactive_messages (
                id {auto_increment},
                message_id {integer_type},
                channel_id {integer_type},
                guild_id {integer_type},
                message_type {text_type},
                data {text_type} DEFAULT '{{}}',
                status {text_type} DEFAULT 'active',
                created_at {timestamp_type}
            )''')

            # Tabela de partidas da copinha
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS copinha_matches (
                id {auto_increment},
                copinha_id {integer_type},
                round_name {text_type},
                match_number {integer_type},
                players {text_type} DEFAULT '[]',
                winner_id {integer_type},
                ticket_channel_id {integer_type},
                status {text_type} DEFAULT 'waiting',
                created_at {timestamp_type}
            )''')

            # Migração: Adicionar coluna bet_amount se não existir
            try:
                cursor.execute("ALTER TABLE giveaways ADD COLUMN bet_amount BIGINT DEFAULT 0")
                logger.info("✅ Coluna bet_amount adicionada à tabela giveaways")
            except psycopg2.errors.DuplicateColumn:
                # Coluna já existe, tudo bem
                pass
            except Exception as migration_error:
                logger.info(f"ℹ️ Migração bet_amount: {migration_error}")

            conn.commit()
            
            # Verify table creation after commit
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('users', 'tickets', 'giveaways', 'copinhas')
            """)
            table_count = cursor.fetchone()[0]
            
            if table_count != 4:
                raise Exception(f"❌ Table verification failed! Expected 4 core tables, found {table_count} in public schema")
            
            # Log all created tables for diagnostic purposes
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            all_tables = [row[0] for row in cursor.fetchall()]
            logger.info(f"📋 Created tables in public schema: {', '.join(all_tables[:10])}{'...' if len(all_tables) > 10 else ''}")
            
            logger.info("✅ Database initialized successfully!")

        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
        finally:
            if conn:
                conn.close()

# Sistemas de monitoramento anti-hibernação removidos para economizar recursos

# Database será inicializado apenas quando TOKEN existir (modo completo)
# Para modo Flask-only (sem TOKEN), não inicializa o banco

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

# Sistema de cargos Discord baseado em ranks
async def ensure_rank_roles(guild):
    """Cria cargos Discord para cada rank se não existirem"""
    try:
        # Verificar se a guilda exige 2FA
        if guild.mfa_level == 1:
            logger.warning(f"⚠️ Guilda {guild.name} exige 2FA - pulando criação automática de cargos de rank")
            logger.info(f"💡 Para resolver: Desative '2FA obrigatório para moderação' nas configurações do servidor ou peça para um admin com 2FA criar os cargos manualmente")
            return
            
        for rank_id, rank_data in RANK_SYSTEM.items():
            role_name = f"🎖️ {rank_data['name']}"
            
            # Verificar se o cargo já existe
            existing_role = discord.utils.get(guild.roles, name=role_name)
            
            if not existing_role:
                # Criar cargo com a cor do rank
                permissions = discord.Permissions(send_messages=True, read_messages=True, connect=True, speak=True)
                await guild.create_role(
                    name=role_name,
                    color=discord.Color(rank_data['color']),
                    permissions=permissions,
                    mentionable=False,
                    hoist=True,  # Separar na lista de membros
                    reason=f"Auto-criação de cargo para rank {rank_data['name']}"
                )
                logger.info(f"✅ Cargo criado: {role_name}")
    
    except discord.Forbidden as e:
        if "60003" in str(e):  # 2FA required error
            logger.warning(f"❌ 2FA obrigatório impediu criação de cargos em {guild.name}")
            logger.info(f"💡 Solução: Admin com 2FA deve desativar 'Exigir 2FA para ações de moderação' ou criar os cargos manualmente")
        else:
            logger.error(f"❌ Sem permissão para criar cargos de rank em {guild.name}: {e}")
    except Exception as e:
        logger.error(f"Erro ao criar cargos de rank: {e}")

async def update_user_rank_role(member, new_rank_id):
    """Atualiza o cargo Discord do usuário baseado no novo rank"""
    try:
        if not member or not member.guild:
            return
            
        guild = member.guild
        new_rank_data = RANK_SYSTEM[new_rank_id]
        new_role_name = f"🎖️ {new_rank_data['name']}"
        
        # Buscar o cargo do novo rank
        new_role = discord.utils.get(guild.roles, name=new_role_name)
        if not new_role:
            # Se não existe, criar todos os cargos
            await ensure_rank_roles(guild)
            new_role = discord.utils.get(guild.roles, name=new_role_name)
        
        if not new_role:
            logger.error(f"Não foi possível encontrar/criar cargo para rank {new_rank_data['name']}")
            return
        
        # Remover cargos de ranks anteriores
        rank_roles_to_remove = []
        for rank_id, rank_data in RANK_SYSTEM.items():
            if rank_id != new_rank_id:
                old_role_name = f"🎖️ {rank_data['name']}"
                old_role = discord.utils.get(guild.roles, name=old_role_name)
                if old_role and old_role in member.roles:
                    rank_roles_to_remove.append(old_role)
        
        # Remover cargos antigos
        if rank_roles_to_remove:
            await member.remove_roles(*rank_roles_to_remove, reason="Atualização de rank")
        
        # Adicionar novo cargo se não tiver
        if new_role not in member.roles:
            await member.add_roles(new_role, reason=f"Rank up para {new_rank_data['name']}")
            logger.info(f"✅ Cargo atualizado: {member.name} -> {new_role_name}")
    
    except Exception as e:
        logger.error(f"Erro ao atualizar cargo de rank para {member.name}: {e}")

async def organize_rank_roles(guild):
    """Organiza os cargos de rank na hierarquia correta"""
    try:
        # Garantir que o cargo Kaori existe antes de organizar
        await ensure_kaori_role(guild)
        
        # Buscar cargo "Kaori" para posicionar os ranks abaixo dele
        kaori_role = discord.utils.get(guild.roles, name="Kaori")
        member_role = None
        
        if not kaori_role:
            # Se ainda não encontrar Kaori, buscar cargo "membro" para fallback
            for role in guild.roles:
                if role.name.lower() in ['membro', 'member']:
                    member_role = role
                    break
        
        # Organizar cargos de rank em ordem decrescente (maior rank = posição mais alta)
        for rank_id in reversed(range(1, 13)):  # 12 ranks, do maior para o menor
            if rank_id in RANK_SYSTEM:
                rank_data = RANK_SYSTEM[rank_id]
                role_name = f"🎖️ {rank_data['name']}"
                role = discord.utils.get(guild.roles, name=role_name)
                
                if role:
                    # Posicionar abaixo do cargo da Kaori
                    if kaori_role:
                        # Posicionar abaixo da Kaori (posição menor = mais baixo)
                        # Garantir que nunca seja igual ou maior que a posição da Kaori
                        target_position = kaori_role.position - (13 - rank_id + 1)
                        position = max(1, min(target_position, kaori_role.position - 1))
                    elif member_role:
                        # Fallback: posicionar ACIMA do cargo de membro
                        position = member_role.position + rank_id
                    else:
                        position = rank_id
                    
                    await role.edit(position=position)
        
        logger.info("✅ Cargos de rank organizados na hierarquia")
    
    except Exception as e:
        logger.error(f"Erro ao organizar cargos de rank: {e}")

# Palavras que geram warn automático
AUTO_WARN_WORDS = [
    'spam', 'flood', 'hack', 'cheat', 'trapaça',
    'xingamento', 'ofensa', 'discriminação'
]

# Loja de itens do bot
LOJA_ITENS = {
    1: {
        'nome': 'Desafio do Dia',
        'preco': 150,
        'descricao': 'Ganhe entre 0-500 moedas aleatórias',
        'emoji': '🎲',
        'raridade': 'Comum',
        'efeito': 'daily_challenge'
    },
    2: {
        'nome': 'Caixa Misteriosa',
        'preco': 300,
        'descricao': 'Ganhe item aleatório ou coins',
        'emoji': '📦',
        'raridade': 'Incomum',
        'efeito': 'mystery_box'
    },
    3: {
        'nome': 'Boost de XP',
        'preco': 500,
        'descricao': 'Dobra o XP por 1 hora',
        'emoji': '📈',
        'raridade': 'Comum',
        'efeito': 'xp_boost'
    },
    4: {
        'nome': 'Salário VIP',
        'preco': 1000,
        'descricao': '+50% no trabalho por 7 dias',
        'emoji': '💼',
        'raridade': 'Incomum',
        'efeito': 'work_boost'
    },
    5: {
        'nome': 'Título Personalizado',
        'preco': 2000,
        'descricao': 'Defina seu próprio título',
        'emoji': '👑',
        'raridade': 'Raro',
        'efeito': 'custom_title'
    },
    6: {
        'nome': 'Proteção Anti-Roubo',
        'preco': 800,
        'descricao': 'Protege 90% das moedas por 3 dias',
        'emoji': '🛡️',
        'raridade': 'Incomum',
        'efeito': 'protection'
    },
    7: {
        'nome': 'Multiplicador de Daily',
        'preco': 1500,
        'descricao': 'Daily vale 3x mais por 5 dias',
        'emoji': '🎁',
        'raridade': 'Raro',
        'efeito': 'daily_multiplier'
    },
    8: {
        'nome': 'Tickets Prioritários',
        'preco': 300,
        'descricao': 'Tickets com atendimento VIP (5 usos)',
        'emoji': '🎫',
        'raridade': 'Comum',
        'efeito': 'priority_tickets'
    },
    9: {
        'nome': 'Reputação Extra',
        'preco': 600,
        'descricao': '+10 pontos de reputação',
        'emoji': '⭐',
        'raridade': 'Comum',
        'efeito': 'reputation_boost'
    },
    10: {
        'nome': 'Cofre Pessoal',
        'preco': 2500,
        'descricao': 'Banco com 0% de chance de roubo',
        'emoji': '🔒',
        'raridade': 'Épico',
        'efeito': 'personal_vault'
    },
    11: {
        'nome': 'Sorte Extrema',
        'preco': 3000,
        'descricao': '+20% de chance em jogos por 24h',
        'emoji': '🍀',
        'raridade': 'Épico',
        'efeito': 'luck_boost'
    },
    12: {
        'nome': 'Badge Especial',
        'preco': 5000,
        'descricao': 'Badge exclusiva no perfil',
        'emoji': '🏅',
        'raridade': 'Lendário',
        'efeito': 'special_badge'
    },
    13: {
        'nome': 'Chuva de Moedas',
        'preco': 1200,
        'descricao': 'Cria evento de chuva de moedas',
        'emoji': '💰',
        'raridade': 'Raro',
        'efeito': 'coin_rain'
    }
}

# A classe AdvancedAI foi removida - agora usando KaoriAI com ChatGPT real

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

@tasks.loop(hours=12)  # Reduzir frequência para 12 horas
async def backup_database():
    """Backup automático do banco de dados - otimizado"""
    try:
        # Desabilitar backup no Railway para economizar recursos
        if is_production():
            logger.info("⏭️ Backup desabilitado no Railway para economia de recursos")
            return
            
        # Só fazer backup se não for PostgreSQL (que já tem backup automático)
        if HAS_POSTGRESQL:
            logger.info("⏭️ Backup desnecessário - PostgreSQL tem backup automático")
            return
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_rxbot_{timestamp}.db"

        # Fazer backup sem usar o lock principal para não travar o bot
        try:
            import shutil
            if os.path.exists('rxbot.db'):
                shutil.copy2('rxbot.db', backup_name)
                logger.info(f"✅ Backup criado: {backup_name}")
                
                # Limpar backups antigos (manter só os 3 mais recentes)
                backup_files = [f for f in os.listdir('.') if f.startswith('backup_rxbot_') and f.endswith('.db')]
                if len(backup_files) > 3:
                    backup_files.sort()
                    for old_backup in backup_files[:-3]:
                        try:
                            os.remove(old_backup)
                            logger.info(f"🗑️ Backup antigo removido: {old_backup}")
                        except Exception as remove_error:
                            logger.error(f"Erro ao remover backup antigo: {remove_error}")
            else:
                logger.warning("Arquivo rxbot.db não encontrado para backup")
        except Exception as backup_error:
            logger.error(f"Erro específico no backup: {backup_error}")

    except Exception as e:
        logger.error(f"Erro geral no backup: {e}")

@tasks.loop(minutes=2)  # Reduzir frequência para 2 minutos
async def check_reminders():
    """Verifica lembretes"""
    try:
        now = datetime.datetime.now()
        
        # Usar transação única para evitar deadlock
        reminders_to_process = []
        try:
            reminders = execute_query('SELECT * FROM reminders WHERE remind_time <= %s LIMIT 10', (now,), fetch_all=True)
            
            if reminders:
                # Marcar como processados imediatamente
                reminder_ids = []
                for r in reminders:
                    if isinstance(r, dict):
                        reminder_ids.append(r['id'])
                    else:
                        reminder_ids.append(r[0])
                
                # Deletar lembretes processados
                for reminder_id in reminder_ids:
                    execute_query('DELETE FROM reminders WHERE id = %s', (reminder_id,))
                
                reminders_to_process = reminders
                
        except Exception as db_error:
            logger.error(f"Erro no banco check_reminders: {db_error}")
            return

        # Processar lembretes fora do lock
        for reminder in reminders_to_process:
            try:
                if isinstance(reminder, dict):
                    reminder_id = reminder['id']
                    user_id = reminder['user_id']
                    channel_id = reminder['channel_id']
                    text = reminder['reminder_text']
                else:
                    reminder_id, user_id, guild_id, channel_id, text, remind_time, created_at = reminder

                channel = bot.get_channel(channel_id)
                user = bot.get_user(user_id)

                if channel and user:
                    embed = create_embed(
                        "⏰ Lembrete!",
                        f"**{user.mention}** você pediu para eu lembrar:\n\n{text}",
                        color=0xffaa00
                    )
                    await channel.send(embed=embed)
                    logger.info(f"Lembrete {reminder_id} enviado para {user}")

            except Exception as e:
                logger.error(f"Erro ao enviar lembrete {reminder_id}: {e}")

    except Exception as e:
        logger.error(f"Erro check_reminders: {e}")

@tasks.loop(hours=6)  # A cada 6 horas
async def cleanup_inactive_messages():
    """Limpar mensagens interativas inativas do banco"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Buscar mensagens antigas (mais de 7 dias)
            cursor.execute('''
                SELECT message_id, channel_id FROM interactive_messages 
                WHERE created_at < NOW() - INTERVAL '7 days' AND status = 'active'
            ''')
            old_messages = cursor.fetchall()
            
            cleaned = 0
            for msg_data in old_messages:
                try:
                    if isinstance(msg_data, dict):
                        message_id = msg_data['message_id']
                        channel_id = msg_data['channel_id']
                    else:
                        message_id, channel_id = msg_data
                    
                    # Verificar se mensagem ainda existe
                    channel = bot.get_channel(channel_id)
                    if not channel:
                        # Canal não existe mais, marcar como inativa
                        cursor.execute('UPDATE interactive_messages SET status = %s WHERE message_id = %s', 
                                     ('inactive', message_id))
                        cleaned += 1
                        continue
                    
                    try:
                        message = await channel.fetch_message(message_id)
                        if not message:
                            cursor.execute('UPDATE interactive_messages SET status = %s WHERE message_id = %s', 
                                         ('inactive', message_id))
                            cleaned += 1
                    except discord.NotFound:
                        cursor.execute('UPDATE interactive_messages SET status = %s WHERE message_id = %s', 
                                     ('inactive', message_id))
                        cleaned += 1
                        
                except Exception as msg_error:
                    logger.error(f"Erro ao verificar mensagem {message_id}: {msg_error}")
                    
            conn.commit()
            conn.close()
            
            if cleaned > 0:
                logger.info(f"🧹 {cleaned} mensagens interativas inativas limpas")
                
    except Exception as e:
        logger.error(f"Erro na limpeza de mensagens: {e}")

@tasks.loop(minutes=2)  # Reduzir frequência para 2 minutos
async def check_giveaways():
    """Verifica sorteios que terminaram"""
    try:
        now = datetime.datetime.now()
        
        # Buscar sorteios finalizados com limite para evitar sobrecarga
        finished_giveaways = execute_query(
            'SELECT * FROM giveaways WHERE status = %s AND end_time <= %s LIMIT 5', 
            ('active', now), 
            fetch_all=True
        )

        if not finished_giveaways:
            return

        for giveaway in finished_giveaways:
            try:
                # Validar estrutura do giveaway primeiro
                if not giveaway or len(giveaway) < 10:
                    logger.warning(f"Estrutura de sorteio inválida: {giveaway}")
                    continue
                
                # Descompactar corretamente incluindo bet_amount (13 valores no total)
                if len(giveaway) == 13:
                    giveaway_id, guild_id, channel_id, creator_id, title, prize, winners_count, bet_amount, end_time, message_id, participants_json, status, created_at = giveaway
                else:
                    # Fallback para estrutura antiga (12 valores)
                    giveaway_id, guild_id, channel_id, creator_id, title, prize, winners_count, end_time, message_id, participants_json, status, created_at = giveaway
                    bet_amount = 0

                # Validar message_id antes de usar
                if not message_id or message_id == "[]" or not str(message_id).isdigit():
                    logger.error(f"Message ID inválido para sorteio {giveaway_id}: {message_id}")
                    # Marcar sorteio como erro e continuar
                    execute_query('UPDATE giveaways SET status = %s WHERE id = %s', ('error', giveaway_id))
                    continue

                # Converter message_id para int se necessário
                try:
                    message_id = int(message_id)
                except (ValueError, TypeError):
                    logger.error(f"Não foi possível converter message_id para int: {message_id}")
                    execute_query('UPDATE giveaways SET status = %s WHERE id = %s', ('error', giveaway_id))
                    continue

                # Validar outros IDs críticos
                if not channel_id or not guild_id:
                    logger.error(f"IDs críticos inválidos para sorteio {giveaway_id}: channel={channel_id}, guild={guild_id}")
                    execute_query('UPDATE giveaways SET status = %s WHERE id = %s', ('error', giveaway_id))
                    continue

                channel = bot.get_channel(channel_id)
                if not channel:
                    logger.warning(f"Canal não encontrado: {channel_id}")
                    execute_query('UPDATE giveaways SET status = %s WHERE id = %s', ('expired', giveaway_id))
                    continue

                # Tentar buscar mensagem com tratamento de erro
                try:
                    message = await channel.fetch_message(message_id)
                    if not message:
                        logger.warning(f"Mensagem não encontrada: {message_id}")
                        execute_query('UPDATE giveaways SET status = %s WHERE id = %s', ('expired', giveaway_id))
                        continue
                except discord.NotFound:
                    logger.warning(f"Mensagem deletada: {message_id}")
                    execute_query('UPDATE giveaways SET status = %s WHERE id = %s', ('expired', giveaway_id))
                    continue
                except discord.HTTPException as http_err:
                    logger.error(f"Erro HTTP ao buscar mensagem {message_id}: {http_err}")
                    continue
                except Exception as fetch_err:
                    logger.error(f"Erro inesperado ao buscar mensagem {message_id}: {fetch_err}")
                    continue

                # Obter participantes das reações
                participants = []
                try:
                    for reaction in message.reactions:
                        if str(reaction.emoji) == "🎉":
                            async for user in reaction.users():
                                if not user.bot:
                                    participants.append(user.id)
                except Exception as reaction_err:
                    logger.error(f"Erro ao obter reações: {reaction_err}")
                    participants = []

                # Determinar vencedores
                if len(participants) < winners_count:
                    winners = participants
                else:
                    winners = random.sample(participants, winners_count)

                # Usar o bet_amount já obtido da query principal
                coin_amount = bet_amount if bet_amount else 0

                if winners:
                    winner_mentions = []

                    # Se é sorteio de coins, distribuir automaticamente
                    if coin_amount > 0 and "coins" in prize.lower():
                        coins_per_winner = coin_amount // len(winners)

                        for winner_id in winners:
                            try:
                                # Adicionar coins usando execute_query
                                winner_data = get_user_data(winner_id)
                                if not winner_data:
                                    update_user_data(winner_id)
                                    current_coins = 50
                                else:
                                    current_coins = winner_data[1]

                                new_coins = current_coins + coins_per_winner
                                execute_query('UPDATE users SET coins = %s WHERE user_id = %s', (new_coins, winner_id))

                                # Registrar transação
                                execute_query('''
                                    INSERT INTO transactions (user_id, guild_id, type, amount, description)
                                    VALUES (%s, %s, %s, %s, %s)
                                ''', (winner_id, guild_id, 'giveaway_win', coins_per_winner, f"Ganhou sorteio: {title}"))

                                winner_mentions.append(f"<@{winner_id}>")

                                # Notificar vencedor por DM
                                try:
                                    winner_user = bot.get_user(winner_id)
                                    if winner_user:
                                        dm_embed = create_embed(
                                            "🎉 Você Ganhou!",
                                            f"Parabéns! Você ganhou **{coins_per_winner:,} coins** no sorteio **{title}**!\n\n"
                                            f"Os coins foram automaticamente adicionados ao seu saldo.",
                                            color=0xffd700
                                        )
                                        await winner_user.send(embed=dm_embed)
                                except Exception as dm_err:
                                    logger.info(f"Não foi possível enviar DM para {winner_id}: {dm_err}")
                            except Exception as winner_err:
                                logger.error(f"Erro ao processar vencedor {winner_id}: {winner_err}")

                        embed = create_embed(
                            f"🎉 Sorteio de Coins Finalizado: {title}",
                            f"**💰 Prêmio:** {coin_amount:,} coins\n"
                            f"**🏆 Vencedor(es):** {', '.join(winner_mentions)}\n"
                            f"**💰 Coins por vencedor:** {coins_per_winner:,} coins\n"
                            f"**👥 Participantes:** {len(participants)}\n\n"
                            f"**✅ Os coins foram automaticamente adicionados aos saldos dos vencedores!**",
                            color=0xffd700
                        )
                    else:
                        # Sorteio normal (não de coins)
                        winner_mentions = [f"<@{winner_id}>" for winner_id in winners]
                        embed = create_embed(
                            f"🎉 Sorteio Finalizado: {title}",
                            f"**🎁 Prêmio:** {prize}\n"
                            f"**🏆 Vencedor(es):** {', '.join(winner_mentions)}\n"
                            f"**👥 Participantes:** {len(participants)}",
                            color=0xffd700
                        )
                else:
                    embed = create_embed(
                        f"😢 Sorteio Cancelado: {title}",
                        f"**🎁 Prêmio:** {prize}\n"
                        f"**❌ Motivo:** Nenhum participante válido",
                        color=0xff6b6b
                    )

                # Enviar resultado no canal
                try:
                    await channel.send(embed=embed)
                except Exception as send_err:
                    logger.error(f"Erro ao enviar resultado do sorteio: {send_err}")

                # Marcar como finalizado
                execute_query('UPDATE giveaways SET status = %s WHERE id = %s', ('finished', giveaway_id))
                logger.info(f"Sorteio {giveaway_id} finalizado com sucesso")

            except Exception as e:
                logger.error(f"Erro ao finalizar sorteio {giveaway.get('id', 'unknown') if isinstance(giveaway, dict) else 'unknown'}: {e}")
                # Marcar sorteio com erro para evitar tentar novamente
                if 'giveaway_id' in locals():
                    execute_query('UPDATE giveaways SET status = %s WHERE id = %s', ('error', giveaway_id))

    except Exception as e:
        logger.error(f"Erro geral no check_giveaways: {e}")


async def get_user_position(user_id, guild_id):
    """Obter posição do usuário no ranking"""
    try:
        result = execute_query('''
            SELECT COUNT(*) + 1 as position
            FROM users u1
            WHERE u1.xp > (
                SELECT COALESCE(u2.xp, 0)
                FROM users u2
                WHERE u2.user_id = %s
            )
        ''', (user_id,), fetch_one=True)
        
        if result:
            return result[0] if isinstance(result, (list, tuple)) else result
        return "N/A"
            
    except Exception as e:
        logger.error(f"Erro ao obter posição do usuário: {e}")
        return "N/A"

def get_bot_stats():
    """Obter estatísticas do bot"""
    try:
        if not bot.is_ready():
            return {
                'guilds': 0,
                'users': 0,
                'latency': 0,
                'commands_used': global_stats.get('commands_used', 0)
            }
            
        guild_count = len(bot.guilds) if bot.guilds else 0
        all_members = list(bot.get_all_members()) if bot.guilds else []
        unique_users = len(set(all_members)) if all_members else 0
        latency = round(bot.latency * 1000, 2) if bot.latency else 0
            
        return {
            'guilds': guild_count,
            'users': unique_users,
            'latency': latency,
            'commands_used': global_stats.get('commands_used', 0)
        }
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return {
            'guilds': 0,
            'users': 0, 
            'latency': 0,
            'commands_used': 0
        }

def save_interactive_message(message_id, channel_id, guild_id, message_type, data=None):
    """Salvar mensagem interativa no banco para persistir após redeploy"""
    try:
        if data is None:
            data = {}
            
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO interactive_messages (message_id, channel_id, guild_id, message_type, data)
                VALUES (%s, %s, %s, %s, %s)
            ''', (message_id, channel_id, guild_id, message_type, json.dumps(data)))
            conn.commit()
            conn.close()
            
        logger.info(f"Mensagem interativa salva: {message_type} - {message_id}")
    except Exception as e:
        logger.error(f"Erro ao salvar mensagem interativa: {e}")

async def restore_interactive_messages():
    """Restaurar mensagens interativas após reinício do bot"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT message_id, channel_id, guild_id, message_type, data 
                FROM interactive_messages 
                WHERE status = 'active'
            ''')
            messages = cursor.fetchall()
            conn.close()

        restored_count = 0
        failed_messages = []
        
        for msg_data in messages:
            try:
                # PostgreSQL retorna tuplas, não dicionários
                if isinstance(msg_data, (tuple, list)) and len(msg_data) >= 5:
                    message_id, channel_id, guild_id, message_type, data_json = msg_data[:5]
                    data = json.loads(data_json) if data_json else {}
                else:
                    logger.warning(f"Formato inesperado de dados da mensagem: {msg_data}")
                    continue

                # Verificar se guild ainda existe
                guild = bot.get_guild(guild_id)
                if not guild:
                    failed_messages.append(message_id)
                    continue

                # Verificar se canal ainda existe
                channel = bot.get_channel(channel_id)
                if not channel:
                    failed_messages.append(message_id)
                    continue

                # Verificar se mensagem ainda existe (com retry) - apenas para canais de texto
                message_exists = False
                if hasattr(channel, 'fetch_message'):
                    for attempt in range(3):  # 3 tentativas
                        try:
                            message = await channel.fetch_message(message_id)
                            if message:
                                message_exists = True
                                break
                        except discord.NotFound:
                            break
                        except (discord.HTTPException, discord.Forbidden) as e:
                            logger.warning(f"Tentativa {attempt + 1} falhou para mensagem {message_id}: {e}")
                            await asyncio.sleep(1)  # Aguardar 1 segundo antes de tentar novamente
                else:
                    # Canal não suporta fetch_message, marcar como inválido
                    failed_messages.append(message_id)
                    continue

                if not message_exists:
                    failed_messages.append(message_id)
                    continue

                # Restaurar na memória
                active_games[message_id] = {
                    'type': message_type,
                    'channel_id': channel_id,
                    'guild_id': guild_id,
                    **data
                }
                
                # Restaurar views específicas
                if message_type == 'match_winner':
                    try:
                        winner_view = MatchWinnerView(
                            copinha_id=data.get('copinha_id'),
                            match_id=data.get('match_id'), 
                            team1=data.get('team1'),
                            team2=data.get('team2'),
                            creator_id=data.get('creator_id'),
                            team_format=data.get('team_format')
                        )
                        bot.add_view(winner_view)
                        logger.debug(f"View de match_winner restaurada para message {message_id}")
                    except Exception as view_error:
                        logger.error(f"Erro ao restaurar view match_winner para {message_id}: {view_error}")
                
                restored_count += 1
                logger.debug(f"Mensagem {message_id} ({message_type}) restaurada com sucesso")
                
            except Exception as msg_error:
                logger.error(f"Erro ao restaurar mensagem {message_id}: {msg_error}")
                if 'message_id' in locals():
                    failed_messages.append(message_id)

        # Limpar mensagens que falharam
        if failed_messages:
            try:
                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.executemany('''
                        UPDATE interactive_messages 
                        SET status = 'inactive' 
                        WHERE message_id = %s
                    ''', [(msg_id,) for msg_id in failed_messages])
                    conn.commit()
                    conn.close()
                logger.info(f"🧹 {len(failed_messages)} mensagens inválidas marcadas como inativas")
            except Exception as cleanup_error:
                logger.error(f"Erro ao limpar mensagens inválidas: {cleanup_error}")

        if restored_count > 0:
            logger.info(f"✅ {restored_count} mensagens interativas restauradas após redeploy")
        else:
            logger.info("ℹ️ Nenhuma mensagem interativa para restaurar")

    except Exception as e:
        logger.error(f"Erro ao restaurar mensagens interativas: {e}")

# Utility function for interaction handling
async def safe_interaction_response(interaction, embed, ephemeral=False):
    """Safely respond to interaction, handling timeout errors"""
    try:
        # Check if interaction is valid
        if not interaction:
            logger.warning("Interaction is None in safe_interaction_response")
            return

        # Check if interaction has required attributes
        if not hasattr(interaction, 'response') or interaction.response is None:
            logger.warning("Interaction.response is None or missing")
            return

        # Check if interaction expired (older than 14 minutes to be safe)
        import time
        if hasattr(interaction, 'created_at') and interaction.created_at:
            age = time.time() - interaction.created_at.timestamp()
            if age > 840:  # 14 minutes
                logger.warning("Interaction expired (>14 minutes)")
                return

        # Check if already responded with proper None checking
        try:
            is_done = interaction.response.is_done()
        except AttributeError:
            logger.warning("interaction.response.is_done() not available")
            # Try fallback method
            await safe_send_response(interaction, embed=embed, ephemeral=ephemeral)
            return

        if is_done:
            try:
                await safe_send_response(interaction, embed=embed, ephemeral=ephemeral)
            except (discord.errors.InteractionResponded, discord.errors.NotFound, discord.errors.HTTPException):
                pass
        else:
            try:
                await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            except (discord.errors.InteractionResponded, discord.errors.NotFound, discord.errors.HTTPException):
                try:
                    await safe_send_response(interaction, embed=embed, ephemeral=ephemeral)
                except Exception as fallback_error:
                    logger.error(f"All response methods failed: {fallback_error}")
                    pass
    except (discord.errors.NotFound, discord.errors.HTTPException):
        # Interaction expired or already handled, ignore silently
        pass
    except Exception as e:
        logger.error(f"Erro inesperado ao responder interação: {e}")

# Utility functions with proper database handling
def get_user_data(user_id):
    """Get user data with proper error handling - sempre retorna tupla"""
    if not user_id:
        logger.error("user_id não fornecido para get_user_data")
        return None
        
    try:
        result = execute_query('SELECT * FROM users WHERE user_id = %s', (user_id,), fetch_one=True)
        
        if result:
            # Se for dict (PostgreSQL com RealDictCursor), converter para tupla
            if isinstance(result, dict):
                return (
                    result.get('user_id', user_id),
                    result.get('coins', 50),
                    result.get('xp', 0),
                    result.get('level', 1),
                    result.get('reputation', 0),
                    result.get('bank', 0),
                    result.get('last_daily'),
                    result.get('last_weekly'),
                    result.get('last_monthly'),
                    result.get('inventory', '{}'),
                    result.get('achievements', '[]'),
                    result.get('settings', '{}'),
                    result.get('join_date'),
                    result.get('total_messages', 0),
                    result.get('voice_time', 0),
                    result.get('warnings', 0)
                )
            # Se for tupla ou lista, garantir que tem todos os campos
            elif isinstance(result, (tuple, list)):
                # Completar tupla se estiver incompleta
                default_values = [user_id, 50, 0, 1, 0, 0, None, None, None, '{}', '[]', '{}', None, 0, 0, 0]
                result_list = list(result)
                
                # Preencher campos faltantes
                while len(result_list) < len(default_values):
                    result_list.append(default_values[len(result_list)])
                    
                return tuple(result_list)
                
        # Se não encontrou dados, criar usuário com dados padrão
        default_data = (user_id, 50, 0, 1, 0, 0, None, None, None, '{}', '[]', '{}', None, 0, 0, 0)
        
        # Tentar criar o usuário no banco
        try:
            execute_query('INSERT INTO users (user_id, coins, xp, level) VALUES (%s, %s, %s, %s)', 
                         (user_id, 50, 0, 1))
            logger.info(f"Usuário {user_id} criado com dados padrão")
        except Exception as create_error:
            logger.error(f"Erro ao criar usuário {user_id}: {create_error}")
            
        return default_data
        
    except Exception as e:
        logger.error(f"Erro ao buscar dados do usuário {user_id}: {e}")
        # Sempre retornar dados padrão em caso de erro
        return (user_id, 50, 0, 1, 0, 0, None, None, None, '{}', '[]', '{}', None, 0, 0, 0)

def update_user_data(user_id, **kwargs):
    """Update user data with proper error handling"""
    try:
        # Check if user exists
        user_exists = execute_query('SELECT user_id FROM users WHERE user_id = %s', (user_id,), fetch_one=True)
        if not user_exists:
            execute_query('INSERT INTO users (user_id) VALUES (%s)', (user_id,))

        # Update fields
        for field, value in kwargs.items():
            if field in ['coins', 'xp', 'level', 'reputation', 'bank', 'total_messages', 'voice_time', 'warnings']:
                execute_query(f'UPDATE users SET {field} = %s WHERE user_id = %s', (value, user_id))
            elif field in ['inventory', 'achievements', 'settings']:
                execute_query(f'UPDATE users SET {field} = %s WHERE user_id = %s', (json.dumps(value), user_id))
            elif field in ['last_daily', 'last_weekly', 'last_monthly']:
                execute_query(f'UPDATE users SET {field} = %s WHERE user_id = %s', (value, user_id))

    except Exception as e:
        logger.error(f"Error updating user data: {e}")

def add_xp(user_id, amount):
    """Add XP with level and rank calculation"""
    try:
        data = get_user_data(user_id)
        if not data:
            update_user_data(user_id, xp=amount, level=1)
            return False, 1, False, 1

        # data sempre retorna tupla agora
        current_xp = data[2] if len(data) > 2 else 0
        current_level = data[3] if len(data) > 3 else 1

        new_xp = current_xp + amount

        # Calculate new level
        new_level = int(math.sqrt(new_xp / 100)) + 1
        leveled_up = new_level > current_level

        # Calculate rank progression
        old_rank_id, old_rank = get_user_rank(current_xp)
        new_rank_id, new_rank = get_user_rank(new_xp)
        rank_up = new_rank_id > old_rank_id

        update_user_data(user_id, xp=new_xp, level=new_level)
        return leveled_up, new_level, rank_up, new_rank_id, old_rank_id
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

def create_embed(title, description=None, color=0xFF4500, **kwargs):
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

# ============ SLASH COMMANDS - TODOS OS COMANDOS LISTADOS NA AJUDA ============

# ============ TODOS OS 300+ SLASH COMMANDS DISPONÍVEIS ============

# 1. COMANDOS BÁSICOS (20 comandos)
@bot.tree.command(name="ping", description="Ver latência do bot")
async def slash_ping(interaction: discord.Interaction):
    """Slash command para ping"""
    cmd_msg = f"⚡ Comando /ping executado por {interaction.user.name} no servidor {interaction.guild.name if interaction.guild else 'DM'}"
    print(cmd_msg)
    sys.stdout.flush()
    logger.info(cmd_msg)
    
    start_time = time.time()
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

    await safe_interaction_response(interaction, embed)

@bot.tree.command(name="ajuda", description="Sistema de ajuda completo")
async def slash_ajuda(interaction: discord.Interaction, categoria: str = None):
    """Slash command para ajuda"""
    try:
        if not categoria:
            embed = create_embed(
                "📚 Central de Ajuda - Kaori",
                """**Agora com Slash Commands! Use /** antes dos comandos:

**🎮 Diversão:**
`/ajuda diversao` - Jogos, piadas, entretenimento

**💰 Economia:**
`/ajuda economia` - Dinheiro, loja premium, trabalho

**🏆 Ranks:**
`/ajuda ranks` - Sistema de ranking e XP

**📊 Informações:**
`/ajuda info` - Stats, perfil, servidor, avatar

**⚙️ Utilidades:**
`/ajuda utilidades` - Ferramentas e conversores

**🎟️ Tickets:**
`/ajuda tickets` - Sistema de suporte

**👑 Administração:**
`/ajuda admin` - Comandos para administradores

**🛠️ Sistema:**
`/ajuda sistema` - Status, performance

**🤖 IA Avançada:**
Mencione o bot para conversar!

**Total:** 59+ comandos disponíveis!
**✨ Agora todos com Slash Commands!**""",
                color=0x7289da
            )
            embed.set_footer(text="Use /ajuda <categoria> para ver comandos específicos!")
            await interaction.response.send_message(embed=embed)
            return

        # Restante das categorias...
        if categoria.lower() in ['diversao', 'diversão', 'fun']:
            embed = create_embed(
                "🎮 Comandos de Diversão (Slash)",
                """**🎲 Jogos Básicos:**
• `/jokenpo <escolha>` - Pedra, papel, tesoura
• `/dado [lados]` - Rola um dado
• `/moeda` - Cara ou coroa

**🎊 Entretenimento:**
• `/piada` - Conta uma piada aleatória
• `/enquete <pergunta>` - Cria enquete

**🤖 IA Interativa:**
• Mencione o bot para conversar!
• Sistema de IA com 200+ tópicos""",
                color=0x7289da
            )
            await interaction.response.send_message(embed=embed)

        elif categoria.lower() in ['economia', 'money', 'eco']:
            embed = create_embed(
                "💰 Comandos de Economia (Slash)",
                """**💵 Dinheiro Básico:**
• `/saldo [usuário]` - Ver saldo
• `/daily` - Recompensa diária (100 moedas)
• `/trabalhar` - Trabalhe por dinheiro
• `/roubar <usuário>` - **NOVO!** Tentar roubar (60% chance de sucesso!)

**🛒 Loja Premium:**
• `/loja` - Ver loja com itens exclusivos
• `/inventario [usuário]` - Ver inventário
• `/usar <id>` - Usar item comprado
• `/transferir <usuário> <quantidade>` - Transferir moedas

**📊 Rankings:**
• `/leaderboard [tipo]` - Ranking do servidor""",
                color=0xffd700
            )
            await interaction.response.send_message(embed=embed)

        # Continue com outras categorias conforme necessário...
        else:
            embed = create_embed(
                "❌ Categoria não encontrada",
                "Use categorias válidas: diversao, economia, ranks, info, utilidades, tickets, admin, sistema",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed)

    except Exception as e:
        logger.error(f"Erro no comando ajuda: {e}")
        await interaction.response.send_message("Erro ao carregar ajuda!", ephemeral=True)

# 2. COMANDOS DE DIVERSÃO (25 comandos)
# COMANDO TEMPORARIAMENTE DESABILITADO PARA FICAR DENTRO DO LIMITE DE 100 SLASH COMMANDS
# @bot.tree.command(name="jokenpo", description="Jogar pedra, papel ou tesoura")
async def slash_jokenpo(interaction: discord.Interaction, escolha: str):
    """Slash command para jokenpo"""
    try:
        escolhas = ['pedra', 'papel', 'tesoura']
        emojis = {'pedra': '🪨', 'papel': '📄', 'tesoura': '✂️'}

        escolha = escolha.lower()
        if escolha not in escolhas:
            embed = create_embed("❌ Escolha inválida", "Use: pedra, papel ou tesoura", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
        await safe_interaction_response(interaction, embed)
    except Exception as e:
        logger.error(f"Erro no jokenpo: {e}")
        error_embed = create_embed("❌ Erro", "Erro no jogo!", color=0xff0000)
        await safe_interaction_response(interaction, error_embed, ephemeral=True)

# COMANDO TEMPORARIAMENTE DESABILITADO PARA FICAR DENTRO DO LIMITE DE 100 SLASH COMMANDS
# @bot.tree.command(name="dado", description="Rolar um dado")
async def slash_dado(interaction: discord.Interaction, lados: int = 6):
    """Slash command para dado"""
    try:
        if lados < 2 or lados > 100:
            embed = create_embed("❌ Número inválido", "Use entre 2 e 100 lados", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        resultado = random.randint(1, lados)
        embed = create_embed(
            f"🎲 Dado de {lados} lados",
            f"**Resultado:** {resultado}",
            color=0x7289da
        )
        await safe_interaction_response(interaction, embed)
    except Exception as e:
        logger.error(f"Erro no dado: {e}")
        error_embed = create_embed("❌ Erro", "Erro no dado!", color=0xff0000)
        await safe_interaction_response(interaction, error_embed, ephemeral=True)

# MAIS 270+ SLASH COMMANDS ADICIONADOS
# COMANDO TEMPORARIAMENTE DESABILITADO PARA FICAR DENTRO DO LIMITE DE 100 SLASH COMMANDS
# @bot.tree.command(name="moeda", description="Cara ou coroa")
async def slash_moeda(interaction: discord.Interaction):
    """Slash command para moeda"""
    try:
        resultado = random.choice(['Cara', 'Coroa'])
        emoji = '🪙' if resultado == 'Cara' else '🥇'

        embed = create_embed(
            "🪙 Cara ou Coroa",
            f"**Resultado:** {emoji} {resultado}!",
            color=0xffd700
        )
        await safe_interaction_response(interaction, embed)
    except Exception as e:
        logger.error(f"Erro na moeda: {e}")
        error_embed = create_embed("❌ Erro", "Erro na moeda!", color=0xff0000)
        await safe_interaction_response(interaction, error_embed, ephemeral=True)

# COMANDO TEMPORARIAMENTE DESABILITADO PARA FICAR DENTRO DO LIMITE DE 100 SLASH COMMANDS
# @bot.tree.command(name="piada", description="Contar uma piada")
async def slash_piada(interaction: discord.Interaction):
    """Slash command para piada"""
    try:
        piadas = [
            "Por que os pássaros voam para o sul no inverno? Porque é longe demais para ir andando!",
            "O que a impressora falou para a outra impressora? Essa folha é sua ou é impressão minha?",
            "Por que o livro de matemática estava triste? Porque tinha muitos problemas!",
            "O que o pato disse para a pata? Vem quá!",
            "Por que os programadores preferem dark mode? Porque light atrai bugs!"
        ]

        piada = random.choice(piadas)
        embed = create_embed("😂 Piada da Kaori", piada, color=0xffaa00)
        await safe_interaction_response(interaction, embed)
    except Exception as e:
        logger.error(f"Erro na piada: {e}")
        error_embed = create_embed("❌ Erro", "Erro na piada!", color=0xff0000)
        await safe_interaction_response(interaction, error_embed, ephemeral=True)

@bot.tree.command(name="copinha", description="Criar uma copinha/torneio de Stumble Guys")
@app_commands.describe(
    nome="Nome da copinha (ex: Copa RX de Stumble Guys)",
    mapa="Mapa do jogo (ex: Hex-A-Gone, Fall Mountain, Door Dash)",
    formato="Formato do torneio (1v1, 2v2, 3v3, 4v4)",
    max_jogadores="Número máximo de participantes (4, 8, 16, 32, 64)"
)
@app_commands.choices(mapa=[
    app_commands.Choice(name="🧱 Block Dash", value="Block Dash"),
    app_commands.Choice(name="🏃 Rush Hour", value="Rush Hour"),
    app_commands.Choice(name="🌋 Lava Land", value="Lava Land"),
    app_commands.Choice(name="💣 Bombardment", value="Bombardment"),
    app_commands.Choice(name="🍯 Honey Drop", value="Honey Drop"),
    app_commands.Choice(name="⚡ Laser Tracer", value="Laser Tracer")
])
@app_commands.choices(formato=[
    app_commands.Choice(name="⚔️ 1v1 (Individual)", value="1v1"),
    app_commands.Choice(name="👥 2v2 (Duplas)", value="2v2"),
    app_commands.Choice(name="🏅 3v3 (Trios)", value="3v3"),
    app_commands.Choice(name="🏆 4v4 (Squads)", value="4v4")
])
@app_commands.choices(max_jogadores=[
    app_commands.Choice(name="4 participantes", value=4),
    app_commands.Choice(name="8 participantes", value=8),
    app_commands.Choice(name="16 participantes", value=16),
    app_commands.Choice(name="32 participantes", value=32),
    app_commands.Choice(name="64 participantes", value=64)
])
async def slash_copinha(interaction: discord.Interaction, 
                       nome: str, 
                       mapa: str, 
                       formato: str, 
                       max_jogadores: int):
    """Slash command para criar copinha de Stumble Guys"""
    try:
        # Verificar permissões
        if not interaction.user.guild_permissions.manage_messages:
            embed = create_embed(
                "❌ Permissão negada", 
                "Você precisa da permissão 'Gerenciar Mensagens' para criar copinhas!", 
                color=0xff0000
            )
            await safe_send_response(interaction, embed, ephemeral=True)
            return

        # Validar parâmetros
        valid_formats = ['1v1', '2v2', '3v3', '4v4']
        valid_players = [4, 8, 16, 32, 64]
        
        if formato not in valid_formats:
            embed = create_embed("❌ Formato inválido", f"Use: {', '.join(valid_formats)}", color=0xff0000)
            await safe_send_response(interaction, embed, ephemeral=True)
            return
            
        if max_jogadores not in valid_players:
            embed = create_embed("❌ Número inválido", f"Use: {', '.join(map(str, valid_players))} participantes", color=0xff0000)
            await safe_send_response(interaction, embed, ephemeral=True)
            return

        # Criar embed da copinha
        embed = create_embed(
            f"🏆 {nome}",
            f"**🗺️ Mapa:** {mapa}\n"
            f"**👥 Formato:** {formato}\n"
            f"**📊 Participantes:** 0/{max_jogadores}\n"
            f"**📋 Status:** Inscrições abertas\n"
            f"**👑 Organizador:** {interaction.user.mention}\n\n"
            f"**🎮 Clique no botão abaixo para se inscrever!**",
            color=0xffd700
        )

        # Criar view com botão de participar
        view = CopinhaJoinView(nome, mapa, formato, max_jogadores, interaction.user.id)

        # Enviar mensagem
        await interaction.response.send_message(embed=embed, view=view)
        
        # Buscar a mensagem criada para salvar no banco e active_games
        try:
            message = await interaction.original_response()
            
            # Associar mensagem à view para timeout funcionar
            view.message = message
            
            # Salvar no banco
            execute_query(
                '''INSERT INTO copinhas (guild_id, creator_id, channel_id, message_id, title, map_name, team_format, max_players, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                (interaction.guild.id, interaction.user.id, interaction.channel.id, 
                 message.id, nome, mapa, formato, max_jogadores, 'active')
            )
            
            # Salvar no active_games para gerenciamento 
            active_games[message.id] = {
                'type': 'copinha_join',
                'view': view,
                'guild_id': interaction.guild.id,
                'channel_id': interaction.channel.id,
                'creator_id': interaction.user.id,
                'created_at': datetime.datetime.now().timestamp()
            }
            
            # Salvar mensagem interativa para persistência
            save_interactive_message(
                message.id, 
                interaction.channel.id, 
                interaction.guild.id, 
                'copinha_join',
                {
                    'title': nome,
                    'map_name': mapa,
                    'team_format': formato,
                    'max_players': max_jogadores,
                    'creator_id': interaction.user.id,
                    'participants': []
                }
            )
            
            logger.info(f"Copinha criada: {nome} por {interaction.user}")
            
        except Exception as db_error:
            logger.error(f"Erro ao salvar copinha no banco: {db_error}")

    except Exception as e:
        logger.error(f"Erro ao criar copinha: {e}")
        embed = create_embed("❌ Erro", "Erro ao criar copinha! Tente novamente.", color=0xff0000)
        await safe_interaction_response(interaction, embed, ephemeral=True)

# 3. COMANDOS DE ECONOMIA (50 comandos)
@bot.tree.command(name="saldo", description="Ver saldo de moedas")
async def slash_saldo(interaction: discord.Interaction, usuario: discord.Member = None):
    """Slash command para saldo"""
    try:
        # Validar se o usuário e guild existem
        if not interaction.user or not interaction.guild:
            embed = create_embed("❌ Erro", "Este comando só pode ser usado em servidores!", color=0xff0000)
            await safe_send_response(interaction, embed, ephemeral=True)
            return

        target = usuario or interaction.user
        data = get_user_data(target.id)

        if not data or len(data) == 0:
            update_user_data(target.id)
            coins, bank = 50, 0
        else:
            coins = data[1] if data and len(data) > 1 else 50
            bank = data[5] if data and len(data) > 5 else 0

        total = coins + bank

        embed = create_embed(
            f"💰 Carteira de {target.display_name}",
            f"""**💵 Dinheiro:** {coins:,} moedas
**🏦 Banco:** {bank:,} moedas
**💎 Total:** {total:,} moedas

*Use `/daily` para ganhar moedas diárias!*""",
            color=0xffd700
        )
        embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
        await safe_interaction_response(interaction, embed)
    except Exception as e:
        logger.error(f"Erro no saldo: {e}")
        error_embed = create_embed("❌ Erro", "Erro ao carregar saldo!", color=0xff0000)
        await safe_interaction_response(interaction, error_embed, ephemeral=True)

@bot.tree.command(name="daily", description="Recompensa diária")
async def slash_daily(interaction: discord.Interaction):
    """Slash command para daily"""
    try:
        # Validar se o usuário e guild existem
        if not interaction.user or not interaction.guild:
            embed = create_embed("❌ Erro", "Este comando só pode ser usado em servidores!", color=0xff0000)
            await safe_send_response(interaction, embed, ephemeral=True)
            return

        user_id = interaction.user.id
        user_data = get_user_data(user_id)

        if not user_data:
            update_user_data(user_id)
            user_data = get_user_data(user_id)

        last_daily = user_data[6] if user_data and len(user_data) > 6 else None
        today = datetime.date.today().isoformat()

        if last_daily == today:
            embed = create_embed(
                "⏰ Já coletado!",
                "Você já coletou sua recompensa diária hoje!\nVolte amanhã para coletar novamente.",
                color=0xff6b6b
            )
            await safe_send_response(interaction, embed, ephemeral=True)
            return

        current_coins = user_data[1] if user_data and len(user_data) > 1 else 50
        new_coins = current_coins + DAILY_REWARD

        # Use execute_query para compatibilidade SQLite/PostgreSQL
        execute_query('UPDATE users SET coins = %s, last_daily = %s WHERE user_id = %s',
                     (new_coins, today, user_id))

        embed = create_embed(
            "🎁 Recompensa Diária!",
            f"""**Recompensa:** {DAILY_REWARD:,} moedas
**Novo saldo:** {new_coins:,} moedas

🔥 *Continue coletando diariamente!*""",
            color=0x00ff00
        )

        await safe_interaction_response(interaction, embed)
    except Exception as e:
        logger.error(f"Erro no daily: {e}")
        error_embed = create_embed("❌ Erro", "Erro ao coletar daily!", color=0xff0000)
        await safe_interaction_response(interaction, error_embed, ephemeral=True)

@bot.tree.command(name="trabalhar", description="Trabalhar para ganhar dinheiro")
async def slash_trabalhar(interaction: discord.Interaction):
    """Slash command para trabalhar"""
    try:
        # Validar se o usuário e guild existem
        if not interaction.user or not interaction.guild:
            embed = create_embed("❌ Erro", "Este comando só pode ser usado em servidores!", color=0xff0000)
            await safe_send_response(interaction, embed, ephemeral=True)
            return

        user_data = get_user_data(interaction.user.id)
        if not user_data:
            update_user_data(interaction.user.id)
            user_data = get_user_data(interaction.user.id)

        # Verificar cooldown (2 horas)
        try:
            settings_data = user_data[11] if len(user_data) > 11 else None
            settings = json.loads(settings_data) if settings_data else {}
            last_work = settings.get('last_work', 0)

            current_time = time.time()
            cooldown_time = WORK_COOLDOWN

            if current_time - last_work < cooldown_time:
                remaining = cooldown_time - (current_time - last_work)
                embed = create_embed(
                    "⏰ Muito cansado!",
                    f"Você precisa descansar por mais **{format_time(int(remaining))}**!",
                    color=0xff6b6b
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        except:
            settings = {}

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

        level = user_data[3] if user_data and len(user_data) > 3 else 1
        bonus = int(ganho * (level * 0.05))
        ganho_total = ganho + bonus

        # Update database with improved error handling
        conn = None
        try:
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()

                new_coins = user_data[1] + ganho_total
                # Usar execute_query para compatibilidade
                execute_query('UPDATE users SET coins = %s WHERE user_id = %s', (new_coins, interaction.user.id))

                settings['last_work'] = current_time
                execute_query('UPDATE users SET settings = %s WHERE user_id = %s', (json.dumps(settings), interaction.user.id))

                # Usar execute_query para compatibilidade
                execute_query('''
                    INSERT INTO transactions (user_id, guild_id, type, amount, description)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (interaction.user.id, interaction.guild.id, 'work', ganho_total, f"Trabalhou como {trabalho['nome']}"))

                conn.close()
                conn = None

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
            await safe_interaction_response(interaction, embed)

        except Exception as db_error:
            logger.error(f"Database error in trabalhar: {db_error}")
            if conn:
                conn.close()
            error_embed = create_embed(
                "⚠️ Erro no Sistema", 
                "Houve um problema com o banco de dados. Tente novamente em alguns segundos.", 
                color=0xff6b6b
            )
            await safe_interaction_response(interaction, error_embed, ephemeral=True)

    except Exception as e:
        logger.error(f"Erro no trabalho: {e}")
        error_embed = create_embed(
            "❌ Erro", 
            "Ocorreu um erro inesperado. Tente novamente.", 
            color=0xff6b6b
        )
        await safe_interaction_response(interaction, error_embed, ephemeral=True)

# CONTINUA COM TODOS OS 300+ COMANDOS...
# Aqui adicionarei todos os outros comandos para completar os 300+

@bot.tree.command(name="weekly", description="Recompensa semanal")
async def slash_weekly(interaction: discord.Interaction):
    """Slash command para weekly"""
    try:
        user_id = interaction.user.id
        data = get_user_data(user_id)

        if not data:
            update_user_data(user_id)
            data = get_user_data(user_id)

        last_weekly = data[7] if len(data) > 7 else None
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
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        new_coins = data[1] + WEEKLY_REWARD

        # Use execute_query para compatibilidade SQLite/PostgreSQL
        execute_query('UPDATE users SET coins = %s, last_weekly = %s WHERE user_id = %s',
                     (new_coins, week_start_str, user_id))

        embed = create_embed(
            "🎁 Recompensa Semanal!",
            f"""**Recompensa:** {WEEKLY_REWARD:,} moedas
**Novo saldo:** {new_coins:,} moedas

🔥 *Continue coletando semanalmente!*""",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Erro no weekly: {e}")
        await interaction.response.send_message("Erro ao coletar weekly!", ephemeral=True)

@bot.tree.command(name="monthly", description="Recompensa mensal")
async def slash_monthly(interaction: discord.Interaction):
    """Slash command para monthly"""
    try:
        user_id = interaction.user.id
        data = get_user_data(user_id)

        if not data:
            update_user_data(user_id)
            data = get_user_data(user_id)

        last_monthly = data[8] if len(data) > 8 else None
        today = datetime.date.today()
        month_start = today.replace(day=1).isoformat()

        if last_monthly == month_start:
            next_month = (today.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
            embed = create_embed(
                "⏰ Já coletado este mês!",
                f"Você já coletou sua recompensa mensal!\nPróxima coleta: {next_month.strftime('%d/%m/%Y')}",
                color=0xff6b6b
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        new_coins = data[1] + MONTHLY_REWARD

        # Use execute_query para compatibilidade SQLite/PostgreSQL
        execute_query('UPDATE users SET coins = %s, last_monthly = %s WHERE user_id = %s',
                     (new_coins, month_start, user_id))

        embed = create_embed(
            "🎁 Recompensa Mensal!",
            f"""**Recompensa:** {MONTHLY_REWARD:,} moedas
**Novo saldo:** {new_coins:,} moedas

🔥 *Continue coletando mensalmente!*""",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Erro no monthly: {e}")
        await interaction.response.send_message("Erro ao coletar monthly!", ephemeral=True)

@bot.tree.command(name="roubar", description="Roube coins de outro usuário (60% de chance de sucesso)")
async def slash_roubar(interaction: discord.Interaction, usuario: discord.Member):
    """Slash command para roubar coins de outro usuário"""
    try:
        # Validar se o usuário e guild existem
        if not interaction.user or not interaction.guild:
            embed = create_embed("❌ Erro", "Este comando só pode ser usado em servidores!", color=0xff0000)
            await safe_send_response(interaction, embed, ephemeral=True)
            return

        # Não pode roubar de si mesmo
        if interaction.user.id == usuario.id:
            embed = create_embed("❌ Erro", "Você não pode roubar de si mesmo!", color=0xff0000)
            await safe_send_response(interaction, embed, ephemeral=True)
            return

        # Não pode roubar do bot
        if usuario.bot:
            embed = create_embed("❌ Erro", "Você não pode roubar de bots!", color=0xff0000)
            await safe_send_response(interaction, embed, ephemeral=True)
            return

        # Obter dados dos usuários
        ladrão_data = get_user_data(interaction.user.id)
        vítima_data = get_user_data(usuario.id)

        if not ladrão_data:
            update_user_data(interaction.user.id)
            ladrão_data = get_user_data(interaction.user.id)

        if not vítima_data:
            update_user_data(usuario.id)
            vítima_data = get_user_data(usuario.id)

        # Verificar se a vítima tem coins para roubar (apenas coins fora do banco)
        coins_vítima = vítima_data[1] if len(vítima_data) > 1 else 50
        if coins_vítima <= 0:
            embed = create_embed("❌ Sem dinheiro", f"{usuario.mention} não tem coins na carteira para roubar!", color=0xff0000)
            await safe_send_response(interaction, embed, ephemeral=True)
            return

        # 60% de chance de sucesso
        sucesso = random.randint(1, 100) <= 60

        if sucesso:
            # Calcular quantos coins roubar (10% a 30% dos coins da vítima)
            porcentagem = random.randint(10, 30)
            coins_roubados = max(1, int(coins_vítima * porcentagem / 100))

            # Chance de roubar item também (20% de chance)
            item_roubado = None
            inventário_vítima = []
            inventário_ladrão = []

            try:
                inventário_vítima = json.loads(vítima_data[9]) if len(vítima_data) > 9 and vítima_data[9] else []
                inventário_ladrão = json.loads(ladrão_data[9]) if len(ladrão_data) > 9 and ladrão_data[9] else []
            except:
                inventário_vítima = []
                inventário_ladrão = []

            if inventário_vítima and random.randint(1, 100) <= 20:
                item_roubado = random.choice(inventário_vítima)
                inventário_vítima.remove(item_roubado)
                inventário_ladrão.append(item_roubado)

            # Atualizar dados
            coins_ladrão = ladrão_data[1] if len(ladrão_data) > 1 else 50
            coins_vítima_novo = coins_vítima - coins_roubados
            coins_ladrão_novo = coins_ladrão + coins_roubados

            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()

                # Atualizar ladrão
                cursor.execute('UPDATE users SET coins = %s, inventory = %s WHERE user_id = %s',
                              (coins_ladrão_novo, json.dumps(inventário_ladrão), interaction.user.id))

                # Atualizar vítima
                cursor.execute('UPDATE users SET coins = %s, inventory = %s WHERE user_id = %s',
                              (coins_vítima_novo, json.dumps(inventário_vítima), usuario.id))

                conn.commit()
                conn.close()

            # Mensagem de sucesso
            embed = create_embed(
                "🦹‍♂️ Roubo Bem Sucedido!",
                f"{interaction.user.mention} roubou **{coins_roubados:,} coins** de {usuario.mention}!",
                color=0x00ff00
            )

            if item_roubado:
                embed.add_field(name="🎁 Bônus!", value=f"Também roubou o item: **{item_roubado}**", inline=False)

        else:
            # Falhou no roubo - perde coins como punição
            coins_ladrão = ladrão_data[1] if len(ladrão_data) > 1 else 50
            penalidade = random.randint(10, 50)
            penalidade = min(penalidade, coins_ladrão)  # Não pode perder mais do que tem

            if penalidade > 0:
                coins_ladrão_novo = coins_ladrão - penalidade

                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s',
                                  (coins_ladrão_novo, interaction.user.id))
                    conn.commit()
                    conn.close()

            embed = create_embed(
                "🚨 Roubo Falhado!",
                f"{interaction.user.mention} foi pego tentando roubar {usuario.mention}!",
                color=0xff0000
            )

            if penalidade > 0:
                embed.add_field(name="💸 Punição", value=f"Perdeu **{penalidade:,} coins** como multa!", inline=False)

        await safe_interaction_response(interaction, embed)

    except Exception as e:
        logger.error(f"Erro no comando roubar: {e}")
        error_embed = create_embed("❌ Erro", "Erro ao tentar roubar!", color=0xff0000)
        await safe_interaction_response(interaction, error_embed, ephemeral=True)


# SLASH COMMANDS - ECONOMIA (Comandos únicos organizados)

# Comando slash trabalhar removido - duplicata

@bot.tree.command(name="loja", description="Ver loja de itens")
async def slash_loja(interaction: discord.Interaction):
    """Slash command para loja"""
    try:
        pass
    except:
        return

    embed = create_embed(
        "🛒 Loja Premium da Kaori",
        "✨ Itens exclusivos e poderosos disponíveis!\nUse `/comprar <id>` para comprar um item!",
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

    embed.set_footer(text=f"Use /inventario para ver seus itens | /usar <id> para usar itens")
    try:
        await safe_send_response(interaction, embed=embed)
    except:
        pass

@bot.tree.command(name="inventario", description="Ver inventário de itens")
async def slash_inventario(interaction: discord.Interaction, usuario: discord.Member = None):
    """Slash command para inventário"""
    try:
        # Validar se o usuário e guild existem
        if not interaction.user or not interaction.guild:
            embed = create_embed("❌ Erro", "Este comando só pode ser usado em servidores!", color=0xff0000)
            await safe_send_response(interaction, embed, ephemeral=True)
            return

        target = usuario or interaction.user

        try:
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (target.id,))
                result = cursor.fetchone()
                conn.close()

            if not result:
                update_user_data(target.id)
                embed = create_embed("📦 Inventário vazio", f"{target.display_name} ainda não tem itens!", color=0xffaa00)
                await safe_interaction_response(interaction, embed)
                return

            inventory_data = result[0]
            inventory = json.loads(inventory_data) if inventory_data else {}

            if not inventory:
                embed = create_embed("📦 Inventário vazio", f"{target.display_name} ainda não tem itens!", color=0xffaa00)
                await safe_interaction_response(interaction, embed)
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
                    if item_id_int in LOJA_ITENS and items_added < 25:
                        item = LOJA_ITENS[item_id_int]
                        valor_total = item['preco'] * quantidade
                        total_valor += valor_total

                        embed.add_field(
                            name=f"{item['emoji']} {item['nome']} (ID: {item_id})",
                            value=f"**Quantidade:** {quantidade}\n**Valor:** {valor_total:,} moedas\n**Use:** `/usar {item_id}`",
                            inline=True
                        )
                        items_added += 1
                except (ValueError, KeyError) as e:
                    logger.error(f"Erro ao processar item {item_id}: {e}")
                    continue

            embed.add_field(
                name="💎 Valor Total do Inventário",
                value=f"{total_valor:,} moedas",
                inline=False
            )

            embed.set_footer(text=f"Use /loja para ver itens disponíveis | Use /usar <id> para usar itens")
            embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)

            await safe_interaction_response(interaction, embed)

        except Exception as e:
            logger.error(f"Erro no inventário: {e}")
            error_embed = create_embed("❌ Erro", "Erro ao carregar inventário!", color=0xff0000)
            await safe_interaction_response(interaction, error_embed, ephemeral=True)

    except Exception as e:
        logger.error(f"Erro geral no inventário: {e}")
        error_embed = create_embed("❌ Erro", "Ocorreu um erro inesperado!", color=0xff0000)
        await safe_interaction_response(interaction, error_embed, ephemeral=True)

# SLASH COMMANDS - RANK E INFORMAÇÕES
# Comando slash rank removido - duplicata

# Comando slash perfil removido - duplicata

# Comandos slash removidos - duplicatas eliminadas

# Event handlers
@bot.event
async def on_command_error(ctx, error):
    """Manipular erros de comandos"""
    try:
        if isinstance(error, commands.CommandNotFound):
            # Ignorar comandos não encontrados silenciosamente
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = create_embed(
                "❌ Argumento Faltando",
                f"Você esqueceu de fornecer um argumento necessário.\nUse `RXajuda` para ver a sintaxe correta.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingPermissions):
            embed = create_embed(
                "❌ Sem Permissão",
                "Você não tem permissão para usar este comando.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.CommandOnCooldown):
            embed = create_embed(
                "⏰ Cooldown",
                f"Este comando está em cooldown. Tente novamente em {error.retry_after:.1f} segundos.",
                color=0xff6600
            )
            await ctx.send(embed=embed)
        elif isinstance(error, TypeError):
            logger.error(f"TypeError no comando {ctx.command}: {error}")
            return
        else:
            logger.error(f"Erro não tratado no comando {ctx.command}: {error}")
    except Exception as e:
        # Silenciosamente ignorar erros do error handler para evitar loops
        pass

@bot.event
async def on_message(message):
    """Processar mensagens para XP, IA e moderação"""
    if message.author.bot:
        return

    global_stats['messages_processed'] += 1
    
    # Log ocasional de atividade (a cada 25 mensagens para ver mais logs)
    if global_stats['messages_processed'] % 25 == 0:
        activity_msg = f"📨 Processadas {global_stats['messages_processed']} mensagens | Usuário: {message.author.name} | Servidor: {message.guild.name if message.guild else 'DM'}"
        print(activity_msg)
        sys.stdout.flush()
        logger.info(f"📨 Atividade: {global_stats['messages_processed']} mensagens processadas")

    # Sistema de XP
    try:
        leveled_up, new_level, rank_up, new_rank_id, old_rank_id = add_xp(message.author.id, XP_PER_MESSAGE)
        
        # Atualizar cargo Discord se houve rank up
        if rank_up and message.guild:
            try:
                member = message.guild.get_member(message.author.id)
                if member:
                    await update_user_rank_role(member, new_rank_id)
            except Exception as e:
                logger.error(f"Erro ao atualizar cargo de rank: {e}")

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

    # Sistema de IA (responder quando mencionado OU quando "kaori" aparecer no texto)
    should_respond = False
    content = message.content
    
    # Verificar se o bot foi mencionado
    if bot.user.mentioned_in(message) and not message.mention_everyone:
        should_respond = True
        content = message.content.replace(f'<@{bot.user.id}>', '').strip()
    
    # Verificar se "kaori" aparece no texto (case insensitive)
    elif "kaori" in message.content.lower():
        should_respond = True
        content = message.content.strip()
    
    if should_respond and content:
        try:
            response = await kaori_ai.get_response(content, message.author.display_name)
            await message.reply(response)
        except Exception as e:
            logger.error(f"Erro no sistema IA: {e}")

    # Processar comandos
    await bot.process_commands(message)

@bot.event
async def on_guild_join(guild):
    """Evento quando o bot entra em um novo servidor"""
    try:
        logger.info(f"🎉 Bot adicionado ao servidor: {guild.name} (ID: {guild.id})")
        
        # Criar cargo Kaori automaticamente
        await ensure_kaori_role(guild)
        
        # Criar cargos de rank se possível
        await ensure_rank_roles(guild)
        
        # Log sobre novo servidor
        logger.info(f"🎉 Novo servidor: {guild.name} (ID: {guild.id}) com {guild.member_count} membros")
        
    except Exception as e:
        logger.error(f"Erro no evento on_guild_join: {e}")
        await send_error_to_privileged_user(f"Erro ao entrar no servidor {guild.name}: {e}", guild)

# O handler on_message duplicado foi removido - usando apenas o principal acima

@bot.event
async def on_ready():
    # Environment check with diagnostic logging
    print("🎯 Inicializando sistema completo...")
    print("📋 Configurando sistema de logs...")
    sys.stdout.flush()  # Forçar flush
    
    logger.info("🎯 Inicializando sistema completo...")
    
    # Diagnostic environment check
    database_url = os.getenv('DATABASE_URL')
    railway_env = os.getenv('RAILWAY_ENVIRONMENT')
    port = os.getenv('PORT', '5000')
    
    if database_url:
        # Mask the URL for security (show only first and last part)
        masked_url = database_url[:15] + "***" + database_url[-10:] if len(database_url) > 25 else "***"
        logger.info(f"🔗 DATABASE_URL found: {masked_url}")
    else:
        logger.error("❌ DATABASE_URL not found in environment!")
    
    logger.info(f"🌐 Environment: {'Railway' if railway_env else 'Local'} | Port: {port}")
    
    # Inicializar database imediatamente quando bot estiver pronto
    try:
        init_database()
        init_copinha_scoreboard_table()  # Inicializar tabelas do scoreboard
        logger.info("✅ Database inicializado")
    except Exception as db_error:
        logger.error(f"❌ Erro ao inicializar database: {db_error}")
        logger.error(f"💡 DATABASE_URL status: {'SET' if database_url else 'NOT SET'}")
    
    print(f"🤖 Kaori está online! Conectado como {bot.user}")
    print(f"📊 Conectado em {len(bot.guilds)} servidores") 
    print(f"👥 Servindo {len(set(bot.get_all_members()))} usuários únicos")
    print("🎮 Bot totalmente operacional!")
    sys.stdout.flush()  # Forçar flush
    
    logger.info(f"🤖 Kaori está online! Conectado como {bot.user}")
    logger.info(f"📊 Conectado em {len(bot.guilds)} servidores")
    logger.info("🎮 Bot totalmente operacional!")
    logger.info(f"👥 Servindo {len(set(bot.get_all_members()))} usuários únicos")

    # Log de reinício (sem enviar para Discord)
    logger.info(f"🚀 Kaori Online! Servidores: {len(bot.guilds)} | Usuários: {len(set(bot.get_all_members()))} | Latência: {round(bot.latency * 1000, 2)}ms")

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
            cleanup_inactive_messages.start()

            # Iniciar monitor de saúde
            asyncio.create_task(health_monitor())
            global last_heartbeat
            last_heartbeat = datetime.datetime.now()

            logger.info("✅ Background tasks e monitor de saúde iniciados")
        except Exception as e:
            logger.error(f"Erro ao iniciar background tasks: {e}")

        # Inicializar cargos de rank em todos os servidores
        try:
            for guild in bot.guilds:
                await ensure_rank_roles(guild)
                await organize_rank_roles(guild)
            logger.info("✅ Cargos de rank inicializados em todos os servidores")
        except Exception as e:
            logger.error(f"Erro ao inicializar cargos de rank: {e}")

    # Restaurar mensagens interativas após reinício
    await restore_interactive_messages()

    # Sistemas de proteção 24/7 removidos para economizar recursos

    # ============ SINCRONIZAR TODOS OS SLASH COMMANDS ============
    # Sincronizar slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"✅ {len(synced)} slash commands sincronizados")

        # Lista todos os comandos slash sincronizados
        slash_commands = [cmd.name for cmd in synced]
        logger.info(f"📋 Comandos slash disponíveis: {', '.join(slash_commands[:10])}...")
        logger.info(f"🚀 Total de comandos slash: {len(slash_commands)}")

        # Log detalhado dos primeiros comandos
        for cmd in synced[:15]:
            logger.info(f"   /{cmd.name} - {cmd.description}")
        if len(synced) > 15:
            logger.info(f"   ... e mais {len(synced) - 15} comandos!")

    except Exception as e:
        logger.error(f"❌ Erro ao sincronizar slash commands: {e}")

        # Tentar sincronizar novamente com delay
        try:
            await asyncio.sleep(2)
            synced = await bot.tree.sync()
            logger.info(f"✅ Sincronização em segunda tentativa: {len(synced)} comandos")
        except Exception as e2:
            logger.error(f"❌ Segunda tentativa falhou: {e2}")

    # Set initial status com retry
    try:
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"🚀 {len(bot.guilds)} servidores | {len(synced) if 'synced' in locals() else '60+'} slash commands!"
            )
        )
        logger.info("✅ Status inicial configurado")
    except Exception as e:
        logger.error(f"Erro ao configurar status: {e}")

    print("🔥 Kaori está online! Pronto para comandar!")
    print(f"✨ TODOS os {len(synced) if 'synced' in locals() else 'Muitos'} slash commands disponíveis!")
    print("📋 Use / no Discord para ver TODOS os comandos disponíveis!")
    print("🎯 Sistema dual: Use / ou RX - Ambos funcionam!")

    # ============ SISTEMA DE SCOREBOARD DA COPINHA ============

# Tabela para scoreboard da copinha
def init_copinha_scoreboard_table():
    """Inicializar tabela do scoreboard da copinha"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Tabela de scoreboard da copinha
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS copinha_scoreboard (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT,
                user_id BIGINT,
                username TEXT,
                points BIGINT DEFAULT 0,
                wins BIGINT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            
            # Tabela para configuração de canais do servidor
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS guild_channels (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT,
                channel_type TEXT,
                channel_id BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Tabelas do scoreboard da copinha criadas")
    except Exception as e:
        logger.error(f"Erro ao criar tabelas do scoreboard: {e}")

class CopinhaScoreboardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="🏆 Top 10", style=discord.ButtonStyle.primary, emoji="🏆")
    async def show_top10(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, username, points, wins 
                    FROM copinha_scoreboard 
                    WHERE guild_id = %s 
                    ORDER BY points DESC 
                    LIMIT 10
                ''', (interaction.guild.id,))
                results = cursor.fetchall()
                conn.close()

            if not results:
                embed = create_embed("🏆 Scoreboard Vazio", "Nenhum vencedor registrado ainda!", color=0xffaa00)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            scoreboard_text = ""
            medals = ["🥇", "🥈", "🥉"]
            
            for i, (user_id, username, points, wins) in enumerate(results):
                medal = medals[i] if i < 3 else f"{i+1}º"
                user = interaction.guild.get_member(user_id)
                display_name = user.display_name if user else username
                scoreboard_text += f"{medal} **{display_name}** - {points:,} pontos ({wins} vitórias)\n"

            embed = create_embed(
                "🏆 Top 10 - Scoreboard da Copinha",
                scoreboard_text,
                color=0xffd700
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Erro no top 10: {e}")
            await interaction.response.send_message("❌ Erro ao carregar ranking!", ephemeral=True)

    @discord.ui.button(label="➕ Adicionar Troféus", style=discord.ButtonStyle.success, emoji="➕")
    async def add_points(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Apenas staff pode usar este botão!", ephemeral=True)
            return
        
        view = PlayerSelectView(action='add', guild=interaction.guild)
        embed = create_embed(
            "➕ Adicionar Troféus",
            "Selecione um player para adicionar troféus:\n\n"
            "🔍 **Dica:** Use a busca abaixo para encontrar rapidamente entre os 300+ membros!",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="➖ Remover Troféus", style=discord.ButtonStyle.danger, emoji="➖")
    async def remove_points(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Apenas staff pode usar este botão!", ephemeral=True)
            return
        
        view = PlayerSelectView(action='remove', guild=interaction.guild)
        embed = create_embed(
            "➖ Remover Troféus",
            "Selecione um player para remover troféus:\n\n"
            "🔍 **Dica:** Use a busca abaixo para encontrar rapidamente entre os 300+ membros!",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🔄 Atualizar", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh_scoreboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            embed = create_embed(
                "🏆 Scoreboard da Copinha",
                "Sistema de pontuação dos vencedores das copinhas!\n\n"
                "**🎯 Como funciona:**\n"
                "• Vencedores ganham pontos automaticamente\n"
                "• Staff pode adicionar/remover pontos manualmente\n"
                "• Ranking atualizado em tempo real\n\n"
                "**🏆 Sistema de pontuação:**\n"
                "• O vencedor da copinha ganha 1 troféu\n"
                "• Sistema simples e justo para todos\n\n"
                "**💡 Use os botões abaixo para interagir:**",
                color=0x7289da
            )
            
            view = CopinhaScoreboardView()
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            logger.error(f"Erro ao atualizar: {e}")
            await interaction.response.send_message("❌ Erro ao atualizar!", ephemeral=True)

class PlayerSelectView(discord.ui.View):
    def __init__(self, action, guild):
        super().__init__(timeout=300)
        self.action = action  # 'add' ou 'remove'
        self.guild = guild
        self.selected_user = None
        self.search_term = ""
        self.update_player_select()

    def update_player_select(self):
        # Limpar componentes existentes
        self.clear_items()
        
        # Filtrar membros baseado no termo de busca
        members = []
        for member in self.guild.members:
            if not member.bot:  # Excluir bots
                if not self.search_term or self.search_term.lower() in member.display_name.lower():
                    members.append(member)
        
        # Limitar a 25 membros (limite do Discord)
        members = sorted(members, key=lambda m: m.display_name.lower())[:25]
        
        if members:
            # Select menu para escolher player
            select_options = []
            for member in members:
                # Verificar pontos atuais no scoreboard
                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT points, wins FROM copinha_scoreboard 
                        WHERE guild_id = %s AND user_id = %s
                    ''', (self.guild.id, member.id))
                    result = cursor.fetchone()
                    conn.close()
                
                current_points = result[0] if result else 0
                current_wins = result[1] if result else 0
                
                description = f"🏆 {current_points} troféus • {current_wins} vitórias"
                select_options.append(
                    discord.SelectOption(
                        label=member.display_name[:100],
                        value=str(member.id),
                        description=description[:100],
                        emoji="👤"
                    )
                )
            
            player_select = PlayerSelect(select_options, self.action)
            self.add_item(player_select)
        
        # Campo de busca
        search_button = discord.ui.Button(
            label=f"🔍 Buscar: '{self.search_term}'" if self.search_term else "🔍 Buscar Player",
            style=discord.ButtonStyle.secondary,
            custom_id="search_player"
        )
        search_button.callback = self.search_callback
        self.add_item(search_button)
        
        # Botão para limpar busca
        if self.search_term:
            clear_button = discord.ui.Button(
                label="🗑️ Limpar Busca",
                style=discord.ButtonStyle.secondary,
                custom_id="clear_search"
            )
            clear_button.callback = self.clear_search_callback
            self.add_item(clear_button)
        
        if not members:
            no_results_button = discord.ui.Button(
                label="❌ Nenhum resultado encontrado",
                style=discord.ButtonStyle.secondary,
                disabled=True
            )
            self.add_item(no_results_button)

    async def search_callback(self, interaction: discord.Interaction):
        modal = SearchModal(self)
        await interaction.response.send_modal(modal)

    async def clear_search_callback(self, interaction: discord.Interaction):
        self.search_term = ""
        self.update_player_select()
        
        embed = create_embed(
            f"{'➕ Adicionar Troféus' if self.action == 'add' else '➖ Remover Troféus'}",
            "Busca limpa! Selecione um player da lista:\n\n"
            f"🔍 **Mostrando:** Primeiros 25 membros em ordem alfabética",
            color=0x00ff00 if self.action == 'add' else 0xff0000
        )
        await interaction.response.edit_message(embed=embed, view=self)

class SearchModal(discord.ui.Modal):
    def __init__(self, parent_view):
        super().__init__(title="🔍 Buscar Player")
        self.parent_view = parent_view
        
        self.search_input = discord.ui.TextInput(
            label="Nome do Player",
            placeholder="Digite parte do nome do player...",
            required=True,
            max_length=50
        )
        self.add_item(self.search_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.parent_view.search_term = self.search_input.value.strip()
        self.parent_view.update_player_select()
        
        embed = create_embed(
            f"{'➕ Adicionar Troféus' if self.parent_view.action == 'add' else '➖ Remover Troféus'}",
            f"**🔍 Busca:** '{self.parent_view.search_term}'\n\n"
            "Selecione um player da lista filtrada:",
            color=0x00ff00 if self.parent_view.action == 'add' else 0xff0000
        )
        await interaction.response.edit_message(embed=embed, view=self.parent_view)

class PlayerSelect(discord.ui.Select):
    def __init__(self, options, action):
        super().__init__(
            placeholder=f"Escolha um player para {'adicionar' if action == 'add' else 'remover'} troféus...",
            options=options,
            custom_id="player_select"
        )
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        user_id = int(self.values[0])
        member = interaction.guild.get_member(user_id)
        
        if not member:
            await interaction.response.send_message("❌ Player não encontrado!", ephemeral=True)
            return
        
        # Buscar dados atuais
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT points, wins FROM copinha_scoreboard 
                WHERE guild_id = %s AND user_id = %s
            ''', (interaction.guild.id, user_id))
            result = cursor.fetchone()
            conn.close()
        
        current_points = result[0] if result else 0
        current_wins = result[1] if result else 0
        
        # Criar view de confirmação
        view = PointsConfirmView(member, self.action, current_points, current_wins)
        
        emoji = "➕" if self.action == 'add' else "➖"
        action_text = "adicionar" if self.action == 'add' else "remover"
        
        embed = create_embed(
            f"{emoji} {action_text.title()} Troféus - {member.display_name}",
            f"**👤 Player:** {member.mention}\n"
            f"**🏆 Troféus atuais:** {current_points}\n"
            f"**🎯 Vitórias:** {current_wins}\n\n"
            f"**Quantos troféus deseja {action_text}?**",
            color=0x00ff00 if self.action == 'add' else 0xff0000
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        await interaction.response.edit_message(embed=embed, view=view)

class PointsConfirmView(discord.ui.View):
    def __init__(self, member, action, current_points, current_wins):
        super().__init__(timeout=300)
        self.member = member
        self.action = action
        self.current_points = current_points
        self.current_wins = current_wins

    @discord.ui.button(label="1 🏆", style=discord.ButtonStyle.primary)
    async def one_point(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_points_change(interaction, 1)

    @discord.ui.button(label="2 🏆", style=discord.ButtonStyle.primary)
    async def two_points(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_points_change(interaction, 2)

    @discord.ui.button(label="5 🏆", style=discord.ButtonStyle.primary)
    async def five_points(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_points_change(interaction, 5)

    @discord.ui.button(label="10 🏆", style=discord.ButtonStyle.primary)
    async def ten_points(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_points_change(interaction, 10)

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_embed(
            "❌ Operação Cancelada",
            "Nenhuma alteração foi feita no scoreboard.",
            color=0x808080
        )
        await interaction.response.edit_message(embed=embed, view=None)

    async def handle_points_change(self, interaction: discord.Interaction, points):
        try:
            if self.action == 'add':
                # Adicionar pontos
                new_total = add_copinha_points(
                    interaction.guild.id, 
                    self.member.id, 
                    self.member.display_name, 
                    points, 
                    "adição manual por staff"
                )
                
                embed = create_embed(
                    "✅ Troféus Adicionados!",
                    f"**👤 Player:** {self.member.mention}\n"
                    f"**➕ Adicionado:** {points} 🏆\n"
                    f"**📊 Total atual:** {new_total} troféus\n"
                    f"**👑 Por:** {interaction.user.mention}",
                    color=0x00ff00
                )
            else:
                # Remover pontos
                if self.current_points < points:
                    embed = create_embed(
                        "❌ Erro!",
                        f"**{self.member.display_name}** tem apenas **{self.current_points}** troféus!\n"
                        f"Não é possível remover **{points}** troféus.",
                        color=0xff0000
                    )
                    await interaction.response.edit_message(embed=embed, view=None)
                    return
                
                new_points = max(0, self.current_points - points)
                
                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE copinha_scoreboard 
                        SET points = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE guild_id = %s AND user_id = %s
                    ''', (new_points, interaction.guild.id, self.member.id))
                    conn.commit()
                    conn.close()
                
                embed = create_embed(
                    "✅ Troféus Removidos!",
                    f"**👤 Player:** {self.member.mention}\n"
                    f"**➖ Removido:** {points} 🏆\n"
                    f"**📊 Total atual:** {new_points} troféus\n"
                    f"**👑 Por:** {interaction.user.mention}",
                    color=0xff6600
                )
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            logger.error(f"Erro ao modificar pontos: {e}")
            embed = create_embed(
                "❌ Erro!",
                "Ocorreu um erro ao modificar os troféus. Tente novamente.",
                color=0xff0000
            )
            await interaction.response.edit_message(embed=embed, view=None)

class AddPointsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="➕ Adicionar Pontos")
        
        self.user_input = discord.ui.TextInput(
            label="Usuário",
            placeholder="@usuário ou ID do usuário",
            required=True
        )
        
        self.points_input = discord.ui.TextInput(
            label="Pontos",
            placeholder="Quantidade de pontos para adicionar",
            required=True
        )
        
        self.reason_input = discord.ui.TextInput(
            label="Motivo",
            placeholder="Motivo da adição de pontos",
            required=False,
            default="Adição manual por staff"
        )
        
        self.add_item(self.user_input)
        self.add_item(self.points_input)
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parsear usuário
            user_input = self.user_input.value.strip()
            user = None
            
            if user_input.startswith('<@') and user_input.endswith('>'):
                user_id = int(user_input[2:-1].replace('!', ''))
                user = interaction.guild.get_member(user_id)
            elif user_input.isdigit():
                user = interaction.guild.get_member(int(user_input))
            else:
                # Buscar por nome
                user = discord.utils.find(lambda m: m.display_name.lower() == user_input.lower(), interaction.guild.members)
            
            if not user:
                await interaction.response.send_message("❌ Usuário não encontrado!", ephemeral=True)
                return
            
            points = int(self.points_input.value)
            if points <= 0:
                await interaction.response.send_message("❌ Pontos devem ser positivos!", ephemeral=True)
                return
            
            reason = self.reason_input.value or "Adição manual por staff"
            
            # Adicionar pontos
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Verificar se usuário já existe
                cursor.execute('''
                    SELECT points, wins FROM copinha_scoreboard 
                    WHERE guild_id = %s AND user_id = %s
                ''', (interaction.guild.id, user.id))
                result = cursor.fetchone()
                
                if result:
                    new_points = result[0] + points
                    cursor.execute('''
                        UPDATE copinha_scoreboard 
                        SET points = %s, username = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE guild_id = %s AND user_id = %s
                    ''', (new_points, user.display_name, interaction.guild.id, user.id))
                else:
                    cursor.execute('''
                        INSERT INTO copinha_scoreboard (guild_id, user_id, username, points, wins)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (interaction.guild.id, user.id, user.display_name, points, 0))
                    new_points = points
                
                conn.commit()
                conn.close()
            
            embed = create_embed(
                "✅ Pontos Adicionados!",
                f"**Usuário:** {user.mention}\n"
                f"**Pontos adicionados:** +{points:,}\n"
                f"**Novo total:** {new_points:,} pontos\n"
                f"**Motivo:** {reason}\n"
                f"**Staff:** {interaction.user.mention}",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed)
            
            # Notificar canal da copinha se configurado
            await notify_copinha_channel(interaction.guild, f"➕ {user.display_name} ganhou {points} pontos! (Total: {new_points})")
            
        except ValueError:
            await interaction.response.send_message("❌ Número de pontos inválido!", ephemeral=True)
        except Exception as e:
            logger.error(f"Erro ao adicionar pontos: {e}")
            await interaction.response.send_message("❌ Erro ao adicionar pontos!", ephemeral=True)

class RemovePointsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="➖ Remover Pontos")
        
        self.user_input = discord.ui.TextInput(
            label="Usuário",
            placeholder="@usuário ou ID do usuário",
            required=True
        )
        
        self.points_input = discord.ui.TextInput(
            label="Pontos",
            placeholder="Quantidade de pontos para remover",
            required=True
        )
        
        self.reason_input = discord.ui.TextInput(
            label="Motivo",
            placeholder="Motivo da remoção de pontos",
            required=False,
            default="Remoção manual por staff"
        )
        
        self.add_item(self.user_input)
        self.add_item(self.points_input)
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parsear usuário (mesmo código do AddPointsModal)
            user_input = self.user_input.value.strip()
            user = None
            
            if user_input.startswith('<@') and user_input.endswith('>'):
                user_id = int(user_input[2:-1].replace('!', ''))
                user = interaction.guild.get_member(user_id)
            elif user_input.isdigit():
                user = interaction.guild.get_member(int(user_input))
            else:
                user = discord.utils.find(lambda m: m.display_name.lower() == user_input.lower(), interaction.guild.members)
            
            if not user:
                await interaction.response.send_message("❌ Usuário não encontrado!", ephemeral=True)
                return
            
            points = int(self.points_input.value)
            if points <= 0:
                await interaction.response.send_message("❌ Pontos devem ser positivos!", ephemeral=True)
                return
            
            reason = self.reason_input.value or "Remoção manual por staff"
            
            # Remover pontos
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT points FROM copinha_scoreboard 
                    WHERE guild_id = %s AND user_id = %s
                ''', (interaction.guild.id, user.id))
                result = cursor.fetchone()
                
                if not result:
                    await interaction.response.send_message("❌ Usuário não está no scoreboard!", ephemeral=True)
                    return
                
                current_points = result[0]
                new_points = max(0, current_points - points)
                
                cursor.execute('''
                    UPDATE copinha_scoreboard 
                    SET points = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE guild_id = %s AND user_id = %s
                ''', (new_points, interaction.guild.id, user.id))
                
                conn.commit()
                conn.close()
            
            embed = create_embed(
                "✅ Pontos Removidos!",
                f"**Usuário:** {user.mention}\n"
                f"**Pontos removidos:** -{points:,}\n"
                f"**Novo total:** {new_points:,} pontos\n"
                f"**Motivo:** {reason}\n"
                f"**Staff:** {interaction.user.mention}",
                color=0xff6b6b
            )
            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            await interaction.response.send_message("❌ Número de pontos inválido!", ephemeral=True)
        except Exception as e:
            logger.error(f"Erro ao remover pontos: {e}")
            await interaction.response.send_message("❌ Erro ao remover pontos!", ephemeral=True)

class ChannelSelectView(discord.ui.View):
    def __init__(self, channel_type, channel_name):
        super().__init__(timeout=60)
        self.channel_type = channel_type
        self.channel_name = channel_name

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        placeholder="Escolha um canal...",
        channel_types=[discord.ChannelType.text, discord.ChannelType.news]
    )
    async def select_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        try:
            channel = select.values[0]
            
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Verificar se já existe configuração para este tipo
                cursor.execute('''
                    SELECT id FROM guild_channels 
                    WHERE guild_id = %s AND channel_type = %s
                ''', (interaction.guild.id, self.channel_type))
                existing = cursor.fetchone()
                
                if existing:
                    # Atualizar
                    cursor.execute('''
                        UPDATE guild_channels 
                        SET channel_id = %s 
                        WHERE guild_id = %s AND channel_type = %s
                    ''', (channel.id, interaction.guild.id, self.channel_type))
                else:
                    # Inserir novo
                    cursor.execute('''
                        INSERT INTO guild_channels (guild_id, channel_type, channel_id)
                        VALUES (%s, %s, %s)
                    ''', (interaction.guild.id, self.channel_type, channel.id))
                
                conn.commit()
                conn.close()
            
            embed = create_embed(
                "✅ Canal Configurado!",
                f"**{self.channel_name}** foi definido como: {channel.mention}",
                color=0x00ff00
            )
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            logger.error(f"Erro ao configurar canal: {e}")
            await interaction.response.send_message("❌ Erro ao configurar canal!", ephemeral=True)

async def notify_copinha_channel(guild, message):
    """Notificar canal da copinha sobre eventos"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT channel_id FROM guild_channels 
                WHERE guild_id = %s AND channel_type = %s
            ''', (guild.id, 'copinha'))
            result = cursor.fetchone()
            conn.close()
            
        if result:
            channel = guild.get_channel(result[0])
            if channel:
                embed = create_embed("🏆 Copinha - Atualização", message, color=0xffd700)
                await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Erro ao notificar canal da copinha: {e}")

def add_copinha_points(guild_id, user_id, username, points, phase="vitoria"):
    """Adicionar pontos automaticamente quando definir vencedor"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar se usuário já existe
            cursor.execute('''
                SELECT points, wins FROM copinha_scoreboard 
                WHERE guild_id = %s AND user_id = %s
            ''', (guild_id, user_id))
            result = cursor.fetchone()
            
            if result:
                new_points = result[0] + points
                new_wins = result[1] + 1
                cursor.execute('''
                    UPDATE copinha_scoreboard 
                    SET points = %s, wins = %s, username = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE guild_id = %s AND user_id = %s
                ''', (new_points, new_wins, username, guild_id, user_id))
            else:
                cursor.execute('''
                    INSERT INTO copinha_scoreboard (guild_id, user_id, username, points, wins)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (guild_id, user_id, username, points, 1))
                new_points = points
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ {points} pontos adicionados para {username} (fase: {phase})")
            return new_points
    except Exception as e:
        logger.error(f"Erro ao adicionar pontos automáticos: {e}")
        return 0

# ============ COMANDO ESPECIAL PARA TICKETS PERSISTENTE ============

async def create_persistent_ticket_message(ctx_or_interaction):
    """Criar mensagem de ticket persistente que sobrevive a redeploys"""
    try:
        # Determinar se é ctx tradicional ou interaction
        if hasattr(ctx_or_interaction, 'guild'):
            guild = ctx_or_interaction.guild
            channel = ctx_or_interaction.channel
            user = getattr(ctx_or_interaction, 'author', getattr(ctx_or_interaction, 'user', None))
        else:
            guild = ctx_or_interaction.guild
            channel = ctx_or_interaction.channel
            user = ctx_or_interaction.user

        embed = create_embed(
            "🎫 Sistema de Tickets - RXbot",
            """**Precisa de ajuda? Crie um ticket!**

**📋 Reaja com o emoji correspondente:**
🐛 - Bug/Erro no bot
💰 - Problema com economia  
⚖️ - Denúncia/Moderação
💡 - Sugestão/Ideia
❓ - Dúvida geral
🛠️ - Suporte técnico
👑 - Ticket especial (apenas Tier)

**⚡ Resposta rápida garantida!**
*Equipe de suporte estará com você em breve*""",
            color=0x00ff00
        )

        if hasattr(ctx_or_interaction, 'respond'):  # Slash command
            message = await ctx_or_interaction.respond(embed=embed)
            if hasattr(message, 'message'):
                message = message.message
        elif hasattr(ctx_or_interaction, 'send'):  # Traditional command
            message = await ctx_or_interaction.send(embed=embed)
        else:
            message = await channel.send(embed=embed)

        # Adicionar reações
        reactions = ["🐛", "💰", "⚖️", "💡", "❓", "🛠️", "👑"]
        for emoji in reactions:
            await message.add_reaction(emoji)

        # Salvar no banco para persistir
        save_interactive_message(
            message.id, 
            channel.id, 
            guild.id, 
            'ticket_creation',
            {'user': user.id if user else None}
        )

        # Salvar em memória também
        active_games[message.id] = {
            'type': 'ticket_creation',
            'channel_id': channel.id,
            'guild_id': guild.id,
            'user': user.id if user else None
        }

        logger.info(f"Mensagem de ticket persistente criada: {message.id}")
        return message

    except Exception as e:
        logger.error(f"Erro ao criar mensagem de ticket persistente: {e}")
        raise

# ============ COMANDOS COM PREFIXO RX (NÃO-SLASH) ============

@bot.command(name='escolhercanais', aliases=['configcanais'])
async def rx_escolher_canais(ctx):
    """Comando RX para escolher canais padrão do servidor"""
    try:
        if not ctx.author.guild_permissions.manage_channels:
            embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Gerenciar Canais'!", color=0xff0000)
            await ctx.send(embed=embed)
            return

        embed = create_embed(
            "⚙️ Configurar Canais do Servidor",
            "**Escolha qual tipo de canal deseja configurar:**\n\n"
            "🔔 **Avisos** - Para anúncios importantes\n"
            "⚔️ **X-Clan** - Para eventos entre clans\n"
            "📋 **Logs** - Para logs de moderação\n"
            "🏆 **Copinha** - Para eventos e scoreboards\n"
            "👋 **Boas-vindas** - Para dar boas-vindas\n\n"
            "**Clique nos botões abaixo para configurar:**",
            color=0x7289da
        )

        view = ConfigChannelsView()
        await ctx.send(embed=embed, view=view)

    except Exception as e:
        logger.error(f"Erro no comando escolhercanais: {e}")
        await ctx.send("❌ Erro ao carregar configurações de canais!")

class ConfigChannelsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="🔔 Avisos", style=discord.ButtonStyle.primary, emoji="🔔")
    async def config_avisos(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ChannelSelectView('avisos', 'Canal de Avisos')
        embed = create_embed("🔔 Configurar Canal de Avisos", "Selecione o canal para avisos importantes:", color=0x7289da)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="⚔️ X-Clan", style=discord.ButtonStyle.secondary, emoji="⚔️")
    async def config_xclan(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ChannelSelectView('xclan', 'Canal X-Clan')
        embed = create_embed("⚔️ Configurar Canal X-Clan", "Selecione o canal para eventos entre clans:", color=0x7289da)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="📋 Logs", style=discord.ButtonStyle.secondary, emoji="📋")
    async def config_logs(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ChannelSelectView('logs', 'Canal de Logs')
        embed = create_embed("📋 Configurar Canal de Logs", "Selecione o canal para logs de moderação:", color=0x7289da)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🏆 Copinha", style=discord.ButtonStyle.success, emoji="🏆")
    async def config_copinha(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ChannelSelectView('copinha', 'Canal da Copinha')
        embed = create_embed("🏆 Configurar Canal da Copinha", "Selecione o canal para eventos e scoreboards da copinha:", color=0x7289da)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="👋 Boas-vindas", style=discord.ButtonStyle.secondary, emoji="👋")
    async def config_welcome(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ChannelSelectView('welcome', 'Canal de Boas-vindas')
        embed = create_embed("👋 Configurar Canal de Boas-vindas", "Selecione o canal para dar boas-vindas:", color=0x7289da)
        await interaction.response.edit_message(embed=embed, view=view)

@bot.command(name='scorecup', aliases=['scorecopinha'])
async def rx_score_cup(ctx):
    """Comando RX para mostrar scoreboard da copinha"""
    try:
        embed = create_embed(
            "🏆 Scoreboard da Copinha",
            "Sistema de pontuação dos vencedores das copinhas!\n\n"
            "**🎯 Como funciona:**\n"
            "• Vencedores ganham pontos automaticamente\n"
            "• Staff pode adicionar/remover pontos manualmente\n"
            "• Ranking atualizado em tempo real\n\n"
            "**🏆 Sistema de pontuação:**\n"
            "• O vencedor da copinha ganha 1 troféu\n"
            "• Sistema simples e justo para todos\n\n"
            "**💡 Use os botões abaixo para interagir:**",
            color=0x7289da
        )
        
        view = CopinhaScoreboardView()
        await ctx.send(embed=embed, view=view)

    except Exception as e:
        logger.error(f"Erro no comando scorecup: {e}")
        await ctx.send("❌ Erro ao carregar scoreboard!")

@bot.tree.command(name="cuptop10", description="Ver top 10 do ranking das copinhas")
async def slash_cup_top10(interaction: discord.Interaction):
    """Slash command para mostrar top 10 do scoreboard das copinhas de forma organizada"""
    global_stats['commands_used'] += 1
    ctx = interaction
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, username, points, wins 
                FROM copinha_scoreboard 
                WHERE guild_id = %s 
                ORDER BY points DESC 
                LIMIT 10
            ''', (interaction.guild.id,))
            results = cursor.fetchall()
            conn.close()

        if not results:
            embed = create_embed(
                "🏆 Top 10 Copinhas", 
                "Nenhum vencedor registrado ainda!\n\nParticipe das copinhas para aparecer aqui! 🎮", 
                color=0xffaa00
            )
            await interaction.response.send_message(embed=embed)
            return

        # Criar texto organizado do ranking
        ranking_text = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for i, (user_id, username, points, wins) in enumerate(results):
            medal = medals[i] if i < 3 else f"**{i+1}º**"
            user = interaction.guild.get_member(user_id)
            display_name = user.display_name if user else username
            
            # Formatação bonita com troféus e vitórias
            if points == 1:
                trophies_text = "1 🏆"
            else:
                trophies_text = f"{points} 🏆" if points > 0 else "0 🏆"
            
            victories_text = f"{wins} vitórias" if wins != 1 else "1 vitória"
            
            ranking_text += f"{medal} **{display_name}**\n"
            ranking_text += f"   └ {trophies_text} • {victories_text}\n\n"

        embed = create_embed(
            "🏆 Top 10 - Campeões das Copinhas",
            f"**🎯 Os maiores campeões do servidor:**\n\n{ranking_text}"
            f"**🏅 Total de jogadores no ranking:** {len(results)}\n"
            f"**🎮 Participe das copinhas e apareça aqui!**",
            color=0xffd700
        )
        
        embed.set_footer(text="Use RXscoreCup para gerenciar o scoreboard")
        await interaction.response.send_message(embed=embed)

    except Exception as e:
        logger.error(f"Erro no comando cuptop10: {e}")
        await interaction.response.send_message("❌ Erro ao carregar ranking das copinhas!")

@bot.tree.command(name="rankcopas", description="Ativar sistema de ranking das copinhas (RXscoreCup)")
async def slash_rank_copas(interaction: discord.Interaction):
    """Comando slash para ativar o sistema completo de ranking das copinhas"""
    global_stats['commands_used'] += 1
    try:
        embed = create_embed(
            "🏆 Sistema de Ranking das Copinhas",
            "Sistema completo de pontuação dos vencedores das copinhas!\n\n"
            "**🎯 Como funciona:**\n"
            "• Vencedores ganham pontos automaticamente\n"
            "• Staff pode adicionar/remover pontos manualmente\n"
            "• Ranking atualizado em tempo real\n\n"
            "**🏆 Sistema de pontuação:**\n"
            "• O vencedor da copinha ganha 1 troféu\n"
            "• Sistema simples e justo para todos\n\n"
            "**💡 Use os botões abaixo para gerenciar o sistema:**",
            color=0x7289da
        )
        
        # Usar a mesma view que o comando RX original
        view = CopinhaScoreboardView()
        await interaction.response.send_message(embed=embed, view=view)

    except Exception as e:
        logger.error(f"Erro no comando rankcopas: {e}")
        await interaction.response.send_message("❌ Erro ao carregar sistema de ranking das copinhas!")

class EscolherCargoView(discord.ui.View):
    """View para seleção de cargos pelo usuário específico"""
    def __init__(self, authorized_user_id: int):
        super().__init__(timeout=300)
        self.authorized_user_id = authorized_user_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verificar se apenas o usuário autorizado pode usar os botões"""
        if interaction.user.id != self.authorized_user_id:
            embed = create_embed(
                "❌ Acesso Negado",
                "Estes botões são restritos a um usuário específico!",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="🎮 Gamer", style=discord.ButtonStyle.primary)
    async def cargo_gamer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "🎮 Gamer", 0x00ff00)
    
    @discord.ui.button(label="🎵 Músico", style=discord.ButtonStyle.primary)
    async def cargo_musico(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "🎵 Músico", 0x9b59b6)
    
    @discord.ui.button(label="🎨 Artista", style=discord.ButtonStyle.primary)
    async def cargo_artista(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "🎨 Artista", 0xe67e22)
    
    @discord.ui.button(label="💻 Programador", style=discord.ButtonStyle.primary)
    async def cargo_programador(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "💻 Programador", 0x3498db)
    
    @discord.ui.button(label="🎬 Streamer", style=discord.ButtonStyle.secondary)
    async def cargo_streamer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "🎬 Streamer", 0xff4500)  # Cor vermelho alaranjado
    
    @discord.ui.button(label="🔥 Membro VIP", style=discord.ButtonStyle.success)
    async def cargo_vip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "🔥 Membro VIP", 0xf1c40f)
    
    @discord.ui.button(label="🏆 Elite", style=discord.ButtonStyle.success)
    async def cargo_elite(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "🏆 Elite", 0xffd700)
    
    @discord.ui.button(label="❌ Remover Cargos", style=discord.ButtonStyle.danger)
    async def remover_cargos(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            member = interaction.user
            guild = interaction.guild
            
            # Verificar permissões do bot
            if not guild.me.guild_permissions.manage_roles:
                embed = create_embed(
                    "❌ Sem Permissões",
                    "O bot não possui permissão para gerenciar cargos!",
                    color=0xff0000
                )
                await safe_send_response(interaction, embed, ephemeral=True)
                return
            
            # Lista de cargos que podem ser removidos
            cargo_names = ["🎮 Gamer", "🎵 Músico", "🎨 Artista", "💻 Programador", 
                          "🎬 Streamer", "🔥 Membro VIP", "🏆 Elite"]
            
            roles_to_remove = []
            for cargo_name in cargo_names:
                role = discord.utils.get(guild.roles, name=cargo_name)
                if role and role in member.roles:
                    # Verificar hierarquia
                    if role.position < guild.me.top_role.position:
                        roles_to_remove.append(role)
            
            if roles_to_remove:
                try:
                    await member.remove_roles(*roles_to_remove, reason="Remoção de cargos via RXescolhercargo")
                    embed = create_embed(
                        "✅ Cargos Removidos",
                        f"Todos os cargos selecionáveis foram removidos de {member.mention}!",
                        color=0xff0000
                    )
                    logger.info(f"✅ Cargos removidos para {member.name} via RXescolhercargo: {[r.name for r in roles_to_remove]}")
                except discord.Forbidden:
                    embed = create_embed(
                        "❌ Erro de Permissão",
                        "Não foi possível remover alguns cargos. Verifique as permissões!",
                        color=0xff0000
                    )
            else:
                embed = create_embed(
                    "ℹ️ Nenhum Cargo",
                    "Você não possui cargos selecionáveis para remover.",
                    color=0xffa500
                )
            
            await safe_send_response(interaction, embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Erro ao remover cargos: {e}")
            embed = create_embed(
                "❌ Erro Interno",
                "Ocorreu um erro interno ao remover os cargos!",
                color=0xff0000
            )
            await safe_send_response(interaction, embed, ephemeral=True)
    
    async def assign_role(self, interaction: discord.Interaction, role_name: str, color: int):
        try:
            # Verificar se estamos em um servidor
            if not interaction.guild:
                embed = create_embed(
                    "❌ Contexto Inválido",
                    "Este comando só funciona dentro de servidores!",
                    color=0xff0000
                )
                await safe_send_response(interaction, embed, ephemeral=True)
                return
                
            member = interaction.user
            guild = interaction.guild
            
            # Verificar permissões do bot
            if not guild.me.guild_permissions.manage_roles:
                embed = create_embed(
                    "❌ Sem Permissões",
                    "O bot não possui permissão para gerenciar cargos!",
                    color=0xff0000
                )
                await safe_send_response(interaction, embed, ephemeral=True)
                return
            
            # Buscar ou criar o cargo
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                try:
                    # Criar o cargo se não existir
                    permissions = discord.Permissions(send_messages=True, read_messages=True, connect=True, speak=True)
                    role = await guild.create_role(
                        name=role_name,
                        color=discord.Color(color),
                        permissions=permissions,
                        mentionable=True,
                        hoist=False,
                        reason="Cargo criado automaticamente via RXescolhercargo"
                    )
                except discord.Forbidden:
                    embed = create_embed(
                        "❌ Erro de Permissão",
                        "Não foi possível criar o cargo. Verifique as permissões do bot!",
                        color=0xff0000
                    )
                    await safe_send_response(interaction, embed, ephemeral=True)
                    return
            
            # Verificar hierarquia de cargos
            if role.position >= guild.me.top_role.position:
                embed = create_embed(
                    "❌ Hierarquia de Cargo",
                    "O cargo está muito alto na hierarquia para ser gerenciado pelo bot!",
                    color=0xff0000
                )
                await safe_send_response(interaction, embed, ephemeral=True)
                return
            
            if role in member.roles:
                embed = create_embed(
                    "ℹ️ Cargo Já Atribuído",
                    f"Você já possui o cargo {role.mention}!",
                    color=0xffa500
                )
            else:
                await member.add_roles(role, reason="Cargo selecionado via RXescolhercargo")
                embed = create_embed(
                    "✅ Cargo Atribuído",
                    f"Cargo {role.mention} atribuído com sucesso para {member.mention}!",
                    color=0x00ff00
                )
                logger.info(f"✅ Cargo {role_name} atribuído para {member.name} via RXescolhercargo")
            
            # Usar safe_interaction_response e ephemeral para segurança
            await safe_send_response(interaction, embed, ephemeral=True)
            
        except discord.Forbidden:
            embed = create_embed(
                "❌ Erro de Permissão",
                "Não foi possível atribuir o cargo. Verifique as permissões!",
                color=0xff0000
            )
            await safe_send_response(interaction, embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Erro ao atribuir cargo {role_name}: {e}")
            embed = create_embed(
                "❌ Erro Interno",
                "Ocorreu um erro interno ao atribuir o cargo!",
                color=0xff0000
            )
            await safe_send_response(interaction, embed, ephemeral=True)

@bot.command(name='autouser', aliases=['adduser', 'authorizeuser'])
async def rx_authorize_user(ctx, user_id: int = None):
    """Comando para usuário privilegiado autorizar outros usuários para sistema de cargos"""
    global_stats['commands_used'] += 1
    
    try:
        # Verificar se é usuário privilegiado
        if not is_privileged_user(ctx.author.id):
            embed = create_embed(
                "❌ Acesso Negado",
                "Apenas usuários privilegiados podem autorizar outros usuários!",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        if user_id is None:
            embed = create_embed(
                "📝 Como Autorizar Usuários",
                f"**Para autorizar @skplays87:**\n"
                f"1. Digite `\@skplays87` no chat\n"
                f"2. Copie o ID que aparece\n"
                f"3. Use: `RXautouser [ID_COPIADO]`\n\n"
                f"**Usuários autorizados atuais:**\n"
                f"• <@{PRIVILEGED_USER_ID}> (privilegiado)\n"
                f"• {len(USUARIOS_AUTORIZADOS_CARGOS)} usuários na lista",
                color=0x7289da
            )
            await ctx.send(embed=embed)
            return
        
        if user_id in USUARIOS_AUTORIZADOS_CARGOS:
            embed = create_embed(
                "⚠️ Usuário já autorizado",
                f"<@{user_id}> já está na lista de usuários autorizados!",
                color=0xffaa00
            )
            await ctx.send(embed=embed)
            return
        
        # Adicionar usuário à lista
        USUARIOS_AUTORIZADOS_CARGOS.append(user_id)
        
        embed = create_embed(
            "✅ Usuário Autorizado",
            f"<@{user_id}> foi adicionado à lista de usuários autorizados!\n\n"
            f"**Agora este usuário pode:**\n"
            f"• Usar o comando `RXescolhercargo`\n"
            f"• Atribuir/remover cargos personalizados\n"
            f"• Acesso total ao sistema de cargos",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
        logger.info(f"✅ Usuário {user_id} autorizado por {ctx.author.name}")
        
    except Exception as e:
        logger.error(f"Erro no comando autouser: {e}")
        await ctx.send("❌ Erro ao autorizar usuário!")

@bot.command(name='escolhercargo', aliases=['cargo', 'cargos'])
async def rx_escolher_cargo(ctx):
    """Comando RX para usuário específico escolher um cargo"""
    global_stats['commands_used'] += 1
    
    try:
        # Verificar se é um usuário autorizado
        if not is_authorized_for_roles(ctx.author.id):
            embed = create_embed(
                "❌ Acesso Negado",
                "Este comando é restrito a um usuário específico!",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        embed = create_embed(
            "🎨 Escolher Cargo Personalizado",
            f"Olá {ctx.author.mention}! Escolha um cargo especial para você:\n\n"
            "**Cargos Disponíveis:**\n"
            "🎮 **Gamer** - Para os apaixonados por jogos\n"
            "🎵 **Músico** - Para os amantes da música\n"
            "🎨 **Artista** - Para os criativos\n"
            "💻 **Programador** - Para os desenvolvedores\n"
            "🎬 **Streamer** - Para os criadores de conteúdo\n"
            "🔥 **Membro VIP** - Cargo especial VIP\n"
            "🏆 **Elite** - Cargo de elite exclusivo\n\n"
            "**💡 Clique no botão do cargo desejado!**\n"
            "Use o botão vermelho para remover todos os cargos.",
            color=0x7289da
        )
        
        # Não enviar View publicamente - direcionar para slash command
        redirect_embed = create_embed(
            "💬 Use o Slash Command",
            f"Para maior privacidade, use o comando `/escolhercargo` ao invés do comando de texto.\n\n"
            f"✨ O slash command garante que apenas você veja as opções de cargo!",
            color=0x7289da
        )
        await ctx.send(embed=redirect_embed, delete_after=10)
        
    except Exception as e:
        logger.error(f"Erro no comando RXescolhercargo: {e}")
        await ctx.send("❌ Erro ao carregar sistema de cargos!")

# Comando slash para escolher cargo (privado)
@bot.tree.command(name="escolhercargo", description="Escolher um cargo personalizado (somente usuários autorizados)")
async def slash_escolher_cargo(interaction: discord.Interaction):
    """Slash command privado para escolher cargo"""
    try:
        global_stats['commands_used'] += 1
        
        # Verificar se é um usuário autorizado
        if not is_authorized_for_roles(interaction.user.id):
            embed = create_embed(
                "❌ Acesso Negado",
                "Este comando é restrito a usuários específicos!",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = create_embed(
            "🎨 Escolher Cargo Personalizado",
            f"Olá {interaction.user.mention}! Escolha um cargo especial para você:\n\n"
            "**Cargos Disponíveis:**\n"
            "🎮 **Gamer** - Para os apaixonados por jogos\n"
            "🎵 **Músico** - Para os amantes da música\n"
            "🎨 **Artista** - Para os criativos\n"
            "💻 **Programador** - Para os desenvolvedores\n"
            "🎬 **Streamer** - Para os criadores de conteúdo\n"
            "🔥 **Membro VIP** - Cargo especial VIP\n"
            "🏆 **Elite** - Cargo de elite exclusivo\n\n"
            "**💡 Clique no botão do cargo desejado!**\n"
            "Use o botão vermelho para remover todos os cargos.",
            color=0x7289da
        )
        
        view = EscolherCargoView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Erro no comando slash escolhercargo: {e}")
        embed = create_embed("❌ Erro", "Erro interno ao carregar sistema de cargos!", color=0xff0000)
        await safe_send_response(interaction, embed, ephemeral=True)

@bot.tree.command(name="desbugar", description="Cancelar uma copinha ativa")
async def slash_desbugar(interaction: discord.Interaction):
    """Comando slash para cancelar copinha ativa"""
    try:
        global_stats['commands_used'] += 1
        
        # Verificar permissões
        if not interaction.user.guild_permissions.manage_messages:
            embed = create_embed(
                "❌ Permissão negada", 
                "Você precisa da permissão 'Gerenciar Mensagens' para cancelar copinhas!", 
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Procurar copinhas ativas no servidor
        copinhas_ativas = []
        copinhas_em_andamento = []
        
        for message_id, game_data in list(active_games.items()):
            try:
                # Copinhas com inscrições abertas
                if (game_data.get('type') == 'copinha_join' and 
                    hasattr(game_data.get('view'), 'participants')):
                    view = game_data.get('view')
                    if len(view.participants) < view.max_players:
                        copinhas_ativas.append((message_id, view))
                
                # Copinhas em andamento (partidas)
                elif game_data.get('type') == 'match_winner':
                    copinhas_em_andamento.append(message_id)
            except:
                continue
        
        if not copinhas_ativas and not copinhas_em_andamento:
            embed = create_embed(
                "❌ Nenhuma copinha ativa", 
                "Não há copinhas para cancelar no momento!", 
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        canceladas = 0
        
        # Cancelar copinhas com inscrições
        for message_id, view in copinhas_ativas:
            try:
                # Remover do active_games
                if message_id in active_games:
                    del active_games[message_id]
                
                # Marcar mensagem interativa como inativa
                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE interactive_messages 
                        SET status = 'cancelled'
                        WHERE message_id = %s
                    ''', (message_id,))
                    conn.commit()
                    conn.close()
                
                canceladas += 1
                logger.info(f"Copinha {view.title} cancelada por {interaction.user.display_name}")
                
            except Exception as e:
                logger.error(f"Erro ao cancelar copinha {message_id}: {e}")

        # Cancelar partidas em andamento
        partidas_canceladas = 0
        for message_id in copinhas_em_andamento:
            try:
                # Remover do active_games
                if message_id in active_games:
                    game_data = active_games[message_id]
                    copinha_id = game_data.get('data', {}).get('copinha_id')
                    del active_games[message_id]
                
                # Marcar mensagem interativa como cancelada
                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE interactive_messages 
                        SET status = 'cancelled'
                        WHERE message_id = %s
                    ''', (message_id,))
                    
                    # Marcar copinha como cancelada se tiver
                    if copinha_id:
                        cursor.execute('''
                            UPDATE copinhas 
                            SET status = 'cancelled'
                            WHERE id = %s
                        ''', (copinha_id,))
                    
                    conn.commit()
                    conn.close()
                
                partidas_canceladas += 1
                
            except Exception as e:
                logger.error(f"Erro ao cancelar partida {message_id}: {e}")

        # Resposta de sucesso
        total_canceladas = canceladas + partidas_canceladas
        
        if total_canceladas > 0:
            embed = create_embed(
                "✅ Copinhas canceladas!", 
                f"**{canceladas}** copinhas com inscrições e **{partidas_canceladas}** partidas em andamento foram canceladas.\n\n"
                f"🧹 **Total:** {total_canceladas} itens cancelados\n"
                f"🔄 Use `/copinha` para criar uma nova!",
                color=0x00ff00
            )
        else:
            embed = create_embed(
                "⚠️ Nenhuma copinha cancelada", 
                "Não foi possível cancelar nenhuma copinha. Tente novamente!",
                color=0xffaa00
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        logger.error(f"Erro no comando desbugar: {e}")
        embed = create_embed("❌ Erro", "Erro interno! Tente novamente.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ============ TODOS OS SLASH COMMANDS - MAIS DE 300 COMANDOS ============

# SLASH COMMANDS - ECONOMIA
# (Duplicatas removidas - comandos já definidos acima)

@bot.tree.command(name="comprar", description="Comprar item da loja")
async def slash_comprar(interaction: discord.Interaction, item_id: int):
    """Slash command para comprar"""
    try:
        pass
    except (discord.errors.InteractionResponded, discord.errors.NotFound):
        # Interaction already handled or expired
        return

    if item_id not in LOJA_ITENS:
        embed = create_embed("❌ Item não encontrado", "Use `/loja` para ver itens disponíveis", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    item = LOJA_ITENS[item_id]
    user_data = get_user_data(interaction.user.id)

    if not user_data:
        update_user_data(interaction.user.id)
        user_data = get_user_data(interaction.user.id)

    coins = user_data[1]

    if coins < item['preco']:
        embed = create_embed(
            "💸 Dinheiro insuficiente",
            f"Você precisa de **{item['preco']:,} moedas** para comprar **{item['nome']}**!\n"
            f"Você tem apenas **{coins:,} moedas**.",
            color=0xff0000
        )
        await safe_send_response(interaction, embed=embed)
        return

    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            new_coins = coins - item['preco']
            cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (new_coins, interaction.user.id))

            cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (interaction.user.id,))
            inventory_data = cursor.fetchone()[0]
            inventory = json.loads(inventory_data) if inventory_data else {}

            if str(item_id) in inventory:
                inventory[str(item_id)] += 1
            else:
                inventory[str(item_id)] = 1

            cursor.execute('UPDATE users SET inventory = %s WHERE user_id = %s', (json.dumps(inventory), interaction.user.id))

            cursor.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (%s, %s, %s, %s, %s)
            ''', (interaction.user.id, interaction.guild.id, 'compra', -item['preco'], f"Comprou {item['nome']}"))

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
        await safe_send_response(interaction, embed=embed)

    except Exception as e:
        logger.error(f"Erro na compra: {e}")
        embed = create_embed("❌ Erro", "Erro ao processar compra!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)



@bot.tree.command(name="presentear", description="Presentear item para outro usuário")
async def slash_presentear(interaction: discord.Interaction, usuario: discord.Member, item_id: int, quantidade: int = 1):
    """Slash command para presentear item"""


    if quantidade <= 0:
        embed = create_embed("❌ Quantidade inválida", "Use quantidades positivas!", color=0xff0000)
        await safe_send_response(interaction, embed=embed, ephemeral=True)
        return

    if usuario == interaction.user:
        embed = create_embed("❌ Impossível", "Você não pode dar itens para si mesmo!", color=0xff0000)
        await safe_send_response(interaction, embed=embed, ephemeral=True)
        return

    if usuario.bot:
        embed = create_embed("❌ Impossível", "Você não pode dar itens para bots!", color=0xff0000)
        await safe_send_response(interaction, embed=embed, ephemeral=True)
        return

    if item_id not in LOJA_ITENS:
        embed = create_embed("❌ Item inválido", "Este item não existe!", color=0xff0000)
        await safe_send_response(interaction, embed=embed, ephemeral=True)
        return

    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (interaction.user.id,))
            sender_result = cursor.fetchone()

            if not sender_result:
                conn.close()
                embed = create_embed("❌ Sem dados", "Você não tem dados no sistema!", color=0xff0000)
                await safe_send_response(interaction, embed=embed, ephemeral=True)
                return

            sender_inventory_data = sender_result[0]
            sender_inventory = json.loads(sender_inventory_data) if sender_inventory_data else {}

            if str(item_id) not in sender_inventory or sender_inventory[str(item_id)] < quantidade:
                item_name = LOJA_ITENS[item_id]['nome']
                conn.close()
                embed = create_embed(
                    "❌ Item insuficiente",
                    f"Você não tem {quantidade}x **{item_name}** suficientes!\n"
                    f"Você tem apenas: {sender_inventory.get(str(item_id), 0)}",
                    color=0xff0000
                )
                await safe_send_response(interaction, embed=embed, ephemeral=True)
                return

            cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (usuario.id,))
            receiver_result = cursor.fetchone()

            if not receiver_result:
                cursor.execute('INSERT INTO users (user_id) VALUES (%s)', (usuario.id,))
                receiver_inventory = {}
            else:
                receiver_inventory_data = receiver_result[0]
                receiver_inventory = json.loads(receiver_inventory_data) if receiver_inventory_data else {}

            item = LOJA_ITENS[item_id]

            sender_inventory[str(item_id)] -= quantidade
            if sender_inventory[str(item_id)] <= 0:
                del sender_inventory[str(item_id)]

            if str(item_id) in receiver_inventory:
                receiver_inventory[str(item_id)] += quantidade
            else:
                receiver_inventory[str(item_id)] = quantidade

            cursor.execute('UPDATE users SET inventory = %s WHERE user_id = %s',
                          (json.dumps(sender_inventory), interaction.user.id))
            cursor.execute('UPDATE users SET inventory = %s WHERE user_id = %s',
                          (json.dumps(receiver_inventory), usuario.id))

            conn.commit()
            conn.close()

        embed = create_embed(
            "🎁 Item Presenteado!",
            f"**{item['emoji']} {item['nome']}**\n"
            f"**Quantidade:** {quantidade}x\n"
            f"**De:** {interaction.user.mention}\n"
            f"**Para:** {usuario.mention}\n\n"
            f"**Descrição:** {item['descricao']}\n"
            f"Item transferido com sucesso!",
            color=0x00ff00
        )
        await safe_send_response(interaction, embed=embed)

        try:
            dm_embed = create_embed(
                "🎁 Presente Recebido!",
                f"Você recebeu **{quantidade}x {item['emoji']} {item['nome']}** de {interaction.user.mention}!\n\n"
                f"**Descrição:** {item['descricao']}\n"
                f"Use `/inventario` para ver seus itens!\n"
                f"Use `/usar {item_id}` para usar o item!",
                color=0x00ff00
            )
            await usuario.send(embed=dm_embed)
        except:
            pass

    except Exception as e:
        logger.error(f"Erro ao presentear item: {e}")
        embed = create_embed("❌ Erro", f"Erro ao presentear item: {str(e)[:100]}", color=0xff0000)
        await safe_send_response(interaction, embed=embed, ephemeral=True)

@bot.tree.command(name="daritem", description="Dar item para outro usuário")
async def slash_daritem(interaction: discord.Interaction, usuario: discord.Member, item_id: int, quantidade: int = 1):
    """Slash command para dar item"""


    if quantidade <= 0:
        embed = create_embed("❌ Quantidade inválida", "Use quantidades positivas!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    if usuario == interaction.user:
        embed = create_embed("❌ Impossível", "Você não pode dar itens para si mesmo!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    if usuario.bot:
        embed = create_embed("❌ Impossível", "Você não pode dar itens para bots!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    if item_id not in LOJA_ITENS:
        embed = create_embed("❌ Item inválido", "Este item não existe!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (interaction.user.id,))
            sender_result = cursor.fetchone()

            if not sender_result:
                conn.close()
                embed = create_embed("❌ Sem dados", "Você não tem dados no sistema!", color=0xff0000)
                await safe_send_response(interaction, embed=embed)
                return

            sender_inventory_data = sender_result[0]
            sender_inventory = json.loads(sender_inventory_data) if sender_inventory_data else {}

            if str(item_id) not in sender_inventory or sender_inventory[str(item_id)] < quantidade:
                item_name = LOJA_ITENS[item_id]['nome']
                conn.close()
                embed = create_embed(
                    "❌ Item insuficiente",
                    f"Você não tem {quantidade}x **{item_name}** suficientes!\n"
                    f"Você tem apenas: {sender_inventory.get(str(item_id), 0)}",
                    color=0xff0000
                )
                await safe_send_response(interaction, embed=embed)
                return

            cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (usuario.id,))
            receiver_result = cursor.fetchone()

            if not receiver_result:
                cursor.execute('INSERT INTO users (user_id) VALUES (%s)', (usuario.id,))
                receiver_inventory = {}
            else:
                receiver_inventory_data = receiver_result[0]
                receiver_inventory = json.loads(receiver_inventory_data) if receiver_inventory_data else {}

            item = LOJA_ITENS[item_id]

            sender_inventory[str(item_id)] -= quantidade
            if sender_inventory[str(item_id)] <= 0:
                del sender_inventory[str(item_id)]

            if str(item_id) in receiver_inventory:
                receiver_inventory[str(item_id)] += quantidade
            else:
                receiver_inventory[str(item_id)] = quantidade

            cursor.execute('UPDATE users SET inventory = %s WHERE user_id = %s',
                          (json.dumps(sender_inventory), interaction.user.id))
            cursor.execute('UPDATE users SET inventory = %s WHERE user_id = %s',
                          (json.dumps(receiver_inventory), usuario.id))

            conn.commit()
            conn.close()

        embed = create_embed(
            "✅ Item Transferido!",
            f"**{item['emoji']} {item['nome']}**\n"
            f"**Quantidade:** {quantidade}x\n"
            f"**De:** {interaction.user.mention}\n"
            f"**Para:** {usuario.mention}\n\n"
            f"Item transferido com sucesso!",
            color=0x00ff00
        )
        await safe_send_response(interaction, embed=embed)

        try:
            dm_embed = create_embed(
                "🎁 Item Recebido!",
                f"Você recebeu **{quantidade}x {item['emoji']} {item['nome']}** de {interaction.user.mention}!\n\n"
                f"**Descrição:** {item['descricao']}\n"
                f"Use `/inventario` para ver seus itens!",
                color=0x00ff00
            )
            await usuario.send(embed=dm_embed)
        except:
            pass

    except Exception as e:
        logger.error(f"Erro ao transferir item: {e}")
        embed = create_embed("❌ Erro", f"Erro ao transferir item: {str(e)[:100]}", color=0xff0000)
        await safe_send_response(interaction, embed=embed)

@bot.tree.command(name="efeitos", description="Ver buffs e efeitos ativos")
async def slash_efeitos(interaction: discord.Interaction, usuario: discord.Member = None):
    """Slash command para efeitos"""


    target = usuario or interaction.user
    user_data = get_user_data(target.id)

    if not user_data:
        embed = create_embed("❌ Dados não encontrados", f"{target.display_name} não está no sistema!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    settings_data = user_data[11]
    settings = json.loads(settings_data) if settings_data else {}

    efeitos_ativos = []
    current_time = datetime.datetime.now().timestamp()

    xp_boost_end = settings.get('xp_boost', 0)
    if xp_boost_end > current_time:
        tempo_restante = int(xp_boost_end - current_time)
        efeitos_ativos.append(f"📈 **Boost de XP:** XP dobrado por {format_time(tempo_restante)}")

    vip_salary_end = settings.get('vip_salary', 0)
    if vip_salary_end > current_time:
        dias_restantes = int((vip_salary_end - current_time) / 86400)
        efeitos_ativos.append(f"💼 **Salário VIP:** +50% em trabalhos por {dias_restantes} dias")

    priority_tickets = settings.get('priority_tickets', 0)
    if priority_tickets > 0:
        efeitos_ativos.append(f"🎫 **Tickets Prioritários:** {priority_tickets} usos disponíveis")

    if not efeitos_ativos:
        embed = create_embed(
            f"✨ Efeitos de {target.display_name}",
            "**Nenhum efeito ativo no momento**\n\n"
            "💡 **Como obter efeitos:**\n"
            "• Compre itens na `/loja`\n"
            "• Use itens especiais como Boost de XP\n"
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
    await safe_send_response(interaction, embed=embed)

@bot.tree.command(name="depositar", description="Depositar dinheiro no banco")
async def slash_depositar(interaction: discord.Interaction, valor: int):
    """Slash command para depositar"""


    if valor <= 0:
        embed = create_embed("❌ Valor inválido", "Use valores positivos!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    user_data = get_user_data(interaction.user.id)
    if not user_data:
        update_user_data(interaction.user.id)
        user_data = get_user_data(interaction.user.id)

    coins, bank = user_data[1], user_data[5]

    if coins < valor:
        embed = create_embed(
            "💸 Dinheiro insuficiente",
            f"Você só tem **{coins:,} moedas** na carteira!",
            color=0xff0000
        )
        await safe_send_response(interaction, embed=embed)
        return

    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = %s, bank = %s WHERE user_id = %s',
                          (coins - valor, bank + valor, interaction.user.id))
            conn.commit()
            conn.close()

        embed = create_embed(
            "🏦 Depósito realizado!",
            f"**Valor depositado:** {valor:,} moedas\n"
            f"**Carteira:** {coins - valor:,} moedas\n"
            f"**Banco:** {bank + valor:,} moedas\n"
            f"**Total:** {(coins - valor) + (bank + valor):,} moedas",
            color=0x00ff00
        )
        await safe_send_response(interaction, embed=embed)

    except Exception as e:
        logger.error(f"Erro no depósito: {e}")
        embed = create_embed("❌ Erro", "Erro ao depositar!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)

@bot.tree.command(name="sacar", description="Sacar dinheiro do banco")
async def slash_sacar(interaction: discord.Interaction, valor: int):
    """Slash command para sacar"""


    if valor <= 0:
        embed = create_embed("❌ Valor inválido", "Use valores positivos!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    user_data = get_user_data(interaction.user.id)
    if not user_data:
        update_user_data(interaction.user.id)
        user_data = get_user_data(interaction.user.id)

    coins, bank = user_data[1], user_data[5]

    if bank < valor:
        embed = create_embed(
            "🏦 Saldo insuficiente no banco",
            f"Você só tem **{bank:,} moedas** no banco!",
            color=0xff0000
        )
        await safe_send_response(interaction, embed=embed)
        return

    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = %s, bank = %s WHERE user_id = %s',
                          (coins + valor, bank - valor, interaction.user.id))
            conn.commit()
            conn.close()

        embed = create_embed(
            "💰 Saque realizado!",
            f"**Valor sacado:** {valor:,} moedas\n"
            f"**Carteira:** {coins + valor:,} moedas\n"
            f"**Banco:** {bank - valor:,} moedas\n"
            f"**Total:** {(coins + valor) + (bank - valor):,} moedas",
            color=0x00ff00
        )
        await safe_send_response(interaction, embed=embed)

    except Exception as e:
        logger.error(f"Erro no saque: {e}")
        embed = create_embed("❌ Erro", "Erro ao sacar!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)

# SLASH COMMANDS - UTILIDADES
@bot.tree.command(name="lembrete", description="Criar um lembrete")
async def slash_lembrete(interaction: discord.Interaction, tempo: str, texto: str):
    """Slash command para lembrete"""


    # Parse do tempo
    time_units = {'m': 60, 's': 1, 'h': 3600, 'd': 86400}
    unit = tempo[-1].lower()

    if unit not in time_units:
        embed = create_embed("❌ Tempo inválido", "Use: s (segundos), m (minutos), h (horas), d (dias)", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    try:
        amount = int(tempo[:-1])
        seconds = amount * time_units[unit]
        remind_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
    except ValueError:
        embed = create_embed("❌ Tempo inválido", "Use números válidos: 30m, 2h, 1d", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO reminders (user_id, guild_id, channel_id, reminder_text, remind_time)
                VALUES (%s, %s, %s, %s, %s)
            ''', (interaction.user.id, interaction.guild.id, interaction.channel.id, texto, remind_time))
            conn.commit()
            conn.close()

        embed = create_embed(
            "⏰ Lembrete Criado!",
            f"**Texto:** {texto}\n"
            f"**Tempo:** {tempo}\n"
            f"**Quando:** <t:{int(remind_time.timestamp())}:R>\n\n"
            f"Vou te lembrar em {tempo}!",
            color=0x00ff00
        )
        await safe_send_response(interaction, embed=embed)

    except Exception as e:
        logger.error(f"Erro ao criar lembrete: {e}")
        embed = create_embed("❌ Erro", "Erro ao criar lembrete!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)

@bot.tree.command(name="enquete", description="Criar uma enquete")
async def slash_enquete(interaction: discord.Interaction, pergunta: str):
    """Slash command para enquete"""


    embed = create_embed(
        "📊 Enquete",
        f"**{pergunta}**\n\n✅ - Sim\n❌ - Não",
        color=0x7289da
    )
    embed.set_footer(text=f"Enquete criada por {interaction.user.display_name}")

    message = await safe_send_response(interaction, embed=embed)
    await message.add_reaction("✅")
    await message.add_reaction("❌")

@bot.tree.command(name="base64", description="Converter texto para base64")
async def slash_base64(interaction: discord.Interaction, texto: str):
    """Slash command para base64"""


    try:
        encoded = base64.b64encode(texto.encode('utf-8')).decode('utf-8')
        embed = create_embed(
            "🔐 Codificação Base64",
            f"**Texto original:** {texto}\n**Base64:** `{encoded}`",
            color=0x00ff00
        )
        await safe_send_response(interaction, embed=embed)
    except Exception as e:
        embed = create_embed("❌ Erro", f"Erro ao codificar: {e}", color=0xff0000)
        await safe_send_response(interaction, embed=embed)

# COMANDO TEMPORARIAMENTE DESABILITADO PARA FICAR DENTRO DO LIMITE DE 100 SLASH COMMANDS
# @bot.tree.command(name="password", description="Gerar senha segura")
async def slash_password(interaction: discord.Interaction, tamanho: int = 12):
    """Slash command para password"""


    if tamanho < 4 or tamanho > 50:
        embed = create_embed("❌ Tamanho inválido", "Use entre 4 e 50 caracteres", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
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

        try:
            await interaction.user.send(embed=embed)
            public_embed = create_embed(
                "✅ Senha enviada!",
                f"Sua senha de {tamanho} caracteres foi enviada por DM para segurança!",
                color=0x00ff00
            )
            await interaction.followup.send(embed=public_embed)
        except:
            await safe_send_response(interaction, embed=embed)

    except Exception as e:
        embed = create_embed("❌ Erro", f"Erro ao gerar senha: {e}", color=0xff0000)
        await safe_send_response(interaction, embed=embed)

@bot.tree.command(name="settitle", description="Definir título personalizado")
async def slash_settitle(interaction: discord.Interaction, titulo: str):
    """Slash command para settitle"""


    if len(titulo) > 30:
        embed = create_embed("❌ Título muito longo", "Use no máximo 30 caracteres", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    user_data = get_user_data(interaction.user.id)
    if not user_data:
        embed = create_embed("❌ Dados não encontrados", "Você não tem dados no sistema!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    settings_data = user_data[11]
    settings = json.loads(settings_data) if settings_data else {}

    if not settings.get('custom_title_available', False):
        embed = create_embed(
            "❌ Sem permissão",
            "Você precisa comprar o item **Título Personalizado** na loja!\nUse `/loja` para ver.",
            color=0xff0000
        )
        await safe_send_response(interaction, embed=embed)
        return

    settings['custom_title'] = titulo
    settings['custom_title_available'] = False  # Consumir o item

    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET settings = %s WHERE user_id = %s', (json.dumps(settings), interaction.user.id))
            conn.commit()
            conn.close()

        embed = create_embed(
            "👑 Título Definido!",
            f"Seu novo título personalizado: **{titulo}**\n\n"
            f"Agora aparecerá em seu perfil e rank!",
            color=0xffd700
        )
        await safe_send_response(interaction, embed=embed)

    except Exception as e:
        logger.error(f"Erro ao definir título: {e}")
        embed = create_embed("❌ Erro", "Erro ao definir título!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)

# SLASH COMMANDS - INFORMAÇÕES
@bot.tree.command(name="avatar", description="Ver avatar de um usuário")
async def slash_avatar(interaction: discord.Interaction, usuario: discord.Member = None):
    """Slash command para avatar"""


    target = usuario or interaction.user

    embed = create_embed(
        f"🖼️ Avatar de {target.display_name}",
        f"[Clique aqui para ver em alta resolução]({target.avatar.url if target.avatar else target.default_avatar.url}?size=1024)",
        color=0x7289da
    )
    embed.set_image(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await safe_send_response(interaction, embed=embed)

@bot.tree.command(name="serverinfo", description="Informações do servidor")
async def slash_serverinfo(interaction: discord.Interaction):
    """Slash command para serverinfo"""


    guild = interaction.guild

    embed = create_embed(
        f"🛡️ Informações do {guild.name}",
        f"""**👑 Dono:** {guild.owner.mention if guild.owner else 'Desconhecido'}
**📅 Criado em:** <t:{int(guild.created_at.timestamp())}:F>
**👥 Membros:** {guild.member_count:,}
**📁 Canais:** {len(guild.channels)}
**🎭 Cargos:** {len(guild.roles)}
**😎 Emojis:** {len(guild.emojis)}
**🔐 Nível de verificação:** {guild.verification_level.name.title()}
**🛡️ Filtro de conteúdo:** {guild.explicit_content_filter.name.title()}

**📊 ID do servidor:** {guild.id}""",
        color=0x7289da
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    await safe_send_response(interaction, embed=embed)

@bot.tree.command(name="userinfo", description="Informações detalhadas de um usuário")
async def slash_userinfo(interaction: discord.Interaction, usuario: discord.Member = None):
    """Slash command para userinfo"""


    target = usuario or interaction.user

    status_emoji = {
        discord.Status.online: "🟢",
        discord.Status.idle: "🟡", 
        discord.Status.dnd: "🔴",
        discord.Status.offline: "⚫"
    }

    embed = create_embed(
        f"👤 Info de {target.display_name}",
        f"""**📛 Nome:** {target.name}#{target.discriminator}
**🎭 Apelido:** {target.display_name}
**🆔 ID:** {target.id}
**📅 Conta criada:** <t:{int(target.created_at.timestamp())}:R>
**📥 Entrou no servidor:** <t:{int(target.joined_at.timestamp())}:R>
**📊 Status:** {status_emoji.get(target.status, '❓')} {target.status.name.title()}

**🎭 Cargos ({len(target.roles)-1}):**
{' '.join([role.mention for role in target.roles[1:6]])}{'...' if len(target.roles) > 6 else ''}

**🏆 Cargo mais alto:** {target.top_role.mention}
**🔐 Permissões:** {'Admin' if target.guild_permissions.administrator else 'Membro'}""",
        color=target.color if target.color != discord.Color.default() else 0x7289da
    )

    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await safe_send_response(interaction, embed=embed)

@bot.tree.command(name="version", description="Informações da versão do bot")
async def slash_version(interaction: discord.Interaction):
    """Slash command para version"""


    embed = create_embed(
        "🤖 RXbot - Informações de Versão",
        f"""**🔖 Versão:** 3.0.0 (Slash Commands Completa)
**📅 Última atualização:** Janeiro 2025
**🐍 Python:** {platform.python_version()}
**📦 Discord.py:** {discord.__version__}
**💻 Plataforma:** {platform.system()} {platform.release()}

**🆕 Novidades desta versão:**
• ✅ TODOS os comandos agora têm slash commands
• ✅ Mais de 300 comandos disponíveis via /
• ✅ Prefixo RX mantido para compatibilidade
• ✅ Interface moderna e intuitiva
• ✅ Sistema dual: slash + prefixo

**📊 Estatísticas:**
• Uptime: {format_time(int((datetime.datetime.now() - global_stats['uptime_start']).total_seconds()))}
• Comandos: 300+ disponíveis via / e RX
• Sistemas: Tickets, Economia, Ranks, IA""",
        color=0x00ff00
    )

    await safe_send_response(interaction, embed=embed)

@bot.tree.command(name="estatisticas_bot", description="Estatísticas do bot")
async def slash_estatisticas_bot(interaction: discord.Interaction):
    """Slash command para stats"""


    uptime = datetime.datetime.now() - global_stats['uptime_start']

    embed = create_embed(
        "📊 Estatísticas do RXbot",
        f"""**⏱️ Uptime:** {format_time(int(uptime.total_seconds()))}
**🏓 Latência:** {round(bot.latency * 1000, 2)}ms
**🏛️ Servidores:** {len(bot.guilds)}
**👥 Usuários:** {len(set(bot.get_all_members()))}
**📡 Canais:** {len(list(bot.get_all_channels()))}

**📈 Uso:**
• Comandos executados: {global_stats['commands_used']:,}
• Mensagens processadas: {global_stats['messages_processed']:,}

**💾 Sistema:**
• Comandos slash: 300+
• Comandos prefixo: 300+
• Sistema dual completo
• Database SQLite ativo""",
        color=0x7289da
    )

    await safe_send_response(interaction, embed=embed)

# SLASH COMMANDS - MODERAÇÃO
@bot.tree.command(name="clear", description="Limpar mensagens do canal")
async def slash_clear(interaction: discord.Interaction, quantidade: int = 10):
    """Slash command para clear"""
    try:
        # Verificar permissões
        if not interaction.user.guild_permissions.manage_messages:
            embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Gerenciar Mensagens'!", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if quantidade < 1 or quantidade > 100:
            embed = create_embed("❌ Quantidade inválida", "Use entre 1 e 100 mensagens", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Verificar se o bot tem permissões no canal
        bot_member = interaction.guild.me if interaction.guild else None
        if not bot_member or not interaction.channel.permissions_for(bot_member).manage_messages:
            embed = create_embed("❌ Bot sem permissão", "O bot não tem permissão para gerenciar mensagens neste canal!", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Responder primeiro para evitar timeout
        await interaction.response.send_message(f"🧹 Limpando {quantidade} mensagens...", ephemeral=True)

        # Fazer a limpeza
        deleted = await interaction.channel.purge(limit=quantidade, check=lambda m: m != interaction.response._parent)

        # Enviar confirmação no canal
        embed = create_embed(
            "🧹 Limpeza Concluída",
            f"**{len(deleted)} mensagens foram deletadas!**\n"
            f"**Moderador:** {interaction.user.mention}\n"
            f"**Canal:** {interaction.channel.mention}",
            color=0x00ff00
        )
        
        confirmation_msg = await interaction.channel.send(embed=embed)
        
        # Deletar a mensagem de confirmação após 5 segundos
        await asyncio.sleep(5)
        try:
            await confirmation_msg.delete()
        except:
            pass

    except discord.Forbidden:
        embed = create_embed("❌ Sem permissão", "O bot não tem permissão para deletar mensagens!", color=0xff0000)
        try:
            await interaction.followup.send(embed=embed, ephemeral=True)
        except:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.HTTPException as e:
        logger.error(f"Erro HTTP na limpeza: {e}")
        embed = create_embed("❌ Erro HTTP", "Erro ao deletar mensagens. Tente uma quantidade menor.", color=0xff0000)
        try:
            await interaction.followup.send(embed=embed, ephemeral=True)
        except:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Erro geral na limpeza: {e}")
        embed = create_embed("❌ Erro", f"Erro inesperado: {str(e)[:100]}", color=0xff0000)
        try:
            await interaction.followup.send(embed=embed, ephemeral=True)
        except:
            await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="warn", description="Dar advertência a um usuário")
async def slash_warn(interaction: discord.Interaction, usuario: discord.Member, motivo: str = "Sem motivo especificado"):
    """Slash command para warn"""


    if not interaction.user.guild_permissions.manage_messages:
        embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Gerenciar Mensagens'!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    if usuario == interaction.user:
        embed = create_embed("❌ Impossível", "Você não pode se advertir!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    if usuario.top_role >= interaction.user.top_role:
        embed = create_embed("❌ Sem permissão", "Você não pode advertir este usuário!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    try:
        user_data = get_user_data(usuario.id)
        if not user_data:
            update_user_data(usuario.id)
            current_warns = 0
        else:
            current_warns = user_data[15] if user_data and len(user_data) > 15 else 0

        new_warns = current_warns + 1

        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('UPDATE users SET warnings = %s WHERE user_id = %s', (new_warns, usuario.id))

            cursor.execute('''
                INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason)
                VALUES (%s, %s, %s, %s, %s)
            ''', (interaction.guild.id, usuario.id, interaction.user.id, 'warn', motivo))

            conn.commit()
            conn.close()

        embed = create_embed(
            "⚠️ Advertência Aplicada",
            f"**Usuário:** {usuario.mention}\n"
            f"**Motivo:** {motivo}\n"
            f"**Moderador:** {interaction.user.mention}\n"
            f"**Total de warns:** {new_warns}",
            color=0xff6600
        )
        await safe_send_response(interaction, embed=embed)

        try:
            dm_embed = create_embed(
                "⚠️ Você recebeu uma advertência",
                f"**Servidor:** {interaction.guild.name}\n"
                f"**Motivo:** {motivo}\n"
                f"**Moderador:** {interaction.user.name}\n"
                f"**Total de advertências:** {new_warns}",
                color=0xff6600
            )
            await usuario.send(embed=dm_embed)
        except:
            pass

    except Exception as e:
        logger.error(f"Erro ao aplicar warn: {e}")
        embed = create_embed("❌ Erro", "Erro ao aplicar advertência!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)

@bot.tree.command(name="addcoins", description="Adicionar moedas a um usuário (Admin)")
async def slash_addcoins(interaction: discord.Interaction, usuario: discord.Member, quantidade: int, motivo: str = "Adição manual"):
    """Slash command para adicionar moedas (Admin only)"""
    try:
        # Verificar se é administrador
        if not interaction.user.guild_permissions.administrator:
            embed = create_embed("❌ Sem permissão", "Você precisa da permissão de 'Administrador' para usar este comando!", color=0xff0000)
            await safe_send_response(interaction, embed, ephemeral=True)
            return

        # Validar quantidade
        if quantidade <= 0:
            embed = create_embed("❌ Quantidade inválida", "A quantidade deve ser maior que 0!", color=0xff0000)
            await safe_send_response(interaction, embed, ephemeral=True)
            return

        if quantidade > 1000000:
            embed = create_embed("❌ Quantidade muito alta", "Máximo de 1.000.000 moedas por vez!", color=0xff0000)
            await safe_send_response(interaction, embed, ephemeral=True)
            return

        # Obter dados do usuário
        user_data = get_user_data(usuario.id)
        if not user_data:
            update_user_data(usuario.id)
            user_data = get_user_data(usuario.id)

        current_coins = user_data[1] if user_data and len(user_data) > 1 else 50
        new_coins = current_coins + quantidade

        # Atualizar banco de dados com tratamento de erro
        conn = None
        try:
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()

                cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (new_coins, usuario.id))

                # Registrar transação
                cursor.execute('''
                    INSERT INTO transactions (user_id, guild_id, type, amount, description)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (usuario.id, interaction.guild.id, 'admin_add', quantidade, f"Admin {interaction.user.name}: {motivo}"))

                conn.commit()
                conn.close()
                conn = None

            embed = create_embed(
                "💰 Moedas Adicionadas!",
                f"**Usuário:** {usuario.mention}\n"
                f"**Quantidade:** +{quantidade:,} moedas\n"
                f"**Saldo anterior:** {current_coins:,} moedas\n"
                f"**Novo saldo:** {new_coins:,} moedas\n"
                f"**Motivo:** {motivo}\n"
                f"**Admin:** {interaction.user.mention}",
                color=0x00ff00
            )
            await safe_interaction_response(interaction, embed)

            # Log da ação
            logger.info(f"Admin {interaction.user.name} adicionou {quantidade} moedas para {usuario.name}. Motivo: {motivo}")

        except Exception as db_error:
            logger.error(f"Database error in addcoins: {db_error}")
            if conn:
                conn.close()
            error_embed = create_embed(
                "⚠️ Erro no Sistema", 
                "Houve um problema com o banco de dados. Tente novamente em alguns segundos.", 
                color=0xff6b6b
            )
            await safe_interaction_response(interaction, error_embed, ephemeral=True)

    except Exception as e:
        logger.error(f"Erro no addcoins: {e}")
        error_embed = create_embed(
            "❌ Erro", 
            "Ocorreu um erro inesperado. Tente novamente.", 
            color=0xff6b6b
        )
        await safe_interaction_response(interaction, error_embed, ephemeral=True)

@bot.tree.command(name="warns", description="Ver advertências de um usuário")
async def slash_warns(interaction: discord.Interaction, usuario: discord.Member = None):
    """Slash command para warns"""


    target = usuario or interaction.user

    try:
        user_data = get_user_data(target.id)
        if not user_data:
            warns = 0
        else:
            warns = user_data[15] if user_data and len(user_data) > 15 else 0

        embed = create_embed(
            f"⚠️ Advertências de {target.display_name}",
            f"**Total de advertências:** {warns}\n"
            f"**Status:** {'🔴 Muitas advertências' if warns >= 5 else '🟡 Algumas advertências' if warns >= 3 else '🟢 Poucas advertências'}",
            color=0xff0000 if warns >= 5 else 0xff6600 if warns >= 3 else 0x00ff00
        )

        embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
        await safe_send_response(interaction, embed=embed)

    except Exception as e:
        logger.error(f"Erro ao verificar warns: {e}")
        embed = create_embed("❌ Erro", "Erro ao verificar advertências!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)

@bot.tree.command(name="ban", description="Banir um membro")
async def slash_ban(interaction: discord.Interaction, usuario: discord.Member, motivo: str = "Sem motivo especificado"):
    """Slash command para ban"""


    if not interaction.user.guild_permissions.ban_members:
        embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Banir Membros'!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    if usuario == interaction.user:
        embed = create_embed("❌ Impossível", "Você não pode se banir!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    if usuario.top_role >= interaction.user.top_role:
        embed = create_embed("❌ Sem permissão", "Você não pode banir este usuário!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    try:
        await usuario.ban(reason=motivo)

        embed = create_embed(
            "🔨 Membro Banido!",
            f"**Usuário:** {usuario.name}#{usuario.discriminator}\n"
            f"**Motivo:** {motivo}\n"
            f"**Moderador:** {interaction.user.mention}",
            color=0xff0000
        )
        await safe_send_response(interaction, embed=embed)

        try:
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (interaction.guild.id, usuario.id, interaction.user.id, 'ban', motivo))
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Erro ao salvar log de moderação: {e}")

    except Exception as e:
        logger.error(f"Erro ao banir membro: {e}")
        embed = create_embed("❌ Erro", f"Erro ao banir membro: {str(e)[:100]}", color=0xff0000)
        await safe_send_response(interaction, embed=embed)

@bot.tree.command(name="kick", description="Expulsar um membro")
async def slash_kick(interaction: discord.Interaction, usuario: discord.Member, motivo: str = "Sem motivo especificado"):
    """Slash command para kick"""


    if not interaction.user.guild_permissions.kick_members:
        embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Expulsar Membros'!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    if usuario == interaction.user:
        embed = create_embed("❌ Impossível", "Você não pode se expulsar!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    if usuario.top_role >= interaction.user.top_role:
        embed = create_embed("❌ Sem permissão", "Você não pode expulsar este usuário!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)
        return

    try:
        await usuario.kick(reason=motivo)

        embed = create_embed(
            "👢 Membro Expulso!",
            f"**Usuário:** {usuario.name}#{usuario.discriminator}\n"
            f"**Motivo:** {motivo}\n"
            f"**Moderador:** {interaction.user.mention}",
            color=0xff6600
        )
        await safe_send_response(interaction, embed=embed)

        try:
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (interaction.guild.id, usuario.id, interaction.user.id, 'kick', motivo))
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Erro ao salvar log de moderação: {e}")

    except Exception as e:
        logger.error(f"Erro ao expulsar membro: {e}")
        embed = create_embed("❌ Erro", f"Erro ao expulsar membro: {str(e)[:100]}", color=0xff0000)
        await safe_send_response(interaction, embed=embed)

# SLASH COMMANDS - MAIS COMANDOS
# COMANDO TEMPORARIAMENTE DESABILITADO PARA FICAR DENTRO DO LIMITE DE 100 SLASH COMMANDS
# @bot.tree.command(name="texto_reverso", description="Inverter texto")
async def slash_texto_reverso(interaction: discord.Interaction, texto: str):
    """Slash command para reverse"""


    reversed_text = texto[::-1]
    embed = create_embed(
        "🔄 Texto Invertido",
        f"**Original:** {texto}\n**Invertido:** {reversed_text}",
        color=0x00ff00
    )
    await safe_send_response(interaction, embed=embed)

# COMANDO TEMPORARIAMENTE DESABILITADO PARA FICAR DENTRO DO LIMITE DE 100 SLASH COMMANDS
# @bot.tree.command(name="uppercase", description="Converter texto para maiúsculas")
async def slash_uppercase(interaction: discord.Interaction, texto: str):
    """Slash command para uppercase"""


    upper_text = texto.upper()
    embed = create_embed(
        "🔤 TEXTO EM MAIÚSCULAS",
        f"**Original:** {texto}\n**Maiúsculas:** {upper_text}",
        color=0x00ff00
    )
    await safe_send_response(interaction, embed=embed)

# COMANDO TEMPORARIAMENTE DESABILITADO PARA FICAR DENTRO DO LIMITE DE 100 SLASH COMMANDS
# @bot.tree.command(name="lowercase", description="Converter texto para minúsculas")
async def slash_lowercase(interaction: discord.Interaction, texto: str):
    """Slash command para lowercase"""


    lower_text = texto.lower()
    embed = create_embed(
        "🔤 texto em minúsculas",
        f"**Original:** {texto}\n**Minúsculas:** {lower_text}",
        color=0x00ff00
    )
    await safe_send_response(interaction, embed=embed)

@bot.tree.command(name="membercount", description="Contagem de membros do servidor")
async def slash_membercount(interaction: discord.Interaction):
    """Slash command para membercount"""


    guild = interaction.guild

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

    await safe_send_response(interaction, embed=embed)

@bot.tree.command(name="level", description="Ver informações de level e XP")
async def slash_level(interaction: discord.Interaction, usuario: discord.Member = None):
    """Slash command para level"""


    target = usuario or interaction.user

    try:
        user_data = get_user_data(target.id)
        if not user_data:
            update_user_data(target.id)
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
        await safe_send_response(interaction, embed=embed)

    except Exception as e:
        logger.error(f"Erro no comando level: {e}")
        embed = create_embed("❌ Erro", "Erro ao carregar informações de level.", color=0xff0000)
        await safe_send_response(interaction, embed=embed)

@bot.tree.command(name="top", description="Ranking geral do servidor")
async def slash_top(interaction: discord.Interaction):
    """Slash command para top"""


    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT user_id, xp, level FROM users ORDER BY xp DESC LIMIT 10')
            top_xp = cursor.fetchall()

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
            user = interaction.guild.get_member(user_id)
            if user:
                rank_id, rank_data = get_user_rank(xp)
                medal = ["🥇", "🥈", "🥉", "4º", "5º"][i]
                xp_text += f"{medal} {user.display_name} - {rank_data['emoji']} Lv.{level} ({xp:,} XP)\n"

        if xp_text:
            embed.add_field(name="⭐ Top XP/Level", value=xp_text, inline=True)

        # Top Coins
        coins_text = ""
        for i, (user_id, coins, bank) in enumerate(top_coins[:5]):
            user = interaction.guild.get_member(user_id)
            if user:
                total = coins + bank
                medal = ["🥇", "🥈", "🥉", "4º", "5º"][i]
                coins_text += f"{medal} {user.display_name} - {total:,} moedas\n"

        if coins_text:
            embed.add_field(name="💰 Top Economia", value=coins_text, inline=True)

        embed.set_footer(text=f"Sua posição: #{await get_user_position(interaction.user.id, interaction.guild.id)} | Use /leaderboard para ver mais")
        await safe_send_response(interaction, embed=embed)

    except Exception as e:
        logger.error(f"Erro no comando top: {e}")
        embed = create_embed("❌ Erro", "Erro ao carregar rankings.", color=0xff0000)
        await safe_send_response(interaction, embed=embed)

@bot.tree.command(name="uptime", description="Tempo que o bot está online")
async def slash_uptime(interaction: discord.Interaction):
    """Slash command para uptime"""


    uptime = datetime.datetime.now() - global_stats['uptime_start']

    embed = create_embed(
        "⏱️ Uptime do RXbot",
        f"**Online há:** {format_time(int(uptime.total_seconds()))}\n"
        f"**Desde:** <t:{int(global_stats['uptime_start'].timestamp())}:F>\n"
        f"**Status:** 🟢 Online e estável",
        color=0x00ff00
    )
    await safe_send_response(interaction, embed=embed)

@bot.tree.command(name="sorteios", description="Ver sorteios ativos")
async def slash_sorteios(interaction: discord.Interaction):
    """Slash command para sorteios"""


    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT title, prize, end_time, winners_count, participants
                FROM giveaways
                WHERE guild_id = %s AND status = 'active'
                ORDER BY end_time
            ''', (interaction.guild.id,))

            giveaways = cursor.fetchall()
            conn.close()

        if not giveaways:
            embed = create_embed(
                "🎁 Nenhum sorteio ativo",
                "Não há sorteios ativos no momento.\nAdministradores podem criar com `/criarsorteio`",
                color=0xffaa00
            )
            await safe_send_response(interaction, embed=embed)
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

        await safe_send_response(interaction, embed=embed)

    except Exception as e:
        logger.error(f"Error listing giveaways: {e}")
        embed = create_embed("❌ Erro", "Erro ao carregar sorteios!", color=0xff0000)
        await safe_send_response(interaction, embed=embed)

@bot.tree.command(name="ticket", description="Criar ticket de suporte")
async def slash_ticket(interaction: discord.Interaction, motivo: str = None):
    """Slash command para ticket"""


    if not motivo:
        embed = create_embed(
            "🎟️ Sistema de Tickets",
            "Para criar um ticket, especifique o motivo:\n"
            "`/ticket <motivo>`\n\n"
            "**Exemplos:**\n"
            "• `/ticket Problema com economia`\n"
            "• `/ticket Bug no bot`\n"
            "• `/ticket Sugestão de melhoria`",
            color=0x7289da
        )
        await safe_send_response(interaction, embed=embed)
        return

    # Criar ticket usando a função existente
    try:
        user = interaction.user
        guild = interaction.guild

        existing_channels = [ch for ch in guild.channels if ch.name.startswith('ticket-') and str(user.id) in ch.name]
        if len(existing_channels) >= 3:
            embed = create_embed(
                "⚠️ Limite de Tickets",
                "Você já tem muitos tickets abertos! Feche alguns antes de criar novos.",
                color=0xff6600
            )
            await safe_send_response(interaction, embed=embed)
            return

        ctx_mock = type('MockCtx', (), {
            'guild': guild,
            'channel': interaction.channel,
            'send': interaction.channel.send,
            'author': user
        })()

        await create_ticket_channel(ctx_mock, motivo, user)

        embed = create_embed(
            "✅ Ticket Criado!",
            f"Seu ticket foi criado com sucesso!\n**Motivo:** {motivo}\n\nVerifique a categoria **📋 Tickets** para encontrar seu canal.",
            color=0x00ff00
        )
        await safe_send_response(interaction, embed=embed)

    except Exception as e:
        logger.error(f"Erro ao criar ticket: {e}")
        embed = create_embed("❌ Erro", "Erro ao criar ticket! Tente novamente.", color=0xff0000)
        await safe_send_response(interaction, embed=embed)

@bot.tree.command(name="ticket_publico", description="Criar painel público de tickets (Admin)")
async def slash_ticket_publico(interaction: discord.Interaction):
    """Slash command para criar painel público de tickets persistente"""
    try:
        if not interaction.user.guild_permissions.manage_channels:
            embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Gerenciar Canais'!", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer()
        
        message = await create_persistent_ticket_message(interaction)
        
        embed = create_embed(
            "✅ Painel Criado!",
            f"Painel de tickets público criado com sucesso!\n\n"
            f"**🔄 Persistente:** Sobrevive a redeploys\n"
            f"**📍 Localização:** {interaction.channel.mention}\n"
            f"**💡 Como usar:** Usuários reagem para criar tickets\n\n"
            f"*Este painel é salvo no PostgreSQL e será restaurado automaticamente após redeploys do Railway.*",
            color=0x00ff00
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        logger.error(f"Erro ao criar ticket público: {e}")
        try:
            await interaction.followup.send("❌ Erro ao criar painel de tickets!", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Erro ao criar painel de tickets!", ephemeral=True)

@bot.tree.command(name="ranklist", description="Lista de todos os ranks")
async def slash_ranklist(interaction: discord.Interaction):
    """Slash command para ranklist"""


    embed = create_embed(
        "🏆 Sistema de Ranks do RXbot",
        "Ganhe XP enviando mensagens e suba de rank!",
        color=0xffd700
    )

    rank_text = ""
    for rank_id, rank_data in RANK_SYSTEM.items():
        rank_text += f"{rank_data['emoji']} **{rank_data['name']}** - {rank_data['xp']:,} XP\n"

    embed.add_field(name="📋 Lista de Ranks", value=rank_text, inline=False)
    embed.add_field(name="💡 Dicas", value=f"• Ganhe {XP_PER_MESSAGE} XP por mensagem\n• Use `/rank` para ver seu progresso\n• Use `/leaderboard` para ver o ranking", inline=False)

    await safe_send_response(interaction, embed=embed)

# 4. COMANDOS DE RANKS (30 comandos)
# Rank slash command moved to avoid conflicts

# Classes de Modal e View para interações

class GiveawayModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🎁 Criar Sorteio")
        
        self.title_input = discord.ui.TextInput(
            label="Título do Sorteio",
            placeholder="Ex: Sorteio de 1000 moedas!",
            required=True,
            max_length=100
        )
        
        self.prize_input = discord.ui.TextInput(
            label="Prêmio",
            placeholder="Ex: 1000 moedas",
            required=True,
            max_length=200
        )
        
        self.duration_input = discord.ui.TextInput(
            label="Duração (em minutos)",
            placeholder="Ex: 60 (para 1 hora)",
            required=True,
            max_length=10
        )
        
        self.winners_input = discord.ui.TextInput(
            label="Número de Vencedores",
            placeholder="Ex: 1",
            required=True,
            max_length=2
        )
        
        self.description_input = discord.ui.TextInput(
            label="Descrição (opcional)",
            placeholder="Regras, condições, etc...",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=500
        )
        
        self.add_item(self.title_input)
        self.add_item(self.prize_input)
        self.add_item(self.duration_input)
        self.add_item(self.winners_input)
        self.add_item(self.description_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            title = self.title_input.value
            prize = self.prize_input.value
            duration = int(self.duration_input.value)
            winners_count = int(self.winners_input.value)
            description = self.description_input.value or "Participe reagindo com 🎉!"
            
            if duration < 1 or duration > 10080:  # Máximo 7 dias
                await interaction.followup.send("❌ Duração deve ser entre 1 minuto e 7 dias!", ephemeral=True)
                return
                
            if winners_count < 1 or winners_count > 20:
                await interaction.followup.send("❌ Número de vencedores deve ser entre 1 e 20!", ephemeral=True)
                return
            
            end_time = datetime.datetime.now() + datetime.timedelta(minutes=duration)
            
            embed = create_embed(
                f"🎁 {title}",
                f"**🎁 Prêmio:** {prize}\n"
                f"**🏆 Vencedores:** {winners_count}\n"
                f"**📋 Descrição:** {description}\n"
                f"**⏰ Termina:** <t:{int(end_time.timestamp())}:R>\n\n"
                f"**Reaja com 🎉 para participar!**",
                color=0xffd700
            )
            
            message = await interaction.channel.send(embed=embed)
            await message.add_reaction("🎉")
            
            # Salvar no banco com query corrigida
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Query corrigida para PostgreSQL/SQLite
                cursor.execute('''
                    INSERT INTO giveaways (guild_id, channel_id, creator_id, title, prize, winners_count, end_time, message_id, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    interaction.guild.id,
                    interaction.channel.id, 
                    interaction.user.id,
                    title,
                    prize,
                    winners_count,
                    end_time,
                    message.id,
                    'active'
                ))
                conn.commit()
                conn.close()
            
            await interaction.followup.send("✅ Sorteio criado com sucesso!", ephemeral=True)
            
        except ValueError:
            await interaction.followup.send("❌ Valores inválidos! Verifique duração e número de vencedores.", ephemeral=True)
        except Exception as e:
            logger.error(f"Erro ao criar sorteio: {e}")
            await interaction.followup.send("❌ Erro ao criar sorteio! Tente novamente.", ephemeral=True)

class CopinhaConfigModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🏆 Configurar Copinha")
        
        self.title_input = discord.ui.TextInput(
            label="Nome da Copinha",
            placeholder="Ex: Copa de Stumble Guys",
            required=True,
            max_length=50
        )
        
        self.map_input = discord.ui.TextInput(
            label="Mapa",
            placeholder="Ex: Hex-A-Gone",
            required=True,
            max_length=30
        )
        
        self.format_input = discord.ui.TextInput(
            label="Formato",
            placeholder="1v1, 2v2, 3v3 ou 4v4",
            required=True,
            max_length=10
        )
        
        self.max_players_input = discord.ui.TextInput(
            label="Máximo de Participantes",
            placeholder="8, 16, 32 ou 64",
            required=True,
            max_length=2
        )
        
        self.add_item(self.title_input)
        self.add_item(self.map_input)
        self.add_item(self.format_input)
        self.add_item(self.max_players_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            title = self.title_input.value
            map_name = self.map_input.value
            team_format = self.format_input.value
            
            try:
                max_players = int(self.max_players_input.value)
            except ValueError:
                embed = create_embed("❌ Erro", "Número de participantes deve ser um número válido!", color=0xff0000)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            valid_formats = ['1v1', '2v2', '3v3', '4v4']
            valid_players = [8, 16, 32, 64]
            
            if team_format not in valid_formats:
                embed = create_embed("❌ Formato inválido", "Use: 1v1, 2v2, 3v3 ou 4v4", color=0xff0000)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
                
            if max_players not in valid_players:
                embed = create_embed("❌ Número inválido", "Use: 8, 16, 32 ou 64 participantes", color=0xff0000)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Criar embed da copinha
            embed = create_embed(
                f"🏆 {title}",
                f"**🗺️ Mapa:** {map_name}\n"
                f"**👥 Formato:** {team_format}\n"
                f"**📊 Participantes:** 0/{max_players}\n"
                f"**📋 Status:** Inscrições abertas\n"
                f"**👑 Organizador:** {interaction.user.mention}\n\n"
                f"**🎮 Clique no botão abaixo para se inscrever!**",
                color=0xffd700
            )
            
            # Criar view com botão de participar
            view = CopinhaJoinView(title, map_name, team_format, max_players, interaction.user.id)
            
            # Enviar mensagem no canal usando interaction.response
            await interaction.response.send_message(embed=embed, view=view)
            
            # Buscar a mensagem criada para salvar no banco
            try:
                message = await interaction.original_response()
                
                # Database save
                execute_query(
                    '''
                    INSERT INTO copinhas (guild_id, creator_id, channel_id, message_id, title, map_name, team_format, max_players, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''',
                    (
                        interaction.guild.id,
                        interaction.user.id,
                        interaction.channel.id,
                        message.id,
                        title,
                        map_name,
                        team_format,
                        max_players,
                        'active'
                    )
                )
                logger.info(f"Copinha criada com sucesso: {title} por {interaction.user}")
                
            except Exception as db_error:
                logger.error(f"Erro ao salvar copinha no banco: {db_error}")
                # Não falhar a criação por erro de banco
            
        except discord.errors.HTTPException as http_error:
            logger.error(f"Erro HTTP ao criar copinha: {http_error}")
            if not interaction.response.is_done():
                embed = create_embed("❌ Erro HTTP", "Erro de comunicação com Discord. Tente novamente.", color=0xff0000)
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Erro geral ao criar copinha: {e}")
            if not interaction.response.is_done():
                embed = create_embed("❌ Erro", "Erro inesperado ao criar copinha. Tente novamente.", color=0xff0000)
                await interaction.response.send_message(embed=embed, ephemeral=True)

class CopinhaJoinView(discord.ui.View):
    def __init__(self, title, map_name, team_format, max_players, creator_id):
        super().__init__(timeout=480)  # 8 minutos
        self.title = title
        self.map_name = map_name
        self.team_format = team_format
        self.max_players = max_players
        self.creator_id = creator_id
        self.participants = []
        self.message = None  # Para armazenar a mensagem original

    @discord.ui.button(label="📝 Inscrever-se", style=discord.ButtonStyle.success, emoji="🎮")
    async def join_tournament(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Verificar se já está inscrito
            if interaction.user.id in self.participants:
                embed = create_embed("❌ Já inscrito", "Você já está inscrito nesta copinha!", color=0xff0000)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
                
            # Verificar se ainda há vagas
            if len(self.participants) >= self.max_players:
                embed = create_embed("❌ Copinha lotada", "Não há mais vagas disponíveis!", color=0xff0000)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Adicionar participante
            self.participants.append(interaction.user.id)
            
            # Lista de participantes para mostrar
            participant_list = []
            for i, user_id in enumerate(self.participants[:10]):  # Mostrar apenas 10
                try:
                    user = bot.get_user(user_id)
                    if user:
                        participant_list.append(f"{i+1}. {user.display_name}")
                    else:
                        participant_list.append(f"{i+1}. Usuário #{user_id}")
                except:
                    participant_list.append(f"{i+1}. Usuário #{user_id}")
            
            participant_text = "\n".join(participant_list)
            if len(self.participants) > 10:
                participant_text += f"\n... e mais {len(self.participants) - 10} jogadores"
            
            # Criar embed atualizado
            embed = create_embed(
                f"🏆 {self.title}",
                f"**🗺️ Mapa:** {self.map_name}\n"
                f"**👥 Formato:** {self.team_format}\n"
                f"**📊 Participantes:** {len(self.participants)}/{self.max_players}\n"
                f"**📋 Status:** {'🚀 Iniciando!' if len(self.participants) == self.max_players else '🔓 Inscrições abertas'}\n\n"
                f"**👥 Lista de Participantes:**\n{participant_text if participant_text else 'Nenhum participante ainda'}\n\n"
                f"**🎮 Clique no botão para se inscrever!**",
                color=0x00ff00 if len(self.participants) == self.max_players else 0xffd700
            )
            
            # Tentar editar a mensagem original
            try:
                if len(self.participants) < self.max_players:
                    await interaction.response.edit_message(embed=embed, view=self)
                else:
                    # Torneio completo, remover view
                    await interaction.response.edit_message(embed=embed, view=None)
                    # Iniciar torneio
                    await self.start_tournament(interaction)
            except discord.errors.NotFound:
                # Mensagem não existe mais
                embed_success = create_embed("✅ Inscrito!", f"Você foi inscrito na copinha **{self.title}**!", color=0x00ff00)
                await interaction.response.send_message(embed=embed_success, ephemeral=True)
            except discord.errors.HTTPException as e:
                logger.error(f"Erro HTTP ao editar mensagem: {e}")
                embed_success = create_embed("✅ Inscrito!", f"Você foi inscrito na copinha **{self.title}**!", color=0x00ff00)
                await interaction.response.send_message(embed=embed_success, ephemeral=True)
                
        except discord.errors.InteractionResponded:
            # Interação já foi respondida
            logger.info("Interação já respondida no join_tournament")
        except Exception as e:
            logger.error(f"Erro ao inscrever na copinha: {e}")
            try:
                if not interaction.response.is_done():
                    embed_error = create_embed("❌ Erro", "Erro ao se inscrever! Tente novamente.", color=0xff0000)
                    await interaction.response.send_message(embed=embed_error, ephemeral=True)
            except:
                logger.error("Falha total ao responder erro de inscrição")

    async def start_tournament(self, interaction):
        """Iniciar torneio quando lotado"""
        try:
            # Criar categoria para a copinha
            category_name = f"🏆 {self.title[:30]}"  # Limitar a 30 caracteres
            category = await interaction.guild.create_category(
                category_name,
                reason=f"Categoria da copinha {self.title}"
            )
            
            # Salvar copinha no banco de dados
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO copinhas (guild_id, creator_id, channel_id, message_id, title, map_name, team_format, max_players, participants, current_round, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    interaction.guild.id,
                    self.creator_id,
                    interaction.channel.id,
                    interaction.message.id if hasattr(interaction, 'message') else None,
                    self.title,
                    self.map_name,
                    self.team_format,
                    self.max_players,
                    json.dumps(self.participants),
                    'inscricoes',
                    'active'
                ))
                
                copinha_id = cursor.fetchone()[0]
                conn.commit()
                conn.close()
            
            # Anunciar início do torneio
            embed_start = create_embed(
                f"🚀 {self.title} - INICIADA!",
                f"**🎯 Participantes:** {len(self.participants)}\n"
                f"**🗺️ Mapa:** {self.map_name}\n"
                f"**👥 Formato:** {self.team_format}\n\n"
                f"🏆 **A copinha está oficialmente iniciada!**\n"
                f"📋 Os tickets das partidas estão sendo criados...\n\n"
                f"🎮 **Boa sorte a todos os participantes!**",
                color=0x00ff00
            )
            
            # Enviar mensagem de início
            try:
                await interaction.followup.send(embed=embed_start)
            except discord.errors.NotFound:
                # Followup não disponível, tentar no canal
                await interaction.channel.send(embed=embed_start)
            except discord.errors.HTTPException:
                # Erro HTTP, tentar método alternativo
                await interaction.channel.send(f"🚀 **{self.title}** iniciada com {len(self.participants)} participantes!")
            
            # Buscar dados da copinha do banco para criar primeira rodada
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM copinhas WHERE id = %s', (copinha_id,))
                copinha_data = cursor.fetchone()
                conn.close()
            
            # Criar primeira rodada com todos os participantes, passando categoria
            await create_next_round(copinha_data, self.participants, 'inscricoes', copinha_id, category)
                
            logger.info(f"Copinha '{self.title}' iniciada com {len(self.participants)} participantes")
            
        except Exception as e:
            logger.error(f"Erro ao iniciar torneio: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def on_timeout(self):
        """Cancelar copinha automaticamente após 8 minutos se não lotar"""
        try:
            # Se a copinha já lotou, não cancelar
            if len(self.participants) >= self.max_players:
                return
            
            # Criar embed de cancelamento
            embed_timeout = create_embed(
                "⏰ Copinha Cancelada por Timeout",
                f"**🏆 {self.title}** foi cancelada automaticamente.\n\n"
                f"**⏱️ Motivo:** Não lotou em 8 minutos\n"
                f"**📊 Participantes:** {len(self.participants)}/{self.max_players}\n"
                f"**🎮 Tentativas:** Precisava de mais {self.max_players - len(self.participants)} jogadores\n\n"
                f"🔄 Use `/copinha` para criar uma nova!",
                color=0xffa500
            )

            # Tentar editar mensagem original se disponível
            if self.message:
                try:
                    await self.message.edit(embed=embed_timeout, view=None)
                    logger.info(f"Copinha '{self.title}' cancelada por timeout (8 min)")
                except discord.errors.NotFound:
                    # Mensagem foi deletada, pular
                    pass
                except Exception as edit_error:
                    logger.error(f"Erro ao editar mensagem de timeout: {edit_error}")

            # Remover copinha do active_games
            for message_id in list(active_games.keys()):
                game_data = active_games.get(message_id)
                if (game_data and game_data.get('view') is self):
                    del active_games[message_id]
                    logger.info(f"Copinha removida de active_games por timeout: {message_id}")
                    break

            # Marcar mensagem interativa como timeout no banco
            try:
                for message_id, game_data in active_games.items():
                    if game_data.get('view') is self:
                        with db_lock:
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute('''
                                UPDATE interactive_messages 
                                SET status = 'timeout'
                                WHERE message_id = %s
                            ''', (message_id,))
                            conn.commit()
                            conn.close()
                        break
            except Exception as db_error:
                logger.error(f"Erro ao marcar timeout no banco: {db_error}")

        except Exception as e:
            logger.error(f"Erro no timeout da copinha: {e}")

async def start_tournament_standalone(channel, title, map_name, team_format, max_players, participants, creator_id):
    """Função standalone para iniciar torneio - usada no rxrandownplayers"""
    try:
        # Criar categoria para a copinha
        category_name = f"🏆 {title[:30]}"  # Limitar a 30 caracteres
        category = await channel.guild.create_category(
            category_name,
            reason=f"Categoria da copinha {title}"
        )
        
        # Salvar copinha no banco de dados
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO copinhas (guild_id, creator_id, channel_id, message_id, title, map_name, team_format, max_players, participants, current_round, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                channel.guild.id,
                creator_id,
                channel.id,
                None,  # Message ID não disponível neste contexto
                title,
                map_name,
                team_format,
                max_players,
                json.dumps(participants),
                'inscricoes',
                'active'
            ))
            
            copinha_id = cursor.fetchone()[0]
            conn.commit()
            conn.close()
        
        # Anunciar início do torneio
        embed_start = create_embed(
            f"🚀 {title} - INICIADA!",
            f"**🎯 Participantes:** {len(participants)}\n"
            f"**🗺️ Mapa:** {map_name}\n"
            f"**👥 Formato:** {team_format}\n\n"
            f"🏆 **A copinha está oficialmente iniciada!**\n"
            f"📋 Os tickets das partidas estão sendo criados...\n\n"
            f"🎮 **Boa sorte a todos os participantes!**",
            color=0x00ff00
        )
        
        # Enviar mensagem de início
        await channel.send(embed=embed_start)
        
        # Buscar dados da copinha do banco para criar primeira rodada
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM copinhas WHERE id = %s', (copinha_id,))
            copinha_data = cursor.fetchone()
            conn.close()
        
        # Criar primeira rodada com todos os participantes, passando categoria
        await create_next_round(copinha_data, participants, 'inscricoes', copinha_id, category)
            
        logger.info(f"Copinha '{title}' iniciada automaticamente com {len(participants)} participantes")
        
    except Exception as e:
        logger.error(f"Erro ao iniciar torneio standalone: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise  # Re-raise para que o comando possa capturar e tratar

class MatchWinnerView(discord.ui.View):
    def __init__(self, copinha_id, match_id, team1, team2, creator_id, team_format):
        super().__init__(timeout=None)  # Sem timeout para permitir escolha a qualquer momento
        self.copinha_id = copinha_id
        self.match_id = match_id
        self.team1 = team1
        self.team2 = team2
        self.creator_id = creator_id
        self.team_format = team_format

    @discord.ui.button(label="🔴 Time 1 Venceu", style=discord.ButtonStyle.success, emoji="🔴", custom_id="match_winner_team1")
    async def team1_wins(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.declare_winner(interaction, self.team1, "Team 1")

    @discord.ui.button(label="🔵 Time 2 Venceu", style=discord.ButtonStyle.success, emoji="🔵", custom_id="match_winner_team2") 
    async def team2_wins(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.declare_winner(interaction, self.team2, "Team 2")

    async def declare_winner(self, interaction, winning_team, team_name):
        """Declarar vencedor da partida"""
        try:
            # Verificar permissões (criador da copinha ou moderadores)
            if not (interaction.user.id == self.creator_id or 
                   interaction.user.guild_permissions.manage_messages):
                await interaction.response.send_message(
                    "❌ Apenas o criador da copinha ou moderadores podem definir o vencedor!", 
                    ephemeral=True
                )
                return

            # Atualizar match no banco de dados
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Marcar match como finalizado com vencedor
                winner_id = winning_team[0]  # ID do primeiro jogador da equipe vencedora
                cursor.execute('''
                    UPDATE copinha_matches 
                    SET status = %s, winner_id = %s 
                    WHERE id = %s
                ''', ('finished', winner_id, self.match_id))
                
                conn.commit()
                conn.close()

            # Formatar equipes para exibição
            team1_display = format_team_display_simple(self.team1, "🔴", self.team_format)
            team2_display = format_team_display_simple(self.team2, "🔵", self.team_format) 
            winner_display = format_team_display_simple(winning_team, "🏆", self.team_format)

            # Criar embed de resultado
            result_embed = create_embed(
                f"🏆 {team_name} Venceu!",
                f"""**🏁 Resultado da Partida:**

{team1_display}
**VS**  
{team2_display}

**🎉 VENCEDOR:**
{winner_display}

**👤 Definido por:** {interaction.user.mention}
**🕒 Data:** {datetime.now().strftime('%d/%m/%Y às %H:%M')}

✅ Resultado registrado! Próxima rodada será criada automaticamente se todas as partidas terminaram.""",
                color=0x00ff00
            )

            # Responder com resultado
            await interaction.response.edit_message(embed=result_embed, view=None)

            # Verificar se pode criar próxima rodada
            await asyncio.sleep(2)  # Pequena pausa para garantir que a atualização do BD foi processada
            await check_next_round(self.copinha_id)

            # Programar exclusão do ticket em 30 segundos
            await asyncio.sleep(30)
            try:
                await interaction.channel.delete(reason=f"Partida finalizada - {team_name} venceu")
            except discord.NotFound:
                pass  # Canal já foi deletado
            except Exception as e:
                logger.error(f"Erro ao deletar canal da partida: {e}")

        except Exception as e:
            logger.error(f"Erro ao declarar vencedor: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erro ao registrar vencedor! Tente novamente.", 
                    ephemeral=True
                )
            except:
                await interaction.followup.send(
                    "❌ Erro ao registrar vencedor! Tente novamente.", 
                    ephemeral=True
                )

class CloseTicketView(discord.ui.View):
    def __init__(self, authorized_user_id):
        super().__init__(timeout=None)
        self.authorized_user_id = authorized_user_id

    @discord.ui.button(label="🔒 Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.authorized_user_id:
            await interaction.response.send_message("❌ Apenas quem solicitou pode fechar!", ephemeral=True)
            return
            
        try:
            await interaction.response.send_message("🔒 Fechando ticket em 5 segundos...")
            await asyncio.sleep(5)
            await interaction.channel.delete(reason=f"Ticket fechado por {interaction.user}")
        except Exception as e:
            logger.error(f"Erro ao fechar ticket: {e}")
            await interaction.followup.send("❌ Erro ao fechar ticket!", ephemeral=True)

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.authorized_user_id:
            await interaction.response.send_message("❌ Apenas quem solicitou pode cancelar!", ephemeral=True)
            return
            
        embed = create_embed("✅ Cancelado", "Fechamento do ticket foi cancelado.", color=0x00ff00)
        await interaction.response.edit_message(embed=embed, view=None)

# Leaderboard slash command removed to avoid conflict with prefix command

# COMANDO LEMBRETE JÁ DEFINIDO ANTERIORMENTE - REMOVIDO DUPLICATA

# COMANDO PASSWORD JÁ DEFINIDO ANTERIORMENTE - REMOVIDO DUPLICATA

# ==== NOVOS COMANDOS SLASH ADICIONAIS ====

@bot.tree.command(name="transferir", description="Transferir moedas para outro usuário")
async def slash_transferir(interaction: discord.Interaction, usuario: discord.Member, quantidade: int):
    """Slash command para transferir moedas"""


    if usuario == interaction.user:
        embed = create_embed("❌ Impossível", "Você não pode transferir para si mesmo!", color=0xff0000)
        await safe_send_response(interaction, embed=embed, ephemeral=True)
        return

    if usuario.bot:
        embed = create_embed("❌ Impossível", "Você não pode transferir para bots!", color=0xff0000)
        await safe_send_response(interaction, embed=embed, ephemeral=True)
        return

    if quantidade <= 0:
        embed = create_embed("❌ Valor inválido", "Use valores positivos!", color=0xff0000)
        await safe_send_response(interaction, embed=embed, ephemeral=True)
        return

    try:
        sender_data = get_user_data(interaction.user.id)
        if not sender_data:
            update_user_data(interaction.user.id)
            sender_data = get_user_data(interaction.user.id)

        sender_coins = sender_data[1] if len(sender_data) > 1 else 50

        if sender_coins < quantidade:
            embed = create_embed(
                "💸 Saldo insuficiente",
                f"Você tem apenas **{sender_coins:,} moedas**!\nNão é possível transferir **{quantidade:,} moedas**.",
                color=0xff0000
            )
            await safe_send_response(interaction, embed=embed, ephemeral=True)
            return

        # Verificar/criar dados do destinatário
        receiver_data = get_user_data(usuario.id)
        if not receiver_data:
            update_user_data(usuario.id)
            receiver_data = get_user_data(usuario.id)

        receiver_coins = receiver_data[1] if len(receiver_data) > 1 else 50

        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Remover do remetente
            new_sender_coins = sender_coins - quantidade
            cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', 
                         (new_sender_coins, interaction.user.id))

            # Adicionar ao destinatário
            new_receiver_coins = receiver_coins + quantidade
            cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', 
                         (new_receiver_coins, usuario.id))

            # Log da transação
            cursor.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (%s, %s, %s, %s, %s)
            ''', (interaction.user.id, interaction.guild.id, 'transferencia_enviada', -quantidade, f"Transferiu para {usuario.display_name}"))

            cursor.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (%s, %s, %s, %s, %s)
            ''', (usuario.id, interaction.guild.id, 'transferencia_recebida', quantidade, f"Recebeu de {interaction.user.display_name}"))

            conn.commit()
            conn.close()

        embed = create_embed(
            "💸 Transferência Realizada!",
            f"""**De:** {interaction.user.display_name}
**Para:** {usuario.display_name}
**Valor:** {quantidade:,} moedas

**Seu novo saldo:** {new_sender_coins:,} moedas
**Saldo de {usuario.display_name}:** {new_receiver_coins:,} moedas""",
            color=0x00ff00
        )
        await safe_send_response(interaction, embed=embed)

    except Exception as e:
        logger.error(f"Erro na transferência: {e}")
        embed = create_embed("❌ Erro", "Erro ao processar transferência!", color=0xff0000)
        await safe_send_response(interaction, embed=embed, ephemeral=True)

@bot.tree.command(name="roles", description="Ver todos os cargos do servidor")
async def slash_roles(interaction: discord.Interaction):
    """Slash command para listar roles"""


    try:
        roles = interaction.guild.roles[1:]  # Remove @everyone
        roles.reverse()  # Maior hierarquia primeiro

        embed = create_embed(
            f"📋 Cargos de {interaction.guild.name}",
            f"**Total:** {len(roles)} cargos",
            color=0x7289da
        )

        roles_text = ""
        for i, role in enumerate(roles[:50]):  # Máximo 50 roles
            role_info = f"{role.mention} - {len(role.members)} membros\n"
            if len(roles_text + role_info) > 1000:
                break
            roles_text += role_info

        if roles_text:
            embed.add_field(name="🎭 Lista de Cargos", value=roles_text, inline=False)

        if len(roles) > 50:
            embed.set_footer(text=f"Mostrando 50 de {len(roles)} cargos")

        await safe_send_response(interaction, embed=embed)

    except Exception as e:
        logger.error(f"Erro no comando roles: {e}")
        embed = create_embed("❌ Erro", "Erro ao carregar cargos!", color=0xff0000)
        await safe_send_response(interaction, embed=embed, ephemeral=True)

@bot.tree.command(name="channels", description="Ver todos os canais do servidor")
async def slash_channels(interaction: discord.Interaction):
    """Slash command para listar canais"""


    try:
        text_channels = interaction.guild.text_channels
        voice_channels = interaction.guild.voice_channels
        categories = interaction.guild.categories

        embed = create_embed(
            f"📺 Canais de {interaction.guild.name}",
            f"**📝 Texto:** {len(text_channels)} canais\n**🔊 Voz:** {len(voice_channels)} canais\n**📁 Categorias:** {len(categories)}",
            color=0x7289da
        )

        # Canais de texto
        text_list = ""
        for channel in text_channels[:15]:
            text_list += f"📝 {channel.mention}\n"
        if text_list:
            embed.add_field(name="💬 Canais de Texto", value=text_list, inline=True)

        # Canais de voz  
        voice_list = ""
        for channel in voice_channels[:15]:
            members_count = len(channel.members)
            voice_list += f"🔊 {channel.name} ({members_count} membros)\n"
        if voice_list:
            embed.add_field(name="🎤 Canais de Voz", value=voice_list, inline=True)

        await safe_send_response(interaction, embed=embed)

    except Exception as e:
        logger.error(f"Erro no comando channels: {e}")
        embed = create_embed("❌ Erro", "Erro ao carregar canais!", color=0xff0000)
        await safe_send_response(interaction, embed=embed, ephemeral=True)

@bot.tree.command(name="id", description="Ver ID de usuário, canal ou servidor")
async def slash_id(interaction: discord.Interaction, usuario: discord.Member = None):
    """Slash command para obter IDs"""
    try:
        if usuario:
            target = usuario
            embed = create_embed(
                f"🆔 ID de {target.display_name}",
                f"**Usuário:** {target.name}#{target.discriminator}\n**ID:** `{target.id}`",
                color=0x7289da
            )
            embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
        else:
            embed = create_embed(
                "🆔 IDs do Sistema",
                f"""**👤 Seu ID:** `{interaction.user.id}`
**📺 Canal atual:** `{interaction.channel.id}`
**🏛️ Servidor:** `{interaction.guild.id}`
**🤖 Bot:** `{interaction.client.user.id}`""",
                color=0x7289da
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        logger.error(f"Erro no comando ID: {e}")
        await interaction.response.send_message("Erro ao obter IDs!", ephemeral=True)

# COMANDO TEMPORARIAMENTE DESABILITADO PARA FICAR DENTRO DO LIMITE DE 100 SLASH COMMANDS
# @bot.tree.command(name="qr", description="Gerar código QR de texto")
async def slash_qr(interaction: discord.Interaction, texto: str):
    """Slash command para gerar QR Code"""
    try:
        # Simular geração de QR (você pode integrar uma biblioteca real aqui)
        embed = create_embed(
            "📱 QR Code Gerado",
            f"**Texto:** {texto}\n\n*Em desenvolvimento - QR será gerado em breve!*",
            color=0x7289da
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Erro no QR: {e}")
        await interaction.response.send_message("Erro ao gerar QR!", ephemeral=True)

# COMANDO TEMPORARIAMENTE DESABILITADO PARA FICAR DENTRO DO LIMITE DE 100 SLASH COMMANDS
# @bot.tree.command(name="hash", description="Gerar hash MD5 de texto")
async def slash_hash(interaction: discord.Interaction, texto: str):
    """Slash command para hash MD5"""
    try:
        import hashlib
        hash_md5 = hashlib.md5(texto.encode()).hexdigest()

        embed = create_embed(
            "🔐 Hash MD5",
            f"**Texto original:** {texto}\n**Hash MD5:** `{hash_md5}`",
            color=0x7289da
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Erro no hash: {e}")
        await interaction.response.send_message("Erro ao gerar hash!", ephemeral=True)

# COMANDO TEMPORARIAMENTE DESABILITADO PARA FICAR DENTRO DO LIMITE DE 100 SLASH COMMANDS
# @bot.tree.command(name="bin", description="Converter texto para binário")
async def slash_bin(interaction: discord.Interaction, texto: str):
    """Slash command para converter para binário"""
    try:
        binary = ' '.join(format(ord(c), '08b') for c in texto)

        embed = create_embed(
            "💾 Texto em Binário",
            f"**Texto:** {texto}\n**Binário:** `{binary[:500]}{'...' if len(binary) > 500 else ''}`",
            color=0x7289da
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Erro no binário: {e}")
        await interaction.response.send_message("Erro na conversão!", ephemeral=True)

# COMANDO TEMPORARIAMENTE DESABILITADO PARA FICAR DENTRO DO LIMITE DE 100 SLASH COMMANDS
# @bot.tree.command(name="hex", description="Converter texto para hexadecimal")
async def slash_hex(interaction: discord.Interaction, texto: str):
    """Slash command para converter para hex"""
    try:
        hex_value = texto.encode().hex()

        embed = create_embed(
            "🔢 Texto em Hexadecimal",
            f"**Texto:** {texto}\n**Hex:** `{hex_value}`",
            color=0x7289da
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Erro no hex: {e}")
        await interaction.response.send_message("Erro na conversão!", ephemeral=True)

# COMANDO TEMPORARIAMENTE DESABILITADO PARA FICAR DENTRO DO LIMITE DE 100 SLASH COMMANDS
# @bot.tree.command(name="capitalize", description="Capitalizar texto")
async def slash_capitalize(interaction: discord.Interaction, texto: str):
    """Slash command para capitalizar"""
    try:
        result = texto.capitalize()

        embed = create_embed(
            "✨ Texto Capitalizado",
            f"**Original:** {texto}\n**Capitalizado:** {result}",
            color=0x7289da
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Erro no capitalize: {e}")
        await interaction.response.send_message("Erro na conversão!", ephemeral=True)

@bot.tree.command(name="lockdown", description="Bloquear canal (apenas admins)")
async def slash_lockdown(interaction: discord.Interaction, motivo: str = "Manutenção"):
    """Slash command para lockdown"""
    try:
        if not interaction.user.guild_permissions.manage_channels:
            embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Gerenciar Canais'!", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Remover permissão de enviar mensagens para @everyone
        everyone = interaction.guild.default_role
        await interaction.channel.set_permissions(everyone, send_messages=False)

        embed = create_embed(
            "🔒 Canal Bloqueado",
            f"**Canal:** {interaction.channel.mention}\n**Motivo:** {motivo}\n**Por:** {interaction.user.mention}",
            color=0xff6b6b
        )
        await interaction.response.send_message(embed=embed)

    except Exception as e:
        logger.error(f"Erro no lockdown: {e}")
        await interaction.response.send_message("Erro ao bloquear canal!", ephemeral=True)

@bot.tree.command(name="unlockdown", description="Desbloquear canal (apenas admins)")
async def slash_unlockdown(interaction: discord.Interaction):
    """Slash command para unlock"""
    try:
        if not interaction.user.guild_permissions.manage_channels:
            embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Gerenciar Canais'!", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Restaurar permissão de enviar mensagens para @everyone
        everyone = interaction.guild.default_role
        await interaction.channel.set_permissions(everyone, send_messages=None)

        embed = create_embed(
            "🔓 Canal Desbloqueado",
            f"**Canal:** {interaction.channel.mention}\n**Por:** {interaction.user.mention}",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed)

    except Exception as e:
        logger.error(f"Erro no unlock: {e}")
        await interaction.response.send_message("Erro ao desbloquear canal!", ephemeral=True)

@bot.tree.command(name="slowmode", description="Configurar modo lento do canal")
async def slash_slowmode(interaction: discord.Interaction, segundos: int):
    """Slash command para slowmode"""
    try:
        if not interaction.user.guild_permissions.manage_channels:
            embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Gerenciar Canais'!", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if segundos < 0 or segundos > 21600:  # Max 6 horas
            embed = create_embed("❌ Valor inválido", "Use entre 0 e 21600 segundos (6 horas)", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.channel.edit(slowmode_delay=segundos)

        if segundos == 0:
            embed = create_embed(
                "⚡ Modo Lento Desabilitado",
                f"**Canal:** {interaction.channel.mention}\n**Por:** {interaction.user.mention}",
                color=0x00ff00
            )
        else:
            embed = create_embed(
                "🐌 Modo Lento Ativado",
                f"**Canal:** {interaction.channel.mention}\n**Delay:** {segundos} segundos\n**Por:** {interaction.user.mention}",
                color=0xffaa00
            )

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        logger.error(f"Erro no slowmode: {e}")
        await interaction.response.send_message("Erro ao configurar slowmode!", ephemeral=True)

@bot.tree.command(name="nuke", description="Recriar canal (apaga todas as mensagens)")
async def slash_nuke(interaction: discord.Interaction):
    """Slash command para nukar canal"""
    try:
        if not interaction.user.guild_permissions.manage_channels:
            embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Gerenciar Canais'!", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        channel = interaction.channel
        channel_position = channel.position

        await interaction.response.send_message("💥 Recriando canal... Aguarde!", ephemeral=True)

        # Recriar canal
        new_channel = await channel.clone()
        await new_channel.edit(position=channel_position)
        await channel.delete()

        embed = create_embed(
            "💥 Canal Nukado!",
            f"Canal recriado com sucesso!\n**Por:** {interaction.user.mention}",
            color=0xff0000
        )
        await new_channel.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro no nuke: {e}")
        try:
            await interaction.followup.send("Erro ao nukar canal!", ephemeral=True)
        except:
            pass

@bot.tree.command(name="vender", description="Vender item do inventário")
async def slash_vender(interaction: discord.Interaction, item_id: int, quantidade: int = 1):
    """Slash command para vender item"""
    try:


        if quantidade <= 0:
            embed = create_embed("❌ Quantidade inválida", "Use quantidades positivas!", color=0xff0000)
            await safe_send_response(interaction, embed=embed, ephemeral=True)
            return

        if item_id not in LOJA_ITENS:
            embed = create_embed("❌ Item inválido", "Este item não existe!", color=0xff0000)
            await safe_send_response(interaction, embed=embed, ephemeral=True)
            return

        try:
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT inventory, coins FROM users WHERE user_id = %s', (interaction.user.id,))
                result = cursor.fetchone()
                conn.close()
        except Exception as e:
            logger.error(f"Erro ao buscar dados do usuário: {e}")
            embed = create_embed("❌ Erro", "Erro ao acessar dados!", color=0xff0000)
            await safe_send_response(interaction, embed=embed, ephemeral=True)
            return

        if not result:
            embed = create_embed("❌ Dados não encontrados", "Você não tem dados de usuário!", color=0xff0000)
            await safe_send_response(interaction, embed=embed, ephemeral=True)
            return

        inventory_data, current_coins = result[0], result[1]
        inventory = json.loads(inventory_data) if inventory_data else {}

        if str(item_id) not in inventory or inventory[str(item_id)] < quantidade:
            embed = create_embed(
                "❌ Item insuficiente",
                f"Você não tem {quantidade}x deste item!\n"
                f"Você tem: {inventory.get(str(item_id), 0)}x",
                color=0xff0000
            )
            await safe_send_response(interaction, embed=embed, ephemeral=True)
            return

        item = LOJA_ITENS[item_id]
        preco_venda = int(item['preco'] * 0.7)  # 70% do preço original
        total_venda = preco_venda * quantidade

        # Remover itens e adicionar dinheiro
        inventory[str(item_id)] -= quantidade
        if inventory[str(item_id)] <= 0:
            del inventory[str(item_id)]

        new_coins = current_coins + total_venda

        try:
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET inventory = %s, coins = %s WHERE user_id = %s',
                              (json.dumps(inventory), new_coins, interaction.user.id))

                # Registrar transação
                cursor.execute('''
                    INSERT INTO transactions (user_id, guild_id, type, amount, description)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (interaction.user.id, interaction.guild.id, 'item_sale', total_venda, f"Vendeu {quantidade}x {item['nome']}"))

                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Erro ao vender item: {e}")
            embed = create_embed("❌ Erro", "Erro ao processar venda!", color=0xff0000)
            await safe_send_response(interaction, embed=embed, ephemeral=True)
            return

        embed = create_embed(
            "💰 Item Vendido!",
            f"**Item:** {item['emoji']} {item['nome']}\n"
            f"**Quantidade:** {quantidade}x\n"
            f"**Preço unitário:** {preco_venda:,} moedas (70% do original)\n"
            f"**Total recebido:** {total_venda:,} moedas\n"
            f"**Novo saldo:** {new_coins:,} moedas\n\n"
            f"*Itens são vendidos por 70% do preço da loja*",
            color=0x00ff00
        )
        await safe_send_response(interaction, embed=embed)

    except Exception as e:
        logger.error(f"Erro geral na venda: {e}")
        embed = create_embed("❌ Erro", "Ocorreu um erro inesperado!", color=0xff0000)
        await safe_send_response(interaction, embed=embed, ephemeral=True)

@bot.tree.command(name="trocar", description="Propor troca de itens com outro usuário")
async def slash_trocar(interaction: discord.Interaction, usuario: discord.Member, seu_item: int, item_dele: int):
    """Slash command para trocar itens"""


    if usuario == interaction.user:
        embed = create_embed("❌ Impossível", "Você não pode trocar consigo mesmo!", color=0xff0000)
        await safe_send_response(interaction, embed=embed, ephemeral=True)
        return

    if usuario.bot:
        embed = create_embed("❌ Impossível", "Você não pode trocar com bots!", color=0xff0000)
        await safe_send_response(interaction, embed=embed, ephemeral=True)
        return

    try:
        # Verificar se os itens existem
        if seu_item not in LOJA_ITENS or item_dele not in LOJA_ITENS:
            embed = create_embed("❌ Item inválido", "Um dos itens não existe na loja!", color=0xff0000)
            await safe_send_response(interaction, embed=embed, ephemeral=True)
            return

        embed = create_embed(
            "🔄 Proposta de Troca",
            f"""**Proposta de:** {interaction.user.mention}
**Para:** {usuario.mention}

**{interaction.user.display_name} oferece:**
{LOJA_ITENS[seu_item]['emoji']} {LOJA_ITENS[seu_item]['nome']}

**{usuario.display_name} oferece:**
{LOJA_ITENS[item_dele]['emoji']} {LOJA_ITENS[item_dele]['nome']}

*{usuario.mention}, reaja com ✅ para aceitar ou ❌ para recusar*""",
            color=0x7289da
        )

        message = await safe_send_response(interaction, embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")

        # TODO: Implementar sistema de reações para confirmar troca

    except Exception as e:
        logger.error(f"Erro na troca: {e}")
        embed = create_embed("❌ Erro", "Erro ao processar troca!", color=0xff0000)
        await safe_send_response(interaction, embed=embed, ephemeral=True)

# ========== NOVOS COMANDOS ÚNICOS PARA CHEGAR AOS 300+ ==========

@bot.tree.command(name="warn_user", description="Advertir um usuário")
async def slash_warn_user(interaction: discord.Interaction, usuario: discord.Member, motivo: str = "Sem motivo especificado"):
    """Slash command para warn (nome único)"""
    if not interaction.user.guild_permissions.manage_messages:
        embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Gerenciar Mensagens'!", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.send_message(f"⚠️ {usuario.mention} foi advertido por: {motivo}")

@bot.tree.command(name="warnings", description="Ver advertências de um usuário")
async def slash_warnings(interaction: discord.Interaction, usuario: discord.Member = None):
    """Slash command para ver warns (nome único)"""
    target = usuario or interaction.user
    embed = create_embed(f"⚠️ Advertências de {target.display_name}", "Sistema em desenvolvimento", color=0xffaa00)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="kick_user", description="Expulsar um usuário")
async def slash_kick_user(interaction: discord.Interaction, usuario: discord.Member, motivo: str = "Sem motivo especificado"):
    """Slash command para kick (nome único)"""
    if not interaction.user.guild_permissions.kick_members:
        embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Expulsar Membros'!", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        await usuario.kick(reason=motivo)
        embed = create_embed("👢 Usuário Expulso", f"{usuario.mention} foi expulso por: {motivo}", color=0xff6b6b)
        await interaction.response.send_message(embed=embed)
    except:
        await interaction.response.send_message("Erro ao expulsar usuário!", ephemeral=True)

@bot.tree.command(name="ban_user", description="Banir um usuário")
async def slash_ban_user(interaction: discord.Interaction, usuario: discord.Member, motivo: str = "Sem motivo especificado"):
    """Slash command para ban (nome único)"""
    if not interaction.user.guild_permissions.ban_members:
        embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Banir Membros'!", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        await usuario.ban(reason=motivo)
        embed = create_embed("🔨 Usuário Banido", f"{usuario.mention} foi banido por: {motivo}", color=0xff0000)
        await interaction.response.send_message(embed=embed)
    except:
        await interaction.response.send_message("Erro ao banir usuário!", ephemeral=True)

@bot.tree.command(name="ia_trocar", description="Trocar modelo de IA da Kaori (Admin)")
@app_commands.describe(
    tipo="""Tipo de IA a usar:
    - auto: OpenAI primeiro, depois IA local
    - openai: Apenas OpenAI (ChatGPT)  
    - local: Apenas IA local (LLaMA)""",
    modelo="Nome do modelo local (.gguf) - apenas para modo 'local'"
)
@app_commands.choices(tipo=[
    app_commands.Choice(name="Auto (OpenAI + Local)", value="auto"),
    app_commands.Choice(name="OpenAI (ChatGPT)", value="openai"),
    app_commands.Choice(name="Local (LLaMA)", value="local")
])
async def slash_trocar_ia(interaction: discord.Interaction, tipo: str, modelo: str = None):
    """Slash command para trocar IA da Kaori (apenas admins)"""
    try:
        # Verificar se é admin ou usuário privilegiado
        is_admin = (interaction.user.guild_permissions.administrator or 
                   interaction.user.id == PRIVILEGED_USER_ID or
                   interaction.user.id in USUARIOS_AUTORIZADOS_CARGOS)
        
        if not is_admin:
            embed = create_embed(
                "❌ Acesso Negado", 
                "Apenas administradores podem trocar o sistema de IA!", 
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Status atual
        status_ai = local_ai.get_status()
        openai_status = "✅ Conectado" if kaori_ai.openai_client else "❌ Não configurado"
        local_status = "✅ Carregado" if status_ai["inicializada"] else "❌ Não carregado"
        
        # Trocar modo de IA
        if tipo in ["auto", "openai", "local"]:
            kaori_ai.set_ai_mode(tipo)
            
            # Se modo local e modelo especificado, trocar modelo
            if tipo == "local" and modelo:
                if local_ai.trocar_modelo(modelo):
                    modelo_info = f"\n🔄 Modelo trocado para: **{modelo}**"
                else:
                    modelo_info = f"\n❌ Erro ao trocar para modelo: **{modelo}**"
            else:
                modelo_info = ""
            
            # Criar embed de resposta
            embed = create_embed(
                "🤖 Sistema de IA Atualizado",
                f"""**Modo atual:** {tipo.upper()}

**Status dos sistemas:**
🌐 **OpenAI ChatGPT:** {openai_status}
🖥️ **IA Local:** {local_status}
📦 **Modelo Local:** {status_ai['modelo_atual']}

**Modelos disponíveis:** {len(status_ai['modelos_disponiveis'])} arquivos .gguf{modelo_info}

**Como funciona:**
• **Auto:** Tenta OpenAI primeiro, depois IA local
• **OpenAI:** Usa apenas ChatGPT (requer API key)
• **Local:** Usa apenas LLaMA local (requer modelo .gguf)""",
                color=0x00ff88
            )
            
            await interaction.response.send_message(embed=embed)
            
        else:
            embed = create_embed(
                "❌ Tipo Inválido", 
                "Use: `auto`, `openai` ou `local`", 
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
    except Exception as e:
        logger.error(f"Erro no comando /trocar: {e}")
        embed = create_embed(
            "❌ Erro", 
            "Erro interno do sistema - verifique os logs", 
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="limpar_canal", description="Limpar mensagens do canal")
async def slash_limpar_canal(interaction: discord.Interaction, quantidade: int):
    """Slash command para limpar canal (nome único)"""
    if not interaction.user.guild_permissions.manage_messages:
        embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Gerenciar Mensagens'!", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if quantidade < 1 or quantidade > 100:
        embed = create_embed("❌ Quantidade inválida", "Use entre 1 e 100 mensagens!", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.send_message(f"🧹 Limpando {quantidade} mensagens...", ephemeral=True)
    deleted = await interaction.channel.purge(limit=quantidade)

    embed = create_embed("🧹 Canal Limpo", f"**{len(deleted)} mensagens** foram deletadas!", color=0x00ff00)
    await interaction.channel.send(embed=embed, delete_after=5)

@bot.tree.command(name="info_servidor", description="Informações do servidor")
async def slash_info_servidor(interaction: discord.Interaction):
    """Slash command para info servidor (nome único)"""
    guild = interaction.guild
    embed = create_embed(
        f"📊 {guild.name}",
        f"""**🏛️ Criado:** <t:{int(guild.created_at.timestamp())}:R>
**👑 Dono:** {guild.owner.mention if guild.owner else 'Desconhecido'}
**👥 Membros:** {guild.member_count:,}
**📺 Canais:** {len(guild.channels)}
**🎭 Cargos:** {len(guild.roles)}
**🎨 Emojis:** {len(guild.emojis)}
**🔒 Nível verificação:** {guild.verification_level}""",
        color=0x7289da
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="info_usuario", description="Informações de um usuário")
async def slash_info_usuario(interaction: discord.Interaction, usuario: discord.Member = None):
    """Slash command para info usuário (nome único)"""
    target = usuario or interaction.user
    embed = create_embed(
        f"👤 {target.display_name}",
        f"""**🏷️ Tag:** {target.name}#{target.discriminator}
**🆔 ID:** `{target.id}`
**📅 Conta criada:** <t:{int(target.created_at.timestamp())}:R>
**📅 Entrou no servidor:** <t:{int(target.joined_at.timestamp())}:R>
**🎭 Cargos:** {len(target.roles) - 1}
**🤖 Bot:** {'Sim' if target.bot else 'Não'}""",
        color=target.color
    )
    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="foto_perfil", description="Ver avatar de um usuário")
async def slash_foto_perfil(interaction: discord.Interaction, usuario: discord.Member = None):
    """Slash command para avatar (nome único)"""
    target = usuario or interaction.user
    embed = create_embed(
        f"🖼️ Avatar de {target.display_name}",
        f"[Link direto]({target.avatar.url if target.avatar else target.default_avatar.url})",
        color=0x7289da
    )
    embed.set_image(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="tempo_online", description="Tempo online do bot")
async def slash_tempo_online(interaction: discord.Interaction):
    """Slash command para uptime"""
    uptime_seconds = int((datetime.datetime.now() - global_stats['uptime_start']).total_seconds())
    uptime_formatted = format_time(uptime_seconds)

    embed = create_embed(
        "⏰ Tempo Online",
        f"**Uptime:** {uptime_formatted}\n**Iniciado:** <t:{int(global_stats['uptime_start'].timestamp())}:R>",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="info_bot", description="Informações do bot")
async def slash_info_bot(interaction: discord.Interaction):
    """Slash command para info bot (nome único)"""
    embed = create_embed(
        "📊 Informações do RXbot",
        f"""**🏛️ Servidores:** {len(bot.guilds)}
**👥 Usuários:** {len(set(bot.get_all_members()))}
**📺 Canais:** {len(list(bot.get_all_channels()))}
**💬 Comandos executados:** {global_stats.get('commands_executed', 0)}
**⏰ Uptime:** {format_time(int((datetime.datetime.now() - global_stats['uptime_start']).total_seconds()))}
**🏓 Latência:** {round(bot.latency * 1000, 2)}ms""",
        color=0x7289da
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="versao_bot", description="Versão do bot")
async def slash_versao_bot(interaction: discord.Interaction):
    """Slash command para versão (nome único)"""
    embed = create_embed(
        "🤖 RXbot v2.1.0",
        "**Versão:** 2.1.0 Estável\n**Discord.py:** 2.3.2\n**Python:** 3.11+\n**Última atualização:** Hoje",
        color=0x7289da
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="contador_membros", description="Contagem de membros")
async def slash_contador_membros(interaction: discord.Interaction):
    """Slash command para membercount"""
    guild = interaction.guild
    embed = create_embed(
        f"👥 Membros de {guild.name}",
        f"**Total:** {guild.member_count:,} membros",
        color=0x7289da
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="servericon", description="Ícone do servidor")
async def slash_servericon(interaction: discord.Interaction):
    """Slash command para servericon"""
    guild = interaction.guild
    if not guild.icon:
        embed = create_embed("❌ Sem ícone", "Este servidor não tem ícone!", color=0xff0000)
        await interaction.response.send_message(embed=embed)
        return

    embed = create_embed(
        f"🏛️ Ícone de {guild.name}",
        f"[Link direto]({guild.icon.url})",
        color=0x7289da
    )
    embed.set_image(url=guild.icon.url)
    await interaction.response.send_message(embed=embed)

# Note: uppercase and lowercase commands already exist earlier in the file

@bot.tree.command(name="lowercase2", description="Converter para minúsculas (alternativo)")
async def slash_lowercase2(interaction: discord.Interaction, texto: str):
    """Slash command para lowercase"""
    result = texto.lower()
    embed = create_embed("🔡 minúsculas", f"**Original:** {texto}\n**Minúsculas:** {result}", color=0x7289da)
    await interaction.response.send_message(embed=embed)

# base64 command already exists earlier in the file

# ============ MAIS 200+ COMANDOS SLASH ADICIONAIS ============

# enquete command already exists earlier in the file

# Duplicate commands section removed to fix CommandAlreadyRegistered errors


# ============ 100 NOVOS COMANDOS SLASH IMPORTANTES ============

# ========== ECONOMIA AVANÇADA (25 COMANDOS) ==========

@bot.tree.command(name="investir", description="Investir dinheiro na bolsa")
async def slash_investir(interaction: discord.Interaction, quantia: int):
    """Investir na bolsa virtual"""
    try:
        user_data = get_user_data(interaction.user.id)
        if not user_data:
            update_user_data(interaction.user.id)
            user_data = get_user_data(interaction.user.id)

        coins = user_data[1] if user_data and len(user_data) > 1 else 50

        if quantia < 50:
            embed = create_embed("❌ Investimento mínimo", "Mínimo: 50 moedas", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if quantia > coins:
            embed = create_embed("❌ Saldo insuficiente", f"Você tem apenas {coins:,} moedas", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Calcular retorno (70% chance positivo, 30% negativo)
        chance = random.randint(1, 100)
        if chance <= 70:
            multiplier = random.uniform(1.05, 1.25)  # 5-25% ganho
            resultado = int(quantia * multiplier)
            lucro = resultado - quantia
            emoji = "📈"
            cor = 0x00ff00
        else:
            multiplier = random.uniform(0.75, 0.95)  # 5-25% perda
            resultado = int(quantia * multiplier)
            lucro = resultado - quantia
            emoji = "📉"
            cor = 0xff0000

        new_coins = coins - quantia + resultado

        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (new_coins, interaction.user.id))
            cursor.execute('''INSERT INTO transactions (user_id, guild_id, type, amount, description)
                             VALUES (%s, %s, %s, %s, %s)''', 
                          (interaction.user.id, interaction.guild.id, 'investment', lucro, f"Investimento de {quantia:,} moedas"))
            conn.commit()
            conn.close()

        embed = create_embed(
            f"{emoji} Resultado do Investimento",
            f"**Investimento:** {quantia:,} moedas\n"
            f"**Retorno:** {resultado:,} moedas\n"
            f"**{'Lucro' if lucro >= 0 else 'Prejuízo'}:** {abs(lucro):,} moedas\n"
            f"**Novo saldo:** {new_coins:,} moedas",
            color=cor
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Erro no investir: {e}")
        await interaction.response.send_message("Erro no investimento!", ephemeral=True)

@bot.tree.command(name="cassino", description="Jogar no cassino")
async def slash_cassino(interaction: discord.Interaction, jogo: str, aposta: int):
    """Jogar no cassino"""
    try:
        jogos_validos = ['roleta', 'blackjack', 'slots', 'dados']
        if jogo.lower() not in jogos_validos:
            embed = create_embed("❌ Jogo inválido", f"Jogos: {', '.join(jogos_validos)}", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        user_data = get_user_data(interaction.user.id)
        if not user_data:
            update_user_data(interaction.user.id)
            user_data = get_user_data(interaction.user.id)

        coins = user_data[1] if user_data and len(user_data) > 1 else 50

        if aposta < 10:
            embed = create_embed("❌ Aposta mínima", "Mínimo: 10 moedas", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if aposta > coins:
            embed = create_embed("❌ Saldo insuficiente", f"Você tem apenas {coins:,} moedas", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Lógica dos jogos
        if jogo.lower() == 'roleta':
            numero = random.randint(0, 36)
            cor = 'verde' if numero == 0 else ('vermelho' if numero % 2 == 1 else 'preto')
            if numero == 0:
                ganho = aposta * 35
                resultado = "🎰 JACKPOT! Zero verde!"
            elif random.choice([True, False]):
                ganho = aposta * 2
                resultado = f"🎯 Ganhou! Número {numero} ({cor})"
            else:
                ganho = 0
                resultado = f"😢 Perdeu! Número {numero} ({cor})"

        elif jogo.lower() == 'blackjack':
            player_cards = [random.randint(1, 11), random.randint(1, 11)]
            dealer_cards = [random.randint(1, 11), random.randint(1, 11)]
            player_total = sum(player_cards)
            dealer_total = sum(dealer_cards)

            if player_total == 21:
                ganho = aposta * 3
                resultado = "🃏 BLACKJACK! 21 perfeito!"
            elif player_total > 21:
                ganho = 0
                resultado = f"💥 Estourou! Suas cartas: {player_total}"
            elif dealer_total > 21 or player_total > dealer_total:
                ganho = aposta * 2
                resultado = f"🎯 Ganhou! Você: {player_total} vs Dealer: {dealer_total}"
            else:
                ganho = 0
                resultado = f"😢 Perdeu! Você: {player_total} vs Dealer: {dealer_total}"

        elif jogo.lower() == 'slots':
            symbols = ['🍒', '🍊', '🍋', '🔔', '⭐', '💎']
            slot1, slot2, slot3 = [random.choice(symbols) for _ in range(3)]

            if slot1 == slot2 == slot3:
                if slot1 == '💎':
                    ganho = aposta * 50
                    resultado = f"💎💎💎 MEGA JACKPOT!"
                else:
                    ganho = aposta * 10
                    resultado = f"{slot1}{slot2}{slot3} Três iguais!"
            elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
                ganho = aposta * 2
                resultado = f"{slot1}{slot2}{slot3} Par!"
            else:
                ganho = 0
                resultado = f"{slot1}{slot2}{slot3} Sem sorte!"

        elif jogo.lower() == 'dados':
            dado1, dado2 = random.randint(1, 6), random.randint(1, 6)
            total = dado1 + dado2

            if total == 7:
                ganho = aposta * 4
                resultado = f"🎲🎲 SETE! ({dado1} + {dado2})"
            elif total in [2, 12]:
                ganho = aposta * 10
                resultado = f"🎲🎲 EXTREMOS! ({dado1} + {dado2})"
            elif total in [6, 8]:
                ganho = aposta * 2
                resultado = f"🎲🎲 Boa! ({dado1} + {dado2})"
            else:
                ganho = 0
                resultado = f"🎲🎲 Perdeu! ({dado1} + {dado2})"

        new_coins = coins - aposta + ganho

        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (new_coins, interaction.user.id))
            cursor.execute('''INSERT INTO transactions (user_id, guild_id, type, amount, description)
                             VALUES (%s, %s, %s, %s, %s)''', 
                          (interaction.user.id, interaction.guild.id, 'casino', ganho - aposta, f"Cassino - {jogo}"))
            conn.commit()
            conn.close()

        embed = create_embed(
            f"🎰 Cassino - {jogo.title()}",
            f"{resultado}\n\n"
            f"**Aposta:** {aposta:,} moedas\n"
            f"**Ganho:** {ganho:,} moedas\n"
            f"**Lucro:** {ganho - aposta:,} moedas\n"
            f"**Novo saldo:** {new_coins:,} moedas",
            color=0x00ff00 if ganho > aposta else 0xff0000
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Erro no cassino: {e}")
        await interaction.response.send_message("Erro no cassino!", ephemeral=True)

@bot.tree.command(name="emprestimo", description="Pedir empréstimo ao banco")
async def slash_emprestimo(interaction: discord.Interaction, quantia: int):
    """Pedir empréstimo"""
    try:
        user_data = get_user_data(interaction.user.id)
        if not user_data:
            update_user_data(interaction.user.id)
            user_data = get_user_data(interaction.user.id)

        # Verificar se já tem empréstimo ativo
        settings_data = user_data[11] if user_data and len(user_data) > 11 else '{}'
        settings = json.loads(settings_data) if settings_data else {}

        if settings.get('loan_amount', 0) > 0:
            embed = create_embed("❌ Empréstimo ativo", "Quite o empréstimo atual primeiro!", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if quantia < 100 or quantia > 10000:
            embed = create_embed("❌ Quantia inválida", "Empréstimo: 100-10,000 moedas", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Juros de 15%
        juros = int(quantia * 0.15)
        total_pagamento = quantia + juros

        coins = user_data[1] if user_data and len(user_data) > 1 else 50
        new_coins = coins + quantia

        # Salvar empréstimo
        settings['loan_amount'] = total_pagamento
        settings['loan_date'] = datetime.datetime.now().isoformat()

        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = %s, settings = %s WHERE user_id = %s', 
                          (new_coins, json.dumps(settings), interaction.user.id))
            cursor.execute('''INSERT INTO transactions (user_id, guild_id, type, amount, description)
                             VALUES (%s, %s, %s, %s, %s)''', 
                          (interaction.user.id, interaction.guild.id, 'loan', quantia, f"Empréstimo de {quantia:,} moedas"))
            conn.commit()
            conn.close()

        embed = create_embed(
            "💰 Empréstimo Aprovado!",
            f"**Valor emprestado:** {quantia:,} moedas\n"
            f"**Juros (15%):** {juros:,} moedas\n"
            f"**Total a pagar:** {total_pagamento:,} moedas\n"
            f"**Novo saldo:** {new_coins:,} moedas\n\n"
            f"*Use `/quitar` para pagar o empréstimo*",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Erro no empréstimo: {e}")
        await interaction.response.send_message("Erro no empréstimo!", ephemeral=True)

@bot.tree.command(name="quitar", description="Quitar empréstimo pendente")
async def slash_quitar(interaction: discord.Interaction):
    """Quitar empréstimo"""
    try:
        user_data = get_user_data(interaction.user.id)
        if not user_data:
            embed = create_embed("❌ Nenhum empréstimo", "Você não tem empréstimos!", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        settings_data = user_data[11] if user_data and len(user_data) > 11 else '{}'
        settings = json.loads(settings_data) if settings_data else {}

        loan_amount = settings.get('loan_amount', 0)
        if loan_amount <= 0:
            embed = create_embed("❌ Nenhum empréstimo", "Você não tem empréstimos!", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        coins = user_data[1] if user_data and len(user_data) > 1 else 50

        if coins < loan_amount:
            embed = create_embed(
                "❌ Saldo insuficiente", 
                f"Você precisa de {loan_amount:,} moedas\nSeu saldo: {coins:,} moedas",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        new_coins = coins - loan_amount
        settings['loan_amount'] = 0
        settings.pop('loan_date', None)

        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = %s, settings = %s WHERE user_id = %s', 
                          (new_coins, json.dumps(settings), interaction.user.id))
            cursor.execute('''INSERT INTO transactions (user_id, guild_id, type, amount, description)
                             VALUES (%s, %s, %s, %s, %s)''', 
                          (interaction.user.id, interaction.guild.id, 'loan_payment', -loan_amount, f"Quitação de empréstimo"))
            conn.commit()
            conn.close()

        embed = create_embed(
            "✅ Empréstimo Quitado!",
            f"**Valor pago:** {loan_amount:,} moedas\n"
            f"**Novo saldo:** {new_coins:,} moedas\n\n"
            f"🎉 Parabéns! Você está livre de dívidas!",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Erro ao quitar: {e}")
        await interaction.response.send_message("Erro ao quitar empréstimo!", ephemeral=True)

@bot.tree.command(name="seguro", description="Contratar seguro para proteção")
async def slash_seguro(interaction: discord.Interaction, tipo: str):
    """Contratar seguro"""
    try:
        seguros = {
            'basico': {'preco': 100, 'protecao': 0.5, 'duracao': 7},
            'premium': {'preco': 250, 'protecao': 0.75, 'duracao': 14},
            'vip': {'preco': 500, 'protecao': 0.9, 'duracao': 30}
        }

        if tipo.lower() not in seguros:
            embed = create_embed("❌ Tipo inválido", "Tipos: basico, premium, vip", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        user_data = get_user_data(interaction.user.id)
        if not user_data:
            update_user_data(interaction.user.id)
            user_data = get_user_data(interaction.user.id)

        coins = user_data[1] if user_data and len(user_data) > 1 else 50
        seguro_info = seguros[tipo.lower()]

        if coins < seguro_info['preco']:
            embed = create_embed("❌ Saldo insuficiente", f"Preço: {seguro_info['preco']:,} moedas", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        settings_data = user_data[11] if user_data and len(user_data) > 11 else '{}'
        settings = json.loads(settings_data) if settings_data else {}

        # Verificar se já tem seguro ativo
        seguro_ativo = settings.get('insurance', {})
        if seguro_ativo.get('expires', 0) > time.time():
            embed = create_embed("❌ Seguro ativo", "Você já tem um seguro ativo!", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        new_coins = coins - seguro_info['preco']
        expires = time.time() + (seguro_info['duracao'] * 24 * 3600)

        settings['insurance'] = {
            'type': tipo.lower(),
            'protection': seguro_info['protecao'],
            'expires': expires
        }

        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = %s, settings = %s WHERE user_id = %s', 
                          (new_coins, json.dumps(settings), interaction.user.id))
            conn.commit()
            conn.close()

        embed = create_embed(
            "🛡️ Seguro Contratado!",
            f"**Tipo:** {tipo.title()}\n"
            f"**Proteção:** {int(seguro_info['protecao'] * 100)}%\n"
            f"**Duração:** {seguro_info['duracao']} dias\n"
            f"**Preço:** {seguro_info['preco']:,} moedas\n"
            f"**Novo saldo:** {new_coins:,} moedas",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Erro no seguro: {e}")
        await interaction.response.send_message("Erro no seguro!", ephemeral=True)

@bot.tree.command(name="mineracao", description="Minerar criptomoedas")
async def slash_mineracao(interaction: discord.Interaction):
    """Minerar criptomoedas"""
    try:
        user_data = get_user_data(interaction.user.id)
        if not user_data:
            update_user_data(interaction.user.id)
            user_data = get_user_data(interaction.user.id)

        # Verificar cooldown (4 horas)
        settings_data = user_data[11] if user_data and len(user_data) > 11 else '{}'
        settings = json.loads(settings_data) if settings_data else {}
        last_mining = settings.get('last_mining', 0)

        current_time = time.time()
        cooldown_time = 14400  # 4 horas

        if current_time - last_mining < cooldown_time:
            remaining = cooldown_time - (current_time - last_mining)
            embed = create_embed(
                "⏰ Mineração em cooldown", 
                f"Aguarde mais **{format_time(int(remaining))}**",
                color=0xff6b6b
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Tipos de mineração
        crypto_types = [
            {'name': 'Bitcoin', 'emoji': '₿', 'min': 50, 'max': 200, 'chance': 0.3},
            {'name': 'Ethereum', 'emoji': 'Ξ', 'min': 30, 'max': 150, 'chance': 0.4},
            {'name': 'Dogecoin', 'emoji': '🐕', 'min': 20, 'max': 100, 'chance': 0.5},
            {'name': 'Litecoin', 'emoji': 'Ł', 'min': 25, 'max': 120, 'chance': 0.45}
        ]

        # Sucesso baseado na chance
        crypto = random.choice(crypto_types)
        success = random.random() < crypto['chance']

        if success:
            ganho = random.randint(crypto['min'], crypto['max'])
            level = user_data[3] if user_data and len(user_data) > 3 else 1
            bonus = int(ganho * (level * 0.02))  # 2% por level
            ganho_total = ganho + bonus

            coins = user_data[1] if user_data and len(user_data) > 1 else 50
            new_coins = coins + ganho_total

            settings['last_mining'] = current_time

            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET coins = %s, settings = %s WHERE user_id = %s', 
                              (new_coins, json.dumps(settings), interaction.user.id))
                cursor.execute('''INSERT INTO transactions (user_id, guild_id, type, amount, description)
                                 VALUES (%s, %s, %s, %s, %s)''', 
                              (interaction.user.id, interaction.guild.id, 'mining', ganho_total, f"Mineração de {crypto['name']}"))
                conn.commit()
                conn.close()

            embed = create_embed(
                f"⛏️ Mineração Bem-sucedida!",
                f"**Criptomoeda:** {crypto['emoji']} {crypto['name']}\n"
                f"**Ganho base:** {ganho:,} moedas\n"
                f"**Bônus level {level}:** {bonus:,} moedas\n"
                f"**Total ganho:** {ganho_total:,} moedas\n"
                f"**Novo saldo:** {new_coins:,} moedas",
                color=0x00ff00
            )
        else:
            settings['last_mining'] = current_time

            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET settings = %s WHERE user_id = %s', 
                              (json.dumps(settings), interaction.user.id))
                conn.commit()
                conn.close()

            embed = create_embed(
                f"💻 Mineração Falhou",
                f"**Criptomoeda:** {crypto['emoji']} {crypto['name']}\n"
                f"**Resultado:** Sem blocos encontrados\n"
                f"**Ganho:** 0 moedas\n\n"
                f"💡 *Tente novamente em 4 horas!*",
                color=0xff6b6b
            )

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Erro na mineração: {e}")
        await interaction.response.send_message("Erro na mineração!", ephemeral=True)

@bot.tree.command(name="acao", description="Comprar/vender ações")
async def slash_acao(interaction: discord.Interaction, operacao: str, empresa: str, quantidade: int = 1):
    """Sistema de ações"""
    try:
        # Defer immediately to avoid timeout

        if operacao.lower() not in ['comprar', 'vender']:
            embed = create_embed("❌ Operação inválida", "Use: comprar ou vender", color=0xff0000)
            await safe_send_response(interaction, embed=embed, ephemeral=True)
            return

        empresas = {
            'techcorp': {'name': 'TechCorp', 'price': 250, 'emoji': '💻'},
            'greenergy': {'name': 'GreenErgy', 'price': 180, 'emoji': '🌱'},
            'spacex': {'name': 'SpaceX', 'price': 320, 'emoji': '🚀'},
            'medihealth': {'name': 'MediHealth', 'price': 150, 'emoji': '🏥'},
            'foodchain': {'name': 'FoodChain', 'price': 90, 'emoji': '🍔'}
        }

        if empresa.lower() not in empresas:
            embed = create_embed("❌ Empresa inválida", f"Empresas: {', '.join(empresas.keys())}", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        user_data = get_user_data(interaction.user.id)
        if not user_data:
            update_user_data(interaction.user.id)
            user_data = get_user_data(interaction.user.id)

        empresa_info = empresas[empresa.lower()]
        preco_flutuante = int(empresa_info['price'] * random.uniform(0.85, 1.15))  # Flutuação de ±15%

        settings_data = user_data[11] if user_data and len(user_data) > 11 else '{}'
        settings = json.loads(settings_data) if settings_data else {}
        stocks = settings.get('stocks', {})

        if operacao.lower() == 'comprar':
            custo_total = preco_flutuante * quantidade
            coins = user_data[1] if user_data and len(user_data) > 1 else 50

            if custo_total > coins:
                embed = create_embed("❌ Saldo insuficiente", f"Custo: {custo_total:,} moedas", color=0xff0000)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            new_coins = coins - custo_total
            stocks[empresa.lower()] = stocks.get(empresa.lower(), 0) + quantidade

            settings['stocks'] = stocks

            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET coins = %s, settings = %s WHERE user_id = %s', 
                              (new_coins, json.dumps(settings), interaction.user.id))
                conn.commit()
                conn.close()

            embed = create_embed(
                f"📈 Ações Compradas!",
                f"**Empresa:** {empresa_info['emoji']} {empresa_info['name']}\n"
                f"**Quantidade:** {quantidade:,} ações\n"
                f"**Preço/ação:** {preco_flutuante:,} moedas\n"
                f"**Custo total:** {custo_total:,} moedas\n"
                f"**Novo saldo:** {new_coins:,} moedas\n"
                f"**Ações totais:** {stocks[empresa.lower()]:,}",
                color=0x00ff00
            )
        else:  # vender
            if empresa.lower() not in stocks or stocks[empresa.lower()] < quantidade:
                embed = create_embed("❌ Ações insuficientes", f"Você tem {stocks.get(empresa.lower(), 0)} ações", color=0xff0000)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            valor_total = preco_flutuante * quantidade
            coins = user_data[1] if user_data and len(user_data) > 1 else 50
            new_coins = coins + valor_total
            stocks[empresa.lower()] -= quantidade

            if stocks[empresa.lower()] == 0:
                del stocks[empresa.lower()]

            settings['stocks'] = stocks

            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET coins = %s, settings = %s WHERE user_id = %s', 
                              (new_coins, json.dumps(settings), interaction.user.id))
                conn.commit()
                conn.close()

            embed = create_embed(
                f"📉 Ações Vendidas!",
                f"**Empresa:** {empresa_info['emoji']} {empresa_info['name']}\n"
                f"**Quantidade:** {quantidade:,} ações\n"
                f"**Preço/ação:** {preco_flutuante:,} moedas\n"
                f"**Valor total:** {valor_total:,} moedas\n"
                f"**Novo saldo:** {new_coins:,} moedas\n"
                f"**Ações restantes:** {stocks.get(empresa.lower(), 0):,}",
                color=0x00ff00
            )

        await safe_send_response(interaction, embed=embed)
    except Exception as e:
        logger.error(f"Erro nas ações: {e}")
        try:
            await interaction.followup.send("Erro no sistema de ações!", ephemeral=True)
        except:
            pass

@bot.tree.command(name="carteira", description="Ver carteira de investimentos")
async def slash_carteira(interaction: discord.Interaction, usuario: discord.Member = None):
    """Ver carteira de investimentos"""
    try:
        target = usuario or interaction.user
        user_data = get_user_data(target.id)
        if not user_data:
            embed = create_embed("❌ Usuário não encontrado", "Dados não disponíveis", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        settings_data = user_data[11] if user_data and len(user_data) > 11 else '{}'
        settings = json.loads(settings_data) if settings_data else {}

        stocks = settings.get('stocks', {})
        insurance = settings.get('insurance', {})
        loan = settings.get('loan_amount', 0)

        empresas = {
            'techcorp': {'name': 'TechCorp', 'price': 250, 'emoji': '💻'},
            'greenergy': {'name': 'GreenErgy', 'price': 180, 'emoji': '🌱'},
            'spacex': {'name': 'SpaceX', 'price': 320, 'emoji': '🚀'},
            'medihealth': {'name': 'MediHealth', 'price': 150, 'emoji': '🏥'},
            'foodchain': {'name': 'FoodChain', 'price': 90, 'emoji': '🍔'}
        }

        portfolio_value = 0
        stock_text = ""

        if stocks:
            for empresa, quantidade in stocks.items():
                if empresa in empresas:
                    info = empresas[empresa]
                    valor_atual = int(info['price'] * random.uniform(0.85, 1.15))
                    valor_total = valor_atual * quantidade
                    portfolio_value += valor_total
                    stock_text += f"{info['emoji']} **{info['name']}:** {quantidade:,} ações (≈{valor_total:,} moedas)\n"

        if not stock_text:
            stock_text = "Nenhuma ação"

        seguro_text = "Nenhum seguro"
        if insurance.get('expires', 0) > time.time():
            tipo = insurance.get('type', 'desconhecido')
            protecao = int(insurance.get('protection', 0) * 100)
            expires_date = datetime.datetime.fromtimestamp(insurance['expires']).strftime('%d/%m/%Y')
            seguro_text = f"🛡️ {tipo.title()} ({protecao}% proteção)\nExpira: {expires_date}"

        emprestimo_text = "Nenhum empréstimo" if loan <= 0 else f"💸 {loan:,} moedas pendentes"

        coins = user_data[1] if user_data and len(user_data) > 1 else 50
        bank = user_data[5] if user_data and len(user_data) > 5 else 0
        valor_total = coins + bank + portfolio_value

        embed = create_embed(
            f"💼 Carteira de {target.display_name}",
            f"**💰 Dinheiro:** {coins:,} moedas\n"
            f"**🏦 Banco:** {bank:,} moedas\n"
            f"**📈 Ações:** {portfolio_value:,} moedas\n"
            f"**💎 Valor total:** {valor_total:,} moedas\n\n"
            f"**📊 Portfólio de Ações:**\n{stock_text}\n"
            f"**🛡️ Seguro:** {seguro_text}\n"
            f"**💸 Empréstimos:** {emprestimo_text}",
            color=0x7289da
        )
        embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Erro na carteira: {e}")
        await interaction.response.send_message("Erro ao carregar carteira!", ephemeral=True)

@bot.tree.command(name="mercado", description="Ver estado do mercado financeiro")
async def slash_mercado(interaction: discord.Interaction):
    """Ver estado do mercado"""
    try:
        empresas = {
            'techcorp': {'name': 'TechCorp', 'base_price': 250, 'emoji': '💻', 'sector': 'Tecnologia'},
            'greenergy': {'name': 'GreenErgy', 'base_price': 180, 'emoji': '🌱', 'sector': 'Energia'},
            'spacex': {'name': 'SpaceX', 'base_price': 320, 'emoji': '🚀', 'sector': 'Aeroespacial'},
            'medihealth': {'name': 'MediHealth', 'base_price': 150, 'emoji': '🏥', 'sector': 'Saúde'},
            'foodchain': {'name': 'FoodChain', 'base_price': 90, 'emoji': '🍔', 'sector': 'Alimentação'}
        }

        market_text = ""
        for empresa_id, info in empresas.items():
            # Simular flutuação do mercado
            flutuacao = random.uniform(-0.15, 0.15)  # -15% a +15%
            preco_atual = int(info['base_price'] * (1 + flutuacao))
            variacao = ((preco_atual - info['base_price']) / info['base_price']) * 100

            emoji_trend = "📈" if variacao > 0 else "📉" if variacao < 0 else "➡️"
            cor_variacao = "+" if variacao > 0 else ""

            market_text += f"{info['emoji']} **{info['name']}** ({info['sector']})\n"
            market_text += f"💰 {preco_atual:,} moedas {emoji_trend} {cor_variacao}{variacao:.1f}%\n\n"

        # Índice geral do mercado
        indice_geral = random.uniform(-5, 5)
        emoji_indice = "📈" if indice_geral > 0 else "📉" if indice_geral < 0 else "➡️"
        cor_indice = "+" if indice_geral > 0 else ""

        embed = create_embed(
            "📊 Estado do Mercado Financeiro",
            f"**📈 Índice RXBot:** {emoji_indice} {cor_indice}{indice_geral:.2f}%\n\n"
            f"**💼 Empresas Listadas:**\n\n{market_text}"
            f"💡 *Use `/acao comprar <empresa> <quantidade>` para investir*\n"
            f"💡 *Preços flutuam a cada consulta*",
            color=0x7289da
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Erro no mercado: {e}")
        await interaction.response.send_message("Erro ao carregar mercado!", ephemeral=True)

@bot.tree.command(name="poupanca", description="Investir na poupança")
async def slash_poupanca(interaction: discord.Interaction, operacao: str, quantia: int = 0):
    """Sistema de poupança"""
    try:
        if operacao.lower() not in ['depositar', 'sacar', 'consultar']:
            embed = create_embed("❌ Operação inválida", "Use: depositar, sacar ou consultar", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        user_data = get_user_data(interaction.user.id)
        if not user_data:
            update_user_data(interaction.user.id)
            user_data = get_user_data(interaction.user.id)

        settings_data = user_data[11] if user_data and len(user_data) > 11 else '{}'
        settings = json.loads(settings_data) if settings_data else {}
        poupanca = settings.get('savings', {'amount': 0, 'last_interest': time.time()})

        # Calcular juros acumulados (0.5% ao dia)
        time_diff = time.time() - poupanca.get('last_interest', time.time())
        days_passed = time_diff / (24 * 3600)

        if days_passed >= 1 and poupanca['amount'] > 0:
            interest_rate = 0.005  # 0.5% ao dia
            days_to_calculate = int(days_passed)
            juros = int(poupanca['amount'] * interest_rate * days_to_calculate)
            poupanca['amount'] += juros
            poupanca['last_interest'] = time.time()

            # Atualizar no banco
            settings['savings'] = poupanca
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET settings = %s WHERE user_id = %s', 
                              (json.dumps(settings), interaction.user.id))
                conn.commit()
                conn.close()

        if operacao.lower() == 'consultar':
            dias_investido = (time.time() - poupanca.get('last_interest', time.time())) / (24 * 3600)
            embed = create_embed(
                "💰 Poupança RXBot",
                f"**Saldo na poupança:** {poupanca['amount']:,} moedas\n"
                f"**Rendimento:** 0.5% ao dia\n"
                f"**Dias investido:** {int(dias_investido)}\n"
                f"**Próximos juros:** {int(poupanca['amount'] * 0.005):,} moedas\n\n"
                f"💡 *Use `/poupanca depositar <quantia>` para investir*",
                color=0x00ff00
            )

        elif operacao.lower() == 'depositar':
            if quantia < 50:
                embed = create_embed("❌ Depósito mínimo", "Mínimo: 50 moedas", color=0xff0000)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            coins = user_data[1] if user_data and len(user_data) > 1 else 50
            if quantia > coins:
                embed = create_embed("❌ Saldo insuficiente", f"Você tem {coins:,} moedas", color=0xff0000)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            new_coins = coins - quantia
            poupanca['amount'] += quantia
            if 'last_interest' not in poupanca:
                poupanca['last_interest'] = time.time()

            settings['savings'] = poupanca

            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET coins = %s, settings = %s WHERE user_id = %s', 
                              (new_coins, json.dumps(settings), interaction.user.id))
                conn.commit()
                conn.close()

            embed = create_embed(
                "💰 Depósito Realizado!",
                f"**Depositado:** {quantia:,} moedas\n"
                f"**Saldo poupança:** {poupanca['amount']:,} moedas\n"
                f"**Saldo carteira:** {new_coins:,} moedas\n"
                f"**Rendimento:** 0.5% ao dia\n\n"
                f"💡 *Juros calculados diariamente*",
                color=0x00ff00
            )

        else:  # sacar
            if quantia > poupanca['amount']:
                embed = create_embed("❌ Saldo insuficiente", f"Poupança: {poupanca['amount']:,} moedas", color=0xff0000)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if quantia < 10:
                embed = create_embed("❌ Saque mínimo", "Mínimo: 10 moedas", color=0xff0000)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            coins = user_data[1] if user_data and len(user_data) > 1 else 50
            new_coins = coins + quantia
            poupanca['amount'] -= quantia

            settings['savings'] = poupanca

            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET coins = %s, settings = %s WHERE user_id = %s', 
                              (new_coins, json.dumps(settings), interaction.user.id))
                conn.commit()
                conn.close()

            embed = create_embed(
                "💰 Saque Realizado!",
                f"**Sacado:** {quantia:,} moedas\n"
                f"**Saldo poupança:** {poupanca['amount']:,} moedas\n"
                f"**Saldo carteira:** {new_coins:,} moedas\n\n"
                f"💡 *Continue investindo para ganhar juros*",
                color=0x00ff00
            )

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Erro na poupança: {e}")
        await interaction.response.send_message("Erro na poupança!", ephemeral=True)

@bot.tree.command(name="cripto", description="Minerar/trocar criptomoedas")
async def slash_cripto(interaction: discord.Interaction, operacao: str, tipo: str = "bitcoin", quantia: int = 1):
    """Sistema de criptomoedas"""
    try:
        if operacao.lower() not in ['minar', 'comprar', 'vender', 'carteira']:
            embed = create_embed("❌ Operação inválida", "Use: minar, comprar, vender, carteira", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        criptos = {
            'bitcoin': {'name': 'Bitcoin', 'symbol': '₿', 'price': 1000, 'mining_cost': 200},
            'ethereum': {'name': 'Ethereum', 'symbol': 'Ξ', 'price': 600, 'mining_cost': 120},
            'dogecoin': {'name': 'Dogecoin', 'symbol': '🐕', 'price': 50, 'mining_cost': 20},
            'litecoin': {'name': 'Litecoin', 'symbol': 'Ł', 'price': 300, 'mining_cost': 80}
        }

        if tipo.lower() not in criptos:
            embed = create_embed("❌ Cripto inválida", f"Tipos: {', '.join(criptos.keys())}", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        user_data = get_user_data(interaction.user.id)
        if not user_data:
            update_user_data(interaction.user.id)
            user_data = get_user_data(interaction.user.id)

        settings_data = user_data[11] if user_data and len(user_data) > 11 else '{}'
        settings = json.loads(settings_data) if settings_data else {}
        crypto_wallet = settings.get('crypto', {})

        cripto_info = criptos[tipo.lower()]
        preco_flutuante = int(cripto_info['price'] * random.uniform(0.7, 1.3))  # Flutuação de ±30%

        if operacao.lower() == 'carteira':
            if not crypto_wallet:
                embed = create_embed("💰 Carteira de Criptomoedas", "Nenhuma criptomoeda encontrada", color=0x7289da)
            else:
                wallet_text = ""
                total_value = 0
                for crypto, amount in crypto_wallet.items():
                    if crypto in criptos:
                        info = criptos[crypto]
                        current_price = int(info['price'] * random.uniform(0.7, 1.3))
                        value = current_price * amount
                        total_value += value
                        wallet_text += f"{info['symbol']} **{info['name']}:** {amount:.4f} (≈{value:,} moedas)\n"

                embed = create_embed(
                    "💰 Carteira de Criptomoedas",
                    f"{wallet_text}\n**💎 Valor total:** ≈{total_value:,} moedas\n\n"
                    f"💡 *Preços flutuam constantemente*",
                    color=0x7289da
                )

        elif operacao.lower() == 'minar':
            custo_mineracao = cripto_info['mining_cost']
            coins = user_data[1] if user_data and len(user_data) > 1 else 50

            if coins < custo_mineracao:
                embed = create_embed("❌ Saldo insuficiente", f"Custo mineração: {custo_mineracao:,} moedas", color=0xff0000)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Chance de sucesso baseada no tipo de cripto
            chance_sucesso = {'bitcoin': 0.3, 'ethereum': 0.4, 'dogecoin': 0.6, 'litecoin': 0.5}[tipo.lower()]

            if random.random() < chance_sucesso:
                amount_mined = random.uniform(0.001, 0.01)  # Quantidade minerada
                new_coins = coins - custo_mineracao
                crypto_wallet[tipo.lower()] = crypto_wallet.get(tipo.lower(), 0) + amount_mined

                settings['crypto'] = crypto_wallet

                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('UPDATE users SET coins = %s, settings = %s WHERE user_id = %s', 
                                  (new_coins, json.dumps(settings), interaction.user.id))
                    conn.commit()
                    conn.close()

                embed = create_embed(
                    f"⛏️ Mineração Sucesso!",
                    f"**Cripto:** {cripto_info['symbol']} {cripto_info['name']}\n"
                    f"**Minerado:** {amount_mined:.4f} {cripto_info['symbol']}\n"
                    f"**Custo:** {custo_mineracao:,} moedas\n"
                    f"**Novo saldo:** {new_coins:,} moedas\n"
                    f"**Total {tipo}:** {crypto_wallet[tipo.lower()]:.4f}",
                    color=0x00ff00
                )
            else:
                new_coins = coins - custo_mineracao

                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (new_coins, interaction.user.id))
                    conn.commit()
                    conn.close()

                embed = create_embed(
                    f"💻 Mineração Falhou",
                    f"**Cripto:** {cripto_info['symbol']} {cripto_info['name']}\n"
                    f"**Resultado:** Nenhum bloco encontrado\n"
                    f"**Custo:** {custo_mineracao:,} moedas\n"
                    f"**Novo saldo:** {new_coins:,} moedas",
                    color=0xff6b6b
                )

        elif operacao.lower() == 'comprar':
            custo_total = int(preco_flutuante * quantia)
            coins = user_data[1] if user_data and len(user_data) > 1 else 50

            if custo_total > coins:
                embed = create_embed("❌ Saldo insuficiente", f"Custo: {custo_total:,} moedas", color=0xff0000)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            new_coins = coins - custo_total
            crypto_wallet[tipo.lower()] = crypto_wallet.get(tipo.lower(), 0) + quantia

            settings['crypto'] = crypto_wallet

            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET coins = %s, settings = %s WHERE user_id = %s', 
                              (new_coins, json.dumps(settings), interaction.user.id))
                conn.commit()
                conn.close()

            embed = create_embed(
                f"💰 Compra Realizada!",
                f"**Cripto:** {cripto_info['symbol']} {cripto_info['name']}\n"
                f"**Quantidade:** {quantia} {cripto_info['symbol']}\n"
                f"**Preço/unidade:** {preco_flutuante:,} moedas\n"
                f"**Custo total:** {custo_total:,} moedas\n"
                f"**Novo saldo:** {new_coins:,} moedas\n"
                f"**Total {tipo}:** {crypto_wallet[tipo.lower()]:.4f}",
                color=0x00ff00
            )

        else:  # vender
            if tipo.lower() not in crypto_wallet or crypto_wallet[tipo.lower()] < quantia:
                embed = create_embed("❌ Saldo insuficiente", f"Você tem {crypto_wallet.get(tipo.lower(), 0):.4f} {cripto_info['symbol']}", color=0xff0000)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            valor_total = int(preco_flutuante * quantia)
            coins = user_data[1] if user_data and len(user_data) > 1 else 50
            new_coins = coins + valor_total
            crypto_wallet[tipo.lower()] -= quantia

            if crypto_wallet[tipo.lower()] <= 0:
                del crypto_wallet[tipo.lower()]

            settings['crypto'] = crypto_wallet

            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET coins = %s, settings = %s WHERE user_id = %s', 
                              (new_coins, json.dumps(settings), interaction.user.id))
                conn.commit()
                conn.close()

            embed = create_embed(
                f"💸 Venda Realizada!",
                f"**Cripto:** {cripto_info['symbol']} {cripto_info['name']}\n"
                f"**Quantidade:** {quantia} {cripto_info['symbol']}\n"
                f"**Preço/unidade:** {preco_flutuante:,} moedas\n"
                f"**Valor total:** {valor_total:,} moedas\n"
                f"**Novo saldo:** {new_coins:,} moedas\n"
                f"**Restante:** {crypto_wallet.get(tipo.lower(), 0):.4f}",
                color=0x00ff00
            )

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Erro nas criptos: {e}")
        await interaction.response.send_message("Erro no sistema de criptomoedas!", ephemeral=True)

# ========== ADMINISTRAÇÃO E MODERAÇÃO (25 COMANDOS) ==========

@bot.tree.command(name="automod", description="Configurar auto-moderação")
async def slash_automod(interaction: discord.Interaction, acao: str, configuracao: str = "ver"):
    """Sistema de auto-moderação"""
    try:
        if not interaction.user.guild_permissions.manage_guild:
            embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Gerenciar Servidor'", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        acoes_validas = ['spam', 'xingamento', 'link', 'caps', 'emoji', 'mention']
        if acao.lower() not in acoes_validas:
            embed = create_embed("❌ Ação inválida", f"Ações: {', '.join(acoes_validas)}", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            if configuracao.lower() == "ver":
                cursor.execute('SELECT * FROM auto_mod_rules WHERE guild_id = %s AND rule_type = %s', 
                              (interaction.guild.id, acao.lower()))
                rule = cursor.fetchone()

                if rule:
                    status = "✅ Ativo" if rule[4] else "❌ Inativo"
                    embed = create_embed(
                        f"🛡️ Auto-Mod: {acao.title()}",
                        f"**Status:** {status}\n"
                        f"**Punição:** {rule[3]}\n"
                        f"**Configurado em:** {rule[5]}\n\n"
                        f"💡 *Use `/automod {acao} ativar/desativar` para alterar*",
                        color=0x7289da
                    )
                else:
                    embed = create_embed(
                        f"🛡️ Auto-Mod: {acao.title()}",
                        "**Status:** ❌ Não configurado\n\n"
                        f"💡 *Use `/automod {acao} ativar` para configurar*",
                        color=0xff6b6b
                    )

            elif configuracao.lower() == "ativar":
                punishments = {
                    'spam': 'warn',
                    'xingamento': 'timeout',
                    'link': 'delete',
                    'caps': 'delete',
                    'emoji': 'delete',
                    'mention': 'warn'
                }

                cursor.execute('''INSERT OR REPLACE INTO auto_mod_rules 
                                 (guild_id, rule_type, rule_data, punishment, enabled) 
                                 VALUES (%s, %s, %s, %s, %s)''',
                              (interaction.guild.id, acao.lower(), '{}', punishments[acao.lower()], 1))
                conn.commit()

                embed = create_embed(
                    f"✅ Auto-Mod Ativado",
                    f"**Regra:** {acao.title()}\n"
                    f"**Punição:** {punishments[acao.lower()]}\n"
                    f"**Status:** ✅ Ativo\n\n"
                    f"🛡️ *Protegendo o servidor automaticamente*",
                    color=0x00ff00
                )

            elif configuracao.lower() == "desativar":
                cursor.execute('UPDATE auto_mod_rules SET enabled = 0 WHERE guild_id = %s AND rule_type = %s',
                              (interaction.guild.id, acao.lower()))
                conn.commit()

                embed = create_embed(
                    f"❌ Auto-Mod Desativado",
                    f"**Regra:** {acao.title()}\n"
                    f"**Status:** ❌ Inativo\n\n"
                    f"⚠️ *Esta proteção foi desativada*",
                    color=0xff6b6b
                )

            else:
                embed = create_embed("❌ Configuração inválida", "Use: ver, ativar ou desativar", color=0xff0000)

            conn.close()

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Erro no automod: {e}")
        await interaction.response.send_message("Erro no sistema de auto-moderação!", ephemeral=True)

@bot.tree.command(name="timeout", description="Dar timeout em um usuário")
async def slash_timeout(interaction: discord.Interaction, usuario: discord.Member, duracao: int, motivo: str = "Não especificado"):
    """Aplicar timeout em usuário"""
    try:
        if not interaction.user.guild_permissions.moderate_members:
            embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Moderar Membros'", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if usuario.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            embed = create_embed("❌ Hierarquia", "Você não pode aplicar timeout neste usuário", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if duracao < 1 or duracao > 10080:  # Max 7 dias
            embed = create_embed("❌ Duração inválida", "Use entre 1 minuto e 7 dias (10080 min)", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        timeout_until = datetime.datetime.now() + datetime.timedelta(minutes=duracao)

        await usuario.timeout(timeout_until, reason=f"Por {interaction.user}: {motivo}")

        # Registrar no banco
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason, duration)
                             VALUES (%s, %s, %s, %s, %s, %s)''',
                          (interaction.guild.id, usuario.id, interaction.user.id, 'timeout', motivo, duracao))
            conn.commit()
            conn.close()

        embed = create_embed(
            "⏰ Timeout Aplicado",
            f"**Usuário:** {usuario.mention}\n"
            f"**Duração:** {duracao} minutos\n"
            f"**Motivo:** {motivo}\n"
            f"**Moderador:** {interaction.user.mention}\n"
            f"**Expira:** <t:{int(timeout_until.timestamp())}:F>",
            color=0xffaa00
        )

        await interaction.response.send_message(embed=embed)

        # Tentar DM para o usuário
        try:
            dm_embed = create_embed(
                f"⏰ Timeout em {interaction.guild.name}",
                f"**Duração:** {duracao} minutos\n"
                f"**Motivo:** {motivo}\n"
                f"**Expira:** <t:{int(timeout_until.timestamp())}:F>",
                color=0xffaa00
            )
            await usuario.send(embed=dm_embed)
        except:
            pass
    except Exception as e:
        logger.error(f"Erro no timeout: {e}")
        await interaction.response.send_message("Erro ao aplicar timeout!", ephemeral=True)

@bot.tree.command(name="untimeout", description="Remover timeout de um usuário")
async def slash_untimeout(interaction: discord.Interaction, usuario: discord.Member):
    """Remover timeout"""
    try:
        if not interaction.user.guild_permissions.moderate_members:
            embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Moderar Membros'", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not usuario.is_timed_out():
            embed = create_embed("❌ Sem timeout", "Este usuário não está em timeout", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await usuario.timeout(None, reason=f"Timeout removido por {interaction.user}")

        embed = create_embed(
            "✅ Timeout Removido",
            f"**Usuário:** {usuario.mention}\n"
            f"**Moderador:** {interaction.user.mention}\n"
            f"**Ação:** Timeout removido com sucesso",
            color=0x00ff00
        )

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Erro ao remover timeout: {e}")
        await interaction.response.send_message("Erro ao remover timeout!", ephemeral=True)

@bot.tree.command(name="massban", description="Banir múltiplos usuários")
async def slash_massban(interaction: discord.Interaction, usuarios: str, motivo: str = "Banimento em massa"):
    """Banir múltiplos usuários"""
    try:
        if not interaction.user.guild_permissions.ban_members:
            embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Banir Membros'", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Parsear IDs de usuários (separados por espaço ou vírgula)
        user_ids = []
        for uid in usuarios.replace(',', ' ').split():
            try:
                user_ids.append(int(uid.strip()))
            except ValueError:
                continue

        if not user_ids:
            embed = create_embed("❌ IDs inválidos", "Forneça IDs válidos separados por espaço", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        banned_count = 0
        failed_bans = []



        for user_id in user_ids:
            try:
                user = await bot.fetch_user(user_id)
                member = interaction.guild.get_member(user_id)

                if member and member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
                    failed_bans.append(f"{user.name} (hierarquia)")
                    continue

                await interaction.guild.ban(user, reason=f"Banimento em massa por {interaction.user}: {motivo}")
                banned_count += 1

                # Registrar no banco
                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('''INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason)
                                     VALUES (%s, %s, %s, %s, %s)''',
                                  (interaction.guild.id, user_id, interaction.user.id, 'massban', motivo))
                    conn.commit()
                    conn.close()

                await asyncio.sleep(1)  # Evitar rate limit
            except Exception as e:
                failed_bans.append(f"ID {user_id} (erro)")

        result_text = f"**Banidos:** {banned_count} usuários\n"
        if failed_bans:
            result_text += f"**Falhas:** {', '.join(failed_bans[:5])}"
            if len(failed_bans) > 5:
                result_text += f" e mais {len(failed_bans) - 5}"

        embed = create_embed(
            "🔨 Banimento em Massa",
            f"{result_text}\n\n"
            f"**Motivo:** {motivo}\n"
            f"**Moderador:** {interaction.user.mention}",
            color=0xff0000
        )

        await safe_send_response(interaction, embed=embed)
    except Exception as e:
        logger.error(f"Erro no massban: {e}")
        await interaction.followup.send("Erro no banimento em massa!", ephemeral=True)

@bot.tree.command(name="purge", description="Limpar mensagens com filtros avançados")
async def slash_purge(interaction: discord.Interaction, quantidade: int, filtro: str = "todas", usuario: discord.Member = None):
    """Limpar mensagens com filtros"""
    try:
        if not interaction.user.guild_permissions.manage_messages:
            embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Gerenciar Mensagens'", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if quantidade < 1 or quantidade > 100:
            embed = create_embed("❌ Quantidade inválida", "Use entre 1 e 100 mensagens", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        filtros_validos = ['todas', 'bots', 'humanos', 'imagens', 'links', 'usuario']
        if filtro.lower() not in filtros_validos:
            embed = create_embed("❌ Filtro inválido", f"Filtros: {', '.join(filtros_validos)}", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if filtro.lower() == 'usuario' and not usuario:
            embed = create_embed("❌ Usuário necessário", "Especifique um usuário para este filtro", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return



        def check_message(message):
            if filtro.lower() == 'todas':
                return True
            elif filtro.lower() == 'bots':
                return message.author.bot
            elif filtro.lower() == 'humanos':
                return not message.author.bot
            elif filtro.lower() == 'imagens':
                return len(message.attachments) > 0
            elif filtro.lower() == 'links':
                return 'http' in message.content.lower()
            elif filtro.lower() == 'usuario':
                return message.author == usuario
            return False

        deleted = await interaction.channel.purge(limit=quantidade, check=check_message)

        embed = create_embed(
            "🧹 Limpeza Concluída",
            f"**Mensagens deletadas:** {len(deleted)}\n"
            f"**Filtro usado:** {filtro.title()}\n"
            f"**Canal:** {interaction.channel.mention}\n"
            f"**Moderador:** {interaction.user.mention}",
            color=0x00ff00
        )

        await safe_send_response(interaction, embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Erro no purge: {e}")
        await interaction.followup.send("Erro na limpeza de mensagens!", ephemeral=True)

@bot.tree.command(name="lockserver", description="Bloquear servidor inteiro")
async def slash_lockserver(interaction: discord.Interaction, motivo: str = "Emergência"):
    """Bloquear servidor inteiro"""
    try:
        if not interaction.user.guild_permissions.administrator:
            embed = create_embed("❌ Sem permissão", "Você precisa ser administrador", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return



        locked_channels = 0
        failed_channels = []

        for channel in interaction.guild.text_channels:
            try:
                overwrites = channel.overwrites_for(interaction.guild.default_role)
                overwrites.send_messages = False
                await channel.set_permissions(interaction.guild.default_role, overwrite=overwrites, 
                                            reason=f"Servidor bloqueado por {interaction.user}: {motivo}")
                locked_channels += 1
            except Exception:
                failed_channels.append(channel.name)

        embed = create_embed(
            "🔒 Servidor Bloqueado",
            f"**Canais bloqueados:** {locked_channels}\n"
            f"**Falhas:** {len(failed_channels)}\n"
            f"**Motivo:** {motivo}\n"
            f"**Administrador:** {interaction.user.mention}\n\n"
            f"⚠️ *Use `/unlockserver` para desbloquear*",
            color=0xff6b6b
        )

        await safe_send_response(interaction, embed=embed)
    except Exception as e:
        logger.error(f"Erro no lockserver: {e}")
        await interaction.followup.send("Erro ao bloquear servidor!", ephemeral=True)



@bot.tree.command(name="unlockserver", description="Desbloquear servidor")
async def slash_unlockserver(interaction: discord.Interaction):
    """Desbloquear servidor"""
    try:
        if not interaction.user.guild_permissions.administrator:
            embed = create_embed("❌ Sem permissão", "Você precisa ser administrador", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return



        unlocked_channels = 0
        failed_channels = []

        for channel in interaction.guild.text_channels:
            try:
                overwrites = channel.overwrites_for(interaction.guild.default_role)
                overwrites.send_messages = None  # Resetar para padrão
                await channel.set_permissions(interaction.guild.default_role, overwrite=overwrites,
                                            reason=f"Servidor desbloqueado por {interaction.user}")
                unlocked_channels += 1
            except Exception:
                failed_channels.append(channel.name)

        embed = create_embed(
            "🔓 Servidor Desbloqueado",
            f"**Canais desbloqueados:** {unlocked_channels}\n"
            f"**Falhas:** {len(failed_channels)}\n"
            f"**Administrador:** {interaction.user.mention}\n\n"
            f"✅ *Servidor restaurado ao normal*",
            color=0x00ff00
        )

        await safe_send_response(interaction, embed=embed)
    except Exception as e:
        logger.error(f"Erro no unlockserver: {e}")
        await interaction.followup.send("Erro ao desbloquear servidor!", ephemeral=True)

@bot.tree.command(name="definir_vencedor", description="Definir vencedor de uma partida da copinha")
async def slash_definir_vencedor(interaction: discord.Interaction, vencedor: discord.Member):
    """Definir vencedor de uma partida"""
    try:
        if not interaction.user.guild_permissions.manage_messages:
            embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Gerenciar Mensagens'", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Verificar se está em um canal de partida
        if not interaction.channel.name.startswith('🎮-partida-'):
            embed = create_embed("❌ Canal inválido", "Este comando só funciona em canais de partida!", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Buscar match no banco com tratamento de erro
        try:
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM copinha_matches WHERE ticket_channel_id = %s', (interaction.channel.id,))
                match = cursor.fetchone()

                if not match:
                    conn.close()
                    embed = create_embed("❌ Partida não encontrada", "Esta partida não está registrada no sistema!", color=0xff0000)
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Verificar se partida já foi finalizada
                if isinstance(match, dict):
                    match_status = match.get('status', 'waiting')
                    match_id = match.get('id')
                    copinha_id = match.get('copinha_id')
                    round_name = match.get('round_name')
                    match_number = match.get('match_number')
                    players_json = match.get('players', '[]')
                else:
                    match_status = match[8] if len(match) > 8 else 'waiting'
                    match_id = match[0]
                    copinha_id = match[1]
                    round_name = match[2]
                    match_number = match[3]
                    players_json = match[4]

                if match_status == 'finished':
                    conn.close()
                    embed = create_embed("❌ Partida já finalizada", "Esta partida já tem um vencedor definido!", color=0xff0000)
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Verificar se vencedor está na partida
                try:
                    players = json.loads(players_json) if players_json else []
                except json.JSONDecodeError:
                    players = []

                if vencedor.id not in players:
                    conn.close()
                    embed = create_embed("❌ Jogador inválido", "Este jogador não está nesta partida!", color=0xff0000)
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Atualizar match como finalizado
                cursor.execute('UPDATE copinha_matches SET winner_id = %s, status = %s WHERE id = %s', 
                             (vencedor.id, 'finished', match_id))

                # Buscar dados da copinha
                cursor.execute('SELECT * FROM copinhas WHERE id = %s', (copinha_id,))
                copinha = cursor.fetchone()

                if not copinha:
                    conn.close()
                    embed = create_embed("❌ Copinha não encontrada", "Dados da copinha não foram encontrados!", color=0xff0000)
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                conn.commit()
                conn.close()

        except Exception as db_error:
            logger.error(f"Erro no banco ao definir vencedor: {db_error}")
            embed = create_embed("❌ Erro no banco de dados", "Tente novamente em alguns segundos.", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Extrair dados da copinha de forma segura
        if isinstance(copinha, dict):
            copinha_title = copinha.get('title', 'Copinha')
        else:
            copinha_title = copinha[4] if len(copinha) > 4 else 'Copinha'

        # Anunciar vencedor
        embed = create_embed(
            "🏆 Vencedor Definido!",
            f"""**🎮 Partida {match_number} - {round_name}**
**🏆 Copinha:** {copinha_title}

**🎉 Vencedor:** {vencedor.mention}
**📊 Resultado confirmado por:** {interaction.user.mention}

**✅ O vencedor avançou para a próxima fase!**
*Este canal será arquivado em breve.*""",
            color=0xffd700
        )

        await interaction.response.send_message(embed=embed)

        # Verificar se precisa criar próxima rodada (com tratamento de erro)
        try:
            await check_next_round(copinha_id)
        except Exception as round_error:
            logger.error(f"Erro ao verificar próxima rodada: {round_error}")
            # Não falhar o comando principal por causa disso

        # Arquivar canal após 30 segundos
        try:
            await asyncio.sleep(30)
            await interaction.channel.edit(name=f"🏁-finalizada-{match_number}", archived=True)
        except Exception as archive_error:
            logger.error(f"Erro ao arquivar canal: {archive_error}")

        logger.info(f"Vencedor definido: {vencedor.name} na partida {match_number} da copinha {copinha_title}")

    except Exception as e:
        logger.error(f"Erro geral ao definir vencedor: {e}")
        try:
            await interaction.response.send_message("❌ Erro ao definir vencedor! Tente novamente.", ephemeral=True)
        except:
            await interaction.followup.send("❌ Erro ao definir vencedor! Tente novamente.", ephemeral=True)

async def check_next_round(copinha_id):
    """Verificar se todas as partidas da rodada terminaram para criar próxima"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Buscar copinha
            cursor.execute('SELECT * FROM copinhas WHERE id = %s', (copinha_id,))
            copinha = cursor.fetchone()
            
            if not copinha:
                conn.close()
                return
            
            # Extrair current_round de forma segura
            if isinstance(copinha, dict):
                current_round = copinha.get('current_round', 'inscricoes')
            else:
                current_round = copinha[10] if len(copinha) > 10 else 'inscricoes'  # current_round está no índice 10
            
            # Verificar partidas pendentes da rodada atual (normalizar para pesquisa)
            current_round_normalized = current_round.lower().strip()
            cursor.execute('SELECT COUNT(*) FROM copinha_matches WHERE copinha_id = %s AND LOWER(round_name) = %s AND status = %s', 
                         (copinha_id, current_round_normalized, 'waiting'))
            pending_result = cursor.fetchone()
            pending_matches = pending_result[0] if pending_result else 0
            
            logger.info(f"Verificando rodada {current_round}: {pending_matches} partidas pendentes")
            
            if pending_matches == 0:
                # Todas as partidas terminaram, buscar vencedores (normalizar para pesquisa)
                cursor.execute('SELECT * FROM copinha_matches WHERE copinha_id = %s AND LOWER(round_name) = %s AND status = %s', 
                             (copinha_id, current_round_normalized, 'finished'))
                finished_matches = cursor.fetchall()
                
                if not finished_matches:
                    conn.close()
                    logger.warning(f"Nenhuma partida finalizada encontrada para copinha {copinha_id}")
                    return
                
                # Extrair IDs dos vencedores de forma segura
                winners = []
                for match in finished_matches:
                    if isinstance(match, dict):
                        winner_id = match.get('winner_id')
                    else:
                        winner_id = match[5] if len(match) > 5 else None
                    
                    if winner_id:
                        winners.append(winner_id)
                
                logger.info(f"Vencedores da rodada {current_round}: {len(winners)}")
                
                # Verificar se número de vencedores é válido para próxima rodada
                if len(winners) % 2 != 0 and len(winners) > 1:
                    logger.warning(f"Número ímpar de vencedores ({len(winners)}) - impossível criar próxima rodada")
                    # Não fazer nada, deixar como está
                    conn.close()
                    return
                
                if len(winners) == 1:
                    # É o vencedor final!
                    logger.info(f"Copinha {copinha_id} finalizada - campeão: {winners[0]}")
                    await announce_tournament_winner(copinha, winners[0])
                    
                    # Marcar copinha como finalizada
                    cursor.execute('UPDATE copinhas SET status = %s, current_round = %s WHERE id = %s', 
                                 ('finished', 'finalizada', copinha_id))
                    conn.commit()
                    
                elif len(winners) >= 2:
                    # Criar próxima rodada
                    logger.info(f"Criando próxima rodada com {len(winners)} vencedores")
                    await create_next_round(copinha, winners, current_round, copinha_id, None)
                else:
                    logger.warning(f"Número insuficiente de vencedores: {len(winners)}")
            
            conn.close()
            
    except Exception as e:
        logger.error(f"Erro ao verificar próxima rodada: {e}")
        import traceback
        logger.error(traceback.format_exc())

async def create_next_round(copinha, winners, current_round, copinha_id, forced_category=None):
    """Criar próxima rodada do torneio"""
    try:
        # Extrair dados da copinha de forma segura
        if isinstance(copinha, dict):
            guild_id = copinha.get('guild_id')
            team_format = copinha.get('team_format', '1v1')
            copinha_title = copinha.get('title', 'Copinha')
            copinha_map = copinha.get('map_name', 'Desconhecido')
        else:
            guild_id = copinha[1] if len(copinha) > 1 else None
            team_format = copinha[7] if len(copinha) > 7 else '1v1'
            copinha_title = copinha[5] if len(copinha) > 5 else 'Copinha'
            copinha_map = copinha[6] if len(copinha) > 6 else 'Desconhecido'

        if not guild_id:
            logger.error("Guild ID não encontrado para criar próxima rodada")
            return

        guild = bot.get_guild(guild_id)
        if not guild:
            logger.error(f"Guild {guild_id} não encontrada")
            return

        # Determinar nome da próxima rodada (normalizar case)
        current_round_normalized = current_round.lower().strip()
        
        round_progression = {
            'inscricoes': 'primeira_rodada',
            'primeira_rodada': 'quartas',
            'quartas': 'semifinal',
            'semifinal': 'final'
        }
        
        next_round_key = round_progression.get(current_round_normalized, 'proxima_rodada')
        
        # Nome amigável para exibição
        round_display_names = {
            'primeira_rodada': 'Primeira Rodada',
            'quartas': 'Quartas de Final',
            'semifinal': 'Semifinal',
            'final': 'Final'
        }
        
        next_round_name = round_display_names.get(next_round_key, 'Próxima Rodada')

        # Usar categoria fornecida ou encontrar categoria da copinha
        category = forced_category
        if not category:
            # Busca mais robusta por categoria existente
            search_terms = [
                copinha_title[:20],  # Primeira busca: primeiros 20 caracteres
                copinha_title.lower()[:15],  # Segunda busca: 15 caracteres minúsculos
                f"🏆 {copinha_title[:15]}"  # Terceira busca: com emoji
            ]
            
            for cat in guild.categories:
                for search_term in search_terms:
                    if search_term.lower() in cat.name.lower():
                        category = cat
                        break
                if category:
                    break

        if not category:
            logger.error(f"Categoria da copinha '{copinha_title}' não encontrada")
            logger.info(f"Categorias disponíveis: {[c.name for c in guild.categories]}")
            return

        # Determinar teams para a próxima rodada
        winner_teams = []
        
        if current_round_normalized == 'inscricoes':
            # Primeira rodada: organizar participantes em times
            team_size = int(team_format[0]) if team_format[0].isdigit() else 1
            
            # Embaralhar para distribuição aleatória
            import random
            shuffled_winners = winners.copy()
            random.shuffle(shuffled_winners)
            
            # Agrupar em times
            for i in range(0, len(shuffled_winners), team_size):
                team = shuffled_winners[i:i + team_size]
                if len(team) == team_size:  # Só adicionar se o time estiver completo
                    winner_teams.append(team)
        else:
            # Rodadas posteriores: buscar dados dos vencedores de partidas anteriores  
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                for winner_id in winners:
                    # Buscar o match onde este jogador venceu para pegar os dados da equipe
                    cursor.execute('''
                        SELECT players FROM copinha_matches 
                        WHERE copinha_id = %s AND winner_id = %s AND status = %s
                    ''', (copinha_id, winner_id, 'finished'))
                    
                    match_data = cursor.fetchone()
                    if match_data:
                        try:
                            players_data = json.loads(match_data[0])
                            
                            # Determinar qual equipe venceu
                            if isinstance(players_data, dict) and 'team1' in players_data:
                                # Novo formato com equipes
                                if winner_id in players_data['team1']:
                                    winner_teams.append(players_data['team1'])
                                elif winner_id in players_data['team2']:
                                    winner_teams.append(players_data['team2'])
                            else:
                                # Formato antigo - assumir 1v1
                                winner_teams.append([winner_id])
                        except (json.JSONDecodeError, KeyError):
                            # Fallback para formato antigo
                            winner_teams.append([winner_id])
                
                conn.close()

        # Criar matches da próxima rodada
        num_matches = len(winner_teams) // 2
        
        with db_lock:
            for i in range(num_matches):
                team1 = winner_teams[i * 2]
                team2 = winner_teams[i * 2 + 1]

                # Criar canal para a partida
                match_channel = await guild.create_text_channel(
                    f"🏆-{next_round_key}-{i+1}",
                    category=category
                )

                # Dar permissão aos jogadores das duas equipes
                await match_channel.set_permissions(guild.default_role, read_messages=False)
                
                # Permissões para time 1
                for player_id in team1:
                    member = guild.get_member(player_id)
                    if member:
                        await match_channel.set_permissions(member, read_messages=True, send_messages=True)
                
                # Permissões para time 2
                for player_id in team2:
                    member = guild.get_member(player_id)
                    if member:
                        await match_channel.set_permissions(member, read_messages=True, send_messages=True)

                # Salvar match no banco (usar key normalizada para consistência)
                cursor.execute('''
                    INSERT INTO copinha_matches (copinha_id, round_name, match_number, players, ticket_channel_id, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    copinha_id,
                    next_round_key,  # Usar versão normalizada para pesquisas consistentes
                    i + 1,
                    json.dumps({'team1': team1, 'team2': team2}),
                    match_channel.id,
                    'waiting'
                ))
                
                # Capturar ID do match inserido
                match_id = cursor.fetchone()[0]

                # Buscar creator_id da copinha
                cursor.execute('SELECT creator_id FROM copinhas WHERE id = %s', (copinha_id,))
                creator_result = cursor.fetchone()
                creator_id = creator_result[0] if creator_result else None

                # Criar embed da partida
                team1_display = format_team_display_simple(team1, "🔴", team_format)
                team2_display = format_team_display_simple(team2, "🔵", team_format)
                
                match_embed = create_embed(
                    f"🏆 {next_round_name} - Partida {i+1}",
                    f"""**🏆 Copinha:** {copinha_title}
**🗺️ Mapa:** {copinha_map}
**👥 Formato:** {team_format}

**⚔️ {next_round_name}:**
{team1_display}

VS

{team2_display}

**📋 Instruções:**
1. Coordenem o horário da partida entre as equipes
2. Joguem no mapa **{copinha_map}** no formato **{team_format}**
3. Após a partida, clique em um dos botões abaixo para definir o vencedor

**🎯 Boa sorte para ambas as equipes!**""",
                    color=0xffd700
                )

                # Criar view com botões para escolher vencedor
                winner_view = MatchWinnerView(
                    copinha_id=copinha_id,
                    match_id=match_id,
                    team1=team1,
                    team2=team2,
                    creator_id=creator_id,
                    team_format=team_format
                )

                # Registrar view persistente no bot
                bot.add_view(winner_view)

                # Enviar mensagem com view
                message = await match_channel.send(embed=match_embed, view=winner_view)

                # Salvar view persistente no banco para restaurar após restart
                save_interactive_message(
                    message.id,
                    match_channel.id,
                    guild.id,
                    'match_winner',
                    {
                        'copinha_id': copinha_id,
                        'match_id': match_id,
                        'team1': team1,
                        'team2': team2,
                        'creator_id': creator_id,
                        'team_format': team_format
                    }
                )

            # Atualizar rodada atual da copinha
            cursor.execute('UPDATE copinhas SET current_round = %s WHERE id = %s', 
                         (next_round_key, copinha_id))
            conn.commit()
            conn.close()

        logger.info(f"Próxima rodada '{next_round_name}' criada com {num_matches} partidas")

    except Exception as e:
        logger.error(f"Erro ao criar próxima rodada: {e}")
        import traceback
        logger.error(traceback.format_exc())

def format_team_display_simple(team, emoji, team_format):
    """Função auxiliar para formatar exibição da equipe"""
    if team_format.lower() == '1v1':
        return f"{emoji} <@{team[0]}>"
    else:
        return f"{emoji} **Equipe:** " + " & ".join([f"<@{p}>" for p in team])

async def announce_tournament_winner(copinha, winner_id):
    """Anunciar vencedor do torneio"""
    try:
        # Extrair dados da copinha de forma segura
        if isinstance(copinha, dict):
            guild_id = copinha.get('guild_id')
            channel_id = copinha.get('channel_id')
            copinha_title = copinha.get('title', 'Copinha')
            copinha_map = copinha.get('map_name', 'N/A')
            copinha_format = copinha.get('team_format', 'N/A')
            creator_id = copinha.get('creator_id')
            copinha_id = copinha.get('id')
        else:
            guild_id = copinha[1] if len(copinha) > 1 else None
            channel_id = copinha[3] if len(copinha) > 3 else None
            copinha_title = copinha[4] if len(copinha) > 4 else 'Copinha'
            copinha_map = copinha[5] if len(copinha) > 5 else 'N/A'
            copinha_format = copinha[6] if len(copinha) > 6 else 'N/A'
            creator_id = copinha[2] if len(copinha) > 2 else None
            copinha_id = copinha[0] if len(copinha) > 0 else None

        if not guild_id or not channel_id:
            logger.error("Dados insuficientes da copinha para anunciar vencedor")
            return

        guild = bot.get_guild(guild_id)
        if not guild:
            logger.error(f"Guild {guild_id} não encontrada")
            return
            
        winner = guild.get_member(winner_id)
        if not winner:
            logger.error(f"Vencedor {winner_id} não encontrado no servidor")
            return
            
        # Canal principal onde foi criada a copinha
        channel = guild.get_channel(channel_id)
        if not channel:
            logger.error(f"Canal {channel_id} não encontrado")
            return

        # Contar participantes
        try:
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM copinha_matches WHERE copinha_id = %s', (copinha_id,))
                result = cursor.fetchone()
                total_matches = result[0] if result else 0
                total_participants = total_matches * 2  # Estimativa
                conn.close()
        except:
            total_participants = "N/A"
            
        embed = create_embed(
            f"🏆 {copinha_title} - CAMPEÃO!",
            f"""**🎉 PARABÉNS AO CAMPEÃO! 🎉**

**👑 Campeão:** {winner.mention}
**🏆 Torneio:** {copinha_title}
**🗺️ Mapa:** {copinha_map}
**👥 Formato:** {copinha_format}

**🎊 Você é oficialmente o campeão desta copinha!**

**📊 Estatísticas:**
• Total de participantes: {total_participants}
• Organizador: <@{creator_id}>
• Data de conclusão: <t:{int(datetime.datetime.now().timestamp())}:F>

**🎁 Parabéns pela vitória épica!** 🎁""",
            color=0xffd700
        )
        
        await channel.send(embed=embed)
        
        # Dar coins de prêmio ao vencedor e 1 ponto no scoreboard
        try:
            prize_coins = 1000  # Prêmio base
            user_data = get_user_data(winner_id)
            if user_data:
                current_coins = user_data[1] if user_data and len(user_data) > 1 else 50
                new_coins = current_coins + prize_coins
                
                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (new_coins, winner_id))
                    cursor.execute('''INSERT INTO transactions (user_id, guild_id, type, amount, description)
                                     VALUES (%s, %s, %s, %s, %s)''',
                                  (winner_id, guild_id, 'tournament_win', prize_coins, f"Venceu a copinha: {copinha_title}"))
                    conn.commit()
                    conn.close()
                
                # Adicionar 1 ponto no scoreboard da copinha
                points_added = add_copinha_points(guild_id, winner_id, winner.display_name, 1, "vitoria_copinha")
                
                prize_embed = create_embed(
                    "🏆 Prêmio do Campeão!",
                    f"**{winner.mention}** ganhou:\n"
                    f"💰 **{prize_coins:,} coins**\n"
                    f"🏆 **1 troféu** (Total: {points_added} troféus)",
                    color=0xffd700
                )
                await channel.send(embed=prize_embed)
        except Exception as prize_error:
            logger.error(f"Erro ao dar prêmio ao vencedor: {prize_error}")
            
        logger.info(f"Copinha {copinha_title} finalizada - campeão: {winner.name}")
        
    except Exception as e:
        logger.error(f"Erro ao anunciar vencedor: {e}")
        import traceback
        logger.error(traceback.format_exc())


@bot.tree.command(name="modlogs", description="Ver logs de moderação")
async def slash_modlogs(interaction: discord.Interaction, usuario: discord.Member = None, limite: int = 10):
    """Ver logs de moderação"""
    try:
        if not interaction.user.guild_permissions.view_audit_log:
            embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Ver Logs de Auditoria'", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if limite < 1 or limite > 50:
            embed = create_embed("❌ Limite inválido", "Use entre 1 e 50 registros", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            if usuario:
                cursor.execute('''SELECT * FROM moderation_logs 
                                 WHERE guild_id = %s AND user_id = %s 
                                 ORDER BY timestamp DESC LIMIT %s''',
                              (interaction.guild.id, usuario.id, limite))
            else:
                cursor.execute('''SELECT * FROM moderation_logs 
                                 WHERE guild_id = %s 
                                 ORDER BY timestamp DESC LIMIT %s''',
                              (interaction.guild.id, limite))

            logs = cursor.fetchall()
            conn.close()

        if not logs:
            embed = create_embed("📋 Logs de Moderação", "Nenhum registro encontrado", color=0x7289da)
            await interaction.response.send_message(embed=embed)
            return

        logs_text = ""
        for log in logs:
            timestamp = datetime.datetime.fromisoformat(log[7]).strftime('%d/%m/%Y %H:%M')
            user_mention = f"<@{log[2]}>"
            mod_mention = f"<@{log[3]}>"
            action_emojis = {
                'warn': '⚠️', 'ban': '🔨', 'kick': '👢', 'timeout': '⏰',
                'massban': '🔥', 'unban': '✅'
            }
            emoji = action_emojis.get(log[4], '📋')

            logs_text += f"{emoji} **{log[4].title()}** - {user_mention}\n"
            logs_text += f"📅 {timestamp} por {mod_mention}\n"
            if log[5]:
                logs_text += f"💬 {log[5][:50]}{'...' if len(log[5]) > 50 else ''}\n"
            logs_text += "\n"

        embed = create_embed(
            f"📋 Logs de Moderação{f' - {usuario.display_name}' if usuario else ''}",
            logs_text[:4000],  # Discord limit
            color=0x7289da
        )
        embed.set_footer(text=f"Mostrando {len(logs)} registros mais recentes")

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Erro nos modlogs: {e}")
        await interaction.response.send_message("Erro ao carregar logs!", ephemeral=True)

@bot.tree.command(name="unban", description="Desbanir usuário")
async def slash_unban(interaction: discord.Interaction, usuario_id: str, motivo: str = "Não especificado"):
    """Desbanir usuário"""
    try:
        if not interaction.user.guild_permissions.ban_members:
            embed = create_embed("❌ Sem permissão", "Você precisa da permissão 'Banir Membros'", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            user_id = int(usuario_id)
        except ValueError:
            embed = create_embed("❌ ID inválido", "Forneça um ID de usuário válido", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            user = await bot.fetch_user(user_id)
        except discord.NotFound:
            embed = create_embed("❌ Usuário não encontrado", "ID de usuário inválido", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            await interaction.guild.unban(user, reason=f"Por {interaction.user}: {motivo}")
        except discord.NotFound:
            embed = create_embed("❌ Não banido", "Este usuário não está banido", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Registrar no banco
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason)
                             VALUES (%s, %s, %s, %s, %s)''',
                          (interaction.guild.id, user_id, interaction.user.id, 'unban', motivo))
            conn.commit()
            conn.close()

        embed = create_embed(
            "✅ Usuário Desbanido",
            f"**Usuário:** {user.name}#{user.discriminator}\n"
            f"**ID:** {user.id}\n"
            f"**Motivo:** {motivo}\n"
            f"**Moderador:** {interaction.user.mention}",
            color=0x00ff00
        )

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Erro no unban: {e}")
        await interaction.response.send_message("Erro ao desbanir usuário!", ephemeral=True)

# ========== UTILIDADES (20 COMANDOS) ==========

# COMANDOS ESPECIAIS FINAIS PARA COMPLETAR OS 300+!

    # Set initial status com retry
    try:
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"🚀 {len(bot.guilds)} servidores | Use / para slash commands!"
            )
        )
        logger.info("✅ Status inicial configurado")
    except Exception as e:
        logger.error(f"Erro ao configurar status: {e}")

    print("🔥 Kaori está online! Pronto para comandar!")
    print(f"✨ TODOS os {len(synced) if 'synced' in locals() else 'Muitos'} slash commands disponíveis!")
    print("📋 Use / no Discord para ver TODOS os comandos disponíveis!")
    print("🎯 Sistema dual: Use / ou RX - Ambos funcionam!")

    # Log dos comandos slash ativos
    if 'synced' in locals():
        logger.info(f"🎮 Comandos slash ativos: {len(synced)}")
        for cmd in synced[:10]:  # Mostrar primeiros 10
            logger.info(f"   /{cmd.name} - {cmd.description}")
        if len(synced) > 10:
            logger.info(f"   ... e mais {len(synced) - 10} comandos!")

    # Executar limpeza de memória inicial
    try:
        import gc
        gc.collect()
        logger.info("🧹 Limpeza de memória inicial concluída")
    except:
        pass

# Eventos de conexão removidos para evitar conflitos

# Handler de erros para slash commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Handle slash command errors"""
    try:
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            embed = create_embed(
                "⏰ Comando em Cooldown",
                f"Aguarde {error.retry_after:.1f} segundos antes de usar novamente.",
                color=0xff6600
            )
            await safe_send_response(interaction, embed, ephemeral=True)
        elif isinstance(error, discord.app_commands.MissingPermissions):
            embed = create_embed(
                "❌ Sem Permissão",
                "Você não tem permissão para usar este comando.",
                color=0xff0000
            )
            await safe_send_response(interaction, embed, ephemeral=True)
        elif isinstance(error, discord.app_commands.BotMissingPermissions):
            embed = create_embed(
                "❌ Bot Sem Permissão",
                "O bot não tem as permissões necessárias para executar este comando.",
                color=0xff0000
            )
            await safe_send_response(interaction, embed, ephemeral=True)
        else:
            logger.error(f"Erro em slash command {interaction.command.name if interaction.command else 'desconhecido'}: {error}")
            embed = create_embed(
                "❌ Erro Interno",
                "Ocorreu um erro inesperado. Tente novamente.",
                color=0xff0000
            )
            await safe_send_response(interaction, embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Erro no handler de slash commands: {e}")

# Evento para capturar erros críticos do bot
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
    except Exception as e:
        logger.error(f"Erro ao enviar alerta de erro: {e}")



# Sistema de reconexão automática removido para economizar recursos

@bot.event
async def on_guild_join(guild):
    global_stats['guilds_joined'] += 1
    logger.info(f"📈 Entrei no servidor: {guild.name} ({guild.id})")

    # Initialize guild data
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO guilds (guild_id, name) VALUES (%s, %s)', (guild.id, guild.name))
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

        # Verificar se é o usuário correto para este tipo de interação
        if game_data.get('type') in ['ticket_creation', 'ticket_confirmation', 'ticket_tier_confirmation', 'clear_confirmation', 'ban_confirmation']:
            if game_data.get('user') != user.id:
                # Remover reação de usuário não autorizado
                try:
                    await reaction.remove(user)
                except:
                    pass
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

                    # Editar mensagem original para mostrar que foi processado
                    embed = create_embed(
                        "✅ Ticket Criado!",
                        f"Seu ticket foi criado com sucesso!\n**Motivo:** {motivo}",
                        color=0x00ff00
                    )
                    await message.edit(embed=embed)
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

                    # Editar mensagem de confirmação
                    embed = create_embed(
                        "✅ Ticket Criado!",
                        f"Seu ticket foi criado com sucesso!\n**Motivo:** {motivo}",
                        color=0x00ff00
                    )
                    await message.edit(embed=embed)
                    del active_games[message.id]
                except Exception as e:
                    logger.error(f"Erro ao criar ticket: {e}")

            elif str(reaction.emoji) == "❌":
                embed = create_embed("❌ Ticket Cancelado", "Criação de ticket cancelada pelo usuário.", color=0xff6b6b)
                await message.edit(embed=embed)
                del active_games[message.id]

# Função auxiliar para criar tickets
async def create_ticket_channel(ctx, motivo, user):
    """Criar canal de ticket"""
    try:
        guild = ctx.guild

        # Verificar se existe categoria de tickets
        ticket_category = discord.utils.get(guild.categories, name="📋 Tickets")
        
        if not ticket_category:
            # Criar categoria se não existir
            ticket_category = await guild.create_category("📋 Tickets")

        # Nome do canal
        channel_name = f"ticket-{user.name}-{user.discriminator}"
        
        # Criar canal
        ticket_channel = await guild.create_text_channel(
            channel_name,
            category=ticket_category
        )

        # Configurar permissões
        await ticket_channel.set_permissions(guild.default_role, read_messages=False)
        await ticket_channel.set_permissions(user, read_messages=True, send_messages=True)
        
        # Dar permissão para staff
        for role in guild.roles:
            if any(keyword in role.name.lower() for keyword in ['admin', 'mod', 'staff', 'suporte']):
                await ticket_channel.set_permissions(role, read_messages=True, send_messages=True)

        # Salvar ticket no banco
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tickets (guild_id, creator_id, channel_id, status, reason)
                VALUES (%s, %s, %s, %s, %s)
            ''', (guild.id, user.id, ticket_channel.id, 'open', motivo))
            conn.commit()
            conn.close()

        # Embed de boas-vindas
        welcome_embed = create_embed(
            "🎫 Ticket Criado",
            f"""**Bem-vindo, {user.mention}!**

**📋 Motivo:** {motivo}
**🕐 Criado:** <t:{int(datetime.datetime.now().timestamp())}:F>

**👥 Equipe de suporte será notificada em breve!**

Para fechar este ticket, reaja com 🔒 em qualquer mensagem.

*Descreva seu problema detalhadamente para um atendimento mais rápido.*""",
            color=0x00ff00
        )

        message = await ticket_channel.send(embed=welcome_embed)
        await message.add_reaction("🔒")

        logger.info(f"Ticket criado: {channel_name} por {user.name}")

    except Exception as e:
        logger.error(f"Erro ao criar ticket: {e}")
        raise e

        # Ticket tier confirmation removido - usará modais
        # Sistemas de confirmação antigos removidos - agora usam botões
        # Stumble guys event removido - usará modais
        # Trade invitation removido - usará modais
        pass  # Placeholder para manter estrutura

    # Sistema de fechar tickets com BOTÕES - NOVO SISTEMA
    if str(reaction.emoji) == "🔒" and hasattr(message.channel, 'name') and message.channel.name.startswith('ticket-'):
        # Verificar se usuário tem permissão OU é o criador do ticket
        has_permission = False
        is_creator = False

        # Verificar permissões de forma mais segura
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
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT creator_id FROM tickets WHERE channel_id = %s', (message.channel.id,))
                result = cursor.fetchone()
                if result and result[0] == user.id:
                    is_creator = True
                conn.close()
        except Exception as e:
            logger.error(f"Erro ao verificar criador do ticket: {e}")

        if not (has_permission or is_creator):
            # Remover a reação do usuário não autorizado
            try:
                await reaction.remove(user)
            except:
                pass

            # Enviar mensagem de erro temporária
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

        # Remover a reação para limpar
        try:
            await reaction.remove(user)
        except:
            pass

        # Confirmar fechamento com BOTÕES (sem tempo limite)
        confirm_embed = create_embed(
            "🔒 Fechar Ticket?",
            f"**{user.mention}** deseja fechar este ticket?\n\n"
            f"**⚠️ Esta ação é irreversível!**\n"
            f"O canal será **DELETADO** permanentemente!\n\n"
            f"**🎯 Use os botões abaixo para confirmar ou cancelar.**\n"
            f"**✨ Sem tempo limite - decida quando quiser!**",
            color=0xff6b6b
        )

        try:
            view = CloseTicketView(user.id)
            await message.channel.send(embed=confirm_embed, view=view)

        except Exception as e:
            logger.error(f"Erro ao criar confirmação de fechamento: {e}")
            error_embed = create_embed(
                "❌ Erro",
                "Erro ao processar fechamento do ticket. Tente novamente.",
                color=0xff0000
            )
            try:
                await message.channel.send(embed=error_embed, delete_after=10)
            except:
                pass

    # Sistema de chuva de moedas
    if message.id in active_games:
        game_data = active_games[message.id]

        if game_data['type'] == 'coin_rain' and str(reaction.emoji) == "💰":
            if user.id not in game_data['participants'] and len(game_data['participants']) < game_data['max_participants']:
                game_data['participants'].append(user.id)

                # Se chegou no limite, distribuir prêmios
                if len(game_data['participants']) >= game_data['max_participants']:
                    total_coins = game_data['total_coins']
                    coins_per_user = total_coins // game_data['max_participants']

                    winners = []
                    try:
                        with db_lock:
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            for participant_id in game_data['participants']:
                                user_data = get_user_data(participant_id)
                                if user_data:
                                    new_coins = user_data[1] + coins_per_user
                                    cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (new_coins, participant_id))
                                    participant = bot.get_user(participant_id)
                                    if participant:
                                        winners.append(participant.mention)
                            conn.commit()
                            conn.close()
                    except Exception as e:
                        logger.error(f"Erro na distribuição da chuva de moedas: {e}")


                    # Anunciar vencedores
                    embed = create_embed(
                        "💰 Chuva de Moedas Finalizada!",
                        f"🎉 **Vencedores:**\n{', '.join(winners)}\n\n"
                        f"💰 **Prêmio individual:** {coins_per_user:,} moedas\n"
                        f"🏆 **Total distribuído:** {total_coins:,} moedas",
                        color=0xffd700
                    )
                    await message.edit(embed=embed)

                    del active_games[message.id]

@bot.event
async def on_member_join(member):
    """Enviar mensagem de boas-vindas personalizada quando alguém entrar no servidor"""
    if member.bot:
        return

    try:
        # Canal específico para boas-vindas
        welcome_channel_id = 1398027575028220013  # <#1398027575028220013>
        welcome_channel = bot.get_channel(welcome_channel_id)

        if not welcome_channel:
            logger.error(f"Canal de boas-vindas {welcome_channel_id} não encontrado!")
            return

        # Buscar dados do usuário para personalizar ainda mais
        user_data = get_user_data(member.id)
        if not user_data:
            update_user_data(member.id)
            user_data = get_user_data(member.id)

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
        leveled_up, new_level, rank_up, new_rank_id, old_rank_id = add_xp(member.id, 25)  # XP bônus para novos membros
        
        # Criar cargos de rank se não existirem e atribuir cargo inicial
        if member.guild:
            try:
                await ensure_rank_roles(member.guild)
                await update_user_rank_role(member, new_rank_id)
            except Exception as e:
                logger.error(f"Erro ao configurar cargo inicial para {member.name}: {e}")

    except Exception as e:
        logger.error(f"Erro ao enviar boas-vindas para {member.name}: {e}")

        # Tentar enviar mensagem simples se o embed falhar
        try:
            if welcome_channel:
                await welcome_channel.send(f"🎉 Bem-vindo(a) {member.mention} ao {member.guild.name}! 🎉")
        except:
            pass

# Health monitor removido para economizar recursos no Railway

# Sistema de emergência removido para economizar recursos

# ============ SISTEMA DE TICKETS COMPLETO ============

# ============ SISTEMA DE FEEDBACK PÚBLICO ============

# Modal para feedback do staff
class StaffFeedbackModal(discord.ui.Modal, title="📊 Avaliação do Staff"):
    def __init__(self, staff_name):
        super().__init__()
        self.staff_name = staff_name

    atendimento = discord.ui.TextInput(
        label="⭐ Nota do Atendimento (0-10)",
        placeholder="Digite uma nota de 0 a 10",
        required=True,
        max_length=2
    )

    qualidade = discord.ui.TextInput(
        label="🎯 Nota da Qualidade (0-10)",
        placeholder="Digite uma nota de 0 a 10", 
        required=True,
        max_length=2
    )

    rapidez = discord.ui.TextInput(
        label="⚡ Nota da Rapidez (0-10)",
        placeholder="Digite uma nota de 0 a 10",
        required=True,
        max_length=2
    )

    profissionalismo = discord.ui.TextInput(
        label="🤝 Nota do Profissionalismo (0-10)",
        placeholder="Digite uma nota de 0 a 10",
        required=True,
        max_length=2
    )

    comentarios = discord.ui.TextInput(
        label="💭 Comentários (Opcional)",
        placeholder="Deixe comentários sobre o atendimento...",
        required=False,
        max_length=500,
        style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validar notas
            notas = {}
            try:
                notas['atendimento'] = int(self.atendimento.value)
                notas['qualidade'] = int(self.qualidade.value)
                notas['rapidez'] = int(self.rapidez.value)
                notas['profissionalismo'] = int(self.profissionalismo.value)

                # Verificar se todas as notas estão entre 0 e 10
                for categoria, nota in notas.items():
                    if nota < 0 or nota > 10:
                        await interaction.response.send_message(f"❌ A nota de {categoria} deve estar entre 0 e 10!", ephemeral=True)
                        return

            except ValueError:
                await interaction.response.send_message("❌ Todas as notas devem ser números válidos entre 0 e 10!", ephemeral=True)
                return

            # Calcular média
            media = round(sum(notas.values()) / len(notas), 1)

            # Determinar qualidade baseada na média
            if media >= 9:
                emoji = "🌟"
                cor = 0x00ff00
                qualidade_texto = "Excelente"
            elif media >= 7:
                emoji = "⭐"
                cor = 0xffaa00
                qualidade_texto = "Bom"
            elif media >= 5:
                emoji = "⚠️"
                cor = 0xff6600
                qualidade_texto = "Regular"
            else:
                emoji = "❌"
                cor = 0xff0000
                qualidade_texto = "Ruim"

            # Salvar no banco de dados
            try:
                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()

                    # Criar tabela de feedback de staff se não existir
                    cursor.execute('''CREATE TABLE IF NOT EXISTS staff_feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        staff_name TEXT,
                        avaliador_id INTEGER,
                        nota_atendimento INTEGER,
                        nota_qualidade INTEGER,
                        nota_rapidez INTEGER,
                        nota_profissionalismo INTEGER,
                        media_final REAL,
                        comentarios TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )''')

                    cursor.execute('''
                        INSERT INTO staff_feedback (guild_id, staff_name, avaliador_id, nota_atendimento, nota_qualidade, nota_rapidez, nota_profissionalismo, media_final, comentarios)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        interaction.guild.id,
                        self.staff_name,
                        interaction.user.id,
                        notas['atendimento'],
                        notas['qualidade'],
                        notas['rapidez'],
                        notas['profissionalismo'],
                        media,
                        self.comentarios.value or "Sem comentários"
                    ))

                    conn.commit()
                    conn.close()
            except Exception as e:
                logger.error(f"Erro ao salvar feedback do staff: {e}")

            # Resposta ao usuário
            embed = create_embed(
                f"{emoji} Feedback Registrado - {qualidade_texto}",
                f"""**📊 Avaliação do Staff: {self.staff_name}**

**📋 Notas:**
• ⭐ Atendimento: {notas['atendimento']}/10
• 🎯 Qualidade: {notas['qualidade']}/10  
• ⚡ Rapidez: {notas['rapidez']}/10
• 🤝 Profissionalismo: {notas['profissionalismo']}/10

**📈 Média Final: {media}/10**
**🏆 Qualidade: {qualidade_texto}**

**💭 Comentários:** {self.comentarios.value or "Nenhum"}

**👤 Avaliado por:** {interaction.user.mention}
**📅 Data:** <t:{int(datetime.datetime.now().timestamp())}:R>

*Obrigado pela sua avaliação! Isso nos ajuda a melhorar nosso atendimento.*""",
                color=cor
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

            # Enviar para canal de feedback
            try:
                feedback_channel = interaction.guild.get_channel(1401195599281393754)
                if feedback_channel:
                    public_embed = create_embed(
                        f"{emoji} Nova Avaliação de Staff",
                        f"""**👥 Staff Avaliado:** {self.staff_name}
**📊 Média Final:** {media}/10 ({qualidade_texto})

**📋 Detalhes:**
• ⭐ Atendimento: {notas['atendimento']}/10
• 🎯 Qualidade: {notas['qualidade']}/10  
• ⚡ Rapidez: {notas['rapidez']}/10
• 🤝 Profissionalismo: {notas['profissionalismo']}/10

**💭 Comentários:** {self.comentarios.value or "Nenhum"}

**👤 Avaliado por:** {interaction.user.mention}
**📅 Data:** <t:{int(datetime.datetime.now().timestamp())}:F>
**🆔 ID da Avaliação:** #{cursor.lastrowid if 'cursor' in locals() else 'N/A'}""",
                        color=cor
                    )
                    await feedback_channel.send(embed=public_embed)
            except Exception as e:
                logger.error(f"Erro ao enviar feedback para canal: {e}")

            logger.info(f"Feedback do staff registrado: {self.staff_name} - média {media}/10 por {interaction.user}")

        except Exception as e:
            logger.error(f"Erro no feedback do staff: {e}")
            await interaction.response.send_message("❌ Erro ao processar feedback! Tente novamente.", ephemeral=True)

# Modal para resultado de teste tier
class TierResultModal(discord.ui.Modal, title="📋 Resultado do Teste Tier"):
    def __init__(self):
        super().__init__()

    resultado = discord.ui.TextInput(
        label="📝 Resultado do Teste",
        placeholder="Ex: Aprovado - Excelente performance...",
        required=True,
        max_length=500,
        style=discord.TextStyle.paragraph
    )

    observacoes = discord.ui.TextInput(
        label="📋 Observações (Opcional)",
        placeholder="Observações adicionais sobre o teste...",
        required=False,
        max_length=300,
        style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel = bot.get_channel(CHANNEL_ID_TESTE_TIER)
            if not channel:
                await interaction.response.send_message("❌ Canal de teste tier não encontrado!", ephemeral=True)
                return

            embed = create_embed(
                "📋 Resultado - Teste Tier",
                f"""**Resultado do teste tier:**

{self.resultado.value}

{f"**Observações:** {self.observacoes.value}" if self.observacoes.value else ""}

**Avaliado por:** {interaction.user.mention}
**Data:** <t:{int(datetime.datetime.now().timestamp())}:F>

*Este é um resultado oficial do teste tier.*""",
                color=0xffd700
            )

            await channel.send(embed=embed)
            await interaction.response.send_message("✅ Resultado enviado com sucesso!", ephemeral=True)

        except Exception as e:
            logger.error(f"Erro ao enviar resultado tier: {e}")
            await interaction.response.send_message("❌ Erro ao enviar resultado!", ephemeral=True)

# Modal para configuração da copinha
class CopinhaConfigModal(discord.ui.Modal, title="🏆 Criar Copinha Stumble Guys"):
    def __init__(self):
        super().__init__()

    titulo = discord.ui.TextInput(
        label="🎯 Nome da Copinha",
        placeholder="Ex: Copinha RX Elite, Torneio Noturno...",
        required=True,
        max_length=50
    )

    mapa = discord.ui.TextInput(
        label="🗺️ Mapa do Stumble Guys",
        placeholder="Ex: Block Dash, Super Slide, Hex-a-gone...",
        required=True,
        max_length=30
    )

    formato = discord.ui.TextInput(
        label="👥 Formato",
        placeholder="1v1, 2v2 ou 3v3",
        required=True,
        max_length=3
    )

    max_players = discord.ui.TextInput(
        label="🎮 Máximo de Jogadores",
        placeholder="4, 8, 16 ou 32",
        required=True,
        max_length=2
    )

    descricao = discord.ui.TextInput(
        label="📝 Descrição (Opcional)",
        placeholder="Regras especiais, prêmios, etc...",
        required=False,
        max_length=200,
        style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validar formato
            if self.formato.value.lower() not in ['1v1', '2v2', '3v3']:
                await safe_send_response(interaction, content="❌ Formato deve ser 1v1, 2v2 ou 3v3!", ephemeral=True)
                return

            # Validar número de jogadores baseado no formato
            try:
                max_players = int(self.max_players.value)
                format_type = self.formato.value.lower()
                
                if format_type == '1v1':
                    if max_players not in [2, 4, 8, 16, 32]:
                        await safe_send_response(interaction, content="❌ Para 1v1: 2, 4, 8, 16 ou 32 jogadores!", ephemeral=True)
                        return
                elif format_type == '2v2':
                    if max_players not in [4, 8, 16, 32]:
                        await safe_send_response(interaction, content="❌ Para 2v2: 4, 8, 16 ou 32 jogadores!", ephemeral=True)
                        return
                elif format_type == '3v3':
                    if max_players not in [6, 12, 18, 24, 30]:
                        await safe_send_response(interaction, content="❌ Para 3v3: 6, 12, 18, 24 ou 30 jogadores!", ephemeral=True)
                        return
                else:
                    await safe_send_response(interaction, content="❌ Formato inválido!", ephemeral=True)
                    return
            except ValueError:
                await safe_send_response(interaction, content="❌ Número de jogadores deve ser um número válido!", ephemeral=True)
                return

            # Criar copinha no banco de dados
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO copinhas (guild_id, creator_id, channel_id, title, map_name, team_format, max_players, current_round, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    interaction.guild.id,
                    interaction.user.id,
                    interaction.channel.id,
                    self.titulo.value,
                    self.mapa.value,
                    self.formato.value,
                    max_players,
                    'inscricoes',
                    'active'
                ))
                copinha_id = cursor.lastrowid
                conn.commit()
                conn.close()

            # Criar embed da copinha
            embed = create_embed(
                f"🏆 {self.titulo.value}",
                f"""**🗺️ Mapa:** {self.mapa.value}
**👥 Formato:** {self.formato.value}
**🎮 Jogadores:** 0/{max_players}
**📊 Status:** 🟢 Inscrições Abertas

{f"**📝 Descrição:** {self.descricao.value}" if self.descricao.value else ""}

**🎯 Como participar:**
Clique no botão "🎮 Participar" abaixo!

**📋 Organizador:** {interaction.user.mention}
**⏰ Criado:** <t:{int(datetime.datetime.now().timestamp())}:R>""",
                color=0xffd700
            )

            # Criar view com botão de participar
            view = CopinhaView(copinha_id, max_players)
            
            await interaction.response.send_message(embed=embed, view=view)

            # Atualizar message_id no banco
            message = await interaction.original_response()
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE copinhas SET message_id = %s WHERE id = %s', (message.id, copinha_id))
                conn.commit()
                conn.close()

            logger.info(f"Copinha criada: {self.titulo.value} por {interaction.user}")

        except Exception as e:
            logger.error(f"Erro ao criar copinha: {e}")
            # Robust error handling without depending on webhooks
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Erro ao criar copinha! Tente novamente.", ephemeral=True)
                else:
                    await interaction.followup.send("❌ Erro ao criar copinha! Tente novamente.", ephemeral=True)
            except (discord.errors.NotFound, discord.errors.HTTPException):
                # If interaction expired, try channel fallback
                try:
                    if hasattr(interaction, 'channel') and interaction.channel:
                        await interaction.channel.send("❌ Erro ao criar copinha! Tente novamente.")
                except Exception:
                    logger.error("Failed to send error message - interaction and channel both failed")

# View para fechar tickets
class CloseTicketView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)  # 5 minutos
        self.user_id = user_id

    @discord.ui.button(label="✅ Confirmar", style=discord.ButtonStyle.danger)
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Verificar se é o usuário correto
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ Apenas quem solicitou pode confirmar!", ephemeral=True)
                return

            # Marcar ticket como fechado no banco
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE tickets SET status = %s, closed_by = %s WHERE channel_id = %s', 
                             ('closed', interaction.user.id, interaction.channel.id))
                conn.commit()
                conn.close()

            # Embed de fechamento
            embed = create_embed(
                "🔒 Ticket Fechado",
                f"""**Ticket fechado por:** {interaction.user.mention}
**Data:** <t:{int(datetime.datetime.now().timestamp())}:F>

**📋 Este canal será deletado em 10 segundos...**

*Obrigado por usar nosso sistema de suporte!*""",
                color=0xff6b6b
            )

            await interaction.response.edit_message(embed=embed, view=None)

            # Aguardar e deletar canal
            await asyncio.sleep(10)
            await interaction.channel.delete(reason=f"Ticket fechado por {interaction.user}")

        except Exception as e:
            logger.error(f"Erro ao fechar ticket: {e}")
            await interaction.response.send_message("❌ Erro ao fechar ticket!", ephemeral=True)

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            embed = create_embed(
                "❌ Fechamento Cancelado", 
                "O fechamento do ticket foi cancelado. Continue seu atendimento normalmente.",
                color=0xffaa00
            )
            await interaction.response.edit_message(embed=embed, view=None)
        except Exception as e:
            logger.error(f"Erro ao cancelar fechamento: {e}")

# View para botões da copinha
class CopinhaView(discord.ui.View):
    def __init__(self, copinha_id, max_players):
        super().__init__(timeout=None)  # Sem timeout para copinhas
        self.copinha_id = copinha_id
        self.max_players = max_players

    @discord.ui.button(label="🎮 Participar", style=discord.ButtonStyle.green, custom_id="copinha_join")
    async def join_copinha(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Buscar dados da copinha
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM copinhas WHERE id = %s', (self.copinha_id,))
                copinha = cursor.fetchone()
                conn.close()

            if not copinha:
                await safe_send_response(interaction, content="❌ Copinha não encontrada!", ephemeral=True)
                return

            # Verificar se copinha ainda está ativa
            if copinha[12] != 'active':  # status
                await safe_send_response(interaction, content="❌ Esta copinha já foi finalizada!", ephemeral=True)
                return

            # Verificar participantes atuais
            participants = json.loads(copinha[9]) if copinha[9] else []  # participants

            if interaction.user.id in participants:
                await safe_send_response(interaction, content="❌ Você já está participando desta copinha!", ephemeral=True)
                return

            if len(participants) >= self.max_players:
                await safe_send_response(interaction, content="❌ Copinha lotada! Não há mais vagas.", ephemeral=True)
                return

            # Adicionar participante
            participants.append(interaction.user.id)

            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE copinhas SET participants = %s WHERE id = %s', 
                             (json.dumps(participants), self.copinha_id))
                conn.commit()
                conn.close()

            # Atualizar embed
            embed = create_embed(
                f"🏆 {copinha[5]}",  # title
                f"""**🗺️ Mapa:** {copinha[6]}
**👥 Formato:** {copinha[7]}
**🎮 Jogadores:** {len(participants)}/{self.max_players}
**📊 Status:** {'🟢 Inscrições Abertas' if len(participants) < self.max_players else '🔴 Copinha Cheia'}

**👥 Participantes:**
{', '.join([f"<@{p}>" for p in participants])}

**📋 Organizador:** <@{copinha[2]}>
**⏰ Criado:** <t:{int(datetime.datetime.now().timestamp())}:R>""",
                color=0xffd700 if len(participants) < self.max_players else 0xff6b6b
            )

            # Se copinha encheu, criar brackets
            if len(participants) >= self.max_players:
                await self.create_brackets(interaction, copinha, participants)
                # Desabilitar botão
                button.disabled = True
                button.label = "🔒 Copinha Cheia"
                
                # Usar safe_edit_message personalizada
                await self.safe_edit_message(interaction, embed, self)
            else:
                await self.safe_edit_message(interaction, embed, self)

        except Exception as e:
            logger.error(f"Erro ao participar da copinha: {e}")
            await safe_send_response(interaction, content="❌ Erro ao entrar na copinha!", ephemeral=True)

    async def safe_edit_message(self, interaction, embed, view):
        """Método para editar mensagem de forma segura"""
        try:
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                await interaction.edit_original_response(embed=embed, view=view)
        except (discord.errors.NotFound, discord.errors.InteractionResponded, discord.errors.HTTPException) as e:
            logger.info(f"Edit message falhou, ignorando: {e}")
            # Se não conseguir editar, não é crítico para a funcionalidade
            pass

    async def create_brackets(self, interaction, copinha, participants):
        """Criar brackets automáticos quando a copinha encher"""
        try:
            # Embaralhar participantes
            random.shuffle(participants)
            
            # Extrair formato e título
            team_format = copinha[7]  # team_format
            copinha_title = copinha[5]  # title
            copinha_map = copinha[6]  # map_name

            # Criar categoria para a copinha
            category_name = f"🏆 {copinha_title[:20]}"
            category = await interaction.guild.create_category(category_name)

            # Criar canal de informações
            info_channel = await interaction.guild.create_text_channel(
                f"📋-info-{copinha_title[:15]}",
                category=category
            )

            # Criar times baseado no formato
            teams = self.create_teams(participants, team_format)
            num_matches = len(teams) // 2

            # Criar matches da primeira rodada
            for i in range(num_matches):
                team1 = teams[i * 2]
                team2 = teams[i * 2 + 1]
                
                # Criar canal para a partida
                match_channel = await interaction.guild.create_text_channel(
                    f"🎮-partida-{i+1}",
                    category=category
                )

                # Dar permissão aos jogadores das duas equipes
                await match_channel.set_permissions(interaction.guild.default_role, read_messages=False)
                
                # Permissões para time 1
                for player_id in team1:
                    member = interaction.guild.get_member(player_id)
                    if member:
                        await match_channel.set_permissions(member, read_messages=True, send_messages=True)
                
                # Permissões para time 2
                for player_id in team2:
                    member = interaction.guild.get_member(player_id)
                    if member:
                        await match_channel.set_permissions(member, read_messages=True, send_messages=True)

                # Salvar match no banco com todos os jogadores
                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO copinha_matches (copinha_id, round_name, match_number, players, ticket_channel_id, status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (
                        self.copinha_id,
                        'Primeira Rodada',
                        i + 1,
                        json.dumps({'team1': team1, 'team2': team2}),
                        match_channel.id,
                        'waiting'
                    ))
                    conn.commit()
                    conn.close()

                # Criar embed da partida baseado no formato
                team1_text = self.format_team_display(team1, "🔴", team_format)
                team2_text = self.format_team_display(team2, "🔵", team_format)
                
                match_embed = create_embed(
                    f"🎮 Partida {i+1} - Primeira Rodada ({team_format})",
                    f"""**🏆 Copinha:** {copinha_title}
**🗺️ Mapa:** {copinha_map}
**👥 Formato:** {team_format}

**⚔️ Teams:**
{team1_text}

VS

{team2_text}

**📋 Instruções:**
1. Coordenem o horário da partida entre as equipes
2. Joguem no mapa **{copinha_map}** no formato **{team_format}**
3. A equipe vencedora deve avisar aqui
4. Aguardem um moderador confirmar o resultado

**🎯 Boa sorte para ambas as equipes!**""",
                    color=0x00ff00
                )

                await match_channel.send(embed=match_embed)

            # Atualizar status da copinha
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE copinhas SET current_round = %s, status = %s WHERE id = %s', 
                             ('primeira_rodada', 'em_andamento', self.copinha_id))
                conn.commit()
                conn.close()

            # Criar texto das partidas para o resumo
            matches_text = []
            for i in range(num_matches):
                team1 = teams[i * 2]
                team2 = teams[i * 2 + 1]
                team1_simple = " & ".join([f"<@{p}>" for p in team1])
                team2_simple = " & ".join([f"<@{p}>" for p in team2])
                matches_text.append(f"**Partida {i+1}:** ({team1_simple}) vs ({team2_simple})")

            # Enviar resumo no canal de info
            brackets_embed = create_embed(
                f"🏆 {copinha_title} - Brackets Criados!",
                f"""**🎉 A copinha está oficialmente iniciada!**

**📊 Informações:**
• **Participantes:** {len(participants)}
• **Formato:** {team_format}
• **Equipes:** {len(teams)}
• **Partidas da 1ª rodada:** {num_matches}
• **Categoria:** {category.mention}

**🎮 Partidas da Primeira Rodada:**
""" + "\n".join(matches_text) + f"""

**📋 Próximos passos:**
• As equipes devem ir aos seus canais específicos
• Coordenar horários e jogar as partidas no formato {team_format}
• Equipes vencedoras devem reportar no canal da partida
• Moderadores confirmarão os resultados

**🏆 Que comecem os jogos!**""",
                color=0xffd700
            )

            await info_channel.send(embed=brackets_embed)

        except Exception as e:
            logger.error(f"Erro ao criar brackets: {e}")
            
    def create_teams(self, participants, team_format):
        """Criar equipes baseado no formato"""
        teams = []
        
        if team_format.lower() == '1v1':
            # Para 1v1, cada participante é uma "equipe" de 1
            teams = [[p] for p in participants]
        elif team_format.lower() == '2v2':
            # Para 2v2, criar equipes de 2
            for i in range(0, len(participants), 2):
                if i + 1 < len(participants):
                    teams.append([participants[i], participants[i + 1]])
        elif team_format.lower() == '3v3':
            # Para 3v3, criar equipes de 3
            for i in range(0, len(participants), 3):
                if i + 2 < len(participants):
                    teams.append([participants[i], participants[i + 1], participants[i + 2]])
                    
        return teams
        
    def format_team_display(self, team, emoji, team_format):
        """Formatar exibição da equipe"""
        if team_format.lower() == '1v1':
            return f"{emoji} <@{team[0]}>"
        else:
            return f"{emoji} **Equipe:** " + " & ".join([f"<@{p}>" for p in team])

# Modal para resultado XClan
class XClanResultModal(discord.ui.Modal, title="🏆 Resultado XClan VS"):
    def __init__(self):
        super().__init__()

    resultado = discord.ui.TextInput(
        label="🏆 Resultado da Batalha",
        placeholder="Ex: ## 🏆 RX vs WLX\nRX 11 ✖ 0 WLX\nObs: WO",
        required=True,
        max_length=500,
        style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            result_channel = bot.get_channel(1400167040504823869)
            if not result_channel:
                await interaction.response.send_message("❌ Canal de resultados não encontrado!", ephemeral=True)
                return

            embed = create_embed(
                "🏆 RESULTADO XCLAN VS",
                f"""{self.resultado.value}

**📊 Resultado enviado por:** {interaction.user.mention}
**⏰ Data:** <t:{int(datetime.datetime.now().timestamp())}:F>""",
                color=0xffd700
            )

            await result_channel.send(embed=embed)
            await interaction.response.send_message("✅ Resultado enviado com sucesso!", ephemeral=True)

        except Exception as e:
            logger.error(f"Erro ao enviar resultado XClan: {e}")
            await interaction.response.send_message("❌ Erro ao enviar resultado!", ephemeral=True)

# Modal para criar sorteio de coins
class CoinGiveawayModal(discord.ui.Modal, title="💰 Criar Sorteio de Coins"):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    titulo = discord.ui.TextInput(
        label="🎯 Título do Sorteio",
        placeholder="Ex: Sorteio de 10.000 Coins!",
        required=True,
        max_length=50
    )

    quantidade_coins = discord.ui.TextInput(
        label="💰 Quantidade de Coins",
        placeholder="Ex: 10000, 50000, 100000...",
        required=True,
        max_length=10
    )

    duracao = discord.ui.TextInput(
        label="⏰ Duração",
        placeholder="Ex: 30m, 2h, 1d, 7d",
        required=True,
        max_length=10
    )

    vencedores = discord.ui.TextInput(
        label="🏆 Número de Vencedores",
        placeholder="Ex: 1, 2, 3...",
        required=True,
        max_length=2
    )

    requisitos = discord.ui.TextInput(
        label="📋 Requisitos (Opcional)",
        placeholder="Ex: Seguir o servidor, ser ativo...",
        required=False,
        max_length=200,
        style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validar quantidade de coins
            try:
                coin_amount = int(self.quantidade_coins.value)
                if coin_amount < 100 or coin_amount > 1000000:
                    raise ValueError
            except ValueError:
                await interaction.response.send_message("❌ Quantidade de coins deve ser entre 100 e 1.000.000!", ephemeral=True)
                return

            # Validar número de vencedores
            try:
                winners_count = int(self.vencedores.value)
                if winners_count < 1 or winners_count > 10:
                    raise ValueError
            except ValueError:
                await interaction.response.send_message("❌ Número de vencedores deve ser entre 1 e 10!", ephemeral=True)
                return

            # Parse duration
            time_units = {'m': 60, 'h': 3600, 'd': 86400}
            duration_str = self.duracao.value.lower()
            unit = duration_str[-1]

            if unit not in time_units:
                await interaction.response.send_message("❌ Duração inválida! Use: m (minutos), h (horas), d (dias)", ephemeral=True)
                return

            try:
                amount = int(duration_str[:-1])
                seconds = amount * time_units[unit]
                end_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
            except ValueError:
                await interaction.response.send_message("❌ Duração inválida! Use números válidos: 30m, 2h, 1d", ephemeral=True)
                return

            # Criar embed do sorteio
            embed = create_embed(
                f"💰 {self.titulo.value}",
                f"""**💰 Prêmio:** {coin_amount:,} coins (distribuídos entre vencedores)
**🏆 Vencedores:** {winners_count}
**⏰ Termina:** <t:{int(end_time.timestamp())}:R>
**👑 Criado por:** <@{self.user_id}>
**📋 Requisitos:** {self.requisitos.value or "Nenhum requisito especial"}

**🎉 Reaja com 🎉 para participar!**

**💫 Os coins serão automaticamente adicionados ao saldo dos vencedores!**""",
                color=0xffd700
            )

            giveaway_msg = await interaction.response.send_message(embed=embed)
            message = await interaction.original_response()
            await message.add_reaction("🎉")

            # Salvar no banco
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO giveaways (guild_id, channel_id, creator_id, title, prize, winners_count, end_time, message_id, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (interaction.guild.id, interaction.channel.id, self.user_id, self.titulo.value, f"{coin_amount:,} coins", winners_count, end_time, message.id, 'active'))

                # Salvar quantidade de coins no campo prize para distribuição automática
                giveaway_id = cursor.lastrowid
                cursor.execute('UPDATE giveaways SET bet_amount = %s WHERE id = %s', (coin_amount, giveaway_id))

                conn.commit()
                conn.close()

            success_embed = create_embed(
                "✅ Sorteio de Coins Criado!",
                f"**{self.titulo.value}** foi criado com sucesso!\n\n"
                f"📋 **Resumo:**\n"
                f"• Prêmio: {coin_amount:,} coins\n"
                f"• Vencedores: {winners_count}\n"
                f"• Duração: {self.duracao.value}\n"
                f"• Os coins serão automaticamente distribuídos!\n\n"
                f"🎯 **Criado por:** <@{self.user_id}>",
                color=0x00ff00
            )

            await interaction.followup.send(embed=success_embed, ephemeral=True)
            logger.info(f"Sorteio de coins criado: {self.titulo.value} - {coin_amount:,} coins por {interaction.user}")

        except Exception as e:
            logger.error(f"Erro ao criar sorteio de coins: {e}")
            await interaction.response.send_message("❌ Erro ao criar sorteio! Tente novamente.", ephemeral=True)

# Modal para configurar copinha Stumble Guys
class CopinhaConfigModal(discord.ui.Modal, title="🏆 Configurar Copinha Stumble Guys"):
    def __init__(self):
        super().__init__()

    titulo = discord.ui.TextInput(
        label="🎯 Nome da Copinha",
        placeholder="Ex: Copa RX de Stumble Guys",
        required=True,
        max_length=50
    )

    mapa = discord.ui.TextInput(
        label="🗺️ Mapa",
        placeholder="Ex: Block Dash, Super Slide, Dizzy Heights...",
        required=True,
        max_length=30
    )

    formato = discord.ui.TextInput(
        label="👥 Formato",
        placeholder="Ex: 1v1, 2v2, 3v3",
        required=True,
        max_length=10
    )

    max_players = discord.ui.TextInput(
        label="👑 Máximo de Jogadores",
        placeholder="Ex: 4, 8, 16, 32",
        required=True,
        max_length=2
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validar formato
            formato_lower = self.formato.value.lower()
            if not any(f in formato_lower for f in ['1v1', '2v2', '3v3', '1x1', '2x2', '3x3']):
                await interaction.response.send_message("❌ Formato deve ser 1v1, 2v2 ou 3v3!", ephemeral=True)
                return

            # Validar máximo de jogadores
            try:
                max_players = int(self.max_players.value)
                if max_players < 4 or max_players > 32 or (max_players & (max_players - 1)) != 0:
                    raise ValueError
            except ValueError:
                await interaction.response.send_message("❌ Máximo de jogadores deve ser 4, 8, 16 ou 32!", ephemeral=True)
                return

            # Mapas disponíveis do Stumble Guys com emojis
            mapas_emojis = {
                'block dash': '🧱',
                'super slide': '🛝',
                'dizzy heights': '🌪️',
                'gate crash': '🚪',
                'hit parade': '🎯',
                'the whirlygig': '🌀',
                'see saw': '⚖️',
                'tip toe': '👣',
                'perfect match': '🎮',
                'fall mountain': '🏔️'
            }

            mapa_emoji = '🗺️'
            for mapa_nome, emoji in mapas_emojis.items():
                if mapa_nome in self.mapa.value.lower():
                    mapa_emoji = emoji
                    break

            # Criar embed da copinha
            embed = create_embed(
                f"🏆 {self.titulo.value}",
                f"""**🗺️ Mapa:** {mapa_emoji} {self.mapa.value}
**👥 Formato:** {self.formato.value}
**👑 Máximo de Jogadores:** {max_players}
**📊 Status:** Inscrições Abertas
**👑 Organizador:** {interaction.user.mention}

**📝 Regras:**
• Apenas jogadores do servidor podem participar
• Sem apostas - apenas diversão e glória!
• Um moderador definirá os vencedores de cada partida
• As partidas serão organizadas em tickets privados

**🎮 Clique em "Participar" para se inscrever!**
**Inscritos: 0/{max_players}**""",
                color=0x00ff00
            )

            # Buscar o ID da copinha para criar a view
            message = await interaction.followup.send(embed=embed, wait=True)
            
            # Criar view com botão de participar
            view = CopinhaParticipationView(message.id, max_players, self.titulo.value, self.mapa.value, self.formato.value)
            await message.edit(embed=embed, view=view)

            # Buscar a mensagem criada
            message = await interaction.original_response()

            # Salvar no banco de dados usando execute_query
            execute_query('''
                INSERT INTO copinhas (guild_id, creator_id, channel_id, message_id, title, map_name, team_format, max_players)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (interaction.guild.id, interaction.user.id, interaction.channel.id, message.id, self.titulo.value, self.mapa.value, self.formato.value, max_players))

            logger.info(f"Copinha criada: {self.titulo.value} por {interaction.user}")

        except Exception as e:
            logger.error(f"Erro ao criar copinha: {e}")
            # Robust error handling without depending on webhooks
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Erro ao criar copinha! Tente novamente.", ephemeral=True)
                else:
                    await interaction.followup.send("❌ Erro ao criar copinha! Tente novamente.", ephemeral=True)
            except (discord.errors.NotFound, discord.errors.HTTPException):
                # If interaction expired, try channel fallback
                try:
                    if hasattr(interaction, 'channel') and interaction.channel:
                        await interaction.channel.send("❌ Erro ao criar copinha! Tente novamente.")
                except Exception:
                    logger.error("Failed to send error message - interaction and channel both failed")

# View para participar da copinha
class CopinhaParticipationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.copinha_id = None

    @discord.ui.button(label="🎮 Participar", style=discord.ButtonStyle.success, emoji="🎮")
    async def participate(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Buscar dados da copinha usando execute_query
            copinha = execute_query('SELECT * FROM copinhas WHERE message_id = %s AND status = %s', (interaction.message.id, "active"), fetch_one=True)

            if not copinha:
                logger.error("Dados da copinha: Não encontrada")
                await safe_send_response(interaction, content="❌ Copinha não encontrada ou já finalizada!", ephemeral=True)
                return

            # Verificar participantes atuais - compatível com PostgreSQL e SQLite
            if isinstance(copinha, dict):
                participants_data = copinha.get('participants', '[]')
                max_players = copinha.get('max_players', 4)
                copinha_id = copinha.get('id')
            else:
                participants_data = copinha[9] if len(copinha) > 9 else '[]'
                max_players = copinha[8] if len(copinha) > 8 else 4
                copinha_id = copinha[0] if len(copinha) > 0 else None

            try:
                participants = json.loads(participants_data) if participants_data else []
            except (json.JSONDecodeError, TypeError):
                participants = []

            # Verificar se já está inscrito
            if interaction.user.id in participants:
                await safe_send_response(interaction, content="❌ Você já está inscrito nesta copinha!", ephemeral=True)
                return

            # Verificar se há vagas
            if len(participants) >= max_players:
                await safe_send_response(interaction, content="❌ Copinha lotada! Não há mais vagas.", ephemeral=True)
                return

            # Adicionar participante
            participants.append(interaction.user.id)
            execute_query('UPDATE copinhas SET participants = %s WHERE id = %s', 
                         (json.dumps(participants), copinha_id))

            # Atualizar embed - compatível com PostgreSQL e SQLite
            if isinstance(copinha, dict):
                title = copinha.get('title', 'Copinha')
                map_name = copinha.get('map_name', 'Desconhecido')
                team_format = copinha.get('team_format', '1v1')
                creator_id = copinha.get('creator_id')
            else:
                title = copinha[5] if len(copinha) > 5 else 'Copinha'
                map_name = copinha[6] if len(copinha) > 6 else 'Desconhecido'
                team_format = copinha[7] if len(copinha) > 7 else '1v1'
                creator_id = copinha[2] if len(copinha) > 2 else None

            mapa_emoji = '🗺️'
            mapas_emojis = {
                'block dash': '🧱', 'super slide': '🛝', 'dizzy heights': '🌪️',
                'gate crash': '🚪', 'hit parade': '🎯', 'the whirlygig': '🌀',
                'see saw': '⚖️', 'tip toe': '👣', 'perfect match': '🎮', 'fall mountain': '🏔️'
            }

            for mapa_nome, emoji in mapas_emojis.items():
                if mapa_nome in map_name.lower():
                    mapa_emoji = emoji
                    break

            embed = create_embed(
                f"🏆 {title}",
                f"""**🗺️ Mapa:** {mapa_emoji} {map_name}
**👥 Formato:** {team_format}  
**👑 Máximo de Jogadores:** {max_players}
**📊 Status:** {'Lotado - Iniciando Brackets!' if len(participants) == max_players else 'Inscrições Abertas'}
**👑 Organizador:** <@{creator_id}>

**📝 Regras:**
• Apenas jogadores do servidor podem participar
• Sem apostas - apenas diversão e glória!
• Um moderador definirá os vencedores de cada partida
• As partidas serão organizadas em tickets privados

**🎮 Clique em "Participar" para se inscrever!**
**Inscritos: {len(participants)}/{max_players}**""",
                color=0xffd700 if len(participants) == max_players else 0x00ff00
            )

            if len(participants) == max_players:
                # Desabilitar botão se lotou
                button.disabled = True
                await interaction.response.edit_message(embed=embed, view=self)

                # Iniciar criação dos brackets/tickets
                await self.create_tournament_brackets(interaction, copinha, participants)
            else:
                await interaction.response.edit_message(embed=embed, view=self)
                await interaction.followup.send(f"✅ {interaction.user.mention} se inscreveu na copinha!", ephemeral=True)

        except Exception as e:
            logger.error(f"Erro ao participar da copinha: {e}")
            logger.error(f"Dados da copinha: {copinha if 'copinha' in locals() else 'Não encontrada'}")
            await interaction.response.send_message("❌ Erro ao se inscrever! Tente novamente.", ephemeral=True)

    async def create_tournament_brackets(self, interaction, copinha, participants):
        try:
            # Embaralhar participantes para brackets aleatórios
            import random
            random.shuffle(participants)

            # Calcular rounds necessários
            import math
            total_rounds = int(math.log2(len(participants)))

            # Criar primeira fase
            matches = []
            for i in range(0, len(participants), 2):
                match = {
                    'round': 'Primeira Fase',
                    'players': [participants[i], participants[i+1]] if i+1 < len(participants) else [participants[i]],
                    'match_number': (i // 2) + 1
                }
                matches.append(match)

            # Salvar matches no banco - compatível com PostgreSQL e SQLite
            copinha_id = copinha.get('id') if isinstance(copinha, dict) else copinha[0]

            for match in matches:
                execute_query('''
                    INSERT INTO copinha_matches (copinha_id, round_name, match_number, players)
                    VALUES (%s, %s, %s, %s)
                ''', (copinha_id, match['round'], match['match_number'], json.dumps(match['players'])))

            # Atualizar status da copinha
            execute_query('UPDATE copinhas SET current_round = ?, status = ? WHERE id = ?', 
                         ('Primeira Fase', 'running', copinha_id))

            # Criar tickets para cada partida
            await self.create_match_tickets(interaction, copinha, matches)

        except Exception as e:
            logger.error(f"Erro ao criar brackets: {e}")

    async def create_match_tickets(self, interaction, copinha, matches):
        try:
            guild = interaction.guild

            # Buscar categoria de tickets ou criar
            ticket_category = None
            for category in guild.categories:
                if 'ticket' in category.name.lower() or 'copinha' in category.name.lower():
                    ticket_category = category
                    break

            if not ticket_category:
                title = copinha.get('title', 'Copinha')[:20] if isinstance(copinha, dict) else copinha[5][:20]
                ticket_category = await guild.create_category(f"🏆 Copinha {title}")

            for i, match in enumerate(matches):
                # Criar canal privado para a partida
                player_names = []
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }

                # Dar permissão aos jogadores
                for player_id in match['players']:
                    member = guild.get_member(player_id)
                    if member:
                        overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                        player_names.append(member.display_name)

                # Dar permissão a moderadores
                for role in guild.roles:
                    if any(perm_name in role.name.lower() for perm_name in ['mod', 'admin', 'staff']):
                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

                channel_name = f"partida-{match['match_number']}-{'-vs-'.join(player_names[:2])}"[:100]
                match_channel = await guild.create_text_channel(
                    channel_name,
                    category=ticket_category,
                    overwrites=overwrites
                )

                # Salvar canal no banco
                copinha_id = copinha.get('id') if isinstance(copinha, dict) else copinha[0]
                execute_query('UPDATE copinha_matches SET ticket_channel_id = %s WHERE copinha_id = %s AND match_number = %s AND round_name = %s',
                             (match_channel.id, copinha_id, match['match_number'], 'Primeira Fase'))

                # Criar embed da partida
                players_text = " vs ".join([f"<@{pid}>" for pid in match['players']])

                mapa_emoji = '🗺️'
                mapas_emojis = {
                    'block dash': '🧱', 'super slide': '🛝', 'dizzy heights': '🌪️',
                    'gate crash': '🚪', 'hit parade': '🎯', 'the whirlygig': '🌀',
                    'see saw': '⚖️', 'tip toe': '👣', 'perfect match': '🎮', 'fall mountain': '🏔️'
                }

                map_name = copinha.get('map_name', 'Desconhecido') if isinstance(copinha, dict) else copinha[6]
                for mapa_nome, emoji in mapas_emojis.items():
                    if mapa_nome in map_name.lower():
                        mapa_emoji = emoji
                        break

                title = copinha.get('title', 'Copinha') if isinstance(copinha, dict) else copinha[5]
                team_format = copinha.get('team_format', '1v1') if isinstance(copinha, dict) else copinha[7]

                embed = create_embed(
                    f"🏆 {title} - {match['round']}",
                    f"""**🥊 Partida #{match['match_number']}**

**👥 Jogadores:**
{players_text}

**🗺️ Mapa:** {mapa_emoji} {map_name}
**👥 Formato:** {team_format}

**📋 Instruções:**
1. Os jogadores devem combinar horário
2. Joguem a partida no Stumble Guys
3. Um moderador definirá o vencedor
4. O vencedor avança para a próxima fase

**⚠️ Aguardando resultado do moderador...**""",
                    color=0xff9900
                )

                copinha_id = copinha.get('id') if isinstance(copinha, dict) else copinha[0]
                view = MatchResultView(copinha_id, match['match_number'], 'Primeira Fase')
                await match_channel.send(embed=embed, view=view)

            # Notificar no canal original
            await interaction.followup.send(
                f"🏆 **Copinha iniciada!** Foram criados {len(matches)} tickets de partida na categoria {ticket_category.mention}. "
                f"Cada jogador pode ver apenas sua partida. Moderadores, definam os vencedores nos tickets!", 
                ephemeral=False
            )

        except Exception as e:
            logger.error(f"Erro ao criar tickets: {e}")

# View para definir resultado da partida
class MatchResultView(discord.ui.View):
    def __init__(self, copinha_id, match_number, round_name):
        super().__init__(timeout=None)
        self.copinha_id = copinha_id
        self.match_number = match_number
        self.round_name = round_name

    @discord.ui.button(label="👑 Definir Vencedor", style=discord.ButtonStyle.primary, emoji="🏆")
    async def define_winner(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verificar se é moderador
        if not any(role.permissions.manage_messages for role in interaction.user.roles):
            await interaction.response.send_message("❌ Apenas moderadores podem definir vencedores!", ephemeral=True)
            return

        try:
            # Buscar dados da partida usando execute_query para evitar deadlock
            result = execute_query('SELECT players FROM copinha_matches WHERE copinha_id = ? AND match_number = ? AND round_name = ?',
                                 (self.copinha_id, self.match_number, self.round_name), fetch_one=True)

            if not result:
                await interaction.response.send_message("❌ Partida não encontrada!", ephemeral=True)
                return

            players = json.loads(result[0])

            # Criar select com os jogadores
            select = discord.ui.Select(
                placeholder="Escolha o vencedor da partida...",
                options=[discord.SelectOption(
                    label=f"{interaction.guild.get_member(player_id).display_name}" if interaction.guild.get_member(player_id) else f"Player {player_id}",
                    value=str(player_id),
                    emoji="👑"
                ) for player_id in players]
            )

            async def select_winner_callback(select_interaction):
                winner_id = int(select.values[0])
                await self.set_match_winner(select_interaction, winner_id)

            select.callback = select_winner_callback
            view = discord.ui.View()
            view.add_item(select)

            await interaction.response.send_message("🏆 Selecione o vencedor da partida:", view=view, ephemeral=True)

        except Exception as e:
            logger.error(f"Erro ao definir vencedor: {e}")
            await interaction.response.send_message("❌ Erro ao definir vencedor!", ephemeral=True)

    async def set_match_winner(self, interaction, winner_id):
        try:
            # Atualizar banco com vencedor usando execute_query
            execute_query('UPDATE copinha_matches SET winner_id = %s, status = %s WHERE copinha_id = %s AND match_number = %s AND round_name = %s',
                         (winner_id, 'completed', self.copinha_id, self.match_number, self.round_name))
            
            # Buscar dados da copinha
            copinha = execute_query('SELECT * FROM copinhas WHERE id = %s', (self.copinha_id,), fetch_one=True)
            
            if copinha:
                winner = interaction.guild.get_member(winner_id)
                winner_name = winner.display_name if winner else f"Player {winner_id}"
                
                embed = create_embed(
                    "🏆 Vencedor Definido!",
                    f"**👑 Vencedor da partida:** {winner_name}\n\n✅ **O vencedor avançou para a próxima fase!**",
                    color=0x00ff00
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
                # Verificar se a rodada terminou
                await self.check_round_completion(interaction, copinha)
            
        except Exception as e:
            logger.error(f"Erro ao definir vencedor: {e}")
            await interaction.response.send_message("❌ Erro ao definir vencedor!", ephemeral=True)

    async def check_round_completion(self, interaction, copinha):
        """Verifica se a rodada terminou e cria próxima fase"""
        try:
            # Usar uma única query para evitar deadlock
            query_result = execute_query('''
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed
                FROM copinha_matches 
                WHERE copinha_id = ? AND round_name = ?
            ''', (self.copinha_id, self.round_name), fetch_one=True)
            
            if not query_result:
                return
                
            if isinstance(query_result, dict):
                total = query_result['total']
                completed = query_result['completed']
            else:
                total = query_result[0]
                completed = query_result[1]
            
            logger.info(f"Copinha {self.copinha_id} - {self.round_name}: {completed}/{total} partidas completas")
            
            if completed == total and total > 0:
                # Todas as partidas terminaram, buscar vencedores
                winners_result = execute_query('''
                    SELECT winner_id FROM copinha_matches 
                    WHERE copinha_id = %s AND round_name = %s AND status = 'completed' AND winner_id IS NOT NULL
                ''', (self.copinha_id, self.round_name), fetch_all=True)
                
                if winners_result:
                    winners = [row[0] if isinstance(row, (list, tuple)) else row for row in winners_result]
                    winners = [w for w in winners if w]  # Filtrar nulls
                    
                    logger.info(f"Copinha {self.copinha_id} - Vencedores da {self.round_name}: {winners}")
                    
                    if len(winners) == 1:
                        # Final! Anunciar vencedor
                        await self.announce_tournament_winner(interaction, copinha, winners[0])
                    elif len(winners) > 1:
                        # Criar próxima fase
                        await self.create_next_round(interaction, copinha, winners)
                else:
                    logger.error(f"Copinha {self.copinha_id} - Nenhum vencedor encontrado para {self.round_name}")

        except Exception as e:
            logger.error(f"Erro ao verificar completude da fase {self.round_name}: {e}")
            # Tentar recuperar enviando mensagem de erro
            try:
                await interaction.followup.send(f"⚠️ Erro na verificação da fase. Entre em contato com os administradores.", ephemeral=True)
            except:
                pass

    async def create_next_round(self, interaction, copinha, winners):
        """Cria a próxima rodada do torneio"""
        try:
            # Determinar nome da próxima fase
            round_names = {
                'Primeira Fase': 'Semifinal' if len(winners) <= 4 else 'Quartas de Final',
                'Quartas de Final': 'Semifinal',
                'Semifinal': 'Final'
            }

            next_round = round_names.get(self.round_name, 'Próxima Fase')
            logger.info(f"Copinha {self.copinha_id} - Criando {next_round} com {len(winners)} vencedores")

            # Criar partidas da próxima fase
            matches = []
            for i in range(0, len(winners), 2):
                if i+1 < len(winners):
                    match = {
                        'round': next_round,
                        'players': [winners[i], winners[i+1]],
                        'match_number': (i // 2) + 1
                    }
                    matches.append(match)

            if not matches:
                logger.error(f"Copinha {self.copinha_id} - Nenhuma partida criada para {next_round}")
                return

            # Usar transação única para evitar deadlock
            try:
                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    # Salvar todas as partidas em uma transação
                    for match in matches:
                        cursor.execute('''
                            INSERT INTO copinha_matches (copinha_id, round_name, match_number, players, status)
                            VALUES (%s, %s, %s, %s, %s)
                        ''', (self.copinha_id, match['round'], match['match_number'], json.dumps(match['players']), 'waiting'))

                    # Atualizar status da copinha
                    cursor.execute('UPDATE copinhas SET current_round = %s WHERE id = %s', 
                                  (next_round, self.copinha_id))
                    
                    conn.commit()
                    conn.close()
                    
                logger.info(f"Copinha {self.copinha_id} - {len(matches)} partidas salvas para {next_round}")
                
            except Exception as db_error:
                logger.error(f"Erro no banco ao criar {next_round}: {db_error}")
                return

            # Criar tickets para próxima fase
            await self.create_match_tickets_for_round(interaction, copinha, matches, next_round)

            # Notificar no canal original
            copinha_data = copinha if isinstance(copinha, dict) else {
                'channel_id': copinha[3],
                'title': copinha[5] if len(copinha) > 5 else 'Copinha'
            }
            
            original_channel = interaction.guild.get_channel(copinha_data.get('channel_id', copinha[3]))
            if original_channel:
                try:
                    await original_channel.send(
                        f"🎉 **{self.round_name} finalizada!** A **{next_round}** foi criada com {len(matches)} partida(s). "
                        f"Boa sorte aos classificados! 🏆"
                    )
                except Exception as channel_error:
                    logger.error(f"Erro ao notificar canal original: {channel_error}")

        except Exception as e:
            logger.error(f"Erro ao criar próxima fase {next_round}: {e}")
            try:
                await interaction.followup.send(f"⚠️ Erro ao criar {next_round}. Contate os administradores.", ephemeral=True)
            except:
                pass

    async def create_match_tickets_for_round(self, interaction, copinha, matches, round_name):
        """Cria tickets para as partidas da rodada"""
        try:
            guild = interaction.guild
            ticket_category = interaction.channel.category

            for match in matches:
                # Criar canal para a nova partida
                player_names = []
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }

                for player_id in match['players']:
                    member = guild.get_member(player_id)
                    if member:
                        overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                        player_names.append(member.display_name)

                # Dar permissão a moderadores
                for role in guild.roles:
                    if role.permissions.manage_messages:
                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

                channel_name = f"🥊-{round_name.lower().replace(' ', '-')}-{match['match_number']}"
                match_channel = await guild.create_text_channel(
                    name=channel_name,
                    category=ticket_category,
                    overwrites=overwrites
                )

                # Salvar channel_id no banco
                execute_query('UPDATE copinha_matches SET ticket_channel_id = %s WHERE copinha_id = %s AND round_name = %s AND match_number = %s',
                             (match_channel.id, self.copinha_id, round_name, match['match_number']))

                # Criar embed da partida
                copinha_data = copinha if isinstance(copinha, dict) else {
                    'title': copinha[5] if len(copinha) > 5 else 'Copinha',
                    'map_name': copinha[6] if len(copinha) > 6 else 'Desconhecido',
                    'team_format': copinha[7] if len(copinha) > 7 else '1v1'
                }
                
                players_text = "\n".join([f"• {name}" for name in player_names])
                
                embed = create_embed(
                    f"🏆 {copinha_data['title']} - {round_name}",
                    f"""**🥊 {round_name} - Partida #{match['match_number']}**

**👥 Jogadores:**
{players_text}

**🗺️ Mapa:** {copinha_data['map_name']}
**👥 Formato:** {copinha_data['team_format']}

**📋 Instruções:**
1. Os jogadores devem combinar horário
2. Joguem a partida no Stumble Guys
3. Um moderador definirá o vencedor
4. O vencedor avança para {'A FINAL!' if round_name == 'Final' else 'a próxima fase'}

**⚠️ Aguardando resultado do moderador...**""",
                    color=0xff9900 if round_name != 'Final' else 0xffd700
                )

                view = MatchResultView(self.copinha_id, match['match_number'], round_name)
                await match_channel.send(embed=embed, view=view)

        except Exception as e:
            logger.error(f"Erro ao criar tickets da rodada: {e}")

    async def announce_tournament_winner(self, interaction, copinha, winner_id):
        """Anuncia o vencedor do torneio"""
        try:
            winner = interaction.guild.get_member(winner_id)

            # Atualizar status da copinha
            execute_query('UPDATE copinhas SET status = %s WHERE id = %s', ('finished', self.copinha_id))

            # Criar embed de vitória
            copinha_data = copinha if isinstance(copinha, dict) else {
                'title': copinha[5] if len(copinha) > 5 else 'Copinha',
                'map_name': copinha[6] if len(copinha) > 6 else 'Desconhecido',
                'team_format': copinha[7] if len(copinha) > 7 else '1v1',
                'channel_id': copinha[3] if len(copinha) > 3 else None,
                'creator_id': copinha[2] if len(copinha) > 2 else None
            }
            
            embed = create_embed(
                f"🏆 {copinha_data['title']} - CAMPEÃO!",
                f"""**🎉 A COPINHA TERMINOU! 🎉**

**👑 CAMPEÃO: {winner.mention}**

**📊 Detalhes do Torneio:**
**🗺️ Mapa:** {copinha_data['map_name']}
**👥 Formato:** {copinha_data['team_format']}
**👑 Organizador:** <@{copinha_data['creator_id']}>

**🎊 PARABÉNS AO CAMPEÃO! 🎊**

*{winner.display_name} é o grande vencedor da copinha! 🏆*

**📅 Finalizado:** <t:{int(datetime.datetime.now().timestamp())}:F>""",
                color=0xffd700
            )

            # Tentar adicionar avatar do vencedor
            if winner and winner.avatar:
                embed.set_thumbnail(url=winner.avatar.url)

            # Anunciar no canal original
            if copinha_data['channel_id']:
                original_channel = interaction.guild.get_channel(copinha_data['channel_id'])
                if original_channel:
                    await original_channel.send(embed=embed)

            logger.info(f"Copinha {copinha_data['title']} finalizada com vencedor: {winner}")

        except Exception as e:
            logger.error(f"Erro ao anunciar vencedor: {e}")


            # Atualizar o embed da partida
            original_channel = interaction.guild.get_channel(interaction.channel.id)
            if original_channel:
                async for message in original_channel.history(limit=50):
                    if interaction.guild and interaction.guild.me and message.author == interaction.guild.me and message.embeds:
                        await message.edit(embed=embed, view=self)
                        break

            # Verificar se todas as partidas da fase terminaram
            await self.check_round_completion(interaction, copinha)

        except Exception as e:
            logger.error(f"Erro ao definir vencedor: {e}")
            await interaction.response.send_message("❌ Erro ao salvar vencedor!", ephemeral=True)

    async def check_round_completion(self, interaction, copinha):
        try:
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()

                # Verificar quantas partidas desta fase estão completas
                cursor.execute('SELECT COUNT(*) FROM copinha_matches WHERE copinha_id = %s AND round_name = %s AND status = %s',
                              (self.copinha_id, self.round_name))
                completed = cursor.fetchone()[0]

                cursor.execute('SELECT COUNT(*) FROM copinha_matches WHERE copinha_id = %s AND round_name = %s',
                              (self.copinha_id, self.round_name))
                total = cursor.fetchone()[0]

                if completed == total:
                    # Todas as partidas terminaram, criar próxima fase
                    cursor.execute('SELECT winner_id FROM copinha_matches WHERE copinha_id = %s AND round_name = %s AND status = %s',
                                  (self.copinha_id, self.round_name))
                    winners = [row[0] for row in cursor.fetchall()]

                    conn.close()

                    if len(winners) == 1:
                        # Final! Anunciar vencedor
                        await self.announce_tournament_winner(interaction, copinha, winners[0])
                    elif len(winners) > 1:
                        # Criar próxima fase
                        await self.create_next_round(interaction, copinha, winners)
                else:
                    conn.close()

        except Exception as e:
            logger.error(f"Erro ao verificar completude da fase: {e}")

    async def create_next_round(self, interaction, copinha, winners):
        try:
            # Determinar nome da próxima fase
            round_names = {
                'Primeira Fase': 'Semifinal' if len(winners) <= 4 else 'Quartas de Final',
                'Quartas de Final': 'Semifinal',
                'Semifinal': 'Final'
            }

            next_round = round_names.get(self.round_name, 'Próxima Fase')

            # Criar partidas da próxima fase
            matches = []
            for i in range(0, len(winners), 2):
                if i+1 < len(winners):
                    match = {
                        'round': next_round,
                        'players': [winners[i], winners[i+1]],
                        'match_number': (i // 2) + 1
                    }
                    matches.append(match)

            # Salvar no banco usando threading.current_thread para verificar se é thread principal
            def save_matches():
                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()

                    for match in matches:
                        cursor.execute('''
                            INSERT INTO copinha_matches (copinha_id, round_name, match_number, players)
                            VALUES (%s, %s, %s, %s)
                        ''', (self.copinha_id, match['round'], match['match_number'], json.dumps(match['players'])))

                    cursor.execute('UPDATE copinhas SET current_round = %s WHERE id = %s', 
                                  (next_round, self.copinha_id))
                    conn.commit()
                    conn.close()

            # Executar em thread separada para evitar deadlock
            await asyncio.get_event_loop().run_in_executor(None, save_matches)

            # Criar tickets para próxima fase
            guild = interaction.guild
            ticket_category = interaction.channel.category

            for match in matches:
                # Criar canal para a nova partida
                player_names = []
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }

                for player_id in match['players']:
                    member = guild.get_member(player_id)
                    if member:
                        overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                        player_names.append(member.display_name)

                # Dar permissão a moderadores
                for role in guild.roles:
                    if any(perm_name in role.name.lower() for perm_name in ['mod', 'admin', 'staff']):
                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

                channel_name = f"{next_round.lower().replace(' ', '-')}-{match['match_number']}-{'-vs-'.join(player_names[:2])}"[:100]
                match_channel = await guild.create_text_channel(
                    channel_name,
                    category=ticket_category,
                    overwrites=overwrites
                )

                # Salvar canal no banco
                def save_channel_id():
                    with db_lock:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute('UPDATE copinha_matches SET ticket_channel_id = %s WHERE copinha_id = %s AND match_number = %s AND round_name = %s',
                                      (match_channel.id, self.copinha_id, match['match_number'], next_round))
                        conn.commit()
                        conn.close()

                # Executar em thread separada para evitar deadlock
                await asyncio.get_event_loop().run_in_executor(None, save_channel_id)

                # Embed da nova partida
                players_text = " vs ".join([f"<@{pid}>" for pid in match['players']])

                embed = create_embed(
                    f"🏆 {copinha[5]} - {next_round}",
                    f"""**🥊 {next_round} - Partida #{match['match_number']}**

**👥 Jogadores:**
{players_text}

**🗺️ Mapa:** {copinha[6]}
**👥 Formato:** {copinha[7]}

**📋 Instruções:**
1. Os jogadores devem combinar horário
2. Joguem a partida no Stumble Guys
3. Um moderador definirá o vencedor
4. O vencedor avança para {'A FINAL!' if next_round == 'Final' else 'a próxima fase'}

**⚠️ Aguardando resultado do moderador...**""",
                    color=0xff9900 if next_round != 'Final' else 0xffd700
                )

                view = MatchResultView(self.copinha_id, match['match_number'], next_round)
                await match_channel.send(embed=embed, view=view)

            # Notificar no canal original
            original_channel = interaction.guild.get_channel(copinha[3])  # channel_id
            if original_channel:
                await original_channel.send(
                    f"🎉 **{self.round_name} finalizada!** A **{next_round}** foi criada com {len(matches)} partida(s). "
                    f"Boa sorte aos classificados! 🏆"
                )

        except Exception as e:
            logger.error(f"Erro ao criar próxima fase: {e}")

    async def announce_tournament_winner(self, interaction, copinha, winner_id):
        try:
            winner = interaction.guild.get_member(winner_id)

            # Atualizar status da copinha
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE copinhas SET status = %s WHERE id = %s', ('finished', self.copinha_id))
                conn.commit()
                conn.close()

            # Criar embed de vitória
            embed = create_embed(
                f"🏆 {copinha[5]} - CAMPEÃO!",
                f"""**🎉 A COPINHA TERMINOU! 🎉**

**👑 CAMPEÃO: {winner.mention}**

**📊 Detalhes do Torneio:**
**🗺️ Mapa:** {copinha[6]}
**👥 Formato:** {copinha[7]}
**👥 Participantes:** {copinha[9]}
**👑 Organizador:** <@{copinha[2]}>

**🎊 PARABÉNS AO CAMPEÃO! 🎊**

*{winner.display_name} é o grande vencedor da copinha! 🏆*

**📅 Finalizado:** <t:{int(datetime.datetime.now().timestamp())}:F>""",
                color=0xffd700
            )

            # Tentar adicionar avatar do vencedor
            if winner.avatar:
                embed.set_thumbnail(url=winner.avatar.url)

            # Anunciar no canal original
            original_channel = interaction.guild.get_channel(copinha[3])
            if original_channel:
                await original_channel.send(embed=embed)

            logger.info(f"Copinha {copinha[5]} finalizada com vencedor: {winner}")

        except Exception as e:
            logger.error(f"Erro ao anunciar vencedor: {e}")

# Views com botões para substituir confirmações de emoji
class ConfirmButtonView(discord.ui.View):
    def __init__(self, action_type, user_id, **kwargs):
        super().__init__(timeout=30)
        self.action_type = action_type
        self.user_id = user_id
        self.kwargs = kwargs
        self.result = None

    @discord.ui.button(label="✅ Confirmar", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Apenas quem iniciou pode confirmar!", ephemeral=True)
            return

        self.result = True
        self.stop()
        await interaction.response.edit_message(content="✅ Confirmado!", view=None)

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Apenas quem iniciou pode cancelar!", ephemeral=True)
            return

        self.result = False
        self.stop()
        await interaction.response.edit_message(content="❌ Cancelado!", view=None)

# View para comandos administrativos com formulários
class AdminCommandView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📋 Resultado Teste Tier", style=discord.ButtonStyle.primary, emoji="👑")
    async def tier_result(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Apenas administradores podem usar este comando!", ephemeral=True)
            return
        await interaction.response.send_modal(TierResultModal())

    @discord.ui.button(label="🏆 Resultado XClan", style=discord.ButtonStyle.secondary, emoji="⚔️")
    async def xclan_result(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Apenas moderadores podem usar este comando!", ephemeral=True)
            return
        await interaction.response.send_modal(XClanResultModal())

    @discord.ui.button(label="💰 Sorteio de Coins", style=discord.ButtonStyle.success, emoji="🎁")
    async def coin_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Apenas administradores podem criar sorteios de coins!", ephemeral=True)
            return
        await interaction.response.send_modal(CoinGiveawayModal(interaction.user.id))

# View para seleção de staff
class StaffSelectionView(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=300)  # 5 minutos
        self.guild = guild

        # Buscar membros com cargos de staff
        staff_members = []
        staff_role_names = ['admin', 'administrador', 'mod', 'moderador', 'staff', 'suporte', 'helper', 'ajudante']

        for member in guild.members:
            if member.bot:
                continue
            for role in member.roles:
                if any(staff_name in role.name.lower() for staff_name in staff_role_names) or role.permissions.administrator:
                    staff_members.append(member)
                    break

        # Limitar a 25 opções (máximo do Discord)
        staff_members = staff_members[:25]

        if staff_members:
            # Criar select menu
            options = []
            for member in staff_members:
                options.append(discord.SelectOption(
                    label=member.display_name,
                    value=str(member.id),
                    description=f"Avaliar {member.display_name}",
                    emoji="👥"
                ))

            if options:
                self.add_item(StaffSelect(options))

class StaffSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(
            placeholder="Escolha o staff para avaliar...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        selected_member_id = int(self.values[0])
        selected_member = interaction.guild.get_member(selected_member_id)

        if not selected_member:
            await interaction.response.send_message("❌ Staff não encontrado!", ephemeral=True)
            return

        # Abrir modal de feedback
        await interaction.response.send_modal(StaffFeedbackModal(selected_member.display_name))

# View principal do feedback
class FeedbackMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Sem timeout - botão permanente

    @discord.ui.button(label="📊 Avaliar Staff", style=discord.ButtonStyle.primary, emoji="⭐")
    async def avaliar_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Criar view de seleção de staff
        view = StaffSelectionView(interaction.guild)

        if not view.children:
            await interaction.response.send_message("❌ Nenhum membro da staff encontrado neste servidor!", ephemeral=True)
            return

        embed = create_embed(
            "👥 Selecionar Staff para Avaliar",
            "Escolha o membro da staff que você deseja avaliar no menu abaixo:",
            color=0x7289da
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.command(name='painelcomandos', aliases=['adminpanel', 'comandosadmin'])
@commands.has_permissions(administrator=True)
async def painel_comandos_admin(ctx):
    """[ADMIN] Criar painel de comandos administrativos com formulários"""

    embed = create_embed(
        "👑 Painel de Comandos Administrativos",
        f"""**🛡️ Sistema Avançado para Staff**

**📋 Comandos Disponíveis:**
• **📋 Resultado Teste Tier** - Enviar resultado de teste tier
• **🏆 Resultado XClan** - Enviar resultado de batalha XClan
• **💰 Sorteio de Coins** - Criar sorteio automático de coins

**✨ Vantagens do sistema:**
• 📝 Formulários interativos organizados
• ⚡ Envio automático para canais corretos
• 💾 Registro automático no banco de dados
• 🎯 Interface moderna e intuitiva

**🔧 Como usar:**
1️⃣ Clique no botão do comando desejado
2️⃣ Preencha o formulário que aparece
3️⃣ Confirme o envio
4️⃣ O sistema processa automaticamente

**👑 Painel criado por:** {ctx.author.mention}
**📅 Data:** <t:{int(datetime.datetime.now().timestamp())}:F>

⬇️ **ESCOLHA O COMANDO DESEJADO:**""",
        color=0xff6b6b
    )

    view = AdminCommandView()
    await ctx.send(embed=embed, view=view)

    # Confirmar criação
    confirm_embed = create_embed(
        "✅ Painel Administrativo Criado!",
        f"Sistema de comandos com formulários ativo!\nTodos os comandos agora têm interface moderna.",
        color=0x00ff00
    )
    await ctx.send(embed=confirm_embed, delete_after=10)

@bot.command(name='mensagemfeedback', aliases=['feedbackmessage'])
@commands.has_permissions(administrator=True)
async def mensagem_feedback(ctx):
    """[ADMIN] Criar painel de feedback para staff"""

    embed = create_embed(
        "📊 Sistema de Avaliação de Staff",
        f"""**⭐ Avalie nosso atendimento!**

**🎯 Como funciona:**
1️⃣ Clique no botão "📊 Avaliar Staff"
2️⃣ Escolha o membro da staff que te atendeu
3️⃣ Preencha o formulário de avaliação
4️⃣ Suas notas são calculadas automaticamente

**📋 Critérios de Avaliação:**
• ⭐ **Atendimento** - Cordialidade e educação
• 🎯 **Qualidade** - Resolução do problema
• ⚡ **Rapidez** - Tempo de resposta
• 🤝 **Profissionalismo** - Postura e conhecimento

**📊 Sistema de Notas:**
• **0-4:** Ruim ❌
• **5-6:** Regular ⚠️  
• **7-8:** Bom ⭐
• **9-10:** Excelente 🌟

**✨ Benefícios:**
• 💯 Avaliação justa e transparente
• 📈 Melhoria contínua do atendimento
• 🏆 Reconhecimento dos melhores
• 📊 Estatísticas automáticas

**👑 Painel criado por:** {ctx.author.mention}

⬇️ **CLIQUE NO BOTÃO PARA AVALIAR:**""",
        color=0x7289da
    )

    view = FeedbackMainView()
    await ctx.send(embed=embed, view=view)

    # Confirmar criação
    confirm_embed = create_embed(
        "✅ Painel de Feedback Criado!",
        f"Sistema de avaliação de staff ativo!\nTodas as avaliações aparecerão em <#1401195599281393754>",
        color=0x00ff00
    )
    await ctx.send(embed=confirm_embed, delete_after=10)

# ============ SISTEMA DE TICKETS PÚBLICOS ============
@bot.command(name='ticketpublico', aliases=['rxticketpublico'])
@commands.has_permissions(manage_messages=True)
async def criar_ticket_publico(ctx, tipo=None):
    """[MOD] Criar sistema de ticket público"""

    if tipo is None:
        # Menu principal
        embed = create_embed(
            "🎟️ Sistema de Tickets Públicos",
            """**Comandos disponíveis:**

`RXticketpublico` - Criar painel geral de tickets
`RXticketpublico atendimento` - Criar painel de atendimento
`RXticketpublico testetier` - Criar painel para teste tier

**ℹ️ Como funciona:**
• Moderador usa o comando
• Bot cria uma mensagem com botão
• Qualquer pessoa pode clicar e criar ticket
• Sem limites de uso ou quantidade de pessoas""",
            color=0x7289da
        )
        await ctx.send(embed=embed)
        return

    elif tipo.lower() == "atendimento":
        # Painel de atendimento geral
        embed = create_embed(
            "🎧 Sistema de Atendimento - Tickets",
            f"""**🌟 Precisa de ajuda? Estamos aqui para você!**

**📋 Tipos de atendimento disponíveis:**
• 🐛 **Problemas técnicos** - Bugs, erros, falhas
• 💰 **Economia** - Problemas com moedas, loja, itens
• ⚖️ **Moderação** - Denúncias, reports, punições
• 💡 **Sugestões** - Ideias e melhorias
• ❓ **Dúvidas gerais** - Comandos, funcionamento
• 🛠️ **Suporte técnico** - Configurações, permissões

**✨ Vantagens do nosso atendimento:**
• ⚡ **Resposta rápida** da equipe
• 🔒 **Canal privado** só para você
• 👥 **Suporte especializado** por categoria
• 📋 **Histórico salvo** para acompanhamento

**🚀 Criar seu ticket é simples:**
Clique no botão abaixo e seu canal privado será criado instantaneamente!

*Criado por {ctx.author.mention} | {ctx.guild.name}*""",
            color=0x00ff00
        )

        view = PublicTicketView("atendimento")
        msg = await ctx.send(embed=embed, view=view)

        # Confirmar para o moderador
        confirm_embed = create_embed(
            "✅ Painel de Atendimento Criado!",
            f"Sistema público de tickets de atendimento ativo!\nQualquer pessoa pode clicar no botão para criar um ticket.",
            color=0x00ff00
        )
        await ctx.send(embed=confirm_embed, delete_after=10)

    elif tipo.lower() == "testetier":
        # Painel específico para teste tier
        embed = create_embed(
            "👑 Sistema de Teste Tier - Tickets",
            f"""**🎯 TESTE TIER EXCLUSIVO**

**📋 Sobre o Teste Tier:**
• 🏆 **Avaliação especializada** da equipe tier
• 📊 **Critérios rigorosos** de seleção
• 🎮 **Testes práticos** de habilidade
• 👑 **Acesso a benefícios exclusivos** se aprovado

**✨ O que você precisa saber:**
• 📝 **Prepare-se bem** antes de fazer o teste
• ⏰ **Atendimento prioritário** garantido
• 🔍 **Avaliação completa** de suas skills
• 📈 **Feedback detalhado** sobre seu desempenho

**🎪 Benefícios de ser Tier:**
• 🌟 **Privilégios especiais** no servidor
• 💎 **Acesso a canais exclusivos**
• 🎁 **Recompensas diferenciadas**
• 👑 **Reconhecimento da comunidade**

**🚀 Pronto para o desafio?**
Clique no botão abaixo para iniciar seu teste tier!

*Criado por {ctx.author.mention} | Sistema Tier {ctx.guild.name}*""",
            color=0xffd700
        )

        view = PublicTicketView("testetier")
        msg = await ctx.send(embed=embed, view=view)

        # Confirmar para o moderador
        confirm_embed = create_embed(
            "✅ Painel de Teste Tier Criado!",
            f"Sistema público de teste tier ativo!\nQualquer pessoa pode clicar no botão para criar um ticket de teste tier.",
            color=0xffd700
        )
        await ctx.send(embed=confirm_embed, delete_after=10)

    else:
        # Painel geral de tickets
        embed = create_embed(
            "🎟️ Sistema Geral de Tickets",
            f"""**🌟 Central de Suporte {ctx.guild.name}**

**📞 Precisa de ajuda? Crie seu ticket agora!**

**🔧 Nosso sistema oferece:**
• 🏆 **Atendimento personalizado** da equipe
• 🔒 **Privacidade total** - só você e a staff veem
• ⚡ **Resposta rápida** em horário comercial
• 📋 **Histórico completo** de todas as interações
• ✨ **Suporte especializado** para cada tipo de problema

**📋 Para que você pode usar:**
• Reportar bugs ou problemas técnicos
• Fazer denúncias ou reports
• Tirar dúvidas sobre comandos
• Sugerir melhorias para o servidor
• Resolver problemas com economia
• Qualquer outro assunto que precise de atenção da staff

**🎯 É muito simples:**
1. Clique no botão abaixo
2. Seu ticket será criado automaticamente
3. Descreva sua situação no canal privado
4. Nossa equipe te atenderá em breve!

*Sistema criado por {ctx.author.mention} | Suporte 24/7*""",
            color=0x7289da
        )

        view = PublicTicketView("geral")
        msg = await ctx.send(embed=embed, view=view)

        # Confirmar para o moderador
        confirm_embed = create_embed(
            "✅ Painel de Tickets Criado!",
            f"Sistema público de tickets ativo!\nQualquer pessoa pode clicar no botão para criar um ticket.",
            color=0x00ff00
        )
        await ctx.send(embed=confirm_embed, delete_after=10)

# Classe para seleção de mapas do Stumble Guys
class StumbleGuysEventView(discord.ui.View):
    def __init__(self, clan_name, creator_id, end_time):
        super().__init__(timeout=3600)  # 1 hora para escolher mapa
        self.clan_name = clan_name
        self.creator_id = creator_id
        self.end_time = end_time

    @discord.ui.button(label="🏃 Block Dash", style=discord.ButtonStyle.primary)
    async def block_dash(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.select_map(interaction, "Block Dash", "🏃")

    @discord.ui.button(label="🌊 Water Race", style=discord.ButtonStyle.primary)
    async def water_race(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.select_map(interaction, "Water Race", "🌊")

    @discord.ui.button(label="🔥 Lava Land", style=discord.ButtonStyle.danger)
    async def lava_land(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.select_map(interaction, "Lava Land", "🔥")

    @discord.ui.button(label="❄️ Ice Cold", style=discord.ButtonStyle.secondary)
    async def ice_cold(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.select_map(interaction, "Ice Cold", "❄️")

    @discord.ui.button(label="🌪️ Wind Rush", style=discord.ButtonStyle.success)
    async def wind_rush(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.select_map(interaction, "Wind Rush", "🌪️")

    @discord.ui.button(label="⚡ Speed Run", style=discord.ButtonStyle.danger)
    async def speed_run(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.select_map(interaction, "Speed Run", "⚡")

    async def select_map(self, interaction, map_name, map_emoji):
        # Verificar se é o criador ou admin
        if interaction.user.id != self.creator_id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Apenas o criador do evento ou admins podem selecionar o mapa!", ephemeral=True)
            return

        try:
            # Atualizar banco de dados
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE clan_events 
                    SET selected_map = ? 
                    WHERE message_id = ?
                ''', (map_name, interaction.message.id))
                conn.commit()
                conn.close()

            # Criar embed atualizado com mapa selecionado
            embed = create_embed(
                f"🎮 EVENTO STUMBLE GUYS - {self.clan_name}",
                f"""**🏆 Clan:** {self.clan_name}
**🗺️ Mapa Selecionado:** {map_emoji} **{map_name}**
**🏁 Termina:** <t:{int(self.end_time.timestamp())}:R>
**👑 Mapa escolhido por:** {interaction.user.mention}

**📋 Agora os membros podem participar:**
Reaja com 🎮 para entrar na batalha!

**⚠️ Instruções:**
• Apenas membros do {self.clan_name}
• Partida no mapa **{map_name}**
• Sem apostas - apenas diversão!
• Boa sorte a todos!""",
                color=0x00ff00
            )

            # Desativar todos os botões
            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(embed=embed, view=self)

            # Adicionar reação para participar
            await interaction.followup.send("✅ Mapa selecionado! Agora os membros podem reagir com 🎮 para participar!", ephemeral=True)
            await interaction.message.add_reaction("🎮")

            logger.info(f"Mapa {map_name} selecionado para evento do clan {self.clan_name}")

        except Exception as e:
            logger.error(f"Erro ao selecionar mapa: {e}")
            await interaction.response.send_message("❌ Erro ao selecionar mapa!", ephemeral=True)

# View para fechar tickets com botões
class CloseTicketView(discord.ui.View):
    def __init__(self, closer_id):
        super().__init__(timeout=None)  # Sem timeout - botão permanente
        self.closer_id = closer_id

    @discord.ui.button(label="🔒 Confirmar Fechamento", style=discord.ButtonStyle.danger, emoji="🔒")
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.closer_id:
            await interaction.response.send_message("❌ Apenas quem iniciou o fechamento pode confirmar!", ephemeral=True)
            return

        try:
            # Fechar ticket imediatamente
            closer = interaction.guild.get_member(self.closer_id)

            # Buscar informações do ticket para logs
            ticket_creator = None
            try:
                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('SELECT creator_id FROM tickets WHERE channel_id = %s', (interaction.channel.id,))
                    result = cursor.fetchone()
                    if result:
                        ticket_creator = interaction.guild.get_member(result[0])
                    conn.close()
            except Exception as e:
                logger.error(f"Erro ao buscar criador do ticket: {e}")

            # Atualizar banco de dados
            try:
                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE tickets
                        SET status = 'closed', closed_by = ?
                        WHERE channel_id = ?
                    ''', (self.closer_id, interaction.channel.id))
                    conn.commit()
                    conn.close()
            except Exception as e:
                logger.error(f"Erro ao atualizar ticket no banco: {e}")

            # Enviar mensagem de fechamento
            final_embed = create_embed(
                "🔒 Ticket Fechado com Sucesso",
                f"**📋 Detalhes do Fechamento:**\n"
                f"**Fechado por:** {closer.mention if closer else 'Usuário desconhecido'}\n"
                f"**Criado por:** {ticket_creator.mention if ticket_creator else 'Usuário desconhecido'}\n"
                f"**Data/Hora:** <t:{int(datetime.datetime.now().timestamp())}:F>\n"
                f"**Canal:** {interaction.channel.name}\n\n"
                f"🗑️ **Este canal será deletado em 3 segundos...**\n"
                f"💾 Dados salvos no banco de dados para histórico.",
                color=0xff6b6b
            )

            await interaction.response.edit_message(embed=final_embed, view=None)

            # Log do fechamento
            logger.info(f"Ticket fechado: {interaction.channel.name} por {closer.name if closer else 'Unknown'}")

            # Notificar em canal de logs se existir
            try:
                log_channel = discord.utils.get(interaction.guild.channels, name="logs-tickets")
                if log_channel:
                    log_embed = create_embed(
                        "🔒 Ticket Fechado",
                        f"**Canal:** {interaction.channel.name}\n"
                        f"**Fechado por:** {closer.mention if closer else 'Desconhecido'}\n"
                        f"**Criado por:** {ticket_creator.mention if ticket_creator else 'Desconhecido'}\n"
                        f"**Data:** <t:{int(datetime.datetime.now().timestamp())}:F>",
                        color=0xff6b6b
                    )
                    await log_channel.send(embed=log_embed)
            except:
                pass

            # Aguardar e deletar canal
            await asyncio.sleep(3)
            await interaction.channel.delete(reason=f"Ticket fechado por {closer.name if closer else 'Unknown'}")

        except discord.NotFound:
            # Canal já foi deletado
            pass
        except Exception as e:
            logger.error(f"Erro ao fechar ticket: {e}")
            try:
                error_embed = create_embed(
                    "❌ Erro ao Fechar Ticket",
                    f"Ocorreu um erro: {str(e)[:200]}\n\nContate um administrador.",
                    color=0xff0000
                )
                await interaction.channel.send(embed=error_embed)
            except:
                pass

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.closer_id:
            await interaction.response.send_message("❌ Apenas quem iniciou o fechamento pode cancelar!", ephemeral=True)
            return

        try:
            cancel_embed = create_embed(
                "❌ Fechamento Cancelado",
                f"O fechamento do ticket foi cancelado por {interaction.user.mention}.\n"
                f"O ticket permanece **aberto** e funcional.",
                color=0xffaa00
            )
            await interaction.response.edit_message(embed=cancel_embed, view=None)
        except Exception as e:
            logger.error(f"Erro ao cancelar fechamento: {e}")

# Classe para os botões dos tickets públicos
class PublicTicketView(discord.ui.View):
    def __init__(self, tipo):
        super().__init__(timeout=None)  # Sem timeout para botões permanentes
        self.tipo = tipo

    @discord.ui.button(label="🎟️ Criar Ticket", style=discord.ButtonStyle.primary, emoji="🎟️")
    async def criar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            user = interaction.user
            guild = interaction.guild

            # Definir motivo baseado no tipo
            if self.tipo == "atendimento":
                motivo = "Atendimento Geral - Painel Público"
                emoji = "🎧"
                cor = 0x00ff00
            elif self.tipo == "testetier":
                motivo = "Teste Tier - Painel Público"
                emoji = "👑"
                cor = 0xffd700
            else:
                motivo = "Suporte Geral - Painel Público"
                emoji = "🎟️"
                cor = 0x7289da

            # Verificar se usuário já tem ticket aberto
            existing_channels = [ch for ch in guild.channels if ch.name.startswith('ticket-') and str(user.id) in ch.name]
            if len(existing_channels) >= 3:  # Limite de 3 tickets simultâneos
                embed = create_embed(
                    "⚠️ Limite de Tickets",
                    "Você já tem muitos tickets abertos! Feche alguns antes de criar novos.",
                    color=0xff6600
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Responder imediatamente
            embed_loading = create_embed(
                f"{emoji} Criando Ticket...",
                f"Criando seu ticket de {motivo.lower()}...\nAguarde alguns segundos!",
                color=cor
            )
            await interaction.response.send_message(embed=embed_loading, ephemeral=True)

            # Criar ticket usando a função existente
            ctx_mock = type('MockCtx', (), {
                'guild': guild,
                'channel': interaction.channel,
                'send': interaction.channel.send,
                'author': user  # Para logs
            })()

            await create_ticket_channel(ctx_mock, motivo, user)

            # Confirmar criação
            embed_success = create_embed(
                f"✅ {emoji} Ticket Criado!",
                f"Seu ticket foi criado com sucesso!\n**Tipo:** {motivo}\n\nVerifique a categoria **📋 Tickets** para encontrar seu canal.",
                color=cor
            )

            try:
                await interaction.edit_original_response(embed=embed_success)
            except:
                await interaction.followup.send(embed=embed_success, ephemeral=True)

            # Log da criação
            logger.info(f"Ticket público criado: {user.name} - Tipo: {self.tipo}")

        except Exception as e:
            logger.error(f"Erro ao criar ticket público: {e}")
            try:
                embed_error = create_embed(
                    "❌ Erro ao Criar Ticket",
                    "Ocorreu um erro ao criar seu ticket. Tente novamente ou contate um administrador.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed_error, ephemeral=True)
            except:
                try:
                    await interaction.edit_original_response(embed=embed_error)
                except:
                    pass

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
                VALUES (%s, %s, %s, %s)
            ''', (guild.id, user.id, ticket_channel.id, motivo))
            ticket_id = cursor.lastrowid
            conn.commit()
            conn.close()
    except Exception as e:
        logger.error(f"Error saving ticket: {e}")
        ticket_id = "ERRO"

    # Embed inicial do ticket
    priority_text = "🎫 PRIORITÁRIO " if priority else ""

    # Determinar cor e emoji baseado no tipo
    if "Teste Tier" in motivo:
        cor = 0xffd700
        emoji_tipo = "👑"
    elif "Atendimento" in motivo:
        cor = 0x00ff00
        emoji_tipo = "🎧"
    elif "Painel Público" in motivo:
        cor = 0x7289da
        emoji_tipo = "🎟️"
    else:
        cor = 0x7289da if not priority else 0xffd700
        emoji_tipo = "🎟️"

    # View para fechar ticket com botão
    class TicketCloseView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)  # Sem timeout - botão permanente

        @discord.ui.button(label="🔒 Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
        async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
            # Verificar permissões
            has_permission = False
            is_creator = False

            member = interaction.user
            if member:
                has_permission = (member.guild_permissions.manage_channels or
                                member.guild_permissions.administrator or
                                any(role.name.lower() in ['admin', 'mod', 'staff', 'moderador', 'administrador'] for role in member.roles))

            try:
                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('SELECT creator_id FROM tickets WHERE channel_id = %s', (interaction.channel.id,))
                    result = cursor.fetchone()
                    if result and result[0] == interaction.user.id:
                        is_creator = True
                    conn.close()
            except Exception as e:
                logger.error(f"Erro ao verificar criador do ticket: {e}")

            if not (has_permission or is_creator):
                await interaction.response.send_message(
                    "❌ **Sem permissão!** Apenas staff ou o criador do ticket podem fechá-lo!",
                    ephemeral=True
                )
                return

            # Mostrar confirmação com botões
            confirm_embed = create_embed(
                "🔒 Fechar Ticket?",
                f"**{interaction.user.mention}** deseja fechar este ticket?\n\n"
                f"**⚠️ Esta ação é irreversível!**\n"
                f"O canal será **DELETADO** permanentemente!\n\n"
                f"**🎯 Use os botões abaixo para confirmar ou cancelar.**\n"
                f"**✨ Sem tempo limite - decida quando quiser!**",
                color=0xff6b6b
            )

            view = CloseTicketView(interaction.user.id)
            await interaction.response.send_message(embed=confirm_embed, view=view)

    embed = create_embed(
        f"{emoji_tipo} {priority_text}Ticket #{ticket_id}",
        f"""**Criado por:** {user.mention}
**Motivo:** {motivo}
**Status:** 🟢 Aberto
**Criado em:** <t:{int(datetime.datetime.now().timestamp())}:F>

📋 **Informações:**
• Este ticket foi criado automaticamente
• A staff será notificada em breve
• Para fechar o ticket, clique no botão abaixo

{"🎫 **Este ticket tem prioridade!**" if priority else ""}
{"👑 **Este é um ticket de Teste Tier especial!**" if "Teste Tier" in motivo else ""}

⚠️ **Regras do ticket:**
• Seja respeitoso e educado
• Descreva seu problema claramente
• Aguarde a resposta da staff
• Não spam ou flood""",
        color=cor
    )

    view = TicketCloseView()
    msg = await ticket_channel.send(f"{user.mention}", embed=embed, view=view)

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

# ============ COMANDOS FALTANDO ADICIONADOS ============

@bot.command(name='perfil', aliases=['profile'])
async def perfil(ctx, user: discord.Member = None):
    """Ver perfil completo do usuário"""
    global_stats['commands_used'] += 1
    target = user or ctx.author

    try:
        user_data = get_user_data(target.id)
        if not user_data:
            update_user_data(target.id)
            user_data = get_user_data(target.id)

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
        user_data = get_user_data(target.id)
        if not user_data:
            update_user_data(target.id)
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

@bot.command(name='top', aliases=['toplist'])
async def top_users(ctx):
    """Ranking geral do servidor"""
    global_stats['commands_used'] += 1

    try:
        with db_lock:
            conn = get_db_connection()
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
                xp_text += f"{medal} {user.display_name} - {rank_data['emoji']} Lv.{level} ({xp:,} XP)\n"

        if xp_text:
            embed.add_field(name="⭐ Top XP/Level", value=xp_text, inline=True)

        # Top Coins
        coins_text = ""
        for i, (user_id, coins, bank) in enumerate(top_coins[:5]):
            user = ctx.guild.get_member(user_id)
            if user:
                total = coins + bank
                medal = ["🥇", "🥈", "🥉", "4º", "5º"][i]
                coins_text += f"{medal} {user.display_name} - {total:,} moedas\n"

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

@bot.command(name='roles')
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

        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Verificar se usuário existe
            cursor.execute('SELECT user_id, inventory FROM users WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()

            if not result:
                embed = create_embed("❌ Usuário não encontrado", "Criando dados do usuário...", color=0xff6600)
                await ctx.send(embed=embed)

                # Criar usuário
                cursor.execute('INSERT INTO users (user_id) VALUES (%s)', (user_id,))
                conn.commit()

                cursor.execute('SELECT user_id, inventory FROM users WHERE user_id = %s', (user_id,))
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
        resultados.append("✅ **Database:** Funcionando - " + str(user_count) + " usuários")
    except Exception as e:
        resultados.append("❌ **Database:** Erro - " + str(e)[:50] + "...")

    # 2. Teste Sistema HTTP
    try:
        # Sistema HTTP simplificado sem keep-alive
        resultados.append("✅ **Sistema HTTP:** Simplificado ativo")
    except Exception as e:
        resultados.append("❌ **Sistema HTTP:** Erro - " + str(e))

    # 3. Teste Memória
    try:
        import psutil
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent()
        resultados.append("✅ **Sistema:** RAM " + str(memory.percent) + "%, CPU " + str(cpu) + "%")
    except Exception as e:
        resultados.append("⚠️ **Sistema:** Dados não disponíveis")

    # 4. Teste Conexão Discord
    latency = round(bot.latency * 1000, 2)
    if latency < 200:
        resultados.append("✅ **Discord:** " + str(latency) + "ms - Excelente")
    else:
        resultados.append("⚠️ **Discord:** " + str(latency) + "ms - Lenta")

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
        resultados.append("✅ **Tasks:** " + str(len(running_tasks)) + "/4 ativos")
    else:
        resultados.append("⚠️ **Tasks:** " + str(len(running_tasks)) + "/4 ativos")

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
        resultados.append("⚠️ **Arquivos:** " + str(arquivos_ok) + "/" + str(len(arquivos_criticos)) + " encontrados")

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
        "**" + status + "**" +

        "\n\n**📊 Resumo:**\n"
        "• ✅ OK: " + str(sucessos) + "\n"
        "• ⚠️ Avisos: " + str(avisos) + "\n"
        "• ❌ Erros: " + str(erros) + "\n\n"
        "**📋 Detalhes:**\n" + "\n".join(resultados) +

        f"""

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

    # 2. Teste Sistema HTTP
    try:
        # Sistema HTTP simplificado sem keep-alive
        resultados.append("✅ **Sistema HTTP:** Simplificado ativo")
    except Exception as e:
        resultados.append("❌ **Sistema HTTP:** Erro - " + str(e))

    # 3. Teste Guild e Permissions
    try:
        guild = ctx.guild
        if guild and hasattr(guild, 'categories'):
            resultados.append("✅ **Guild:** Válido - " + guild.name)
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
        resultados.append("✅ **Background Tasks:** " + str(len(running_tasks)) + " ativos - " + ", ".join(running_tasks))
    else:
        resultados.append("❌ **Background Tasks:** Nenhum ativo")

    # 8. Teste Final - Latência
    start = time.time()
    latency = round(bot.latency * 1000, 2)
    end = time.time()
    response_time = round((end - start) * 1000, 2)

    if latency < 200:
        resultados.append("✅ **Latência:** " + str(latency) + "ms - Excelente")
    else:
        resultados.append("⚠️ **Latência:** " + str(latency) + "ms - Alta")

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
        "**" + status + "**" +

        "\n\n**📈 Resumo:**\n"
        "• ✅ Sucessos: " + str(sucesso) + "\n"
        "• ⚠️ Avisos: " + str(avisos) + "\n"
        "• ❌ Erros: " + str(erros) + "\n\n"
        "**📋 Detalhes:**\n" + "\n".join(resultados) +

        f"""

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
`RXcriarsorteio iPhone 15 | iPhone novo | 24h | 1`

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
            """**📝 Criar Tickets (Usuários):**
• `RXticket <motivo>` - Criar ticket com motivo específico
• `RXticket` - Menu interativo de criação rápida
• `RXtestetier` - Ticket específico para teste tier

**🎯 Sistema Rápido (React):**
🐛 Bug/Erro no bot | 💰 Problema com economia
⚖️ Denúncia/Moderação | 💡 Sugestão/Ideia
❓ Dúvida geral | 🛠️ Suporte técnico | 👑 Tier

**🌐 Sistema de Tickets Públicos (MOD):**
• `RXticketpublico` - Painel geral de tickets
• `RXticketpublico atendimento` - Painel de atendimento
• `RXticketpublico testetier` - Painel de teste tier
• Qualquer pessoa pode clicar e criar ticket
• Sem limites de uso ou quantidade

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

**📊 Sistema de Feedback de Staff:**
• `RXmensagemfeedback` - Criar painel de avaliação de staff
• `RXfeedbacksstaff` - Ver avaliações de staff (com ranking)

**🎁 Sistema de Sorteios:**
• `RXcriarsorteio <dados>` - Criar sorteios
• `RXendgiveaway <id>` - Finalizar sorteio
• `RXreroll <id>` - Sortear novamente

**⚔️ Eventos de Clan:**
• `RXcriareventoclan <dados>` - Criar batalha entre clans
• `RXeventosclan` - Ver eventos ativos
• `RXfinalizareventoclan <id> <vencedor>` - Finalizar evento

**🎯 Eventos Personalizados (NOVO):**
• `RXcriar <tipo>` - Criar eventos com reações
• `RXcriar xtreino` - Criar treino personalizado
• `RXcriar xtreino Título | hoje | 20:00` - Formato rápido
• Tipos: xtreino, treino, torneio, evento, meeting, party

**💰 Economia Admin (RESTRITO):**
• `RXaddsaldo <@user> <valor>` - Adicionar saldo (apenas IDs autorizados)
• `RXremovesaldo <@user> <valor>` - Remover saldo (apenas IDs autorizados)

**🛡️ Moderação Avançada:**
• `RXban <@user> [motivo]` - Ban com confirmação
• `RXkick <@user> [motivo]` - Kick com confirmação
• `RXclear <quantidade>` - Limpeza com confirmação
• `RXwarn <@user> [motivo]` - Sistema de warns

**🔧 Sistema e Monitoramento:**
• `RXdiagnostico` - Diagnóstico completo do sistema
• `RXperformance` - Monitor de performance detalhado
• `RXtestecompleto` - Teste de todos os sistemas
• `RXbackup` - [ADMIN] Backup do banco de dados

**💡 Total:** 300+ comandos | Sistema de eventos personalizados""",
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
            "🎮 Sistema de Eventos Stumble Guys",
            """**🚨 EVENTOS XCLAN VS (NOVO):**
• `RXmensagemxclan` - Criar evento RX vs outro clan (interativo)
• `RXresultadoxclan <resultado>` - [MOD] Enviar resultado do evento
• Sistema completo com formulário interativo
• Publicação automática com @everyone ping

**🎯 EVENTOS PERSONALIZADOS (NOVO):**
• `RXcriar xtreino` - Criar treino personalizado
• `RXcriar xtreino Treino Block Dash | hoje | 20:00` - Formato rápido
• `RXcriar torneio` - Criar torneio
• `RXcriar evento` - Criar evento geral
• `RXcriar meeting` - Criar reunião
• Reações automáticas: ✅ (posso ir) ❌ (não posso) ❓ (talvez)

**Para Membros do Clan:**
• `RXeventosclan` - Ver eventos ativos
• Reaja com 🎮 para participar (sem custo!)

**Para Administradores:**
• `RXcriareventoclan <dados>` - Criar evento simples
• `RXfinalizareventoclan <id> <resultado>` - Finalizar

**🚨 SISTEMA XCLAN VS:**
1️⃣ Use `RXmensagemxclan`
2️⃣ Escolha clan adversário (WLX, TOP, PRO, etc.)
3️⃣ Selecione mapa do Stumble Guys
4️⃣ Defina MD (1, 3, 5, 7)
5️⃣ Escolha jogadores (1v1 até 6v6)
6️⃣ Defina data e horário
7️⃣ Escolha emotes do Stumble Guys
8️⃣ Publica automaticamente com ping @everyone

**🗺️ Mapas do Stumble Guys:**
🏃 **Block Dash** - Corrida clássica
🌊 **Water Race** - Corrida aquática  
🔥 **Lava Land** - Obstáculos de lava
❄️ **Ice Cold** - Pista escorregadia
🌪️ **Wind Rush** - Corrida com vento
⚡ **Speed Run** - Velocidade máxima

**📊 Envio de Resultado:**
• Use `RXresultadoxclan ## 🏆 RX vs WLX`
• `RX 11 ✖ 0 WLX`
• `Obs: WO`
• Resultado vai para <#1400167040504823869>

**Recompensas:**
• Vitória: 50 XP para todos
• Derrota/Empate: 25 XP para todos""",
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

    # Sistema de confirmação com botões
    class ClearConfirmView(discord.ui.View):
        def __init__(self, amount, channel, moderator):
            super().__init__(timeout=30)
            self.amount = amount
            self.channel = channel
            self.moderator = moderator

        @discord.ui.button(label="✅ Confirmar Limpeza", style=discord.ButtonStyle.danger)
        async def confirm_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.moderator.id:
                await interaction.response.send_message("❌ Apenas quem iniciou pode confirmar!", ephemeral=True)
                return

            try:


                # Deletar a mensagem de confirmação primeiro
                try:
                    await interaction.delete_original_response()
                except:
                    pass

                # Limpar mensagens do canal
                deleted = await self.channel.purge(limit=self.amount)

                confirm_embed = create_embed(
                    "🧹 Limpeza Concluída",
                    f"**{len(deleted)} mensagens foram deletadas com sucesso!**",
                    color=0x00ff00
                )
                await self.channel.send(embed=confirm_embed, delete_after=5)

            except Exception as e:
                logger.error(f"Erro na limpeza: {e}")
                embed = create_embed("❌ Erro na Limpeza", f"Erro: {str(e)[:100]}", color=0xff0000)
                try:
                    await self.channel.send(embed=embed, delete_after=10)
                except:
                    pass

        @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
        async def cancel_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.moderator.id:
                await interaction.response.send_message("❌ Apenas quem iniciou pode cancelar!", ephemeral=True)
                return

            embed = create_embed("❌ Limpeza Cancelada", "Operação cancelada pelo usuário.", color=0xff6b6b)
            await interaction.response.edit_message(embed=embed, view=None)

    embed = create_embed(
        "🧹 Confirmação de Limpeza",
        f"""**⚠️ ATENÇÃO: Ação Irreversível**

**Você está prestes a deletar {amount} mensagens!**

**📍 Canal:** {ctx.channel.mention}
**👤 Moderador:** {ctx.author.mention}
**📊 Quantidade:** {amount} mensagens

**Deseja realmente continuar?**

Use os botões abaixo para confirmar ou cancelar.""",
        color=0xff6b6b
    )

    view = ClearConfirmView(amount, ctx.channel, ctx.author)
    await ctx.send(embed=embed, view=view)

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

    # Sistema de confirmação com botões
    class BanConfirmView(discord.ui.View):
        def __init__(self, member, reason, moderator):
            super().__init__(timeout=30)
            self.member = member
            self.reason = reason
            self.moderator = moderator

        @discord.ui.button(label="✅ Confirmar Ban", style=discord.ButtonStyle.danger)
        async def confirm_ban(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.moderator.id:
                await interaction.response.send_message("❌ Apenas quem iniciou pode confirmar!", ephemeral=True)
                return

            try:
                await self.member.ban(reason=self.reason)

                embed = create_embed(
                    "🔨 Membro Banido!",
                    f"**Usuário:** {self.member.name}#{self.member.discriminator}\n"
                    f"**Motivo:** {self.reason}\n"
                    f"**Moderador:** {self.moderator.mention}",
                    color=0xff0000
                )
                await interaction.response.edit_message(embed=embed, view=None)

                # Log da moderação
                try:
                    with db_lock:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason)
                            VALUES (%s, %s, %s, %s, %s)
                        ''', (interaction.guild.id, self.member.id, self.moderator.id, 'ban', self.reason))
                        conn.commit()
                        conn.close()
                except Exception as e:
                    logger.error(f"Erro ao salvar log de moderação: {e}")

            except Exception as e:
                logger.error(f"Erro ao banir membro: {e}")
                embed = create_embed("❌ Erro", f"Erro ao banir membro: {str(e)[:100]}", color=0xff0000)
                await interaction.response.edit_message(embed=embed, view=None)

        @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
        async def cancel_ban(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.moderator.id:
                await interaction.response.send_message("❌ Apenas quem iniciou pode cancelar!", ephemeral=True)
                return

            embed = create_embed("❌ Ban Cancelado", "Operação de ban cancelada.", color=0xffaa00)
            await interaction.response.edit_message(embed=embed, view=None)

    embed = create_embed(
        "🔨 Confirmação de Ban",
        f"""**🚨 AÇÃO EXTREMAMENTE GRAVE**

**Você está prestes a BANIR um membro!**

**👤 Usuário:** {member.mention} ({member.name}#{member.discriminator})
**🛡️ Moderador:** {ctx.author.mention}
**📝 Motivo:** {reason}

**⚠️ Esta ação é IRREVERSÍVEL!**
**Tem certeza que deseja continuar?**

Use os botões abaixo para confirmar ou cancelar.""",
        color=0xff0000
    )

    view = BanConfirmView(member, reason, ctx.author)
    await ctx.send(embed=embed, view=view)

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
            cursor.execute('UPDATE users SET coins = %s, last_daily = %s WHERE user_id = %s',
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
@bot.command(name='rank', aliases=['nivel', 'meurank'])
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

# Modal para transferências
class TransferModal(discord.ui.Modal, title="💰 Transferir Dinheiro"):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    destinatario = discord.ui.TextInput(
        label="👤 Destinatário (mencione ou ID)",
        placeholder="@usuario ou ID do usuário",
        required=True,
        max_length=100
    )

    valor = discord.ui.TextInput(
        label="💰 Valor a Transferir",
        placeholder="Ex: 1000, 5000, 10000...",
        required=True,
        max_length=10
    )

    motivo = discord.ui.TextInput(
        label="📝 Motivo (Opcional)",
        placeholder="Ex: pagamento, presente, aposta...",
        required=False,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Processar destinatário
            dest_input = self.destinatario.value.strip()
            user = None

            # Tentar extrair ID de menção
            if dest_input.startswith('<@') and dest_input.endswith('>'):
                user_id = int(dest_input[2:-1].replace('!', ''))
                user = interaction.guild.get_member(user_id)
            elif dest_input.isdigit():
                user = interaction.guild.get_member(int(dest_input))
            else:
                # Buscar por nome
                user = discord.utils.find(lambda m: m.display_name.lower() == dest_input.lower() or m.name.lower() == dest_input.lower(), interaction.guild.members)

            if not user:
                await interaction.response.send_message("❌ Usuário não encontrado!", ephemeral=True)
                return

            if user.id == self.user_id:
                await interaction.response.send_message("❌ Você não pode transferir para si mesmo!", ephemeral=True)
                return

            # Validar valor
            try:
                amount = int(self.valor.value)
                if amount <= 0:
                    raise ValueError
            except ValueError:
                await interaction.response.send_message("❌ Valor deve ser um número positivo!", ephemeral=True)
                return

            # Verificar saldo
            sender_data = get_user_data(self.user_id)
            if not sender_data:
                await interaction.response.send_message("❌ Você não tem dados no sistema!", ephemeral=True)
                return

            sender_coins = sender_data[1]
            if sender_coins < amount:
                await interaction.response.send_message(
                    f"💸 **Dinheiro insuficiente!**\n"
                    f"Você tem: **{sender_coins:,} moedas**\n"
                    f"Necessário: **{amount:,} moedas**",
                    ephemeral=True
                )
                return

            # Processar transferência
            receiver_data = get_user_data(user.id)
            if not receiver_data:
                update_user_data(user.id)
                receiver_data = get_user_data(user.id)

            receiver_coins = receiver_data[1]

            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()

                # Atualizar saldos
                cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (sender_coins - amount, self.user_id))
                cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (receiver_coins + amount, user.id))

                # Registrar transações
                cursor.execute('''
                    INSERT INTO transactions (user_id, guild_id, type, amount, description)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (self.user_id, interaction.guild.id, 'transfer_out', -amount, f"Transferiu para {user.name}: {self.motivo.value or 'Sem motivo'}"))

                cursor.execute('''
                    INSERT INTO transactions (user_id, guild_id, type, amount, description)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (user.id, interaction.guild.id, 'transfer_in', amount, f"Recebeu de {interaction.user.name}: {self.motivo.value or 'Sem motivo'}"))

                conn.commit()
                conn.close()

            embed = create_embed(
                "✅ Transferência Realizada!",
                f"""**💰 Transferência concluída com sucesso!**

**👤 De:** <@{self.user_id}>
**👤 Para:** {user.mention}
**💰 Valor:** {amount:,} moedas
**📝 Motivo:** {self.motivo.value or "Não informado"}

**💳 Novo saldo:** {sender_coins - amount:,} moedas

*Transferência registrada no sistema.*""",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed)

            # Notificar receptor
            try:
                dm_embed = create_embed(
                    "💰 Dinheiro Recebido!",
                    f"Você recebeu **{amount:,} moedas** de <@{self.user_id}>!\n"
                    f"**Motivo:** {self.motivo.value or 'Não informado'}\n"
                    f"**Seu novo saldo:** {receiver_coins + amount:,} moedas",
                    color=0x00ff00
                )
                await user.send(embed=dm_embed)
            except:
                pass

        except Exception as e:
            logger.error(f"Erro na transferência: {e}")
            await interaction.response.send_message("❌ Erro ao processar transferência! Tente novamente.", ephemeral=True)

# View para transferências
class TransferView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💰 Transferir com Formulário", style=discord.ButtonStyle.success, emoji="💸")
    async def transfer_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TransferModal(interaction.user.id))

@bot.command(name='transferir', aliases=['transfer', 'pay'])
async def transferir(ctx, user: discord.Member = None, amount: int = None):
    """Transferir dinheiro para outro usuário"""
    # Se não forneceu argumentos, mostrar sistema moderno
    if not user or not amount:
        embed = create_embed(
            "💰 Sistema de Transferências Avançado",
            """**🚀 Sistema Moderno com Formulário!**

Clique no botão abaixo para transferir dinheiro com formulário interativo!

**✨ Vantagens do novo sistema:**
• 📝 Formulário fácil de preencher
• 🔍 Busca automática de usuários
• ✅ Validação automática de dados
• 📝 Campo para motivo da transferência
• ⚡ Transferência instantânea

**📋 Formato antigo ainda funciona:**
`RXtransferir @usuário valor`

**Exemplo:**
`RXtransferir @João 5000`

⬇️ **RECOMENDADO: Use o botão abaixo!**""",
            color=0x00ff00
        )

        view = TransferView()
        await ctx.send(embed=embed, view=view)
        return

    if amount <= 0:
        embed = create_embed("❌ Valor inválido", "Use valores positivos!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if user == ctx.author:
        embed = create_embed("❌ Impossível", "Você não pode transferir para si mesmo!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    sender_data = get_user_data(ctx.author.id)
    if not sender_data:
        update_user_data(ctx.author.id)
        sender_data = get_user_data(ctx.author.id)

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
        receiver_data = get_user_data(user.id)
        if not receiver_data:
            update_user_data(user.id)
            receiver_data = get_user_data(user.id)

        receiver_coins = receiver_data[1]

        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Atualizar saldos
            cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (sender_coins - amount, ctx.author.id))
            cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (receiver_coins + amount, user.id))

            # Registrar transações
            cursor.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (%s, %s, %s, %s, %s)
            ''', (ctx.author.id, ctx.guild.id, 'transfer_out', -amount, f"Transferiu para {user.name}"))

            cursor.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (%s, %s, %s, %s, %s)
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

    user_data = get_user_data(ctx.author.id)
    if not user_data:
        update_user_data(ctx.author.id)
        user_data = get_user_data(ctx.author.id)

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
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = %s, bank = %s WHERE user_id = %s',
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

    user_data = get_user_data(ctx.author.id)
    if not user_data:
        update_user_data(ctx.author.id)
        user_data = get_user_data(ctx.author.id)

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
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = %s, bank = %s WHERE user_id = %s',
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
    user_data = get_user_data(ctx.author.id)
    if not user_data:
        update_user_data(ctx.author.id)
        user_data = get_user_data(ctx.author.id)

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
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Atualizar dinheiro
            new_coins = user_data[1] + ganho_total
            cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (new_coins, ctx.author.id))

            # Atualizar cooldown
            settings['last_work'] = current_time
            cursor.execute('UPDATE users SET settings = %s WHERE user_id = %s', (json.dumps(settings), ctx.author.id))

            # Registrar transação
            cursor.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (%s, %s, %s, %s, %s)
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
            leveled_up, new_level, rank_up, new_rank_id, old_rank_id = add_xp(ctx.author.id, xp_bonus)
            
            # Atualizar cargo se houve rank up
            if rank_up and ctx.guild:
                try:
                    member = ctx.guild.get_member(ctx.author.id)
                    if member:
                        await update_user_rank_role(member, new_rank_id)
                except Exception as e:
                    logger.error(f"Erro ao atualizar cargo após trabalho: {e}")
            await ctx.send(f"🎉 Bônus: +{xp_bonus} XP por trabalhar bem!")

    except Exception as e:
        logger.error(f"Erro no trabalho: {e}")
        embed = create_embed("❌ Erro", "Erro ao trabalhar!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='crime', aliases=['roubar'])
async def crime(ctx):
    """Cometer um crime (risco/recompensa)"""
    user_data = get_user_data(ctx.author.id)
    if not user_data:
        update_user_data(ctx.author.id)
        user_data = get_user_data(ctx.author.id)

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
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            if sucesso:
                # Crime bem-sucedido
                ganho = random.randint(crime["ganho"][0], crime["ganho"][1])
                new_coins = user_data[1] + ganho

                cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (new_coins, ctx.author.id))

                cursor.execute('''
                    INSERT INTO transactions (user_id, guild_id, type, amount, description)
                    VALUES (%s, %s, %s, %s, %s)
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

                cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (new_coins, ctx.author.id))

                cursor.execute('''
                    INSERT INTO transactions (user_id, guild_id, type, amount, description)
                    VALUES (%s, %s, %s, %s, %s)
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
            cursor.execute('UPDATE users SET settings = %s WHERE user_id = %s', (json.dumps(settings), ctx.author.id))

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
    data = get_user_data(user_id)

    if not data:
        update_user_data(user_id)
        data = get_user_data(user_id)

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
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = %s, last_weekly = %s WHERE user_id = %s',
                          (new_coins, week_start_str, user_id))
            conn.commit()
            conn.close()
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
    data = get_user_data(user_id)

    if not data:
        update_user_data(user_id)
        data = get_user_data(user_id)

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
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = %s, last_monthly = %s WHERE user_id = %s',
                          (new_coins, month_start, user_id))
            conn.commit()
            conn.close()
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

@bot.command(name='leaderboard', aliases=['lb'])
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
            cursor.execute('SELECT COUNT(*) FROM users WHERE xp > (SELECT xp FROM users WHERE user_id = %s)', (user_id,))
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

# Modal para criar sorteios
class GiveawayModal(discord.ui.Modal, title="🎁 Criar Sorteio"):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    titulo = discord.ui.TextInput(
        label="🎯 Título do Sorteio",
        placeholder="Ex: iPhone 15, Nitro Discord, 10.000 moedas...",
        required=True,
        max_length=50
    )

    premio = discord.ui.TextInput(
        label="🎁 Prêmio",
        placeholder="Ex: iPhone 15 Pro Max, Discord Nitro 1 mês...",
        required=True,
        max_length=100
    )

    duracao = discord.ui.TextInput(
        label="⏰ Duração",
        placeholder="Ex: 30m, 2h, 1d, 7d",
        required=True,
        max_length=10
    )

    vencedores = discord.ui.TextInput(
        label="🏆 Número de Vencedores",
        placeholder="Ex: 1, 2, 3...",
        required=True,
        max_length=2
    )

    requisitos = discord.ui.TextInput(
        label="📋 Requisitos (Opcional)",
        placeholder="Ex: Seguir o servidor, ter 5+ mensagens...",
        required=False,
        max_length=200,
        style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validar número de vencedores
            try:
                winners_count = int(self.vencedores.value)
                if winners_count < 1 or winners_count > 10:
                    raise ValueError
            except ValueError:
                await interaction.response.send_message("❌ Número de vencedores deve ser entre 1 e 10!", ephemeral=True)
                return

            # Parse duration
            time_units = {'m': 60, 'h': 3600, 'd': 86400}
            duration_str = self.duracao.value.lower()
            unit = duration_str[-1]

            if unit not in time_units:
                await interaction.response.send_message("❌ Duração inválida! Use: m (minutos), h (horas), d (dias)", ephemeral=True)
                return

            try:
                amount = int(duration_str[:-1])
                seconds = amount * time_units[unit]
                end_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
            except ValueError:
                await interaction.response.send_message("❌ Duração inválida! Use números válidos: 30m, 2h, 1d", ephemeral=True)
                return

            # Criar embed do sorteio
            embed = create_embed(
                f"🎁 {self.titulo.value}",
                f"""**🎁 Prêmio:** {self.premio.value}
**🏆 Vencedores:** {winners_count}
**⏰ Termina:** <t:{int(end_time.timestamp())}:R>
**👑 Criado por:** <@{self.user_id}>
**📋 Requisitos:** {self.requisitos.value or "Nenhum requisito especial"}

**🎉 Reaja com 🎉 para participar!**

**⚠️ Boa sorte a todos!**""",
                color=0xffd700
            )

            giveaway_msg = await interaction.response.send_message(embed=embed)
            message = await interaction.original_response()
            await message.add_reaction("🎉")

            # Salvar no banco
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO giveaways (guild_id, channel_id, creator_id, title, prize, winners_count, end_time, message_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (interaction.guild.id, interaction.channel.id, self.user_id, self.titulo.value, self.premio.value, winners_count, end_time, message.id))
                conn.commit()
                conn.close()

            # Confirmar criação
            success_embed = create_embed(
                "✅ Sorteio Criado!",
                f"**{self.titulo.value}** foi criado com sucesso!\n\n"
                f"📋 **Resumo:**\n"
                f"• Prêmio: {self.premio.value}\n"
                f"• Vencedores: {winners_count}\n"
                f"• Duração: {self.duracao.value}\n"
                f"• Requisitos: {self.requisitos.value or 'Nenhum'}\n\n"
                f"🎯 **Criado por:** <@{self.user_id}>",
                color=0x00ff00
            )

            await interaction.followup.send(embed=success_embed, ephemeral=True)
            logger.info(f"Sorteio criado: {self.titulo.value} por {interaction.user}")

        except Exception as e:
            logger.error(f"Erro ao criar sorteio: {e}")
            await interaction.response.send_message("❌ Erro ao criar sorteio! Tente novamente.", ephemeral=True)

# View para criar sorteios com botão
class GiveawayCreateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎁 Criar Sorteio", style=discord.ButtonStyle.primary, emoji="🎁")
    async def create_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verificar permissões
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Apenas administradores podem criar sorteios!", ephemeral=True)
            return

        await interaction.response.send_modal(GiveawayModal(interaction.user.id))

# ============ COMANDOS DE SORTEIO ============
@bot.command(name='criarsorteio', aliases=['giveaway'])
@commands.has_permissions(administrator=True)
async def create_giveaway(ctx, *, giveaway_data=None):
    """[ADMIN] Criar um novo sorteio"""
    if not giveaway_data:
        embed = create_embed(
            "🎁 Sistema de Sorteios Avançado",
            """**🚀 Sistema Moderno com Formulário!**

Clique no botão abaixo para criar um sorteio com formulário interativo!

**✨ Vantagens do novo sistema:**
• 📝 Formulário fácil de preencher
• ✅ Validação automática de dados
• 🎯 Interface moderna e intuitiva
• ⚡ Criação instantânea

**📋 Formato antigo ainda funciona:**
`RXcriarsorteio Título | Prêmio | Duração | Vencedores`

**Exemplo:**
`RXcriarsorteio iPhone 15 | iPhone 15 Pro | 24h | 1`

**⏰ Durações aceitas:** 30m, 2h, 1d, 7d

⬇️ **RECOMENDADO: Use o botão abaixo!**""",
            color=0xffd700
        )

        view = GiveawayCreateView()
        await ctx.send(embed=embed, view=view)
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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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
                WHERE guild_id = %s AND status = 'active'
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
            title, prize, end_time_str, winners_count, participants_json = giveaway  # Ignorar status e created_at
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
async def resultado_teste_tier(ctx, *, resultado=None):
    """[ADMIN] Enviar resultado de teste tier com formulário"""
    if not resultado:
        # Mostrar painel com botão para formulário
        embed = create_embed(
            "📋 Sistema de Resultado Teste Tier",
            f"""**🎯 Modo Moderno com Formulário!**

Clique no botão abaixo para enviar resultado do teste tier usando formulário interativo!

**✨ Vantagens do novo sistema:**
• 📝 Formulário organizado e fácil
• ✅ Campos específicos para resultado e observações  
• ⚡ Envio direto para canal <#{CHANNEL_ID_TESTE_TIER}>
• 💾 Salvo automaticamente

**📋 Formato antigo ainda funciona:**
`RXresultadotier Aprovado - Excelente performance...`

**⚡ Administradores:** Use o botão para melhor experiência!

⬇️ **RECOMENDADO: Use o botão abaixo!**""",
            color=0xffd700
        )

        view = AdminCommandView()
        await ctx.send(embed=embed, view=view)
        return

    # Formato antigo ainda funciona
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
                    VALUES (%s, %s, %s, %s, %s)
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

@bot.command(name='feedbacksstaff', aliases=['avaliacoesstaff'])
@commands.has_permissions(manage_messages=True)
async def ver_feedbacks_staff(ctx):
    """[STAFF] Ver feedbacks de staff"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Buscar feedbacks mais recentes
            cursor.execute('''
                SELECT staff_name, nota_atendimento, nota_qualidade, nota_rapidez, nota_profissionalismo, media_final, comentarios, timestamp, avaliador_id
                FROM staff_feedback
                WHERE guild_id = ?
                ORDER BY timestamp DESC
                LIMIT 15
            ''', (ctx.guild.id,))

            feedbacks = cursor.fetchall()

            # Calcular estatísticas gerais
            cursor.execute('''
                SELECT staff_name, AVG(media_final) as media_geral, COUNT(*) as total_avaliacoes
                FROM staff_feedback
                WHERE guild_id = ?
                GROUP BY staff_name
                ORDER BY media_geral DESC
            ''', (ctx.guild.id,))

            estatisticas = cursor.fetchall()
            conn.close()

        if not feedbacks:
            embed = create_embed(
                "📊 Nenhum Feedback",
                "Ainda não há feedbacks de staff registrados.",
                color=0xffaa00
            )
            await ctx.send(embed=embed)
            return

        # Embed principal
        embed = create_embed(
            "📊 Últimos Feedbacks de Staff",
            f"Mostrando os {len(feedbacks)} feedbacks mais recentes:",
            color=0x7289da
        )

        # Mostrar feedbacks recentes
        for feedback in feedbacks[:5]:
            staff_name, atendimento, qualidade, rapidez, profissionalismo, media, comentarios, timestamp, avaliador_id = feedback

            avaliador = ctx.guild.get_member(avaliador_id)
            avaliador_mention = avaliador.mention if avaliador else f"<@{avaliador_id}> (usuário não encontrado)"

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
                name=f"{emoji} {staff_name} - {media}/10",
                value=f"**Notas:** Atend: {atendimento} | Qual: {qualidade} | Rapid: {rapidez} | Prof: {profissionalismo}\n"
                      f"**Avaliador:** {avaliador_mention}\n"
                      f"**Comentários:** {comentarios[:50]}{'...' if len(comentarios) > 50 else ''}\n"
                      f"*<t:{int(datetime.datetime.fromisoformat(timestamp).timestamp())}:R>*",
                inline=False
            )

        # Estatísticas gerais
        if estatisticas:
            stats_text = ""
            for staff_name, media_geral, total in estatisticas[:5]:
                emoji = "🌟" if media_geral >= 9 else "⭐" if media_geral >= 7 else "⚠️" if media_geral >= 5 else "❌"
                stats_text += f"{emoji} **{staff_name}:** {media_geral:.1f}/10 ({total} avaliações)\n"

            embed.add_field(
                name="📈 Ranking Geral (por média)",
                value=stats_text or "Nenhuma estatística disponível",
                inline=False
            )

        embed.set_footer(text=f"Total de avaliações: {len(feedbacks)} | Use RXmensagemfeedback para criar painel")
        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro ao ver feedbacks de staff: {e}")
        embed = create_embed("❌ Erro", "Erro ao carregar feedbacks!", color=0xff0000)
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
        "🛒 Loja Premium da Kaori",
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
    user_data = get_user_data(ctx.author.id)

    if not user_data:
        update_user_data(ctx.author.id)
        user_data = get_user_data(ctx.author.id)

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
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Remover dinheiro
            new_coins = coins - item['preco']
            cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (new_coins, ctx.author.id))

            # Adicionar ao inventário
            cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (ctx.author.id,))
            inventory_data = cursor.fetchone()[0]
            inventory = json.loads(inventory_data) if inventory_data else {}

            if str(item_id) in inventory:
                inventory[str(item_id)] += 1
            else:
                inventory[str(item_id)] = 1

            cursor.execute('UPDATE users SET inventory = %s WHERE user_id = %s', (json.dumps(inventory), ctx.author.id))

            # Registrar transação
            cursor.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (%s, %s, %s, %s, %s)
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
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Buscar dados do usuário diretamente
            cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (target.id,))
            result = cursor.fetchone()
            conn.close()

        if not result:
            update_user_data(target.id)
            embed = create_embed("📦 Inventário vazio", f"{target.display_name} ainda não tem itens!", color=0xffaa00)
            await ctx.send(embed=embed)
            return

        inventory_data = result[0]
        inventory = json.loads(inventory_data) if inventory_data else {}

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

    try:
        # Buscar inventário do remetente diretamente do banco
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Verificar se remetente existe
            cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (ctx.author.id,))
            sender_result = cursor.fetchone()

            if not sender_result:
                conn.close()
                embed = create_embed("❌ Sem dados", "Você não tem dados no sistema!", color=0xff0000)
                await ctx.send(embed=embed)
                return

            sender_inventory_data = sender_result[0]
            sender_inventory = json.loads(sender_inventory_data) if sender_inventory_data else {}

            # Verificar se tem o item
            if str(item_id) not in sender_inventory or sender_inventory[str(item_id)] < quantidade:
                item_name = LOJA_ITENS[item_id]['nome']
                conn.close()
                embed = create_embed(
                    "❌ Item insuficiente",
                    f"Você não tem {quantidade}x **{item_name}** suficientes!\n"
                    f"Você tem apenas: {sender_inventory.get(str(item_id), 0)}",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return

            # Verificar/criar receptor
            cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (user.id,))
            receiver_result = cursor.fetchone()

            if not receiver_result:
                # Criar dados do receptor
                cursor.execute('INSERT INTO users (user_id) VALUES (%s)', (user.id,))
                receiver_inventory = {}
            else:
                receiver_inventory_data = receiver_result[0]
                receiver_inventory = json.loads(receiver_inventory_data) if receiver_inventory_data else {}

            item = LOJA_ITENS[item_id]

            # Processar transferência
            sender_inventory[str(item_id)] -= quantidade
            if sender_inventory[str(item_id)] <= 0:
                del sender_inventory[str(item_id)]

            if str(item_id) in receiver_inventory:
                receiver_inventory[str(item_id)] += quantidade
            else:
                receiver_inventory[str(item_id)] = quantidade

            # Atualizar banco de dados
            cursor.execute('UPDATE users SET inventory = %s WHERE user_id = %s',
                          (json.dumps(sender_inventory), ctx.author.id))
            cursor.execute('UPDATE users SET inventory = %s WHERE user_id = %s',
                          (json.dumps(receiver_inventory), user.id))

            # Registrar transações
            cursor.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (%s, %s, %s, %s, %s)
            ''', (ctx.author.id, ctx.guild.id, 'item_given', 0, f"Deu {quantidade}x {item['nome']} para {user.name}"))

            cursor.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (%s, %s, %s, %s, %s)
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
        embed = create_embed("❌ Erro", f"Erro ao transferir item: {str(e)[:100]}", color=0xff0000)
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
    sender_data = get_user_data(ctx.author.id)
    receiver_data = get_user_data(user.id)

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
    active_games[trade_msg.id] = {
        'type': 'trade_invitation',
        'initiator': ctx.author.id,
        'target': user.id,
        'channel': ctx.channel.id,
        'step': 'invitation'
    }

@bot.command(name='efeitos', aliases=['buffs', 'effects'])
async def ver_efeitos(ctx, user: discord.Member = None):
    """Ver buffs e efeitos ativos do usuário"""
    target = user or ctx.author
    user_data = get_user_data(target.id)

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
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (ctx.author.id,))
            result = cursor.fetchone()
            conn.close()
    except Exception as e:
        logger.error(f"Erro ao buscar inventário: {e}")
        embed = create_embed("❌ Erro", "Erro ao acessar inventário!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if not result:
        embed = create_embed("❌ Dados não encontrados", "Você não tem dados de usuário!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    inventory_data = result[0]
    inventory = json.loads(inventory_data) if inventory_data else {}

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
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Buscar dados atuais
            cursor.execute('SELECT settings, coins, xp FROM users WHERE user_id = %s', (ctx.author.id,))
            user_info = cursor.fetchone()
            settings_data, current_coins, current_xp = user_info[0], user_info[1], user_info[2]
            settings = json.loads(settings_data) if settings_data else {}

            resultado = ""
            coins_gained = 0  # Para tracking automático

            # ITEM 1: Desafio do Dia
            if item_id == 1:
                # Simular mini-game (pedra/papel/tesoura automático)
                resultado_jogo = random.choice(['vitoria', 'derrota', 'empate'])
                if resultado_jogo == 'vitoria':
                    premio = random.randint(200, 500)
                    coins_gained = premio
                    cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (current_coins + premio, ctx.author.id))
                    resultado = f"🎉 **VITÓRIA!** Você ganhou {premio:,} moedas! ✅ **Automaticamente adicionadas ao seu saldo!**"
                elif resultado_jogo == 'empate':
                    resultado = "😐 **EMPATE!** Nada aconteceu."
                else:
                    perda = random.randint(50, 150)
                    perda = min(perda, current_coins)
                    cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (current_coins - perda, ctx.author.id))
                    resultado = f"😢 **DERROTA!** Você perdeu {perda:,} moedas."

            # ITEM 2: Caixa Misteriosa
            elif item_id == 2:
                sorte = random.randint(1, 100)
                if sorte <= 5:  # 5% - Muito raro
                    premio_coins = random.randint(2000, 5000)
                    premio_xp = random.randint(100, 200)
                    coins_gained = premio_coins
                    cursor.execute('UPDATE users SET coins = %s, xp = %s WHERE user_id = %s', (current_coins + premio_coins, current_xp + premio_xp, ctx.author.id))
                    resultado = f"🌟 **JACKPOT!** {premio_coins:,} moedas + {premio_xp} XP! ✅ **Automaticamente adicionados!**"
                elif sorte <= 25:  # 20% - Bom
                    premio_coins = random.randint(500, 1500)
                    coins_gained = premio_coins
                    cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (current_coins + premio_coins, ctx.author.id))
                    resultado = f"💰 **SORTE!** Você ganhou {premio_coins:,} moedas! ✅ **Automaticamente adicionadas!**"
                elif sorte <= 50:  # 25% - Regular
                    premio_xp = random.randint(50, 100)
                    cursor.execute('UPDATE users SET xp = %s WHERE user_id = %s', (current_xp + premio_xp, ctx.author.id))
                    resultado = f"⭐ **XP!** Você ganhou {premio_xp} pontos de experiência! ✅ **Automaticamente adicionados!**"
                elif sorte <= 80:  # 30% - Pequeno
                    premio_coins = random.randint(100, 300)
                    coins_gained = premio_coins
                    cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (current_coins + premio_coins, ctx.author.id))
                    resultado = f"🪙 **Algo!** {premio_coins:,} moedas encontradas! ✅ **Automaticamente adicionadas!**"
                else:  # 20% - Nada
                    resultado = "📦 **VAZIA!** A caixa estava vazia... que azar!"

            # ITEM 3: Ticket Prioritário
            elif item_id == 3:
                settings['priority_tickets'] = settings.get('priority_tickets', 0) + 1
                cursor.execute('UPDATE users SET settings = %s WHERE user_id = %s', (json.dumps(settings), ctx.author.id))
                resultado = "🎫 **PRIORIDADE ATIVADA!** Seu próximo ticket terá atendimento prioritário! ✅ **Efeito aplicado automaticamente!**"

            # ITEM 4: Explosão de Moedas
            elif item_id == 4:
                # Criar evento de chuva de moedas usando botões em vez de reações
                moedas_total = random.randint(800, 1500)

                class CoinRainView(discord.ui.View):
                    def __init__(self):
                        super().__init__(timeout=60)
                        self.participants = []
                        self.max_participants = 3
                        self.total_coins = moedas_total

                    @discord.ui.button(label="💰 PEGAR MOEDAS!", style=discord.ButtonStyle.success, emoji="💰")
                    async def grab_coins(self, interaction: discord.Interaction, button: discord.ui.Button):
                        if interaction.user.id not in self.participants and len(self.participants) < self.max_participants:
                            self.participants.append(interaction.user.id)

                            if len(self.participants) >= self.max_participants:
                                # Distribuir moedas automaticamente
                                coins_per_user = self.total_coins // self.max_participants
                                winners = []

                                with db_lock:
                                    conn = get_db_connection()
                                    cursor = conn.cursor()

                                    for participant_id in self.participants:
                                        user_data = get_user_data(participant_id)
                                        if user_data:
                                            new_coins = user_data[1] + coins_per_user
                                            cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (new_coins, participant_id))
                                            participant = bot.get_user(participant_id)
                                            if participant:
                                                winners.append(participant.mention)

                                    conn.commit()
                                    conn.close()

                                embed = create_embed(
                                    "💰 Explosão de Moedas Finalizada!",
                                    f"🎉 **Vencedores:**\n{', '.join(winners)}\n\n"
                                    f"💰 **Prêmio individual:** {coins_per_user:,} moedas\n"
                                    f"🏆 **Total distribuído:** {self.total_coins:,} moedas\n\n"
                                    f"✅ **Moedas automaticamente adicionadas aos saldos!**",
                                    color=0xffd700
                                )
                                await interaction.response.edit_message(embed=embed, view=None)
                            else:
                                await interaction.response.send_message(f"💰 Você entrou na disputa! Posição: {len(self.participants)}/{self.max_participants}", ephemeral=True)
                        else:
                            await interaction.response.send_message("❌ Você já está participando ou a disputa já acabou!", ephemeral=True)

                embed_chuva = create_embed(
                    "🧨 EXPLOSÃO DE MOEDAS!",
                    f"💰 **{ctx.author.mention} ativou uma Explosão de Moedas!**\n\n"
                    f"🪙 **{moedas_total:,} moedas** estão caindo do céu!\n"
                    f"⚡ **Os 3 primeiros a clicar no botão ganham parte das moedas!**\n\n"
                    f"🏃‍♂️ **CORRA!** Seja rápido e clique no botão abaixo!",
                    color=0xffd700
                )

                view = CoinRainView()
                await ctx.send(embed=embed_chuva, view=view)
                resultado = f"🧨 **EXPLOSÃO ATIVADA!** Chuva de {moedas_total:,} moedas liberada no chat com botão!"

            # ITEM 5: Boost de XP (1h)
            elif item_id == 5:
                boost_end = datetime.datetime.now() + datetime.timedelta(hours=1)
                settings['xp_boost'] = boost_end.timestamp()
                cursor.execute('UPDATE users SET settings = %s WHERE user_id = %s', (json.dumps(settings), ctx.author.id))
                resultado = f"📈 **BOOST ATIVO!** XP dobrado por 1 hora! (até <t:{int(boost_end.timestamp())}:t>) ✅ **Efeito aplicado automaticamente!**"

            # ITEM 6: Título Personalizado
            elif item_id == 6:
                settings['custom_title_available'] = True
                cursor.execute('UPDATE users SET settings = %s WHERE user_id = %s', (json.dumps(settings), ctx.author.id))
                resultado = f"👑 **TÍTULO DESBLOQUEADO!** Use `RXsettitle <título>` para definir seu título personalizado! ✅ **Permissão adicionada automaticamente!**"

            # ITEM 7: Salário VIP (7 dias)
            elif item_id == 7:
                vip_end = datetime.datetime.now() + datetime.timedelta(days=7)
                settings['vip_salary'] = vip_end.timestamp()
                cursor.execute('UPDATE users SET settings = %s WHERE user_id = %s', (json.dumps(settings), ctx.author.id))
                resultado = f"💼 **SALÁRIO VIP ATIVO!** +50% em trabalhos por 7 dias! (até <t:{int(vip_end.timestamp())}:d>) ✅ **Efeito aplicado automaticamente!**"

            # ITEM 8: Cargo Exclusivo (3 dias)
            elif item_id == 8:
                exclusive_end = datetime.datetime.now() + datetime.timedelta(days=3)
                settings['exclusive_role'] = exclusive_end.timestamp()
                cursor.execute('UPDATE users SET settings = %s WHERE user_id = %s', (json.dumps(settings), ctx.author.id))

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
                    resultado = f"🛡️ **CARGO EXCLUSIVO ATIVO!** Você recebeu o cargo {special_role.mention} por 3 dias! ✅ **Cargo aplicado automaticamente!**"
                except:
                    resultado = f"🛡️ **CARGO EXCLUSIVO ATIVO!** Privilégios especiais por 3 dias! ✅ **Efeito aplicado automaticamente!**"

            # ITEM 9: RX Medalha Épica
            elif item_id == 9:
                settings['epic_medals'] = settings.get('epic_medals', 0) + 1
                settings['collection_power'] = settings.get('collection_power', 0) + 10
                cursor.execute('UPDATE users SET settings = %s WHERE user_id = %s', (json.dumps(settings), ctx.author.id))
                resultado = f"🌌 **MEDALHA ÉPICA COLETADA!** Adicionada à sua coleção! Poder de Coleção: +10 (Total: {settings['collection_power']}) ✅ **Automaticamente adicionada ao inventário de coleções!**"

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
                        cursor.execute('UPDATE users SET settings = %s WHERE user_id = %s', (json.dumps(settings), ctx.author.id))
                        resultado = f"🧬 **DNA RX ABSORVIDO!** +25 Pontos de Evolução + Habilidade Especial: **{new_ability.replace('_', ' ').title()}**! ✅ **Automaticamente aplicado!**"
                    else:
                        cursor.execute('UPDATE users SET settings = %s WHERE user_id = %s', (json.dumps(settings), ctx.author.id))
                        resultado = f"🧬 **DNA RX ABSORVIDO!** +25 Pontos de Evolução! (Total: {settings['evolution_points']}) ✅ **Automaticamente aplicado!**"
                else:
                    cursor.execute('UPDATE users SET settings = %s WHERE user_id = %s', (json.dumps(settings), ctx.author.id))
                    resultado = f"🧬 **DNA RX ABSORVIDO!** +25 Pontos de Evolução! (Total: {settings['evolution_points']}) ✅ **Automaticamente aplicado!**"

            # Registrar transação se ganhou coins
            if coins_gained > 0:
                cursor.execute('''
                    INSERT INTO transactions (user_id, guild_id, type, amount, description)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (ctx.author.id, ctx.guild.id, 'item_reward', coins_gained, f"Recompensa do item {item['nome']}"))

            # Remover item do inventário APÓS aplicar efeito
            inventory[str(item_id)] -= 1
            if inventory[str(item_id)] <= 0:
                del inventory[str(item_id)]

            cursor.execute('UPDATE users SET inventory = %s WHERE user_id = %s', (json.dumps(inventory), ctx.author.id))

            conn.commit()
            conn.close()

        embed = create_embed(
            f"✅ {item['emoji']} {item['nome']} Usado!",
            f"**Efeito aplicado:**\n{resultado}\n\n"
            f"**Descrição:** {item['descricao']}\n\n"
            f"💡 **Sistema Automático:** Todas as recompensas são aplicadas automaticamente!",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

        # Log do uso
        logger.info(f"Item usado: {ctx.author.name} usou {item['nome']} (ID: {item_id}) - Coins ganhos: {coins_gained}")

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

    user_data = get_user_data(ctx.author.id)
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
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            settings['custom_title'] = titulo
            settings['custom_title_available'] = False  # Consumir o uso

            cursor.execute('UPDATE users SET settings = %s WHERE user_id = %s', (json.dumps(settings), ctx.author.id))
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
    """Gerar QR Code (placeholder)"""
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
        user_data = get_user_data(user.id)
        if not user_data:
            update_user_data(user.id)
            current_warns = 0
        else:
            current_warns = user_data[15] if user_data and len(user_data) > 15 else 0

        new_warns = current_warns + 1

        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Atualizar warns
            cursor.execute('UPDATE users SET warnings = %s WHERE user_id = %s', (new_warns, user.id))

            # Registrar no log de moderação
            cursor.execute('''
                INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason)
                VALUES (%s, %s, %s, %s, %s)
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
        user_data = get_user_data(target.id)
        if not user_data:
            warns = 0
        else:
            warns = user_data[15] if user_data and len(user_data) > 15 else 0

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
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (ctx.guild.id, member.id, ctx.author.id, 'kick', reason))
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Erro ao salvar log de moderação: {e}")

    except Exception as e:
        logger.error(f"Erro ao expulsar membro: {e}")
        embed = create_embed("❌ Erro", f"Erro ao expulsar membro: {str(e)[:100]}", color=0xff0000)
        await ctx.send(embed=embed)

# ============ COMANDOS DE ADMINISTRAÇÃO AVANÇADOS ============
@bot.command(name='addsaldo', aliases=['addcoins', 'addmoney'])
async def add_saldo(ctx, user: discord.Member, amount: int):
    """[ADMIN] Adicionar saldo a um usuário - Restrito"""
    # Verificar se é um dos usuários autorizados
    authorized_users = [1339336477661724674, 784828686099677204]

    if ctx.author.id not in authorized_users:
        embed = create_embed(
            "❌ Acesso Negado",
            "Apenas usuários autorizados podem usar este comando!",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    if amount <= 0:
        embed = create_embed("❌ Valor inválido", "Use valores positivos!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        user_data = get_user_data(user.id)
        if not user_data:
            update_user_data(user.id)
            current_coins = 50
        else:
            current_coins = user_data[1]

        new_coins = current_coins + amount

        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (new_coins, user.id))

            # Registrar transação
            cursor.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (%s, %s, %s, %s, %s)
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
async def remove_saldo(ctx, user: discord.Member, amount: int):
    """[ADMIN] Remover saldo de um usuário - Restrito"""
    # Verificar se é um dos usuários autorizados
    authorized_users = [1339336477661724674, 784828686099677204]

    if ctx.author.id not in authorized_users:
        embed = create_embed(
            "❌ Acesso Negado",
            "Apenas usuários autorizados podem usar este comando!",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    if amount <= 0:
        embed = create_embed("❌ Valor inválido", "Use valores positivos!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        user_data = get_user_data(user.id)
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

        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET coins = %s WHERE user_id = %s', (new_coins, user.id))

            # Registrar transação
            cursor.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (%s, %s, %s, %s, %s)
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

# Modal para eventos personalizados de treino
class TreinoEventModal(discord.ui.Modal, title="🎯 Criar Evento de Treino"):
    def __init__(self, event_type, user_id):
        super().__init__()
        self.event_type = event_type
        self.user_id = user_id

    titulo = discord.ui.TextInput(
        label="📋 Título do Evento",
        placeholder="Ex: Treino de Block Dash, Treino Geral, etc.",
        required=True,
        max_length=50
    )

    data = discord.ui.TextInput(
        label="📅 Data",
        placeholder="Ex: hoje, amanhã, 15/01, sábado...",
        required=True,
        max_length=20
    )

    horario = discord.ui.TextInput(
        label="⏰ Horário",
        placeholder="Ex: 20:00, 14:30, 19h...",
        required=True,
        max_length=10
    )

    detalhes = discord.ui.TextInput(
        label="📝 Detalhes (Opcional)",
        placeholder="Informações extras, mapas específicos, etc.",
        required=False,
        max_length=200,
        style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Criar embed do evento
            embed = create_embed(
                f"🎯 {self.titulo.value}",
                f"""**📅 Data:** {self.data.value}
**⏰ Horário:** {self.horario.value}
**👥 Tipo:** {self.event_type}
**🎮 Detalhes:** {self.detalhes.value or "Treino padrão"}

**📋 Participação:**
✅ - Posso ir / Confirmo presença
❌ - Não posso ir / Não confirmo
❓ - Talvez / Não tenho certeza

**👑 Criado por:** <@{self.user_id}>

**Reaja abaixo para confirmar sua participação!**""",
                color=0x00ff00
            )

            # Resposta de confirmação
            success_embed = create_embed(
                "✅ Evento de Treino Criado!",
                f"**{self.titulo.value}** foi criado com sucesso!\n\n"
                f"📋 **Resumo:**\n"
                f"• Data: {self.data.value}\n"
                f"• Horário: {self.horario.value}\n"
                f"• Tipo: {self.event_type}\n\n"
                f"🎯 **Criado por:** <@{self.user_id}>\n\n"
                f"📨 **O evento foi publicado em <#1398027576894816415>!**",
                color=0x00ff00
            )

            await interaction.response.send_message(embed=success_embed, ephemeral=True)

            # Publicar evento no canal específico
            target_channel = interaction.guild.get_channel(1398027576894816415)
            if target_channel:
                event_msg = await target_channel.send(embed=embed)
            else:
                # Fallback para o canal atual se não encontrar o canal específico
                event_msg = await safe_send_response(interaction, embed=embed)

            # Adicionar reações
            await event_msg.add_reaction("✅")
            await event_msg.add_reaction("❌")
            await event_msg.add_reaction("❓")

            # Salvar no banco de dados
            try:
                end_time = datetime.datetime.now() + datetime.timedelta(days=7)  # Evento por 7 dias

                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()

                    cursor.execute('''
                        INSERT INTO clan_events (guild_id, creator_id, clan1, event_type, end_time, message_id, participants, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        interaction.guild.id, 
                        self.user_id, 
                        self.titulo.value,
                        f"{self.event_type} - {self.data.value} {self.horario.value}", 
                        end_time,
                        event_msg.id,
                        "[]",
                        'active'
                    ))

                    conn.commit()
                    conn.close()
            except Exception as e:
                logger.error(f"Erro ao salvar evento de treino: {e}")

            logger.info(f"Evento de treino criado: {self.titulo.value} por {interaction.user}")

        except Exception as e:
            logger.error(f"Erro ao criar evento de treino: {e}")
            await interaction.response.send_message("❌ Erro ao criar evento! Tente novamente.", ephemeral=True)

# View principal com botão para criar eventos XClan
class XClanMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Sem timeout - botão permanente

    @discord.ui.button(label="🚨 CRIAR XCLAN VS! 🚨", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def create_xclan_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Qualquer pessoa pode clicar e criar seu evento
        await interaction.response.send_modal(XClanModal(interaction.user.id))

# Modal para criar evento XClan completo
class XClanModal(discord.ui.Modal, title="🚨 CRIAR EVENTO XCLAN VS! 🚨"):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    clan_input = discord.ui.TextInput(
        label="🏆 Nome do Clan Adversário",
        placeholder="Ex: WLX, TOP, PRO, ELITE, KING...",
        required=True,
        max_length=20
    )

    mapa_input = discord.ui.TextInput(
        label="🗺️ Mapa do Stumble Guys",
        placeholder="Ex: Block Dash, Water Race, Lava Land...",
        required=True,
        max_length=30
    )

    md_input = discord.ui.TextInput(
        label="🎯 MD (Melhor de quantas)",
        placeholder="Ex: 1, 3, 5, 7",
        required=True,
        max_length=2
    )

    jogadores_input = discord.ui.TextInput(
        label="👥 Quantos jogadores (1v1, 2v2, etc)",
        placeholder="Ex: 1, 2, 3, 4, 5, 6",
        required=True,
        max_length=2
    )

    detalhes_input = discord.ui.TextInput(
        label="📅 Data, Horário e Emotes",
        placeholder="Ex: 15/01/2025 às 20:00 🏃💨🔥⚡",
        required=True,
        max_length=100,
        style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validar MD
            try:
                md_num = int(self.md_input.value)
                if md_num not in [1, 3, 5, 7]:
                    raise ValueError
            except ValueError:
                await interaction.response.send_message("❌ MD deve ser: 1, 3, 5 ou 7", ephemeral=True)
                return

            # Validar jogadores
            try:
                jogadores_num = int(self.jogadores_input.value)
                if jogadores_num not in [1, 2, 3, 4, 5, 6]:
                    raise ValueError
            except ValueError:
                await interaction.response.send_message("❌ Jogadores deve ser: 1, 2, 3, 4, 5 ou 6", ephemeral=True)
                return

            # Criar embed do evento
            embed = create_embed(
                "🚨 MODELO DE VS! 🚨",
                f"""**Nome do Cla/Line:** {self.clan_input.value}
**Mapa(s):** {self.mapa_input.value}
**MD:** MD{self.md_input.value}
**Quantos jogadores?** {self.jogadores_input.value}v{self.jogadores_input.value}
**Detalhes:** {self.detalhes_input.value}

**PING:** ||@everyone||

👨‍🎤**Marque:** <@&1400167903126356120>

**🎯 Criado por:** <@{self.user_id}>

||@everyone // @here||""",
                color=0xff0000
            )

            # Salvar no banco de dados
            try:
                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()

                    cursor.execute('''
                        INSERT INTO clan_events (guild_id, creator_id, clan1, clan2, event_type, end_time, message_id, participants, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        interaction.guild.id, 
                        self.user_id, 
                        "RX", 
                        self.clan_input.value, 
                        f"VS - {self.mapa_input.value}", 
                        datetime.datetime.now() + datetime.timedelta(days=1),  # Evento por 24h
                        0,  # Será atualizado depois
                        "[]",  # Lista de participantes
                        'active'
                    ))

                    event_id = cursor.lastrowid
                    conn.commit()
                    conn.close()
            except Exception as e:
                logger.error(f"Erro ao salvar evento XClan: {e}")

            # Resposta de sucesso
            success_embed = create_embed(
                "✅ Evento XClan Criado!",
                f"**RX vs {self.clan_input.value}** foi criado com sucesso!\n\n"
                f"📋 **Resumo:**\n"
                f"• Mapa: {self.mapa_input.value}\n"
                f"• MD: MD{self.md_input.value}\n"
                f"• Jogadores: {self.jogadores_input.value}v{self.jogadores_input.value}\n"
                f"• Detalhes: {self.detalhes_input.value}\n\n"
                f"🎯 **Criado por:** <@{self.user_id}>\n\n"
                f"📨 **O evento foi publicado no canal!**",
                color=0x00ff00
            )

            await interaction.response.send_message(embed=success_embed, ephemeral=True)

            # Publicar evento no canal
            await safe_send_response(interaction, embed=embed)

            # Notificar no canal específico
            try:
                notification_channel = interaction.guild.get_channel(1400166850045673482)
                if notification_channel:
                    notify_embed = create_embed(
                        "🚨 NOVO EVENTO XCLAN CRIADO! 🚨",
                        f"""**📢 Um novo evento XClan foi criado!**

**⚔️ Batalha:** RX vs {self.clan_input.value}
**🗺️ Mapa:** {self.mapa_input.value}
**🎯 MD:** MD{self.md_input.value}
**👥 Jogadores:** {self.jogadores_input.value}v{self.jogadores_input.value}
**📅 Detalhes:** {self.detalhes_input.value}

**👑 Criado por:** <@{self.user_id}>
**📍 Evento publicado no canal principal**

@everyone""",
                        color=0xff0000
                    )
                    await notification_channel.send(embed=notify_embed)
            except Exception as e:
                logger.error(f"Erro ao notificar canal específico: {e}")

            logger.info(f"Evento XClan criado: RX vs {self.clan_input.value} - criado por {interaction.user}")

        except Exception as e:
            logger.error(f"Erro ao criar evento XClan: {e}")
            await interaction.response.send_message("❌ Erro ao criar evento! Tente novamente.", ephemeral=True)

# Modal para data e horário
class DateTimeModal(discord.ui.Modal, title="📅 Data e Horário do Evento"):
    def __init__(self, view, user):
        super().__init__()
        self.view = view
        self.user = user

    date_input = discord.ui.TextInput(
        label="Data e Horário",
        placeholder="Ex: 15/01/2025 às 20:00",
        required=True,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        self.view.event_data['data'] = self.date_input.value
        await self.view.update_embed_response(interaction, f"✅ Data definida: **{self.date_input.value}** por {self.user.mention}")

# Modal para emotes
class EmotesModal(discord.ui.Modal, title="😎 Emotes do Stumble Guys"):
    def __init__(self, view, user):
        super().__init__()
        self.view = view
        self.user = user

    emotes_input = discord.ui.TextInput(
        label="Emotes",
        placeholder="Ex: 🏃💨🔥⚡🌊❄️",
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        self.view.event_data['emotes'] = self.emotes_input.value
        await self.view.update_embed_response(interaction, f"✅ Emotes definidos: **{self.emotes_input.value}** por {self.user.mention}")

@bot.command(name='mensagemxclan', aliases=['xclan', 'eventoxclan'])
@commands.has_permissions(manage_messages=True)
async def mensagem_xclan(ctx):
    """[STAFF] Criar painel XClan - qualquer pessoa pode criar eventos"""

    embed = create_embed(
        "🚨 PAINEL DE EVENTOS XCLAN VS! 🚨",
        f"""**⚔️ Sistema de Batalhas RX vs Outros Clans**

**🎮 Como funciona:**
1️⃣ **Qualquer pessoa** clica no botão abaixo
2️⃣ Preenche o formulário completo
3️⃣ O evento é criado automaticamente
4️⃣ Várias pessoas podem criar eventos diferentes

**📋 Informações necessárias:**
• 🏆 **Clan Adversário** (WLX, TOP, PRO, etc.)
• 🗺️ **Mapa** (Block Dash, Water Race, etc.)
• 🎯 **MD** (1, 3, 5 ou 7)
• 👥 **Jogadores** (1v1 até 6v6)
• 📅 **Data, horário e emotes**

**✨ Vantagens:**
• ⚡ Criação instantânea
• 🔄 Múltiplos eventos por pessoa
• 📨 Publicação automática com ping @everyone
• 💾 Salvo no banco de dados

**👑 Painel criado por:** {ctx.author.mention}
**🎯 Use `RXresultadoxclan` para enviar resultados**

⬇️ **CLIQUE NO BOTÃO PARA CRIAR SEU EVENTO:**""",
        color=0xff0000
    )

    view = XClanMainView()
    await ctx.send(embed=embed, view=view)

@bot.command(name='criar', aliases=['createevent', 'event'])
@commands.has_permissions(manage_messages=True)
async def criar_evento_personalizado(ctx, tipo=None, *, dados=None):
    """[STAFF] Criar eventos personalizados com reações"""

    if not tipo:
        embed = create_embed(
            "🎯 Sistema de Eventos Personalizados",
            """**📋 Comandos disponíveis:**

**🏃 Treinos:**
• `RXcriar xtreino` - Criar evento de treino
• `RXcriar treino` - Criar treino geral
• `RXcriar practice` - Criar prática

**⚔️ Competições:**
• `RXcriar torneio` - Criar torneio
• `RXcriar championship` - Criar campeonato
• `RXcriar battle` - Criar batalha

**🎮 Eventos Gerais:**
• `RXcriar evento` - Criar evento geral
• `RXcriar meeting` - Criar reunião
• `RXcriar party` - Criar festa/evento social

**📋 Formato rápido:**
`RXcriar xtreino Treino Block Dash | hoje | 20:00`

**🎯 Todos os eventos:**
• Têm reações ✅❌❓ automáticas
• São salvos no banco de dados
• Podem ser criados por qualquer staff
• Ficam ativos por 7 dias""",
            color=0x7289da
        )
        await ctx.send(embed=embed)
        return

    # Tipos de eventos aceitos
    tipos_aceitos = {
        'xtreino': 'XTreino',
        'treino': 'Treino',
        'practice': 'Prática',
        'torneio': 'Torneio', 
        'tournament': 'Torneio',
        'championship': 'Campeonato',
        'battle': 'Batalha',
        'evento': 'Evento',
        'meeting': 'Reunião',
        'party': 'Festa'
    }

    tipo_lower = tipo.lower()
    if tipo_lower not in tipos_aceitos:
        embed = create_embed(
            "❌ Tipo inválido",
            f"Tipos aceitos: {', '.join(tipos_aceitos.keys())}\nUse `RXcriar` para ver todos os tipos.",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

    event_type = tipos_aceitos[tipo_lower]

    # Se dados foram fornecidos, criar formato rápido
    if dados:
        parts = [part.strip() for part in dados.split('|')]
        if len(parts) >= 3:
            titulo, data, horario = parts[0], parts[1], parts[2]
            detalhes = parts[3] if len(parts) > 3 else ""

            # Criar evento diretamente
            embed = create_embed(
                f"🎯 {titulo}",
                f"""**📅 Data:** {data}
**⏰ Horário:** {horario}
**👥 Tipo:** {event_type}
**🎮 Detalhes:** {detalhes or "Evento padrão"}

**📋 Participação:**
✅ - Posso ir / Confirmo presença
❌ - Não posso ir / Não confirmo
❓ - Talvez / Não tenho certeza

**👑 Criado por:** {ctx.author.mention}

**Reaja abaixo para confirmar sua participação!**""",
                color=0x00ff00
            )

            # Publicar evento no canal específico
            target_channel = ctx.guild.get_channel(1398027576894816415)
            if target_channel:
                event_msg = await target_channel.send(embed=embed)
            else:
                # Fallback para o canal atual se não encontrar o canal específico
                event_msg = await ctx.send(embed=embed)

            # Adicionar reações
            await event_msg.add_reaction("✅")
            await event_msg.add_reaction("❌")
            await event_msg.add_reaction("❓")

            # Salvar no banco
            try:
                end_time = datetime.datetime.now() + datetime.timedelta(days=7)

                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()

                    cursor.execute('''
                        INSERT INTO clan_events (guild_id, creator_id, clan1, event_type, end_time, message_id, participants, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        ctx.guild.id, 
                        ctx.author.id, 
                        titulo,
                        f"{event_type} - {data} {horario}", 
                        end_time,
                        event_msg.id,
                        "[]",
                        'active'
                    ))

                    conn.commit()
                    conn.close()
            except Exception as e:
                logger.error(f"Erro ao salvar evento rápido: {e}")

            # Confirmar criação
            confirm_embed = create_embed(
                "✅ Evento Criado!",
                f"**{titulo}** foi criado com sucesso!\nTipo: {event_type} | Data: {data} | Horário: {horario}\n\n**📨 Evento publicado em <#1398027576894816415>**",
                color=0x00ff00
            )
            await ctx.send(embed=confirm_embed, delete_after=10)

            logger.info(f"Evento rápido criado: {titulo} por {ctx.author}")
            return

    # Abrir modal para criar evento detalhado
    await ctx.send("📝 Abrindo formulário de criação de evento...")

    # Como não podemos enviar modal diretamente em command, vamos usar uma view
    view = CreateEventView(event_type, ctx.author.id)
    embed = create_embed(
        f"🎯 Criar {event_type}",
        f"Clique no botão abaixo para abrir o formulário de criação de **{event_type}**:",
        color=0x7289da
    )

    await ctx.send(embed=embed, view=view)

# View para criar eventos personalizados
class CreateEventView(discord.ui.View):
    def __init__(self, event_type, user_id):
        super().__init__(timeout=300)  # 5 minutos
        self.event_type = event_type
        self.user_id = user_id

    @discord.ui.button(label="📝 Criar Evento", style=discord.ButtonStyle.primary, emoji="🎯")
    async def create_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Apenas quem criou pode usar este botão!", ephemeral=True)
            return

        await interaction.response.send_modal(TreinoEventModal(self.event_type, self.user_id))

@bot.command(name='resultadoxclan', aliases=['resultxclan'])
@commands.has_permissions(manage_messages=True)
async def resultado_xclan(ctx, *, resultado=None):
    """[MOD] Enviar resultado do evento XClan com formulário"""

    if not resultado:
        # Mostrar painel com botão para formulário
        embed = create_embed(
            "🏆 Sistema de Resultado XClan VS",
            f"""**⚔️ Modo Moderno com Formulário!**

Clique no botão abaixo para enviar resultado XClan usando formulário interativo!

**✨ Vantagens do novo sistema:**
• 📝 Formulário organizado para resultados
• ⚡ Envio direto para canal <#1400167040504823869>
• 🎯 Formato padronizado automático
• 💾 Registro automático no sistema

**📋 Formato antigo ainda funciona:**
```
RXresultadoxclan ## 🏆 RX vs WLX
RX 11 ✖ 0 WLX
Obs: WO
```

**🛡️ Moderadores:** Use o botão para melhor experiência!

⬇️ **RECOMENDADO: Use o botão abaixo!**""",
            color=0xff0000
        )

        view = AdminCommandView()
        await ctx.send(embed=embed, view=view)
        return

    # Formato antigo ainda funciona
    try:
        # Canal específico para resultados
        result_channel = bot.get_channel(1400167040504823869)
        if not result_channel:
            embed = create_embed("❌ Erro", "Canal de resultados não encontrado!", color=0xff0000)
            await ctx.send(embed=embed)
            return

        # Criar embed do resultado
        embed = create_embed(
            "🏆 RESULTADO XCLAN VS",
            f"""{resultado}

**📊 Resultado enviado por:** {ctx.author.mention}
**⏰ Data:** <t:{int(datetime.datetime.now().timestamp())}:F>""",
            color=0xffd700
        )

        await result_channel.send(embed=embed)

        # Confirmar envio
        confirm_embed = create_embed(
            "✅ Resultado Enviado!",
            f"Resultado do evento XClan foi enviado para {result_channel.mention}",
            color=0x00ff00
        )
        await ctx.send(embed=confirm_embed, delete_after=10)

        logger.info(f"Resultado XClan enviado por {ctx.author}: {resultado[:50]}...")

    except Exception as e:
        logger.error(f"Erro ao enviar resultado XClan: {e}")
        embed = create_embed("❌ Erro", "Erro ao enviar resultado!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='criareventoclan', aliases=['createclanevent'])
@commands.has_permissions(administrator=True)
async def criar_evento_clan(ctx, *, dados_evento=None):
    """[ADMIN] Criar evento de batalha entre clans no Stumble Guys"""
    if not dados_evento:
        embed = create_embed(
            "🎮 Como criar evento de clan - Stumble Guys",
            """**Formato:** `XCLAN | duração`

**Exemplo:**
`RXcriareventoclan XCLAN | 2h`

**Mapas disponíveis do Stumble Guys:**
🏃 **Block Dash** - Corrida clássica
🌊 **Water Race** - Corrida aquática
🔥 **Lava Land** - Obstáculos de lava
❄️ **Ice Cold** - Pista escorregadia
🌪️ **Wind Rush** - Corrida com vento
⚡ **Speed Run** - Velocidade máxima

**Durações:** 30m, 1h, 2h, 6h, 12h, 1d""",
            color=0x7289da
        )
        await ctx.send(embed=embed)
        return

    parts = [part.strip() for part in dados_evento.split('|')]
    if len(parts) < 2:
        embed = create_embed(
            "❌ Formato incorreto",
            "Use: `XCLAN | duração`\nExemplo: `XCLAN | 2h`",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

    try:
        clan_name = parts[0].strip().upper()
        duracao_str = parts[1].strip()

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

        # Criar view com botões para seleção de mapa
        view = StumbleGuysEventView(clan_name, ctx.author.id, end_time)

        # Criar embed do evento
        embed = create_embed(
            f"🎮 EVENTO STUMBLE GUYS - {clan_name}",
            f"""**🏆 Clan:** {clan_name}
**⏰ Duração:** {duracao_str}
**🏁 Termina:** <t:{int(end_time.timestamp())}:R>
**👑 Criado por:** {ctx.author.mention}

**🗺️ Escolha o mapa do Stumble Guys:**
Clique em um dos botões abaixo para selecionar o mapa da batalha!

**📋 Como funciona:**
• Apenas membros do {clan_name} podem participar
• Sem apostas necessárias - só diversão!
• Admin escolhe o mapa clicando nos botões
• Resultado decidido após a partida""",
            color=0xff6600
        )

        evento_msg = await ctx.send(embed=embed, view=view)

        # Salvar evento no banco
        try:
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()

                # Atualizar tabela de eventos de clan
                cursor.execute('''CREATE TABLE IF NOT EXISTS clan_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    creator_id INTEGER,
                    clan1 TEXT,
                    clan2 TEXT,
                    event_type TEXT,
                    bet_amount INTEGER DEFAULT 0,
                    end_time TIMESTAMP,
                    message_id INTEGER,
                    participants TEXT DEFAULT '[]',
                    bets TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'active',
                    winner_clan TEXT,
                    selected_map TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')

                cursor.execute('''
                    INSERT INTO clan_events (guild_id, creator_id, clan1, event_type, bet_amount, end_time, message_id, selected_map)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (ctx.guild.id, ctx.author.id, clan_name, 'Stumble Guys', 0, end_time, evento_msg.id, 'Aguardando seleção'))

                conn.commit()
                conn.close()

            logger.info(f"Evento Stumble Guys criado para clan: {clan_name}")

        except Exception as e:
            logger.error(f"Erro ao salvar evento de clan: {e}")

    except ValueError:
        embed = create_embed("❌ Duração inválida", "Use números válidos para duração: 30m, 2h, 1d", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='eventosclan', aliases=['clanevents'])
async def listar_eventos_clan(ctx):
    """Ver eventos Stumble Guys ativos"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT clan1, event_type, selected_map, end_time, participants, status, id
                FROM clan_events
                WHERE guild_id = %s AND status = 'active'
                ORDER BY end_time
            ''', (ctx.guild.id,))

            eventos = cursor.fetchall()
            conn.close()

        if not eventos:
            embed = create_embed(
                "🎮 Nenhum evento ativo",
                "Não há eventos Stumble Guys ativos no momento.\nAdministradores podem criar com `RXcriareventoclan`",
                color=0xffaa00
            )
            await ctx.send(embed=embed)
            return

        embed = create_embed(
            "🎮 Eventos Stumble Guys Ativos",
            f"Encontrados {len(eventos)} evento(s) ativo(s):",
            color=0xff6600
        )

        for evento in eventos[:5]:
            clan_name, event_type, selected_map, end_time_str, participants_json, status, event_id = evento
            participants = json.loads(participants_json) if participants_json else []

            # Emoji do mapa
            map_emojis = {
                "Block Dash": "🏃",
                "Water Race": "🌊", 
                "Lava Land": "🔥",
                "Ice Cold": "❄️",
                "Wind Rush": "🌪️",
                "Speed Run": "⚡",
                "Aguardando seleção": "❓"
            }

            map_emoji = map_emojis.get(selected_map, "🗺️")

            embed.add_field(
                name=f"🏆 {clan_name} (ID: {event_id})",
                value=f"**🎮 Tipo:** {event_type}\n"
                      f"**🗺️ Mapa:** {map_emoji} {selected_map}\n"
                      f"**👥 Participantes:** {len(participants)}\n"
                      f"**⏰ Termina:** <t:{int(datetime.datetime.fromisoformat(end_time_str).timestamp())}:R>\n"
                      f"**🎯 Status:** {'Aguardando mapa' if selected_map == 'Aguardando seleção' else 'Pronto para jogar!'}",
                inline=False
            )

        embed.add_field(
            name="📋 Como Finalizar",
            value="Use `RXfinalizareventoclan <id> <resultado>`\n"
                  "**Resultados:** `vitoria`, `derrota`, `empate`",
            inline=False
        )

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro ao listar eventos de clan: {e}")

@bot.command(name='finalizareventoclan', aliases=['endclanevent'])
@commands.has_permissions(administrator=True)
async def finalizar_evento_clan(ctx, evento_id: int, resultado: str = "empate"):
    """[ADMIN] Finalizar evento Stumble Guys"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Buscar evento
            cursor.execute('''
                SELECT clan1, selected_map, participants, message_id, end_time
                FROM clan_events
                WHERE id = ? AND guild_id = ? AND status = 'active'
            ''', (evento_id, ctx.guild.id))

            evento = cursor.fetchone()
            if not evento:
                embed = create_embed("❌ Evento não encontrado", "Evento não existe ou já foi finalizado!", color=0xff0000)
                await ctx.send(embed=embed)
                return

            clan_name, selected_map, participants_json, message_id, end_time = evento
            participants = json.loads(participants_json) if participants_json else []

            # Dar XP para participantes (sem moedas)
            xp_bonus = 50 if resultado.lower() == "vitoria" else 25  # XP baseado no resultado

            for user_id in participants:
                leveled_up, new_level, rank_up, new_rank_id, old_rank_id = add_xp(user_id, xp_bonus)
                
                # Atualizar cargo se houve rank up
                if rank_up:
                    try:
                        guild = bot.get_guild(guild_id) if 'guild_id' in locals() else None
                        if guild:
                            member = guild.get_member(user_id)
                            if member:
                                await update_user_rank_role(member, new_rank_id)
                    except Exception as e:
                        logger.error(f"Erro ao atualizar cargo após daily: {e}")

            # Marcar como finalizado
            cursor.execute('''
                UPDATE clan_events
                SET status = 'finished', winner_clan = ?
                WHERE id = ?
            ''', (resultado, evento_id))

            conn.commit()
            conn.close()

        # Determinar emoji e cor baseado no resultado
        if resultado.lower() == "vitoria":
            emoji = "🏆"
            cor = 0xffd700
            mensagem_resultado = "VITÓRIA!"
        elif resultado.lower() == "derrota":
            emoji = "😢"
            cor = 0xff6b6b
            mensagem_resultado = "DERROTA"
        else:
            emoji = "🤝"
            cor = 0x7289da
            mensagem_resultado = "EMPATE"

        embed = create_embed(
            f"{emoji} {clan_name} - {mensagem_resultado}",
            f"""**🎮 Evento Stumble Guys Finalizado!**

**🏆 Clan:** {clan_name}
**🗺️ Mapa:** {selected_map}
**📊 Resultado:** {mensagem_resultado}
**👥 Participantes:** {len(participants)}
**⭐ XP concedido:** {xp_bonus} para cada participante
**👑 Finalizado por:** {ctx.author.mention}

**🎯 Resultados possíveis:**
• `vitoria` - 50 XP para todos
• `derrota` - 25 XP para todos  
• `empate` - 25 XP para todos

*Obrigado por participar! GG! 🎮*""",
            color=cor
        )
        await ctx.send(embed=embed)

        # Notificar participantes
        notification_embed = create_embed(
            f"🎮 Evento Finalizado - {mensagem_resultado}",
            f"O evento Stumble Guys do **{clan_name}** foi finalizado!\n"
            f"**Resultado:** {mensagem_resultado}\n"
            f"**Mapa:** {selected_map}\n"
            f"**XP recebido:** +{xp_bonus} XP",
            color=cor
        )

        for user_id in participants:
            try:
                user = bot.get_user(user_id)
                if user:
                    await user.send(embed=notification_embed)
            except:
                pass

        logger.info(f"Evento Stumble Guys finalizado: {clan_name} - {resultado}")

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
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO reminders (user_id, guild_id, channel_id, reminder_text, remind_time)
                VALUES (%s, %s, %s, %s, %s)
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

@bot.command(name='randownplayers', aliases=['randomplayers'])
async def randownplayers(ctx, quantidade: int = 5):
    """Adiciona jogadores aleatórios do servidor a uma copinha ativa"""
    try:
        global_stats['commands_used'] += 1
        
        # Verificar permissões
        if not ctx.author.guild_permissions.manage_messages:
            embed = create_embed("❌ Permissão negada", 
                               "Você precisa da permissão 'Gerenciar Mensagens' para usar este comando!", 
                               color=0xff0000)
            await ctx.send(embed=embed)
            return

        # Validar quantidade
        if quantidade < 1 or quantidade > 20:
            embed = create_embed("❌ Quantidade inválida", 
                               "Use entre 1 e 20 jogadores por vez!", 
                               color=0xff0000)
            await ctx.send(embed=embed)
            return

        # Procurar copinha ativa no servidor
        copinha_ativa = None
        for message_id, game_data in active_games.items():
            if (game_data.get('type') == 'copinha_join' and 
                hasattr(game_data.get('view'), 'participants') and 
                len(game_data.get('view').participants) < game_data.get('view').max_players):
                copinha_ativa = game_data
                break
        
        if not copinha_ativa:
            embed = create_embed("❌ Nenhuma copinha ativa", 
                               "Não há copinhas com inscrições abertas no momento!\n"
                               "Use `/copinha` para criar uma nova.", 
                               color=0xff0000)
            await ctx.send(embed=embed)
            return

        view = copinha_ativa.get('view')
        if not view:
            embed = create_embed("❌ Erro interno", 
                               "Copinha encontrada mas view não disponível!", 
                               color=0xff0000)
            await ctx.send(embed=embed)
            return

        # Pegar membros do servidor (excluindo bots e já inscritos)
        all_members = [m for m in ctx.guild.members if not m.bot and m.id not in view.participants]
        
        if not all_members:
            embed = create_embed("❌ Sem membros disponíveis", 
                               "Não há membros disponíveis para adicionar!", 
                               color=0xff0000)
            await ctx.send(embed=embed)
            return

        # Calcular quantos podem ser adicionados
        vagas_disponiveis = view.max_players - len(view.participants)
        quantidade_real = min(quantidade, vagas_disponiveis, len(all_members))
        
        if quantidade_real == 0:
            embed = create_embed("❌ Copinha lotada", 
                               "A copinha já está lotada!", 
                               color=0xff0000)
            await ctx.send(embed=embed)
            return

        # Selecionar membros aleatórios
        random_members = random.sample(all_members, quantidade_real)
        
        # Adicionar à copinha
        added_names = []
        for member in random_members:
            view.participants.append(member.id)
            added_names.append(member.display_name)

        # Verificar se a copinha agora está lotada
        if len(view.participants) >= view.max_players:
            # Iniciar torneio automaticamente
            try:
                await start_tournament_standalone(ctx.channel, view.title, view.map_name, 
                                                view.team_format, view.max_players, 
                                                view.participants, view.creator_id)
                action_text = f"Copinha **{view.title}** está lotada e foi **iniciada automaticamente**! 🚀"
            except Exception as e:
                logger.error(f"Erro ao iniciar torneio automaticamente: {e}")
                action_text = "Copinha lotada! Use `/copinha` para iniciar."
        else:
            action_text = f"Ainda faltam **{view.max_players - len(view.participants)}** jogadores para iniciar."

        # Resposta de sucesso
        embed = create_embed(
            "✅ Jogadores adicionados!", 
            f"**{quantidade_real}** jogadores aleatórios foram adicionados à copinha:\n\n"
            f"👥 **Adicionados:** {', '.join(added_names)}\n"
            f"📊 **Total:** {len(view.participants)}/{view.max_players}\n\n"
            f"{action_text}",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Erro no comando randownplayers: {e}")
        embed = create_embed("❌ Erro", "Erro interno! Tente novamente.", color=0xff0000)
        await ctx.send(embed=embed)


# Sistemas de manutenção de conexão removidos para economizar recursos

# Sistemas de restart automático removidos para economizar recursos

# ==================== DASHBOARD WEB FLASK ====================

# Configuração Flask
app = Flask(__name__, template_folder='dashboard/templates', static_folder='dashboard/static')
app.secret_key = os.environ.get('SECRET_KEY', 'rxbot-dashboard-secret-key')

# Importar template functions
from flask import render_template

def get_dashboard_stats():
    """Obter estatísticas para o dashboard"""
    try:
        # Total de usuários
        result = execute_query('SELECT COUNT(DISTINCT user_id) as total_users FROM users', fetch_one=True)
        total_users = result[0] if result else 0
        
        # Total de copinhas
        try:
            result = execute_query('SELECT COUNT(*) as total_copinhas FROM copinhas', fetch_one=True)
            total_copinhas = result[0] if result else 0
        except:
            total_copinhas = 0
        
        # Total de tickets
        try:
            result = execute_query('SELECT COUNT(*) as total_tickets FROM tickets WHERE status = %s', ['open'], fetch_one=True)
            total_tickets = result[0] if result else 0
        except:
            total_tickets = 0
        
        # Total de giveaways
        try:
            result = execute_query('SELECT COUNT(*) as total_giveaways FROM giveaways', fetch_one=True)
            total_giveaways = result[0] if result else 0
        except:
            total_giveaways = 0
        
        return {
            'total_users': total_users,
            'total_copinhas': total_copinhas,
            'total_tickets': total_tickets,
            'total_giveaways': total_giveaways,
            'total_commands': 98
        }
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas dashboard: {e}")
        return {
            'total_users': 0,
            'total_copinhas': 0,
            'total_tickets': 0,
            'total_giveaways': 0,
            'total_commands': 98
        }

def get_guild_stats():
    """Obter estatísticas dos servidores"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Total de usuários
            cursor.execute('SELECT COUNT(*) FROM users')
            result = cursor.fetchone()
            total_users = result[0] if result else 0

            # Total de servidores
            cursor.execute('SELECT COUNT(*) FROM guilds')
            result = cursor.fetchone()
            total_guilds = result[0] if result else 0

            # Total de tickets
            cursor.execute('SELECT COUNT(*) FROM tickets')
            result = cursor.fetchone()
            total_tickets = result[0] if result else 0

            # Total de eventos
            cursor.execute('SELECT COUNT(*) FROM events WHERE status = "active"')
            result = cursor.fetchone()
            active_events = result[0] if result else 0

            # Total de copinhas - verificar se tabela existe
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='copinhas'")
                if cursor.fetchone():
                    cursor.execute('SELECT COUNT(*) FROM copinhas WHERE status = "active"')
                    result = cursor.fetchone()
                    active_copinhas = result[0] if result else 0
                else:
                    active_copinhas = 0
            except:
                active_copinhas = 0

            conn.close()
            return {
                'total_users': total_users,
                'total_guilds': total_guilds,
                'total_tickets': total_tickets,
                'active_events': active_events,
                'active_copinhas': active_copinhas
            }
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return {
            'total_users': 0,
            'total_guilds': 0,
            'total_tickets': 0,
            'active_events': 0,
            'active_copinhas': 0
        }

@app.route('/')
def dashboard_home():
    """Página inicial do dashboard"""
    stats = get_dashboard_stats()
    return render_template('index.html', stats=stats)

@app.route('/commands')
def commands():
    """Página de comandos"""
    commands_data = {
        'Diversão': [
            {'name': '/jokenpo', 'description': 'Jogar pedra, papel ou tesoura'},
            {'name': '/dado', 'description': 'Rolar um dado'},
            {'name': '/moeda', 'description': 'Cara ou coroa'},
            {'name': '/piada', 'description': 'Contar uma piada'}
        ],
        'Economia': [
            {'name': '/saldo', 'description': 'Ver saldo de moedas'},
            {'name': '/daily', 'description': 'Recompensa diária'},
            {'name': '/weekly', 'description': 'Recompensa semanal'},
            {'name': '/trabalhar', 'description': 'Trabalhar para ganhar dinheiro'}
        ],
        'Copinha/Torneios': [
            {'name': '/copinha', 'description': 'Criar torneio de Stumble Guys'},
            {'name': '/brackets', 'description': 'Ver brackets do torneio'}
        ],
        'Moderação': [
            {'name': '/ban', 'description': 'Banir usuário do servidor'},
            {'name': '/kick', 'description': 'Expulsar usuário'},
            {'name': '/clear', 'description': 'Limpar mensagens'}
        ]
    }
    return render_template('commands.html', commands=commands_data)

@app.route('/faq')
def faq():
    """Página de FAQ"""
    faq_data = [
        {
            'question': 'Como criar uma copinha/torneio?',
            'answer': 'Use o comando /copinha e siga os passos: escolha o mapa, formato (1v1, 2v2, 3v3) e número de jogadores (4, 8, 16, 32). O bot criará automaticamente os brackets!'
        },
        {
            'question': 'Como participar de uma copinha?',
            'answer': 'Clique no botão "🎮 Participar" na mensagem da copinha. O bot verificará automaticamente se há vagas disponíveis.'
        },
        {
            'question': 'Como ganhar moedas no bot?',
            'answer': 'Use /daily (diário), /weekly (semanal), /monthly (mensal), /trabalhar, ou tente a sorte com /roubar de outros usuários!'
        }
    ]
    return render_template('faq.html', faq=faq_data)

@app.route('/support')
def support():
    """Página de suporte"""
    return render_template('support.html')

@app.route('/tutorials')
def tutorials():
    """Página de tutoriais"""
    tutorials_data = [
        {
            'title': 'Como Criar sua Primeira Copinha',
            'description': 'Aprenda passo a passo como organizar um torneio épico',
            'steps': [
                'Use o comando /copinha no canal desejado',
                'Escolha um nome chamativo para seu torneio',
                'Selecione o mapa do Stumble Guys',
                'Defina o formato: 1v1, 2v2 ou 3v3 jogadores',
                'Escolha quantos participantes: 4, 8, 16 ou 32',
                'Clique em "Criar Copinha" e pronto!'
            ]
        }
    ]
    return render_template('tutorials.html', tutorials=tutorials_data)

@app.route('/healthz')
def health_check():
    """Endpoint de health check para Railway - liveness probe"""
    return "OK", 200

@app.route('/health')
def health_check_alt():
    """Endpoint alternativo de health check"""
    return "OK", 200

@app.route('/readyz')
def readiness_check():
    """Endpoint de readiness check - inclui verificações mais complexas"""
    try:
        ready_status = {
            'status': 'ready',
            'service': 'discord-bot-rx',
            'timestamp': datetime.datetime.now().isoformat(),
            'bot_ready': bot.is_ready() if 'bot' in globals() else False
        }
        
        # Verificar conexão com banco apenas se token existe (modo completo)
        if os.getenv('TOKEN'):
            try:
                execute_query("SELECT 1", fetch_one=True)
                ready_status['database'] = 'connected'
            except Exception as e:
                ready_status['database'] = 'error'
                ready_status['status'] = 'degraded'
        else:
            ready_status['database'] = 'not_required'
            
        return jsonify(ready_status)
    except Exception as e:
        return jsonify({
            'status': 'not_ready',
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }), 503

@app.route('/')
def root_health():
    """Root endpoint para compatibilidade"""
    return "RX Bot - OK", 200

@app.route('/dashboard')
def dashboard():
    """Página principal do dashboard"""
    try:
        stats = get_guild_stats()
        stats['bot_status'] = 'ready' if bot.is_ready() else 'offline'
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        return jsonify({
            'service': 'RX Discord Bot Dashboard',
            'status': 'error',
            'error': str(e)
        })

@app.route('/comandos')
def comandos_page():
    """Página de comandos"""
    return render_template('comandos.html')

@app.route('/faq')
def faq_page():
    """Página de FAQ"""
    return render_template('faq.html')

@app.route('/suporte')
def suporte_page():
    """Página de suporte"""
    return render_template('suporte.html')

@app.route('/api/stats')
def api_stats():
    """API para obter estatísticas em tempo real"""
    stats = get_guild_stats()
    return jsonify(stats)

@app.route('/users')
def users_page():
    """Página de usuários"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT user_id, coins, xp, level, reputation, bank, 
                       last_daily, total_messages, warnings 
                FROM users 
                ORDER BY xp DESC 
                LIMIT 50
            ''')

            users = cursor.fetchall()
            conn.close()

            return render_template('users.html', users=users)
    except Exception as e:
        logger.error(f"Erro ao carregar usuários: {e}")
        return render_template('users.html', users=[])

@app.route('/tickets')
def tickets_page():
    """Página de tickets"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT ticket_id, guild_id, creator_id, channel_id, 
                       status, created_at, closed_by, reason 
                FROM tickets 
                ORDER BY created_at DESC 
                LIMIT 50
            ''')

            tickets = cursor.fetchall()
            conn.close()

            return render_template('tickets.html', tickets=tickets)
    except Exception as e:
        logger.error(f"Erro ao carregar tickets: {e}")
        return render_template('tickets.html', tickets=[])

@app.route('/copinha')
def copinha_api():
    """API endpoint para sistema de copinhas"""
    try:
        return jsonify({
            'status': 'success',
            'message': '⚽ Sistema de copinhas ativo e funcionando!',
            'commands': {
                'create': '/copinha - Criar nova copinha/torneio',
                'active': '/copinhas_ativas - Ver copinhas ativas',
                'scoreboard': '/cuptop10 - Ver ranking'
            },
            'description': 'Sistema completo de torneios e copinhas do Stumble Guys integrado ao Discord'
        })
    except Exception as e:
        logger.error(f"Erro na API de copinha: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Erro interno no sistema de copinhas'
        }), 500

@app.route('/copinhas')
def copinhas_page():
    """Página de copinhas/torneios"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Verificar se a tabela copinhas existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='copinhas'")
            if cursor.fetchone():
                cursor.execute('''
                    SELECT id, guild_id, channel_id, creator_id, title, 
                           map_name, format_type, status, participants, 
                           current_round, created_at 
                    FROM copinhas 
                    ORDER BY created_at DESC 
                    LIMIT 20
                ''')
                copinhas = cursor.fetchall()
            else:
                copinhas = []

            conn.close()

            return render_template('copinhas.html', copinhas=copinhas)
    except Exception as e:
        logger.error(f"Erro ao carregar copinhas: {e}")
        return render_template('copinhas.html', copinhas=[])

@app.route('/api/user/<int:user_id>')
def api_user(user_id):
    """API para obter dados específicos de um usuário"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
            user_data = cursor.fetchone()

            if user_data:
                user_dict = {
                    'user_id': user_data[0],
                    'coins': user_data[1],
                    'xp': user_data[2],
                    'level': user_data[3],
                    'reputation': user_data[4],
                    'bank': user_data[5],
                    'last_daily': user_data[6],
                    'last_weekly': user_data[7],
                    'last_monthly': user_data[8],
                    'inventory': json.loads(user_data[9]) if user_data[9] else {},
                    'achievements': json.loads(user_data[10]) if user_data[10] else [],
                    'settings': json.loads(user_data[11]) if user_data[11] else {},
                    'join_date': user_data[12],
                    'total_messages': user_data[13],
                    'voice_time': user_data[14],
                    'warnings': user_data[15]
                }

                conn.close()
                return jsonify(user_dict)
            else:
                conn.close()
                return jsonify({'error': 'Usuário não encontrado'}), 404

    except Exception as e:
        logger.error(f"Erro ao obter dados do usuário: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

def run_dashboard():
    """Executar o dashboard Flask usando gunicorn para produção"""
    port = int(os.getenv('PORT', 5000))
    
    # Verificar se está em produção (Railway/Heroku)
    if is_production():
        print(f"🌐 Modo produção detectado - use: gunicorn main:app --bind 0.0.0.0:{port}")
        print(f"🔗 Para testar localmente, execute: gunicorn main:app --bind 0.0.0.0:{port} --reload")
        # Em produção, o gunicorn será iniciado externamente
        # Não executar app.run() aqui
        return
    else:
        # Modo desenvolvimento - usar Flask diretamente
        print(f"🌐 Modo desenvolvimento - iniciando Flask na porta {port}")
        try:
            app.run(host='0.0.0.0', port=port, debug=False, threaded=True, use_reloader=False)
        except Exception as e:
            print(f"❌ Erro ao iniciar Flask: {e}")
            raise

def start_dashboard():
    """Iniciar dashboard Flask em thread separada"""
    try:
        logger.info("🌐 Iniciando dashboard web na porta 5000...")
        run_dashboard()
    except Exception as e:
        logger.error(f"❌ Erro no dashboard: {e}")

# ==================== FIM DASHBOARD WEB ====================

async def start_bot():
    """Sistema de inicialização simplificado"""
    token = os.getenv('TOKEN')
    if not token:
        logger.error("🚨 TOKEN não encontrado!")
        return

    try:
        logger.info("🚀 Iniciando RXbot...")
        await bot.start(token)
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar bot: {e}")
        raise


# Funções de keep-alive removidos para economizar recursos

# Sistemas de restart automático removidos para economizar recursos

if __name__ == "__main__":
    try:
        # Verificar token
        token = os.getenv('TOKEN')
        
        logger.info("🚀 Iniciando RXBot + Dashboard...")

        # Detectar ambiente Railway
        is_railway = os.getenv('RAILWAY_ENVIRONMENT_NAME') or os.getenv('RAILWAY_PROJECT_NAME')
        
        if is_railway:
            print("🚂 Detectado ambiente Railway")
            print(f"📍 Porta configurada: {os.getenv('PORT', '5000')}")
            
        # Inicializar database SEMPRE (independente de ter TOKEN ou não)
        logger.info("🎯 Inicializando sistema completo...")
        try:
            init_database()
            logger.info("✅ Database initialized successfully!")
        except Exception as db_error:
            logger.warning(f"⚠️ Erro no database: {db_error}")
            
        # Sempre iniciar Flask primeiro (Railway precisa de resposta rápida)
        print("🌐 Iniciando servidor Flask...")
        
        if not token:
            logger.warning("⚠️ TOKEN não encontrado nas variáveis de ambiente!")
            logger.info("🌐 Rodando apenas o servidor Flask para health check")
            
            # Modo Flask-only para Railway (thread não-daemon)
            try:
                run_dashboard()
            except KeyboardInterrupt:
                logger.info("🛑 Servidor interrompido pelo usuário")
        else:
            # Modo completo: Flask + Bot Discord
            logger.info("🎯 Modo completo: Flask + Bot Discord...")
            
            # Iniciar Flask em thread separada
            dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
            dashboard_thread.start()
            
            # Aguardar Flask inicializar
            time.sleep(3)
            
            try:
                # Testar se Flask está respondendo
                import requests
                response = requests.get(f"http://127.0.0.1:{os.getenv('PORT', '5000')}/healthz", timeout=5)
                if response.status_code == 200:
                    logger.info("✅ Flask está respondendo")
                else:
                    logger.warning(f"⚠️ Flask resposta: {response.status_code}")
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível testar Flask: {e}")
            
            # Iniciar bot Discord
            logger.info("🤖 Iniciando bot Discord...")
            try:
                bot.run(token)
            except Exception as e:
                logger.error(f"❌ Erro no bot Discord: {e}")
                # Manter Flask rodando mesmo se bot falhar
                logger.info("🌐 Mantendo Flask ativo...")
                try:
                    dashboard_thread.join()
                except KeyboardInterrupt:
                    logger.info("🛑 Servidor interrompido pelo usuário")

    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido pelo usuário")
    except Exception as e:
        logger.error(f"🚨 Erro fatal: {e}")
        sys.exit(1)

# View para participação na copinha
class CopinhaParticipationView(discord.ui.View):
    def __init__(self, message_id, max_players, titulo, mapa, formato):
        super().__init__(timeout=None)
        self.message_id = message_id
        self.max_players = max_players
        self.titulo = titulo
        self.mapa = mapa
        self.formato = formato
        self.participants = []

    @discord.ui.button(label="🎮 Participar", style=discord.ButtonStyle.green, custom_id="join_copinha")
    async def join_copinha(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Verificar se já está participando
            if interaction.user.id in self.participants:
                await interaction.response.send_message("❌ Você já está participando desta copinha!", ephemeral=True)
                return

            # Verificar se há vagas
            if len(self.participants) >= self.max_players:
                await interaction.response.send_message("❌ Copinha lotada! Não há mais vagas.", ephemeral=True)
                return

            # Adicionar participante
            self.participants.append(interaction.user.id)

            # Buscar dados da copinha no banco
            copinha_data = execute_query('SELECT * FROM copinhas WHERE message_id = ?', (self.message_id,), fetch_one=True)
            
            if copinha_data:
                # Atualizar no banco
                execute_query('UPDATE copinhas SET participants = ? WHERE message_id = ?', 
                            (json.dumps(self.participants), self.message_id))

            # Criar lista de participantes para exibir
            participant_mentions = [f"<@{p}>" for p in self.participants]
            participants_text = "\n".join([f"{i+1}. {mention}" for i, mention in enumerate(participant_mentions)])

            # Mapas disponíveis do Stumble Guys com emojis
            mapas_emojis = {
                'block dash': '🧱', 'super slide': '🛝', 'dizzy heights': '🌪️',
                'gate crash': '🚪', 'hit parade': '🎯', 'the whirlygig': '🌀',
                'see saw': '⚖️', 'tip toe': '👣', 'perfect match': '🎮',
                'fall mountain': '🏔️', 'hex-a-gone': '⬡', 'royal fumble': '👑'
            }

            mapa_emoji = '🗺️'
            for mapa_nome, emoji in mapas_emojis.items():
                if mapa_nome in self.mapa.lower():
                    mapa_emoji = emoji
                    break

            # Atualizar embed
            embed = create_embed(
                f"🏆 {self.titulo}",
                f"""**🗺️ Mapa:** {mapa_emoji} {self.mapa}
**👥 Formato:** {self.formato}
**👑 Máximo de Jogadores:** {self.max_players}
**📊 Status:** {'🟢 Inscrições Abertas' if len(self.participants) < self.max_players else '🔴 Copinha Cheia'}
**👑 Organizador:** <@{copinha_data[2] if copinha_data else interaction.user.id}>

**👥 Participantes ({len(self.participants)}/{self.max_players}):**
{participants_text if participants_text else "Nenhum participante ainda"}

**📝 Regras:**
• Apenas jogadores do servidor podem participar
• As partidas serão organizadas em canais privados
• Um moderador definirá os vencedores
• Sem apostas - apenas diversão e glória!

{f"**🎉 COPINHA CHEIA! Criando brackets...**" if len(self.participants) >= self.max_players else "**🎮 Clique em 'Participar' para se inscrever!**"}""",
                color=0xffd700 if len(self.participants) >= self.max_players else 0x00ff00
            )

            # Se copinha encheu, iniciar torneio
            if len(self.participants) >= self.max_players:
                await self.start_tournament(interaction, embed)
                button.disabled = True
                button.label = "🔒 Copinha Cheia"
                button.style = discord.ButtonStyle.secondary
            
            await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            logger.error(f"Erro ao participar da copinha: {e}")
            await safe_send_response(interaction, content="❌ Erro ao entrar na copinha! Tente novamente.", ephemeral=True)

    @discord.ui.button(label="❌ Sair", style=discord.ButtonStyle.red, custom_id="leave_copinha")
    async def leave_copinha(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if interaction.user.id not in self.participants:
                await safe_send_response(interaction, content="❌ Você não está participando desta copinha!", ephemeral=True)
                return

            # Remover participante
            self.participants.remove(interaction.user.id)

            # Atualizar no banco
            execute_query('UPDATE copinhas SET participants = %s WHERE message_id = %s', 
                        (json.dumps(self.participants), self.message_id))

            # Criar lista de participantes atualizada
            participant_mentions = [f"<@{p}>" for p in self.participants]
            participants_text = "\n".join([f"{i+1}. {mention}" for i, mention in enumerate(participant_mentions)])

            # Mapas disponíveis do Stumble Guys com emojis
            mapas_emojis = {
                'block dash': '🧱', 'super slide': '🛝', 'dizzy heights': '🌪️',
                'gate crash': '🚪', 'hit parade': '🎯', 'the whirlygig': '🌀',
                'see saw': '⚖️', 'tip toe': '👣', 'perfect match': '🎮',
                'fall mountain': '🏔️', 'hex-a-gone': '⬡', 'royal fumble': '👑'
            }

            mapa_emoji = '🗺️'
            for mapa_nome, emoji in mapas_emojis.items():
                if mapa_nome in self.mapa.lower():
                    mapa_emoji = emoji
                    break

            # Atualizar embed
            embed = create_embed(
                f"🏆 {self.titulo}",
                f"""**🗺️ Mapa:** {mapa_emoji} {self.mapa}
**👥 Formato:** {self.formato}
**👑 Máximo de Jogadores:** {self.max_players}
**📊 Status:** 🟢 Inscrições Abertas
**👑 Organizador:** <@{interaction.message.embeds[0].description.split('<@')[1].split('>')[0] if interaction.message.embeds else interaction.user.id}>

**👥 Participantes ({len(self.participants)}/{self.max_players}):**
{participants_text if participants_text else "Nenhum participante ainda"}

**📝 Regras:**
• Apenas jogadores do servidor podem participar
• As partidas serão organizadas em canais privados
• Um moderador definirá os vencedores
• Sem apostas - apenas diversão e glória!

**🎮 Clique em 'Participar' para se inscrever!**""",
                color=0x00ff00
            )

            await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            logger.error(f"Erro ao sair da copinha: {e}")
            await safe_send_response(interaction, content="❌ Erro ao sair da copinha! Tente novamente.", ephemeral=True)

    async def start_tournament(self, interaction, embed):
        """Iniciar o torneio quando a copinha encher"""
        try:
            # Embaralhar participantes para fairness
            random.shuffle(self.participants)

            # Criar categoria para o torneio
            category_name = f"🏆 {self.titulo[:15]}"
            category = await interaction.guild.create_category(category_name)

            # Criar canal de informações gerais
            info_channel = await interaction.guild.create_text_channel(
                f"📋-info-{self.titulo[:10]}",
                category=category
            )

            # Calcular quantas partidas na primeira rodada
            first_round_matches = len(self.participants) // 2

            # Criar canais para cada partida
            matches_data = []
            for i in range(first_round_matches):
                player1_id = self.participants[i * 2]
                player2_id = self.participants[i * 2 + 1]

                # Criar canal da partida
                match_channel = await interaction.guild.create_text_channel(
                    f"🎮-partida-{i+1}",
                    category=category
                )

                # Configurar permissões do canal
                await match_channel.set_permissions(interaction.guild.default_role, read_messages=False)
                await match_channel.set_permissions(interaction.guild.get_member(player1_id), read_messages=True, send_messages=True)
                await match_channel.set_permissions(interaction.guild.get_member(player2_id), read_messages=True, send_messages=True)

                # Dar permissão para moderadores
                for role in interaction.guild.roles:
                    if any(keyword in role.name.lower() for keyword in ['mod', 'admin', 'staff']):
                        await match_channel.set_permissions(role, read_messages=True, send_messages=True)

                # Salvar dados da partida
                match_data = {
                    'match_number': i + 1,
                    'player1_id': player1_id,
                    'player2_id': player2_id,
                    'channel_id': match_channel.id
                }
                matches_data.append(match_data)

                # Salvar no banco
                copinha_data = execute_query('SELECT id FROM copinhas WHERE message_id = ?', (self.message_id,), fetch_one=True)
                if copinha_data:
                    execute_query('''
                        INSERT INTO copinha_matches (copinha_id, round_name, match_number, players, ticket_channel_id, status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (copinha_data[0], 'Primeira Rodada', i + 1, json.dumps([player1_id, player2_id]), match_channel.id, 'waiting'))

                # Embed da partida
                match_embed = create_embed(
                    f"🎮 Partida {i+1} - Primeira Rodada",
                    f"""**🏆 Copinha:** {self.titulo}
**🗺️ Mapa:** {self.mapa}
**👥 Formato:** {self.formato}

**⚔️ CONFRONTO:**
🔴 <@{player1_id}> 
🆚 
🔵 <@{player2_id}>

**📋 INSTRUÇÕES:**
1. 📅 Coordenem o horário da partida entre vocês
2. 🎮 Joguem APENAS no mapa **{self.mapa}**
3. 🏆 O vencedor deve reportar o resultado aqui
4. ⏳ Aguardem um moderador confirmar o resultado
5. 📸 Prints da vitória são bem-vindos!

**🎯 BOA SORTE PARA AMBOS!**
**⏰ Partida criada:** <t:{int(datetime.datetime.now().timestamp())}:R>""",
                    color=0x00ff00
                )

                await match_channel.send(embed=match_embed)

            # Embed de resumo no canal de informações
            matches_text = "\n".join([f"**Partida {m['match_number']}:** <@{m['player1_id']}> 🆚 <@{m['player2_id']}>" for m in matches_data])

            tournament_embed = create_embed(
                f"🏆 {self.titulo} - TORNEIO INICIADO!",
                f"""**🎉 A copinha está oficialmente em andamento!**

**📊 INFORMAÇÕES:**
• **🗺️ Mapa:** {self.mapa}
• **👥 Formato:** {self.formato}
• **👑 Participantes:** {len(self.participants)}
• **🎮 Partidas da 1ª rodada:** {first_round_matches}

**⚔️ CONFRONTOS DA PRIMEIRA RODADA:**
{matches_text}

**📋 PRÓXIMOS PASSOS:**
1. Os jogadores devem ir aos seus canais de partida
2. Coordenar horários e jogar no mapa especificado
3. Vencedores reportam resultado no canal da partida
4. Moderadores confirmam e criam próxima rodada

**🏆 QUE COMECEM OS JOGOS!**
**📅 Iniciado:** <t:{int(datetime.datetime.now().timestamp())}:F>""",
                color=0xffd700
            )

            await info_channel.send(embed=tournament_embed)

            # Atualizar status no banco
            execute_query('UPDATE copinhas SET current_round = ?, status = ? WHERE message_id = ?', 
                        ('primeira_rodada', 'em_andamento', self.message_id))

            logger.info(f"Torneio iniciado: {self.titulo} com {len(self.participants)} participantes")

        except Exception as e:
            logger.error(f"Erro ao iniciar torneio: {e}")

@bot.tree.command(name="copinhas_ativas", description="Ver copinhas ativas no servidor")
async def slash_copinhas_ativas(interaction: discord.Interaction):
    """Ver copinhas/torneios ativos"""
    try:
        # Buscar copinhas ativas
        copinhas = execute_query('''
            SELECT title, map_name, team_format, max_players, participants, current_round, status, creator_id, created_at 
            FROM copinhas 
            WHERE guild_id = ? AND status IN ('active', 'em_andamento')
            ORDER BY created_at DESC
        ''', (interaction.guild.id,), fetch_all=True)

        if not copinhas:
            embed = create_embed(
                "🏆 Copinhas Ativas",
                "**Nenhuma copinha ativa no momento!**\n\n"
                "💡 Moderadores podem criar uma nova copinha com `/copinha`",
                color=0xffaa00
            )
            await interaction.response.send_message(embed=embed)
            return

        embed = create_embed(
            f"🏆 Copinhas Ativas ({len(copinhas)})",
            "Copinhas/torneios ativos no servidor:",
            color=0xffd700
        )

        for i, copinha in enumerate(copinhas[:5]):  # Máximo 5 para não ficar muito longo
            title, map_name, team_format, max_players, participants_json, current_round, status, creator_id, created_at = copinha
            
            participants = json.loads(participants_json) if participants_json else []
            creator = interaction.guild.get_member(creator_id)
            creator_name = creator.display_name if creator else "Usuário desconhecido"

            status_emoji = "🟢" if status == "active" else "🔴" if status == "em_andamento" else "⏸️"
            status_text = "Inscrições abertas" if status == "active" else "Em andamento" if status == "em_andamento" else "Pausada"

            embed.add_field(
                name=f"🏆 {title}",
                value=f"**🗺️ Mapa:** {map_name}\n"
                      f"**👥 Formato:** {team_format}\n"
                      f"**👑 Participantes:** {len(participants)}/{max_players}\n"
                      f"**📊 Status:** {status_emoji} {status_text}\n"
                      f"**⚔️ Rodada:** {current_round}\n"
                      f"**👤 Criador:** {creator_name}",
                inline=True
            )

        if len(copinhas) > 5:
            embed.set_footer(text=f"Mostrando 5 de {len(copinhas)} copinhas ativas")

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        logger.error(f"Erro ao listar copinhas: {e}")
        await safe_send_response(interaction, content="❌ Erro ao carregar copinhas!", ephemeral=True)