#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


class AnalisadorArgumentos(argparse.ArgumentParser):
    def format_help(self):
        return (
            super().format_help()
            .replace("usage:", "uso:")
            .replace("options:", "opções:")
        )

    def format_usage(self):
        return super().format_usage().replace("usage:", "uso:")


SCHEMA = """
CREATE TABLE contatos (
    email TEXT PRIMARY KEY,
    tipo_contato TEXT,
    prioridade_envio INTEGER,
    relevancia_sp TEXT,
    razao_social TEXT,
    nome_fantasia TEXT,
    cnpj TEXT,
    tipo_entidade TEXT,
    situacao_cadastral TEXT,
    municipio TEXT,
    uf TEXT,
    porte TEXT,
    natureza_juridica TEXT,
    tipo_estabelecimento TEXT,
    cnaes_relacionados TEXT,
    modalidades TEXT,
    quantidade_veiculos TEXT,
    telefone TEXT,
    website TEXT,
    responsavel_cadastrado TEXT,
    nome_para_mencionar TEXT,
    cidade_para_mencionar TEXT,
    uf_para_mencionar TEXT,
    fatos_seguros_json TEXT NOT NULL,
    abertura_sugerida TEXT,
    pedido_sugerido TEXT,
    nao_afirmar_json TEXT NOT NULL,
    fonte_nome TEXT,
    fonte_competencia TEXT,
    fonte_url TEXT,
    fonte_campo_email_origem TEXT,
    score INTEGER,
    categoria TEXT,
    componentes_json TEXT NOT NULL,
    bonus_motivos_json TEXT NOT NULL,
    penalidades_motivos_json TEXT NOT NULL,
    motivo_ranking TEXT,
    dados_json TEXT NOT NULL
);

CREATE INDEX idx_contatos_ranking
ON contatos(categoria, score DESC);

CREATE TABLE envios (
    email TEXT PRIMARY KEY,
    entidade TEXT NOT NULL DEFAULT '',
    municipio TEXT NOT NULL DEFAULT '',
    uf TEXT NOT NULL DEFAULT '',
    score INTEGER,
    categoria TEXT,
    status TEXT NOT NULL,
    data TEXT,
    erro TEXT
);
"""


INSERT_CONTATO = """
INSERT INTO contatos VALUES (
    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
)
"""


def serializar_json(valor):
    return json.dumps(
        valor,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def contato_para_linha(contato):
    entidade = contato.get("entidade", {})
    outros = contato.get("outros_contatos", {})
    personalizacao = contato.get("personalizacao", {})
    fonte = contato.get("fonte", {})
    ranking = contato.get("ranking", {})
    email = str(contato.get("email") or "").strip().lower()

    if not email:
        raise ValueError("contato sem e-mail")

    return (
        email,
        contato.get("tipo_contato"), contato.get("prioridade_envio"),
        contato.get("relevancia_sp"), entidade.get("razao_social"),
        entidade.get("nome_fantasia"), entidade.get("cnpj"),
        entidade.get("tipo"), entidade.get("situacao_cadastral"),
        entidade.get("municipio"), entidade.get("uf"),
        entidade.get("porte"), entidade.get("natureza_juridica"),
        entidade.get("tipo_estabelecimento"),
        entidade.get("cnaes_relacionados"), entidade.get("modalidades"),
        entidade.get("quantidade_veiculos"), outros.get("telefone"),
        outros.get("website"), outros.get("responsavel_cadastrado"),
        personalizacao.get("nome_para_mencionar"),
        personalizacao.get("cidade_para_mencionar"),
        personalizacao.get("uf_para_mencionar"),
        serializar_json(personalizacao.get("fatos_seguros_para_usar", [])),
        personalizacao.get("abertura_sugerida"),
        personalizacao.get("pedido_sugerido"),
        serializar_json(
            personalizacao.get("nao_afirmar_sem_confirmacao", [])
        ),
        fonte.get("nome"), fonte.get("competencia"), fonte.get("url"),
        fonte.get("campo_email_origem"), ranking.get("score"),
        ranking.get("categoria"),
        serializar_json(ranking.get("componentes", {})),
        serializar_json(ranking.get("bonus_motivos", [])),
        serializar_json(ranking.get("penalidades_motivos", [])),
        ranking.get("motivo"), serializar_json(contato),
    )


def carregar_contatos(caminho):
    with caminho.open("r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    contatos = dados.get("contatos") if isinstance(dados, dict) else dados
    if not isinstance(contatos, list):
        raise ValueError(
            "o JSON deve ser uma lista ou um objeto com a chave 'contatos'"
        )

    return contatos


def criar_banco(arquivo_json, arquivo_saida, sobrescrever=False):
    arquivo_json = arquivo_json.resolve()
    arquivo_saida = arquivo_saida.resolve()

    if not arquivo_json.is_file():
        raise FileNotFoundError(f"arquivo JSON não encontrado: {arquivo_json}")

    if arquivo_saida.exists() and not sobrescrever:
        raise FileExistsError(
            f"o arquivo de saída já existe: {arquivo_saida}; "
            "use --sobrescrever para substituí-lo"
        )

    contatos = carregar_contatos(arquivo_json)
    linhas = []
    for indice, contato in enumerate(contatos, start=1):
        if not isinstance(contato, dict):
            raise ValueError(f"contato #{indice} não é um objeto JSON")
        try:
            linhas.append(contato_para_linha(contato))
        except ValueError as erro:
            raise ValueError(f"contato #{indice}: {erro}") from erro

    arquivo_saida.parent.mkdir(parents=True, exist_ok=True)
    if arquivo_saida.exists():
        arquivo_saida.unlink()

    conexao = None
    try:
        conexao = sqlite3.connect(arquivo_saida)
        conexao.execute("PRAGMA synchronous = FULL")
        with conexao:
            conexao.executescript(SCHEMA)
            conexao.executemany(INSERT_CONTATO, linhas)
    except Exception:
        if conexao is not None:
            conexao.close()
        arquivo_saida.unlink(missing_ok=True)
        raise
    else:
        conexao.close()

    return len(linhas)


def criar_parser():
    parser = AnalisadorArgumentos(
        description="Cria o banco SQLite de contatos a partir de um JSON.",
        add_help=False,
    )
    parser.add_argument(
        "-h", "--ajuda",
        action="help",
        help="mostra esta ajuda e encerra",
    )
    parser.add_argument(
        "-a", "--arquivo",
        dest="arquivo",
        required=True,
        type=Path,
        help="arquivo JSON de entrada",
    )
    parser.add_argument(
        "-d", "--destino",
        dest="destino",
        type=Path,
        default=Path("contatos_ranqueados.db"),
        help="arquivo SQLite de saída (padrão: contatos_ranqueados.db)",
    )
    parser.add_argument(
        "--sobrescrever",
        action="store_true",
        help="sobrescreve o arquivo de saída, caso já exista",
    )
    return parser


def principal():
    argumentos = criar_parser().parse_args()
    try:
        quantidade = criar_banco(
            argumentos.arquivo,
            argumentos.destino,
            argumentos.sobrescrever,
        )
    except (OSError, ValueError, json.JSONDecodeError, sqlite3.Error) as erro:
        raise SystemExit(f"Erro: {erro}") from erro

    print(f"Banco criado: {argumentos.destino.resolve()}")
    print(f"Contatos importados: {quantidade}")


if __name__ == "__main__":
    principal()
