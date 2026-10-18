"""SolarFlow - Resultados quantitativos.

Le a telemetria (telemetria.txt), gera os graficos (graficos.py) e calcula:
  - origem da energia entregue aos veiculos e participacao renovavel
  - aproveitamento da geracao solar
  - custo e emissoes de CO2 comparados com uma estacao convencional
  - pico de demanda da rede no horario de ponta
  - sessoes de recarga (SOC de chegada e de saida)

Como usar:  python resultados.py
Saidas: graficos/ (imagens), resultados.md (tabelas para o README) e telemetria.csv
"""

import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import graficos

# ---------------- Premissas (fontes no README) ----------------
# Tarifas de referencia Enel SP, sem impostos (R$/kWh)
TARIFA_CONVENCIONAL = 0.594
TARIFA_BRANCA = {"ponta": 1.115, "intermediario": 0.724, "fora_ponta": 0.499}
# Postos tarifarios da Enel SP (minutos do dia)
PONTA = (17 * 60 + 30, 20 * 60 + 30)                          # 17:30 - 20:30
INTERMEDIARIO = ((16 * 60 + 30, 17 * 60 + 30), (20 * 60 + 30, 21 * 60 + 30))
# Fator medio de emissao do Sistema Interligado Nacional, 2023 (MCTI)
FATOR_CO2_KG_KWH = 0.0385
# Parametros da estacao (iguais ao config.py)
POTENCIA_PONTO_KW = 7.0
CAPACIDADE_VEICULO_KWH = 50.0
DIAS_UTEIS_ANO = 250
ESTADOS_ATIVOS = ("CONECTADO", "CARREGANDO", "AGUARDANDO")


def posto_tarifario(minuto_dia):
    if PONTA[0] <= minuto_dia < PONTA[1]:
        return "ponta"
    for inicio, fim in INTERMEDIARIO:
        if inicio <= minuto_dia < fim:
            return "intermediario"
    return "fora_ponta"


def ler_sessoes(caminho):
    """Le os logs de conexao/desconexao e monta as sessoes de recarga."""
    abertas, sessoes = {}, []
    texto = caminho.read_text(encoding="utf-8", errors="ignore")
    padrao = re.compile(r"\[(\d\d:\d\d)\] Ponto (\w): veiculo (conectado|desconectado) \((?:SOC )?([\d.]+)")
    blocos = texto.split("COLUNAS,")                # usa so a execucao mais recente
    ultimo = blocos[-2] + blocos[-1] if len(blocos) > 1 else texto
    for hora, ponto, evento, valor in padrao.findall(ultimo):
        if evento == "conectado":
            abertas[ponto] = (hora, float(valor))
        elif ponto in abertas:
            chegada, soc_inicial = abertas.pop(ponto)
            energia = float(valor)
            soc_final = soc_inicial + energia / CAPACIDADE_VEICULO_KWH * 100
            sessoes.append((ponto, chegada, soc_inicial, hora, soc_final, energia))
    return sessoes


def calcular(df):
    horas = df["dt_min"] / 60
    # A coluna "ponta" registra a regra que a propria estacao aplicou em cada ciclo
    minuto_dia = (df["hora_dec"] * 60) % (24 * 60)
    df["posto"] = [
        "ponta" if ponta else ("intermediario" if posto_tarifario(m) == "intermediario" else "fora_ponta")
        for ponta, m in zip(df["ponta"], minuto_dia)
    ]
    df["tarifa_branca"] = df["posto"].map(TARIFA_BRANCA)
    df["e_veiculos"] = (df["solar_veic_kw"] + df["bat_veic_kw"] + df["rede_veic_kw"]) * horas
    df["e_rede"] = df["rede_veic_kw"] * horas

    e_veiculos = df["e_veiculos"].sum()
    e_rede = df["e_rede"].sum()
    na_ponta = df["posto"] == "ponta"
    ativos = df["a_estado"].isin(ESTADOS_ATIVOS).astype(int) + df["b_estado"].isin(ESTADOS_ATIVOS).astype(int)

    return {
        "e_veiculos": e_veiculos,
        "e_rede": e_rede,
        "e_veiculos_ponta": df.loc[na_ponta, "e_veiculos"].sum(),
        "e_rede_ponta": df.loc[na_ponta, "e_rede"].sum(),
        # Estacao convencional: mesma energia entregue, toda vinda da rede
        "custo_conv_convencional": e_veiculos * TARIFA_CONVENCIONAL,
        "custo_conv_branca": (df["e_veiculos"] * df["tarifa_branca"]).sum(),
        # SolarFlow: so a energia importada da rede tem custo
        "custo_sf_convencional": e_rede * TARIFA_CONVENCIONAL,
        "custo_sf_branca": (df["e_rede"] * df["tarifa_branca"]).sum(),
        "co2_conv": e_veiculos * FATOR_CO2_KG_KWH,
        "co2_sf": e_rede * FATOR_CO2_KG_KWH,
        # Pico na ponta: convencional entrega a potencia maxima a cada veiculo ativo
        "pico_ponta_conv": (ativos[na_ponta] * POTENCIA_PONTO_KW).max() if na_ponta.any() else 0.0,
        "pico_ponta_sf": df.loc[na_ponta, "rede_veic_kw"].max() if na_ponta.any() else 0.0,
    }


