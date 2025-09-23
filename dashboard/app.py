from flask import Flask, render_template, jsonify
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import json
import os
import threading
import logging
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('Dashboard')

# Database connection pool to avoid locking issues
db_lock = threading.RLock()

# Track database connection state to avoid spam logging
_db_connection_logged = False
_db_connection_error_state = False

def get_db_connection():
    """Get PostgreSQL database connection with schema normalization"""
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
        global _db_connection_logged, _db_connection_error_state
        
        if not _db_connection_logged or _db_connection_error_state:
            cursor.execute("SELECT current_database(), current_user, current_setting('search_path');")
            result = cursor.fetchone()
            if result:
                db_name, db_user, search_path = result
                
                # Mask user details for security
                masked_user = db_user[:3] + "***" if len(db_user) > 3 else "***"
                
                if _db_connection_error_state:
                    logger.info(f"🔄 Dashboard DB Reconnected: {db_name} | User: {masked_user} | Schema: {search_path}")
                else:
                    logger.info(f"🔗 Dashboard DB Connected: {db_name} | User: {masked_user} | Schema: {search_path}")
                
                _db_connection_logged = True
                _db_connection_error_state = False
        else:
            # Still need to set search path, just don't log it
            cursor.execute("SET search_path TO public;")
        
        conn.commit()
        return conn
    except Exception as e:
        global _db_connection_error_state
        _db_connection_error_state = True
        logger.error(f"Erro ao conectar PostgreSQL: {e}")
        raise e

