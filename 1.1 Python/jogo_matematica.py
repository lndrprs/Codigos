#!/usr/bin/env python3
"""Jogo de Matemática via CLI.

Modos: Soma, Subtração, Multiplicação, Divisão (ou Misto).
Configurável: nº de perguntas, casas decimais, faixa de valores,
negativos na subtração, tempo por pergunta.
"""

import random
import time
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

MODOS = {
    "1": ("Soma", "+"),
    "2": ("Subtração", "-"),
    "3": ("Multiplicação", "×"),
    "4": ("Divisão", "÷"),
}

CONFIG_PADRAO = {
    "modos": ["1"],
    "perguntas": 10,
    "casas": 0,
    "minimo": 1,
    "maximo": 20,
    "negativos": False,
    "mostrar_tempo": True,
}


# ---------- utilidades ----------

def fmt(valor: Decimal, casas: int) -> str:
    """Formata no padrão brasileiro (vírgula decimal)."""
    return f"{valor:.{casas}f}".replace(".", ",")


def arredonda(valor: Decimal, casas: int) -> Decimal:
    return valor.quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)


def ler_int(msg, padrao, minimo=None, maximo=None):
    while True:
        txt = input(f"{msg} [{padrao}]: ").strip()
        if not txt:
            return padrao
        try:
            n = int(txt)
        except ValueError:
            print("  ⚠ Digite um número inteiro.")
            continue
        if (minimo is not None and n < minimo) or (maximo is not None and n > maximo):
            print(f"  ⚠ Valor deve estar entre {minimo} e {maximo}.")
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
        print("  ⚠ Responda com s ou n.")


def ler_resposta(msg):
    """Lê um número (aceita vírgula ou ponto). Retorna None se 'sair'."""
    while True:
        txt = input(msg).strip().lower()
        if txt in ("sair", "q", "quit"):
            return None
        try:
            return Decimal(txt.replace(",", "."))
        except InvalidOperation:
            print("  ⚠ Digite um número válido (ou 'sair' para encerrar).")


# ---------- geração de perguntas ----------

def numero_aleatorio(minimo, maximo, casas):
    fator = 10 ** casas
    return Decimal(random.randint(minimo * fator, maximo * fator)) / fator


def gerar_pergunta(modo, cfg):
    casas, lo, hi = cfg["casas"], cfg["minimo"], cfg["maximo"]
    a = numero_aleatorio(lo, hi, casas)
    b = numero_aleatorio(lo, hi, casas)

    if modo == "1":
        return a, b, "+", a + b

    if modo == "2":
        if not cfg["negativos"] and b > a:
            a, b = b, a
        return a, b, "-", a - b

    if modo == "3":
        return a, b, "×", a * b

    # Divisão exata: divisor inteiro, quociente com `casas` decimais,
    # dividendo = divisor * quociente (sem resto estranho).
    lo_d = max(lo, 1)
    hi_d = max(hi, lo_d)
    divisor = Decimal(random.randint(lo_d, hi_d))
    quociente = numero_aleatorio(lo_d, hi_d, casas)
    return divisor * quociente, divisor, "÷", quociente


def checar(resposta, correta, casas):
    """Aceita a resposta exata ou arredondada para `casas` decimais."""
    return resposta == correta or resposta == arredonda(correta, casas)


# ---------- configuração ----------

def escolher_modos(atual):
    print("\nModos disponíveis:")
    for k, (nome, simbolo) in MODOS.items():
        print(f"  {k} - {nome} ({simbolo})")
    print("  5 - Misto (todos)")
    while True:
        txt = input(f"Escolha um ou mais (ex: 1,3) [{','.join(atual)}]: ").strip()
        if not txt:
            return atual
        if txt == "5":
            return list(MODOS)
        escolhas = [t.strip() for t in txt.replace(" ", ",").split(",") if t.strip()]
        if escolhas and all(e in MODOS for e in escolhas):
            return sorted(set(escolhas))
        print("  ⚠ Opção inválida.")


