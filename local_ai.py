
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import logging
import threading
import time
from collections import defaultdict, deque
import random
import json

logger = logging.getLogger('LocalAI')

class LocalAI:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.model_loaded = False
        self.conversation_memory = defaultdict(lambda: deque(maxlen=10))
        
        # Modelos leves que funcionam bem no Replit
        self.available_models = {
            'gpt2-medium': 'gpt2-medium',  # 355M params - Bom para conversação
            'distilgpt2': 'distilgpt2',    # 82M params - Muito rápido
            'microsoft/DialoGPT-medium': 'microsoft/DialoGPT-medium',  # Especializado em diálogo
        }
        
        self.current_model = 'distilgpt2'  # Começar com o mais leve
        
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
        
        # Inicializar modelo em thread separada
        threading.Thread(target=self._load_model, daemon=True).start()

    def _load_model(self):
        """Carregar modelo de IA em background"""
        try:
            logger.info(f"🤖 Carregando modelo de IA local: {self.current_model}")
            
            # Configurações para usar CPU (mais estável no Replit)
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Carregar tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.current_model)
            
            # Adicionar pad_token se não existir
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Carregar modelo
            self.model = AutoModelForCausalLM.from_pretrained(
                self.current_model,
                torch_dtype=torch.float32,  # Usar float32 para CPU
                device_map="auto" if device == "cuda" else None,
                low_cpu_mem_usage=True
            )
            
            # Criar pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if device == "cuda" else -1,
                max_length=512,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            self.model_loaded = True
            logger.info(f"✅ Modelo {self.current_model} carregado com sucesso!")
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar modelo: {e}")
            self.model_loaded = False

    def is_ready(self):
        """Verificar se o modelo está pronto"""
        return self.model_loaded

    def generate_response(self, user_input, user_id=None, context=None):
        """Gerar resposta usando IA local"""
        try:
            # Se modelo não estiver carregado, usar fallback
            if not self.model_loaded:
                return self._fallback_response(user_input)
            
            # Detectar contexto da mensagem
            detected_context = self._detect_context(user_input)
            
            # Se for contexto simples, usar template rápido
            if detected_context in self.response_templates:
                return random.choice(self.response_templates[detected_context])
            
            # Construir prompt com personalidade
            prompt = self._build_prompt(user_input, user_id, context)
            
            # Gerar resposta com timeout
            response = self._generate_with_timeout(prompt, timeout=10)
            
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

    def _generate_with_timeout(self, prompt, timeout=10):
        """Gerar resposta com timeout"""
        try:
            # Usar timeout para evitar travamentos
            result = self.pipeline(
                prompt,
                max_new_tokens=150,
                num_return_sequences=1,
                temperature=0.8,
                do_sample=True,
                early_stopping=True
            )
            
            if result and len(result) > 0:
                generated_text = result[0]['generated_text']
                # Extrair apenas a resposta da Kaori
                if "Kaori:" in generated_text:
                    response = generated_text.split("Kaori:")[-1].strip()
                    return response
            
            return "Desculpe, não consegui gerar uma resposta adequada."
            
        except Exception as e:
            logger.error(f"Erro na geração: {e}")
            return "Ops! Tive um probleminha técnico. 🔧"

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
        """Trocar modelo de IA"""
        if model_name in self.available_models:
            self.current_model = self.available_models[model_name]
            self.model_loaded = False
            threading.Thread(target=self._load_model, daemon=True).start()
            return f"🔄 Trocando para modelo {model_name}..."
        else:
            return f"❌ Modelo {model_name} não disponível. Opções: {', '.join(self.available_models.keys())}"

    def get_model_info(self):
        """Informações sobre o modelo atual"""
        return {
            'current_model': self.current_model,
            'loaded': self.model_loaded,
            'available_models': list(self.available_models.keys()),
            'memory_conversations': len(self.conversation_memory)
        }

# Instância global
local_ai = LocalAI()
