
<line_number>1</line_number>
#!/usr/bin/env python3
"""
Script para configurar LLaMA automaticamente no Railway
"""
import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('LLaMA Setup')

def install_llama_cpp():
    """Instalar llama-cpp-python com configurações otimizadas"""
    try:
        logger.info("🦙 Instalando llama-cpp-python...")
        
        # Configurar variáveis de ambiente para compilação
        env = os.environ.copy()
        env['CMAKE_ARGS'] = '-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS'
        env['FORCE_CMAKE'] = '1'
        
        # Tentar instalação com wheels pré-compilados primeiro
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", 
                "llama-cpp-python==0.2.79",
                "--extra-index-url", "https://abetlen.github.io/llama-cpp-python/whl/cpu",
                "--no-cache-dir"
            ], check=True, env=env)
            logger.info("✅ llama-cpp-python instalado com wheels pré-compilados!")
            return True
        except subprocess.CalledProcessError:
            logger.warning("⚠️ Wheels pré-compilados falharam, tentando compilação local...")
            
            # Fallback: compilação local
            subprocess.run([
                sys.executable, "-m", "pip", "install", 
                "llama-cpp-python==0.2.79",
                "--no-cache-dir",
                "--force-reinstall"
            ], check=True, env=env)
            logger.info("✅ llama-cpp-python compilado localmente!")
            return True
            
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Falha na instalação: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erro inesperado: {e}")
        return False

def download_model():
    """Baixar modelo LLaMA pequeno para teste"""
    try:
        import requests
        
        # Criar diretório models se não existir
        os.makedirs('models', exist_ok=True)
        
        # Baixar modelo pequeno (Phi-3 Mini)
        model_url = "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
        model_path = "models/phi-3-mini-4k-instruct-q4.gguf"
        
        if os.path.exists(model_path):
            logger.info("📁 Modelo já existe, pulando download...")
            return True
        
        logger.info("📥 Baixando modelo Phi-3 Mini (2.4GB)...")
        logger.info("⏳ Isso pode demorar alguns minutos...")
        
        response = requests.get(model_url, stream=True)
        response.raise_for_status()
        
        with open(model_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"✅ Modelo baixado: {model_path}")
        return True
        
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
            logger.warning("⚠️ Nenhum modelo .gguf encontrado")
            return False
        
        model_path = os.path.join('models', model_files[0])
        logger.info(f"🧠 Testando modelo: {model_path}")
        
        # Carregar modelo com configurações mínimas
        llm = Llama(
            model_path=model_path,
            n_ctx=512,  # Contexto pequeno para teste
            n_threads=2,  # Poucos threads
            verbose=False
        )
        
        # Teste simples
        response = llm("Hello", max_tokens=5, echo=False)
        logger.info("✅ LLaMA funcionando corretamente!")
        logger.info(f"🧪 Teste: {response}")
        return True
        
    except ImportError:
        logger.error("❌ llama-cpp-python não encontrado")
        return False
    except Exception as e:
        logger.error(f"❌ Erro no teste: {e}")
        return False

def main():
    """Função principal"""
    logger.info("🚀 Configurando LLaMA para Railway...")
    
    # Verificar se está no Railway
    is_railway = bool(os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('DATABASE_URL'))
    logger.info(f"🌐 Ambiente: {'Railway' if is_railway else 'Local'}")
    
    # Instalar llama-cpp-python
    if not install_llama_cpp():
        logger.error("❌ Falha na instalação do LLaMA")
        sys.exit(1)
    
    # Baixar modelo se não existir
    if not os.path.exists('models') or not any(f.endswith('.gguf') for f in os.listdir('models')):
        if not download_model():
            logger.warning("⚠️ Falha no download do modelo - LLaMA funcionará sem modelos")
    
    # Testar instalação
    if test_llama():
        logger.info("🎉 LLaMA configurado com sucesso!")
        logger.info("💡 O bot agora pode usar IA local + OpenAI!")
    else:
        logger.warning("⚠️ LLaMA instalado mas com problemas - verifique os modelos")
    
    logger.info("🏁 Configuração concluída!")

if __name__ == "__main__":
    main()
