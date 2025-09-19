# 🚂 Guia de Deploy no Railway - Kaori

## ✅ Problemas Corrigidos

### 1. **Deadlock no Banco de Dados**
- ✅ Corrigido sistema de locks que causava travamento
- ✅ Melhorado execute_query com tratamento de erro
- ✅ Removido uso direto de db_lock em funções async

### 2. **Sistema de Copinhas/Torneios**
- ✅ Corrigido problema após primeira rodada
- ✅ Sistema de vencedores funcionando corretamente
- ✅ Criação automática de próximas fases
- ✅ Notificações e canais de partida funcionando

### 3. **Configuração para Railway**
- ✅ Suporte automático PostgreSQL/SQLite
- ✅ Detecção de ambiente Railway
- ✅ Flask + Bot Discord funcionando juntos

## 🚀 Instruções de Deploy

### Passo 1: Preparar o Código
```bash
# Certifique-se que todos os arquivos estão presentes:
# - rxbot/main.py (bot principal)
# - rxbot/dashboard/ (dashboard web)
# - requirements.txt
# - Procfile
# - runtime.txt  
# - railway.json
```

### Passo 2: Criar Projeto no Railway
1. Acesse [railway.app](https://railway.app)
2. Faça login com GitHub
3. Clique em "New Project"
4. Conecte seu repositório GitHub

### Passo 3: Configurar Variáveis de Ambiente
No Railway, vá em **Variables** e adicione:

#### 🔑 **Obrigatórias:**
```
TOKEN=seu_token_do_discord_bot_aqui
PORT=5000
```

#### 🗄️ **Banco de Dados (Automático):**
O Railway pode adicionar PostgreSQL automaticamente:
- Vá em **Add Service** → **Database** → **PostgreSQL**
- A variável `DATABASE_URL` será criada automaticamente
- O bot detecta automaticamente e usa PostgreSQL

#### ⚙️ **Opcionais:**
```
RAILWAY_ENVIRONMENT_NAME=production
DEBUG=false
```

### Passo 4: Deploy
1. O Railway fará deploy automaticamente após conectar o repo
2. Verifique os logs em **Deployments**
3. O bot estará online quando aparecer: "🤖 RXbot está online!"

### Passo 5: Verificar Funcionamento

#### ✅ **Dashboard Web:**
- Acesse a URL do seu projeto Railway
- Deve mostrar o dashboard do bot
- API de estatísticas funcionando

#### ✅ **Bot Discord:**
- Bot aparece online no Discord
- Comandos slash funcionando
- Sistema de copinhas operacional

## 🔧 Comandos Essenciais

### **Testar Localmente:**
```bash
# Instalar dependências
pip install -r requirements.txt

# Definir variáveis locais
export TOKEN="seu_token_aqui"
export PORT="5000"

# Executar
python rxbot/main.py
```

### **Logs no Railway:**
```bash
# Ver logs em tempo real
railway logs --follow

# Ver logs recentes
railway logs
```

## 🏆 Sistema de Copinhas - Como Funciona

### **Criar Copinha:**
```
/copinha
- Escolher nome, mapa, formato (1v1, 2v2, 3v3)
- Participantes se inscrevem clicando no botão
- Quando encher, brackets são criados automaticamente
```

### **Funcionamento Automático:**
1. **Inscrições** → Jogadores clicam para participar
2. **Primeira Fase** → Brackets criados, tickets de partida gerados
3. **Moderador define vencedores** → Automaticamente avança próxima fase
4. **Fases seguintes** → Quartas, Semifinal, Final
5. **Campeão** → Anúncio automático do vencedor

### **Comandos de Moderação:**
- Apenas moderadores podem definir vencedores
- Cada partida tem um canal privado
- Botão "👑 Definir Vencedor" em cada partida

## 🐛 Solução de Problemas

### **Bot não inicia:**
```bash
# Verificar se TOKEN está correto
railway variables

# Ver logs de erro
railway logs
```

### **Banco de dados travando:**
- ✅ **JÁ CORRIGIDO** - Sistema otimizado para evitar deadlocks
- Usa execute_query() seguro para todas operações

### **Copinha não avança para próxima fase:**
- ✅ **JÁ CORRIGIDO** - Sistema de vencedores reescrito
- Verificar se moderador tem permissões adequadas

### **Dashboard não carrega:**
```bash
# Verificar se PORT está configurada
echo $PORT

# Testar endpoint
curl https://seu-projeto.railway.app/api/stats
```

## 📊 Monitoramento

### **Health Check:**
- `https://seu-projeto.railway.app/healthz` - Status do sistema
- `https://seu-projeto.railway.app/api/stats` - Estatísticas em tempo real

### **Logs Importantes:**
```
✅ Database inicializado
🌐 Flask rodando na porta 5000
🤖 RXbot está online!
✅ X slash commands sincronizados
```

## 🎯 Recursos Disponíveis

### **Dashboard Web:**
- Estatísticas em tempo real
- Lista de comandos
- FAQ interativo
- Sistema de busca

### **Bot Discord:**
- 98+ comandos slash
- Sistema de economia completo
- Moderação automática
- Tickets de suporte
- Copinhas/Torneios automáticos
- Sistema de clans
- Reminders e giveaways

## 🔄 Atualizações

Para atualizar o bot:
1. Faça push para o repositório GitHub
2. Railway fará redeploy automaticamente
3. Zero downtime - bot reconecta automaticamente

---

### 🎉 **Bot pronto para produção!**
Todos os problemas foram corrigidos e o sistema está otimizado para Railway.