def br(valor, casas=2):
    """Numero no formato brasileiro: 5932.54 -> 5.932,54"""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(parte, total):
    return parte / total * 100 if total else 0.0


def grafico_comparacao(r):
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, 4.8))
    cinza, verde = "#7F8C8D", graficos.COR_INJETADA

    def rotular(ax, barras, fmt):
        for barra in barras:
            v = barra.get_height()
            ax.annotate(fmt(v), (barra.get_x() + barra.get_width() / 2, v), ha="center",
                        va="bottom", fontsize=9, xytext=(0, 3), textcoords="offset points")

    # Custo: as duas estacoes nas duas modalidades tarifarias
    x = [0, 1]
    largura = 0.38
    b1 = ax1.bar([i - largura / 2 for i in x], [r["custo_conv_convencional"], r["custo_conv_branca"]],
                 largura, color=cinza, label="Convencional")
    b2 = ax1.bar([i + largura / 2 for i in x], [r["custo_sf_convencional"], r["custo_sf_branca"]],
                 largura, color=verde, label="SolarFlow")
    rotular(ax1, list(b1) + list(b2), lambda v: "R$ " + br(v))
    ax1.set_xticks(x, ["Tarifa convencional", "Tarifa branca"])
    ax1.set_title("Custo de energia no dia", fontsize=11, fontweight="bold")
    ax1.set_ylabel("R$ (sem impostos)")
    ax1.set_ylim(0, max(r["custo_conv_convencional"], r["custo_conv_branca"]) * 1.25)
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3, axis="y")

    for ax, valores, titulo, unidade, fmt in (
        (ax2, [r["co2_conv"], r["co2_sf"]], "Emissões de CO₂ no dia", "kg CO₂",
         lambda v: br(v) + " kg"),
        (ax3, [r["pico_ponta_conv"], r["pico_ponta_sf"]], "Pico de demanda da rede na ponta", "kW",
         lambda v: br(v, 1) + " kW"),
    ):
        b = ax.bar(["Convencional", "SolarFlow"], valores, color=[cinza, verde])
        rotular(ax, b, fmt)
        ax.set_title(titulo, fontsize=11, fontweight="bold")
        ax.set_ylabel(unidade)
        ax.set_ylim(0, max(valores + [0.01]) * 1.25)
        ax.grid(alpha=0.3, axis="y")

    fig.suptitle("SolarFlow x estação convencional (mesma energia entregue aos veículos)",
                 fontsize=13, fontweight="bold")
    graficos.salvar(fig, "6_comparacao.png")


