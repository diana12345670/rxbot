CHANNEL_ID_ALERTA = 1402658677923774615
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
import psutil
import platform
import sys
import gc
import traceback
import io
import uuid
import secrets
import string
import csv
import xml.etree.ElementTree as ET
import yaml
from datetime import timedelta
import calendar
import locale
import pytz
from urllib.parse import quote, unquote
import base64
import zlib
import gzip
import tempfile
import shutil
import zipfile
import tarfile
import mimetypes
import email.utils
import hmac
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot está online!"

@app.route('/status')
def status():
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

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

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
                description TEXT,
                prize TEXT,
                winners_count INTEGER DEFAULT 1,
                end_time TIMESTAMP,
                participants TEXT DEFAULT '[]',
                status TEXT DEFAULT 'active',
                message_id INTEGER,
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
            'música': ['música', 'cantando', 'banda', 'artista', 'som', 'playlist'],
            'escola': ['escola', 'estudar', 'prova', 'trabalho', 'faculdade', 'universidade'],
            'trabalho': ['trabalho', 'emprego', 'carreira', 'profissão', 'salário'],
            'relacionamento': ['amor', 'namorado', 'namorada', 'crush', 'paquera', 'relacionamento'],
            'saúde': ['saúde', 'exercício', 'academia', 'dieta', 'médico', 'remédio'],
            'esporte': ['futebol', 'basquete', 'vôlei', 'natação', 'corrida', 'esporte'],
            'comida': ['comida', 'receita', 'cozinhar', 'restaurante', 'pizza', 'hambúrguer'],
            'filme': ['filme', 'cinema', 'série', 'netflix', 'anime', 'desenho'],
            'anime': ['anime', 'manga', 'otaku', 'naruto', 'one piece', 'dragon ball'],
            'meme': ['meme', 'engraçado', 'piada', 'humor', 'rir', 'zoeira'],
            'clima': ['tempo', 'clima', 'chuva', 'sol', 'frio', 'calor'],
            'viagem': ['viagem', 'viajar', 'férias', 'turismo', 'praia', 'cidade'],
            'dinheiro': ['dinheiro', 'economia', 'investir', 'poupança', 'gasto'],
            'pet': ['pet', 'cachorro', 'gato', 'animal', 'bicho'],
            'arte': ['arte', 'desenho', 'pintura', 'criatividade', 'artista'],
            'livro': ['livro', 'ler', 'literatura', 'história', 'romance'],
            'ciência': ['ciência', 'física', 'química', 'biologia', 'matemática'],
            'espaço': ['espaço', 'planeta', 'estrela', 'universo', 'nasa'],
            'história': ['história', 'passado', 'guerra', 'antigo', 'época'],
            'política': ['política', 'governo', 'eleição', 'presidente', 'democracia'],
            'religião': ['deus', 'igreja', 'fé', 'religião', 'oração'],
            'filosofia': ['filosofia', 'pensamento', 'vida', 'existência', 'reflexão'],
            'psicologia': ['psicologia', 'mente', 'comportamento', 'emoção', 'sentimento'],
            'internet': ['internet', 'rede social', 'instagram', 'tiktok', 'youtube'],
            'moda': ['moda', 'roupa', 'estilo', 'look', 'fashion'],
            'beleza': ['beleza', 'cabelo', 'maquiagem', 'pele', 'cuidado'],
            'natureza': ['natureza', 'árvore', 'floresta', 'mar', 'rio'],
            'ecologia': ['ecologia', 'meio ambiente', 'reciclagem', 'sustentabilidade'],
            'carros': ['carro', 'moto', 'veículo', 'dirigir', 'velocidade'],
            'casa': ['casa', 'quarto', 'decoração', 'móveis', 'limpeza'],
            'família': ['família', 'pai', 'mãe', 'irmão', 'irmã', 'parente'],
            'amizade': ['amigo', 'amizade', 'melhor amigo', 'companheiro'],
            'festa': ['festa', 'aniversário', 'celebração', 'comemoração'],
            'hobbies': ['hobby', 'passatempo', 'coleção', 'artesanato'],
            'profissões': ['médico', 'professor', 'engenheiro', 'advogado', 'programador'],
            'instrumentos': ['violão', 'piano', 'guitarra', 'bateria', 'instrumento'],
            'cores': ['cor', 'azul', 'vermelho', 'verde', 'amarelo', 'roxo'],
            'números': ['número', 'matemática', 'conta', 'calcular', 'estatística'],
            'tempo': ['tempo', 'hora', 'minuto', 'segundo', 'relógio'],
            'idiomas': ['idioma', 'inglês', 'espanhol', 'francês', 'alemão'],
            'países': ['país', 'brasil', 'eua', 'japão', 'frança', 'alemanha'],
            'cidades': ['cidade', 'são paulo', 'rio de janeiro', 'nova york'],
            'transporte': ['ônibus', 'metrô', 'avião', 'trem', 'uber'],
            'compras': ['comprar', 'loja', 'shopping', 'preço', 'desconto'],
            'social': ['sociedade', 'comunidade', 'pessoas', 'grupo', 'equipe'],
            'personalidade': ['personalidade', 'caráter', 'jeito', 'modo', 'forma'],
            'objetivos': ['objetivo', 'meta', 'sonho', 'plano', 'futuro'],
            'problemas': ['problema', 'dificuldade', 'desafio', 'obstáculo'],
            'soluções': ['solução', 'resolver', 'consertar', 'arrumar', 'corrigir'],
            'aprendizado': ['aprender', 'ensinar', 'conhecimento', 'sabedoria'],
            'criatividade': ['criativo', 'inovação', 'ideia', 'imaginação'],
            'sucesso': ['sucesso', 'vitória', 'conquista', 'alcançar', 'atingir'],
            'fracasso': ['fracasso', 'derrota', 'falhar', 'perder', 'erro'],
            'motivação': ['motivação', 'inspiração', 'força', 'energia', 'vontade'],
            'paz': ['paz', 'tranquilo', 'calmo', 'sereno', 'relaxar'],
            'estresse': ['estresse', 'pressão', 'ansiedade', 'nervoso', 'tenso'],
            'felicidade': ['feliz', 'alegria', 'contentamento', 'satisfação'],
            'tristeza': ['triste', 'melancolia', 'depressão', 'choro'],
            'raiva': ['raiva', 'ódio', 'irritação', 'bravo', 'furioso'],
            'medo': ['medo', 'susto', 'terror', 'pânico', 'assombração'],
            'coragem': ['coragem', 'bravura', 'ousadia', 'valentia'],
            'confiança': ['confiança', 'segurança', 'certeza', 'convicção'],
            'dúvida': ['dúvida', 'incerteza', 'questão', 'pergunta'],
            'curiosidade': ['curioso', 'interessante', 'investigar', 'descobrir'],
            'aventura': ['aventura', 'explorar', 'descobrir', 'jornada'],
            'rotina': ['rotina', 'dia a dia', 'costume', 'hábito'],
            'mudança': ['mudança', 'transformação', 'diferente', 'novo'],
            'tradição': ['tradição', 'costume', 'cultura', 'herança'],
            'inovação': ['inovação', 'novo', 'moderno', 'tecnologia'],
            'passado': ['passado', 'antes', 'história', 'lembrança'],
            'presente': ['presente', 'agora', 'atual', 'hoje'],
            'futuro': ['futuro', 'amanhã', 'depois', 'próximo'],
            'memória': ['memória', 'lembrar', 'esquecer', 'recordar'],
            'imaginação': ['imaginação', 'fantasia', 'sonhar', 'criar'],
            'realidade': ['realidade', 'verdade', 'fato', 'real'],
            'virtual': ['virtual', 'digital', 'online', 'internet'],
            'físico': ['físico', 'corpo', 'material', 'concreto'],
            'mental': ['mental', 'mente', 'psicológico', 'cerebral'],
            'espiritual': ['espiritual', 'alma', 'espírito', 'transcendente'],
            'social': ['social', 'sociedade', 'comunidade', 'público'],
            'individual': ['individual', 'pessoal', 'próprio', 'único'],
            'coletivo': ['coletivo', 'grupo', 'todos', 'junto'],
            'competição': ['competição', 'concorrer', 'rival', 'disputa'],
            'cooperação': ['cooperação', 'colaborar', 'ajudar', 'unir'],
            'liderança': ['líder', 'liderança', 'comando', 'dirigir'],
            'humildade': ['humilde', 'modesto', 'simples', 'discreto'],
            'orgulho': ['orgulho', 'altivo', 'soberbo', 'vaidoso'],
            'generosidade': ['generoso', 'bondade', 'caridade', 'dar'],
            'egoísmo': ['egoísta', 'interesseiro', 'ganancioso'],
            'honestidade': ['honesto', 'sincero', 'verdadeiro', 'íntegro'],
            'mentira': ['mentira', 'falso', 'enganar', 'iludir'],
            'justiça': ['justiça', 'justo', 'correto', 'direito'],
            'injustiça': ['injustiça', 'injusto', 'errado', 'parcial'],
            'liberdade': ['liberdade', 'livre', 'independente', 'solto'],
            'prisão': ['prisão', 'preso', 'cárcere', 'cadeia']
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
            ],
            'negativo': [
                "Entendo sua frustração. Vamos resolver isso juntos! 🤝",
                "Lamento que esteja com problemas. Como posso ajudar?",
                "Vamos encontrar uma solução! 💡",
                "Não se preocupe, vou te ajudar a resolver! 🛠️",
                "Compreendo sua situação. Vou fazer o possível para ajudar!",
                "Entendo que algo não está funcionando bem. Vamos consertar!"
            ],
            'comando': [
                "Para usar comandos, você pode usar `RXajuda` para ver a lista completa!",
                "Aqui estão os comandos disponíveis: use `RXajuda diversao` para jogos!",
                "Comandos úteis que você pode usar: `RXping`, `RXsaldo`, `RXjokenpo`!",
                "Para executar comandos, digite RX seguido do comando, como `RXticket`!",
                "Tenho mais de 200 comandos! Use `RXajuda` para explorar!",
                "Comandos são minha especialidade! `RXajuda` mostra tudo!"
            ],
            'diversão': [
                "Vamos nos divertir! 🎮 Use `RXjokenpo`, `RXquiz` ou `RXforca`!",
                "Hora da diversão! 🎪 Temos vários jogos: `RXdado`, `RXmoeda`!",
                "Ótima ideia! Vamos brincar! 🎊 Digite `RXajuda diversao`!",
                "Perfeito! Diversão é sempre boa! 🎯 Use `RXmeme` para rir!",
                "Adorei! Tenho mais de 40 comandos de diversão! 🎈",
                "Vamos animar esse servidor! 🎭 `RXpiada` para começar!"
            ],
            'eventos': [
                "Sobre eventos! 📅 Use `RXeventos` para ver eventos ativos!",
                "Os administradores podem criar eventos com `RXcriarevento`!",
                "Para participar de um evento, use `RXparticipar <id>`!",
                "Eventos são uma ótima forma de interagir! Use `RXajuda eventos`!",
                "Eventos deixam o servidor mais animado! 🎪",
                "Que tal participar dos próximos eventos? 🎊"
            ],
            'sorteio': [
                "Sorteios são emocionantes! 🎁 Admins podem criar com `RXcriarsorteio`!",
                "Para ver sorteios ativos, use `RXsorteios`! 🍀",
                "Participe dos sorteios para ganhar prêmios incríveis! 🏆",
                "Os sorteios tornam o servidor mais divertido! 🎪",
                "Boa sorte nos próximos sorteios! 🤞",
                "Que tal tentar a sorte? Veja `RXsorteios`! ✨"
            ],
            'tecnologia': [
                "Tecnologia é fascinante! 💻 Sobre o que quer saber?",
                "Programação é arte! 🎨 Em que linguagem está trabalhando?",
                "O mundo tech está sempre evoluindo! 🚀 Que interessante!",
                "Desenvolvimento é minha paixão! 👨‍💻 Como posso ajudar?",
                "A tecnologia nos conecta! 🌐 Vamos conversar sobre isso!",
                "Inovação tecnológica é o futuro! ⚡ Me conte mais!"
            ],
            'games': [
                "Games são incríveis! 🎮 Qual seu jogo favorito?",
                "Mundo gamer é diversão garantida! 🕹️ Vamos jogar algo aqui?",
                "Que jogo interessante! 🎯 Use `RXajuda diversao` para jogos!",
                "Gaming é vida! 🎪 Temos vários jogos no bot!",
                "Adoro conversar sobre games! 🏆 Me conte mais!",
                "E-sports estão crescendo muito! 📈 Que empolgante!"
            ]
        }

        # Tópicos expandidos para conversação natural
        self.topics = [
            "Que tal jogarmos algo? Tenho vários jogos!",
            "Como está seu dia hoje?",
            "Qual seu hobby favorito?",
            "Gosta de música? Qual estilo prefere?",
            "Já assistiu algum anime bom recentemente?",
            "Qual sua comida favorita?",
            "Pretende fazer algo especial no fim de semana?",
            "Como está o clima aí na sua cidade?",
            "Tem algum pet? Adoro animais!",
            "Qual o último filme que assistiu?",
            "Gosta de ler? Que tipo de livro prefere?",
            "Pratica algum esporte?",
            "Qual sua matéria favorita na escola?",
            "Tem algum sonho ou objetivo que quer alcançar?",
            "O que te faz mais feliz?",
            "Qual seu lugar favorito para relaxar?",
            "Gosta de viajar? Qual destino dos sonhos?",
            "Tem algum talento especial?",
            "Qual sua cor favorita e por quê?",
            "Prefere dia ou noite?",
            "Qual estação do ano prefere?",
            "Gosta de cozinhar?",
            "Tem alguma coleção?",
            "Qual sua música favorita no momento?",
            "Prefere praia ou montanha?",
            "Gosta de desenhar ou fazer arte?",
            "Qual seu jogo de tabuleiro favorito?",
            "Tem algum medo bobo?",
            "Qual sua memória mais feliz?",
            "O que te inspira?",
            "Gosta de tecnologia?",
            "Qual rede social usa mais?",
            "Tem algum ídolo ou pessoa que admira?",
            "Qual seu doce favorito?",
            "Prefere acordar cedo ou dormir tarde?",
            "Gosta de festas ou prefere lugares quietos?",
            "Qual seu super-herói favorito?",
            "Acredita em aliens?",
            "Gosta de horror ou prefere comédia?",
            "Qual sua pizza favorita?",
            "Tem alguma superstição?",
            "Gosta de chuva?",
            "Qual seu emoji mais usado?",
            "Tem algum apelido engraçado?",
            "Gosta de surpresas?",
            "Qual seu número da sorte?",
            "Prefere gatos ou cachorros?",
            "Gosta de acordar com sol ou com chuva?",
            "Qual seu programa de TV favorito?",
            "Tem alguma fobia específica?",
            "Gosta de aventuras ou rotina?",
            "Qual seu sabor de sorvete favorito?",
            "Acredita em fantasmas?",
            "Gosta de puzzles ou jogos de lógica?",
            "Qual sua bebida favorita?",
            "Tem algum ritual matinal?",
            "Gosta de fotografar?",
            "Qual seu meio de transporte preferido?",
            "Tem alguma meta para este ano?",
            "Gosta de surpresas de aniversário?",
            "Qual seu tipo de chocolate preferido?",
            "Acredita em sonhos premonitorios?",
            "Gosta de karaokê?",
            "Qual sua palavra favorita?",
            "Tem algum bordão ou frase que usa muito?",
            "Gosta de jogos de cartas?",
            "Qual seu tipo de clima favorito?",
            "Tem alguma tradição familiar especial?",
            "Gosta de improvisar ou prefere planos?",
            "Qual seu perfume ou cheiro favorito?",
            "Acredita em astrologia?",
            "Gosta de dançar?",
            "Qual seu tipo de música para relaxar?",
            "Tem algum lugar que te traz paz?",
            "Gosta de criar teorias sobre filmes/séries?",
            "Qual seu tipo de celebração favorita?",
            "Acredita que cores afetam o humor?",
            "Gosta de improvisar presentes?",
            "Qual seu tipo de memória preferido para guardar?",
            "Tem algum ritual de concentração?",
            "Gosta de histórias com plot twists?",
            "Qual seu tipo de silêncio favorito?",
            "Acredita que música tem poder de cura?",
            "Gosta de criar ou de consumir conteúdo?",
            "Qual seu tipo de conexão com outras pessoas?",
            "Tem algum lugar dos sonhos para morar?",
            "Gosta de mistérios não resolvidos?",
            "Qual seu tipo de aprendizado preferido?",
            "Acredita que cada pessoa tem uma missão?",
            "Gosta de reinventar tradições?",
            "Qual seu tipo de energia natural preferida?",
            "Tem alguma teoria sobre o universo?",
            "Gosta de conectar pontos entre ideias diferentes?",
            "Qual seu tipo de infinitude favorito para imaginar?",
            "Já pensou sobre o que te faz único no universo?",
            "Se pudesse viver em qualquer época, qual escolheria?",
            "Qual descoberta científica te impressiona mais?",
            "Tem alguma pergunta filosófica que sempre te intriga?",
            "Se pudesse ter uma conversa com alguém do passado, quem seria?",
            "Qual invenção mudou mais sua forma de viver?",
            "Tem alguma tradição que criou para si mesmo?",
            "Se pudesse aprender qualquer habilidade instantaneamente, qual seria?",
            "Qual mistério da vida mais te fascina?",
            "Tem alguma experiência que mudou sua perspectiva?",
            "Se pudesse viajar para qualquer lugar do universo, onde iria?",
            "Qual conceito abstrato consegue te emocionar?",
            "Tem alguma memória sensorial muito forte?",
            "Se pudesse resolver um problema mundial, qual escolheria?",
            "Qual aspecto da natureza humana te impressiona mais?",
            "Tem algum ritual que te conecta com algo maior?",
            "Se pudesse ter uma superpoder, qual seria?",
            "Qual forma de arte consegue te transportar?",
            "Tem alguma crença pessoal que guia suas decisões?",
            "Se pudesse desvendar qualquer código do universo, qual seria?",
            "Qual força da natureza te inspira mais?",
            "Tem alguma forma de meditação ou reflexão?",
            "Se pudesse explorar qualquer dimensão da realidade, qual seria?",
            "Qual aspecto da consciência te impressiona mais?",
            "Tem alguma experiência com sincronicidades?",
            "Se pudesse dialogar com qualquer forma de vida, qual escolheria?",
            "Qual conceito de tempo ressoa mais com você?",
            "Tem alguma forma de se conectar com o momento presente?",
            "Se pudesse desvendar qualquer código do universo, qual seria?",
            "Qual força invisível acredita que mais nos influencia?"
        ]

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

        # Verificar se são só emojis ou mensagem muito curta
        if len(message_content.strip()) <= 3 or message_content.strip() in ['😂', '😭', '😍', '🤔', '👍', '👎', '❤️', '🔥', '💯']:
            return random.choice([
                "Entendi! 😄 Como posso ajudar?",
                "Haha! 😊 Em que posso ser útil?",
                "Legal! 🎉 Vamos conversar?",
                "Interessante! 🤔 Me conte mais!",
                "Show! 🚀 O que quer fazer?",
                "Perfeito! ✨ Como posso ajudar hoje?"
            ])

        # Se não houver contexto específico, usar tópicos aleatórios
        if primary_context == 'geral':
            return f"{random.choice(self.topics)}\n\n💡 Use `RXajuda` para ver todos os comandos!"

        # Resposta baseada no contexto
        if primary_context in self.responses:
            base_response = random.choice(self.responses[primary_context])
        else:
            base_response = f"{random.choice(self.topics)}\n\nUse `RXajuda` para ver todos os comandos disponíveis!"

        # Adiciona informações contextuais baseado nos contextos detectados
        extras = []

        if 'comando' in contexts:
            extras.append("📚 Use `RXajuda` para ver todos os comandos!")

        if 'diversão' in contexts or 'games' in contexts:
            extras.append("🎮 Temos mais de 40 jogos: `RXjokenpo`, `RXquiz`, `RXforca`!")

        if 'eventos' in contexts:
            extras.append("📅 Para eventos: `RXeventos` ou `RXcriarevento`!")

        if 'sorteio' in contexts:
            extras.append("🎁 Para sorteios: `RXsorteios` ou `RXcriarsorteio` (admins)!")

        if 'ajuda' in contexts:
            extras.append("🆘 Para suporte: `RXticket <motivo>` ou `RXajuda`!")

        # Adicionar extras se houver
        if extras:
            base_response += f"\n\n{random.choice(extras)}"

        return base_response

