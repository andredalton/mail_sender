# Mailer do Projeto Integrador — UNIVESP

Sistema em Python para envio individualizado de e-mails a empresas, órgãos públicos, entidades setoriais e outros atores ligados ao transporte de passageiros, com o objetivo de apresentar e validar uma proposta de Projeto Integrador da UNIVESP baseada em QR Codes para acompanhamento colaborativo de ônibus.

O projeto foi construído para trabalhar com uma base grande de contatos, já classificada por relevância, sem enviar a mesma mensagem de forma totalmente genérica. Cada contato pode ter uma abertura específica construída a partir de informações como nome da empresa ou órgão, município, UF, modalidade de transporte, porte, quantidade de veículos, origem do cadastro e outros dados disponíveis.

---

## 1. Objetivo

A ideia acadêmica é estudar uma forma simples e colaborativa de acompanhar o deslocamento de ônibus por meio de QR Codes.

Em uma implementação possível, cada veículo teria um QR Code identificador. Quando um usuário lesse esse código em um ponto ou local de passagem, seria criado um registro contendo informações como horário e localização. A agregação dessas leituras poderia permitir análises de posição, trajetos, intervalos, regularidade e circulação dos veículos.

O sistema de e-mail existe para entrar em contato com atores reais do setor e:

- validar se o problema é relevante;
- entender como empresas e órgãos acompanham atualmente seus veículos;
- descobrir necessidades reais do setor;
- verificar se a proposta pode complementar soluções existentes;
- encontrar possíveis instituições parceiras para o Projeto Integrador;
- obter encaminhamento para setores técnicos, operacionais, de inovação ou mobilidade.

---

## 2. Arquivos principais

Estrutura sugerida do diretório:

```text
send_mail/
├── mailer.py
├── .env
├── .env.example
├── README.md
├── contatos_transporte_individualizados_rankeados.json
├── envios.json
└── envios.jsonl
```

### `mailer.py`

Programa principal. Ele:

1. carrega automaticamente as variáveis do `.env`;
2. abre o JSON de contatos;
3. lê o histórico de envios;
4. elimina contatos já enviados;
5. filtra por categoria e score mínimo;
6. preserva a ordenação de relevância existente no JSON;
7. monta uma mensagem individual para cada destinatário;
8. envia pelo Gmail usando SMTP autenticado;
9. registra imediatamente cada sucesso ou erro no histórico.

### `contatos_transporte_individualizados_rankeados.json`

Base principal de destinatários.

Ela foi construída para conter, além do e-mail, informações que permitem individualizar a mensagem. Um registro típico possui uma estrutura semelhante a:

```json
{
  "email": "contato@empresa.com.br",
  "tipo_contato": "institucional",
  "prioridade_envio": 1,
  "relevancia_sp": "direto_sp",
  "entidade": {
    "razao_social": "EMPRESA EXEMPLO LTDA",
    "nome_fantasia": "Empresa Exemplo",
    "cnpj": "00000000000000",
    "tipo": "empresa_privada_transportadora_turistica",
    "situacao_cadastral": "Regular",
    "municipio": "Campinas",
    "uf": "SP",
    "porte": "EMPRESA DE PEQUENO PORTE",
    "natureza_juridica": "Sociedade Empresária Limitada",
    "modalidades": "Especial | Traslado",
    "quantidade_veiculos": "10"
  },
  "personalizacao": {
    "nome_para_mencionar": "Empresa Exemplo",
    "cidade_para_mencionar": "Campinas",
    "uf_para_mencionar": "SP",
    "fatos_seguros_para_usar": [],
    "abertura_sugerida": "Entrei em contato porque...",
    "pedido_sugerido": "Gostaria de saber se...",
    "nao_afirmar_sem_confirmacao": []
  },
  "ranking": {
    "score": 92,
    "categoria": "A"
  }
}
```

A base contém contatos de empresas privadas, transportadoras, fretadoras, operadores urbanos e rodoviários, órgãos públicos, secretarias, autarquias, sindicatos, federações e entidades relacionadas ao transporte.

