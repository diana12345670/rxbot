# rxbot_railway_ready.py
"""
Versão refatorada do seu main.py pronta para rodar em ambientes como Railway (Free).
Alterações principais:
- Removeu o esqueleto de IA (comentários e hooks removidos).
- Tickets continuam: criação de canal (quando possível) e confirmação/fechamento por reação (🔒).
- Loja e inventário consertados e robustos (busca case-insensitive, uso seguro do inventário).
- Armazenamento em SQLite via aiosqlite (arquivo DB local). Atenção: em Railway Free o filesystem é efêmero — para persistência use o volume persistente/plugin.
- Tasks de background mantidas (sorteios) mas sem loops bloqueantes extras.
- Prefix dinâmico por guild, variáveis via .env.

Como usar:
- Configure as variáveis de ambiente: TOKEN (obrigatório), OWNER_ID (opcional), DB_PATH (opcional)
- Instale dependências: discord.py[voice]? (ou py-cord/nextcord conforme preferir), aiosqlite, python-dotenv
- Execute: python rxbot_railway_ready.py

Observação importante para Railway Free:
- O arquivo SQLite (db padrão rxbot.db) ficará no filesystem do container que pode ser reiniciado/recortado. Para persistência, ative volumes persistentes do Railway ou use um plugin DB (Postgres) e adaptar as queries.
"""

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

# Carrega .env
load_dotenv()

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO),
                    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("rxbot")

# Config
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    logger.critical("TOKEN não definido nas variáveis de ambiente. Abortando.")
    raise SystemExit("Defina a variável TOKEN")

DB_PATH = os.getenv("DB_PATH", "rxbot.db")
DEFAULT_PREFIX = os.getenv("DEFAULT_PREFIX", "!")
OWNER_ID = int(os.getenv("OWNER_ID")) if os.getenv("OWNER_ID") else None

# Intents
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix=DEFAULT_PREFIX, intents=intents)
# remover help default para personalizar
bot.remove_command("help")

# Data models
@dataclass
class Item:
    id: int
    name: str
    description: str
    price: int
    effect: Optional[str]

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
# DB inicialização
# -------------------
async def init_db():
    logger.info("Inicializando DB em %s", DB_PATH)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
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
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
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
    logger.info("DB pronta.")

# -------------------
# DB helpers
# -------------------
async def db_ensure_user_full(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id, coins, xp, level, last_daily) VALUES (?, 0, 0, 1, NULL);", (user_id,))
        await db.commit()