def configurar(cfg):
    print("\n=== CONFIGURAÇÃO (Enter mantém o valor atual) ===")
    cfg["modos"] = escolher_modos(cfg["modos"])
    cfg["perguntas"] = ler_int("Número de perguntas", cfg["perguntas"], 1, 1000)
    cfg["casas"] = ler_int("Casas decimais nos números", cfg["casas"], 0, 6)
    cfg["minimo"] = ler_int("Valor mínimo", cfg["minimo"], -10**6, 10**6)
    while True:
        cfg["maximo"] = ler_int("Valor máximo", cfg["maximo"], -10**6, 10**6)
        if cfg["maximo"] >= cfg["minimo"]:
            break
        print("  ⚠ O máximo deve ser maior ou igual ao mínimo.")
    if "2" in cfg["modos"]:
        cfg["negativos"] = ler_bool("Permitir resultados negativos na subtração?",
                                    cfg["negativos"])
    cfg["mostrar_tempo"] = ler_bool("Mostrar tempo por pergunta?", cfg["mostrar_tempo"])
    return cfg


def mostrar_config(cfg):
    nomes = ", ".join(MODOS[m][0] for m in cfg["modos"])
    print("\nConfiguração atual:")
    print(f"  Modos: {nomes}")
    print(f"  Perguntas: {cfg['perguntas']}")
    print(f"  Casas decimais: {cfg['casas']}")
    print(f"  Faixa: {cfg['minimo']} a {cfg['maximo']}")
    if "2" in cfg["modos"]:
        print(f"  Negativos na subtração: {'sim' if cfg['negativos'] else 'não'}")
    print(f"  Mostrar tempo: {'sim' if cfg['mostrar_tempo'] else 'não'}")


# ---------- jogo ----------

def jogar(cfg):
    casas = cfg["casas"]
    acertos = 0
    respondidas = 0
    tempo_total = 0.0

    print("\n=== VAMOS LÁ! (digite 'sair' para encerrar) ===")
    if casas > 0:
        print(f"Dica: use até {casas} casa(s) decimal(is); vírgula ou ponto valem.")

    for i in range(1, cfg["perguntas"] + 1):
        modo = random.choice(cfg["modos"])
        a, b, op, correta = gerar_pergunta(modo, cfg)
        correta_arred = arredonda(correta, casas)

        sufixo = ""
        if correta != correta_arred:
            sufixo = f"  (arredonde para {casas} casa(s))"

        inicio = time.perf_counter()
        resp = ler_resposta(f"\n[{i}/{cfg['perguntas']}] {fmt(a, casas)} {op} {fmt(b, casas)} = ?{sufixo} ")
        if resp is None:
            print("Jogo encerrado antes do fim.")
            break
        dt = time.perf_counter() - inicio

        respondidas += 1
        tempo_total += dt
        extra = f" ({dt:.1f}s)" if cfg["mostrar_tempo"] else ""

        if checar(resp, correta, casas):
            acertos += 1
            print(f"Correto!{extra}")
        else:
            print(f"Errado. Resposta: {fmt(correta_arred, casas)}{extra}")

    resumo(acertos, respondidas, tempo_total)


def resumo(acertos, respondidas, tempo_total):
    print("\n=== RESULTADO ===")
    if respondidas == 0:
        print("Nenhuma pergunta respondida.")
        return
    pct = acertos / respondidas * 100
    print(f"Acertos: {acertos}/{respondidas} ({pct:.0f}%)")
    print(f"Tempo total: {tempo_total:.1f}s | Média: {tempo_total / respondidas:.1f}s por pergunta")
    if pct == 100:
        print("Perfeito!")
    elif pct >= 70:
        print("Muito bem!")
    else:
        print("Continue praticando!")


def main():
    cfg = dict(CONFIG_PADRAO)
    print("JOGO DE MATEMÁTICA")
    cfg = configurar(cfg)

    while True:
        mostrar_config(cfg)
        print("\n1 - Jogar\n2 - Mudar configuração\n0 - Sair")
        op = input("Escolha: ").strip()
        if op == "1":
            jogar(cfg)
        elif op == "2":
            cfg = configurar(cfg)
            break
        else:
            print("  ⚠ Opção inválida.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nAté a próxima! 👋")