---

## 3. Ranking de relevância

Os contatos foram classificados por um score de `0` a `100`.

O objetivo do ranking não é afirmar que um destinatário certamente responderá, mas ordenar os contatos segundo a probabilidade estimada de serem relevantes para o Projeto Integrador.

Os principais componentes considerados são:

- aderência ao transporte de passageiros;
- localização no Estado de São Paulo;
- tipo de contato disponível;
- proximidade com decisão ou operação;
- potencial de escala da entidade;
- qualidade dos dados existentes;
- capacidade de personalização da mensagem;
- bônus por características especialmente relevantes;
- penalidades para contatos provavelmente indiretos ou de terceiros.

As categorias utilizadas são:

| Categoria | Score | Interpretação |
|---|---:|---|
| A | 80–100 | prioridade máxima |
| B | 65–79 | alta prioridade |
| C | 50–64 | prioridade intermediária |
| D | 35–49 | baixa prioridade |
| E | 0–34 | contato pouco aderente |

A campanha deve começar pelos contatos de categoria `A` e, idealmente, os resultados reais de resposta devem ser usados posteriormente para recalibrar o ranking.

---

## 4. Ambiente virtual Python

O projeto pode ser executado usando `virtualenvwrapper`.

### Criar o ambiente

```bash
mkvirtualenv spam
```

### Ativar posteriormente

```bash
workon spam
```

### Sair do ambiente

```bash
deactivate
```

O `virtualenvwrapper` foi instalado via `pipx`. Uma configuração funcional no `~/.zshrc` é:

```bash
export WORKON_HOME=$HOME/.virtualenvs
export VIRTUALENVWRAPPER_PYTHON=$HOME/.local/share/pipx/venvs/virtualenvwrapper/bin/python
source $HOME/.local/bin/virtualenvwrapper.sh
```

Depois de alterar o `~/.zshrc`:

```bash
source ~/.zshrc
```

---

## 5. Dependências Python

O programa usa majoritariamente módulos da biblioteca padrão do Python.

A dependência externa necessária para carregar o `.env` é:

```bash
pip install python-dotenv
```

Os módulos `json`, `os`, `smtplib`, `ssl`, `time`, `datetime`, `email` e `pathlib` já fazem parte do Python e não precisam ser instalados separadamente.

---

## 6. Configuração do `.env`

As credenciais e os parâmetros da campanha não devem ficar escritos diretamente no código.

Exemplo:

```dotenv
GMAIL_EMAIL=seuemail@gmail.com
GMAIL_APP_PASSWORD=xxxx_xxxx_xxxx_xxxx

EMAIL_UNIVESP=25202874@aluno.univesp.br
NOME_REMETENTE=André Meneghelli
UNIVERSIDADE=Universidade Virtual do Estado de São Paulo – UNIVESP

ARQUIVO_CONTATOS=contatos_transporte_individualizados_rankeados.json

# Histórico legado no formato objeto JSON:
ARQUIVO_ENVIOS=envios.json

# Histórico append-only recomendado para novas execuções:
ARQUIVO_SAIDA=envios.jsonl

DRY_RUN=true

CATEGORIAS_PERMITIDAS=A
SCORE_MINIMO=80

MAX_ENVIOS_POR_EXECUCAO=10
INTERVALO_SEGUNDOS=3

MAX_ERROS_CONSECUTIVOS=5

SMTP_HOST=smtp.gmail.com
SMTP_PORT=465

ASSUNTO_EMAIL=Projeto UNIVESP: proposta de acompanhamento de transporte por QR Code
```

### Nunca versionar o `.env`

Inclua no `.gitignore`:

```gitignore
.env
```

Uma versão segura pode ser mantida como `.env.example`, sem credenciais reais.

---

## 7. Senha de aplicativo do Gmail

O programa não deve usar a senha normal da conta Google.

Use uma **senha de aplicativo** da conta Google e coloque-a em:

