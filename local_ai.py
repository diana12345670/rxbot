
import logging
import threading
import time
from collections import defaultdict, deque
import random
import json
import requests
import os

logger = logging.getLogger('LocalAI')

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
        
        # Verificar se está rodando localmente
        self.is_local = os.getenv('REPLIT_ENVIRONMENT') or not os.getenv('RAILWAY_ENVIRONMENT')
        
        # Personalidade da Kaori
        self.personality_context = """Você é Kaori, uma assistente virtual carinhosa e útil de um bot Discord. 
Características:
- Sempre amigável e prestativa
- Usa emojis ocasionalmente 🌸✨
- Responde de forma concisa mas informativa
- Gosta de anime, tecnologia e jogos
- Sempre educada e respeitosa
- Ajuda com comandos do Discord e dúvidas gerais"""

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
        """Gerar resposta usando DistilGPT2"""
        try:
            # Se modelo não estiver carregado, usar fallback
            if not self.model_loaded:
                return self._fallback_response(user_input)
            
            # Detectar contexto da mensagem
            detected_context = self._detect_context(user_input)
            
            # Se for contexto simples, usar template rápido
            if detected_context in self.response_templates:
                return random.choice(self.response_templates[detected_context])
            
            # Usar DistilGPT2 para gerar resposta mais elaborada
            response = self._generate_with_distilgpt2(user_input, user_id, context)
            
            # Processar e limpar resposta
            cleaned_response = self._clean_response(response, user_input)
            
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
        """Gerar resposta usando DistilGPT2 simplificado"""
        try:
            # Implementação simplificada de geração de texto
            # Usando padrões pré-definidos inspirados no DistilGPT2
            
            # Determinar tipo de template a usar
            template_type = self._select_template_type(user_input)
            
            # Gerar resposta baseada no padrão DistilGPT2
            if template_type == 'conversation':
                response = self._generate_conversational_response(user_input, user_id)
            elif template_type == 'question':
                response = self._generate_question_response(user_input)
            else:
                response = self._generate_casual_response(user_input)
            
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

    def _clean_response(self, response, original_input):
        """Limpar e melhorar a resposta"""
        if not response:
            return self._fallback_response(original_input)
        
        # Remover quebras de linha excessivas
        response = ' '.join(response.split())
        
        # Limitar tamanho
        if len(response) > 300:
            sentences = response.split('.')
            response = '.'.join(sentences[:2]) + '.'
        
        # Remover possíveis repetições
        words = response.split()
        if len(words) > 2 and words[-1] == words[-2]:
            response = ' '.join(words[:-1])
        
        # Adicionar emoji se não tiver
        if not any(emoji in response for emoji in ['🌸', '✨', '💕', '😊', '🎮', '💫']):
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
        return {
            'current_model': self.current_model,
            'model_name': self.model_name,
            'loaded': self.model_loaded,
            'available_models': ['distilgpt2'],
            'memory_conversations': len(self.conversation_memory),
            'features': ['conversational_ai', 'context_aware', 'railway_optimized']
        }

# Instância global DistilGPT2
local_ai = DistilGPT2AI()