ai_system = AdvancedAI()

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
    """Add XP with level calculation"""
    try:
        data = get_user_data(user_id)
        if not data:
            update_user_data(user_id, xp=amount, level=1)
            return False, 1

        current_xp = data[2]
        current_level = data[3]
        new_xp = current_xp + amount

        # Calculate new level
        new_level = int(math.sqrt(new_xp / 100)) + 1
        leveled_up = new_level > current_level

        update_user_data(user_id, xp=new_xp, level=new_level)
        return leveled_up, new_level
    except Exception as e:
        logger.error(f"Error adding XP: {e}")
        return False, 1

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
        elif key == 'author':
            embed.set_author(name=value.get('name'), icon_url=value.get('icon_url'))
        elif key == 'fields':
            for field in value:
                embed.add_field(name=field['name'], value=field['value'], inline=field.get('inline', True))

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

    # Verificar muitos emojis
    emoji_count = sum(1 for char in message_content if char in '😀😃😄😁😆😅😂🤣😊😇🙂🙃😉😌😍🥰😘😗😙😚😋😛😝😜🤪🤨🧐🤓😎🤩🥳😏😒😞😔😟😕🙁☹️😣😖😫😩🥺😢😭😤😠😡🤬🤯😳🥵🥶😱😨😰😥😓🤗🤔🤭🤫🤥😶😐😑😬🙄😯😦😧😮😲🥱😴🤤😪😵🤐🥴🤢🤮🤧😷🤒🤕🤑🤠😈👿👹👺🤡💩👻💀☠️👽👾🤖🎃😺😸😹😻😼😽🙀😿😾')
    if emoji_count > 10:
        violations.append("Spam de emojis")

    return violations

