#!/usr/bin/env python3

import json
import os
import smtplib
import ssl
import time

from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# CARREGA .env
# ============================================================

load_dotenv()


# ============================================================
# CONFIGURAÇÃO
# ============================================================

def env_bool(nome, default=False):
    valor = os.getenv(nome)

    if valor is None:
        return default

    return valor.strip().lower() in {
        "1",
        "true",
        "yes",
        "sim",
        "on",
    }


def env_int(nome, default):
    valor = os.getenv(nome)

    if valor is None:
        return default

    return int(valor)


def env_float(nome, default):
    valor = os.getenv(nome)

    if valor is None:
        return default

    return float(valor)


def env_set(nome, default):
    valor = os.getenv(nome)

    if not valor:
        valor = default

    return {
        item.strip()
        for item in valor.split(",")
        if item.strip()
    }


# ============================================================
# ARQUIVOS
# ============================================================

ARQUIVO_CONTATOS = Path(
    os.getenv(
        "ARQUIVO_CONTATOS",
        "contatos_transporte_individualizados_rankeados.json",
    )
)

ARQUIVO_SAIDA = Path(
    os.getenv(
        "ARQUIVO_SAIDA",
        "envios.jsonl",
    )
)


# ============================================================
# GMAIL
# ============================================================

GMAIL_EMAIL = os.getenv("GMAIL_EMAIL")

GMAIL_APP_PASSWORD = os.getenv(
    "GMAIL_APP_PASSWORD"
)


# ============================================================
# DADOS PESSOAIS
# ============================================================

NOME = os.getenv(
    "NOME_REMETENTE",
    "André Meneghelli",
)

EMAIL_UNIVESP = os.getenv(
    "EMAIL_UNIVESP",
    "25202874@aluno.univesp.br",
)

UNIVERSIDADE = os.getenv(
    "UNIVERSIDADE",
    "Universidade Virtual do Estado de São Paulo – UNIVESP",
)


# ============================================================
# CAMPANHA
# ============================================================

DRY_RUN = env_bool(
    "DRY_RUN",
    True,
)

CATEGORIAS_PERMITIDAS = env_set(
    "CATEGORIAS_PERMITIDAS",
    "A",
)

SCORE_MINIMO = env_int(
    "SCORE_MINIMO",
    80,
)

MAX_ENVIOS_POR_EXECUCAO = env_int(
    "MAX_ENVIOS_POR_EXECUCAO",
    10,
)

INTERVALO_SEGUNDOS = env_float(
    "INTERVALO_SEGUNDOS",
    30.0,
)

MAX_ERROS_CONSECUTIVOS = env_int(
    "MAX_ERROS_CONSECUTIVOS",
    5,
)


# ============================================================
# SMTP
# ============================================================

SMTP_HOST = os.getenv(
    "SMTP_HOST",
    "smtp.gmail.com",
)

SMTP_PORT = env_int(
    "SMTP_PORT",
    465,
)


# ============================================================
# ASSUNTO
# ============================================================

ASSUNTO = os.getenv(
    "ASSUNTO_EMAIL",
    "Projeto UNIVESP: proposta de acompanhamento "
    "de transporte por QR Code",
)


# ============================================================
# UTILITÁRIOS
# ============================================================

def agora_iso():
    return datetime.now().astimezone().isoformat(
        timespec="seconds"
    )


def limpar_texto(valor):
    if valor is None:
        return ""

    return str(valor).strip()


def carregar_json(caminho):
    with caminho.open(
        "r",
        encoding="utf-8",
    ) as arquivo:
        return json.load(arquivo)


# ============================================================
# HISTÓRICO DE ENVIO - JSONL
# ============================================================

def carregar_emails_enviados():
    """
    Lê ARQUIVO_SAIDA caso exista e retorna um set contendo
    todos os e-mails que possuem pelo menos um registro com
    status='enviado'.

    Linhas inválidas são ignoradas com aviso.
    """

    enviados = set()

    if not ARQUIVO_SAIDA.exists():
        return enviados

    with ARQUIVO_SAIDA.open(
        "r",
        encoding="utf-8",
    ) as arquivo:

        for numero_linha, linha in enumerate(
            arquivo,
            start=1,
        ):
            linha = linha.strip()

            if not linha:
                continue

            try:
                registro = json.loads(linha)

            except json.JSONDecodeError as erro:
                print(
                    f"AVISO: linha {numero_linha} inválida "
                    f"em {ARQUIVO_SAIDA}: {erro}"
                )
                continue

            email = limpar_texto(
                registro.get("email")
            ).lower()

            status = limpar_texto(
                registro.get("status")
            ).lower()

            if (
                email
                and status == "enviado"
            ):
                enviados.add(email)

    return enviados