def execute_query(query, params=None, fetch_one=False, fetch_all=False, timeout=10):
    """Executar query PostgreSQL com melhor tratamento de erros"""
    max_retries = 3
    
    # All queries now use native PostgreSQL %s placeholders
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
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
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
                    logger.error(f"Erro PostgreSQL (tentativa {attempt + 1}): {e}")
                    if attempt == max_retries - 1:
                        raise e
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Erro na query (tentativa {attempt + 1}): {e}")
                    if attempt == max_retries - 1:
                        raise e
                finally:
                    if conn:
                        conn.close()
                        
        except Exception as e:
            logger.error(f"Erro crítico no execute_query (tentativa {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                return None
            
        # Pausa progressiva antes de tentar novamente
        time.sleep(0.1 * (attempt + 1))
    
    return None

def get_bot_stats():
    """Obter estatísticas do bot"""
    try:
        # Verificar se as tabelas existem primeiro
        total_users = 0
        total_copinhas = 0
        total_tickets = 0
        total_giveaways = 0
        
        try:
            # Verificar se tabela users existe
            test_result = execute_query("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s", ['users'], fetch_one=True)
            if test_result and test_result[0] > 0:
                result = execute_query('SELECT COUNT(DISTINCT user_id) as total_users FROM users', fetch_one=True)
                total_users = result['total_users'] if result else 0
        except Exception as e:
            logger.warning(f"Tabela users não disponível: {e}")
        
        try:
            # Verificar se tabela copinhas existe
            test_result = execute_query("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s", ['copinhas'], fetch_one=True)
            if test_result and test_result[0] > 0:
                result = execute_query('SELECT COUNT(*) as total_copinhas FROM copinhas', fetch_one=True)
                total_copinhas = result['total_copinhas'] if result else 0
        except Exception as e:
            logger.warning(f"Tabela copinhas não disponível: {e}")
        
        try:
            # Verificar se tabela tickets existe
            test_result = execute_query("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s", ['tickets'], fetch_one=True)
            if test_result and test_result[0] > 0:
                result = execute_query("SELECT COUNT(*) as total_tickets FROM tickets WHERE status = %s", ['open'], fetch_one=True)
                total_tickets = result['total_tickets'] if result else 0
        except Exception as e:
            logger.warning(f"Tabela tickets não disponível: {e}")
        
        try:
            # Verificar se tabela giveaways existe
            test_result = execute_query("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s", ['giveaways'], fetch_one=True)
            if test_result and test_result[0] > 0:
                result = execute_query('SELECT COUNT(*) as total_giveaways FROM giveaways', fetch_one=True)
                total_giveaways = result['total_giveaways'] if result else 0
        except Exception as e:
            logger.warning(f"Tabela giveaways não disponível: {e}")
        
        return {
            'total_users': total_users,
            'total_copinhas': total_copinhas,
            'total_tickets': total_tickets,
            'total_giveaways': total_giveaways,
            'total_commands': 90
        }
    except Exception as e:
        logger.error(f"Erro geral nas estatísticas: {e}")
        return {
            'total_users': 0,
            'total_copinhas': 0,
            'total_tickets': 0,
            'total_giveaways': 0,
            'total_commands': 90
        }

@app.route('/')
def home():
    """Página inicial do dashboard"""
    stats = get_bot_stats()
    return render_template('index.html', stats=stats)

@app.route('/commands')
def commands():
    """Página de comandos"""
    # Lista de comandos organizados por categoria
    commands_data = {
        'Diversão': [
            {'name': '/jokenpo', 'description': 'Jogar pedra, papel ou tesoura'},
            {'name': '/dado', 'description': 'Rolar um dado'},
            {'name': '/moeda', 'description': 'Cara ou coroa'},
            {'name': '/piada', 'description': 'Contar uma piada'},
            {'name': '/adivinhar', 'description': 'Jogo de adivinhação'},
            {'name': '/quiz', 'description': 'Quiz de conhecimento geral'}
        ],
        'Economia': [
            {'name': '/saldo', 'description': 'Ver saldo de moedas'},
            {'name': '/daily', 'description': 'Recompensa diária'},
            {'name': '/weekly', 'description': 'Recompensa semanal'},
            {'name': '/monthly', 'description': 'Recompensa mensal'},
            {'name': '/trabalhar', 'description': 'Trabalhar para ganhar dinheiro'},
            {'name': '/roubar', 'description': 'Roube coins de outro usuário'},
            {'name': '/loja', 'description': 'Ver loja de itens'},
            {'name': '/inventario', 'description': 'Ver inventário de itens'}
        ],
        'Copinha/Torneios': [
            {'name': '/copinha', 'description': 'Criar torneio de Stumble Guys'},
            {'name': '/brackets', 'description': 'Ver brackets do torneio'},
            {'name': '/definir_vencedor', 'description': 'Definir vencedor de uma partida'}
        ],
        'Moderação': [
            {'name': '/ban', 'description': 'Banir usuário do servidor'},
            {'name': '/kick', 'description': 'Expulsar usuário do servidor'},
            {'name': '/mute', 'description': 'Silenciar usuário'},
            {'name': '/unmute', 'description': 'Remover silenciamento'},
            {'name': '/clear', 'description': 'Limpar mensagens do chat'},
            {'name': '/warn', 'description': 'Advertir usuário'},
            {'name': '/ticket', 'description': 'Criar ticket de suporte'}
        ],
        'Utilidades': [
            {'name': '/ping', 'description': 'Ver latência do bot'},
            {'name': '/ajuda', 'description': 'Sistema de ajuda completo'},
            {'name': '/userinfo', 'description': 'Ver informações do usuário'},
            {'name': '/serverinfo', 'description': 'Ver informações do servidor'},
            {'name': '/avatar', 'description': 'Ver avatar do usuário'},
            {'name': '/enquete', 'description': 'Criar enquete/votação'}
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
            'question': 'Como funcionam os brackets automáticos?',
            'answer': 'Quando a copinha encher, o bot cria automaticamente os brackets, tickets privados para cada partida e embaralha os participantes aleatoriamente.'
        },
        {
            'question': 'Quem define os vencedores das partidas?',
            'answer': 'Um moderador usa o comando /definir_vencedor no ticket da partida para avançar o vencedor para a próxima fase.'
        },
        {
            'question': 'Como ganhar moedas no bot?',
            'answer': 'Use /daily (diário), /weekly (semanal), /monthly (mensal), /trabalhar, ou tente a sorte com /roubar de outros usuários!'
        },
        {
            'question': 'O que posso comprar na loja?',
            'answer': 'Use /loja para ver itens disponíveis como emblemas, títulos especiais, multiplicadores de XP e outros upgrades!'
        },
        {
            'question': 'Como criar um ticket de suporte?',
            'answer': 'Use /ticket e descreva seu problema. Um moderador será notificado e poderá ajudar você em um canal privado.'
        },
        {
            'question': 'Posso usar comandos com prefixo RX?',
            'answer': 'Sim! O bot tem sistema dual: use tanto /comando quanto RX comando. Ambos funcionam perfeitamente!'
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
                'Selecione o mapa do Stumble Guys (Block Dash, Super Slide, etc)',
                'Defina o formato: 1v1, 2v2 ou 3v3 jogadores',
                'Escolha quantos participantes: 4, 8, 16 ou 32',
                'Clique em "Criar Copinha" e pronto!',
                'Os jogadores clicam em "🎮 Participar" para se inscrever',
                'Quando encher, os brackets são criados automaticamente!'
            ]
        },
        {
            'title': 'Sistema de Economia do Bot',
            'description': 'Maximize seus ganhos e domine a economia',
            'steps': [
                'Use /daily todo dia para 100-500 coins garantidos',
                'Use /weekly uma vez por semana para bonus maior',
                'Use /monthly uma vez por mês para mega bonus',
                '/trabalhar te dá coins baseado em sua profissão',
                '/roubar outros usuários (60% chance de sucesso)',
                'Compre itens na /loja para melhorar sua experiência',
                'Verifique seu /inventario para ver seus itens',
                'Coins nunca expiram - acumule sem pressa!'
            ]
        },
        {
            'title': 'Comandos de Moderação',
            'description': 'Mantenha seu servidor organizado e seguro',
            'steps': [
                '/ban [usuário] [motivo] - Banir definitivamente',
                '/kick [usuário] [motivo] - Expulsar temporariamente', 
                '/mute [usuário] [tempo] - Silenciar por tempo',
                '/unmute [usuário] - Remover silenciamento',
                '/clear [quantidade] - Limpar mensagens (max 100)',
                '/warn [usuário] [motivo] - Dar advertência',
                '/ticket - Criar canal de suporte privado',
                'Todos os comandos são logados para auditoria'
            ]
        }
    ]
    return render_template('tutorials.html', tutorials=tutorials_data)

@app.route('/api/stats')
def api_stats():
    """API para estatísticas em tempo real"""
    stats = get_bot_stats()
    return jsonify(stats)

@app.route('/health/db')
def health_db():
    """Health check endpoint for database debugging"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get database information
        cursor.execute("SELECT current_database(), current_user, current_setting('search_path');")
        result = cursor.fetchone()
        if not result:
            return jsonify({'status': 'error', 'message': 'No database info returned'}), 500
        db_name, db_user, search_path = result
        
        # Check table existence in public schema
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        # Check for core tables
        core_tables = ['users', 'tickets', 'giveaways', 'copinhas']
        missing_tables = [table for table in core_tables if table not in tables]
        
        conn.close()
        
        # Mask sensitive information
        masked_user = db_user[:3] + "***" if len(db_user) > 3 else "***"
        
        return jsonify({
            'status': 'healthy' if not missing_tables else 'issues_detected',
            'database': db_name,
            'user': masked_user,
            'schema': search_path,
            'tables_count': len(tables),
            'core_tables_status': {
                'found': [table for table in core_tables if table in tables],
                'missing': missing_tables
            },
            'all_tables': tables[:20]  # Limit to first 20 for readability
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'database_url_set': bool(os.getenv('DATABASE_URL'))
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)