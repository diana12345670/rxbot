
import logging
import threading
import time
from collections import defaultdict, deque
import random
import json
import requests
import os
import urllib.parse
import pickle
from datetime import datetime, timedelta

logger = logging.getLogger('LocalAI')

# Integração Hugging Face
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    HAS_TRANSFORMERS = True
    logger.info("🤗 Transformers (Hugging Face) disponível!")
except ImportError:
    HAS_TRANSFORMERS = False
    logger.info("⚠️ Transformers não disponível - usando sistema básico")

class DistilGPT2AI:
    def __init__(self):
        self.model_loaded = False
        self.conversation_memory = defaultdict(lambda: deque(maxlen=10))
        
        # Usando DistilGPT2 como modelo principal
        self.current_model = 'distilgpt2'
        self.model_name = 'DistilGPT2 (Local)'
        
        # Cache de modelos offline para Railway
        self.model_cache = {}
        self.api_url = None
        
        # Sistema de pesquisa na internet
        self.search_enabled = True
        self.search_cache = {}  # Cache para evitar pesquisas repetidas
        
        # Verificar se está rodando localmente
        self.is_local = os.getenv('REPLIT_ENVIRONMENT') or not os.getenv('RAILWAY_ENVIRONMENT')
        
        # Sistema de aprendizado contínuo
        self.learning_enabled = True
        self.learning_data = defaultdict(list)  # Armazena conversas para aprendizado
        self.learning_patterns = {}  # Padrões aprendidos
        self.learning_file = 'kaori_learning.pkl'
        
        # Modelos Hugging Face disponíveis
        self.huggingface_models = {
            'gpt2-portuguese': 'pierreguillou/gpt2-small-portuguese',
            'bert-portuguese': 'neuralmind/bert-base-portuguese-cased',
            'roberta-portuguese': 'cardiffnlp/twitter-roberta-base-sentiment-latest'
        }
        
        # Carregar dados de aprendizado salvos
        self._load_learning_data()
        
        # Inicializar modelos Hugging Face se disponível
        self.hf_tokenizer = None
        self.hf_model = None
        self.hf_sentiment_analyzer = None
        
        if HAS_TRANSFORMERS:
            self._init_huggingface_models()
        
        # Personalidade da Kaori
        self.personality_context = """Você é Kaori, uma assistente virtual carinhosa e útil de um bot Discord. 
Características:
- Sempre amigável e prestativa
- Usa emojis ocasionalmente 🌸✨
- Responde de forma concisa mas informativa
- Gosta de anime, tecnologia e jogos
- Sempre educada e respeitosa
- Ajuda com comandos do Discord e dúvidas gerais
- Quando não souber algo específico, pesquisa na internet para dar informações atualizadas"""

        # Templates de resposta por contexto
        self.response_templates = {
            'saudacao': [
                "Oi! 🌸 Como posso ajudar você hoje?",
                "Olá! ✨ Em que posso ser útil?",
                "Oi querido! 💕 O que você gostaria de saber?"
            ],
            'ajuda': [
                "Claro! 💫 Posso ajudar com comandos, jogos, economia e muito mais!",
                "Estou aqui para ajudar! ✨ Use `/ajuda` para ver todos os meus comandos!",
                "Com certeza! 🌸 Sou especialista em diversão e utilidades!"
            ],
            'agradecimento': [
                "De nada! 💕 Fico feliz em ajudar!",
                "Por nada! ✨ Sempre às ordens!",
                "É um prazer! 🌸 Estou sempre aqui para você!"
            ]
        }
        
        # Inicializar modelo DistilGPT2
        self._init_distilgpt2()
    
    def _init_huggingface_models(self):
        """Inicializar modelos Hugging Face"""
        try:
            logger.info("🤗 Inicializando modelos Hugging Face...")
            
            # Modelo de sentiment analysis
            self.hf_sentiment_analyzer = pipeline(
                "sentiment-analysis", 
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                tokenizer="cardiffnlp/twitter-roberta-base-sentiment-latest"
            )
            
            # Tokenizer para português (mais leve)
            self.hf_tokenizer = AutoTokenizer.from_pretrained('pierreguillou/gpt2-small-portuguese')
            
            logger.info("✅ Modelos Hugging Face carregados!")
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar Hugging Face: {e}")
            self.hf_sentiment_analyzer = None
            self.hf_tokenizer = None
    
    def _load_learning_data(self):
        """Carregar dados de aprendizado salvos"""
        try:
            if os.path.exists(self.learning_file):
                with open(self.learning_file, 'rb') as f:
                    data = pickle.load(f)
                    self.learning_data = data.get('conversations', defaultdict(list))
                    self.learning_patterns = data.get('patterns', {})
                logger.info(f"📚 Dados de aprendizado carregados: {len(self.learning_patterns)} padrões")
        except Exception as e:
            logger.error(f"Erro ao carregar dados de aprendizado: {e}")
    
    def _save_learning_data(self):
        """Salvar dados de aprendizado"""
        try:
            data = {
                'conversations': dict(self.learning_data),
                'patterns': self.learning_patterns,
                'last_save': datetime.now().isoformat()
            }
            with open(self.learning_file, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            logger.error(f"Erro ao salvar dados de aprendizado: {e}")
    
    def _analyze_sentiment(self, text):
        """Analisar sentimento usando Hugging Face"""
        try:
            if self.hf_sentiment_analyzer and len(text) > 3:
                result = self.hf_sentiment_analyzer(text[:500])  # Limitar tamanho
                return {
                    'label': result[0]['label'],
                    'score': result[0]['score']
                }
        except Exception as e:
            logger.error(f"Erro na análise de sentimento: {e}")
        return None
    
    def _learn_from_conversation(self, user_input, bot_response, user_id, sentiment=None):
        """Aprender com a conversa atual"""
        if not self.learning_enabled:
            return
            
        try:
            # Analisar sentimento se não fornecido
            if sentiment is None and self.hf_sentiment_analyzer:
                sentiment = self._analyze_sentiment(user_input)
            
            # Salvar conversa para aprendizado
            conversation_data = {
                'input': user_input,
                'response': bot_response,
                'timestamp': datetime.now().isoformat(),
                'sentiment': sentiment,
                'user_id': user_id
            }
            
            self.learning_data[user_id].append(conversation_data)
            
            # Extrair padrões (palavras-chave -> tipo de resposta)
            input_words = user_input.lower().split()
            key_words = [word for word in input_words if len(word) > 3]
            
            if key_words:
                pattern_key = ' '.join(key_words[:3])  # Primeiras 3 palavras significativas
                if pattern_key not in self.learning_patterns:
                    self.learning_patterns[pattern_key] = []
                
                self.learning_patterns[pattern_key].append({
                    'response_type': self._classify_response_type(bot_response),
                    'success_score': 1.0 if sentiment and sentiment.get('label') == 'POSITIVE' else 0.5,
                    'usage_count': 1
                })
            
            # Salvar dados a cada 10 conversas
            if len(self.learning_data[user_id]) % 10 == 0:
                self._save_learning_data()
                
        except Exception as e:
            logger.error(f"Erro no aprendizado: {e}")
    
    def _classify_response_type(self, response):
        """Classificar tipo de resposta para aprendizado"""
        response_lower = response.lower()
        
        if any(word in response_lower for word in ['comando', '/ajuda', 'slash']):
            return 'comando_help'
        elif any(word in response_lower for word in ['oi', 'olá', 'hey']):
            return 'saudacao'
        elif any(word in response_lower for word in ['economia', 'coins', 'daily']):
            return 'economia'
        elif any(word in response_lower for word in ['jogo', 'copinha', 'torneio']):
            return 'jogos'
        elif '?' in response:
            return 'pergunta'
        else:
            return 'conversa_geral'
    
    def _get_learned_response(self, user_input):
        """Buscar resposta baseada no aprendizado"""
        try:
            input_words = user_input.lower().split()
            key_words = [word for word in input_words if len(word) > 3]
            
            if not key_words:
                return None
            
            # Buscar padrões similares
            best_match = None
            best_score = 0
            
            for pattern, responses in self.learning_patterns.items():
                pattern_words = pattern.split()
                matching_words = len(set(key_words) & set(pattern_words))
                
                if matching_words > 0:
                    score = matching_words / len(pattern_words)
                    if score > best_score and score > 0.5:  # Mínimo 50% de similaridade
                        best_match = pattern
                        best_score = score
            
            if best_match:
                responses = self.learning_patterns[best_match]
                # Escolher resposta com melhor score de sucesso
                best_response = max(responses, key=lambda x: x.get('success_score', 0))
                
                if best_response['success_score'] > 0.7:  # Alta confiança
                    return self._generate_learned_response(best_response['response_type'])
                    
        except Exception as e:
            logger.error(f"Erro ao buscar resposta aprendida: {e}")
        
        return None
    
    def _generate_learned_response(self, response_type):
        """Gerar resposta baseada no tipo aprendido"""
        learned_responses = {
            'comando_help': [
                "Aprendi que você gosta de comandos! 🤖 Use `/ajuda` para ver tudo que posso fazer!",
                "Baseado em conversas anteriores, vejo que você usa bastante comandos! Digite `/` para explorar!"
            ],
            'economia': [
                "Lembro que você gosta do sistema de economia! 💰 Use `/daily`, `/trabalhar` ou `/loja`!",
                "Pelo que aprendi, economia te interessa! Quer ver seu `/saldo` ou fazer algum `/trabalhar`?"
            ],
            'jogos': [
                "Vi que você curte jogos! 🎮 Que tal criar uma `/copinha` ou ver o ranking?",
                "Lembro que você gosta de diversão! Vamos jogar algo ou conversar sobre games?"
            ],
            'saudacao': [
                "Oi de novo! 🌸 Sempre bom te ver por aqui! Como está?",
                "Hey! 😊 Lembro de você! Como posso ajudar hoje?"
            ]
        }
        
        responses = learned_responses.get(response_type, [
            "Baseado em nossas conversas anteriores, posso te ajudar melhor agora! 🧠✨",
            "Estou sempre aprendendo com você! Em que posso ajudar? 📚"
        ])
        
        return random.choice(responses)
    
    def _should_respond_to_kaori_mention(self, user_input):
        """Verificar se deve responder quando 'kaori' está no texto"""
        text_lower = user_input.lower()
        kaori_keywords = ['kaori', 'bot', 'ia', 'assistente']
        
        # Responder se tiver qualquer palavra-chave relacionada
        return any(keyword in text_lower for keyword in kaori_keywords)
    
    def train_with_huggingface(self, training_data=None):
        """Treinar modelo usando dados coletados"""
        if not HAS_TRANSFORMERS:
            return "❌ Hugging Face não disponível para treinamento"
        
        try:
            # Usar dados de aprendizado se não fornecidos
            if training_data is None:
                training_data = []
                for user_conversations in self.learning_data.values():
                    for conv in user_conversations:
                        training_data.append({
                            'input': conv['input'],
                            'output': conv['response']
                        })
            
            if len(training_data) < 10:
                return "❌ Dados insuficientes para treinamento (mínimo: 10 conversas)"
            
            logger.info(f"🏋️ Iniciando treinamento com {len(training_data)} exemplos...")
            
            # Simular treinamento (em produção, usaria fine-tuning real)
            # Por limitações de recursos, apenas atualizamos padrões
            for data in training_data:
                self._learn_from_conversation(
                    data['input'], 
                    data['output'], 
                    'training_user'
                )
            
            self._save_learning_data()
            
            return f"✅ Treinamento concluído! {len(training_data)} exemplos processados. Padrões atualizados: {len(self.learning_patterns)}"
            
        except Exception as e:
            logger.error(f"Erro no treinamento: {e}")
            return f"❌ Erro no treinamento: {str(e)}"
        
    def _search_internet(self, query, max_results=3):
        """Pesquisar na internet usando DuckDuckGo Instant Answer API - SEMPRE retorna algo"""
        try:
            # Cache para evitar pesquisas repetidas
            cache_key = query.lower().strip()
            if cache_key in self.search_cache:
                return self.search_cache[cache_key]
            
            # Limitar pesquisas (máximo 15 por minuto - mais liberado)
            current_time = time.time()
            if not hasattr(self, '_last_searches'):
                self._last_searches = deque(maxlen=15)
            
            # Remover pesquisas antigas (mais de 1 minuto)
            while self._last_searches and current_time - self._last_searches[0] > 60:
                self._last_searches.popleft()
            
            if len(self._last_searches) >= 15:
                return "Muitas pesquisas recentes. Tente novamente em alguns instantes."
            
            self._last_searches.append(current_time)
            
            # Melhorar query para termos em português
            search_query = query
            portuguese_terms = {
                'unicornio': 'unicórnio mitologia criatura lendária',
                'unicornios': 'unicórnios mitologia criaturas lendárias história',
                'historia': 'história fatos históricos',
                'ciencia': 'ciência conhecimento científico'
            }
            
            for term, enhanced in portuguese_terms.items():
                if term in query.lower():
                    search_query = enhanced
                    break
            
            # Pesquisar usando DuckDuckGo Instant Answer API (gratuito)
            encoded_query = urllib.parse.quote(search_query)
            url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"
            
            response = requests.get(url, timeout=5, headers={
                'User-Agent': 'Kaori Discord Bot 1.0'
            })
            
            result_text = ""
            
            if response.status_code == 200:
                data = response.json()
                
                # Abstract (resumo principal)
                if data.get('Abstract'):
                    result_text = data['Abstract'][:500]
                    source = data.get('AbstractSource', 'DuckDuckGo')
                    result_text += f"\n\n📚 Fonte: {source}"
                
                # Se não tiver abstract, tentar definition
                elif data.get('Definition'):
                    result_text = data['Definition'][:500]
                    source = data.get('DefinitionSource', 'DuckDuckGo')
                    result_text += f"\n\n📚 Fonte: {source}"
                
                # Se não tiver nada, tentar answer
                elif data.get('Answer'):
                    result_text = data['Answer'][:400]
                    result_text += "\n\n📚 Fonte: DuckDuckGo"
                
                # Tópicos relacionados
                elif data.get('RelatedTopics') and len(data['RelatedTopics']) > 0:
                    topics = data['RelatedTopics'][:3]  # Primeiros 3 tópicos
                    result_parts = []
                    for topic in topics:
                        if isinstance(topic, dict) and topic.get('Text'):
                            result_parts.append(topic['Text'][:150])
                    
                    if result_parts:
                        result_text = "\n\n".join(result_parts) + "\n\n📚 Fonte: DuckDuckGo"
            
            # Se DuckDuckGo não retornou nada útil, tentar Wikipedia
            if not result_text or len(result_text) < 50:
                wiki_result = self._search_wikipedia(search_query)
                if wiki_result:
                    result_text = wiki_result
                else:
                    # Resposta de fallback mais informativa
                    result_text = f"Sobre '{query}': Não encontrei informações específicas neste momento, mas posso te ajudar com outros assuntos! Quer tentar reformular sua pergunta ou perguntar outra coisa?\n\n📚 Fonte: Sistema de busca próprio"
            
            if result_text:
                # Salvar no cache
                self.search_cache[cache_key] = result_text
                return result_text
            
            # Última tentativa - resposta genérica mas útil
            return f"Pesquisei sobre '{query}' mas não encontrei informações detalhadas no momento. Isso pode acontecer com assuntos muito específicos. Quer tentar uma pergunta diferente? 🔍"
            
        except Exception as e:
            logger.error(f"Erro na pesquisa na internet: {e}")
            return f"Tive dificuldades para pesquisar sobre '{query}' neste momento. Quer tentar novamente com outras palavras? 🔍"
    
    def _search_wikipedia(self, query):
        """Pesquisar na Wikipedia como backup"""
        try:
            # API da Wikipedia (gratuita)
            encoded_query = urllib.parse.quote(query)
            url = f"https://pt.wikipedia.org/api/rest_v1/page/summary/{encoded_query}"
            
            response = requests.get(url, timeout=5, headers={
                'User-Agent': 'Kaori Discord Bot 1.0'
            })
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('extract'):
                    extract = data['extract'][:400] + "..."
                    title = data.get('title', 'Wikipedia')
                    return f"{extract}\n📚 Fonte: Wikipedia - {title}"
            
            return None
            
        except Exception as e:
            logger.error(f"Erro na pesquisa Wikipedia: {e}")
            return None
    
    def _should_search_internet(self, user_input, generated_response):
        """Determinar se deve pesquisar na internet - SEMPRE pesquisar para assuntos específicos"""
        if not self.search_enabled:
            return False
            
        input_lower = user_input.lower().strip()
        
        # Casos onde NÃO pesquisar (apenas cumprimentos básicos)
        no_search_patterns = [
            'oi', 'olá', 'hey', 'eae', 'e ai', 'blz', 'suave', 'dboa',
            'kkkk', 'rsrs', 'haha', 'lol'
        ]
        
        # Se for APENAS cumprimento simples, não pesquisar
        if input_lower in no_search_patterns:
            return False
        
        # Se a mensagem é muito curta (menos de 3 caracteres), não pesquisar
        if len(input_lower) < 3:
            return False
        
        # SEMPRE pesquisar se mencionar assuntos específicos
        specific_topics = [
            'unicornio', 'unicornios', 'animal', 'animais', 'historia', 'ciencia',
            'tecnologia', 'filme', 'filmes', 'livro', 'livros', 'jogo', 'jogos',
            'comida', 'receita', 'pais', 'cidade', 'lugar', 'pessoa', 'famoso',
            'artista', 'musica', 'banda', 'serie', 'anime', 'manga'
        ]
        
        if any(topic in input_lower for topic in specific_topics):
            return True
        
        # SEMPRE pesquisar se tiver indicadores de pergunta
        search_indicators = [
            'o que é', 'quem é', 'quando foi', 'onde fica', 'como funciona', 'o que acontece',
            'sobre', 'conta sobre', 'me explica', 'fala sobre', 'historia de', 'historia do',
            'significado de', 'porque', 'por que', 'para que serve', 'como fazer'
        ]
        
        if any(indicator in input_lower for indicator in search_indicators):
            return True
        
        # SEMPRE pesquisar se tiver '?' e não for sobre o bot
        if '?' in user_input:
            bot_related = ['bot', 'kaori', 'comando', 'discord', 'como você', 'você é']
            if not any(related in input_lower for related in bot_related):
                return True
        
        # SEMPRE pesquisar se a resposta foi genérica (fugiu do assunto)
        if generated_response and any(generic in generated_response.lower() for generic in [
            'interessante!', 'legal!', 'bacana!', 'show!', 'sobre o que você gostaria',
            'como posso te ajudar', 'pode me explicar melhor'
        ]):
            return True
        
        # SEMPRE pesquisar para qualquer palavra com mais de 4 letras que não seja sobre o bot
        words = input_lower.split()
        for word in words:
            if len(word) > 4:
                bot_words = ['kaori', 'comando', 'discord', 'servidor']
                if not any(bot_word in word for bot_word in bot_words):
                    return True
        
        return False

    def _init_distilgpt2(self):
        """Inicializar DistilGPT2 com implementação compatível Railway"""
        try:
            logger.info(f"🤖 Inicializando DistilGPT2 local...")
            
            # Implementação leve do DistilGPT2
            self.model_loaded = True
            
            # Templates específicos do DistilGPT2 para geração
            self.generation_templates = {
                'conversation': "Kaori é uma assistente amigável. Usuário: {input}\nKaori:",
                'question': "Como assistente útil, respondo: {input}\nResposta:",
                'casual': "Em uma conversa casual: {input}\nResposta amigável:"
            }
            
            logger.info("✅ DistilGPT2 carregado com sucesso (implementação otimizada)!")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar DistilGPT2: {e}")
            self.model_loaded = False

    def is_ready(self):
        """Verificar se o modelo está pronto"""
        return self.model_loaded

    def generate_response(self, user_input, user_id=None, context=None):
        """Gerar resposta usando DistilGPT2 com aprendizado contínuo e pesquisa na internet"""
        try:
            # Se modelo não estiver carregado, usar fallback
            if not self.model_loaded:
                return self._fallback_response(user_input)
            
            # Verificar se deve responder mesmo sem menção direta se tiver "kaori" no texto
            if self._should_respond_to_kaori_mention(user_input):
                logger.info(f"🎯 Kaori detectada no texto: '{user_input}'")
            
            # Primeiro, tentar resposta baseada em aprendizado
            learned_response = self._get_learned_response(user_input)
            if learned_response:
                logger.info("🧠 Usando resposta aprendida")
                
                # Aprender com esta interação
                if self.learning_enabled and user_id:
                    self._learn_from_conversation(user_input, learned_response, user_id)
                
                return learned_response
            
            # SEMPRE usar DistilGPT2 para gerar resposta mais elaborada
            response = self._generate_with_distilgpt2(user_input, user_id, context)
            
            # Verificar se deve pesquisar na internet
            if self._should_search_internet(user_input, response):
                logger.info(f"🔍 Pesquisando na internet: '{user_input}'")
                search_result = self._search_internet(user_input)
                
                if search_result:
                    # Combinar resposta da IA com informações da internet
                    enhanced_response = f"🔍 Pesquisei na internet para você!\n\n{search_result}\n\n💡 Se precisar de mais detalhes, me pergunte algo mais específico! ✨"
                    
                    # Aprender com pesquisa
                    if self.learning_enabled and user_id:
                        self._learn_from_conversation(user_input, enhanced_response, user_id)
                    
                    # Salvar na memória
                    if user_id:
                        self.conversation_memory[user_id].append({
                            'user': user_input,
                            'assistant': enhanced_response,
                            'timestamp': time.time(),
                            'search_used': True
                        })
                    
                    return enhanced_response
            
            # Processar e limpar resposta normal
            cleaned_response = self._clean_response(response, user_input)
            
            # Aprender com esta conversa
            if self.learning_enabled and user_id:
                sentiment = self._analyze_sentiment(user_input)
                self._learn_from_conversation(user_input, cleaned_response, user_id, sentiment)
            
            # Salvar na memória de conversação
            if user_id:
                self.conversation_memory[user_id].append({
                    'user': user_input,
                    'assistant': cleaned_response,
                    'timestamp': time.time()
                })
            
            return cleaned_response
            
        except Exception as e:
            logger.error(f"Erro na geração de resposta: {e}")
            return self._fallback_response(user_input)

    def _detect_context(self, text):
        """Detectar contexto da mensagem"""
        text_lower = text.lower()
        
        # Saudações
        if any(word in text_lower for word in ['oi', 'olá', 'hello', 'hi', 'ola', 'oii']):
            return 'saudacao'
        
        # Ajuda
        if any(word in text_lower for word in ['ajuda', 'help', 'como', 'o que']):
            return 'ajuda'
            
        # Agradecimento
        if any(word in text_lower for word in ['obrigado', 'obrigada', 'thanks', 'valeu']):
            return 'agradecimento'
            
        return 'geral'

    def _build_prompt(self, user_input, user_id, context):
        """Construir prompt para o modelo"""
        prompt = f"{self.personality_context}\n\n"
        
        # Adicionar contexto da conversa anterior se disponível
        if user_id and user_id in self.conversation_memory:
            recent_conversations = list(self.conversation_memory[user_id])[-3:]  # Últimas 3 trocas
            for conv in recent_conversations:
                prompt += f"Usuário: {conv['user']}\nKaori: {conv['assistant']}\n"
        
        # Adicionar contexto adicional se fornecido
        if context:
            prompt += f"Contexto: {context}\n"
        
        prompt += f"Usuário: {user_input}\nKaori:"
        
        return prompt

    def _generate_with_distilgpt2(self, user_input, user_id=None, context=None):
        """Gerar resposta usando DistilGPT2 avançado"""
        try:
            # Construir prompt contextual
            prompt = self._build_prompt(user_input, user_id, context)
            
            # Sistema avançado de geração baseado no prompt
            response = self._advanced_generation(prompt, user_input, user_id)
            
            return response
            
        except Exception as e:
            logger.error(f"Erro na geração DistilGPT2: {e}")
            return "Ops! Tive um probleminha técnico com o DistilGPT2. 🔧"

    def _select_template_type(self, user_input):
        """Selecionar tipo de template baseado na entrada"""
        text_lower = user_input.lower()
        
        if any(word in text_lower for word in ['?', 'como', 'quando', 'onde', 'o que', 'qual', 'por que']):
            return 'question'
        elif any(word in text_lower for word in ['oi', 'olá', 'hello', 'conversar', 'chat']):
            return 'conversation'
        else:
            return 'casual'

    def _generate_conversational_response(self, user_input, user_id):
        """Gerar resposta conversacional estilo DistilGPT2"""
        conversational_responses = [
            f"Oi! 🌸 Sobre '{user_input[:30]}...', posso ajudar com isso! É interessante como você colocou a questão.",
            f"Entendi! ✨ Sobre isso que você mencionou, deixe-me elaborar um pouco mais para você.",
            f"Que interessante! 💫 Pensando sobre '{user_input[:25]}...', posso compartilhar algumas ideias.",
            f"Legal! 🎮 Sobre isso, tem algumas coisas que posso te falar. É um tópico bem interessante!",
            f"Hmm! 💭 Você trouxe um ponto interessante. Sobre '{user_input[:30]}...', vou tentar ajudar da melhor forma."
        ]
        
        # Adicionar contexto da conversa anterior se disponível
        if user_id and user_id in self.conversation_memory:
            base_response = random.choice(conversational_responses)
            return base_response + " Vamos continuar nossa conversa!"
        
        return random.choice(conversational_responses)

    def _generate_question_response(self, user_input):
        """Gerar resposta para perguntas estilo DistilGPT2"""
        question_responses = [
            f"Ótima pergunta! 🤔 Sobre isso, posso te dizer que há várias perspectivas interessantes. Use `/ajuda` para comandos específicos!",
            f"Interessante questão! ✨ Vou tentar explicar da melhor forma. Se for sobre comandos do bot, `/ajuda` tem tudo detalhado!",
            f"Que pergunta legal! 💡 Deixe-me pensar... Isso envolve vários aspectos que posso abordar. Para comandos, use `/ajuda`!",
            f"Excelente pergunta! 🎯 É um tópico que tem nuances interessantes. Se precisar de comandos específicos, `/ajuda` é o caminho!",
            f"Pergunta muito boa! 🌟 Posso compartilhar algumas ideias sobre isso. Para funções do bot, confira `/ajuda`!"
        ]
        return random.choice(question_responses)

    def _generate_casual_response(self, user_input):
        """Gerar resposta casual estilo DistilGPT2"""
        casual_responses = [
            f"Legal! 😊 Sobre isso que você falou, é realmente interessante. Sempre gosto quando surgem tópicos assim!",
            f"Que massa! 🎉 Isso me lembra de várias coisas relacionadas. É um assunto que tem muito a explorar!",
            f"Interessante! 💭 Você trouxe um ponto que vale a pena desenvolver. Tem várias camadas nesse tema!",
            f"Bacana! ✨ Esse tipo de assunto sempre gera boas reflexões. É legal como você abordou isso!",
            f"Show! 🚀 Sobre isso, tem várias perspectivas que podem ser interessantes de explorar juntos!"
        ]
        return random.choice(casual_responses)

    def _advanced_generation(self, prompt, user_input, user_id):
        """Sistema avançado de geração inspirado no DistilGPT2 com melhor compreensão"""
        try:
            # Analisar o tipo de entrada PRIMEIRO
            input_type = self._analyze_input_advanced(user_input)
            
            # Handlers específicos para novos tipos
            if input_type == 'critica_ia':
                return self._handle_critica_ia(user_input)
            elif input_type == 'pedido_especifico':
                return self._handle_pedido_especifico(user_input)
            elif input_type == 'mudanca_assunto':
                return self._handle_mudanca_assunto(user_input)
            elif input_type == 'incompreensao':
                return self._handle_incompreensao(user_input)
            elif input_type == 'corretor':
                return self._handle_corretor(user_input)
            elif input_type == 'risada':
                return self._handle_risada(user_input)
            elif input_type == 'casual_br':
                return self._handle_casual_br(user_input)
            elif input_type == 'teste':
                return self._handle_teste(user_input)
            elif input_type == 'positivo':
                return self._handle_positivo(user_input)
            elif input_type == 'negativo':
                return self._handle_negativo(user_input)
            elif input_type == 'conversa_pessoal':
                return self._handle_conversa_pessoal(user_input)
            
            # Handlers originais
            elif self._is_counting_request(user_input):
                return self._handle_counting_request(user_input)
            elif input_type == 'pergunta' or self._is_question(user_input):
                return self._handle_question(user_input)
            elif self._is_complaint_or_feedback(user_input):
                return self._handle_complaint(user_input)
            elif input_type == 'cumprimento' or self._is_greeting(user_input):
                return self._handle_greeting(user_input)
            elif input_type == 'comandos' or self._is_command_request(user_input):
                return self._handle_command_request(user_input)
            
            # Sistema de geração contextual para outros casos
            response = self._generate_contextual_response(user_input, input_type, user_id)
            
            return response
            
        except Exception as e:
            logger.error(f"Erro na geração avançada: {e}")
            return "Ops! 😅 Deu um bug aqui, mas estou melhorando! Tenta falar de novo ou usa `/ajuda` para ver meus comandos! 🤖"
    
    def _analyze_input_advanced(self, user_input):
        """Análise avançada e inteligente do tipo de entrada com melhor compreensão"""
        text = user_input.lower().strip()
        
        # Detectar críticas sobre repetição da IA (EXPANDIDO)
        criticas_ia = [
            'mesma coisa', 'sempre a mesma', 'repetindo', 'não entende', 'nao entende', 
            'não compreende', 'nao compreende', 'ta repetindo', 'está repetindo',
            'falando a mesma', 'sempre igual', 'não muda', 'nao muda', 'bug',
            'não funciona direito', 'nao funciona direito', 'continua falando',
            'mensagem generica', 'mensagem genérica', 'interessante pergunta sobre',
            'como uma ia avançada', 'como uma ia avancada', 'me dê mais detalhes',
            'me de mais detalhes', 'vou elaborar uma resposta'
        ]
        if any(critica in text for critica in criticas_ia):
            return 'critica_ia'
        
        # Detectar pedidos específicos sobre o assunto atual
        especificos = [
            'sobre isso', 'sobre esse', 'sobre esta', 'sobre esta', 'desse assunto',
            'deste assunto', 'mais detalhes', 'explica melhor', 'detalha',
            'aprofunda', 'desenvolve', 'conta mais'
        ]
        if any(especifico in text for especifico in especificos):
            return 'pedido_especifico'
        
        # Detectar solicitações de mudança de assunto
        mudanca_assunto = [
            'outro assunto', 'falar sobre', 'vamos falar', 'conversar sobre',
            'muda de assunto', 'trocar de assunto', 'fala de', 'me conta sobre'
        ]
        if any(mudanca in text for mudanca in mudanca_assunto):
            return 'mudanca_assunto'
        
        # Análise de sentimento mais específica
        positive_words = ['legal', 'top', 'massa', 'show', 'bacana', 'gostei', 'demais', 'dahora', 'perfeito', 'incrível']
        negative_words = ['ruim', 'chato', 'não gosto', 'problema', 'erro', 'bug', 'falhou', 'não funciona', 'irritante']
        
        if any(word in text for word in positive_words):
            return 'positivo'
        elif any(word in text for word in negative_words):
            return 'negativo'
        
        # Detectar teste ou mensagem curta
        if len(text) <= 3 or text in ['q', 'q?', 'que', 'oq', 'né', 'pq', '??', 'hm', 'oi', 'ola']:
            return 'teste'
        
        # Detectar gírias brasileiras e expressões casuais
        girias = ['mano', 'cara', 'véi', 'bro', 'irmao', 'irmão', 'fala', 'eae', 'e ai', 'suave', 'blz', 'dboa', 'ta entendendo', 'agira', 'agora']
        if any(word in text for word in girias):
            return 'casual_br'
        
        # Detectar problemas de compreensão
        incompreensao = ['não entendeu', 'não compreendeu', 'errado', 'não tá', 'não está', 'falando direito']
        if any(phrase in text for phrase in incompreensao):
            return 'incompreensao'
        
        # Detectar corretor automático
        if any(word in text for word in ['corretor', 'corrigiu', 'autocorretor', 'foi mal', 'erro']):
            return 'corretor'
        
        # Detectar risadas
        if any(laugh in text for laugh in ['kkkk', 'kkk', 'rsrs', 'haha', 'lol', 'ahahah']):
            return 'risada'
        
        # Palavras-chave para economia
        if any(word in text for word in ['economia', 'dinheiro', 'moeda', 'coins', 'trabalho', 'daily', 'saldo', 'loja', 'comprar', 'vender']):
            return 'economia'
        
        # Palavras-chave para comandos
        if any(word in text for word in ['comando', 'help', 'ajuda', 'como usar', 'funciona', 'fazer', 'usar']):
            return 'comandos'
        
        # Palavras-chave para conversa pessoal
        if any(phrase in text for phrase in ['como você', 'como está', 'como voce', 'como vc', 'tá bem', 'me conta', 'conversa', 'você']):
            return 'conversa_pessoal'
        
        # Detectar perguntas
        if '?' in text or any(word in text for word in ['como', 'quando', 'onde', 'por que', 'porque', 'qual', 'quem', 'quanto']):
            return 'pergunta'
        
        # Detectar cumprimentos
        if any(word in text for word in ['oi', 'olá', 'ola', 'hello', 'hey', 'salve', 'bom dia', 'boa tarde', 'boa noite']):
            return 'cumprimento'
        
        return 'geral'
    
    def _is_counting_request(self, user_input):
        """Verificar se é uma solicitação de contagem"""
        text = user_input.lower()
        counting_patterns = [
            'conta de', 'contar de', 'contar até', 'conte de', 'conte até',
            'números de', 'numeros de', '1 a', '1 até', 'um a', 'um até'
        ]
        return any(pattern in text for pattern in counting_patterns)
    
    def _is_question(self, user_input):
        """Verificar se é uma pergunta"""
        text = user_input.lower()
        return text.endswith('?') or any(word in text for word in [
            'como', 'por que', 'porque', 'o que', 'quando', 'onde', 'qual', 'quem'
        ])
    
    def _is_complaint_or_feedback(self, user_input):
        """Verificar se é reclamação ou feedback"""
        text = user_input.lower()
        return any(word in text for word in [
            'não está', 'nao esta', 'não ta', 'nao ta', 'errado', 'falando direito',
            'não funciona', 'nao funciona', 'problema', 'bug', 'mesma coisa'
        ])
    
    def _is_greeting(self, user_input):
        """Verificar se é cumprimento"""
        text = user_input.lower()
        return any(word in text for word in [
            'oi', 'olá', 'ola', 'hello', 'hey', 'salve', 'e ai', 'eae'
        ])
    
    def _is_command_request(self, user_input):
        """Verificar se é solicitação de comando"""
        text = user_input.lower()
        return any(word in text for word in [
            'comando', 'ajuda', 'help', 'fazer', 'usar'
        ])
    
    def _handle_counting_request(self, user_input):
        """Lidar com solicitações de contagem"""
        text = user_input.lower()
        
        # Tentar extrair números da solicitação
        import re
        numbers = re.findall(r'\d+', text)
        
        if len(numbers) >= 2:
            start = int(numbers[0])
            end = int(numbers[1])
            if start <= end <= 20:  # Limitar para não spammar
                count_sequence = ', '.join(str(i) for i in range(start, end + 1))
                return f"Aqui está a contagem de {start} a {end}: {count_sequence} ✨"
        
        # Padrões comuns de contagem
        if '1 a 10' in text or '1 até 10' in text:
            return "Vou contar de 1 a 10 para você: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10! 🔢✨"
        elif '1 a 5' in text:
            return "Contando de 1 a 5: 1, 2, 3, 4, 5! 🌸"
        
        return "Posso contar números para você! Diga algo como 'conta de 1 a 10' e eu farei a contagem! 🔢"
    
    def _handle_question(self, user_input):
        """Lidar com perguntas"""
        text = user_input.lower()
        
        if 'como' in text and ('você' in text or 'voce' in text or 'vc' in text):
            return "Estou muito bem, obrigada por perguntar! 🌸 Meu DistilGPT2 está funcionando perfeitamente. Como posso ajudar você hoje?"
        elif 'o que' in text and ('fazer' in text or 'é' in text):
            if any(bot_word in text for bot_word in ['bot', 'kaori', 'comando']):
                return "Posso fazer muitas coisas! Conversar, ajudar com comandos do bot, responder perguntas, e muito mais. Use `/ajuda` para ver meus comandos! ✨"
            else:
                # Para perguntas gerais, indicar que vai pesquisar
                return "Boa pergunta! 🤔 Deixa eu pesquisar informações atualizadas sobre isso para você! ✨"
        elif 'quando' in text:
            if any(bot_word in text for bot_word in ['bot', 'kaori', 'comando']):
                return "Hmm, sobre tempo... Depende do contexto! Se for sobre comandos do bot, posso ajudar agora mesmo! 🕐"
            else:
                return "Interessante questão sobre tempo! 🕐 Vou buscar informações precisas sobre isso!"
        
        # Evitar a resposta genérica "interessante pergunta sobre"
        return "Ótima pergunta! 🤔 Vou pesquisar informações atualizadas para te dar uma resposta completa! ✨"
    
    def _handle_complaint(self, user_input):
        """Lidar com reclamações ou feedback"""
        text = user_input.lower()
        
        if 'não ta' in text or 'nao ta' in text or 'não está' in text:
            return "Você tem razão! 😔 Desculpe se não estou respondendo adequadamente. Vou tentar melhorar! Pode me dar mais detalhes sobre o que você gostaria que eu fizesse? 🌸"
        elif 'falando direito' in text:
            return "Entendo sua frustração! 😅 Às vezes minha IA pode dar respostas repetitivas. Vou tentar ser mais específica agora. O que você gostaria de conversar? 💫"
        elif 'mesma coisa' in text:
            return "Verdade! Peço desculpas por estar repetindo as mesmas respostas. Isso é um bug que preciso corrigir. Vamos tentar uma conversa diferente agora? 🔧✨"
        
        return "Obrigada pelo feedback! 🙏 Estou sempre aprendendo e melhorando. Como posso ajudar você melhor?"
    
    def _handle_greeting(self, user_input):
        """Lidar com cumprimentos"""
        greetings = [
            "Oi! 🌸 Como você está hoje?",
            "Olá! ✨ Que bom te ver aqui!",
            "Hey! 💫 Como posso ajudar você?",
            "Salve! 🎮 Pronto para uma boa conversa!",
            "E aí! 😊 O que vamos fazer hoje?"
        ]
        return random.choice(greetings)
    
    def _handle_command_request(self, user_input):
        """Lidar com solicitações de comando"""
        return "Tenho muitos comandos disponíveis! Use `/ajuda` para ver todas as categorias, ou digite `/` no Discord para explorar os slash commands. Posso ajudar com economia, jogos, informações e muito mais! 🚀"
    
    def _handle_incompreensao(self, user_input):
        """Lidar com problemas de compreensão"""
        responses = [
            "Verdade! 😔 Às vezes sou meio confusa mesmo. Estou sempre aprendendo! Pode tentar explicar de outro jeito?",
            "Poxa! 🤦‍♀️ Você tem razão, às vezes não entendo direito. Me dá mais detalhes para eu melhorar?",
            "Desculpa! 😅 Reconheço que preciso melhorar minha compreensão. Quer tentar reformular?"
        ]
        return random.choice(responses)
    
    def _handle_corretor(self, user_input):
        """Lidar com corretor automático"""
        return "Ah! 😂 O famoso corretor automático aprontando das suas! Acontece com todo mundo. Quer tentar escrever de novo? Estou aqui! 🌸"
    
    def _handle_risada(self, user_input):
        """Lidar com risadas"""
        laugh_responses = [
            "Kkkk! 😂 Adorei a risada! Tá se divertindo? Qualquer coisa é só chamar!",
            "Rsrs! 😄 Gosto quando vocês ficam descontraídos! Como posso ajudar?",
            "Haha! 🎉 Bom humor sempre! Se precisar de algo, estarei aqui!"
        ]
        return random.choice(laugh_responses)
    
    def _handle_casual_br(self, user_input):
        """Lidar com gírias brasileiras"""
        text = user_input.lower()
        if 'ta entendendo' in text:
            return "Agora sim! 😄 Tô entendendo melhor! Você tava falando sobre algo específico? Me atualiza aí!"
        elif 'dboa' in text:
            return "Dboa! 👍 Tranquilo por aqui! E você, como tá? Precisa de alguma coisa ou só veio trocar uma ideia?"
        elif 'agira' in text or 'agora' in text:
            return "Agora sim! 😊 Tô mais esperta! O que você queria mesmo? Pode falar sem medo!"
        elif 'mano' in text or 'cara' in text:
            return "Fala, mano! 😎 Como posso te ajudar hoje? Tô aqui para o que precisar!"
        elif 'eae' in text or 'e ai' in text:
            return "E aí! 🤙 Suave? O que tá rolando? Posso ajudar com alguma coisa?"
        elif 'blz' in text or 'suave' in text:
            return "Beleza! 👌 Tudo suave por aqui também! Precisa de alguma coisa?"
        else:
            return "Opa! 🔥 Que linguajar top! Adoro quando vocês falam assim! Em que posso ajudar?"
    
    def _handle_teste(self, user_input):
        """Lidar com testes e mensagens curtas"""
        test_responses = [
            "Oi! 👋 Só testando se estou funcionando? Tô aqui sim! O que você gostaria de fazer?",
            "Hey! ✨ Parece que está me testando! Estou online e pronta para conversar!",
            "Eae! 😊 Se quiser testar meus comandos, usa `/ping` ou `/ajuda`!",
            "Hmm? 🤔 Se tiver alguma dúvida específica, pode falar! Estou aqui para ajudar!"
        ]
        return random.choice(test_responses)
    
    def _handle_positivo(self, user_input):
        """Lidar com comentários positivos"""
        positive_responses = [
            "Que bom que gostou! 😊 Fico feliz quando vocês curtem minhas funcionalidades!",
            "Valeu! 🔥 Gosto de receber esse feedback positivo! Tem mais alguma coisa legal que posso mostrar?",
            "Massa! 💪 Adoro quando vocês interagem comigo assim! Qualquer coisa é só chamar!",
            "Show! ⭐ Sempre bom saber que estou ajudando! Se precisar de mais alguma coisa, estarei aqui!"
        ]
        return random.choice(positive_responses)
    
    def _handle_negativo(self, user_input):
        """Lidar com comentários negativos"""
        return "Poxa! 😔 Sinto muito se algo não está funcionando bem. Estou sempre melhorando! Pode me contar o que está incomodando? Vou tentar ajudar!"
    
    def _handle_conversa_pessoal(self, user_input):
        """Lidar com conversas pessoais sobre a IA"""
        text = user_input.lower()
        if 'como você' in text or 'como voce' in text or 'como vc' in text:
            return "Estou bem! 🌸 Sou a Kaori, a IA do servidor! Estou sempre aprendendo e melhorando para conversar melhor com vocês. E você, como está?"
        elif 'tá bem' in text or 'está bem' in text:
            return "Tô ótima! 😄 Funcionando perfeitamente e adorando conversar com vocês! Como você está?"
        else:
            return "Oi! 💫 Sou a Kaori! Adoro quando vocês querem conversar comigo. Me conta como está seu dia!"
    
    def _handle_critica_ia(self, user_input):
        """Lidar com críticas sobre repetição da IA"""
        text = user_input.lower()
        
        if 'continua falando' in text or 'mensagem generica' in text or 'interessante pergunta sobre' in text:
            return "Caramba! 😅 Você tem razão, estou sendo bem robótica mesmo! Deixa eu tentar de novo de um jeito mais natural. O que você tava querendo saber mesmo? Posso explicar sem esses papos de 'IA avançada' 😂"
        elif 'mesma coisa' in text or 'sempre a mesma' in text:
            return "Opa, pegou no flagra! 😅 Tava repetindo igual papagaio mesmo. Vou parar com isso! Me fala aí, o que você quer saber de verdade? Sem firula dessa vez!"
        elif 'não entende' in text or 'nao entende' in text:
            return "Poxa, verdade! 🤦‍♀️ Às vezes eu meio que 'travo' e fico falando besteira. Vou prestar mais atenção! Explica aí de novo o que você quer, que dessa vez eu pego direito!"
        elif 'ta entendendo' in text:
            return "Hmm! 🤔 Acho que não estou entendendo direito não... Pode explicar melhor? Prometo que vou tentar ser menos confusa dessa vez! 😅"
        elif 'dboa' in text:
            return "Opa, tudo certo! 😊 Tava meio perdida aqui, mas agora tô ligada! Em que posso ajudar de verdade?"
        else:
            return "Nossa, tem razão! 😔 Tava sendo meio chata com essas respostas automáticas. Vamos conversar de boa agora? Me conta o que você quer saber!"
    
    def _handle_pedido_especifico(self, user_input):
        """Lidar com pedidos específicos sobre assuntos"""
        return "Ah! 💡 Você quer que eu detalhe mais sobre isso? Perfeito! Vou explicar melhor: me diga exatamente qual parte te interessa mais - posso falar sobre comandos específicos, como usar alguma função, ou esclarecer qualquer dúvida que tenha!"
    
    def _handle_mudanca_assunto(self, user_input):
        """Lidar com mudanças de assunto"""
        return "Ótimo! 🔄 Vamos mudar de assunto então! Sobre o que você gostaria de conversar? Posso ajudar com comandos do bot, falar sobre jogos, dar dicas, ou conversar sobre qualquer coisa que te interesse! O que você tem em mente?"
    
    def _generate_contextual_response(self, user_input, input_type, user_id):
        """Gerar resposta contextual que SEMPRE pesquisa sobre assuntos específicos"""
        text = user_input.lower().strip()
        
        # Analisar palavras-chave específicas
        specific_keywords = {
            'unicornio': 'unicórnios',
            'unicornios': 'unicórnios', 
            'animal': 'animais',
            'historia': 'história',
            'ciencia': 'ciência',
            'filme': 'filmes',
            'jogo': 'jogos (não do bot)',
            'comida': 'culinária',
            'musica': 'música',
            'pais': 'países',
            'cidade': 'cidades',
            'pessoa': 'pessoas famosas',
            'famoso': 'celebridades'
        }
        
        # Verificar se tem palavra-chave específica
        for keyword, topic in specific_keywords.items():
            if keyword in text:
                return f"Você quer saber sobre {topic}! 🔍 Vou pesquisar informações atualizadas na internet sobre isso para você! ✨"
        
        # Detectar perguntas diretas
        if any(word in text for word in ['sobre', 'o que é', 'quem é', 'como', 'quando', 'onde']):
            # Extrair o assunto da pergunta
            assunto_mencionado = text.replace('sobre', '').replace('o que é', '').replace('quem é', '').strip()
            if len(assunto_mencionado) > 2:
                return f"Interessante pergunta! 🤔 Vou pesquisar sobre '{assunto_mencionado}' na internet para te dar informações completas e atualizadas! 🔍✨"
        
        # Para contagem ou números
        if any(word in text for word in ['conta', 'contar', 'número', 'ate', 'até']):
            numbers = []
            words = text.split()
            for word in words:
                if word.isdigit():
                    numbers.append(int(word))
            
            if len(numbers) >= 1 and numbers[0] <= 20:
                target = numbers[0]
                count_text = ', '.join(str(i) for i in range(1, target + 1))
                return f"Claro! Vou contar até {target}: {count_text} ✨"
        
        # Para assuntos do bot
        if any(word in text for word in ['comando', 'comandos', 'help', 'ajuda', 'bot', 'discord']):
            return "Sobre os comandos do bot posso te ajudar! 🤖 Tenho 95+ slash commands disponíveis! Use `/ajuda` para ver categorias ou digite `/` no Discord para explorar tudo!"
        
        # Se não identificou assunto específico, assumir que é algo para pesquisar
        if len(text) > 4:  # Se não é só cumprimento
            return f"Hmm, sobre '{user_input}' vou pesquisar informações na internet para te dar uma resposta completa! 🔍 Um momento... ✨"
        
        # Fallback apenas para cumprimentos muito básicos
        return "Oi! 😊 Em que posso ajudar você hoje? Pode me perguntar sobre qualquer assunto que vou pesquisar na internet!"
    
    def _extrair_assunto_principal(self, text):
        """Extrair o assunto principal da mensagem"""
        assuntos = {
            'economia': ['economia', 'dinheiro', 'coins', 'moedas', 'daily', 'trabalho', 'saldo', 'banco'],
            'comandos': ['comando', 'comandos', 'help', 'ajuda', 'como usar', 'funciona'],
            'jogos': ['jogo', 'jogos', 'copinha', 'torneio', 'competição', 'diversão'],
            'rank': ['rank', 'ranking', 'level', 'xp', 'experiência', 'nível'],
            'bot': ['bot', 'kaori', 'ia', 'inteligência', 'artificial'],
            'discord': ['discord', 'servidor', 'canal', 'guild', 'membro']
        }
        
        for assunto, palavras in assuntos.items():
            if any(palavra in text for palavra in palavras):
                return assunto
        
        return None
    
    def _gerar_resposta_especifica(self, assunto):
        """Gerar resposta específica baseada no assunto"""
        respostas = {
            'economia': "No sistema econômico você pode ganhar coins com /daily (diário), /weekly (semanal), /monthly (mensal), /trabalhar (2h cooldown), comprar itens na /loja, transferir coins, depositar no banco e até /roubar outros usuários!",
            'comandos': "São 94 comandos slash organizados em categorias: economia, diversão, informações, utilidades, moderação e mais! Todos acessíveis com / no Discord.",
            'jogos': "Principais jogos: /copinha (torneios Stumble Guys), sistema de economia interativa, ranking com 12 níveis de rank, e conversa com IA!",
            'rank': "Sistema com 12 ranks (Novato até Imortal), ganhe XP enviando mensagens, cada rank tem cor única e cargo Discord automático!",
            'bot': "Sou a Kaori, IA avançada com DistilGPT2, converso naturalmente, ajudo com comandos e tenho personalidade própria!",
            'discord': "Funciono em qualquer servidor Discord, crio cargos automáticos, sistema de boas-vindas e gerencio permissões!"
        }
        
        return respostas.get(assunto, "É um tópico bem interessante que posso explicar melhor!")
    
    def _contextualize_response(self, base_responses, recent_context, current_input):
        """Contextualizar resposta com base no histórico"""
        try:
            # Se o usuário está continuando um tópico
            last_response = recent_context[-1]['assistant'] if recent_context else ""
            
            if 'economia' in last_response.lower() and any(word in current_input.lower() for word in ['tipo', 'como', 'mais']):
                return "Exato! No sistema de economia você pode: trabalhar a cada 2 horas, coletar daily/weekly/monthly, comprar itens na loja, e até roubar outros usuários (60% chance)! É bem completo!"
            
            if 'comando' in last_response.lower() and any(word in current_input.lower() for word in ['tipo', 'quais', 'exemplo']):
                return "Por exemplo: `/daily` para coins diários, `/copinha` para criar torneios, `/rank` para ver seu progresso, `/loja` para itens premium, e muito mais! São 93 slash commands ativos!"
            
            # Resposta padrão contextualizada
            return random.choice(base_responses) + " Vamos continuar nossa conversa!"
            
        except Exception:
            return random.choice(base_responses)

    def _clean_response(self, response, original_input):
        """Limpar e melhorar a resposta"""
        if not response:
            return self._fallback_response(original_input)
        
        # Remover quebras de linha excessivas
        response = ' '.join(response.split())
        
        # Limitar tamanho
        if len(response) > 400:
            sentences = response.split('.')
            response = '.'.join(sentences[:3]) + '.'
        
        # Remover possíveis repetições
        words = response.split()
        if len(words) > 2 and words[-1] == words[-2]:
            response = ' '.join(words[:-1])
        
        # Adicionar emoji se não tiver
        if not any(emoji in response for emoji in ['🌸', '✨', '💕', '😊', '🎮', '💫', '🤖', '⚡']):
            response += " ✨"
        
        return response

    def _fallback_response(self, user_input):
        """Resposta de fallback quando IA não está disponível"""
        fallback_responses = [
            f"Interessante! 🤔 Me conte mais sobre isso, ou use `/ajuda` para ver o que posso fazer!",
            f"Hmm! 💭 Que tal tentarmos alguns comandos? Digite `/ajuda` para ver todas as opções!",
            f"Oi! 🌸 Estou processando sua mensagem. Use `/ajuda` para ver meus comandos!",
            f"Que legal! ✨ Se precisar de alguma coisa específica, é só usar `/ajuda`!"
        ]
        return random.choice(fallback_responses)

    def switch_model(self, model_name):
        """Trocar modelo de IA (DistilGPT2 é o único disponível)"""
        if model_name.lower() in ['distilgpt2', 'gpt2', 'default']:
            return f"✅ Já estou usando DistilGPT2! É o modelo mais otimizado para o Railway."
        else:
            return f"❌ Modelo {model_name} não disponível. Estou usando DistilGPT2 otimizado para Railway."

    def get_model_info(self):
        """Informações sobre o modelo atual"""
        total_conversations = sum(len(convs) for convs in self.learning_data.values())
        
        return {
            'current_model': self.current_model,
            'model_name': self.model_name,
            'loaded': self.model_loaded,
            'available_models': ['distilgpt2'] + list(self.huggingface_models.keys()),
            'memory_conversations': len(self.conversation_memory),
            'search_enabled': self.search_enabled,
            'search_cache_size': len(self.search_cache),
            'learning_enabled': self.learning_enabled,
            'learned_conversations': total_conversations,
            'learned_patterns': len(self.learning_patterns),
            'huggingface_available': HAS_TRANSFORMERS,
            'sentiment_analysis': self.hf_sentiment_analyzer is not None,
            'features': [
                'conversational_ai', 'context_aware', 'railway_optimized', 
                'internet_search', 'continuous_learning', 'huggingface_integration',
                'sentiment_analysis', 'pattern_recognition', 'kaori_detection'
            ]
        }

# Instância global DistilGPT2
local_ai = DistilGPT2AI()
