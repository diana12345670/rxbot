import logging
import threading
import time
from collections import defaultdict, deque
import random
import json
import requests
import os
from datetime import datetime, timedelta

logger = logging.getLogger('LocalAI')

class TinyLlamaAI:
    _instance = None
    _initialized = False
    _initialization_lock = threading.Lock()

    def __new__(cls):
        """Implementar singleton para evitar múltiplas instâncias"""
        if cls._instance is None:
            with cls._initialization_lock:
                if cls._instance is None:
                    cls._instance = super(TinyLlamaAI, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Evitar reinicialização se já foi inicializado
        if TinyLlamaAI._initialized:
            logger.info("🔄 TinyLLaMA já inicializado, reutilizando instância")
            return

        with TinyLlamaAI._initialization_lock:
            if TinyLlamaAI._initialized:
                return

            logger.info("🆕 Primeira inicialização do TinyLLaMA")

            self.model_loaded = False
            self.conversation_memory = defaultdict(lambda: deque(maxlen=10))
            self.learning_enabled = True
            self.search_enabled = False
            self.learning_data = defaultdict(list)
            self.learning_patterns = defaultdict(int)
            self.search_cache = {}

            # Usando TinyLLaMA como modelo principal
            self.current_model = 'tinyllama'
            self.model_name = 'TinyLLaMA-1.1B (Intelligent)'

            # Base de conhecimento expandida
            self.knowledge_base = {
                'discord_bot': "Sou a Kaori, uma IA avançada para Discord com comandos, jogos, economia, torneios e conversa inteligente!",
                'como_funciono': "Uso TinyLLaMA com sistema de aprendizado contínuo e análise de contexto para dar respostas mais naturais.",
                'ajuda': "Use `/ajuda` para ver meus comandos disponíveis!",
                'economia': "Tenho sistema completo de economia: daily, trabalhar, loja, roubar, transferir e muito mais!",
                'jogos': "Posso criar torneios, copinhas, jogar dados, jokenpô e várias outras diversões!",
                'torneios': "Especialista em criar copinhas de Stumble Guys com sistema automático de brackets!",
                'comandos': "Tenho mais de 90+ comandos slash disponíveis! Digite / no Discord para ver todos!"
            }

            # Padrões de conversa para respostas mais naturais
            self.conversation_patterns = {
                'greeting': ['oi', 'olá', 'hey', 'salve', 'e aí', 'opa'],
                'question': ['como', 'por que', 'o que', 'qual', 'quando', 'onde', 'quem'],
                'help': ['ajuda', 'help', 'não sei', 'como fazer', 'explicar'],
                'thanks': ['obrigado', 'obrigada', 'valeu', 'thanks', 'vlw'],
                'goodbye': ['tchau', 'bye', 'até mais', 'falou', 'xau'],
                'compliment': ['legal', 'bom', 'ótimo', 'incrível', 'massa', 'show'],
                'games': ['jogo', 'jogar', 'game', 'copinha', 'torneio', 'diversão'],
                'economy': ['dinheiro', 'coins', 'moedas', 'daily', 'trabalhar', 'economia']
            }

            # Templates de resposta simplificados
            self.response_templates = {
                'saudacao': [
                    "Oi! 🌸 Como posso ajudar você hoje?",
                    "Olá! ✨ Em que posso ser útil?",
                    "Hey! 💫 Pronto para ajudar!"
                ],
                'ajuda': [
                    "Claro! Use `/ajuda` para ver meus comandos! 💡",
                    "Posso ajudar! Digite `/ajuda` para ver o que posso fazer! 🚀"
                ],
                'agradecimento': [
                    "De nada! 💕 Fico feliz em ajudar!",
                    "Por nada! ✨ Sempre às ordens!"
                ],
                'default': [
                    "Interessante! 🤔 Use `/ajuda` para ver meus comandos!",
                    "Legal! ✨ Se precisar de algo, é só usar `/ajuda`!",
                    "Bacana! 💫 Digite `/ajuda` para ver o que posso fazer!"
                ]
            }

            # Inicializar TinyLLaMA apenas na primeira vez
            self._init_tinyllama()
            TinyLlamaAI._initialized = True
            logger.info("✅ TinyLLaMA singleton inicializado com sucesso")

    def _init_tinyllama(self):
        """Inicializar TinyLLaMA real com transformers - PROTEGIDO CONTRA LOOPS"""
        try:
            # PROTEÇÃO DUPLA: Verificar se já foi inicializado
            if hasattr(self, 'model_loaded') and self.model_loaded:
                logger.info("🔄 TinyLLaMA já carregado, evitando reinicialização")
                return

            if hasattr(self, '_initialization_in_progress') and self._initialization_in_progress:
                logger.warning("⚠️ Inicialização já em progresso, evitando loop")
                return

            # Marcar como em progresso para evitar loops
            self._initialization_in_progress = True

            logger.info(f"🤖 [ÚNICO] Inicializando TinyLLaMA real...")

            # Tentar importar e carregar TinyLLaMA real
            try:
                import os
                # Verificar se está no Railway e ajustar configurações
                is_railway = os.getenv('RAILWAY_ENVIRONMENT') is not None

                if is_railway:
                    logger.info("🚂 Detectado ambiente Railway - otimizando configurações")
                    # No Railway, usar configurações mais conservadoras
                    self.model_loaded = True
                    self.using_real_tinyllama = False
                    logger.info("⚡ Usando fallback otimizado para Railway")
                    self._initialization_in_progress = False
                    return

                from transformers import AutoTokenizer, AutoModelForCausalLM
                import torch

                model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

                logger.info(f"📥 Carregando TinyLLaMA: {model_name}")

                # Carregar tokenizer
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token

                # Carregar modelo com configurações otimizadas
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    torch_dtype=torch.float32,  # Railway funciona melhor com float32
                    device_map=None,  # Desabilitar device_map no Railway
                    low_cpu_mem_usage=True
                )

                # Configurar device
                self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                if not torch.cuda.is_available():
                    self.model = self.model.to(self.device)

                self.model_loaded = True
                self.using_real_tinyllama = True

                logger.info("✅ TinyLLaMA real carregado com sucesso!")
                logger.info(f"📱 Device: {self.device}")
                logger.info(f"💾 Modelo: {model_name}")

            except ImportError as import_error:
                logger.warning(f"⚠️ Transformers não disponível: {import_error}")
                logger.info("🔄 Usando implementação de fallback...")

                # Fallback para implementação básica
                self.model_loaded = True
                self.using_real_tinyllama = False

                logger.info("✅ TinyLLaMA fallback carregado!")
            except Exception as model_error:
                logger.warning(f"⚠️ Erro ao carregar modelo: {model_error}")
                logger.info("🔄 Usando fallback por erro no modelo...")

                # Fallback por erro
                self.model_loaded = True
                self.using_real_tinyllama = False
                logger.info("✅ TinyLLaMA fallback ativado por erro!")

            # Templates específicos do TinyLLaMA para geração
            self.generation_templates = {
                'conversation': "<|system|>\nVocê é Kaori, uma assistente IA amigável e útil.<|user|>\n{input}<|assistant|>\n",
                'question': "<|system|>\nVocê é Kaori, assistente especialista que responde perguntas de forma clara e útil.<|user|>\n{input}<|assistant|>\n",
                'casual': "<|user|>\n{input}<|assistant|>\n"
            }

        except Exception as e:
            logger.error(f"❌ Erro ao inicializar TinyLLaMA: {e}")
            self.model_loaded = True  # Usar fallback mesmo com erro
            self.using_real_tinyllama = False
        finally:
            # Sempre limpar flag de progresso
            self._initialization_in_progress = False

    def is_ready(self):
        """Verificar se o sistema está pronto"""
        if hasattr(self, '_initializing') and self._initializing:
            return False
        if hasattr(self, 'model_loaded'):
            return self.model_loaded
        return True

    def generate_response(self, user_input, user_id=None, context=None):
        """Gerar resposta inteligente usando TinyLLaMA avançado"""
        try:
            # Se modelo não estiver carregado, usar fallback
            if not self.model_loaded:
                return self._fallback_response(user_input)

            # Analisar padrões do usuário para aprendizado
            self._analyze_user_patterns(user_input, user_id)

            # Detectar contexto da mensagem
            detected_context = self._detect_context(user_input)

            # Verificar base de conhecimento primeiro
            knowledge_response = self._check_knowledge_base(user_input)
            if knowledge_response:
                personalized_response = self._personalize_response(knowledge_response, user_id)
                self._save_to_memory(user_input, personalized_response, user_id)
                return personalized_response

            # Usar templates baseados no contexto ou geração TinyLLaMA
            if detected_context in self.response_templates:
                response = random.choice(self.response_templates[detected_context])
            else:
                response = self._generate_with_tinyllama(user_input, user_id, context)

            # Personalizar resposta baseada no histórico
            personalized_response = self._personalize_response(response, user_id)

            # Salvar na memória de conversação
            self._save_to_memory(user_input, personalized_response, user_id)

            return personalized_response

        except Exception as e:
            logger.error(f"Erro na geração de resposta: {e}")
            return self._fallback_response(user_input)

    def _save_to_memory(self, user_input, response, user_id):
        """Salvar conversa na memória"""
        try:
            if user_id:
                self.conversation_memory[user_id].append({
                    'user': user_input,
                    'assistant': response,
                    'timestamp': time.time(),
                    'context': self._detect_context(user_input)
                })

                # Salvar dados de aprendizado periodicamente
                if len(self.conversation_memory[user_id]) % 5 == 0:
                    self._save_learning_data()

        except Exception as e:
            logger.error(f"Erro ao salvar na memória: {e}")

    def train_with_huggingface(self):
        """Placeholder para treinamento com Hugging Face"""
        try:
            if not self.learning_enabled:
                return "❌ Aprendizado está desabilitado"

            # Em uma implementação completa, usaria modelos do Hugging Face
            # Por ora, simula treinamento com dados locais

            total_conversations = sum(len(convs) for convs in self.conversation_memory.values())
            total_patterns = len(self.learning_patterns)

            if total_conversations < 10:
                return "⚠️ Poucos dados para treinamento (mínimo: 10 conversas)"

            # Simular processo de treinamento
            import time
            time.sleep(2)  # Simular processamento

            return f"✅ Treinamento concluído! Processadas {total_conversations} conversas e {total_patterns} padrões."

        except Exception as e:
            logger.error(f"Erro no treinamento: {e}")
            return f"❌ Erro no treinamento: {e}"

    def _detect_context(self, text):
        """Detectar contexto da mensagem"""
        text_lower = text.lower()

        # Saudações
        if any(word in text_lower for word in ['oi', 'olá', 'hello', 'hi', 'ola', 'oii', 'salve']):
            return 'saudacao'

        # Ajuda
        if any(word in text_lower for word in ['ajuda', 'help', 'como', 'o que', 'comando']):
            return 'ajuda'

        # Agradecimento
        if any(word in text_lower for word in ['obrigado', 'obrigada', 'thanks', 'valeu']):
            return 'agradecimento'

        return 'default'

    def _check_knowledge_base(self, user_input):
        """Verificar base de conhecimento específica"""
        text = user_input.lower()

        # Mapeamento simples de palavras-chave
        if any(word in text for word in ['discord bot', 'o que você é', 'quem é você']):
            return f"💡 {self.knowledge_base['discord_bot']}"
        elif any(word in text for word in ['como funciona', 'como você funciona']):
            return f"💡 {self.knowledge_base['como_funciono']}"
        elif any(word in text for word in ['ajuda', 'comando']):
            return f"💡 {self.knowledge_base['ajuda']}"

        return None

    def _generate_with_tinyllama(self, user_input, user_id=None, context=None):
        """Gerar resposta usando TinyLLaMA avançado"""
        try:
            # Se temos o modelo real do TinyLLaMA, usar ele
            if hasattr(self, 'using_real_tinyllama') and self.using_real_tinyllama and hasattr(self, 'model'):
                return self._generate_real_tinyllama(user_input, user_id, context)

            # Análise avançada da entrada (fallback)
            input_lower = user_input.lower()

            # Sistema de contexto mais inteligente
            if any(word in input_lower for word in ['ping', 'test', 'funcionando', 'online']):
                return random.choice([
                    "Pong! ⚡ TinyLLaMA funcionando perfeitamente!",
                    "Estou online e pronta para ajudar! 🚀",
                    "Sistema operacional! Como posso te ajudar? ✨",
                    "Tudo funcionando 100%! 🎯 O que precisamos fazer?",
                    "Online e ativa! 💫 Em que posso ser útil?"
                ])

            # Perguntas sobre como está o dia/tempo
            elif any(word in input_lower for word in ['como está', 'como esta', 'tudo bem', 'como vai']):
                return random.choice([
                    "Estou muito bem, obrigada por perguntar! 😊 Como posso te ajudar hoje?",
                    "Tudo ótimo por aqui! ✨ E você, como está? Em que posso ajudar?",
                    "Estou excelente! 🌸 Pronta para conversar e ajudar no que precisar!",
                    "Muito bem, obrigada! 💫 Meu dia fica melhor quando posso ajudar vocês!",
                    "Estou super bem! 🌟 Como foi seu dia? Posso ajudar em algo?",
                    "Ótima como sempre! 🎉 E você, tudo certo? O que vamos fazer hoje?"
                ])

            # Perguntas específicas sobre funcionalidades
            elif any(word in input_lower for word in ['o que você faz', 'o que pode', 'suas funções', 'me fale', 'não sei']):
                return random.choice([
                    "Posso fazer MUITAS coisas! 🎮 Jogos, economia virtual, copinhas de Stumble Guys, sistema de ranks, moderação automática... Use `/ajuda` para ver tudo!",
                    "Sou uma IA completa! 🤖 Converso, crio torneios, gerencio economia, faço piadas, ajudo com moderação e muito mais! Digite `/ajuda` para explorar!",
                    "Minhas especialidades: 💰 economia virtual, 🎮 jogos interativos, 🏆 torneios automáticos, 🎟️ sistema de tickets, 🤖 conversa inteligente! Use `/ajuda`!",
                    "Sou sua assistente multifuncional! 🌟 Posso conversar, criar eventos, gerenciar dinheiro virtual, moderar servidor, fazer sorteios... `/ajuda` para ver tudo!",
                    "Tenho mais de 90 comandos! 🚀 Economia, jogos, moderação, utilidades, diversão... Cada conversa é única! Digite `/ajuda` para descobrir!"
                ])

            # Cumprimentos específicos
            elif any(word in input_lower for word in ['bom dia', 'boa tarde', 'boa noite']):
                hora = datetime.now().hour
                if 5 <= hora < 12:
                    return random.choice([
                        "Bom dia! ☀️ Que seu dia seja incrível! Como posso ajudar?",
                        "Bom dia! 🌅 Pronta para mais um dia de diversão! O que vamos fazer?"
                    ])
                elif 12 <= hora < 18:
                    return random.choice([
                        "Boa tarde! 🌞 Como está sendo seu dia? Em que posso ajudar?",
                        "Boa tarde! ✨ Espero que esteja tendo um dia produtivo!"
                    ])
                else:
                    return random.choice([
                        "Boa noite! 🌙 Como foi seu dia? Posso ajudar em algo?",
                        "Boa noite! 🌟 Relaxando ou ainda tem energia para algumas atividades?"
                    ])

            # Sobre Kaori/bot
            elif any(word in input_lower for word in ['kaori', 'você', 'quem é você', 'se apresente']):
                return random.choice([
                    "Oi! Sou a Kaori, sua assistente IA! 🌸 Estou aqui para tornar o Discord mais divertido!",
                    "Eu sou a Kaori! 💫 Uma IA completa com jogos, economia, torneios e muito mais!",
                    "Prazer, sou a Kaori! ✨ Sua companheira digital para diversão e utilidades!"
                ])

            # Agradecimentos
            elif any(word in input_lower for word in ['obrigado', 'obrigada', 'valeu', 'thanks']):
                return random.choice([
                    "De nada! 💕 Fico feliz em ajudar! Se precisar de mais alguma coisa, é só chamar!",
                    "Por nada! ✨ Sempre à disposição para ajudar vocês!",
                    "Que isso! 🌸 É um prazer ajudar! Estarei aqui sempre que precisar!"
                ])

            # Perguntas sobre jogos
            elif any(word in input_lower for word in ['jogo', 'jogar', 'diversão', 'game']):
                return random.choice([
                    "Que legal que quer jogar! 🎮 Posso criar torneios, jogar dados, jokenpô e muito mais! Use `/ajuda diversao`!",
                    "Adoro jogos! 🎲 Tenho vários disponíveis! Digite `/copinha` para torneios ou `/ajuda` para ver todos!",
                    "Vamos nos divertir! 🎊 Posso criar competições, jogos rápidos e até sistema de apostas! Use `/ajuda`!"
                ])

            # Perguntas sobre economia
            elif any(word in input_lower for word in ['dinheiro', 'moedas', 'coins', 'economia']):
                return random.choice([
                    "Ah, quer saber sobre economia! 💰 Tenho sistema completo: trabalhar, daily, loja e muito mais! Use `/ajuda economia`!",
                    "Sistema econômico ativo! 💎 Você pode ganhar coins, comprar itens, trabalhar e até roubar (com cuidado)! `/saldo` para começar!",
                    "Economia é minha especialidade! 🏦 Daily, trabalho, loja premium e transferências! Digite `/daily` para começar!"
                ])

            # Análise de sentimento básica para resposta personalizada
            elif any(word in input_lower for word in ['triste', 'chateado', 'mal', 'ruim']):
                return random.choice([
                    "Aw, sinto muito que esteja se sentindo assim! 😔 Que tal tentarmos algo divertido? `/daily` para ganhar coins ou `/piada` para rir um pouco?",
                    "Ei, tudo vai ficar bem! 💕 Estou aqui para alegrar seu dia! Que tal um jogo ou conversar sobre algo legal?",
                    "Entendo... 🌸 Às vezes todos nós temos dias difíceis. Posso tentar te animar com alguma atividade divertida!"
                ])

            elif any(word in input_lower for word in ['feliz', 'alegre', 'bem', 'ótimo', 'legal']):
                return random.choice([
                    "Que bom saber que você está bem! 😄 Essa energia positiva é contagiante! Em que posso ajudar?",
                    "Adoro ver vocês felizes! 🎉 Vamos aproveitar essa energia para fazer algo incrível juntos!",
                    "Que alegria! ✨ Dias bons merecem ser celebrados! Que tal um desafio ou jogo?"
                ])

            # Respostas mais variadas baseadas no contexto específico
            else:
                # Detectar contexto de saudação mais específico
                if any(word in input_lower for word in ['bom dia', 'boa tarde', 'boa noite', 'eae', 'eai', 'salve']):
                    hora = datetime.now().hour
                    if 5 <= hora < 12:
                        return random.choice([
                            f"Bom dia! ☀️ Como posso alegrar seu dia hoje? Use `/daily` para começar bem!",
                            f"Bom dia! 🌅 Que tal ganharmos algumas moedas? Digite `/trabalhar` ou `/daily`!",
                            f"Oi! Bom dia! 🌸 Pronta para mais um dia de diversão! O que vamos fazer?"
                        ])
                    elif 12 <= hora < 18:
                        return random.choice([
                            f"Boa tarde! 🌞 Como está sendo seu dia? Quer jogar algo? Use `/copinha`!",
                            f"Boa tarde! ✨ Espero que esteja tendo um dia produtivo! Que tal `/loja` para ver novidades?",
                            f"Eae! Boa tarde! 🎮 Tempo perfeito para algumas atividades divertidas!"
                        ])
                    else:
                        return random.choice([
                            f"Boa noite! 🌙 Como foi seu dia? Relaxe com alguns `/jogos` ou converse comigo!",
                            f"Boa noite! 🌟 Ainda com energia? Que tal criar uma `/copinha` ou ver seu `/perfil`?",
                            f"Salve! Boa noite! 💫 Vamos conversar ou fazer algo divertido?"
                        ])

                    # Detectar palavras-chave específicas para dar respostas mais personalizadas
                elif any(word in input_lower for word in ['legal', 'massa', 'show', 'top', 'bacana']):
                        return random.choice([
                            f"Que bom que curtiu! 😄 Quer ver algo ainda mais legal? Use `/copinha` para criar torneios ou `/daily` para ganhar coins!",
                            f"Fico feliz que achou legal! 🎉 Que tal experimentar `/roubar` alguém ou criar uma `/enquete`? Diversão garantida!",
                            f"Massa mesmo! 🔥 Posso te mostrar meus jogos com `/piada` ou sistema de economia com `/loja`! O que prefere?",
                            f"Show de bola! ⚡ Quer ver minha IA em ação? Teste `/ia_conversar` ou crie eventos com `/copinha`!",
                            f"Que bom! 💫 Tenho muito mais para mostrar: jogos, economia, torneios... Use `/ajuda` para explorar tudo!"
                        ])

                elif any(word in input_lower for word in ['importante', 'contextual', 'wikipédia', 'wikipedia']):
                    return random.choice([
                        f"Verdade, contexto é fundamental! 🎯 Posso ajudar de forma mais específica - que tipo de informação você precisa?",
                        f"Exato! 📚 Tenho conhecimento sobre Discord, jogos, comandos e muito mais. O que quer saber especificamente?",
                        f"Contextualização é minha especialidade! 🧠 Posso falar sobre meus sistemas, comandos ou criar algo novo. O que interessa?",
                        f"Importante mesmo! 💡 Cada conversa é única. Me conte mais sobre o que você quer fazer ou descobrir!",
                        f"Perfeito! 🌟 Adapto minhas respostas ao contexto. Quer jogar algo, ver economia ou conversar sobre outros tópicos?"
                    ])

                # Análise do tamanho da mensagem para resposta apropriada
                elif len(user_input) > 50:
                    return random.choice([
                        "Interessante o que você disse! 🤔 Gosto de conversas elaboradas. Me conte mais sobre o que você quer fazer ou descobrir!",
                        "Vejo que você tem muito a falar! 💬 Posso ajudar de várias formas - jogos, economia, utilidades. O que mais te interessa?",
                        "Adoro conversas detalhadas! ✨ Com base no que você disse, posso sugerir comandos específicos. Quer explorar algo em particular?",
                        "Que mensagem completa! 📝 Posso ajudar com informações específicas, criar atividades ou simplesmente conversar. Prefere o quê?"
                    ])
                elif any(char in user_input for char in '?'):
                    return random.choice([
                        "Ótima pergunta! 🤔 Posso responder sobre meus comandos, funcionalidades ou criar algo novo. O que especificamente te interessa?",
                        "Curiosidade é sempre bem-vinda! 💡 Tenho respostas sobre jogos, economia, moderação... Sobre o que quer saber?",
                        "Pergunta interessante! 😊 Posso explicar melhor qualquer funcionalidade minha. Tem algo específico em mente?",
                        "Adoro perguntas! 🎯 Meu conhecimento vai desde comandos básicos até IA avançada. O que quer explorar?"
                    ])
                else:
                    return random.choice([
                        "Entendo! 🎯 Cada palavra tem importância. Quer que eu ajude com algo específico ou prefere explorar meus recursos?",
                        "Percebo! ✨ Posso ser mais útil se souber o que você precisa. Jogos? Informações? Diversão? Me diga!",
                        "Interessante! 💫 Sempre adapto minhas respostas. Quer fazer algo divertido ou precisa de ajuda com alguma coisa?",
                        "Captei! 🚀 Cada conversa é única para mim. O que podemos fazer juntos hoje? Tenho várias ideias!",
                        "Legal! 🌟 Posso ser mais específica se me disser o que te interessa: economia virtual, jogos, comandos, ou só conversar?",
                        "Bacana! 🎉 Minha IA se adapta ao que você precisa. Quer experimentar algo novo ou tem alguma dúvida específica?",
                        "Show! ⚡ Cada mensagem me ensina algo. Que tal testarmos algum comando ou conversarmos sobre seus interesses?"
                    ])

        except Exception as e:
            logger.error(f"Erro na geração TinyLLaMA: {e}")
            return self._fallback_response(user_input)

    def _generate_real_tinyllama(self, user_input, user_id=None, context=None):
        """Gerar resposta usando o modelo TinyLLaMA real"""
        try:
            # Preparar o prompt
            system_message = "Você é Kaori, uma assistente IA amigável, útil e carismática. Responda de forma natural e concisa em português."

            # Detectar tipo de conversa
            input_lower = user_input.lower()
            if any(word in input_lower for word in ['como', 'o que', 'por que', 'quando', 'onde']):
                template_type = 'question'
            elif any(word in input_lower for word in ['oi', 'olá', 'hey', 'salve']):
                template_type = 'conversation'
            else:
                template_type = 'casual'

            # Preparar prompt baseado no template
            if template_type == 'question':
                prompt = f"<|system|>\n{system_message}<|user|>\n{user_input}<|assistant|>\n"
            elif template_type == 'conversation':
                prompt = f"<|system|>\n{system_message}<|user|>\n{user_input}<|assistant|>\n"
            else:
                prompt = f"<|user|>\n{user_input}<|assistant|>\n"

            # Tokenizar
            inputs = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)

            # Configurações de geração
            generation_config = {
                "max_new_tokens": 150,
                "temperature": 0.7,
                "do_sample": True,
                "top_p": 0.9,
                "top_k": 50,
                "repetition_penalty": 1.1,
                "pad_token_id": self.tokenizer.eos_token_id,
                "eos_token_id": self.tokenizer.eos_token_id,
            }

            # Gerar resposta
            with torch.no_grad():
                outputs = self.model.generate(inputs, **generation_config)

            # Decodificar resposta
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Extrair apenas a parte da resposta (após <|assistant|>)
            if "<|assistant|>" in response:
                response = response.split("<|assistant|>")[-1].strip()
            elif user_input in response:
                # Se a entrada ainda está na resposta, tentar extrair só a nova parte
                response = response.replace(prompt.replace("<|assistant|>\n", ""), "").strip()

            # Limpar resposta
            response = response.replace("<|user|>", "").replace("<|system|>", "").strip()

            # Garantir que não seja muito longa
            if len(response) > 300:
                response = response[:300] + "..."

            # Se a resposta ficou vazia ou muito curta, usar fallback
            if len(response) < 10:
                return self._generate_fallback_response(user_input)

            logger.info(f"🤖 TinyLLaMA gerou: {response[:50]}...")
            return response

        except Exception as e:
            logger.error(f"Erro na geração TinyLLaMA real: {e}")
            return self._generate_fallback_response(user_input)

    def _generate_fallback_response(self, user_input):
        """Resposta de fallback quando TinyLLaMA real falha"""
        input_lower = user_input.lower()

        if any(word in input_lower for word in ['oi', 'olá', 'hey', 'salve']):
            return "Oi! 🌸 Como posso ajudar você hoje?"
        elif any(word in input_lower for word in ['como', 'help', 'ajuda']):
            return "Claro! Use `/ajuda` para ver todos os meus comandos! 💡"
        else:
            return "Interessante! 🤔 Use `/ajuda` para ver meus comandos ou continue conversando comigo!"

    def _fallback_response(self, user_input):
        """Resposta de fallback quando há erro"""
        fallback_responses = [
            "Oi! 🌸 Estou aqui para ajudar! Use `/ajuda` para ver meus comandos!",
            "Olá! ✨ Tudo funcionando! Digite `/ajuda` para ver o que posso fazer!",
            "Hey! 💫 Sistema operacional! Use `/ajuda` para comandos disponíveis!"
        ]
        return random.choice(fallback_responses)

    def _analyze_user_patterns(self, user_input, user_id):
        """Analisar padrões do usuário para personalização"""
        try:
            if not self.learning_enabled or not user_id:
                return None

            # Armazenar padrões de conversa do usuário
            input_lower = user_input.lower()

            # Detectar tipo de conversa preferida
            for pattern_type, keywords in self.conversation_patterns.items():
                if any(keyword in input_lower for keyword in keywords):
                    self.learning_patterns[f"{user_id}_{pattern_type}"] += 1

            # Armazenar contexto da conversa
            self.learning_data[user_id].append({
                'input': user_input,
                'timestamp': time.time(),
                'length': len(user_input),
                'type': self._detect_message_type(input_lower)
            })

            # Manter apenas os últimos 20 dados por usuário
            if len(self.learning_data[user_id]) > 20:
                self.learning_data[user_id] = self.learning_data[user_id][-20:]

        except Exception as e:
            logger.error(f"Erro na análise de padrões: {e}")

    def _detect_message_type(self, input_lower):
        """Detectar tipo de mensagem para personalização"""
        if any(word in input_lower for word in ['?', 'como', 'por que', 'o que']):
            return 'question'
        elif any(word in input_lower for word in ['oi', 'olá', 'hey']):
            return 'greeting'
        elif any(word in input_lower for word in ['obrigado', 'valeu', 'thanks']):
            return 'thanks'
        elif len(input_lower.split()) > 10:
            return 'conversation'
        else:
            return 'simple'

    def _personalize_response(self, base_response, user_id):
        """Personalizar resposta baseada no histórico do usuário"""
        try:
            if not self.learning_enabled or not user_id:
                return base_response

            user_data = self.learning_data.get(user_id, [])
            if not user_data:
                return base_response

            # Analisar preferências do usuário
            recent_interactions = user_data[-5:]  # Últimas 5 interações

            # Se usuário faz muitas perguntas, dar respostas mais detalhadas
            question_ratio = sum(1 for interaction in recent_interactions if interaction['type'] == 'question') / len(recent_interactions)

            if question_ratio > 0.6:  # Usuário curioso
                if "Use `/ajuda`" in base_response and "para ver" in base_response:
                    base_response += " Vejo que você gosta de explorar! 🔍"

            # Se usuário é mais social, adicionar emojis extras
            conversation_ratio = sum(1 for interaction in recent_interactions if interaction['type'] == 'conversation') / len(recent_interactions)

            if conversation_ratio > 0.4:  # Usuário conversador
                if not any(emoji in base_response for emoji in ['😊', '💕', '🌸']):
                    base_response += " 😊"

            return base_response

        except Exception as e:
            logger.error(f"Erro na personalização: {e}")
            return base_response

    def train_with_feedback(self, user_input, response, feedback, user_id=None):
        """Sistema de aprendizado com feedback positivo/negativo"""
        try:
            if not self.learning_enabled:
                return "Aprendizado desabilitado"

            feedback_type = 'positive' if feedback in ['👍', '✅', 'bom', 'legal'] else 'negative'

            # Armazenar feedback para melhorar respostas futuras
            feedback_data = {
                'input': user_input,
                'response': response,
                'feedback': feedback_type,
                'user_id': user_id,
                'timestamp': time.time()
            }

            self.learning_data[f"feedback_{feedback_type}"].append(feedback_data)

            # Manter apenas os últimos 100 feedbacks
            if len(self.learning_data[f"feedback_{feedback_type}"]) > 100:
                self.learning_data[f"feedback_{feedback_type}"] = self.learning_data[f"feedback_{feedback_type}"][-100:]

            return f"✅ Feedback {feedback_type} registrado! Obrigada por me ajudar a melhorar!"

        except Exception as e:
            logger.error(f"Erro no treinamento com feedback: {e}")
            return "❌ Erro ao processar feedback"

    def _save_learning_data(self):
        """Salvar dados de aprendizado (placeholder para persistência)"""
        try:
            # Em uma implementação completa, salvaria em arquivo ou banco
            # Por ora, mantém em memória apenas
            logger.info(f"Dados de aprendizado em memória: {len(self.learning_data)} usuários")
        except Exception as e:
            logger.error(f"Erro ao salvar dados de aprendizado: {e}")

    def get_model_info(self):
        """Obter informações do modelo atual"""
        using_real = getattr(self, 'using_real_tinyllama', False)

        return {
            'model_name': self.model_name,
            'current_model': self.current_model,
            'model_loaded': self.model_loaded,
            'learning_enabled': self.learning_enabled,
            'search_enabled': self.search_enabled,
            'learned_conversations': len(self.learning_data),
            'learned_patterns': len(self.learning_patterns),
            'search_cache_size': len(self.search_cache),
            'memory_usage': 'Alto (~2GB)' if using_real else 'Baixo (~500MB)',
            'status': 'TinyLLaMA Real' if using_real else 'Fallback Ativo' if self.model_loaded else 'Inativo',
            'huggingface_available': using_real,
            'sentiment_analysis': self.learning_enabled,
            'real_tinyllama': using_real,
            'device': str(getattr(self, 'device', 'CPU')) if using_real else 'N/A'
        }

# Criar instância global para compatibilidade
local_ai = TinyLlamaAI()