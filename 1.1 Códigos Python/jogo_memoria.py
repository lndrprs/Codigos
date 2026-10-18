#!/usr/bin/env python3
"""Jogo de Memorização via CLI.

Uma sequência de caracteres aparece por alguns segundos e some.
Você precisa digitá-la exatamente. A cada rodada a sequência cresce.
Só há UMA tentativa: errou, acabou. A classificação final depende
de quantos caracteres você conseguiu memorizar.
"""

import json
import os
import random
import string
import time
from datetime import datetime

ARQUIVO_RANKING = os.path.join(os.path.expanduser("~"), ".jogo_memoria_ranking.json")

CONJUNTOS = {
    "numeros": ("Números", string.digits),
    "maiusculas": ("Letras maiúsculas", string.ascii_uppercase),
    "minusculas": ("Letras minúsculas", string.ascii_lowercase),
    "simbolos": ("Símbolos especiais", "!@#$%&*?+-=/<>()[]{}_.,;:"),
}

# Caracteres fáceis de confundir ao olhar (opcionalmente removidos)
AMBIGUOS = set("O0Il1|oS5B8")

CONFIG_PADRAO = {
    "numeros": True,
    "maiusculas": True,
    "minusculas": True,
    "simbolos": False,
    "inicio": 3,
    "incremento": 1,
    "tempo_por_char": 1.0,
    "sem_ambiguos": True,
}

CLASSIFICACOES = [
    (20, " Lenda da Memória"),
    (15, " Mestre"),
    (11, " Excelente"),
    (8, " Muito bom"),
    (5, " Bom"),
    (3, " Aprendiz"),
    (0, " Iniciante"),
]


# ---------- utilidades de entrada ----------

def ler_int(msg, padrao, minimo, maximo):
    while True:
        txt = input(f"{msg} [{padrao}]: ").strip()
        if not txt:
            return padrao
        try:
            n = int(txt)
        except ValueError:
            print(" Digite um número inteiro.")
            continue
        if not minimo <= n <= maximo:
            print(f" Valor deve estar entre {minimo} e {maximo}.")
            continue
        return n


def ler_float(msg, padrao, minimo, maximo):
    while True:
        txt = input(f"{msg} [{padrao}]: ").strip().replace(",", ".")
        if not txt:
            return padrao
        try:
            n = float(txt)
        except ValueError:
            print(" Digite um número (ex: 0,5).")
            continue
        if not minimo <= n <= maximo:
            print(f" Valor deve estar entre {minimo} e {maximo}.")
            continue
        return n


def ler_bool(msg, padrao):
    d = "S/n" if padrao else "s/N"
    while True:
        txt = input(f"{msg} [{d}]: ").strip().lower()
        if not txt:
            return padrao
        if txt in ("s", "sim", "y", "yes"):
            return True
        if txt in ("n", "nao", "não", "no"):
            return False
        print(" Responda com s ou n.")


def limpar_tela():
    if os.system("cls" if os.name == "nt" else "clear") != 0:
        print("\033[2J\033[H", end="")


# ---------- configuração ----------

def alfabeto(cfg):
    chars = "".join(c for chave, (_, c) in CONJUNTOS.items() if cfg[chave])
    if cfg["sem_ambiguos"]:
        chars = "".join(c for c in chars if c not in AMBIGUOS)
    return chars


def configurar(cfg):
    print("\n=== CONFIGURAÇÃO (Enter mantém o valor atual) ===")
    while True:
        for chave, (nome, _) in CONJUNTOS.items():
            cfg[chave] = ler_bool(f"Incluir {nome}?", cfg[chave])
        if any(cfg[k] for k in CONJUNTOS):
            break
        print("  Escolha pelo menos um tipo de caractere.")

    cfg["sem_ambiguos"] = ler_bool(
        "Evitar caracteres parecidos (O/0, I/l/1, S/5, B/8...)?", cfg["sem_ambiguos"])
    cfg["inicio"] = ler_int("Quantidade inicial de caracteres", cfg["inicio"], 1, 30)
    cfg["incremento"] = ler_int("Caracteres a mais por rodada", cfg["incremento"], 1, 5)
    cfg["tempo_por_char"] = ler_float(
        "Segundos de exibição por caractere", cfg["tempo_por_char"], 0.1, 10)
    return cfg


def resumo_config(cfg):
    tipos = ", ".join(nome for chave, (nome, _) in CONJUNTOS.items() if cfg[chave])
    return (f"Tipos: {tipos} | Início: {cfg['inicio']} (+{cfg['incremento']}/rodada) | "
            f"{cfg['tempo_por_char']}s por caractere")


