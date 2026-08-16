#!/usr/bin/env python3

import json
import os
import smtplib
import sqlite3
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

def ler_booleano_ambiente(nome, padrao=False):
    valor = os.getenv(nome)

    if valor is None:
        return padrao

    return valor.strip().lower() in {
        "1",
        "true",
        "yes",
        "sim",
        "on",
    }


def ler_inteiro_ambiente(nome, padrao):
    valor = os.getenv(nome)

    if valor is None:
        return padrao

    return int(valor)


def ler_decimal_ambiente(nome, padrao):
    valor = os.getenv(nome)

    if valor is None:
        return padrao

    return float(valor)


def ler_conjunto_ambiente(nome, padrao):
    valor = os.getenv(nome)

    if not valor:
        valor = padrao

    return {
        item.strip()
        for item in valor.split(",")
        if item.strip()
    }


# ============================================================
# ARQUIVOS
# ============================================================

BANCO_DADOS = Path(__file__).resolve().parent / "contatos_ranqueados.db"

# ============================================================
# GMAIL
# ============================================================

EMAIL_GMAIL = os.getenv("EMAIL_GMAIL")

SENHA_APP_GMAIL = os.getenv(
    "SENHA_APP_GMAIL"
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

SIMULACAO = ler_booleano_ambiente(
    "SIMULACAO",
    True,
)

CATEGORIAS_PERMITIDAS = ler_conjunto_ambiente(
    "CATEGORIAS_PERMITIDAS",
    "A",
)

SCORE_MINIMO = ler_inteiro_ambiente(
    "SCORE_MINIMO",
    80,
)

MAXIMO_ENVIOS_POR_EXECUCAO = ler_inteiro_ambiente(
    "MAXIMO_ENVIOS_POR_EXECUCAO",
    10,
)

INTERVALO_SEGUNDOS = ler_decimal_ambiente(
    "INTERVALO_SEGUNDOS",
    30.0,
)

MAXIMO_ERROS_CONSECUTIVOS = ler_inteiro_ambiente(
    "MAXIMO_ERROS_CONSECUTIVOS",
    5,
)


# ============================================================
# SMTP
# ============================================================

SERVIDOR_SMTP = os.getenv(
    "SERVIDOR_SMTP",
    "smtp.gmail.com",
)

PORTA_SMTP = ler_inteiro_ambiente(
    "PORTA_SMTP",
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


# ============================================================
# HISTÓRICO DE ENVIO
# ============================================================

def conectar_banco():
    conexao = sqlite3.connect(
        BANCO_DADOS,
        timeout=30,
    )
    conexao.execute("PRAGMA busy_timeout = 30000")
    conexao.execute("PRAGMA synchronous = FULL")
    return conexao


def carregar_contatos_banco():
    with conectar_banco() as conexao:
        linhas = conexao.execute(
            "SELECT dados_json FROM contatos "
            "ORDER BY score DESC, prioridade_envio, rowid"
        )
        return [json.loads(linha[0]) for linha in linhas]


def carregar_emails_enviados():
    """
    Retorna destinatários enviados ou com resultado incerto.
    """

    with conectar_banco() as conexao:
        linhas = conexao.execute(
            """
            SELECT email FROM envios
            WHERE status IN ('enviado', 'enviando')
            """
        )
        return {linha[0] for linha in linhas}


def append_registro_saida(
    contato,
    status,
    erro=None,
):
    """
    Adiciona ou atualiza o registro no banco SQLite.
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

    with conectar_banco() as conexao:
        conexao.execute(
            """
            INSERT INTO envios (
                email, entidade, municipio, uf, score,
                categoria, status, data, erro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                entidade = excluded.entidade,
                municipio = excluded.municipio,
                uf = excluded.uf,
                score = excluded.score,
                categoria = excluded.categoria,
                status = excluded.status,
                data = excluded.data,
                erro = excluded.erro
            """,
            (
                registro["email"],
                registro["entidade"],
                registro["municipio"],
                registro["uf"],
                registro["score"],
                registro["categoria"],
                registro["status"],
                registro["data"],
                registro["erro"],
            ),
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
        f"{NOME} <{EMAIL_GMAIL}>"
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

    if not EMAIL_GMAIL:
        erros.append(
            "EMAIL_GMAIL não definido no .env"
        )

    if not SENHA_APP_GMAIL:
        erros.append(
            "SENHA_APP_GMAIL não definido no .env"
        )

    if not BANCO_DADOS.is_file():
        erros.append(
            "Banco de dados não encontrado: "
            f"{BANCO_DADOS}"
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

    contatos = carregar_contatos_banco()

    # --------------------------------------------------------
    # Lê o histórico existente
    # --------------------------------------------------------

    emails_enviados = (
        carregar_emails_enviados()
    )

    print("=" * 78)

    print(
        f"Banco de dados:       "
        f"{BANCO_DADOS}"
    )

    print(
        f"Histórico:            "
        f"tabela envios"
    )

    print(
        f"Contatos no banco:   "
        f"{len(contatos)}"
    )

    print(
        f"Enviados/pendentes:  "
        f"{len(emails_enviados)}"
    )

    print(
        f"SIMULAÇÃO:           "
        f"{SIMULACAO}"
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
        :MAXIMO_ENVIOS_POR_EXECUCAO
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

    if SIMULACAO:

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
            "SIMULAÇÃO ativa. "
            "Nenhum e-mail foi enviado."
        )

        # IMPORTANTE:
        # Dry run NÃO grava no banco de histórico.

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
        SERVIDOR_SMTP,
        PORTA_SMTP,
        context=contexto_ssl,
    ) as smtp:

        smtp.login(
            EMAIL_GMAIL,
            SENHA_APP_GMAIL,
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

            email_aceito_pelo_smtp = False

            try:

                # Se houver uma interrupção a partir daqui, este
                # destinatário fica bloqueado como resultado incerto.
                append_registro_saida(
                    contato=contato,
                    status="enviando",
                )

                mensagem = criar_mensagem(
                    contato
                )

                smtp.send_message(
                    mensagem
                )
                email_aceito_pelo_smtp = True

                # Confirma o sucesso em uma transação separada.
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

                if not email_aceito_pelo_smtp:
                    # Falhou antes da confirmação do SMTP: pode
                    # ser tentado novamente em outra execução.
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

                if email_aceito_pelo_smtp:
                    print(
                        "       O SMTP aceitou a mensagem, mas não foi "
                        "possível confirmar no banco. O registro "
                        "permanece como 'enviando' para evitar duplicação."
                    )
                    break

                if (
                    erros_consecutivos
                    >= MAXIMO_ERROS_CONSECUTIVOS
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
        f"{BANCO_DADOS} (tabela envios)"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    executar()