# Event handlers
@bot.event
async def on_ready():
    logger.info(f"🤖 RXbot está online! Conectado como {bot.user}")
    logger.info(f"📊 Conectado em {len(bot.guilds)} servidores")
    logger.info(f"👥 Servindo {len(set(bot.get_all_members()))} usuários únicos")
    try:
        channel = bot.get_channel(CHANNEL_ID_ALERTA)
        if channel:
            await channel.send("⚠️ O bot foi reiniciado automaticamente e já está online!")
    except Exception as e:
        logger.error(f"Erro ao enviar alerta de reinício: {e}")

    @bot.event
    async def on_disconnect():
        try:
            channel = bot.get_channel(CHANNEL_ID_ALERTA)
            if channel:
                await channel.send("❌ O bot foi **desconectado** do Discord!")
        except Exception as e:
            logger.error(f"Erro ao enviar alerta de desconexão: {e}")

    @bot.event
    async def on_resumed():
        try:
            channel = bot.get_channel(CHANNEL_ID_ALERTA)
            if channel:
                await channel.send("🔄 O bot **reconectou** ao Discord!")
        except Exception as e:
            logger.error(f"Erro ao enviar alerta de reconexão: {e}")

    # Update global stats
    global_stats['total_users'] = len(set(bot.get_all_members()))
    global_stats['total_channels'] = len(list(bot.get_all_channels()))

    # Start background tasks
    update_status.start()
    backup_database.start()
    check_reminders.start()
    check_giveaways.start()

    # Set initial status
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(bot.guilds)} servidores | RXping para começar!"
        )
    )

    print("🔥 RXbot está online! Pronto para comandar!")

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
async def on_message(message):
    if message.author.bot:
        return

    global_stats['messages_processed'] += 1

    # Verificar violações automáticas
    violations = check_auto_violations(message.content)
    if violations and message.guild:
        try:
            # Aplicar warn automático
            user_data = get_user_data(message.author.id)
            if not user_data:
                update_user_data(message.author.id)
                user_data = get_user_data(message.author.id)

            warnings = user_data[15] + 1
            update_user_data(message.author.id, warnings=warnings)

            # Log da moderação
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason)
                    VALUES (?, ?, ?, ?, ?)
                ''', (message.guild.id, message.author.id, bot.user.id, 'auto_warn', f"Violação automática: {', '.join(violations)}"))
                conn.commit()
                conn.close()

            # Deletar mensagem
            try:
                await message.delete()
            except:
                pass

            # Notificar usuário
            embed = create_embed(
                "⚠️ Warning Automático",
                f"{message.author.mention} recebeu um warning automático!\n"
                f"**Motivo:** {', '.join(violations)}\n"
                f"**Warnings:** {warnings}/5\n"
                f"**Mensagem deletada automaticamente**",
                color=0xff6b6b
            )

            warning_msg = await message.channel.send(embed=embed)
            await asyncio.sleep(10)
            try:
                await warning_msg.delete()
            except:
                pass

            # Aplicar punições se necessário
            if warnings >= 5:
                try:
                    await message.author.ban(reason=f"5+ Warnings automáticos")
                except:
                    pass
            elif warnings >= 3:
                try:
                    timeout_until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
                    await message.author.timeout(timeout_until, reason=f"3+ Warnings automáticos")
                except:
                    pass

        except Exception as e:
            logger.error(f"Error in auto-moderation: {e}")

    # Add XP for message (with error handling)
    if not message.content.startswith(tuple(bot.command_prefix)):
        try:
            leveled_up, new_level = add_xp(message.author.id, XP_PER_MESSAGE)
            if leveled_up and new_level % 5 == 0:
                embed = create_embed(
                    "🎉 Level Up!",
                    f"{message.author.mention} subiu para o nível **{new_level}**! 🚀",
                    color=0xffd700
                )
                await message.channel.send(embed=embed, delete_after=10)
        except Exception as e:
            logger.error(f"Error adding XP: {e}")

    # Anti-spam system
    user_id = message.author.id
    guild_id = message.guild.id if message.guild else None

    if guild_id:
        spam_tracker[f"{guild_id}_{user_id}"].append(time.time())
        recent_messages = [t for t in spam_tracker[f"{guild_id}_{user_id}"] if time.time() - t < 10]
        spam_tracker[f"{guild_id}_{user_id}"] = deque(recent_messages, maxlen=10)

        if len(recent_messages) >= 5:
            try:
                timeout_until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
                await message.author.timeout(timeout_until, reason="Spam detectado")
                embed = create_embed(
                    "🚫 Anti-Spam",
                    f"{message.author.mention} foi mutado por 5 minutos por spam.",
                    color=0xff0000
                )
                await message.channel.send(embed=embed, delete_after=10)
            except:
                pass

    # AI conversation system
    if bot.user.mentioned_in(message) and not message.author.bot:
        conversation_memory[message.author.id].append({
            'content': message.content,
            'timestamp': time.time(),
            'sentiment': 'neutral'
        })

        user_data = get_user_data(message.author.id)
        ai_response = ai_system.generate_response(message.content, user_data)

        embed = create_embed(
            "🤖 RXbot IA Avançada",
            ai_response,
            color=0x7289da
        )
        embed.set_footer(text=f"Conversando com {message.author.display_name} • 200+ tópicos disponíveis")
        await message.channel.send(embed=embed)

    await bot.process_commands(message)

# Background tasks
@tasks.loop(minutes=5)
async def update_status():
    statuses = [
        f"👥 {len(set(bot.get_all_members()))} usuários",
        f"🏠 {len(bot.guilds)} servidores",
        f"💬 {global_stats['messages_processed']} mensagens",
        "🚀 RXping para começar!",
        "💰 Sistema de economia ativo",
        "🎮 200+ comandos disponíveis",
        "🛡️ Moderação automática ligada",
        "🎪 Eventos e diversão!",
        "🎁 Sistema de sorteios ativo",
        "🤖 IA com 200+ tópicos"
    ]

    status = random.choice(statuses)
    activity_type = random.choice([
        discord.ActivityType.watching,
        discord.ActivityType.listening,
        discord.ActivityType.playing
    ])

    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(type=activity_type, name=status)
    )

@tasks.loop(hours=6)
async def backup_database():
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy('rxbot.db', f'backup_rxbot_{timestamp}.db')
        logger.info(f"✅ Database backup created: backup_rxbot_{timestamp}.db")

        # Clean old backups (keep only last 5)
        backup_files = [f for f in os.listdir('.') if f.startswith('backup_rxbot_')]
        backup_files.sort(reverse=True)
        for old_backup in backup_files[5:]:
            try:
                os.remove(old_backup)
            except:
                pass

    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")

@tasks.loop(minutes=1)
async def check_reminders():
    """Check for due reminders"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            current_time = datetime.datetime.now()
            cursor.execute('''
                SELECT id, user_id, guild_id, channel_id, reminder_text
                FROM reminders
                WHERE remind_time <= ?
            ''', (current_time,))

            due_reminders = cursor.fetchall()

            for reminder in due_reminders:
                try:
                    reminder_id, user_id, guild_id, channel_id, text = reminder

                    channel = bot.get_channel(channel_id)
                    if channel:
                        user = bot.get_user(user_id)
                        embed = create_embed(
                            "⏰ Lembrete!",
                            f"{user.mention if user else 'Usuário'}, você pediu para ser lembrado:\n\n**{text}**",
                            color=0xffaa00
                        )
                        await channel.send(embed=embed)

                    cursor.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))

                except Exception as e:
                    logger.error(f"Error sending reminder: {e}")

            conn.commit()
            conn.close()

    except Exception as e:
        logger.error(f"Error checking reminders: {e}")

@tasks.loop(minutes=1)
async def check_giveaways():
    """Check for finished giveaways"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            current_time = datetime.datetime.now()
            cursor.execute('''
                SELECT id, guild_id, channel_id, creator_id, title, prize, winners_count, participants, message_id
                FROM giveaways
                WHERE end_time <= ? AND status = 'active'
            ''', (current_time,))

            finished_giveaways = cursor.fetchall()

            for giveaway in finished_giveaways:
                try:
                    gw_id, guild_id, channel_id, creator_id, title, prize, winners_count, participants_json, message_id = giveaway

                    channel = bot.get_channel(channel_id)
                    if not channel:
                        continue

                    participants = json.loads(participants_json) if participants_json else []

                    if len(participants) == 0:
                        embed = create_embed(
                            "😔 Sorteio Cancelado",
                            f"**{title}**\n\nNenhum participante! O sorteio foi cancelado.",
                            color=0xff6b6b
                        )
                        await channel.send(embed=embed)
                    else:
                        # Selecionar vencedores
                        actual_winners_count = min(winners_count, len(participants))
                        winners = random.sample(participants, actual_winners_count)

                        winner_mentions = []
                        for winner_id in winners:
                            user = bot.get_user(winner_id)
                            if user:
                                winner_mentions.append(user.mention)

                        embed = create_embed(
                            "🎉 Sorteio Finalizado!",
                            f"""**{title}**

    🏆 **Vencedor(es):** {', '.join(winner_mentions)}
    🎁 **Prêmio:** {prize}
    👥 **Total de participantes:** {len(participants)}

    Parabéns aos vencedores! 🎊""",
                            color=0x00ff00
                        )

                        await channel.send(embed=embed)

                        # Tentar encontrar e editar a mensagem original
                        try:
                            original_msg = await channel.fetch_message(message_id)
                            ended_embed = create_embed(
                                "🎁 Sorteio Finalizado",
                                f"**{title}**\n\n🏆 Vencedores: {', '.join(winner_mentions)}\n🎁 Prêmio: {prize}",
                                color=0xff6b6b
                            )
                            await original_msg.edit(embed=ended_embed)
                        except:
                            pass

                    # Marcar como finalizado
                    cursor.execute('UPDATE giveaways SET status = ? WHERE id = ?', ('finished', gw_id))

                except Exception as e:
                    logger.error(f"Error finishing giveaway: {e}")

            conn.commit()
            conn.close()

    except Exception as e:
        logger.error(f"Error checking giveaways: {e}")

# ============ SISTEMA DE SORTEIOS COMPLETO ============
@bot.command(name='criarsorteio', aliases=['giveaway', 'sortear'])
@commands.has_permissions(administrator=True)
async def create_giveaway(ctx, *, giveaway_data=None):
    """[ADMIN] Criar um novo sorteio"""
    if not giveaway_data:
        embed = create_embed(
            "🎁 Como criar um sorteio",
            """**Formato:** `RXcriarsorteio Título | Prêmio | Duração | Vencedores`

    **Exemplo:**
    `RXcriarsorteio iPhone 15 Pro | iPhone 15 Pro Max 256GB | 24h | 1`
    `RXcriarsorteio Nitro Discord | 3 meses de Nitro | 7d | 3`

    **Durações:** 30m, 2h, 1d, 7d, etc.
    **Vencedores:** Número de pessoas que vão ganhar""",
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

        # Confirmação
        confirm_embed = create_embed(
            "✅ Sorteio Criado!",
            f"O sorteio **{title}** foi criado com sucesso!\nTerminará em {amount}{unit}.",
            color=0x00ff00
        )
        await ctx.send(embed=confirm_embed, delete_after=10)

    except ValueError:
        embed = create_embed("❌ Duração inválida", "Use números válidos: 30m, 2h, 1d, etc.", color=0xff0000)
        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"Error creating giveaway: {e}")

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

        for giveaway in giveaways[:5]:  # Show only first 5
            title, prize, end_time_str, winners_count, participants_json = giveaway
            participants = json.loads(participants_json) if participants_json else []

            try:
                end_time = datetime.datetime.fromisoformat(end_time_str)
                time_left = end_time - datetime.datetime.now()

                if time_left.total_seconds() > 0:
                    time_left_str = format_time(int(time_left.total_seconds()))
                else:
                    time_left_str = "Finalizado"
            except:
                time_left_str = "Erro no tempo"

            embed.add_field(
                name=f"🎊 {title}",
                value=f"🎁 **Prêmio:** {prize}\n"
                      f"🏆 **Vencedores:** {winners_count}\n"
                      f"👥 **Participantes:** {len(participants)}\n"
                      f"⏰ **Termina em:** {time_left_str}",
                inline=False
            )

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Error listing giveaways: {e}")

@bot.event
async def on_reaction_add(reaction, user):
    """Handle giveaway participation"""
    if user.bot:
        return

    if str(reaction.emoji) == "🎉":
        try:
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT id, participants FROM giveaways
                    WHERE message_id = ? AND status = 'active'
                ''', (reaction.message.id,))

                giveaway = cursor.fetchone()

                if giveaway:
                    gw_id, participants_json = giveaway
                    participants = json.loads(participants_json) if participants_json else []

                    if user.id not in participants:
                        participants.append(user.id)

                        cursor.execute('''
                            UPDATE giveaways SET participants = ? WHERE id = ?
                        ''', (json.dumps(participants), gw_id))

                        conn.commit()

                        # Enviar confirmação via DM
                        try:
                            embed = create_embed(
                                "✅ Participação Confirmada!",
                                "Você foi inscrito no sorteio com sucesso!\nBoa sorte! 🍀",
                                color=0x00ff00
                            )
                            await user.send(embed=embed)
                        except:
                            pass

                conn.close()

        except Exception as e:
            logger.error(f"Error handling giveaway participation: {e}")