def append_registro_saida(
    contato,
    status,
    erro=None,
):
    """
    Acrescenta um objeto JSON ao FINAL do arquivo.

    O arquivo nunca é reescrito.
    """

    ranking = contato.get(
        "ranking",
        {},
    )

    entidade = contato.get(
        "entidade",
        {},
    )

    registro = {
        "data": agora_iso(),
        "status": status,
        "email": limpar_texto(
            contato.get("email")
        ).lower(),
        "entidade": obter_nome_entidade(
            contato
        ),
        "municipio": limpar_texto(
            entidade.get("municipio")
        ),
        "uf": limpar_texto(
            entidade.get("uf")
        ),
        "score": ranking.get(
            "score"
        ),
        "categoria": ranking.get(
            "categoria"
        ),
        "erro": (
            str(erro)
            if erro is not None
            else None
        ),
    }

    # Cria diretórios intermediários se necessário.
    ARQUIVO_SAIDA.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with ARQUIVO_SAIDA.open(
        "a",
        encoding="utf-8",
    ) as arquivo:

        json.dump(
            registro,
            arquivo,
            ensure_ascii=False,
        )

        arquivo.write("\n")

        # Garante que o registro seja enviado ao sistema
        # operacional imediatamente.
        arquivo.flush()

        os.fsync(
            arquivo.fileno()
        )


# ============================================================
# PERSONALIZAÇÃO
# ============================================================

def obter_nome_entidade(contato):
    personalizacao = contato.get(
        "personalizacao",
        {},
    )

    entidade = contato.get(
        "entidade",
        {},
    )

    nome = limpar_texto(
        personalizacao.get(
            "nome_para_mencionar"
        )
    )

    if nome:
        return nome

    fantasia = limpar_texto(
        entidade.get(
            "nome_fantasia"
        )
    )

    if fantasia:
        return fantasia

    razao_social = limpar_texto(
        entidade.get(
            "razao_social"
        )
    )

    if razao_social:
        return razao_social

    return "instituição"


def obter_localidade(contato):
    entidade = contato.get(
        "entidade",
        {},
    )

    municipio = limpar_texto(
        entidade.get(
            "municipio"
        )
    )

    uf = limpar_texto(
        entidade.get(
            "uf"
        )
    )

    if municipio and uf:
        return f"{municipio}/{uf}"

    return municipio or uf


def obter_abertura(contato):
    personalizacao = contato.get(
        "personalizacao",
        {},
    )

    abertura = limpar_texto(
        personalizacao.get(
            "abertura_sugerida"
        )
    )

    if abertura:
        return abertura

    nome = obter_nome_entidade(
        contato
    )

    localidade = obter_localidade(
        contato
    )

    if localidade:
        return (
            f"Entrei em contato com a {nome} porque identifiquei "
            f"sua atuação relacionada ao transporte de passageiros "
            f"em {localidade}."
        )

    return (
        f"Entrei em contato com a {nome} porque identifiquei "
        "sua atuação relacionada ao transporte de passageiros."
    )


def obter_pedido(contato):
    personalizacao = contato.get(
        "personalizacao",
        {},
    )

    pedido = limpar_texto(
        personalizacao.get(
            "pedido_sugerido"
        )
    )

    if pedido:
        return pedido

    return (
        "Gostaria de saber se vocês teriam interesse em uma breve "
        "conversa sobre a proposta ou poderiam indicar o setor mais "
        "adequado para tratar deste assunto."
    )


# ============================================================
# CORPO DO E-MAIL
# ============================================================

