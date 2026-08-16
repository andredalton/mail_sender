#!/usr/bin/env python3

import argparse
import json
import sqlite3
from datetime import datetime, timezone
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


def validar_banco(conexao):
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


def consultar_envios(conexao, situacoes):
    sql = f"SELECT {', '.join(COLUNAS)} FROM envios"
    parametros = []

    if situacoes:
        marcadores = ", ".join("?" for _ in situacoes)
        sql += f" WHERE status IN ({marcadores})"
        parametros.extend(situacoes)

    sql += " ORDER BY data, email"
    conexao.row_factory = sqlite3.Row
    return [dict(linha) for linha in conexao.execute(sql, parametros)]


def montar_exportacao(registros, arquivo_banco, situacoes):
    return {
        "metadados": {
            "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "banco": arquivo_banco.name,
            "quantidade": len(registros),
            "situacoes": sorted(situacoes) if situacoes else "todas",
        },
        "envios": {
            registro["email"]: registro
            for registro in registros
        },
    }


def gravar_json(dados, arquivo_saida, sobrescrever=False, compacto=False):
    arquivo_saida = arquivo_saida.resolve()

    if arquivo_saida.exists() and not sobrescrever:
        raise FileExistsError(
            f"o arquivo de saída já existe: {arquivo_saida}; "
            "use --sobrescrever para substituí-lo"
        )

    arquivo_saida.parent.mkdir(parents=True, exist_ok=True)
    temporario = arquivo_saida.with_name(f".{arquivo_saida.name}.tmp")

    try:
        with temporario.open("w", encoding="utf-8", newline="\n") as arquivo:
            json.dump(
                dados,
                arquivo,
                ensure_ascii=False,
                indent=None if compacto else 2,
                separators=(",", ":") if compacto else None,
            )
            arquivo.write("\n")
        temporario.replace(arquivo_saida)
    except Exception:
        temporario.unlink(missing_ok=True)
        raise


def gerar_dump(
    arquivo_banco,
    arquivo_saida,
    sobrescrever=False,
    situacoes=None,
    compacto=False,
):
    arquivo_banco = arquivo_banco.resolve()
    arquivo_saida = arquivo_saida.resolve()
    situacoes = {
        situacao.strip().lower()
        for situacao in (situacoes or [])
        if situacao.strip()
    }

    if not arquivo_banco.is_file():
        raise FileNotFoundError(f"banco SQLite não encontrado: {arquivo_banco}")

    if arquivo_saida == arquivo_banco:
        raise ValueError(
            "o arquivo de saída não pode ser o próprio banco SQLite"
        )

    uri = arquivo_banco.as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as conexao:
        validar_banco(conexao)
        registros = consultar_envios(conexao, situacoes)

    dados = montar_exportacao(registros, arquivo_banco, situacoes)
    gravar_json(dados, arquivo_saida, sobrescrever, compacto)
    return len(registros)


def criar_parser():
    parser = AnalisadorArgumentos(
        description="Exporta a tabela envios de um banco SQLite para JSON.",
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
        help="arquivo SQLite de entrada",
    )
    parser.add_argument(
        "-d", "--destino",
        dest="destino",
        type=Path,
        default=Path("enviados.json"),
        help="arquivo JSON de saída (padrão: enviados.json)",
    )
    parser.add_argument(
        "-s", "--situacao",
        dest="situacoes",
        action="append",
        default=[],
        help=(
            "exporta apenas esta situação; pode ser repetido, "
            "por exemplo: -s enviado -s erro"
        ),
    )
    parser.add_argument(
        "--compacto",
        action="store_true",
        help="gera JSON compacto, sem indentação",
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
        quantidade = gerar_dump(
            argumentos.arquivo,
            argumentos.destino,
            sobrescrever=argumentos.sobrescrever,
            situacoes=argumentos.situacoes,
            compacto=argumentos.compacto,
        )
    except (OSError, ValueError, sqlite3.Error) as erro:
        raise SystemExit(f"Erro: {erro}") from erro

    print(f"JSON criado: {argumentos.destino.resolve()}")
    print(f"Registros exportados: {quantidade}")


if __name__ == "__main__":
    principal()