def mostrar_config(cfg):
    print("\nConfiguração atual:")
    print(f"  Tipos: {', '.join(n for k, (n, _) in CONJUNTOS.items() if cfg[k])}")
    print(f"  Evitar ambíguos: {'sim' if cfg['sem_ambiguos'] else 'não'}")
    print(f"  Início: {cfg['inicio']} caracteres (+{cfg['incremento']} por rodada)")
    print(f"  Tempo de exibição: {cfg['tempo_por_char']}s por caractere")
    print(f"  Alfabeto ({len(alfabeto(cfg))}): {alfabeto(cfg)}")


# ---------- ranking ----------

def classificar(pontos):
    for minimo, titulo in CLASSIFICACOES:
        if pontos >= minimo:
            return titulo
    return CLASSIFICACOES[-1][1]


def carregar_ranking():
    try:
        with open(ARQUIVO_RANKING, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def salvar_ranking(nome, pontos, cfg):
    ranking = carregar_ranking()
    ranking.append({
        "nome": nome,
        "pontos": pontos,
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "config": resumo_config(cfg),
    })
    ranking.sort(key=lambda r: r["pontos"], reverse=True)
    ranking = ranking[:10]
    try:
        with open(ARQUIVO_RANKING, "w", encoding="utf-8") as f:
            json.dump(ranking, f, ensure_ascii=False, indent=2)
    except OSError:
        print("  Não foi possível salvar o ranking.")
    return ranking


def mostrar_ranking(ranking, destaque=None):
    print("\n=== TOP 10 ===")
    if not ranking:
        print("Ainda não há registros.")
        return
    for i, r in enumerate(ranking, 1):
        marca = " ◀ você" if r is destaque else ""
        print(f"{i:>2}. {r['nome']:<15} {r['pontos']:>3} caracteres  ({r['data']}){marca}")


# ---------- jogo ----------

def gerar_sequencia(tamanho, chars):
    return "".join(random.choice(chars) for _ in range(tamanho))


def mostrar_diferencas(correta, digitada):
    """Mostra uma linha de marcação apontando onde errou."""
    marcas = ""
    for i, c in enumerate(correta):
        marcas += " " if i < len(digitada) and digitada[i] == c else "^"
    print(f"  Correta : {correta}")
    print(f"  Digitada: {digitada}")
    print(f"            {marcas}")


def jogar(cfg):
    chars = alfabeto(cfg)
    tamanho = cfg["inicio"]
    rodada = 1
    pontos = 0  # maior sequência memorizada com sucesso

    limpar_tela()
    print("=== MEMORIZE! ===")
    print("Você tem UMA tentativa. Errou, acabou. (Maiúsculas e minúsculas contam.)")
    input("Pressione Enter para começar...")

    while True:
        seq = gerar_sequencia(tamanho, chars)
        limpar_tela()
        print(f"Rodada {rodada} — {tamanho} caracteres\n")
        print(f"    {seq}\n")
        time.sleep(tamanho * cfg["tempo_por_char"])
        limpar_tela()

        try:
            resposta = input(f"Rodada {rodada} — digite a sequência de {tamanho} caracteres:\n> ")
        except EOFError:
            resposta = ""
        resposta = resposta.strip()

        if resposta == seq:
            pontos = tamanho
            print(f"\n Correto! ({tamanho} caracteres)")
            time.sleep(0.8)
            tamanho += cfg["incremento"]
            rodada += 1
        else:
            print("\n Errou! Fim de jogo.\n")
            mostrar_diferencas(seq, resposta)
            break

    return pontos, rodada - 1


def tela_final(pontos, rodadas_ok, cfg):
    print("\n=== RESULTADO FINAL ===")
    print(f"Rodadas completas: {rodadas_ok}")
    print(f"Caracteres memorizados: {pontos}")
    print(f"Classificação: {classificar(pontos)}")

    if pontos == 0:
        mostrar_ranking(carregar_ranking())
        return

    nome = input("\nSeu nome para o ranking (Enter para pular): ").strip()[:15]
    if nome:
        ranking = salvar_ranking(nome, pontos, cfg)
        destaque = next((r for r in ranking
                         if r["nome"] == nome and r["pontos"] == pontos), None)
        mostrar_ranking(ranking, destaque)
    else:
        mostrar_ranking(carregar_ranking())


def main():
    cfg = dict(CONFIG_PADRAO)
    print("JOGO DE MEMORIZAÇÃO")
    cfg = configurar(cfg)

    while True:
        mostrar_config(cfg)
        print("\n1 - Jogar\n2 - Mudar configuração\n3 - Ver ranking\n0 - Sair")
        op = input("Escolha: ").strip()
        if op == "1":
            pontos, ok = jogar(cfg)
            tela_final(pontos, ok, cfg)
        elif op == "2":
            cfg = configurar(cfg)
        elif op == "3":
            mostrar_ranking(carregar_ranking())
        elif op == "0":
            break
        else:
            print(" Opção inválida.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n")
