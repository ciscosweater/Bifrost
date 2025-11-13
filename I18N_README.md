# ACCELA Internationalization (i18n) System

Sistema de internacionalização simplificado usando JSON, muito mais fácil de gerenciar que o sistema anterior baseado em Qt Linguist.

## 📁 Estrutura dos Arquivos

```
translations/
├── en.json          # Traduções em inglês (idioma base)
├── pt_BR.json       # Traduções em português brasileiro
├── app_en.ts        # Arquivo TS antigo (mantido para referência)
├── app_pt_BR.ts     # Arquivo TS antigo (mantido para referência)
├── app_en.qm        # Arquivo QM antigo (obsoleto)
└── app_pt_BR.qm     # Arquivo QM antigo (obsoleto)
```

## 🚀 Como Usar

### No Código Python

```python
from utils.i18n import tr, init_i18n

# Inicializar o sistema (geralmente no main.py)
init_i18n()  # Auto-detecta o idioma do sistema
# ou
init_i18n('pt_BR')  # Força idioma específico

# Usar traduções
text = tr("MainWindow", "Depot Downloader GUI")
button_text = tr("DownloadControls", "Download")
```

### Formato das Chaves

As chaves seguem o formato: `"Contexto.Texto"`

- **Contexto**: Geralmente o nome da classe onde a string é usada
- **Texto**: O texto original em inglês

Exemplo:
```json
{
  "translations": {
    "MainWindow.Depot Downloader GUI": "Interface do Depot Downloader",
    "DownloadControls.Download": "Baixar"
  }
}
```

## 🛠️ Gerenciamento de Traduções

### Verificar Traduções Faltantes

```bash
source venv/bin/activate
python manage_translations.py check
```

### Adicionar Nova Tradução

```bash
source venv/bin/activate
python manage_translations.py add
```

### Gerar Traduções Automáticas

Quando você adiciona novas chamadas `tr()` ao código, use:

```bash
source venv/bin/activate
python generate_translations.py
```

Este script:
1. Escaneia todos os arquivos Python em busca de chamadas `tr()`
2. Adiciona automaticamente as strings faltantes aos arquivos JSON
3. Para inglês: usa o texto original
4. Para português: usa o texto original (pode ser traduzido depois)

## 📋 Comandos Disponíveis

### manage_translations.py

- `check`: Verifica traduções faltantes
- `add`: Adiciona tradução interativamente
- `update`: Atualiza JSON a partir de TS (se necessário)

### generate_translations.py

Gera automaticamente todas as traduções faltantes baseado no código.

## 🌐 Idiomas Suportados

- `en`: English (idioma base)
- `pt_BR`: Português Brasileiro

Para adicionar novo idioma:

1. Crie `translations/novo_idioma.json`
2. Adicione ao dicionário `available_languages` em `utils/i18n.py`
3. Execute `generate_translations.py`

## 🔧 Como o Sistema Funciona

1. **Carregamento**: O sistema carrega o arquivo JSON do idioma atual para um dicionário em memória
2. **Tradução**: Quando `tr()` é chamado, procura a chave `"Contexto.Texto"` no dicionário
3. **Fallback**: Se não encontrar, retorna o texto original
4. **Performance**: Acesso O(1) ao dicionário, muito rápido

## 🐛 Debug

Para ver quais traduções estão faltando, configure o logger para DEBUG:

```python
import logging
logging.getLogger('utils.i18n').setLevel(logging.DEBUG)
```

O sistema vai logar chaves não encontradas quando o idioma não for inglês.

## 📝 Melhorias em Relação ao Sistema Anterior

- ✅ **Simplicidade**: JSON vs XML + binário .qm
- ✅ **Performance**: Carregamento instantâneo vs parsing complexo
- ✅ **Debug**: Arquivos legíveis vs binários opacos
- ✅ **Manutenção**: Scripts automatizados vs Qt Linguist manual
- ✅ **Flexibilidade**: Fácil adicionar idiomas vs dependência Qt
- ✅ **Portabilidade**: Funciona em qualquer ambiente vs Qt tools

## 🔄 Migração do Sistema Antigo

O sistema antigo foi completamente substituído, mas os arquivos `.ts` foram mantidos como referência. Os arquivos `.qm` antigos não são mais usados.

## 🚨 Importante

- Sempre use `tr()` para strings que aparecem na interface
- Não use `tr()` para logs técnicos ou mensagens de debug
- O contexto deve ser o nome da classe onde a string é usada
- Execute `generate_translations.py` após adicionar novas strings ao código