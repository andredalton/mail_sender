#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


COLUNAS = (
    "email",
    "entidade",
    "municipio",
    "uf",
    "score",
    "categoria",
    "status",
    "data",
    "erro",
)


class AnalisadorArgumentos(argparse.ArgumentParser):
    def format_help(self):
        return (
            super().format_help()
            .replace("usage:", "uso:")
            .replace("options:", "opções:")
        )

    def format_usage(self):
        return super().format_usage().replace("usage:", "uso:")


def validar_tabela(conexao):
    tabela = conexao.execute(
        "SELECT 1 FROM sqlite_master "
        "WHERE type = 'table' AND name = 'envios'"
    ).fetchone()
    if tabela is None:
        raise ValueError("o banco não contém a tabela 'envios'")

    colunas_existentes = {
        linha[1]
        for linha in conexao.execute("PRAGMA table_info(envios)")
    }
    ausentes = set(COLUNAS) - colunas_existentes
    if ausentes:
        raise ValueError(
            "a tabela 'envios' não contém as colunas: "
            + ", ".join(sorted(ausentes))
        )


def carregar_registros(arquivo_json):
    with arquivo_json.open("r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    if not isinstance(dados, dict) or "envios" not in dados:
        raise ValueError("o JSON deve conter um objeto chamado 'envios'")

    envios = dados["envios"]
    if isinstance(envios, dict):
        itens = envios.items()
    elif isinstance(envios, list):
        itens = ((None, registro) for registro in envios)
    else:
        raise ValueError("'envios' deve ser um objeto ou uma lista")

    registros = []
    emails = set()
    for indice, (email_chave, registro) in enumerate(itens, start=1):
        if not isinstance(registro, dict):
            raise ValueError(f"registro de envio #{indice} não é um objeto")

        email = str(registro.get("email") or email_chave or "").strip().lower()
        if not email:
            raise ValueError(f"registro de envio #{indice} não possui e-mail")
        if email in emails:
            raise ValueError(f"e-mail duplicado no JSON: {email}")

        situacao = str(registro.get("status") or "").strip().lower()
        if not situacao:
            raise ValueError(f"registro de envio #{indice} não possui status")

        emails.add(email)
        registros.append((
            email,
            str(registro.get("entidade") or "").strip(),
            str(registro.get("municipio") or "").strip(),
            str(registro.get("uf") or "").strip(),
            registro.get("score"),
            registro.get("categoria"),
            situacao,
            registro.get("data"),
            registro.get("erro"),
        ))

    return registros


def importar_envios(
    arquivo_json,
    arquivo_banco,
    sobrescrever=False,
    simular=False,
):
    arquivo_json = arquivo_json.resolve()
    arquivo_banco = arquivo_banco.resolve()

    if not arquivo_json.is_file():
        raise FileNotFoundError(f"arquivo JSON não encontrado: {arquivo_json}")
    if not arquivo_banco.is_file():
        raise FileNotFoundError(f"banco SQLite não encontrado: {arquivo_banco}")

    registros = carregar_registros(arquivo_json)
    conexao = sqlite3.connect(arquivo_banco, timeout=30)
    try:
        conexao.execute("PRAGMA busy_timeout = 30000")
        validar_tabela(conexao)

        existentes = {
            linha[0]
            for linha in conexao.execute("SELECT email FROM envios")
        }
        novos = sum(registro[0] not in existentes for registro in registros)
        atualizados = (
            sum(registro[0] in existentes for registro in registros)
            if sobrescrever
            else 0
        )
        ignorados = len(registros) - novos - atualizados

        if not simular:
            if sobrescrever:
                sql = """
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
                """
            else:
                sql = """
                    INSERT OR IGNORE INTO envios (
                        email, entidade, municipio, uf, score,
                        categoria, status, data, erro
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

            with conexao:
                conexao.executemany(sql, registros)
    finally:
        conexao.close()

    return {
        "lidos": len(registros),
        "novos": novos,
        "atualizados": atualizados,
        "ignorados": ignorados,
    }


def criar_parser():
    parser = AnalisadorArgumentos(
        description="Importa um histórico de envios em JSON para o SQLite.",
        add_help=False,
    )
    parser.add_argument(
        "-h", "--ajuda",
        action="help",
        help="mostra esta ajuda e encerra",
    )
    parser.add_argument(
        "-a", "--arquivo",
        required=True,
        type=Path,
        help="arquivo JSON de envios",
    )
    parser.add_argument(
        "-b", "--banco",
        type=Path,
        default=Path("contatos_ranqueados.db"),
        help="banco SQLite de destino (padrão: contatos_ranqueados.db)",
    )
    parser.add_argument(
        "--sobrescrever",
        action="store_true",
        help="atualiza registros que já existem no banco",
    )
    parser.add_argument(
        "--simular",
        action="store_true",
        help="valida e contabiliza os registros sem alterar o banco",
    )
    return parser


def principal():
    argumentos = criar_parser().parse_args()
    try:
        resultado = importar_envios(
            argumentos.arquivo,
            argumentos.banco,
            sobrescrever=argumentos.sobrescrever,
            simular=argumentos.simular,
        )
    except (OSError, ValueError, json.JSONDecodeError, sqlite3.Error) as erro:
        raise SystemExit(f"Erro: {erro}") from erro

    if argumentos.simular:
        print("Simulação concluída; o banco não foi alterado.")
    else:
        print(f"Banco atualizado: {argumentos.banco.resolve()}")
    print(f"Registros lidos: {resultado['lidos']}")
    print(f"Novos: {resultado['novos']}")
    print(f"Atualizados: {resultado['atualizados']}")
    print(f"Ignorados: {resultado['ignorados']}")


if __name__ == "__main__":
    principal()
