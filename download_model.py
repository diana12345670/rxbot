
#!/usr/bin/env python3
"""
Script para baixar modelo GGUF pequeno para IA local
Modelo: TinyLlama-1.1B-Chat-v1.0 (menos de 1GB)
"""

import os
import requests
import sys
from pathlib import Path

def download_model():
    """Baixa modelo TinyLlama otimizado para Railway"""
    
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    # Modelo pequeno e eficiente - TinyLlama 1.1B Q4_K_M (cerca de 700MB)
    model_url = "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.q4_k_m.gguf"
    model_name = "tinyllama-1.1b-chat-v1.0.q4_k_m.gguf"
    model_path = models_dir / model_name
    
    if model_path.exists():
        print(f"✅ Modelo já existe: {model_name}")
        return True
    
    print(f"📥 Baixando modelo: {model_name}")
    print(f"🔗 URL: {model_url}")
    print("⏳ Isso pode levar alguns minutos...")
    
    try:
        response = requests.get(model_url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(model_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\r📥 Progresso: {progress:.1f}% ({downloaded // 1024 // 1024}MB/{total_size // 1024 // 1024}MB)", end="")
        
        print(f"\n✅ Modelo baixado com sucesso: {model_name}")
        print(f"📁 Localização: {model_path.absolute()}")
        print(f"📊 Tamanho: {model_path.stat().st_size // 1024 // 1024}MB")
        return True
        
    except requests.RequestException as e:
        print(f"❌ Erro ao baixar modelo: {e}")
        if model_path.exists():
            model_path.unlink()  # Remove arquivo parcial
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def list_models():
    """Lista modelos disponíveis"""
    models_dir = Path("models")
    if not models_dir.exists():
        print("📁 Pasta models não existe")
        return
    
    gguf_files = list(models_dir.glob("*.gguf"))
    if not gguf_files:
        print("⚠️ Nenhum modelo .gguf encontrado")
    else:
        print("📋 Modelos disponíveis:")
        for model in gguf_files:
            size_mb = model.stat().st_size // 1024 // 1024
            print(f"  • {model.name} ({size_mb}MB)")

if __name__ == "__main__":
    print("🤖 Configurador de IA Local - RXBot")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_models()
    else:
        success = download_model()
        if success:
            print("\n🎉 Configuração concluída!")
            print("💡 A IA local agora funcionará no Railway")
            list_models()
        else:
            print("\n❌ Falha na configuração")
            sys.exit(1)