```dotenv
GMAIL_APP_PASSWORD=...
```

O Gmail é usado como remetente autenticado. O endereço institucional da UNIVESP pode aparecer na assinatura e também pode ser configurado como `Reply-To`.

Exemplo conceitual:

```text
From: André Meneghelli <gmail-do-remetente@gmail.com>
To: contato@empresa.com.br
Reply-To: 25202874@aluno.univesp.br
```

Assim, a mensagem é autenticada corretamente pela infraestrutura do Gmail, enquanto uma resposta ao e-mail pode ser direcionada ao endereço institucional.

Isso evita falsificar o campo `From`, o que poderia causar problemas de SPF, DKIM e DMARC.

---

## 8. Por que a conta da UNIVESP não está sendo usada diretamente para envio

Foi testado SMTP autenticado no Microsoft 365 da UNIVESP usando:

```text
smtp.office365.com:587
```

O tenant retornou:

```text
535 5.7.139 Authentication unsuccessful,
SmtpClientAuthentication is disabled for the Tenant
```

Portanto, SMTP AUTH está desativado no tenant da universidade.

Também foi tentado acesso ao Microsoft Entra para registrar uma aplicação que usasse Microsoft Graph, mas a conta de aluno não apresentou acesso suficiente à área de `App registrations`.

Por isso, o envio atual é realizado via Gmail, mantendo o endereço institucional no corpo e/ou no `Reply-To`.

---

## 9. Carregamento automático do `.env`

No início do `mailer.py`:

```python
from dotenv import load_dotenv

load_dotenv()
```

Depois disso, valores podem ser obtidos normalmente:

```python
GMAIL_EMAIL = os.getenv("GMAIL_EMAIL")
```

Funções auxiliares permitem ler tipos corretamente:

```python
def env_bool(nome, default=False):
    ...


def env_int(nome, default):
    ...


def env_float(nome, default):
    ...
```

`INTERVALO_SEGUNDOS` deve ser lido como `float`, pois valores como `0.5` são sintaticamente válidos para `time.sleep()`:

```python
INTERVALO_SEGUNDOS = env_float(
    "INTERVALO_SEGUNDOS",
    30.0,
)
```

Isso não significa que intervalos extremamente curtos sejam recomendáveis para grandes volumes: limites e mecanismos antispam do Gmail ainda se aplicam.

---

## 10. DRY RUN

Nunca comece uma campanha grande diretamente em modo real.

No `.env`:

```dotenv
DRY_RUN=true
```

Nesse modo o programa:

- carrega os contatos;
- aplica ranking e filtros;
- monta as mensagens;
- mostra no terminal o destinatário e o texto final;
- não abre uma campanha real de envio;
- não marca o destinatário como enviado.

Depois de validar algumas mensagens:

```dotenv
DRY_RUN=false
```

---

## 11. Filtros de campanha

### Categorias

```dotenv
CATEGORIAS_PERMITIDAS=A
```

Mais de uma categoria pode ser aceita:

```dotenv
CATEGORIAS_PERMITIDAS=A,B
```

### Score mínimo

```dotenv
SCORE_MINIMO=80
```

Um contato só é elegível quando passa pelos filtros definidos no programa.

### Máximo por execução

```dotenv
MAX_ENVIOS_POR_EXECUCAO=50
```

Isso limita quantos destinatários serão processados naquela execução, mesmo que milhares sejam elegíveis.

### Intervalo

```dotenv
INTERVALO_SEGUNDOS=3
```

O valor pode ser decimal:

```dotenv
INTERVALO_SEGUNDOS=0.5
```

Tecnicamente `time.sleep(0.5)` funciona. Entretanto, volumes e frequências muito altos podem causar limitação ou bloqueio pelo provedor. O intervalo deve ser tratado como parâmetro operacional, não como garantia de capacidade do Gmail.

---

## 12. Personalização da mensagem

O script não deve produzir apenas um disparo idêntico para todos.

Para cada contato, ele pode utilizar:

