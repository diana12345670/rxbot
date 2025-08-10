# main.py — RXbot (Parte 1/..) - Estrutura, imports, config e camada DB
# Nota: cole as partes na ordem que eu enviar para obter o arquivo completo.
# Requisitos (serão listados no requirements.txt no final):
# discord.py, aiosqlite, python-dotenv, aiohttp, apscheduler (opcional), psutil

import os
import sys
import asyncio
import logging
import aiosqlite
import json
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv

import discord
from discord.ext import commands, tasks

# Carrega .env local (útil para desenvolvimento)
load_dotenv()

# -------------------
# Config & Logging
# -------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("rxbot")

# -------------------
# Environment config
# -------------------
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    logger.critical("TOKEN não encontrado nas variáveis de ambiente. Abortando.")
    raise SystemExit("Defina a variável de ambiente TOKEN.")

DB_PATH = os.getenv("DB_PATH", "rxbot.db")
RESTART_BACKOFF = int(os.getenv("RESTART_BACKOFF", "5"))  # segundos para backoff inicial
OWNER_ID = int(os.getenv("OWNER_ID", "0")) if os.getenv("OWNER_ID") else None

# -------------------
# Intents & Bot
# -------------------
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.reactions = True

# Prefix padrão (pode ser dinâmico por guild)
DEFAULT_PREFIX = os.getenv("DEFAULT_PREFIX", "!")

bot = commands.Bot(command_prefix=DEFAULT_PREFIX, intents=intents)
bot.remove_command("help")  # usaremos help personalizado

# -------------------
# Data models
# -------------------
@dataclass
class Item:
    id: int
    name: str
    description: str
    price: int
    effect: Optional[str]  # efeito em string para parsing, ex: "give_coins:100"

@dataclass
class Giveaway:
    id: int
    guild_id: int
    channel_id: int
    message_id: int
    prize: str
    winners: int
    ends_at: datetime

# -------------------
# Database Layer
# -------------------
# Todas as operações DB usam aiosqlite e abrem conexões curtas para evitar locks
# Você pode alterar para um pool com asyncpg se migrar para Postgres.

async def init_db():
    """Cria as tabelas principais se não existirem."""
    logger.info("Inicializando DB: %s", DB_PATH)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            coins INTEGER DEFAULT 0,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            last_daily TEXT
        );
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            price INTEGER NOT NULL,
            effect TEXT
        );
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS inventories (
            user_id INTEGER,
            item_id INTEGER,
            quantity INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, item_id),
            FOREIGN KEY (item_id) REFERENCES items(id)
        );
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            channel_id INTEGER,
            user_id INTEGER,
            status TEXT DEFAULT 'open',
            created_at TEXT
        );
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS ranks (
            guild_id INTEGER,
            user_id INTEGER,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        );
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS giveaways (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            channel_id INTEGER,
            message_id INTEGER,
            prize TEXT,
            winners INTEGER DEFAULT 1,
            ends_at TEXT
        );
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            guild_id INTEGER PRIMARY KEY,
            prefix TEXT DEFAULT ?
        );
        """, (DEFAULT_PREFIX,))
        await db.execute("""
        CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            data TEXT
        );
        """)
        await db.commit()
    logger.info("DB inicializada com sucesso.")

# -------------------
# DB helpers (users / coins)
# -------------------
async def db_ensure_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id, coins, xp, level) VALUES (?, 0, 0, 1);", (user_id,))
        await db.commit()

async def db_get_coins(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT coins FROM users WHERE user_id = ?;", (user_id,))
        row = await cursor.fetchone()
        return int(row[0]) if row else 0

async def db_add_coins(user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id, coins) VALUES(?, 0);", (user_id,))
        await db.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?;", (amount, user_id))
        await db.commit()

async def db_subtract_coins(user_id: int, amount: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT coins FROM users WHERE user_id = ?;", (user_id,))
        row = await cursor.fetchone()
        if not row or int(row[0]) < amount:
            return False
        await db.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?;", (amount, user_id))
        await db.commit()
        return True

# -------------------
# DB helpers (items / loja / inventario)
# -------------------
async def db_get_items() -> List[Item]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id,name,description,price,effect FROM items ORDER BY id;")
        rows = await cursor.fetchall()
        return [Item(*row) for row in rows]

async def db_get_item_by_name(name: str) -> Optional[Item]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id,name,description,price,effect FROM items WHERE name = ? COLLATE NOCASE;", (name,))
        row = await cursor.fetchone()
        return Item(*row) if row else None

async def db_insert_item(name: str, description: str, price: int, effect: Optional[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO items(name,description,price,effect) VALUES (?, ?, ?, ?);",
                         (name, description, price, effect))
        await db.commit()

async def db_add_item_to_inventory(user_id: int, item_id: int, qty: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO inventories(user_id, item_id, quantity)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity;
        """, (user_id, item_id, qty))
        await db.commit()

