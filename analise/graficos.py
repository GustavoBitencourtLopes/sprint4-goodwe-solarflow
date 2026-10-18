"""SolarFlow - Analise da telemetria e geracao de graficos.

Como usar:
  1. Rode a simulacao no Wokwi e copie TODO o texto do Serial Monitor.
  2. Cole em um arquivo chamado telemetria.txt, na mesma pasta deste script.
  3. Execute:  python graficos.py
Saida: pasta graficos/ com as imagens e telemetria.csv com os dados limpos.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # gera as imagens sem abrir janelas
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd

PASTA = Path(__file__).resolve().parent
ARQUIVO_ENTRADA = PASTA / "telemetria.txt"
PASTA_GRAFICOS = PASTA / "graficos"

# Mesmas cores dos LEDs da estacao
COR_SOLAR = "#F2B705"
COR_BATERIA = "#2E86DE"
COR_REDE = "#E74C3C"
COR_INJETADA = "#27AE60"
COR_A = "#16A085"
COR_B = "#8E44AD"

SOC_ALVO = 80
BAT_MIN = 20
BAT_RESERVA = 50
ESTADOS_SEM_VEICULO = ("DISPONIVEL", "EMERGENCIA")
# Colunas padrao da telemetria (usadas se a linha COLUNAS nao for copiada)
COLUNAS_PADRAO = ["t_min", "dt_min", "hora", "modo", "ponta", "solar_kw", "solar_veic_kw",
                  "bat_veic_kw", "rede_veic_kw", "bat_carga_kw", "injetada_kw", "bat_soc",
                  "a_estado", "a_soc", "a_kw", "b_estado", "b_soc", "b_kw"]
NUMERICAS = ["t_min", "dt_min", "ponta", "solar_kw", "solar_veic_kw", "bat_veic_kw",
             "rede_veic_kw", "bat_carga_kw", "injetada_kw", "bat_soc",
             "a_soc", "a_kw", "b_soc", "b_kw"]


def ler_telemetria(caminho):
    """Le o texto do Serial Monitor e devolve um DataFrame da ultima execucao."""
    if not caminho.exists():
        raise SystemExit(f"Arquivo nao encontrado: {caminho}\n"
                         "Cole o texto do Serial Monitor em telemetria.txt.")

    execucoes, colunas, atual = [], None, []
    for linha in caminho.read_text(encoding="utf-8", errors="ignore").splitlines():
        linha = linha.strip()
        if linha.startswith("COLUNAS,"):           # nova execucao da simulacao
            if atual:
                execucoes.append(atual)
            colunas, atual = linha.split(",")[1:], []
        elif linha.startswith("DADOS,"):
            if colunas is None:                    # COLUNAS nao foi copiada: usa o padrao
                colunas = COLUNAS_PADRAO
            valores = linha.split(",")[1:]
            if len(valores) == len(colunas):       # ignora linhas cortadas
                atual.append(dict(zip(colunas, valores)))
    if atual:
        execucoes.append(atual)
    if not execucoes:
        raise SystemExit("Nenhuma linha de telemetria encontrada em telemetria.txt.")

    df = pd.DataFrame(execucoes[-1])               # usa a execucao mais recente
    for coluna in NUMERICAS:
        # Remove caracteres soltos da copia (ex.: ")") e converte para numero
        valores = df[coluna].str.replace(r"[^0-9.\-]", "", regex=True)
        df[coluna] = pd.to_numeric(valores, errors="coerce")
    df = df.dropna(subset=NUMERICAS).reset_index(drop=True)   # descarta linhas corrompidas
    if df.empty:
        raise SystemExit("As linhas de telemetria estao corrompidas. Copie o Serial Monitor de novo.")

    # Eixo X em horas do relogio simulado (pode passar de 24h)
    h, m = map(int, df["hora"].iloc[0].split(":"))
    hora_inicio = h + m / 60 - df["t_min"].iloc[0] / 60
    df["hora_dec"] = hora_inicio + df["t_min"] / 60

    # SOC dos veiculos so existe com veiculo conectado
    for p in ("a", "b"):
        df.loc[df[f"{p}_estado"].isin(ESTADOS_SEM_VEICULO), f"{p}_soc"] = float("nan")
    return df


def calcular_energias(df):
    """Integra potencia x tempo de cada ciclo (kWh)."""
    horas = df["dt_min"] / 60
    return {
        "solar_gerada": (df["solar_kw"] * horas).sum(),
        "solar_veiculos": (df["solar_veic_kw"] * horas).sum(),
        "bateria_veiculos": (df["bat_veic_kw"] * horas).sum(),
        "rede_veiculos": (df["rede_veic_kw"] * horas).sum(),
        "bateria_carga": (df["bat_carga_kw"] * horas).sum(),
        "injetada": (df["injetada_kw"] * horas).sum(),
    }


def formatar_hora(x, _pos):
    minutos = int(round(x * 60)) % (24 * 60)
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def preparar_eixo(ax, df, titulo, rotulo_y):
    """Titulo, grade, eixo de horas e faixa do horario de ponta."""
    ax.set_title(titulo, fontsize=11, fontweight="bold")
    ax.set_ylabel(rotulo_y)
    ax.grid(alpha=0.3)
    ax.xaxis.set_major_formatter(FuncFormatter(formatar_hora))
    ax.set_xlim(df["hora_dec"].iloc[0], df["hora_dec"].iloc[-1])

    inicio = None
    for x, ponta in zip(df["hora_dec"], df["ponta"]):
        if ponta and inicio is None:
            inicio = x
        elif not ponta and inicio is not None:
            ax.axvspan(inicio, x, color="gray", alpha=0.15, lw=0, zorder=0)
            inicio = None
    if inicio is not None:
        ax.axvspan(inicio, df["hora_dec"].iloc[-1], color="gray", alpha=0.15, lw=0, zorder=0)


def grafico_fontes(ax, df):
    x = df["hora_dec"]
    solar = df["solar_veic_kw"]
    bateria = solar + df["bat_veic_kw"]
    rede = bateria + df["rede_veic_kw"]
    ax.fill_between(x, 0, solar, step="pre", color=COR_SOLAR, alpha=0.85, label="Solar")
    ax.fill_between(x, solar, bateria, step="pre", color=COR_BATERIA, alpha=0.85, label="Bateria")
    ax.fill_between(x, bateria, rede, step="pre", color=COR_REDE, alpha=0.85, label="Rede")
    ax.step(x, df["solar_kw"], where="pre", color="black", lw=1.2, ls="--", label="Geração solar")
    preparar_eixo(ax, df, "Origem da energia entregue aos veículos", "Potência (kW)")
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper right", fontsize=8)


def grafico_soc_veiculos(ax, df):
    ax.plot(df["hora_dec"], df["a_soc"], color=COR_A, lw=2, label="Veículo A")
    ax.plot(df["hora_dec"], df["b_soc"], color=COR_B, lw=2, label="Veículo B")
    ax.axhline(SOC_ALVO, color="black", ls=":", lw=1, label=f"Alvo ({SOC_ALVO}%)")
    preparar_eixo(ax, df, "Carga (SOC) dos veículos", "SOC (%)")
    ax.set_ylim(0, 100)
    ax.legend(loc="lower right", fontsize=8)


def grafico_potencia_pontos(ax, df):
    ax.step(df["hora_dec"], df["a_kw"], where="pre", color=COR_A, lw=2, label="Ponto A")
    ax.step(df["hora_dec"], df["b_kw"], where="pre", color=COR_B, lw=2, label="Ponto B")
    preparar_eixo(ax, df, "Potência por ponto (divisão proporcional)", "Potência (kW)")
    ax.set_ylim(0, 7.5)
    ax.legend(loc="upper right", fontsize=8)


def grafico_bateria(ax, df):
    ax.plot(df["hora_dec"], df["bat_soc"], color=COR_BATERIA, lw=2, label="SOC da bateria")
    ax.axhline(BAT_RESERVA, color=COR_BATERIA, ls="--", lw=1, label=f"Reserva p/ ponta ({BAT_RESERVA}%)")
    ax.axhline(BAT_MIN, color=COR_REDE, ls=":", lw=1, label=f"Mínimo de proteção ({BAT_MIN}%)")
    preparar_eixo(ax, df, "Bateria estacionária", "SOC (%)")
    ax.set_ylim(0, 105)
    ax.legend(loc="lower right", fontsize=8)


def grafico_resumo(ax, e):
    nomes = ["Solar\n(direto)", "Bateria", "Rede", "Injetada\nna rede"]
    valores = [e["solar_veiculos"], e["bateria_veiculos"], e["rede_veiculos"], e["injetada"]]
    cores = [COR_SOLAR, COR_BATERIA, COR_REDE, COR_INJETADA]
    barras = ax.bar(nomes, valores, color=cores)
    for barra, valor in zip(barras, valores):
        ax.annotate(f"{valor:.1f} kWh", (barra.get_x() + barra.get_width() / 2, valor),
                    ha="center", va="bottom", fontsize=9, xytext=(0, 3), textcoords="offset points")
    ax.set_title("Balanço de energia da sessão", fontsize=11, fontweight="bold")
    ax.set_ylabel("Energia (kWh)")
    ax.set_ylim(0, max(valores + [1]) * 1.2)
    ax.grid(alpha=0.3, axis="y")


def salvar(fig, nome):
    fig.tight_layout()
    fig.savefig(PASTA_GRAFICOS / nome, dpi=150)
    plt.close(fig)
    print(f"  graficos/{nome}")


def main():
    df = ler_telemetria(ARQUIVO_ENTRADA)
    e = calcular_energias(df)
    PASTA_GRAFICOS.mkdir(exist_ok=True)
    df.drop(columns=["hora_dec"]).to_csv(PASTA / "telemetria.csv", index=False)

    entregue = e["solar_veiculos"] + e["bateria_veiculos"] + e["rede_veiculos"]
    renovavel = e["solar_veiculos"] + e["bateria_veiculos"]
    print(f"Linhas de telemetria: {len(df)}  |  periodo: "
          f"{df['hora'].iloc[0]} a {df['hora'].iloc[-1]} ({df['dt_min'].sum() / 60:.1f} h simuladas)")
    print(f"Energia entregue aos veiculos: {entregue:.2f} kWh")
    if entregue > 0:
        print(f"  Solar direto: {e['solar_veiculos']:.2f} kWh ({e['solar_veiculos'] / entregue:.0%})")
        print(f"  Bateria:      {e['bateria_veiculos']:.2f} kWh ({e['bateria_veiculos'] / entregue:.0%})")
        print(f"  Rede:         {e['rede_veiculos']:.2f} kWh ({e['rede_veiculos'] / entregue:.0%})")
        print(f"  Renovavel (solar + bateria): {renovavel / entregue:.0%}")
    print(f"Geracao solar: {e['solar_gerada']:.2f} kWh  |  guardada na bateria: "
          f"{e['bateria_carga']:.2f} kWh  |  injetada na rede: {e['injetada']:.2f} kWh")

    print("Gerando graficos:")
    for nome, funcao in (("1_origem_energia.png", grafico_fontes),
                         ("2_soc_veiculos.png", grafico_soc_veiculos),
                         ("3_potencia_pontos.png", grafico_potencia_pontos),
                         ("4_bateria.png", grafico_bateria)):
        fig, ax = plt.subplots(figsize=(10, 4.5))
        funcao(ax, df)
        salvar(fig, nome)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    grafico_resumo(ax, e)
    salvar(fig, "5_balanco_energia.png")

    # Painel completo (dashboard) com tudo junto
    fig = plt.figure(figsize=(15, 10))
    grade = fig.add_gridspec(3, 2)
    grafico_fontes(fig.add_subplot(grade[0, :]), df)
    grafico_potencia_pontos(fig.add_subplot(grade[1, 0]), df)
    grafico_soc_veiculos(fig.add_subplot(grade[1, 1]), df)
    grafico_bateria(fig.add_subplot(grade[2, 0]), df)
    grafico_resumo(fig.add_subplot(grade[2, 1]), e)
    fig.suptitle("SolarFlow — Painel de monitoramento (faixa cinza = horário de ponta)",
                 fontsize=14, fontweight="bold")
    salvar(fig, "0_painel.png")
    print("Dados limpos salvos em telemetria.csv")


if __name__ == "__main__":
    main()