async def db_get_coins(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT coins FROM users WHERE user_id = ?;", (user_id,))
        row = await cur.fetchone()
        return int(row[0]) if row else 0

async def db_add_coins(user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id, coins) VALUES(?, 0);", (user_id,))
        await db.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?;", (amount, user_id))
        await db.commit()

async def db_subtract_coins(user_id: int, amount: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT coins FROM users WHERE user_id = ?;", (user_id,))
        row = await cur.fetchone()
        if not row or int(row[0]) < amount:
            return False
        await db.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?;", (amount, user_id))
        await db.commit()
        return True

# Items / loja / inventario
async def db_get_items() -> List[Item]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, name, description, price, effect FROM items ORDER BY id;")
        rows = await cur.fetchall()
        return [Item(*row) for row in rows]

async def db_get_item_by_name(name: str) -> Optional[Item]:
    # busca case-insensitive e permite correspondência parcial
    like = f"%{name.strip()}%"
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, name, description, price, effect FROM items WHERE name LIKE ? COLLATE NOCASE LIMIT 1;", (like,))
        row = await cur.fetchone()
        return Item(*row) if row else None

async def db_insert_item(name: str, description: str, price: int, effect: Optional[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO items(name,description,price,effect) VALUES (?, ?, ?, ?);", (name, description, price, effect))
        await db.commit()

async def db_add_item_to_inventory(user_id: int, item_id: int, qty: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO inventories(user_id, item_id, quantity) VALUES (?, ?, ?) ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity;", (user_id, item_id, qty))
        await db.commit()

async def db_get_inventory(user_id: int) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT i.item_id, it.name, it.description, it.effect, i.quantity FROM inventories i JOIN items it ON i.item_id = it.id WHERE i.user_id = ? AND i.quantity > 0 ORDER BY it.name;",
            (user_id,))
        rows = await cur.fetchall()
        return [{"item_id": r[0], "name": r[1], "description": r[2], "effect": r[3], "quantity": r[4]} for r in rows]

async def db_decrement_inventory(user_id: int, item_id: int, qty: int = 1) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT quantity FROM inventories WHERE user_id = ? AND item_id = ?;", (user_id, item_id))
        row = await cur.fetchone()
        if not row or int(row[0]) < qty:
            return False
        await db.execute("UPDATE inventories SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?;", (qty, user_id, item_id))
        await db.commit()
        return True

# Ranks / XP
async def db_add_xp(guild_id: int, user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO ranks(guild_id, user_id, xp, level) VALUES (?, ?, 0, 0);", (guild_id, user_id))
        await db.execute("UPDATE ranks SET xp = xp + ? WHERE guild_id = ? AND user_id = ?;", (amount, guild_id, user_id))
        await db.commit()

async def db_get_rank(guild_id: int, user_id: int) -> Tuple[int, int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT xp, level FROM ranks WHERE guild_id = ? AND user_id = ?;", (guild_id, user_id))
        row = await cur.fetchone()
        return (int(row[0]), int(row[1])) if row else (0, 0)

# Giveaways
async def db_create_giveaway(guild_id: int, channel_id: int, message_id: int, prize: str, winners: int, ends_at: datetime) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("INSERT INTO giveaways(guild_id, channel_id, message_id, prize, winners, ends_at) VALUES (?, ?, ?, ?, ?, ?);", (guild_id, channel_id, message_id, prize, winners, ends_at.isoformat()))
        await db.commit()
        return cur.lastrowid

async def db_get_active_giveaways() -> List[Giveaway]:
    out = []
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id,guild_id,channel_id,message_id,prize,winners,ends_at FROM giveaways;")
        rows = await cur.fetchall()
        for r in rows:
            try:
                ends_at = datetime.fromisoformat(r[6])
            except Exception:
                ends_at = datetime.utcnow()
            out.append(Giveaway(id=r[0], guild_id=r[1], channel_id=r[2], message_id=r[3], prize=r[4], winners=int(r[5]), ends_at=ends_at))
    return out

# Utils
def format_coins(n: int) -> str:
    return f"{n:,}"

def now_iso() -> str:
    return datetime.utcnow().isoformat()

# Default items
async def ensure_default_items():
    logger.info("Inserindo itens padrão se necessário...")
    defaults = [
        ("PequenaPoção", "Restaura 50 coins quando usado.", 100, "give_coins:50"),
        ("GrandePoção", "Restaura 200 coins quando usado.", 350, "give_coins:200"),
        ("BoletoPremium", "Dá 1000 coins (promoção)", 800, "give_coins:1000"),
        ("SorteToken", "Aumenta chances em sorteios.", 250, "sorte_token:1"),
    ]
    for name, desc, price, effect in defaults:
        await db_insert_item(name, desc, price, effect)
    logger.info("Itens padrão assegurados.")

# -------------------
# Eventos e comandos
# -------------------
@bot.event
async def on_ready():
    logger.info(f"Bot pronto: {bot.user} (ID:{bot.user.id})")
    await init_db()
    await ensure_default_items()
    if not giveaways_checker.is_running():
        giveaways_checker.start()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Argumentos faltando. Use `!help`.")
        return
    logger.exception("Erro em comando: %s", error)
    try:
        await ctx.send("Ocorreu um erro ao executar o comando. Verifique os logs.")
    except Exception:
        pass

# Ping / help
@bot.command(name="ping")
async def ping_cmd(ctx):
    await ctx.send(f"Pong! Latência: {round(bot.latency*1000)}ms")

@bot.command(name="help")
async def help_cmd(ctx):
    txt = (
        "**RXbot - comandos**\n"
        "`!ping` - teste\n"
        "`!saldo` - mostra saldo\n"
        "`!loja` - ver loja\n"
        "`!comprar <nome>` - comprar item\n"
        "`!inventario` - ver inventário\n"
        "`!usar <nome>` - usar item\n"
        "`!ticket <motivo>` - abrir ticket\n"
        "`!sorteio <minutos> <vencedores> <prêmio>` - criar sorteio (moderação)\n"
    )
    await ctx.send(txt)

# Economia: saldo, pay, daily
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
    last = None
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT last_daily FROM users WHERE user_id = ?;", (user_id,))
        row = await cur.fetchone()
        last = row[0] if row and row[0] else None
    now = datetime.utcnow()
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
        except Exception:
            last_dt = datetime.utcfromtimestamp(0)
        if now - last_dt < timedelta(hours=24):
            rem = timedelta(hours=24) - (now - last_dt)
            hh = rem.seconds // 3600
            mm = (rem.seconds % 3600) // 60
            return await ctx.send(f"Você já coletou o daily. Volte em {rem.days}d {hh}h {mm}m.")
    reward = 500
    await db_add_coins(user_id, reward)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET last_daily = ? WHERE user_id = ?;", (now.isoformat(), user_id))
        await db.commit()
    await ctx.send(f"Você coletou o daily e ganhou {format_coins(reward)} coins!")

# Loja / inventário
@bot.command(name="loja")
async def cmd_loja(ctx):
    items = await db_get_items()
    if not items:
        return await ctx.send("A loja está vazia.")
    embed = discord.Embed(title="Loja RXbot", description="Itens disponíveis", color=discord.Color.blurple())
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
    # aplica efeito simples (apenas give_coins/boost_xp/grant_role suportados)
    res_msg = await apply_item_effect_ctx(ctx, user_id, item.effect)
    ok = await db_decrement_inventory(user_id, item.id, 1)
    if not ok:
        return await ctx.send("Erro ao consumir o item (quantidade insuficiente).")
    await ctx.send(f"Você usou **{item.name}** — {res_msg}")

# Administrador: adicionar item
@bot.command(name="additem")
@commands.is_owner()
async def cmd_additem(ctx, price: int, name: str, *, description: str = ""):
    await db_insert_item(name, description, price, None)
    await ctx.send(f"Item **{name}** adicionado com preço {format_coins(price)}.")

# Efeitos de item
async def apply_item_effect_ctx(ctx: commands.Context, user_id: int, effect: Optional[str]) -> str:
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

# -------------------
# Tickets com confirmação por emoji
# -------------------
@bot.command(name="ticket")
async def cmd_ticket(ctx, *, motivo: str = "Sem motivo fornecido"):
    guild = ctx.guild
    user = ctx.author
    await db_ensure_user_full(user.id)
    if not guild:
        return await ctx.send("Tickets só podem ser abertos em servidores.")
    chan_name = f"ticket-{user.name}".lower()[:90]
    existing = discord.utils.get(guild.channels, name=chan_name)
    if existing:
        await ctx.send(f"Você já tem um ticket aberto: {existing.mention}")
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR IGNORE INTO tickets(guild_id, channel_id, user_id, status, created_at) VALUES (?, ?, ?, 'open', ?);", (guild.id, existing.id, user.id, now_iso()))
            await db.commit()
        return
    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        chan = await guild.create_text_channel(chan_name, overwrites=overwrites, reason="Abertura de ticket")
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO tickets(guild_id, channel_id, user_id, status, created_at) VALUES (?, ?, ?, 'open', ?);", (guild.id, chan.id, user.id, now_iso()))
            await db.commit()
        msg = await chan.send(f"{user.mention} abriu um ticket: {motivo}\nStaff pode reagir com 🔒 para fechar este ticket.")
        await msg.add_reaction("🔒")
        await ctx.send(f"Ticket criado: {chan.mention}")
    except discord.Forbidden:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO tickets(guild_id, channel_id, user_id, status, created_at) VALUES (?, ?, ?, 'open', ?);", (guild.id, 0, user.id, now_iso()))
            await db.commit()
        await ctx.send("Não tenho permissão para criar canais. Ticket registrado no sistema, aguarde um staff responder.")

@bot.event
async def on_reaction_add(reaction, user):
    # Ignorar bots
    if user.bot:
        return
    try:
        message = reaction.message
        if str(reaction.emoji) == "🔒":
            channel = message.channel
            # verificar se canal corresponde a um ticket aberto no DB
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute("SELECT id, user_id, status FROM tickets WHERE channel_id = ? AND guild_id = ?;", (channel.id, channel.guild.id))
                row = await cur.fetchone()
                if not row:
                    return
                ticket_id, owner_id, status = row
            # só staff (manage_channels) ou dono do ticket podem fechar
            member = channel.guild.get_member(user.id) or await channel.guild.fetch_member(user.id)
            is_staff = member.guild_permissions.manage_channels
            is_owner = (user.id == owner_id)
            if not (is_staff or is_owner):
                # opcional: remover reação de quem não pode fechar
                try:
                    await message.remove_reaction(reaction.emoji, user)
                except Exception:
                    pass
                return
            # fechar ticket: marcar DB e deletar canal (se possível)
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE tickets SET status = 'closed' WHERE id = ?;", (ticket_id,))
                await db.commit()
            try:
                await channel.send("Ticket fechado pelo staff. Este canal será deletado em 5 segundos.")
                await asyncio.sleep(5)
                await channel.delete(reason="Ticket fechado via reação 🔒")
            except Exception:
                try:
                    await channel.send("Ticket marcado como fechado no banco. (Não foi possível deletar o canal.)")
                except Exception:
                    pass
    except Exception as e:
        logger.exception("Erro no on_reaction_add: %s", e)

@bot.command(name="close")
@commands.has_permissions(manage_channels=True)
async def cmd_close_ticket(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM tickets WHERE channel_id = ? AND guild_id = ? AND status = 'open';", (channel.id, ctx.guild.id))
        row = await cur.fetchone()
        if not row:
            return await ctx.send("Canal não é um ticket conhecido ou já está fechado.")
        ticket_id = row[0]
        await db.execute("UPDATE tickets SET status = 'closed' WHERE id = ?;", (ticket_id,))
        await db.commit()
    try:
        await channel.send("Ticket será fechado pelo staff.")
        await asyncio.sleep(2)
        await channel.delete(reason="Ticket fechado por comando")
    except Exception:
        await ctx.send("Ticket marcado como fechado no banco. (Não foi possível deletar o canal.)")

@bot.command(name="tickets")
@commands.has_permissions(manage_guild=True)
async def cmd_list_tickets(ctx, status: str = "open"):
    status = status.lower()
    if status not in ("open", "closed", "all"):
        return await ctx.send("Status inválido. Use 'open', 'closed' ou 'all'.")
    async with aiosqlite.connect(DB_PATH) as db:
        if status == "all":
            cur = await db.execute("SELECT id, guild_id, channel_id, user_id, status, created_at FROM tickets WHERE guild_id = ? ORDER BY created_at DESC;", (ctx.guild.id,))
        else:
            cur = await db.execute("SELECT id, guild_id, channel_id, user_id, status, created_at FROM tickets WHERE guild_id = ? AND status = ? ORDER BY created_at DESC;", (ctx.guild.id, status))
        rows = await cur.fetchall()
    if not rows:
        return await ctx.send("Nenhum ticket encontrado.")
    lines = []
    for r in rows:
        ch = f"<#{r[2]}>" if r[2] and r[2] != 0 else "—"
        lines.append(f"ID:{r[0]} | User:{r[3]} | Canal:{ch} | Status:{r[4]} | Criado:{r[5]}")
    out = "\n".join(lines[:100])
    await ctx.send(f"Tickets:\n```
{out}
```")

# -------------------
# Giveaways (sorteios) - background checker
# -------------------
@giveaways_checker.before_loop
async def before_giveaways():
    await bot.wait_until_ready()

@giveaways_checker.loop(seconds=30.0)
async def giveaways_checker_func():
    # wrapper para compatibilidade; a tasks.loop abaixo já implementa a lógica.
    pass

@tasks.loop(seconds=30)
async def giveaways_checker():
    try:
        now = datetime.utcnow()
        active = await db_get_active_giveaways()
        for g in active:
            if g.ends_at <= now:
                try:
                    guild = bot.get_guild(g.guild_id) or await bot.fetch_guild(g.guild_id)
                    channel = guild.get_channel(g.channel_id) or await guild.fetch_channel(g.channel_id)
                    message = await channel.fetch_message(g.message_id)
                    users = set()
                    for react in message.reactions:
                        if getattr(react.emoji, 'name', None) == '🎉' or react.emoji == '🎉':
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
                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute("DELETE FROM giveaways WHERE id = ?;", (g.id,))
                        await db.commit()
                except Exception as e:
                    logger.exception("Erro ao finalizar sorteio %s: %s", g.id, e)
    except Exception as e:
        logger.exception("Erro no giveaways_checker: %s", e)

@bot.command(name="sorteio")
@commands.has_permissions(manage_guild=True)
async def cmd_create_giveaway(ctx, tempo_minutos: int, winners: int, *, prize: str):
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

# -------------------
# XP por mensagem
# -------------------
MESSAGE_XP_MIN = 5

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    try:
        guild = message.guild
        if guild:
            xp_gain = MESSAGE_XP_MIN + (len(message.content) // 50)
            await db_add_xp(guild.id, message.author.id, xp_gain)
    except Exception as e:
        logger.exception("Erro no on_message XP: %s", e)
    await bot.process_commands(message)

@bot.command(name="level")
async def cmd_level(ctx, member: discord.Member = None):
    member = member or ctx.author
    xp, lvl = await db_get_rank(ctx.guild.id, member.id)
    await ctx.send(f"{member.mention} — Level: {lvl} | XP: {xp}")

@bot.command(name="top")
async def cmd_top(ctx, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, xp FROM ranks WHERE guild_id = ? ORDER BY xp DESC LIMIT ?;", (ctx.guild.id, limit))
        rows = await cur.fetchall()
    if not rows:
        return await ctx.send("Nenhum dado de XP encontrado.")
    lines = [f"{i+1}. <@{r[0]}> — {r[1]} XP" for i, r in enumerate(rows)]
    await ctx.send("Top XP:\n" + "\n".join(lines))

# -------------------
# Backup (simples)
# -------------------
@bot.command(name="backup")
@commands.is_owner()
async def cmd_backup(ctx, action: str = "export"):
    action = action.lower()
    if action == "export":
        data = {}
        async with aiosqlite.connect(DB_PATH) as db:
            for table in ("users", "items", "inventories", "tickets", "ranks", "giveaways", "settings"):
                cur = await db.execute(f"SELECT * FROM {table};")
                rows = await cur.fetchall()
                cols = [c[0] for c in cur.description] if cur.description else []
                data[table] = [dict(zip(cols, r)) for r in rows]
            await db.execute("INSERT INTO backups(created_at, data) VALUES (?, ?);", (now_iso(), json.dumps(data)))
            await db.commit()
        await ctx.send("Backup exportado com sucesso.")
    elif action == "list":
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT id, created_at FROM backups ORDER BY id DESC LIMIT 10;")
            rows = await cur.fetchall()
        if not rows:
            return await ctx.send("Nenhum backup encontrado.")
        await ctx.send("Backups:\n" + "\n".join(f"ID:{r[0]} — {r[1]}" for r in rows))
    else:
        await ctx.send("Ação inválida. Use export | list")

# -------------------
# Config prefix dinâmico
# -------------------
async def db_set_prefix(guild_id: int, prefix: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings(guild_id, prefix) VALUES (?, ?);", (guild_id, prefix))
        await db.commit()

async def db_get_prefix(guild_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT prefix FROM settings WHERE guild_id = ?;", (guild_id,))
        row = await cur.fetchone()
        return row[0] if row else DEFAULT_PREFIX

async def get_dynamic_prefix(bot_, message):
    if not message.guild:
        return DEFAULT_PREFIX
    return await db_get_prefix(message.guild.id)

bot.command_prefix = get_dynamic_prefix

# -------------------
# Entrypoint
# -------------------
if __name__ == '__main__':
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.exception("Erro fatal ao iniciar o bot: %s", e)