async def db_get_inventory(user_id: int) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
        SELECT i.item_id, it.name, it.description, it.effect, i.quantity
        FROM inventories i
        JOIN items it ON i.item_id = it.id
        WHERE i.user_id = ? AND i.quantity > 0
        ORDER BY it.name;
        """, (user_id,))
        rows = await cursor.fetchall()
        return [{"item_id": row[0], "name": row[1], "description": row[2], "effect": row[3], "quantity": row[4]} for row in rows]

async def db_decrement_inventory(user_id: int, item_id: int, qty: int = 1) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT quantity FROM inventories WHERE user_id = ? AND item_id = ?;", (user_id, item_id))
        row = await cursor.fetchone()
        if not row or row[0] < qty:
            return False
        await db.execute("UPDATE inventories SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?;", (qty, user_id, item_id))
        await db.commit()
        return True

# -------------------
# DB helpers (ranks/xp)
# -------------------
async def db_add_xp(guild_id: int, user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO ranks(guild_id, user_id, xp, level) VALUES (?, ?, 0, 0);", (guild_id, user_id))
        await db.execute("UPDATE ranks SET xp = xp + ? WHERE guild_id = ? AND user_id = ?;", (amount, guild_id, user_id))
        await db.commit()

async def db_get_rank(guild_id: int, user_id: int) -> Tuple[int, int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT xp, level FROM ranks WHERE guild_id = ? AND user_id = ?;", (guild_id, user_id))
        row = await cursor.fetchone()
        if not row:
            return (0, 0)
        return (int(row[0]), int(row[1]))

# -------------------
# DB helpers (giveaways)
# -------------------
async def db_create_giveaway(guild_id: int, channel_id: int, message_id: int, prize: str, winners: int, ends_at: datetime) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("INSERT INTO giveaways(guild_id, channel_id, message_id, prize, winners, ends_at) VALUES (?, ?, ?, ?, ?, ?);",
                                  (guild_id, channel_id, message_id, prize, winners, ends_at.isoformat()))
        await db.commit()
        return cursor.lastrowid

async def db_get_active_giveaways() -> List[Giveaway]:
    out = []
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id,guild_id,channel_id,message_id,prize,winners,ends_at FROM giveaways;")
        rows = await cursor.fetchall()
        for r in rows:
            try:
                ends_at = datetime.fromisoformat(r[6])
            except Exception:
                ends_at = datetime.utcnow()
            out.append(Giveaway(id=r[0], guild_id=r[1], channel_id=r[2], message_id=r[3], prize=r[4], winners=int(r[5]), ends_at=ends_at))
    return out

# -------------------
# Utility helpers
# -------------------
def format_coins(n: int) -> str:
    return f"{n:,}"

def now_iso() -> str:
    return datetime.utcnow().isoformat()

# -------------------
# Inicialização de itens padrão (loja)
# -------------------
async def ensure_default_items():
    logger.info("Assegurando itens padrão na loja...")
    default_items = [
        {"name": "PequenaPoção", "description": "Restaura 50 coins quando usado.", "price": 100, "effect": "give_coins:50"},
        {"name": "GrandePoção", "description": "Restaura 200 coins quando usado.", "price": 350, "effect": "give_coins:200"},
        {"name": "BoletoPremium", "description": "Dá 1000 coins (promoção)", "price": 800, "effect": "give_coins:1000"},
        {"name": "SorteToken", "description": "Aumenta chances em sorteios (placeholder effect).", "price": 250, "effect": "sorte_token:1"},
    ]
    for it in default_items:
        await db_insert_item(it["name"], it["description"], it["price"], it["effect"])
    logger.info("Itens padrão garantidos.")

# -------------------
# Eventos básicos & comandos de teste
# -------------------
@bot.event
async def on_ready():
    logger.info(f"Bot pronto: {bot.user} (ID: {bot.user.id})")
    # inicializa DB e dados
    await init_db()
    await ensure_default_items()
    if not background_status.is_running():
        background_status.start()

@bot.event
async def on_command_error(ctx, error):
    # Tratamento padrão de erros de comandos
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Argumentos faltando. Use `!help` para ver os comandos.")
        return
    logger.exception("Erro em comando %s: %s", ctx.command, error)
    try:
        await ctx.send("Ocorreu um erro ao executar o comando. Verifique os logs.")
    except Exception:
        pass

@bot.command(name="ping")
async def ping_cmd(ctx):
    """Comando de teste - responde com latência"""
    latency_ms = round(bot.latency * 1000)
    await ctx.send(f"Pong! Latência: {latency_ms}ms")

@bot.command(name="help")
async def help_cmd(ctx):
    txt = (
        "**RXbot - comandos principais**\n"
        "`!ping` - Teste de latência\n"
        "`!saldo` - Ver seu saldo\n"
        "`!loja` - Ver itens à venda\n"
        "`!comprar <nome>` - Comprar item\n"
        "`!inventario` - Ver inventário\n"
        "`!usar <nome>` - Usar item\n"
        "`!ticket` - Abrir ticket (se habilitado)\n"
        "`!sorteio` - Criar sorteio (moderação)\n"
        "E muitos outros comandos integrados no bot."
    )
    await ctx.send(txt)

# Fim da PARTE 1

# -------------------
# PARTE 2 — Economia, loja, inventário, usar itens, daily, pay
# -------------------

# --- Helpers adicionais de usuário / tempo ---
async def db_ensure_user_full(user_id: int):
    """Garante que o usuário exista na tabela users com valores iniciais."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id, coins, xp, level, last_daily) VALUES (?, 0, 0, 1, NULL);", (user_id,))
        await db.commit()

