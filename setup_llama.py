
#!/usr/bin/env python3
"""
Script para configurar LLaMA automaticamente no Replit
"""
import os
import sys
import subprocess
import logging
import requests
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('LLaMA Setup')

def install_llama_cpp():
    """Instalar llama-cpp-python com configurações otimizadas"""
    try:
        logger.info("🦙 Instalando llama-cpp-python...")
        
        # Tentar instalação com wheels pré-compilados primeiro
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", 
                "llama-cpp-python==0.2.79",
                "--extra-index-url", "https://abetlen.github.io/llama-cpp-python/whl/cpu",
                "--no-cache-dir"
            ], check=True)
            logger.info("✅ llama-cpp-python instalado com wheels pré-compilados!")
            return True
        except subprocess.CalledProcessError:
            logger.warning("⚠️ Wheels pré-compilados falharam, tentando versão padrão...")
            
            # Fallback: versão padrão do PyPI
            subprocess.run([
                sys.executable, "-m", "pip", "install", 
                "llama-cpp-python",
                "--no-cache-dir"
            ], check=True)
            logger.info("✅ llama-cpp-python instalado do PyPI!")
            return True
            
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Falha na instalação: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erro inesperado: {e}")
        return False

def download_model():
    """Baixar modelo LLaMA pequeno e otimizado para Replit"""
    try:
        # Criar diretório models se não existir
        os.makedirs('models', exist_ok=True)
        
        # Modelo TinyLlama 1.1B - Pequeno e eficiente (apenas 637MB)
        model_url = "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.q4_0.gguf"
        model_filename = "tinyllama-1.1b-chat.q4_0.gguf"
        model_path = f"models/{model_filename}"
        
        # Verificar se já existe
        if os.path.exists(model_path):
            logger.info(f"📁 Modelo já existe: {model_filename}")
            return True
        
        logger.info("📥 Baixando TinyLlama 1.1B (637MB) - otimizado para Replit...")
        logger.info("⏳ Isso pode demorar alguns minutos...")
        
        # Download com progress
        response = requests.get(model_url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(model_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Log progresso a cada 25MB
                    if downloaded % (25 * 1024 * 1024) == 0 and total_size > 0:
                        progress = (downloaded / total_size) * 100
                        mb_downloaded = downloaded / (1024*1024)
                        mb_total = total_size / (1024*1024)
                        logger.info(f"📊 {progress:.1f}% - {mb_downloaded:.1f}MB / {mb_total:.1f}MB")
        
        final_size = os.path.getsize(model_path) / (1024*1024)
        logger.info(f"✅ Modelo baixado com sucesso!")
        logger.info(f"📦 {model_filename} - {final_size:.1f}MB")
        return True
        
    except requests.RequestException as e:
        logger.error(f"❌ Erro de conexão ao baixar modelo: {e}")
        logger.info("💡 Verifique sua conexão com a internet")
        return False
    except Exception as e:
        logger.error(f"❌ Erro ao baixar modelo: {e}")
        return False

def test_llama():
    """Testar se LLaMA está funcionando"""
    try:
        from llama_cpp import Llama
        
        # Procurar modelos
        model_files = [f for f in os.listdir('models') if f.endswith('.gguf')]
        if not model_files:
            logger.warning("⚠️ Nenhum modelo .gguf encontrado após download")
            return False
        
        model_path = os.path.join('models', model_files[0])
        logger.info(f"🧠 Testando modelo: {model_files[0]}")
        
        # Carregar modelo com configurações mínimas para teste
        llm = Llama(
            model_path=model_path,
            n_ctx=256,     # Contexto pequeno para teste
            n_threads=2,   # Poucos threads
            verbose=False
        )
        
        # Teste simples
        logger.info("🧪 Executando teste...")
        response = llm("Hello", max_tokens=10, echo=False)
        
        if response and 'choices' in response:
            test_text = response['choices'][0]['text'].strip()
            logger.info(f"✅ LLaMA funcionando! Resposta: '{test_text[:50]}'")
            return True
        else:
            logger.warning("⚠️ LLaMA carregou mas resposta inválida")
            return False
        
    except ImportError:
        logger.error("❌ llama-cpp-python não encontrado")
        return False
    except Exception as e:
        logger.error(f"❌ Erro no teste: {e}")
        return False

def main():
    """Função principal"""
    logger.info("🚀 Configurando LLaMA Local para o RXBot...")
    
    # Verificar ambiente
    logger.info(f"🌐 Executando em: {os.getcwd()}")
    logger.info(f"🐍 Python: {sys.version}")
    
    # Instalar llama-cpp-python se necessário
    try:
        import llama_cpp
        logger.info("✅ llama-cpp-python já instalado")
    except ImportError:
        logger.info("📦 Instalando llama-cpp-python...")
        if not install_llama_cpp():
            logger.error("❌ Falha na instalação do LLaMA")
            sys.exit(1)
    
    # Baixar modelo se necessário
    model_files = []
    if os.path.exists('models'):
        model_files = [f for f in os.listdir('models') if f.endswith('.gguf')]
    
    if not model_files:
        logger.info("📥 Nenhum modelo encontrado - iniciando download...")
        if not download_model():
            logger.error("❌ Falha no download do modelo")
            sys.exit(1)
    else:
        logger.info(f"📁 Modelos encontrados: {', '.join(model_files)}")
    
    # Testar instalação
    if test_llama():
        logger.info("🎉 LLaMA configurado com sucesso!")
        logger.info("💡 O RXBot agora pode usar:")
        logger.info("   • OpenAI ChatGPT (já ativo)")
        logger.info("   • IA Local LLaMA (agora disponível)")
        logger.info("   • Sistema híbrido automático")
    else:
        logger.warning("⚠️ LLaMA instalado mas com problemas")
        logger.info("🔄 Tente reiniciar o bot para recarregar")
    
    logger.info("🏁 Configuração concluída!")

if __name__ == "__main__":
    main()
