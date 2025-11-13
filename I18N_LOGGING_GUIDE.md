# Sistema de Tradução para Logs (i18n Logging)

## Visão Geral

O ACCELA agora possui suporte completo para internacionalização (i18n) de logs de nível INFO, permitindo que mensagens importantes sejam traduzidas automaticamente para o idioma do usuário.

## Como Funciona

### 1. Novo Sistema de Logger

O sistema inclui novos componentes no `utils/logger.py`:

- **`I18nLogFilter`**: Filtro que traduz mensagens de log INFO usando o sistema i18n
- **`get_i18n_logger()`**: Função para obter um logger com suporte i18n
- **`info_i18n()`**: Função para registrar mensagens INFO com suporte a tradução

### 2. Contextos de Tradução

Cada mensagem de log usa um contexto (geralmente "Application") para organização das traduções.

### 3. Formatação com Parâmetros

O sistema suporta formatação de strings com parâmetros nomeados:

```python
# Original
logger.info(f"Loaded {font_name} font")

# Com i18n
info_i18n(logger, "Loaded {font_name} font", font_name)
```

## Como Usar

### 1. Importar as Funções Necessárias

```python
from utils.logger import get_i18n_logger, info_i18n
```

### 2. Obter um Logger com Contexto

```python
# Para módulos principais
logger = get_i18n_logger(__name__, "Application")

# Para classes específicas
class MyClass:
    def __init__(self):
        self.logger = get_i18n_logger(f"{__name__}.{self.__class__.__name__}", "MyClass")
```

### 3. Usar info_i18n para Mensagens INFO

```python
# Mensagem simples
info_i18n(logger, "Application starting...")

# Com parâmetros
info_i18n(logger, "Loaded {font_name} font", font_name)

# Múltiplos parâmetros
info_i18n(logger, "Applied selected font: '{font_name}' with size {size}px", font_name, size)
```

### 4. Manter Logs de Outros Níveis Normais

```python
# WARNING, ERROR, DEBUG continuam normais
logger.warning("This is a warning")
logger.error("This is an error")
logger.debug("This is debug info")
```

## Exemplos de Uso

### Módulo Principal

```python
from utils.logger import get_i18n_logger, info_i18n

def main():
    logger = get_i18n_logger("main", "Application")
    
    info_i18n(logger, "Application starting...")
    info_i18n(logger, "Loaded {font_name} font", "Arial")
    info_i18n(logger, "Main window displayed successfully.")
```

### Classe Específica

```python
class GameManager:
    def __init__(self):
        self.logger = get_i18n_logger(f"{__name__}.GameManager", "GameManager")
    
    def delete_game(self, app_id):
        info_i18n(self.logger, "Successfully deleted game {app_id}: {items}", app_id, "game directory")
```

## Traduções Disponíveis

### Português (pt_BR)

Todas as mensagens INFO comuns já foram traduzidas:

- "Application starting..." → "Iniciando aplicação..."
- "Loaded {font_name} font" → "Fonte {font_name} carregada"
- "Successfully deleted game {app_id}: {items}" → "Jogo {app_id} excluído com sucesso: {items}"
- E muitas outras...

### Inglês (en)

Mantém as strings originais como tradução (idioma base).

## Adicionando Novas Traduções

### 1. Adicionar aos Arquivos .ts

Em `translations/app_pt_BR.ts`:

```xml
<context>
    <name>Application</name>
    <message>
        <source>Your new message {param}</source>
        <translation>Sua nova mensagem {param}</translation>
    </message>
</context>
```

Em `translations/app_en.ts`:

```xml
<context>
    <name>Application</name>
    <message>
        <source>Your new message {param}</source>
        <translation>Your new message {param}</translation>
    </message>
</context>
```

### 2. Compilar Traduções

```bash
python compile_translations.py
```

### 3. Usar no Código

```python
info_i18n(logger, "Your new message {param}", value)
```

## Boas Práticas

### 1. Usar Parâmetros Nomeados

Prefira parâmetros nomeados para melhor clareza:

```python
# Bom
info_i18n(logger, "Processing {count} files for {user}", count, username)

# Evitar
info_i18n(logger, "Processing {} files for {}", count, username)
```

### 2. Contextos Apropriados

Use nomes de classes como contexto:

```python
# Para MainWindow
logger = get_i18n_logger("ui.main_window", "MainWindow")

# Para GameManager
logger = get_i18n_logger("core.game_manager", "GameManager")
```

### 3. Manter Consistência

Use as mesmas strings para mensagens similares:

```python
# Em múltiplos lugares
info_i18n(logger, "Successfully deleted game {app_id}: {items}", app_id, items)
```

### 4. Traduzir Apenas Mensagens INFO

O sistema traduz apenas mensagens INFO. Outros níveis continuam em inglês para facilitar debugging.

## Testando

### 1. Executar Demo

```bash
python example_i18n_logging.py
```

### 2. Testar com Diferentes Idiomas

O sistema detecta automaticamente o idioma do sistema. Para forçar um idioma específico:

```python
from utils.i18n import init_i18n
init_i18n(app, "pt_BR")  # Força português
init_i18n(app, "en")     # Força inglês
```

## Arquivos Modificados

- `utils/logger.py`: Adicionado sistema i18n
- `utils/i18n.py`: Sem alterações (usa sistema existente)
- `translations/app_pt_BR.ts`: Adicionadas traduções de logs
- `translations/app_en.ts`: Adicionadas strings base
- `main.py`: Exemplo de uso implementado
- `example_i18n_logging.py`: Demo completa do sistema

## Benefícios

1. **Experiência Melhorada**: Usadores veem mensagens em seu idioma nativo
2. **Consistência**: Interface e logs usam o mesmo sistema de tradução
3. **Manutenibilidade**: Centralização das traduções
4. **Flexibilidade**: Suporte a múltiplos idiomas facilmente extensível
5. **Performance**: Tradução apenas para logs INFO, sem impacto em debugging

## Próximos Passos

1. Converter gradualmente os logs INFO existentes para usar o novo sistema
2. Adicionar contexto específico para cada módulo/classe
3. Expandir para outros níveis de log se necessário
4. Considerar tradução para outros idiomas no futuro