async def db_get_last_daily(user_id: int) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT last_daily FROM users WHERE user_id = ?;", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row and row[0] else None

async def db_set_last_daily(user_id: int, iso_ts: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET last_daily = ? WHERE user_id = ?;", (iso_ts, user_id))
        await db.commit()

# --- apply item effects (estendido) ---
async def apply_item_effect_ctx(ctx: commands.Context, user_id: int, effect: Optional[str]) -> str:
    """
    Aplica efeito do item no contexto (para efeitos que precisam de guild ou membro).
    Retorna mensagem descritiva do que aconteceu.
    Exemplos de efeito:
      - give_coins:100
      - boost_xp:50
      - grant_role:RoleName
    """
    if not effect:
        return "Nada aconteceu..."
    try:
        if effect.startswith("give_coins:"):
            amount = int(effect.split(":", 1)[1])
            await db_add_coins(user_id, amount)
            return f"Você recebeu {format_coins(amount)} coins!"
        if effect.startswith("boost_xp:"):
            amount = int(effect.split(":", 1)[1])
            guild = ctx.guild
            if guild:
                await db_add_xp(guild.id, user_id, amount)
                return f"Você ganhou {amount} XP!"
            else:
                # fallback se for em DMs
                return "Efeito de XP não pode ser aplicado em DM."
        if effect.startswith("grant_role:"):
            role_name = effect.split(":", 1)[1]
            guild = ctx.guild
            if not guild:
                return "Não é possível dar cargo em DM."
            member = guild.get_member(user_id) or await guild.fetch_member(user_id)
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                return f"Cargo `{role_name}` não encontrado neste servidor."
            try:
                await member.add_roles(role, reason="Item usado")
                return f"Cargo `{role.name}` concedido com sucesso!"
            except Exception as e:
                logger.exception("Erro ao dar cargo: %s", e)
                return "Falha ao conceder o cargo (permissões?)."
        # suporte a efeitos compostos: "give_coins:100|boost_xp:10"
        if "|" in effect:
            parts = effect.split("|")
            msgs = []
            for p in parts:
                msgs.append(await apply_item_effect_ctx(ctx, user_id, p))
            return " | ".join(msgs)
        return "Efeito desconhecido, mas o item foi consumido."
    except Exception as e:
        logger.exception("Erro ao aplicar efeito: %s", e)
        return "Erro ao aplicar o efeito do item."

# --- Comandos de economia / loja / inventário ---
@bot.command(name="saldo")
async def cmd_saldo(ctx, member: discord.Member = None):
    member = member or ctx.author
    await db_ensure_user_full(member.id)
    coins = await db_get_coins(member.id)
    await ctx.send(f"{member.mention} tem {format_coins(coins)} coins.")

@bot.command(name="pay")
async def cmd_pay(ctx, member: discord.Member, amount: int):
    if member.bot:
        return await ctx.send("Não é possível pagar bots.")
    if member.id == ctx.author.id:
        return await ctx.send("Você não pode pagar a si mesmo.")
    if amount <= 0:
        return await ctx.send("Valor inválido.")
    await db_ensure_user_full(ctx.author.id)
    await db_ensure_user_full(member.id)
    ok = await db_subtract_coins(ctx.author.id, amount)
    if not ok:
        return await ctx.send("Saldo insuficiente.")
    await db_add_coins(member.id, amount)
    await ctx.send(f"{ctx.author.mention} pagou {format_coins(amount)} coins para {member.mention}.")

@bot.command(name="daily")
async def cmd_daily(ctx):
    user_id = ctx.author.id
    await db_ensure_user_full(user_id)
    last_iso = await db_get_last_daily(user_id)
    now = datetime.utcnow()
    if last_iso:
        try:
            last = datetime.fromisoformat(last_iso)
        except Exception:
            last = datetime.utcfromtimestamp(0)
        delta = now - last
        if delta < timedelta(hours=24):
            remaining = timedelta(hours=24) - delta
            hh = remaining.seconds // 3600
            mm = (remaining.seconds % 3600) // 60
            return await ctx.send(f"Você já coletou o daily. Volte em {remaining.days}d {hh}h {mm}m.")
    # pagar daily (valor simples, pode alterar)
    reward = 500  # valor diário
    await db_add_coins(user_id, reward)
    await db_set_last_daily(user_id, now.isoformat())
    await ctx.send(f"Você coletou o daily e ganhou {format_coins(reward)} coins!")

@bot.command(name="loja")
async def cmd_loja(ctx):
    items = await db_get_items()
    if not items:
        return await ctx.send("A loja está vazia.")
    embed = discord.Embed(title="Loja RXbot", description="Itens disponíveis para compra", color=discord.Color.blurple())
    for it in items:
        embed.add_field(name=f"{it.name} — {format_coins(it.price)} coins", value=it.description or "Sem descrição", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="comprar")
async def cmd_comprar(ctx, *, item_name: str):
    user_id = ctx.author.id
    await db_ensure_user_full(user_id)
    item = await db_get_item_by_name(item_name)
    if not item:
        return await ctx.send("Item não encontrado. Use `!loja` para ver os itens.")
    ok = await db_subtract_coins(user_id, item.price)
    if not ok:
        return await ctx.send("Saldo insuficiente.")
    await db_add_item_to_inventory(user_id, item.id, 1)
    await ctx.send(f"Você comprou **{item.name}** por {format_coins(item.price)} coins.")

@bot.command(name="inventario")
async def cmd_inventario(ctx):
    user_id = ctx.author.id
    await db_ensure_user_full(user_id)
    inv = await db_get_inventory(user_id)
    if not inv:
        return await ctx.send("Inventário vazio.")
    # Paginação simples (se muitos itens) pode ser adicionada futuramente
    embed = discord.Embed(title=f"Inventário de {ctx.author.display_name}", color=discord.Color.green())
    for it in inv:
        embed.add_field(name=f"{it['name']} x{it['quantity']}", value=it['description'] or "Sem descrição", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="usar")
async def cmd_usar(ctx, *, item_name: str):
    user_id = ctx.author.id
    await db_ensure_user_full(user_id)
    item = await db_get_item_by_name(item_name)
    if not item:
        return await ctx.send("Item não existe.")
    inv = await db_get_inventory(user_id)
    found = next((x for x in inv if x["item_id"] == item.id), None)
    if not found or found["quantity"] <= 0:
        return await ctx.send("Você não possui esse item.")
    # Aplica o efeito no contexto (pode precisar dele)
    res_msg = await apply_item_effect_ctx(ctx, user_id, item.effect)
    ok = await db_decrement_inventory(user_id, item.id, 1)
    if not ok:
        return await ctx.send("Erro ao consumir o item (quantidade insuficiente).")
    await ctx.send(f"Você usou **{item.name}** — {res_msg}")

# --- Admin: adicionar item à loja (apenas owner ou com permissão) ---
@bot.command(name="additem")
@commands.is_owner()  # restrito ao dono do bot (OWNER_ID deve estar configurado no env se quiser outra checagem)
async def cmd_additem(ctx, price: int, name: str, *, description: str = ""):
    await db_insert_item(name, description, price, None)
    await ctx.send(f"Item **{name}** adicionado com preço {format_coins(price)}.")

# --- Segurança: captura de erros de comando com traceback amigável para owner ---
@bot.event
async def on_application_command_error(error, ctx):
    logger.exception("Erro em command de aplicação: %s", error)
    if OWNER_ID and ctx.author.id == OWNER_ID:
        await ctx.send(f"Erro interno: {error}")

# FIM DA PARTE 2

# -------------------
# PARTE 3 — Tickets, Giveaways, Ranks/XP, Backups, IA humanizada (skeleton)
# -------------------

# -------------------
# Tickets
# -------------------
@bot.command(name="ticket")
async def cmd_ticket(ctx, *, motivo: str = "Sem motivo fornecido"):
    """Abre um ticket simples: cria um canal (se permissões permitirem) ou registra no DB."""
    guild = ctx.guild
    user = ctx.author
    await db_ensure_user_full(user.id)
    # Tenta criar canal de texto chamado ticket-<user>
    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        chan_name = f"ticket-{user.name}".lower()[:90]
        existing = discord.utils.get(guild.channels, name=chan_name)
        if existing:
            await ctx.send(f"Você já tem um ticket aberto: {existing.mention}")
            # registra no DB se não existir
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("INSERT OR IGNORE INTO tickets(guild_id, channel_id, user_id, status, created_at) VALUES (?, ?, ?, 'open', ?);",
                                 (guild.id, existing.id, user.id, now_iso()))
                await db.commit()
            return
        chan = await guild.create_text_channel(chan_name, overwrites=overwrites, reason="Abertura de ticket")
        # registra no DB
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO tickets(guild_id, channel_id, user_id, status, created_at) VALUES (?, ?, ?, 'open', ?);",
                             (guild.id, chan.id, user.id, now_iso()))
            await db.commit()
        await chan.send(f"{user.mention} abriu um ticket: {motivo}")
        await ctx.send(f"Ticket criado: {chan.mention}")
    except discord.Forbidden:
        # fallback: registra só no DB e responde
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT channel_id FROM tickets WHERE user_id = ? AND guild_id = ? AND status = 'open';", (user.id, guild.id))
            row = await cursor.fetchone()
            if row:
                return await ctx.send("Você já tem um ticket aberto.")
            await db.execute("INSERT INTO tickets(guild_id, channel_id, user_id, status, created_at) VALUES (?, ?, ?, 'open', ?);",
                             (guild.id, 0, user.id, now_iso()))
            await db.commit()
        await ctx.send("Não tenho permissão para criar canais. Ticket registrado no sistema, aguarde um staff responder.")