@bot.event
async def on_reaction_remove(reaction, user):
    """Handle giveaway departure"""
    if user.bot:
        return

    if str(reaction.emoji) == "🎉":
        try:
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT id, participants FROM giveaways
                    WHERE message_id = ? AND status = 'active'
                ''', (reaction.message.id,))

                giveaway = cursor.fetchone()

                if giveaway:
                    gw_id, participants_json = giveaway
                    participants = json.loads(participants_json) if participants_json else []

                    if user.id in participants:
                        participants.remove(user.id)

                        cursor.execute('''
                            UPDATE giveaways SET participants = ? WHERE id = ?
                        ''', (json.dumps(participants), gw_id))

                        conn.commit()

                conn.close()

        except Exception as e:
            logger.error(f"Error handling giveaway departure: {e}")

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

# ============ COMANDOS DE DIVERSÃO ============
@bot.command(name='jokenpo', aliases=['pedrapapeltesoura', 'ppt'])
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
        # Dar recompensa
        data = get_user_data(ctx.author.id)
        if data:
            new_coins = data[1] + 10
            update_user_data(ctx.author.id, coins=new_coins)
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

@bot.command(name='dado', aliases=['dice', 'roll'])
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

@bot.command(name='moeda', aliases=['coin', 'flip'])
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

@bot.command(name='8ball', aliases=['bola8', 'magicball'])
async def magic_8ball(ctx, *, pergunta=None):
    """Bola mágica 8"""
    if not pergunta:
        embed = create_embed("❌ Pergunta necessária", "Use: `RX8ball Vou passar na prova?`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    respostas = [
        "Sim, definitivamente!",
        "É certo que sim!",
        "Sem dúvida!",
        "Sim, com certeza!",
        "Você pode confiar nisso!",
        "Como eu vejo, sim!",
        "Provavelmente sim!",
        "Perspectiva boa!",
        "Sinais apontam que sim!",
        "Resposta nebulosa, tente novamente!",
        "Pergunte novamente mais tarde!",
        "Melhor não te dizer agora!",
        "Não consigo prever agora!",
        "Concentre-se e pergunte novamente!",
        "Não conte com isso!",
        "Minha resposta é não!",
        "Minhas fontes dizem que não!",
        "Perspectiva não muito boa!",
        "Muito duvidoso!"
    ]

    resposta = random.choice(respostas)
    embed = create_embed(
        "🔮 Bola Mágica 8",
        f"**Pergunta:** {pergunta}\n**Resposta:** {resposta}",
        color=0x7289da
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
        "Por que os programadores preferem dark mode? Porque light atrai bugs!",
        "O que a zero falou para o oito? Que cinto maneiro!",
        "Por que o JavaScript foi ao psicólogo? Porque estava com problemas de undefined!",
        "O que um núcleo falou para o outro? Para de ser radioativo!",
        "Por que o HTML e o CSS terminaram? Porque não tinham química!",
        "O que o Git disse para o SVN? Você está desatualizado!"
    ]

    piada = random.choice(piadas)
    embed = create_embed("😂 Piada do RXbot", piada, color=0xffaa00)
    await ctx.send(embed=embed)

@bot.command(name='fato', aliases=['fact'])
async def fato(ctx):
    """Fato interessante"""
    fatos = [
        "As abelhas podem voar mais alto que o Monte Everest!",
        "Um polvo tem três corações e sangue azul!",
        "Existem mais árvores na Terra do que estrelas na Via Láctea!",
        "O coração de uma baleia azul é tão grande quanto um carro!",
        "Um grupo de flamingos é chamado de 'flamboyance'!",
        "As formigas podem levantar 50 vezes o próprio peso!",
        "A velocidade da luz é de aproximadamente 300.000 km/s!",
        "O cérebro humano usa cerca de 20% da energia do corpo!",
        "Uma nuvem pode pesar mais de um milhão de quilos!",
        "Os golfinhos chamam uns aos outros por nomes!"
    ]

    fato = random.choice(fatos)
    embed = create_embed("🤓 Fato Interessante", fato, color=0x7289da)
    await ctx.send(embed=embed)

@bot.command(name='quiz')
async def quiz(ctx):
    """Jogo de quiz"""
    perguntas = [
        {"pergunta": "Qual é a capital do Brasil?", "resposta": "brasilia", "opcoes": ["A) São Paulo", "B) Rio de Janeiro", "C) Brasília", "D) Salvador"]},
        {"pergunta": "Quantos continentes existem?", "resposta": "7", "opcoes": ["A) 5", "B) 6", "C) 7", "D) 8"]},
        {"pergunta": "Qual o maior planeta do sistema solar?", "resposta": "jupiter", "opcoes": ["A) Terra", "B) Marte", "C) Júpiter", "D) Saturno"]},
        {"pergunta": "Quem pintou a Mona Lisa?", "resposta": "leonardo", "opcoes": ["A) Picasso", "B) Leonardo da Vinci", "C) Van Gogh", "D) Monet"]},
        {"pergunta": "Qual é o elemento químico H?", "resposta": "hidrogenio", "opcoes": ["A) Hélio", "B) Hidrogênio", "C) Ferro", "D) Ouro"]}
    ]

    pergunta = random.choice(perguntas)

    embed = create_embed(
        "🧠 Quiz RXbot",
        f"**{pergunta['pergunta']}**\n\n" + "\n".join(pergunta['opcoes']) + "\n\nDigite sua resposta no chat!",
        color=0x7289da
    )

    await ctx.send(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        resposta = await bot.wait_for('message', timeout=30.0, check=check)
        if pergunta['resposta'].lower() in resposta.content.lower():
            # Dar recompensa
            data = get_user_data(ctx.author.id)
            if data:
                new_coins = data[1] + 25
                update_user_data(ctx.author.id, coins=new_coins)

            embed = create_embed("✅ Correto!", f"Parabéns! Você ganhou 25 moedas! 🪙", color=0x00ff00)
        else:
            embed = create_embed("❌ Incorreto!", f"A resposta correta era: {pergunta['resposta']}", color=0xff0000)

        await ctx.send(embed=embed)
    except asyncio.TimeoutError:
        embed = create_embed("⏰ Tempo esgotado!", "Você demorou muito para responder!", color=0xff6b6b)
        await ctx.send(embed=embed)

@bot.command(name='forca')
async def hangman(ctx):
    """Jogo da forca"""
    palavras = ["PYTHON", "DISCORD", "PROGRAMACAO", "COMPUTADOR", "INTERNET", "TECNOLOGIA"]
    palavra = random.choice(palavras)
    progresso = ["_"] * len(palavra)
    tentativas = 6
    letras_usadas = []

    embed = create_embed(
        "🎪 Jogo da Forca",
        f"```\n{' '.join(progresso)}\n```\n**Tentativas restantes:** {tentativas}\n**Letras usadas:** {', '.join(letras_usadas) if letras_usadas else 'Nenhuma'}",
        color=0x7289da
    )

    message = await ctx.send(embed=embed)

    # Simplified hangman - just show the answer for demo
    embed = create_embed(
        "🎪 Jogo da Forca",
        f"A palavra era: **{palavra}**\nUse `RXforca` para jogar novamente!",
        color=0x7289da
    )
    await ctx.send(embed=embed)

@bot.command(name='meme')
async def meme(ctx):
    """Gera memes aleatórios"""
    memes = [
        "https://i.imgflip.com/1bij.jpg",
        "https://i.imgflip.com/5c7lwq.jpg",
        "https://i.imgflip.com/25w3.jpg"
    ]
    embed = create_embed("😂 Meme Aleatório", color=0xffaa00)
    embed.set_image(url=random.choice(memes))
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

@bot.command(name='cores', aliases=['colors'])
async def colors(ctx):
    """Mostra cores em hexadecimal"""
    cores = [
        ("Vermelho", "#FF0000", 0xFF0000),
        ("Verde", "#00FF00", 0x00FF00),
        ("Azul", "#0000FF", 0x0000FF),
        ("Amarelo", "#FFFF00", 0xFFFF00),
        ("Roxo", "#800080", 0x800080),
        ("Rosa", "#FFC0CB", 0xFFC0CB)
    ]

    cor = random.choice(cores)
    embed = create_embed(f"🎨 Cor: {cor[0]}", f"**Hex:** {cor[1]}", color=cor[2])
    await ctx.send(embed=embed)

# ============ COMANDOS DE ECONOMIA ============
@bot.command(name='saldo', aliases=['balance', 'bal', 'money', 'coins'])
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

    if data is None:
        logger.error(f"Could not retrieve or create user data for user ID: {user_id}")
        embed = create_embed(
            "❌ Erro",
            "Não foi possível processar sua solicitação. Tente novamente mais tarde.",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return

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

    # Calculate reward
    total_reward = DAILY_REWARD

    # Update user data
    new_coins = data[1] + total_reward

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
        f"""**Recompensa:** {total_reward:,} moedas
    **Novo saldo:** {new_coins:,} moedas

    🔥 *Continue coletando diariamente!*""",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name='transferir', aliases=['transfer', 'pay'])
async def transfer_money(ctx, user: discord.Member, amount: int):
    """Transfere dinheiro para outro usuário"""
    if user == ctx.author:
        embed = create_embed("❌ Impossível", "Você não pode transferir para si mesmo!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if amount <= 0:
        embed = create_embed("❌ Valor inválido", "O valor deve ser positivo!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    sender_data = get_user_data(ctx.author.id)
    if not sender_data or sender_data[1] < amount:
        embed = create_embed("❌ Saldo insuficiente", "Você não tem dinheiro suficiente!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    # Transfer money
    receiver_data = get_user_data(user.id)
    if not receiver_data:
        update_user_data(user.id)
        receiver_data = get_user_data(user.id)

    new_sender_coins = sender_data[1] - amount
    new_receiver_coins = receiver_data[1] + amount

    update_user_data(ctx.author.id, coins=new_sender_coins)
    update_user_data(user.id, coins=new_receiver_coins)

    embed = create_embed(
        "💸 Transferência Realizada",
        f"{ctx.author.mention} transferiu **{amount:,} moedas** para {user.mention}!",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name='loja', aliases=['shop', 'store'])
async def shop(ctx):
    """Loja virtual"""
    items = [
        {"name": "🎭 Emoji Personalizado", "price": 5000, "desc": "Crie um emoji personalizado"},
        {"name": "🌈 Cor Personalizada", "price": 10000, "desc": "Cor personalizada no seu perfil"},
        {"name": "👑 Título VIP", "price": 25000, "desc": "Título especial VIP"},
        {"name": "🎪 Evento Privado", "price": 50000, "desc": "Organize um evento privado"},
        {"name": "🤖 Bot Personalizado", "price": 100000, "desc": "Configure o bot para você"}
    ]

    embed = create_embed("🛒 Loja RXbot", "Itens disponíveis para compra:", color=0x7289da)

    for i, item in enumerate(items, 1):
        embed.add_field(
            name=f"{i}. {item['name']} - {item['price']:,} moedas",
            value=item['desc'],
            inline=False
        )

    embed.set_footer(text="Use RXcomprar <número> para comprar um item")
    await ctx.send(embed=embed)

@bot.command(name='comprar', aliases=['buy'])
async def buy_item(ctx, item_id: int):
    """Compra item da loja"""
    items = [
        {"name": "🎭 Emoji Personalizado", "price": 5000},
        {"name": "🌈 Cor Personalizada", "price": 10000},
        {"name": "👑 Título VIP", "price": 25000},
        {"name": "🎪 Evento Privado", "price": 50000},
        {"name": "🤖 Bot Personalizado", "price": 100000}
    ]

    if item_id < 1 or item_id > len(items):
        embed = create_embed("❌ Item inválido", f"Escolha um item de 1 a {len(items)}", color=0xff0000)
        await ctx.send(embed=embed)
        return

    item = items[item_id - 1]
    user_data = get_user_data(ctx.author.id)

    if not user_data or user_data[1] < item['price']:
        embed = create_embed("❌ Saldo insuficiente", f"Você precisa de {item['price']:,} moedas para comprar este item!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    new_coins = user_data[1] - item['price']
    update_user_data(ctx.author.id, coins=new_coins)

    embed = create_embed(
        "🎉 Compra Realizada!",
        f"Você comprou: **{item['name']}**\n**Preço:** {item['price']:,} moedas\n**Saldo restante:** {new_coins:,} moedas",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name='trabalhar', aliases=['work'])
async def work(ctx):
    """Trabalhe para ganhar dinheiro"""
    user_data = get_user_data(ctx.author.id)

    trabalhos = [
        {"nome": "Programador", "min": 20, "max": 80},
        {"nome": "Designer", "min": 15, "max": 60},
        {"nome": "Streamer", "min": 10, "max": 45},
        {"nome": "YouTuber", "min": 12, "max": 50},
        {"nome": "Gamer", "min": 8, "max": 35}
    ]

    trabalho = random.choice(trabalhos)
    ganho = random.randint(trabalho["min"], trabalho["max"])

    if not user_data:
        update_user_data(ctx.author.id)
        user_data = get_user_data(ctx.author.id)

    new_coins = user_data[1] + ganho
    update_user_data(ctx.author.id, coins=new_coins)

    embed = create_embed(
        "💼 Trabalho Concluído!",
        f"Você trabalhou como **{trabalho['nome']}** e ganhou **{ganho:,} moedas**!\n"
        f"**Novo saldo:** {new_coins:,} moedas",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

# ============ COMANDOS DE UTILIDADES ============
@bot.command(name='resetmemoria', aliases=['clearmemory', 'limparmente'])
async def reset_memory(ctx, user: discord.Member = None):
    """Reseta a memória de conversas da IA"""
    target = user or ctx.author

    # Se especificou outro usuário, precisa ser admin
    if user and user != ctx.author:
        if not ctx.author.guild_permissions.administrator:
            embed = create_embed(
                "❌ Sem permissão",
                "Apenas administradores podem resetar a memória de outros usuários!",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return

    # Limpar memória de conversas
    if target.id in conversation_memory:
        conversation_memory[target.id].clear()

    if target.id in user_personalities:
        user_personalities[target.id].clear()

    embed = create_embed(
        "🧠 Memória Resetada",
        f"A memória de conversas de **{target.display_name}** foi limpa!\n"
        f"A IA não se lembrará mais das conversas anteriores.\n"
        f"**Executado por:** {ctx.author.mention}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name='vermemoria', aliases=['showmemory', 'memoria'])
async def show_memory(ctx):
    """Mostra estatísticas da memória da IA"""
    user_id = ctx.author.id

    memory_count = len(conversation_memory[user_id]) if user_id in conversation_memory else 0
    personality_data = len(user_personalities[user_id]) if user_id in user_personalities else 0

    embed = create_embed(
        "🧠 Status da Memória IA",
        f"""**Suas conversas armazenadas:** {memory_count}/50
    **Dados de personalidade:** {personality_data} itens

    **Comandos disponíveis:**
    • `RXresetmemoria` - Limpar sua memória
    • `RXresetmemoria @user` - Limpar memória de outro usuário (admin)

    *A IA usa essas informações para conversas mais naturais!*""",
        color=0x7289da
    )
    await ctx.send(embed=embed)

# ============ COMANDOS ADMINISTRATIVOS ============
@bot.command(name='addcoins', aliases=['darcoins', 'adicionarcoins'])
@commands.has_permissions(administrator=True)
async def add_coins(ctx, user: discord.Member, amount: int):
    """[ADMIN] Adiciona RXcoins para um usuário"""
    if amount <= 0:
        embed = create_embed("❌ Valor inválido", "O valor deve ser positivo!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    # Verificar se o usuário existe no banco de dados
    user_data = get_user_data(user.id)
    if not user_data:
        update_user_data(user.id)
        user_data = get_user_data(user.id)

    new_coins = user_data[1] + amount
    update_user_data(user.id, coins=new_coins)

    embed = create_embed(
        "💰 RXcoins Adicionadas",
        f"**{amount:,} RXcoins** foram adicionadas para {user.mention}!\n"
        f"**Novo saldo:** {new_coins:,} RXcoins\n"
        f"**Administrador:** {ctx.author.mention}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

    # Log da transação
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (user.id, ctx.guild.id, 'admin_add', amount, f'Adicionado por {ctx.author.name}'))
            conn.commit()
            conn.close()
    except Exception as e:
        logger.error(f"Error logging transaction: {e}")

@bot.command(name='removecoins', aliases=['tirarcoins', 'removercoins'])
@commands.has_permissions(administrator=True)
async def remove_coins(ctx, user: discord.Member, amount: int):
    """[ADMIN] Remove RXcoins de um usuário"""
    if amount <= 0:
        embed = create_embed("❌ Valor inválido", "O valor deve ser positivo!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    user_data = get_user_data(user.id)
    if not user_data:
        embed = create_embed("❌ Usuário não encontrado", "Este usuário não tem dados no sistema!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    current_coins = user_data[1]
    if current_coins < amount:
        embed = create_embed(
            "⚠️ Saldo insuficiente",
            f"{user.display_name} tem apenas {current_coins:,} RXcoins!\n"
            f"Não é possível remover {amount:,} RXcoins.",
            color=0xffaa00
        )
        await ctx.send(embed=embed)
        return

    new_coins = current_coins - amount
    update_user_data(user.id, coins=new_coins)

    embed = create_embed(
        "💸 RXcoins Removidas",
        f"**{amount:,} RXcoins** foram removidas de {user.mention}!\n"
        f"**Novo saldo:** {new_coins:,} RXcoins\n"
        f"**Administrador:** {ctx.author.mention}",
        color=0xff6b6b
    )
    await ctx.send(embed=embed)

    # Log da transação
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (user.id, ctx.guild.id, 'admin_remove', -amount, f'Removido por {ctx.author.name}'))
            conn.commit()
            conn.close()
    except Exception as e:
        logger.error(f"Error logging transaction: {e}")

@bot.command(name='setcoins', aliases=['definircoins'])
@commands.has_permissions(administrator=True)
async def set_coins(ctx, user: discord.Member, amount: int):
    """[ADMIN] Define a quantidade exata de RXcoins de um usuário"""
    if amount < 0:
        embed = create_embed("❌ Valor inválido", "O valor não pode ser negativo!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    user_data = get_user_data(user.id)
    if not user_data:
        update_user_data(user.id)

    update_user_data(user.id, coins=amount)

    embed = create_embed(
        "🎯 RXcoins Definidas",
        f"O saldo de {user.mention} foi definido para **{amount:,} RXcoins**!\n"
        f"**Administrador:** {ctx.author.mention}",
        color=0x7289da
    )
    await ctx.send(embed=embed)

    # Log da transação
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO transactions (user_id, guild_id, type, amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (user.id, ctx.guild.id, 'admin_set', amount, f'Definido por {ctx.author.name}'))
            conn.commit()
            conn.close()
    except Exception as e:
        logger.error(f"Error logging transaction: {e}")

@bot.command(name='limpartotalmemoria', aliases=['cleartotalmemory', 'resetbot'])
@commands.has_permissions(administrator=True)
async def clear_total_memory(ctx):
    """[ADMIN] Limpa toda a memória do bot (todas as conversas)"""
    # Confirmar ação
    embed = create_embed(
        "⚠️ Confirmação Necessária",
        "**ATENÇÃO:** Esta ação irá apagar TODA a memória conversacional do bot!\n"
        "Isso inclui conversas de todos os usuários.\n\n"
        "Digite `CONFIRMAR` para prosseguir ou qualquer outra coisa para cancelar:",
        color=0xff6b6b
    )
    await ctx.send(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        response = await bot.wait_for('message', timeout=30.0, check=check)

        if response.content.upper() == 'CONFIRMAR':
            # Limpar toda a memória
            conversation_memory.clear()
            user_personalities.clear()

            embed = create_embed(
                "🧠 Memória Total Limpa",
                "✅ Toda a memória conversacional do bot foi apagada!\n"
                "🔄 O bot agora está com a mente \"fresca\".\n"
                f"**Executado por:** {ctx.author.mention}",
                color=0x00ff00
            )
            await ctx.send(embed=embed)

            # Log da ação
            logger.info(f"Total memory cleared by {ctx.author.name} ({ctx.author.id}) in guild {ctx.guild.name}")

        else:
            embed = create_embed(
                "❌ Ação Cancelada",
                "A limpeza total da memória foi cancelada.",
                color=0xffaa00
            )
            await ctx.send(embed=embed)

    except asyncio.TimeoutError:
        embed = create_embed(
            "⏰ Tempo Esgotado",
            "A confirmação não foi recebida. Ação cancelada.",
            color=0xff6b6b
        )
        await ctx.send(embed=embed)

@bot.command(name='statusmemoria', aliases=['memorystatus'])
@commands.has_permissions(administrator=True)
async def memory_status(ctx):
    """[ADMIN] Mostra estatísticas completas da memória do bot"""
    total_users = len(conversation_memory)
    total_conversations = sum(len(memory) for memory in conversation_memory.values())
    total_personalities = sum(len(personality) for personality in user_personalities.values())

    # Encontrar usuário com mais conversas
    if conversation_memory:
        most_active_user_id = max(conversation_memory.keys(), key=lambda k: len(conversation_memory[k]))
        most_active_user = bot.get_user(most_active_user_id)
        most_conversations = len(conversation_memory[most_active_user_id])
    else:
        most_active_user = None
        most_conversations = 0

    embed = create_embed(
        "🧠 Status Global da Memória IA",
        f"""**📊 Estatísticas Gerais:**
    • **Usuários com memória:** {total_users}
    • **Total de conversas:** {total_conversations}
    • **Dados de personalidade:** {total_personalities}

    **🏆 Usuário mais ativo:**
    • **Nome:** {most_active_user.display_name if most_active_user else 'Nenhum'}
    • **Conversas:** {most_conversations}

    **⚙️ Comandos Admin:**
    • `RXlimpartotalmemoria` - Limpar toda memória
    • `RXresetmemoria @user` - Limpar memória específica
    • `RXstatusmemoria` - Ver estatísticas da memória

    **💾 Limite por usuário:** 50 conversas""",
        color=0x7289da
    )

    embed.set_footer(text=f"Solicitado por {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command(name='calc', aliases=['calcular'])
async def calculator(ctx, *, expressao=None):
    """Calculadora simples"""
    if not expressao:
        embed = create_embed("❌ Expressão necessária", "Use: `RXcalc 2 + 2`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        # Sanitize expression for safety
        allowed_chars = "0123456789+-*/()."
        clean_expr = ''.join(c for c in expressao if c in allowed_chars or c.isspace())

        resultado = eval(clean_expr)
        embed = create_embed(
            "🧮 Calculadora",
            f"**Expressão:** {expressao}\n**Resultado:** {resultado}",
            color=0x7289da
        )
    except:
        embed = create_embed("❌ Expressão inválida", "Verifique a sintaxe da expressão", color=0xff0000)

    await ctx.send(embed=embed)

@bot.command(name='tempo', aliases=['time'])
async def current_time(ctx, *, timezone=None):
    """Mostra hora atual"""
    if timezone:
        embed = create_embed(
            "⏰ Hora Atual",
            f"Para mostrar horário de {timezone}, conecte uma API de timezone!",
            color=0x7289da
        )
    else:
        now = datetime.datetime.now()
        embed = create_embed(
            "⏰ Hora Atual",
            f"**Data:** {now.strftime('%d/%m/%Y')}\n**Hora:** {now.strftime('%H:%M:%S')}",
            color=0x7289da
        )

    await ctx.send(embed=embed)

@bot.command(name='lembrete', aliases=['remind'])
async def reminder(ctx, tempo, *, mensagem=None):
    """Cria um lembrete"""
    if not mensagem:
        embed = create_embed("❌ Mensagem necessária", "Use: `RXlembrete 30m Fazer algo`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    # Parse time
    time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    unit = tempo[-1].lower()

    if unit not in time_units:
        embed = create_embed("❌ Unidade inválida", "Use: s (segundos), m (minutos), h (horas), d (dias)", color=0xff0000)
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
            ''', (ctx.author.id, ctx.guild.id, ctx.channel.id, mensagem, remind_time))
            conn.commit()
            conn.close()

        embed = create_embed(
            "⏰ Lembrete Criado",
            f"Vou te lembrar em {amount}{unit}: **{mensagem}**",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

    except ValueError:
        embed = create_embed("❌ Tempo inválido", "Use formato: 30m, 2h, 1d, etc.", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='senha', aliases=['password'])
async def generate_password(ctx, tamanho: int = 12):
    """Gera senha aleatória"""
    if tamanho < 4 or tamanho > 50:
        embed = create_embed("❌ Tamanho inválido", "Use entre 4 e 50 caracteres", color=0xff0000)
        await ctx.send(embed=embed)
        return

    chars = string.ascii_letters + string.digits + "!@#$%&*"
    senha = ''.join(random.choice(chars) for _ in range(tamanho))

    embed = create_embed(
        "🔑 Senha Gerada",
        f"**Senha:** `{senha}`\n**Tamanho:** {tamanho} caracteres",
        color=0x00ff00
    )

    try:
        await ctx.author.send(embed=embed)
        await ctx.send("✅ Senha enviada no seu privado!")
    except:
        await ctx.send("❌ Não consegui enviar no privado. Verifique suas configurações de DM.")

@bot.command(name='base64')
async def base64_encode(ctx, *, texto=None):
    """Codifica texto em Base64"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXbase64 Hello World`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    encoded = base64.b64encode(texto.encode()).decode()
    embed = create_embed(
        "🔐 Base64",
        f"**Original:** {texto}\n**Codificado:** `{encoded}`",
        color=0x7289da
    )
    await ctx.send(embed=embed)

@bot.command(name='hash')
async def hash_text(ctx, *, texto=None):
    """Gera hash MD5 do texto"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXhash Hello World`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    hash_md5 = hashlib.md5(texto.encode()).hexdigest()
    embed = create_embed(
        "🔒 Hash MD5",
        f"**Original:** {texto}\n**Hash:** `{hash_md5}`",
        color=0x7289da
    )
    await ctx.send(embed=embed)

# ============ COMANDOS DE TEXTO ============
@bot.command(name='reverso', aliases=['reverse'])
async def reverse_text(ctx, *, texto=None):
    """Reverte o texto"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXreverso Hello World`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    reversed_text = texto[::-1]
    embed = create_embed(
        "🔄 Texto Reverso",
        f"**Original:** {texto}\n**Reverso:** {reversed_text}",
        color=0x7289da
    )
    await ctx.send(embed=embed)

@bot.command(name='maiuscula', aliases=['upper'])
async def uppercase(ctx, *, texto=None):
    """Converte para maiúscula"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXmaiuscula hello world`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    embed = create_embed(
        "🔤 Maiúscula",
        f"**Original:** {texto}\n**Maiúscula:** {texto.upper()}",
        color=0x7289da
    )
    await ctx.send(embed=embed)