- `nome_para_mencionar`;
- `cidade_para_mencionar`;
- `uf_para_mencionar`;
- `abertura_sugerida`;
- `pedido_sugerido`;
- `fatos_seguros_para_usar`;
- modalidade da empresa;
- tipo da entidade;
- localização;
- outras informações cadastrais relevantes.

Exemplo de abertura individualizada:

```text
Entrei em contato porque a Empresa Exemplo aparece no Cadastur como
transportadora turística regular em Campinas, SP, e estou desenvolvendo
um Projeto Integrador da UNIVESP relacionado ao acompanhamento
colaborativo de ônibus por QR Code.
```

A base também possui o campo:

```json
"nao_afirmar_sem_confirmacao": [
  "que a empresa opera linhas específicas",
  "que a empresa possui determinada tecnologia de rastreamento"
]
```

Ele serve para impedir personalizações que extrapolem os dados disponíveis.

---

## 13. Corpo geral da mensagem

A estrutura atual da abordagem contém:

1. apresentação como aluno da UNIVESP;
2. abertura específica para a entidade;
3. explicação do Projeto Integrador;
4. conceito dos QR Codes associados aos veículos;
5. possibilidade de registrar horário e localização;
6. uso potencial para posição, trajetos, intervalos e regularidade;
7. explicação de que o projeto ainda está em fase acadêmica de validação;
8. pedido de conversa, parceria ou encaminhamento;
9. assinatura com e-mail institucional.

A mensagem deixa claro que se trata de uma proposta acadêmica, não de uma oferta comercial.

---

## 14. Histórico de envios

Esta parte é crítica: o sistema não deve enviar novamente para um destinatário que já recebeu a mensagem.

Existem atualmente **dois formatos de histórico** no projeto.

### 14.1 `envios.json` — histórico legado/reconstruído

Foi criado um `envios.json` a partir da saída de uma execução anterior do `mailer.py`.

Essa execução tinha:

```text
DRY_RUN: False
Categorias: A
Score mínimo: 80
Máximo por execução: 3500
Intervalo: 3s
```

Foram reconstruídos **549 envios confirmados como `OK`**.

Estrutura:

```json
{
  "envios": {
    "empresa@exemplo.com": {
      "email": "empresa@exemplo.com",
      "entidade": "EMPRESA EXEMPLO",
      "score": 100,
      "categoria": "A",
      "status": "enviado",
      "data": null,
      "erro": null,
      "indice_execucao": 1,
      "total_planejado_execucao": 3500,
      "origem": "Reconstruído da saída do mailer.py"
    }
  }
}
```

Como o log original não possuía timestamp individual por mensagem, `data` foi mantido como `null` em vez de inventar horários.

Esse arquivo é importante porque contém os destinatários já enviados antes da implementação do novo formato append-only.

---

## 15. Histórico append-only recomendado: JSON Lines

Para novas execuções, o formato recomendado é JSON Lines (`.jsonl`).

No `.env`:

```dotenv
ARQUIVO_SAIDA=envios.jsonl
```

Cada tentativa é acrescentada ao fim do arquivo:

```json
{"data":"2026-08-15T20:40:01-03:00","status":"enviado","email":"empresa1@exemplo.com.br","entidade":"Empresa 1","municipio":"Campinas","uf":"SP","score":100,"categoria":"A","erro":null}
{"data":"2026-08-15T20:40:04-03:00","status":"enviado","email":"empresa2@exemplo.com.br","entidade":"Empresa 2","municipio":"São Paulo","uf":"SP","score":99,"categoria":"A","erro":null}
{"data":"2026-08-15T20:40:07-03:00","status":"erro","email":"empresa3@exemplo.com.br","entidade":"Empresa 3","municipio":"Sorocaba","uf":"SP","score":98,"categoria":"A","erro":"..."}
```

### Por que JSONL?

Ele é adequado para esse problema porque:

- não exige reescrever todo o histórico;
- cada envio pode ser persistido imediatamente;
- uma interrupção não destrói os registros anteriores;
- é fácil fazer append;
- é simples reconstruir o conjunto de e-mails já enviados;
- erros podem ser registrados sem marcar o contato como concluído.

---

## 16. Como pular e-mails já enviados

Ao iniciar, o programa deve ler o histórico existente e criar um conjunto (`set`) de e-mails com:

```json
"status": "enviado"
```

Exemplo conceitual:

```python
emails_enviados = carregar_emails_enviados()

if email in emails_enviados:
    return False
```

Assim, se o processo for interrompido após centenas de mensagens, basta executá-lo novamente.

Os e-mails já registrados como enviados serão pulados.

Um registro com:

```json
"status": "erro"
```

não deve entrar no conjunto de enviados e pode ser tentado novamente em outra execução.

---

## 17. Append imediato após cada envio

Depois de `smtp.send_message()` retornar com sucesso, o registro deve ser anexado imediatamente:

```python
append_registro_saida(
    contato=contato,
    status="enviado",
)
```

O arquivo é aberto com:

```python
open("a", encoding="utf-8")
```

ou equivalente via `Path`:

```python
ARQUIVO_SAIDA.open("a", encoding="utf-8")
```

O uso de `flush()` e `os.fsync()` reduz a chance de perder o último registro em caso de encerramento inesperado:

```python
arquivo.flush()
os.fsync(arquivo.fileno())
```

---

## 18. Migração entre `envios.json` e `envios.jsonl`

O projeto possui um histórico inicial em `envios.json` com 549 envios reconstruídos.

Antes de abandonar definitivamente o formato legado, o `mailer.py` deve garantir uma destas estratégias:

### Opção A — ler os dois arquivos

Na inicialização:

1. carregar `envios.json`;
2. carregar `envios.jsonl`, se existir;
3. unir todos os e-mails com status `enviado` em um único `set`.

Essa é a estratégia mais segura durante a transição.

### Opção B — converter o legado uma única vez

Converter os 549 registros do `envios.json` em linhas de `envios.jsonl` e passar a utilizar somente o novo arquivo.

Depois da migração, `envios.json` pode ser mantido apenas como backup histórico.

---

## 19. Execução

Ative o ambiente:

```bash
workon spam
```

Entre no diretório:

```bash
cd ~/Documentos/send_mail
```

Execute:

```bash
python mailer.py
```

Em `DRY_RUN=true`, nenhuma mensagem real deve ser enviada.

Em `DRY_RUN=false`, o terminal mostra o progresso:

```text
[1/50] OK | 100 | EMPRESA EXEMPLO | contato@empresa.com.br
[2/50] OK | 100 | OUTRA EMPRESA | diretoria@outraempresa.com.br
[3/50] ERRO | EMPRESA X | contato@x.com.br
```

---

## 20. Interrupção e retomada

O programa foi pensado para poder ser interrompido.

Exemplo:

```text
1   enviado
2   enviado
3   enviado
...
549 enviado
processo encerrado
```

Na próxima execução:

1. o histórico é carregado;
2. os 549 e-mails são identificados;
3. esses contatos são removidos dos elegíveis;
4. o programa continua nos próximos destinatários.

Por isso, o histórico deve sempre ser persistido imediatamente após cada sucesso.

---

## 21. Erros consecutivos

O `.env` pode conter:

```dotenv
MAX_ERROS_CONSECUTIVOS=5
```

Se muitos envios falharem consecutivamente, o programa deve interromper a execução. Isso evita continuar enviando quando há um problema estrutural, por exemplo:

- senha de app inválida;
- sessão SMTP encerrada;
- bloqueio temporário do Gmail;
- falha de rede;
- limitação do provedor.

---

## 22. Cuidados com Gmail e volume

O fato de o programa conseguir executar:

```python
time.sleep(0.5)
```

não significa que o Gmail permitirá indefinidamente dois envios por segundo.

O provedor pode aplicar:

- limites de envio;
- limitação temporária;
- detecção de comportamento automatizado;
- filtros antispam;
- bloqueio da autenticação ou do envio por determinado período.