def main():
    graficos.main()                                   # graficos 0 a 5 e telemetria.csv
    df = graficos.ler_telemetria(graficos.ARQUIVO_ENTRADA)
    e = graficos.calcular_energias(df)
    r = calcular(df)
    sessoes = ler_sessoes(graficos.ARQUIVO_ENTRADA)
    grafico_comparacao(r)

    entregue = r["e_veiculos"]
    renovavel = e["solar_veiculos"] + e["bateria_veiculos"]
    aproveitamento = e["solar_veiculos"] + e["bateria_carga"]
    eco_conv = r["custo_conv_convencional"] - r["custo_sf_convencional"]
    eco_branca = r["custo_conv_branca"] - r["custo_sf_branca"]
    co2_evitado = r["co2_conv"] - r["co2_sf"]
    melhor_conv = min(r["custo_conv_convencional"], r["custo_conv_branca"])
    melhor_sf = min(r["custo_sf_convencional"], r["custo_sf_branca"])
    tarifa_sf = "convencional" if r["custo_sf_convencional"] <= r["custo_sf_branca"] else "branca"

    linhas = [
        "## Resultados quantitativos (cenário automático de um dia)",
        "",
        f"Período simulado: {df['hora'].iloc[0]} a {df['hora'].iloc[-1]} "
        f"({br(df['dt_min'].sum() / 60, 1)} h), {len(df)} registros de telemetria.",
        "",
        "### Origem da energia entregue aos veículos",
        "",
        "| Fonte | Energia (kWh) | Participação |",
        "|---|---|---|",
        f"| Solar direto | {br(e['solar_veiculos'])} | {br(pct(e['solar_veiculos'], entregue), 1)}% |",
        f"| Bateria (carregada pelo sol) | {br(e['bateria_veiculos'])} | {br(pct(e['bateria_veiculos'], entregue), 1)}% |",
        f"| Rede elétrica | {br(e['rede_veiculos'])} | {br(pct(e['rede_veiculos'], entregue), 1)}% |",
        f"| **Total** | **{br(entregue)}** | **{br(pct(renovavel, entregue), 1)}% de energia renovável local** |",
        "",
        "### Aproveitamento da geração solar",
        "",
        "| Indicador | Valor |",
        "|---|---|",
        f"| Geração solar total | {br(e['solar_gerada'])} kWh |",
        f"| Usada nos veículos ou guardada na bateria | {br(aproveitamento)} kWh "
        f"({br(pct(aproveitamento, e['solar_gerada']), 1)}%) |",
        f"| Excedente injetado na rede | {br(e['injetada'])} kWh "
        f"({br(pct(e['injetada'], e['solar_gerada']), 1)}%) |",
        "",
        "### Comparação com uma estação convencional (100% rede, mesma energia entregue)",
        "",
        "| Estação | Energia comprada da rede (kWh) | Custo, tarifa convencional (R$) | Custo, tarifa branca (R$) | CO₂ (kg) |",
        "|---|---|---|---|---|",
        f"| Convencional | {br(entregue)} | {br(r['custo_conv_convencional'])} | {br(r['custo_conv_branca'])} | {br(r['co2_conv'])} |",
        f"| SolarFlow | {br(r['e_rede'])} | {br(r['custo_sf_convencional'])} | {br(r['custo_sf_branca'])} | {br(r['co2_sf'])} |",
        "",
        "| Ganho do SolarFlow | Valor |",
        "|---|---|",
        f"| Redução da energia comprada da rede | {br(entregue - r['e_rede'])} kWh "
        f"({br(pct(entregue - r['e_rede'], entregue), 1)}%) |",
        f"| Economia no dia, tarifa convencional | R$ {br(eco_conv)} ({br(pct(eco_conv, r['custo_conv_convencional']), 1)}%) |",
        f"| Economia no dia, tarifa branca | R$ {br(eco_branca)} ({br(pct(eco_branca, r['custo_conv_branca']), 1)}%) |",
        f"| Economia projetada no ano, tarifa convencional ({DIAS_UTEIS_ANO} dias úteis) | R$ {br(eco_conv * DIAS_UTEIS_ANO)} |",
        f"| CO₂ evitado no dia | {br(co2_evitado)} kg |",
        f"| CO₂ evitado projetado no ano ({DIAS_UTEIS_ANO} dias úteis) | {br(co2_evitado * DIAS_UTEIS_ANO, 0)} kg |",
        f"| Pico de demanda da rede no horário de ponta | {br(r['pico_ponta_conv'], 1)} kW → {br(r['pico_ponta_sf'], 1)} kW "
        f"({br(pct(r['pico_ponta_conv'] - r['pico_ponta_sf'], r['pico_ponta_conv']), 0)}% menor) |",
        f"| Energia da rede consumida no horário de ponta | {br(r['e_veiculos_ponta'])} kWh → {br(r['e_rede_ponta'])} kWh |",
        "",
        f"Modalidade tarifária mais vantajosa para o SolarFlow neste perfil de uso: **tarifa {tarifa_sf}** "
        f"(R$ {br(melhor_sf)} contra R$ {br(melhor_conv)} da melhor opção da estação convencional).",
        "",
        "### Sessões de recarga",
        "",
        "| Ponto | Chegada | SOC na chegada | Saída | SOC na saída | Energia (kWh) |",
        "|---|---|---|---|---|---|",
    ]
    for ponto, chegada, soc_i, saida, soc_f, energia in sessoes:
        linhas.append(f"| {ponto} | {chegada} | {soc_i:.0f}% | {saida} | {soc_f:.0f}% | {br(energia)} |")
    linhas += [
        "",
        "Premissas: tarifas de referência da Enel SP sem impostos (convencional R$ 0,594/kWh; "
        "tarifa branca R$ 1,115 na ponta, R$ 0,724 no intermediário e R$ 0,499 fora da ponta); "
        "horário de ponta da Enel SP das 17h30 às 20h30; fator médio de emissão do SIN de "
        "0,0385 kg CO₂/kWh (MCTI, 2023); dia útil; a estação convencional entrega a mesma "
        "energia nos mesmos horários, comprando tudo da rede.",
    ]
    texto = "\n".join(linhas)
    (graficos.PASTA / "resultados.md").write_text(texto, encoding="utf-8")

    print()
    print("=" * 60)
    print(texto)
    print("=" * 60)
    print("Tabelas salvas em resultados.md | grafico salvo em graficos/6_comparacao.png")


if __name__ == "__main__":
    main()