@bot.command(name='minuscula', aliases=['lower'])
async def lowercase(ctx, *, texto=None):
    """Converte para minúscula"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXminuscula HELLO WORLD`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    embed = create_embed(
        "🔤 Minúscula",
        f"**Original:** {texto}\n**Minúscula:** {texto.lower()}",
        color=0x7289da
    )
    await ctx.send(embed=embed)

@bot.command(name='contar', aliases=['count'])
async def count_text(ctx, *, texto=None):
    """Conta caracteres e palavras"""
    if not texto:
        embed = create_embed("❌ Texto necessário", "Use: `RXcontar Hello World`", color=0xff0000)
        await ctx.send(embed=embed)
        return

    chars = len(texto)
    words = len(texto.split())
    lines = len(texto.split('\n'))

    embed = create_embed(
        "📊 Estatísticas do Texto",
        f"**Caracteres:** {chars}\n**Palavras:** {words}\n**Linhas:** {lines}",
        color=0x7289da
    )
    await ctx.send(embed=embed)

@bot.command(name='ascii')
async def ascii_art(ctx, *, texto=None):
    """Converte texto em ASCII art simples"""
    if not texto:
        texto = "RXbot"

    ascii_map = {
        'A': "  ▄▀█  \n █▄█ ", 'B': " █▄▄ \n █▄█ ", 'C': " ▄▀█ \n █▄▄ ",
        'R': " █▀█ \n █▀▄ ", 'X': " ▀▄▀ \n █▄█ ", 'O': " █▀█ \n █▄█ "
    }

    result = ""
    for char in texto.upper():
        if char in ascii_map:
            result += ascii_map[char] + "  "
        elif char == ' ':
            result += "   "

    embed = create_embed("🎨 ASCII Art", f"```\n{result}\n```", color=0x7289da)
    await ctx.send(embed=embed)

# ============ COMANDOS DE MODERAÇÃO ============
@bot.command(name='warn', aliases=['advertir', 'aviso'])
@commands.has_permissions(manage_messages=True)
async def warn_user(ctx, user: discord.Member, *, motivo="Sem motivo especificado"):
    """Advertir um usuário"""
    if user == ctx.author:
        embed = create_embed("❌ Impossível", "Você não pode se advertir!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if user.top_role >= ctx.author.top_role:
        embed = create_embed("❌ Sem permissão", "Você não pode advertir este membro!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    # Atualizar warnings no banco de dados
    user_data = get_user_data(user.id)
    if not user_data:
        update_user_data(user.id)
        user_data = get_user_data(user.id)

    warnings = user_data[15] + 1
    update_user_data(user.id, warnings=warnings)

    # Log da moderação
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason)
                VALUES (?, ?, ?, ?, ?)
            ''', (ctx.guild.id, user.id, ctx.author.id, 'warn', motivo))
            conn.commit()
            conn.close()
    except Exception as e:
        logger.error(f"Error logging moderation: {e}")

    # Determinar castigo baseado no número de warnings
    castigo = ""
    action_taken = False

    if warnings >= 5:
        # 5+ warnings = Ban
        try:
            await user.ban(reason=f"5+ Warnings: {motivo}")
            castigo = f"\n🔨 **BANIDO** do servidor por acúmulo de {warnings} warnings!"
            action_taken = True
        except:
            castigo = f"\n⚠️ Tentativa de ban falhou (5+ warnings)"

    elif warnings >= 3:
        # 3-4 warnings = Timeout 24h
        try:
            timeout_until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
            await user.timeout(timeout_until, reason=f"3+ Warnings: {motivo}")
            castigo = f"\n⏰ **TIMEOUT 24h** por acúmulo de {warnings} warnings!"
            action_taken = True
        except:
            castigo = f"\n⚠️ Tentativa de timeout falhou (3+ warnings)"

    elif warnings == 2:
        # 2 warnings = Timeout 1h
        try:
            timeout_until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
            await user.timeout(timeout_until, reason=f"2 Warnings: {motivo}")
            castigo = f"\n⏰ **TIMEOUT 1h** por acúmulo de {warnings} warnings!"
            action_taken = True
        except:
            castigo = f"\n⚠️ Tentativa de timeout falhou (2 warnings)"

    embed = create_embed(
        "⚠️ Usuário Advertido",
        f"**{user.mention}** recebeu um warning!\n"
        f"**Motivo:** {motivo}\n"
        f"**Total de warnings:** {warnings}/5\n"
        f"**Moderador:** {ctx.author.mention}{castigo}",
        color=0xff6b6b if action_taken else 0xffaa00
    )

    await ctx.send(embed=embed)

    # Enviar DM para o usuário
    try:
        dm_embed = create_embed(
            f"⚠️ Warning em {ctx.guild.name}",
            f"**Motivo:** {motivo}\n"
            f"**Warnings totais:** {warnings}/5\n"
            f"**Moderador:** {ctx.author.name}\n\n"
            f"📋 **Lembre-se das regras:**\n"
            f"• Respeite todos os membros\n"
            f"• Não faça spam\n"
            f"• Mantenha conversas adequadas\n"
            f"• Siga as diretrizes do Discord{castigo}",
            color=0xff6b6b
        )
        await user.send(embed=dm_embed)
    except:
        pass

@bot.command(name='warnings', aliases=['avisos', 'infrações'])
async def check_warnings(ctx, user: discord.Member = None):
    """Verificar warnings de um usuário"""
    target = user or ctx.author
    user_data = get_user_data(target.id)

    if not user_data:
        warnings = 0
    else:
        warnings = user_data[15]

    # Buscar histórico de moderação
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT action, reason, timestamp FROM moderation_logs
                WHERE user_id = ? AND guild_id = ?
                ORDER BY timestamp DESC LIMIT 5
            ''', (target.id, ctx.guild.id))
            logs = cursor.fetchall()
            conn.close()
    except Exception as e:
        logger.error(f"Error fetching moderation logs: {e}")
        logs = []

    # Status baseado em warnings
    if warnings == 0:
        status = "🟢 Limpo"
        color = 0x00ff00
    elif warnings <= 2:
        status = "🟡 Atenção"
        color = 0xffaa00
    else:
        status = "🔴 Perigo"
        color = 0xff0000

    embed = create_embed(
        f"⚠️ Warnings de {target.display_name}",
        f"**Status:** {status}\n"
        f"**Warnings:** {warnings}/5\n"
        f"**Próximo castigo:** {get_next_punishment(warnings)}",
        color=color
    )

    if logs:
        log_text = ""
        for log in logs[:3]:  # Mostrar últimos 3
            action, reason, timestamp = log
            try:
                dt = datetime.datetime.fromisoformat(timestamp)
                log_text += f"• **{action.upper()}:** {reason} ({dt.strftime('%d/%m/%Y')})\n"
            except:
                log_text += f"• **{action.upper()}:** {reason}\n"

        if log_text:
            embed.add_field(name="📋 Histórico Recente", value=log_text, inline=False)

    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await ctx.send(embed=embed)

def get_next_punishment(current_warnings):
    """Retorna o próximo castigo baseado no número atual de warnings"""
    if current_warnings == 0:
        return "1º Warning = Aviso"
    elif current_warnings == 1:
        return "2º Warning = Timeout 1h"
    elif current_warnings == 2:
        return "3º Warning = Timeout 24h"
    elif current_warnings >= 3 and current_warnings < 5:
        return "5º Warning = Ban permanente"
    else:
        return "Ban permanente aplicado"

@bot.command(name='limparwarnings', aliases=['clearwarnings', 'resetwarnings'])
@commands.has_permissions(administrator=True)
async def clear_warnings(ctx, user: discord.Member):
    """[ADMIN] Limpar warnings de um usuário"""
    update_user_data(user.id, warnings=0)

    embed = create_embed(
        "✅ Warnings Limpos",
        f"Todos os warnings de {user.mention} foram removidos!\n"
        f"**Administrador:** {ctx.author.mention}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

    # Log da moderação
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason)
                VALUES (?, ?, ?, ?, ?)
            ''', (ctx.guild.id, user.id, ctx.author.id, 'clear_warnings', 'Warnings removidos por admin'))
            conn.commit()
            conn.close()
    except Exception as e:
        logger.error(f"Error logging moderation: {e}")

@bot.command(name='timeout', aliases=['mute', 'mutar'])
@commands.has_permissions(moderate_members=True)
async def timeout_user(ctx, user: discord.Member, duration: str, *, motivo="Sem motivo especificado"):
    """Aplicar timeout em um usuário"""
    if user == ctx.author:
        embed = create_embed("❌ Impossível", "Você não pode se mutar!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if user.top_role >= ctx.author.top_role:
        embed = create_embed("❌ Sem permissão", "Você não pode mutar este membro!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    # Parse duration
    time_units = {'m': 'minutos', 'h': 'horas', 'd': 'dias'}
    unit = duration[-1].lower()

    if unit not in time_units:
        embed = create_embed("❌ Formato inválido", "Use: 30m, 2h, 1d", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        amount = int(duration[:-1])

        if unit == 'm':
            delta = datetime.timedelta(minutes=amount)
        elif unit == 'h':
            delta = datetime.timedelta(hours=amount)
        elif unit == 'd':
            delta = datetime.timedelta(days=amount)

        timeout_until = datetime.datetime.now(datetime.timezone.utc) + delta

        await user.timeout(timeout_until, reason=motivo)

        embed = create_embed(
            "⏰ Timeout Aplicado",
            f"**{user.mention}** foi mutado por **{amount}{unit}**!\n"
            f"**Motivo:** {motivo}\n"
            f"**Moderador:** {ctx.author.mention}",
            color=0xff6b6b
        )
        await ctx.send(embed=embed)

        # Log da moderação
        try:
            with db_lock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason, duration)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (ctx.guild.id, user.id, ctx.author.id, 'timeout', motivo, amount))
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Error logging moderation: {e}")

    except ValueError:
        embed = create_embed("❌ Duração inválida", "Use números válidos: 30m, 2h, 1d", color=0xff0000)
        await ctx.send(embed=embed)
    except Exception as e:
        embed = create_embed("❌ Erro", f"Não foi possível aplicar timeout: {str(e)}", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command(name='regras', aliases=['rules'])
async def server_rules(ctx):
    """Mostra as regras do servidor"""
    embed = create_embed(
        "📋 Regras do Servidor",
        """**1. 🤝 RESPEITO MÚTUO**
    • Trate todos com respeito e cordialidade
    • Não toleramos assédio, bullying ou discriminação
    • Mantenha conversas civilizadas

    **2. 🚫 CONTEÚDO PROIBIDO**
    • Sem spam, flood ou mensagens repetitivas
    • Proibido conteúdo NSFW, violento ou ofensivo
    • Não compartilhe links suspeitos ou maliciosos

    **3. 💬 COMUNICAÇÃO**
    • Use canais apropriados para cada assunto
    • Não faça menções desnecessárias (@everyone/@here)
    • Evite discussões políticas ou religiosas

    **4. 🎮 JOGOS E DIVERSÃO**
    • Respeite outros jogadores nos jogos
    • Não trapaceie ou abuse de bugs
    • Divirta-se respeitando os limites

    **5. ⚖️ CONSEQUÊNCIAS**
    • **1-2 Warnings:** Avisos e timeout curto
    • **3-4 Warnings:** Timeout de 24 horas
    • **5+ Warnings:** Ban permanente

    ⚠️ **Moderadores têm palavra final em todas as situações**""",
        color=0x7289da
    )

    embed.add_field(
        name="📞 Precisa de Ajuda?",
        value="Use `RXticket <motivo>` para abrir um ticket de suporte!",
        inline=False
    )

    embed.set_footer(text="Ao permanecer no servidor, você concorda com estas regras")
    await ctx.send(embed=embed)

@bot.command(name='clear', aliases=['limpar', 'purge'])
@commands.has_permissions(manage_messages=True)
async def clear_messages(ctx, amount: int = 10):
    """Limpa mensagens do canal"""
    if amount < 1 or amount > 100:
        embed = create_embed("❌ Quantidade inválida", "Use entre 1 e 100 mensagens", color=0xff0000)
        await ctx.send(embed=embed)
        return

    deleted = await ctx.channel.purge(limit=amount + 1)  # +1 para incluir o comando

    embed = create_embed(
        "🧹 Canal Limpo",
        f"**{len(deleted) - 1} mensagens** foram deletadas!",
        color=0x00ff00
    )

    msg = await ctx.send(embed=embed)
    await asyncio.sleep(5)
    await msg.delete()

@bot.command(name='kick', aliases=['expulsar'])
@commands.has_permissions(kick_members=True)
async def kick_member(ctx, member: discord.Member, *, reason="Sem motivo especificado"):
    """Expulsa um membro"""
    if member == ctx.author:
        embed = create_embed("❌ Impossível", "Você não pode se expulsar!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    if member.top_role >= ctx.author.top_role:
        embed = create_embed("❌ Sem permissão", "Você não pode expulsar este membro!", color=0xff0000)
        await ctx.send(embed=embed)
        return

    try:
        await member.kick(reason=reason)
        embed = create_embed(
            "👢 Membro Expulso",
            f"**{member}** foi expulso!\n**Motivo:** {reason}",
            color=0xff6b6b
        )
        await ctx.send(embed=embed)
    except:
        embed = create_embed("❌ Erro", "Não foi possível expulsar o membro!", color=0xff0000)
        await ctx.send(embed=embed)

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

    try:
        await member.ban(reason=reason)
        embed = create_embed(
            "🔨 Membro Banido",
            f"**{member}** foi banido!\n**Motivo:** {reason}",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    except:
        embed = create_embed("❌ Erro", "Não foi possível banir o membro!", color=0xff0000)
        await ctx.send(embed=embed)

# ============ COMANDOS DE INFORMAÇÃO ============
@bot.command(name='userinfo', aliases=['uinfo', 'perfil'])
async def user_info(ctx, user: discord.Member = None):
    """Informações do usuário"""
    target = user or ctx.author

    embed = create_embed(
        f"👤 Perfil de {target.display_name}",
        f"""**ID:** {target.id}
    **Nome:** {target.name}#{target.discriminator}
    **Apelido:** {target.display_name}
    **Conta criada:** {target.created_at.strftime('%d/%m/%Y')}
    **Entrou no servidor:** {target.joined_at.strftime('%d/%m/%Y')}
    **Status:** {str(target.status).title()}
    **Maior cargo:** {target.top_role.mention}""",
        color=target.color
    )
    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name='serverinfo', aliases=['sinfo', 'servidor'])
async def server_info(ctx):
    """Informações do servidor"""
    guild = ctx.guild

    embed = create_embed(
        f"🏠 {guild.name}",
        f"""**ID:** {guild.id}
    **Dono:** {guild.owner.mention}
    **Criado em:** {guild.created_at.strftime('%d/%m/%Y')}
    **Membros:** {guild.member_count}
    **Canais:** {len(guild.channels)}
    **Cargos:** {len(guild.roles)}
    **Emojis:** {len(guild.emojis)}
    **Boost Level:** {guild.premium_tier}""",
        color=0x7289da
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await ctx.send(embed=embed)

@bot.command(name='avatar', aliases=['av'])
async def avatar(ctx, user: discord.Member = None):
    """Mostra o avatar do usuário"""
    target = user or ctx.author

    embed = create_embed(
        f"🖼️ Avatar de {target.display_name}",
        f"[Download]({target.avatar.url if target.avatar else target.default_avatar.url})",
        color=target.color
    )
    embed.set_image(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name='level', aliases=['lvl', 'rank'])
async def level(ctx, user: discord.Member = None):
    """Mostra o nível do usuário"""
    target = user or ctx.author
    data = get_user_data(target.id)

    if not data:
        update_user_data(target.id)
        data = get_user_data(target.id)

    xp = data[2]
    level = data[3]
    next_level_xp = ((level + 1) ** 2) * 100

    embed = create_embed(
        f"📊 Nível de {target.display_name}",
        f"""**Nível:** {level}
    **XP:** {xp:,}
    **XP para próximo nível:** {next_level_xp - xp:,}
    **Mensagens enviadas:** {data[12]}""",
        color=target.color
    )
    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name='botinfo', aliases=['binfo'])
async def bot_info(ctx):
    """Informações do bot"""
    uptime_seconds = int((datetime.datetime.now() - global_stats['uptime_start']).total_seconds())
    
    embed = create_embed(
        "🤖 RXbot - Informações",
        f"""**Versão:** 2.0.0
    **Criado por:** RX Team
    **Servidores:** {len(bot.guilds)}
    **Usuários:** {len(set(bot.get_all_members()))}
    **Comandos:** 200+
    **Uptime:** {format_time(uptime_seconds)}
    **Latência:** {round(bot.latency * 1000)}ms

    **Recursos:**
    • Sistema de economia completo
    • Jogos e diversão
    • Moderação avançada
    • Sistema de eventos
    • IA conversacional
    • Sistema de tickets

    **Monitoramento:**
    • Keep-alive ativo na porta 8080
    • Endpoints: `/ping`, `/status`, `/health`
    • Backup automático a cada 6h""",
        color=0x7289da
    )
    embed.set_thumbnail(url=bot.user.avatar.url)
    await ctx.send(embed=embed)

@bot.command(name='uptime')
async def uptime_command(ctx):
    """Mostra informações detalhadas de uptime"""
    uptime_seconds = int((datetime.datetime.now() - global_stats['uptime_start']).total_seconds())
    
    embed = create_embed(
        "⏰ Status de Uptime",
        f"""**🟢 Bot Online há:** {format_time(uptime_seconds)}
    **📊 Comandos executados:** {global_stats['commands_used']:,}
    **💬 Mensagens processadas:** {global_stats['messages_processed']:,}
    **🏠 Servidores ativos:** {len(bot.guilds)}
    **👥 Usuários únicos:** {len(set(bot.get_all_members()))}
    
    **🔗 Endpoints de monitoramento:**
    • `/ping` - Ping simples
    • `/status` - Status detalhado  
    • `/health` - Health check
    
    **📡 Latência atual:** {round(bot.latency * 1000)}ms""",
        color=0x00ff00
    )
    
    embed.set_footer(text="Keep-alive ativo • UptimeRobot monitorando")
    await ctx.send(embed=embed)

# ============ SISTEMA DE AJUDA EXPANDIDO ============
@bot.command(name='ajuda', aliases=['help', 'comandos', 'commands'])
async def help_command(ctx, categoria=None):
    """Sistema de ajuda completo"""
    if not categoria:
        embed = create_embed(
            "📚 Central de Ajuda - RXbot",
            """**🎮 Diversão (40+ comandos):**
    `RXajuda diversao` - Jogos, piadas, memes

    **💰 Economia (30+ comandos):**
    `RXajuda economia` - Dinheiro, loja, trabalho

    **⚙️ Utilidades (50+ comandos):**
    `RXajuda utilidades` - Calculadora, tempo, lembretes

    **🛡️ Moderação (30+ comandos):**
    `RXajuda moderacao` - Kick, ban, clear

    **📅 Eventos (10+ comandos):**
    `RXajuda eventos` - Criar e gerenciar eventos

    **🎨 Texto (20+ comandos):**
    `RXajuda texto` - Manipulação de texto

    **📊 Informações (30+ comandos):**
    `RXajuda info` - Stats, perfil, servidor

    **🎟️ Tickets:**
    `RXticket <motivo>` - Criar ticket de suporte

    **📋 Regras:**
    `RXregras` - Ver regras do servidor

    **🤖 IA Avançada:**
    Mencione o bot para conversar!

    **Total:** 200+ comandos disponíveis!""",
            color=0x7289da
        )
        embed.set_footer(text="Use RXajuda <categoria> para ver comandos específicos!")
        await ctx.send(embed=embed)

    elif categoria.lower() in ['diversao', 'diversão', 'fun']:
        embed = create_embed(
            "🎮 Comandos de Diversão",
            """**Jogos:**
    • `RXjokenpo <escolha>` - Pedra, papel, tesoura
    • `RXquiz` - Jogo de perguntas e respostas
    • `RXforca` - Jogo da forca
    • `RXdado [lados]` - Rola um dado (padrão 6 lados)
    • `RXmoeda` - Cara ou coroa
    • `RX8ball <pergunta>` - Bola mágica 8

    **Entretenimento:**
    • `RXpiada` - Conta uma piada aleatória
    • `RXfato` - Fato interessante
    • `RXmeme` - Memes aleatórios
    • `RXsorteio <@users>` - Sorteia entre usuários
    • `RXenquete <pergunta>` - Cria enquete com reações
    • `RXascii <texto>` - ASCII art
    • `RXcores` - Mostra cores aleatórias""",
            color=0x7289da
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['economia', 'money', 'eco']:
        embed = create_embed(
            "💰 Comandos de Economia",
            """**Dinheiro:**
    • `RXsaldo [@user]` - Ver saldo (carteira + banco)
    • `RXdaily` - Recompensa diária (500💰)
    • `RXtrabalhar` - Trabalhe por dinheiro
    • `RXtransferir <@user> <valor>` - Transferir dinheiro

    **Loja:**
    • `RXloja` - Ver itens da loja
    • `RXcomprar <id>` - Comprar item da loja

    **Sistema completo de economia virtual!**
    *Ganhe moedas jogando, trabalhando e participando!*""",
            color=0xffd700
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['utilidades', 'utils', 'tools']:
        embed = create_embed(
            "⚙️ Comandos de Utilidades",
            """**Ferramentas:**
    • `RXcalc <expressão>` - Calculadora matemática
    • `RXtempo [timezone]` - Hora atual
    • `RXlembrete <tempo> <msg>` - Criar lembrete
    • `RXsenha [tamanho]` - Gerar senha segura
    • `RXbase64 <texto>` - Codificar em Base64
    • `RXhash <texto>` - Gerar hash MD5

    **Memória IA:**
    • `RXresetmemoria [@user]` - Resetar memória de conversas
    • `RXvermemoria` - Ver status da memória

    **Exemplos:**
    • `RXlembrete 30m Estudar` - Lembrete em 30 minutos
    • `RXcalc 2 + 2 * 3` - Calcula expressões
    • `RXsenha 16` - Senha de 16 caracteres""",
            color=0x7289da
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['moderacao', 'mod', 'admin']:
        embed = create_embed(
            "🛡️ Comandos de Moderação",
            """**Punições & Warnings:**
    • `RXwarn <@user> [motivo]` - Advertir usuário
    • `RXwarnings [@user]` - Ver warnings de usuário
    • `RXtimeout <@user> <tempo> [motivo]` - Timeout (30m, 2h, 1d)
    • `RXlimparwarnings <@user>` - Limpar warnings (admin)

    **Moderação Básica:**
    • `RXclear [quantidade]` - Limpar mensagens (1-100)
    • `RXkick <@user> [motivo]` - Expulsar membro
    • `RXban <@user> [motivo]` - Banir membro

    **Sistema de Regras:**
    • `RXregras` - Ver regras do servidor

    **Tickets:**
    • `RXticket <motivo>` - Criar ticket de suporte
    • `RXfechar [motivo]` - Fechar ticket (dentro do canal)

    **Eventos (Admin):**
    • `RXcriarevento` - Criar evento para o servidor

    **Economia Admin:**
    • `RXaddcoins <@user> <valor>` - Adicionar RXcoins
    • `RXremovecoins <@user> <valor>` - Remover RXcoins
    • `RXsetcoins <@user> <valor>` - Definir RXcoins

    **Memória Admin:**
    • `RXresetmemoria <@user>` - Resetar memória específica
    • `RXlimpartotalmemoria` - Limpar TODA memória
    • `RXstatusmemoria` - Ver estatísticas da memória

    **⚖️ Sistema de Castigos:**
    • 1-2 warnings = Avisos
    • 3-4 warnings = Timeout 24h
    • 5+ warnings = Ban permanente

    *Alguns comandos requerem permissões especiais!*""",
            color=0xff6b6b
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['eventos', 'events']:
        embed = create_embed(
            "📅 Sistema de Eventos",
            """**Para Administradores:**
    • `RXcriarevento <dados>` - Criar evento
    • Formato: `Título | Descrição | Data | Participantes`
    • Exemplo: `RXcriarevento Torneio | Competição épica | 2024-12-25 20:00 | 20`

    **Para Todos:**
    • `RXeventos` - Ver eventos disponíveis
    • `RXparticipar <id>` - Participar de um evento

    **Sistema completo de eventos com inscrições automáticas!**""",
            color=0x7289da
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['texto', 'text']:
        embed = create_embed(
            "🎨 Comandos de Texto",
            """**Manipulação:**
    • `RXreverso <texto>` - Reverter texto
    • `RXmaiuscula <texto>` - Converter para MAIÚSCULA
    • `RXminuscula <texto>` - converter para minúscula
    • `RXcontar <texto>` - Contar caracteres/palavras
    • `RXascii <texto>` - Criar ASCII art

    **Úteis para formatação e diversão com texto!**""",
            color=0x7289da
        )
        await ctx.send(embed=embed)

    elif categoria.lower() in ['info', 'informacao', 'stats']:
        embed = create_embed(
            "📊 Comandos de Informação",
            """**Perfil & Stats:**
    • `RXlevel [@user]` - Nível e XP do usuário
    • `RXuserinfo [@user]` - Informações detalhadas
    • `RXavatar [@user]` - Avatar em alta qualidade
    • `RXsaldo [@user]` - Economia do usuário

    **Servidor & Bot:**
    • `RXserverinfo` - Informações do servidor
    • `RXbotinfo` - Informações e estatísticas do bot
    • `RXping` - Latência e uptime

    **Sistema completo de estatísticas e informações!**""",
            color=0x7289da
        )
        await ctx.send(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            "❌ Argumento obrigatório",
            f"Você esqueceu de fornecer: `{error.param.name}`\n"
            f"Use `RXajuda` para ver os comandos.",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.BadArgument):
        embed = create_embed(
            "❌ Argumento inválido",
            f"Verifique os argumentos do comando.\n"
            f"Use `RXajuda` para ver os comandos.",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingPermissions):
        embed = create_embed(
            "❌ Sem permissão",
            "Você não tem permissão para usar este comando!",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    else:
        # Log unexpected errors
        logger.error(f"Unexpected error in command {ctx.command}: {error}")

        embed = create_embed(
            "❌ Erro inesperado",
            "Ocorreu um erro inesperado. Tente novamente em alguns segundos.",
            color=0xff0000
        )
        await ctx.send(embed=embed)

if __name__ == "__main__":
    while True:
        try:
            logger.info("🚀 Iniciando RXbor...")
            keep_alive()
            bot.run(os.getenv('TOKEN'))
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar o bot: {e}")
            print(f"❌ Erro crítico: {e}")
            logger.info("🔄 Reiniciando bot em 5 segundos...")
            time.sleep(5)
            subprocess.run([sys.executable, sys.argv[0]])

