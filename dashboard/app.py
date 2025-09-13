from flask import Flask, render_template, jsonify
from flask_cors import CORS
import sqlite3
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

def get_db_connection():
    """Conectar ao banco de dados do bot"""
    conn = sqlite3.connect('rxbot.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_bot_stats():
    """Obter estatísticas do bot"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Contar usuários únicos com tratamento de erro
        try:
            cursor.execute('SELECT COUNT(DISTINCT user_id) as total_users FROM users')
            result = cursor.fetchone()
            total_users = result['total_users'] if result else 0
        except Exception as e:
            print(f"Erro ao contar usuários: {e}")
            total_users = 0
        
        # Contar copinhas criadas com tratamento de erro
        try:
            cursor.execute('SELECT COUNT(*) as total_copinhas FROM copinhas')
            result = cursor.fetchone()
            total_copinhas = result['total_copinhas'] if result else 0
        except Exception as e:
            print(f"Erro ao contar copinhas: {e}")
            total_copinhas = 0
        
        # Contar tickets abertos com tratamento de erro
        try:
            cursor.execute("SELECT COUNT(*) as total_tickets FROM tickets WHERE status = 'open'")
            result = cursor.fetchone()
            total_tickets = result['total_tickets'] if result else 0
        except Exception as e:
            print(f"Erro ao contar tickets: {e}")
            total_tickets = 0
        
        # Contar giveaways com tratamento de erro
        try:
            cursor.execute('SELECT COUNT(*) as total_giveaways FROM giveaways')
            result = cursor.fetchone()
            total_giveaways = result['total_giveaways'] if result else 0
        except Exception as e:
            print(f"Erro ao contar giveaways: {e}")
            total_giveaways = 0
        
        conn.close()
        
        return {
            'total_users': total_users,
            'total_copinhas': total_copinhas,
            'total_tickets': total_tickets,
            'total_giveaways': total_giveaways,
            'total_commands': 99
        }
    except Exception as e:
        print(f"Erro geral nas estatísticas: {e}")
        return {
            'total_users': 0,
            'total_copinhas': 0,
            'total_tickets': 0,
            'total_giveaways': 0,
            'total_commands': 99
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)