def criar_corpo(contato):
    abertura = obter_abertura(
        contato
    )

    pedido = obter_pedido(
        contato
    )

    return f"""Prezados(as),

Meu nome é {NOME} e sou aluno da {UNIVERSIDADE}.

{abertura}

Estou desenvolvendo um Projeto Integrador na área de Computação cuja proposta é estudar uma forma simples e colaborativa de acompanhar o deslocamento de ônibus por meio de QR Codes.

A ideia é que um QR Code associado ao veículo possa ser lido por usuários em pontos ou locais de passagem. Cada leitura produziria um registro com informações como horário e localização, permitindo construir uma base de dados colaborativa sobre a circulação dos veículos.

Esses registros poderiam ser utilizados para estimativas de posição, análise de trajetos, intervalos e regularidade do serviço. Um dos objetivos do projeto é avaliar em quais situações esse tipo de abordagem pode ser útil como complemento aos sistemas de rastreamento e informação já existentes, especialmente sem exigir inicialmente a instalação de novos equipamentos eletrônicos nos veículos.

Neste momento o projeto ainda está na fase acadêmica de definição e validação do problema. Por isso, estou procurando empresas, órgãos e entidades ligadas ao transporte de passageiros para entender necessidades reais do setor e verificar a possibilidade de colaboração institucional.

{pedido}

Caso este assunto seja tratado por outro departamento ou profissional da organização, agradeço muito se esta mensagem puder ser encaminhada ao contato mais adequado.

Atenciosamente,

{NOME}
Aluno da {UNIVERSIDADE}
E-mail institucional: {EMAIL_UNIVESP}
"""


# ============================================================
# CRIAÇÃO DA MENSAGEM
# ============================================================

def criar_mensagem(contato):
    mensagem = EmailMessage()

    mensagem["From"] = (
        f"{NOME} <{GMAIL_EMAIL}>"
    )

    mensagem["To"] = contato[
        "email"
    ]

    mensagem["Subject"] = ASSUNTO

    if EMAIL_UNIVESP:
        mensagem["Reply-To"] = EMAIL_UNIVESP

    mensagem.set_content(
        criar_corpo(
            contato
        )
    )

    return mensagem


# ============================================================
# VALIDAÇÃO
# ============================================================

def validar_configuracao():
    erros = []

    if not GMAIL_EMAIL:
        erros.append(
            "GMAIL_EMAIL não definido no .env"
        )

    if not GMAIL_APP_PASSWORD:
        erros.append(
            "GMAIL_APP_PASSWORD não definido no .env"
        )

    if not ARQUIVO_CONTATOS.exists():
        erros.append(
            f"Arquivo de contatos não encontrado: "
            f"{ARQUIVO_CONTATOS}"
        )

    if erros:
        print(
            "Erro de configuração:"
        )

        for erro in erros:
            print(
                f"- {erro}"
            )

        raise SystemExit(1)


# ============================================================
# FILTRO
# ============================================================

def contato_deve_ser_enviado(
    contato,
    emails_enviados,
):
    email = limpar_texto(
        contato.get("email")
    ).lower()

    if not email:
        return False

    # Principal requisito:
    # se já foi enviado anteriormente, pula.
    if email in emails_enviados:
        return False

    ranking = contato.get(
        "ranking",
        {},
    )

    categoria = ranking.get(
        "categoria"
    )

    score = ranking.get(
        "score",
        0,
    )

    if (
        CATEGORIAS_PERMITIDAS
        and categoria not in CATEGORIAS_PERMITIDAS
    ):
        return False

    if score < SCORE_MINIMO:
        return False

    return True


# ============================================================
# VISUALIZAÇÃO
# ============================================================

def mostrar_contato(
    indice,
    contato,
):
    ranking = contato.get(
        "ranking",
        {},
    )

    print()
    print("=" * 78)

    print(
        f"#{indice}"
    )

    print(
        f"Score:     "
        f"{ranking.get('score')}"
    )

    print(
        f"Categoria: "
        f"{ranking.get('categoria')}"
    )

    print(
        f"Entidade:  "
        f"{obter_nome_entidade(contato)}"
    )

    print(
        f"E-mail:    "
        f"{contato.get('email')}"
    )

    localidade = obter_localidade(
        contato
    )

    if localidade:
        print(
            f"Local:     "
            f"{localidade}"
        )

    print()
    print(
        criar_corpo(
            contato
        )
    )


# ============================================================
# EXECUÇÃO
# ============================================================