@bot.command(name="close")
@commands.has_permissions(manage_channels=True)
async def cmd_close_ticket(ctx, channel: discord.TextChannel = None):
    """Fecha um ticket: fecha canal (se for ticket) e atualiza DB."""
    channel = channel or ctx.channel
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, status FROM tickets WHERE channel_id = ? OR (guild_id = ? AND user_id = ? AND status = 'open');",
                                  (channel.id, ctx.guild.id, ctx.author.id))
        row = await cursor.fetchone()
        if not row:
            return await ctx.send("Canal não é um ticket conhecido.")
        ticket_id = row[0]
        await db.execute("UPDATE tickets SET status = 'closed' WHERE id = ?;", (ticket_id,))
        await db.commit()
    # tenta deletar o canal se for ticket criado
    try:
        await channel.send("Este ticket será fechado pelo staff.")
        await channel.delete(reason="Ticket fechado")
    except Exception:
        await ctx.send("Ticket marcado como fechado no banco. (Não foi possível deletar o canal.)")
    await ctx.send("Ticket fechado com sucesso.")

@bot.command(name="tickets")
@commands.has_permissions(manage_guild=True)
async def cmd_list_tickets(ctx, status: str = "open"):
    """Lista tickets pelo status."""
    status = status.lower()
    if status not in ("open", "closed", "all"):
        return await ctx.send("Status inválido. Use 'open', 'closed' ou 'all'.")
    async with aiosqlite.connect(DB_PATH) as db:
        if status == "all":
            cursor = await db.execute("SELECT id, guild_id, channel_id, user_id, status, created_at FROM tickets WHERE guild_id = ? ORDER BY created_at DESC;", (ctx.guild.id,))
        else:
            cursor = await db.execute("SELECT id, guild_id, channel_id, user_id, status, created_at FROM tickets WHERE guild_id = ? AND status = ? ORDER BY created_at DESC;", (ctx.guild.id, status))
        rows = await cursor.fetchall()
    if not rows:
        return await ctx.send("Nenhum ticket encontrado.")
    lines = []
    for r in rows:
        ch = f"<#{r[2]}>" if r[2] and r[2] != 0 else "—"
        lines.append(f"ID:{r[0]} | User:{r[3]} | Canal:{ch} | Status:{r[4]} | Criado:{r[5]}")
    # dividir em blocos se muito grande
    out = "\n".join(lines[:50])
    await ctx.send(f"Tickets:\n```\n{out}\n```")