Por isso, o programa deve ser capaz de:

- limitar quantidade por execução;
- controlar intervalo;
- registrar erros;
- parar após erros consecutivos;
- retomar sem duplicar mensagens.

---

## 23. Credenciais e segurança

Nunca coloque no Git:

- senha normal do Gmail;
- senha de aplicativo;
- tokens de autenticação;
- `.env` real.

Use:

```gitignore
.env
*.log
```

O `.env.example` pode ser versionado porque deve conter apenas nomes de variáveis e valores fictícios.

---

## 24. Boas práticas para aumentar a chance de resposta

O objetivo não deve ser apenas maximizar a quantidade de mensagens enviadas.

A chance de resposta tende a ser melhor quando a abordagem:

- cita corretamente o nome da organização;
- menciona a cidade ou região quando relevante;
- explica claramente que se trata de Projeto Integrador da UNIVESP;
- mostra por que aquela entidade foi selecionada;
- evita afirmações não verificadas;
- pede uma conversa breve ou encaminhamento;
- deixa claro que ainda é uma fase de validação acadêmica;
- fornece o e-mail institucional na assinatura;
- utiliza um assunto curto e inteligível.

---

## 25. Recomendações para evolução

Melhorias futuras úteis:

### Registrar respostas

Adicionar campos como:

```json
{
  "respondeu": true,
  "data_resposta": "...",
  "tipo_resposta": "interessado",
  "observacao": "encaminhou para setor técnico"
}
```

### Recalibrar o ranking

Depois de uma amostra suficiente, comparar taxas reais de resposta por:

- tipo de entidade;
- score;
- categoria;
- domínio de e-mail;
- função do contato;
- município;
- modalidade;
- tipo de abertura utilizada.

O ranking pode então deixar de ser apenas heurístico e passar a incorporar resultados reais.

### Gerenciar versões de texto

Registrar qual variante da mensagem foi enviada:

```json
"template": "v2"
```

Isso permite medir qual abordagem produz mais respostas.

### Controlar rejeições

Registrar bounces e endereços inválidos para impedir novas tentativas desnecessárias.

### Respeitar pedidos de não contato

Manter uma blacklist local para qualquer destinatário que peça para não receber novas mensagens.

---

## 26. Estado atual conhecido

No momento da documentação:

- a base rankeada possui dezenas de milhares de contatos;
- a categoria `A` contém os contatos de maior prioridade;
- uma execução real foi iniciada com `DRY_RUN=False`;
- o lote planejado tinha 3.500 contatos;
- o intervalo utilizado era de 3 segundos;
- a saída disponível confirmou 549 mensagens enviadas com status `OK`;
- esses 549 envios foram reconstruídos no arquivo `envios.json` para evitar duplicação;
- o formato append-only `envios.jsonl` é recomendado para novas execuções.

---

## 27. Fluxo recomendado daqui em diante

```text
contatos_transporte_individualizados_rankeados.json
                     │
                     ▼
               carregar contatos
                     │
                     ▼
       carregar envios.json + envios.jsonl
                     │
                     ▼
           criar set de já enviados
                     │
                     ▼
       filtrar categoria / score / histórico
                     │
                     ▼
           personalizar cada mensagem
                     │
                     ▼
               enviar via Gmail
                     │
             ┌───────┴────────┐
             │                │
          sucesso            erro
             │                │
             ▼                ▼
       append enviado     append erro
             │                │
             └───────┬────────┘
                     ▼
               próximo contato
```

Esse desenho garante que o programa possa ser parado e retomado sem perder o estado da campanha e sem reenviar mensagens já confirmadas.

---

## 28. Aviso

Este projeto é uma ferramenta de apoio a uma iniciativa acadêmica. Grandes volumes de e-mail devem ser enviados com cuidado, observando as políticas do provedor de e-mail, a relevância dos destinatários, pedidos de descadastramento/não contato e a legislação aplicável.
