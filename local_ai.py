# Sistema de IA Local usando LLaMA.cpp - blueprint:python_llamacpp
import os
import logging
import asyncio
import json
from typing import Optional, Dict, Any

# Configuração do logger
logger = logging.getLogger('LocalAI')

class LocalAI:
    """
    Sistema modular de IA local usando LLaMA.cpp
    Processa mensagens localmente sem APIs externas
    """
    
    def __init__(self):
        """Inicializa o sistema de IA local"""
        self.llama = None
        self.model_path = None
        self.current_model = "Não carregado"
        self.is_initialized = False
        self._generation_lock = asyncio.Lock()  # Proteção contra concorrência
        self.config = {
            "max_tokens": 200,
            "temperature": 0.7,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
            "n_ctx": 2048,
            "n_threads": 4,
            "verbose": False,
            "timeout": 30  # Timeout em segundos para geração
        }
        
        # Personalidade da Kaori para IA local
        self.system_prompt = """Você é a Kaori, assistente do RXBot. Seja carinhosa, útil e use emojis fofinhos. 
        Responda em português brasileiro de forma natural e amigável. Mantenha respostas concisas (máximo 2-3 frases)."""
        
        # Tentar inicializar automaticamente
        self._initialize_llama()
    
    def _initialize_llama(self):
        """Inicializa LLaMA.cpp de forma segura"""
        try:
            # Verificar se está no Railway - permitir LLaMA local
            railway_env = os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('DATABASE_URL')
            if railway_env:
                logger.info("🚂 Railway detectado - Tentando inicializar LLaMA local...")
            
            # Importar apenas quando necessário para evitar erros se não estiver instalado
            from llama_cpp import Llama
            
            # Procurar por modelos disponíveis
            model_dir = "models"
            if not os.path.exists(model_dir):
                os.makedirs(model_dir)
                logger.info("📁 Diretório 'models' criado - adicione seus modelos .gguf aqui")
            
            # Verificar se existe algum modelo .gguf
            gguf_files = [f for f in os.listdir(model_dir) if f.endswith('.gguf')]
            
            if gguf_files:
                # Usar o primeiro modelo encontrado
                self.model_path = os.path.join(model_dir, gguf_files[0])
                logger.info(f"🤖 Carregando modelo: {gguf_files[0]}")
                
                self.llama = Llama(
                    model_path=self.model_path,
                    n_ctx=self.config["n_ctx"],
                    n_threads=self.config["n_threads"],
                    verbose=self.config["verbose"]
                )
                
                self.current_model = gguf_files[0]
                self.is_initialized = True
                logger.info(f"✅ IA Local inicializada: {self.current_model}")
                
            else:
                logger.warning("⚠️ Nenhum modelo .gguf encontrado na pasta 'models'")
                logger.info("📥 Para usar IA local, baixe um modelo GGUF e coloque na pasta 'models'")
                
        except ImportError:
            logger.warning("⚠️ llama-cpp-python não instalado - IA local desabilitada")
            logger.info("💡 Para instalar: pip install llama-cpp-python")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar IA local: {e}")
    
    async def responder_ia(self, mensagem: str, use_system_prompt: bool = True) -> Optional[str]:
        """
        Função principal para processar mensagens com IA local
        
        Args:
            mensagem (str): Mensagem do usuário para processar
            use_system_prompt (bool): Se deve usar o prompt de sistema da Kaori
            
        Returns:
            Optional[str]: Resposta da IA ou None se houver erro
        """
        try:
            if not self.is_initialized:
                logger.warning("⚠️ IA local não inicializada - retornando None")
                return None
            
            # Usar lock para proteger contra concorrência
            async with self._generation_lock:
                # Preparar prompt
                if use_system_prompt:
                    full_prompt = f"{self.system_prompt}\n\nUsuário: {mensagem}\nKaori:"
                else:
                    full_prompt = mensagem
                
                # Gerar resposta usando thread com timeout
                loop = asyncio.get_event_loop()
                try:
                    response = await asyncio.wait_for(
                        loop.run_in_executor(
                            None, 
                            self._generate_response_sync, 
                            full_prompt
                        ),
                        timeout=self.config["timeout"]
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"⏱️ IA local timeout após {self.config['timeout']}s")
                    return None
                
                if response:
                    # Limpar resposta
                    response = response.strip()
                    # Remover "Kaori:" se aparecer no início
                    if response.startswith("Kaori:"):
                        response = response[6:].strip()
                        
                    logger.info(f"🤖 IA Local respondeu: {response[:50]}...")
                    return response
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro na responder_ia: {e}")
            return None
    
    def _generate_response_sync(self, prompt: str) -> Optional[str]:
        """Gera resposta de forma síncrona"""
        try:
            if not self.llama:
                return None
                
            output = self.llama(
                prompt,
                max_tokens=self.config["max_tokens"],
                temperature=self.config["temperature"],
                top_p=self.config["top_p"],
                repeat_penalty=self.config["repeat_penalty"],
                stop=["Usuario:", "Usuário:", "User:", "\n\n"],
                echo=False
            )
            
            if output and 'choices' in output and len(output['choices']) > 0:
                return output['choices'][0]['text']
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro na geração: {e}")
            return None
    
    def trocar_modelo(self, modelo_nome: str) -> bool:
        """
        Troca o modelo ativo
        
        Args:
            modelo_nome (str): Nome do arquivo .gguf do modelo
            
        Returns:
            bool: True se sucesso, False se erro
        """
        try:
            model_path = os.path.join("models", modelo_nome)
            
            if not os.path.exists(model_path):
                logger.error(f"❌ Modelo não encontrado: {modelo_nome}")
                return False
            
            # Liberar modelo atual
            if self.llama:
                del self.llama
                self.llama = None
            
            # Carregar novo modelo
            from llama_cpp import Llama
            
            self.llama = Llama(
                model_path=model_path,
                n_ctx=self.config["n_ctx"],
                n_threads=self.config["n_threads"],
                verbose=self.config["verbose"]
            )
            
            self.model_path = model_path
            self.current_model = modelo_nome
            logger.info(f"✅ Modelo trocado para: {modelo_nome}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao trocar modelo: {e}")
            return False
    
    def listar_modelos(self) -> list:
        """Lista modelos disponíveis na pasta models"""
        try:
            model_dir = "models"
            if not os.path.exists(model_dir):
                return []
            
            return [f for f in os.listdir(model_dir) if f.endswith('.gguf')]
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar modelos: {e}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status atual da IA local"""
        return {
            "inicializada": self.is_initialized,
            "modelo_atual": self.current_model,
            "modelos_disponiveis": self.listar_modelos(),
            "config": self.config
        }
    
    def set_config(self, **kwargs):
        """Atualiza configurações da IA"""
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value
                logger.info(f"🔧 Config atualizada: {key} = {value}")

# Instância global para usar em todo o bot
local_ai = LocalAI()