# -------------------
# Giveaways (sorteios)
# -------------------
@bot.command(name="sorteio")
@commands.has_permissions(manage_guild=True)
async def cmd_create_giveaway(ctx, tempo_minutos: int, winners: int, *, prize: str):
    """
    Cria um sorteio que dura X minutos, com Y vencedores, e prêmio.
    Ex: !sorteio 60 1 Nitro Nitro do servidor
    """
    if tempo_minutos <= 0 or winners <= 0:
        return await ctx.send("Parâmetros inválidos.")
    ends_at = datetime.utcnow() + timedelta(minutes=tempo_minutos)
    embed = discord.Embed(title="Sorteio!", description=f"Prêmio: **{prize}**\nReaja com 🎉 para participar.", color=discord.Color.gold())
    embed.add_field(name="Vencedores", value=str(winners))
    embed.set_footer(text=f"Termina em {ends_at.isoformat()} UTC")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")
    gid = await db_create_giveaway(ctx.guild.id, ctx.channel.id, msg.id, prize, winners, ends_at)
    await ctx.send(f"Sorteio criado (ID {gid}).")

# Background task para verificar sorteios
@tasks.loop(seconds=30)
async def giveaways_checker():
    try:
        now = datetime.utcnow()
        active = await db_get_active_giveaways()
        for g in active:
            if g.ends_at <= now:
                # buscar mensagem e participantes
                try:
                    guild = bot.get_guild(g.guild_id) or await bot.fetch_guild(g.guild_id)
                    channel = guild.get_channel(g.channel_id) or await guild.fetch_channel(g.channel_id)
                    message = await channel.fetch_message(g.message_id)
                    users = set()
                    for react in message.reactions:
                        if getattr(react.emoji, "name", None) == "🎉" or react.emoji == "🎉":
                            async for u in react.users():
                                if u.bot:
                                    continue
                                users.add(u)
                    users = list(users)
                    if not users:
                        await channel.send(f"Nenhum participante no sorteio **{g.prize}**.")
                    else:
                        import random
                        winners = []
                        if len(users) <= g.winners:
                            winners = users
                        else:
                            winners = random.sample(users, g.winners)
                        mention_text = ", ".join(w.mention for w in winners)
                        await channel.send(f"🎉 Sorteio finalizado! Vencedores: {mention_text} — Prêmio: **{g.prize}**")
                    # remover do DB
                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute("DELETE FROM giveaways WHERE id = ?;", (g.id,))
                        await db.commit()
                except Exception as e:
                    logger.exception("Erro ao finalizar sorteio %s: %s", g.id, e)
    except Exception as e:
        logger.exception("Erro no giveaways_checker: %s", e)