def executar():
    validar_configuracao()

    dados = carregar_json(
        ARQUIVO_CONTATOS
    )

    contatos = dados[
        "contatos"
    ]

    # --------------------------------------------------------
    # Lê o histórico existente
    # --------------------------------------------------------

    emails_enviados = (
        carregar_emails_enviados()
    )

    print("=" * 78)

    print(
        f"Arquivo de contatos: "
        f"{ARQUIVO_CONTATOS}"
    )

    print(
        f"Arquivo de saída:    "
        f"{ARQUIVO_SAIDA}"
    )

    print(
        f"Contatos no JSON:    "
        f"{len(contatos)}"
    )

    print(
        f"Já enviados:         "
        f"{len(emails_enviados)}"
    )

    print(
        f"DRY_RUN:             "
        f"{DRY_RUN}"
    )

    print(
        f"Score mínimo:        "
        f"{SCORE_MINIMO}"
    )

    print(
        f"Categorias:          "
        f"{', '.join(sorted(CATEGORIAS_PERMITIDAS))}"
    )

    print(
        f"Intervalo:           "
        f"{INTERVALO_SEGUNDOS}s"
    )

    print("=" * 78)

    selecionados = [
        contato
        for contato in contatos
        if contato_deve_ser_enviado(
            contato,
            emails_enviados,
        )
    ]

    print(
        f"Elegíveis ainda não enviados: "
        f"{len(selecionados)}"
    )

    selecionados = selecionados[
        :MAX_ENVIOS_POR_EXECUCAO
    ]

    print(
        f"Selecionados nesta execução: "
        f"{len(selecionados)}"
    )

    if not selecionados:
        print(
            "Nenhum contato disponível."
        )

        return

    # ========================================================
    # DRY RUN
    # ========================================================

    if DRY_RUN:

        for indice, contato in enumerate(
            selecionados,
            start=1,
        ):
            mostrar_contato(
                indice,
                contato,
            )

        print()
        print(
            "DRY_RUN ativo. "
            "Nenhum e-mail foi enviado."
        )

        # IMPORTANTE:
        # Dry run NÃO grava no arquivo de saída.

        return

    # ========================================================
    # ENVIO REAL
    # ========================================================

    contexto_ssl = (
        ssl.create_default_context()
    )

    enviados_nesta_execucao = 0
    erros = 0
    erros_consecutivos = 0

    with smtplib.SMTP_SSL(
        SMTP_HOST,
        SMTP_PORT,
        context=contexto_ssl,
    ) as smtp:

        smtp.login(
            GMAIL_EMAIL,
            GMAIL_APP_PASSWORD,
        )

        for indice, contato in enumerate(
            selecionados,
            start=1,
        ):

            email = limpar_texto(
                contato["email"]
            ).lower()

            nome = obter_nome_entidade(
                contato
            )

            ranking = contato.get(
                "ranking",
                {},
            )

            score = ranking.get(
                "score"
            )

            try:

                mensagem = criar_mensagem(
                    contato
                )

                smtp.send_message(
                    mensagem
                )

                # Registra imediatamente no arquivo.
                append_registro_saida(
                    contato=contato,
                    status="enviado",
                )

                # Também atualiza a memória desta execução.
                emails_enviados.add(
                    email
                )

                enviados_nesta_execucao += 1
                erros_consecutivos = 0

                print(
                    f"[{indice}/"
                    f"{len(selecionados)}] "
                    f"OK | "
                    f"{score} | "
                    f"{nome} | "
                    f"{email}"
                )

            except Exception as erro:

                erros += 1
                erros_consecutivos += 1

                # Erros também ficam registrados.
                #
                # Como status != "enviado", o e-mail poderá
                # ser tentado novamente na próxima execução.
                append_registro_saida(
                    contato=contato,
                    status="erro",
                    erro=erro,
                )

                print(
                    f"[{indice}/"
                    f"{len(selecionados)}] "
                    f"ERRO | "
                    f"{nome} | "
                    f"{email}"
                )

                print(
                    f"       {erro}"
                )

                if (
                    erros_consecutivos
                    >= MAX_ERROS_CONSECUTIVOS
                ):

                    print()
                    print(
                        "Muitos erros consecutivos. "
                        "Execução interrompida."
                    )

                    break

            if indice < len(selecionados):
                time.sleep(
                    INTERVALO_SEGUNDOS
                )

    print()
    print("=" * 78)

    print(
        f"Enviados nesta execução: "
        f"{enviados_nesta_execucao}"
    )

    print(
        f"Erros nesta execução:    "
        f"{erros}"
    )

    print(
        f"Histórico:                "
        f"{ARQUIVO_SAIDA}"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    executar()