@giveaways_checker.before_loop
async def before_giveaways():
    await bot.wait_until_ready()

# inicia a tarefa se não estiver rodando
if not giveaways_checker.is_running():
    giveaways_checker.start()

# -------------------
# Ranks / XP por mensagem
# -------------------
MESSAGE_XP_MIN = 5
MESSAGE_XP_MAX = 15

@bot.event
async def on_message(message):
    # Ignora bots
    if message.author.bot:
        return
    # Ganho de XP simples por mensagem
    try:
        guild = message.guild
        if guild:
            xp_gain = MESSAGE_XP_MIN
            # variação leve para evitar farm previsível
            xp_gain += (len(message.content) // 50)
            await db_add_xp(guild.id, message.author.id, xp_gain)
        # IA humanizada: hook para processamento de mensagens (veja a seção de IA abaixo)
        # process_ai_message(message)  <-- hook colocado abaixo
    except Exception as e:
        logger.exception("Erro no on_message XP: %s", e)
    # Processa comandos no final
    await bot.process_commands(message)

@bot.command(name="level")
async def cmd_level(ctx, member: discord.Member = None):
    member = member or ctx.author
    xp, lvl = await db_get_rank(ctx.guild.id, member.id)
    await ctx.send(f"{member.mention} — Level: {lvl} | XP: {xp}")

@bot.command(name="top")
async def cmd_top(ctx, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id, xp FROM ranks WHERE guild_id = ? ORDER BY xp DESC LIMIT ?;", (ctx.guild.id, limit))
        rows = await cursor.fetchall()
    if not rows:
        return await ctx.send("Nenhum dado de XP encontrado.")
    lines = []
    for idx, r in enumerate(rows, start=1):
        lines.append(f"{idx}. <@{r[0]}> — {r[1]} XP")
    await ctx.send("Top XP:\n" + "\n".join(lines))

# -------------------
# Backups (export / import simples)
# -------------------
@bot.command(name="backup")
@commands.is_owner()
async def cmd_backup(ctx, action: str = "export"):
    """
    Backup simples: exporta todos os dados das tabelas principais para a tabela backups (JSON).
    Uso: !backup export
         !backup list
         !backup restore <id>
    """
    action = action.lower()
    if action == "export":
        data = {}
        async with aiosqlite.connect(DB_PATH) as db:
            for table in ("users", "items", "inventories", "tickets", "ranks", "giveaways", "settings"):
                cursor = await db.execute(f"SELECT * FROM {table};")
                rows = await cursor.fetchall()
                cols = [c[0] for c in cursor.description] if cursor.description else []
                data[table] = [dict(zip(cols, r)) for r in rows]
            await db.execute("INSERT INTO backups(created_at, data) VALUES (?, ?);", (now_iso(), json.dumps(data)))
            await db.commit()
        await ctx.send("Backup exportado com sucesso.")
    elif action == "list":
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT id, created_at FROM backups ORDER BY id DESC LIMIT 10;")
            rows = await cursor.fetchall()
        if not rows:
            return await ctx.send("Nenhum backup encontrado.")
        await ctx.send("Backups:\n" + "\n".join(f"ID:{r[0]} — {r[1]}" for r in rows))
    elif action.startswith("restore"):
        parts = action.split()
        if len(parts) < 2:
            return await ctx.send("Uso: !backup restore <id>")
        bid = parts[1]
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT data FROM backups WHERE id = ?;", (bid,))
            row = await cursor.fetchone()
            if not row:
                return await ctx.send("Backup não encontrado.")
            data = json.loads(row[0])
            # Restauração é delicada: aqui só mostramos o que seria restaurado
            return await ctx.send("Restauração suportada manualmente (para evitar sobrescrever dados por acidente).")
    else:
        await ctx.send("Ação inválida. Use export | list | restore <id>")

# -------------------
# IA humanizada (esqueleto)
# -------------------
# Observação: este é um esqueleto/ponte para sua implementação de IA. Não chame APIs externas aqui sem
# configurar chaves e limites. O objetivo é integrar a função de resposta em texto e comandos.

async def process_ai_message(message: discord.Message):
    """
    Hook simples para processar mensagens com IA humanizada.
    Recomendo que você substitua o corpo desta função pela integração com o modelo/serviço que usa.
    """
    # exemplo: se a mensagem começa com "ai:" o bot responde com IA
    try:
        content = message.content.strip()
        if content.lower().startswith("ai:") or content.lower().startswith("chat:"):
            prompt = content.split(":", 1)[1].strip()
            # aqui você chamaria sua função de IA e enviaria a resposta
            # ex: resp = await call_my_ai(prompt, author=message.author, context=...)
            # await message.channel.send(resp)
            await message.channel.send("Resposta IA (esqueleto): ainda não configurada. Substitua `process_ai_message` com sua integração.")
    except Exception as e:
        logger.exception("Erro no process_ai_message: %s", e)

# Hook para chamar o processo de IA dentro do on_message
# (lembrando que on_message já chama process_commands no final)
orig_on_message = on_message  # salvar referencia anterior (definida na parte 1)
# redefinimos on_message para incluir o processamento da IA — já temos uma on_message acima; adaptamos:
@bot.event
async def on_message(message):
    # mantém o comportamento anterior (XP e processamento de comandos)
    if message.author.bot:
        return
    try:
        # XP (como na parte anterior)
        guild = message.guild
        if guild:
            xp_gain = MESSAGE_XP_MIN
            xp_gain += (len(message.content) // 50)
            await db_add_xp(guild.id, message.author.id, xp_gain)
        # IA hook
        await process_ai_message(message)
    except Exception as e:
        logger.exception("Erro no custom on_message: %s", e)
    await bot.process_commands(message)

# FIM DA PARTE 3

# -------------------
# PARTE 4 — Moderação, Configuração, Logs, Auto-Restart, Entrypoint
# -------------------

# -------------------
# Moderação
# -------------------
@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def cmd_kick(ctx, member: discord.Member, *, reason: str = None):
    if member == ctx.author:
        return await ctx.send("Você não pode expulsar a si mesmo.")
    try:
        await member.kick(reason=reason or f"Kick por {ctx.author}")
        await ctx.send(f"{member.mention} foi expulso.")
    except discord.Forbidden:
        await ctx.send("Não tenho permissão para expulsar esse membro.")

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def cmd_ban(ctx, member: discord.Member, *, reason: str = None):
    if member == ctx.author:
        return await ctx.send("Você não pode banir a si mesmo.")
    try:
        await member.ban(reason=reason or f"Ban por {ctx.author}")
        await ctx.send(f"{member.mention} foi banido.")
    except discord.Forbidden:
        await ctx.send("Não tenho permissão para banir esse membro.")

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def cmd_clear(ctx, amount: int):
    if amount <= 0:
        return await ctx.send("Quantidade inválida.")
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"Apaguei {len(deleted)-1} mensagens.", delete_after=5)

# -------------------
# Configuração do servidor
# -------------------
async def db_set_prefix(guild_id: int, prefix: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings(guild_id, prefix) VALUES (?, ?);", (guild_id, prefix))
        await db.commit()

async def db_get_prefix(guild_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT prefix FROM settings WHERE guild_id = ?;", (guild_id,))
        row = await cursor.fetchone()
        return row[0] if row else DEFAULT_PREFIX

@bot.command(name="setprefix")
@commands.has_permissions(manage_guild=True)
async def cmd_setprefix(ctx, prefix: str):
    await db_set_prefix(ctx.guild.id, prefix)
    await ctx.send(f"Prefixo atualizado para `{prefix}`")

# Para suportar prefix dinâmico
async def get_dynamic_prefix(bot, message):
    if not message.guild:
        return DEFAULT_PREFIX
    return await db_get_prefix(message.guild.id)

bot.command_prefix = get_dynamic_prefix

# -------------------
# Logs / Auditoria
# -------------------
@bot.event
async def on_member_join(member):
    logger.info(f"Membro entrou: {member} ({member.id})")
    # Você pode enviar logs para um canal específico se quiser

@bot.event
async def on_member_remove(member):
    logger.info(f"Membro saiu: {member} ({member.id})")

@bot.event
async def on_guild_join(guild):
    logger.info(f"Bot entrou no servidor: {guild.name} ({guild.id})")
    await init_db()
    await ensure_default_items()

@bot.event
async def on_guild_remove(guild):
    logger.info(f"Bot removido do servidor: {guild.name} ({guild.id})")

# -------------------
# Auto-restart / Reconexão robusta
# -------------------
async def start_loop():
    backoff = RESTART_BACKOFF
    while True:
        try:
            logger.info("Iniciando RXbot...")
            await bot.start(TOKEN)
        except discord.PrivilegedIntentsRequired as e:
            logger.critical("Intents privilegiadas não habilitadas: %s", e)
            raise SystemExit
        except KeyboardInterrupt:
            logger.info("Bot interrompido manualmente.")
            await bot.close()
            break
        except Exception as e:
            logger.exception("Bot caiu com erro: %s", e)
            try:
                await bot.close()
            except Exception:
                pass
            logger.info("Reiniciando em %s segundos...", backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 300)

# -------------------
# Entrypoint
# -------------------
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(init_db())
        loop.run_until_complete(ensure_default_items())
        loop.run_until_complete(start_loop())
    finally:
        loop.run_until_complete(bot.close())
        loop.close()

# -------------------
# FIM DO MAIN.PY
# -------------------