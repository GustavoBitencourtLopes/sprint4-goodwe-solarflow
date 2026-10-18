"""SolarFlow - Bancada de testes das estrategias.

Roda o mesmo dia do cenario automatico, usando OS MESMOS MODULOS DO FIRMWARE
(energia.py, algoritmo.py, ponto_recarga.py, cenario.py e config.py), e mede o
efeito de cada decisao do projeto:
  Teste 1 - dia completo: SolarFlow x variacoes x estacao convencional
  Teste 2 - prioridade pela menor bateria (veiculos chegam e saem juntos)
  Teste 3 - reserva da bateria para o horario de ponta

Como usar (na pasta analise/):  python bancada.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "firmware"))

import config                                    # noqa: E402
import cenario                                   # noqa: E402
from algoritmo import dividir_proporcional        # noqa: E402
from energia import GestorEnergia                 # noqa: E402
from ponto_recarga import PontoRecarga, DISPONIVEL  # noqa: E402

DT_MIN = 2.5                                     # mesmo passo do firmware (0,5 s x 5 min/s)
TARIFA_CONVENCIONAL = 0.594
TARIFA_BRANCA = {"ponta": 1.115, "intermediario": 0.724, "fora_ponta": 0.499}
INTERMEDIARIO = ((16 * 60 + 30, 17 * 60 + 30), (20 * 60 + 30, 21 * 60 + 30))
FATOR_CO2 = 0.0385


def posto(minuto, ponta):
    if ponta:
        return "ponta"
    for inicio, fim in INTERMEDIARIO:
        if inicio <= minuto < fim:
            return "intermediario"
    return "fora_ponta"


def sem_sol(_minuto):
    return 0.0


def simular(divisao="proporcional", reserva=True, convencional=False, eventos=cenario.EVENTOS,
            inicio_h=cenario.INICIO_H, fim_h=cenario.FIM_H, irradiancia=cenario.irradiancia,
            bat_inicial=None):
    gestor = GestorEnergia()
    if bat_inicial is not None:
        gestor.bateria.soc = bat_inicial
    if convencional:
        gestor.bateria.soc = 0.0
    pontos = {"A": PontoRecarga("A"), "B": PontoRecarga("B")}
    modo_eco = False
    dt_h = DT_MIN / 60
    minuto = inicio_h * 60
    evento = 0
    chegada = {}
    sessoes = []
    m = {"rede": 0.0, "rede_ponta": 0.0, "pico_ponta": 0.0, "custo_conv": 0.0, "custo_branca": 0.0,
         "solar_veic": 0.0, "bat_veic": 0.0, "entregue_ponta": 0.0}

    while minuto < fim_h * 60:
        minuto += DT_MIN
        # Agenda do cenario
        while evento < len(eventos) and minuto >= eventos[evento][0]:
            _, acao, nome, soc = eventos[evento]
            evento += 1
            if acao == "conectar" and pontos[nome].estado == DISPONIVEL:
                pontos[nome].botao(soc)
                chegada[nome] = soc
            elif acao == "desconectar" and pontos[nome].estado != DISPONIVEL:
                sessoes.append((nome, chegada.pop(nome), pontos[nome].soc))
                pontos[nome].botao(0)
            elif acao in ("modo_eco", "modo_normal") and not convencional:
                modo_eco = acao == "modo_eco"

        ponta = config.PONTA_INICIO_MIN <= minuto % 1440 < config.PONTA_FIM_MIN
        if convencional:
            solar_kw, rede_limite, bat_min = 0.0, 99.0, 100.0
        else:
            solar_kw = config.PV_POTENCIA_KWP * irradiancia(minuto) / config.IRRADIANCIA_MAX
            if modo_eco:
                rede_limite, bat_min = 0.0, config.BAT_SOC_MIN
            elif ponta:
                rede_limite, bat_min = config.REDE_LIMITE_PONTA_KW, config.BAT_SOC_MIN
            else:
                rede_limite = config.REDE_LIMITE_KW
                bat_min = config.BAT_RESERVA_FORA_PONTA if reserva else config.BAT_SOC_MIN

        demandas = {n: p.demanda_kw(dt_h) for n, p in pontos.items()}
        fluxo = gestor.balancear(sum(demandas.values()), solar_kw, rede_limite, bat_min, dt_h)
        if divisao == "proporcional":
            pedidos = {n: (p.falta_kwh(), demandas[n]) for n, p in pontos.items()}
        else:  # peso igual para todos que precisam de energia
            pedidos = {n: (1.0 if p.falta_kwh() > 0 else 0.0, demandas[n]) for n, p in pontos.items()}
        alocacao = dividir_proporcional(fluxo["para_veiculos"], pedidos)
        for n, p in pontos.items():
            p.atualizar(alocacao[n], dt_h)

        e_rede = fluxo["rede_veiculos"] * dt_h
        m["rede"] += e_rede
        m["solar_veic"] += fluxo["solar_veiculos"] * dt_h
        m["bat_veic"] += fluxo["bateria_veiculos"] * dt_h
        m["custo_conv"] += e_rede * TARIFA_CONVENCIONAL
        m["custo_branca"] += e_rede * TARIFA_BRANCA[posto(minuto % 1440, ponta)]
        if ponta:
            m["rede_ponta"] += e_rede
            m["pico_ponta"] = max(m["pico_ponta"], fluxo["rede_veiculos"])
            m["entregue_ponta"] += fluxo["para_veiculos"] * dt_h

    m["sessoes"] = sessoes
    m["entregue"] = m["rede"] + m["solar_veic"] + m["bat_veic"]
    return m


def br(v, casas=2):
    t = f"{v:,.{casas}f}"
    return t.replace(",", "X").replace(".", ",").replace("X", ".")


def tabela_dia(resultados):
    linhas = [
        "### Teste 1: dia completo (cenário automático)",
        "",
        "| Estratégia | Energia entregue (kWh) | Comprada da rede (kWh) | Rede na ponta (kWh) | Pico na ponta (kW) "
        "| Custo, tarifa convencional (R$) | CO₂ (kg) | SOC na saída (A, B, A, B) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for nome, m in resultados:
        socs = ", ".join(f"{s[2]:.0f}%" for s in m["sessoes"])
        linhas.append(
            f"| {nome} | {br(m['entregue'])} | {br(m['rede'])} | {br(m['rede_ponta'])} | {br(m['pico_ponta'], 1)} "
            f"| {br(m['custo_conv'])} | {br(m['rede'] * FATOR_CO2)} | {socs} |")
    return linhas


def main():
    # ---------- Teste 1: dia completo ----------
    estrategias = (
        ("SolarFlow completo", dict()),
        ("Divisão igual (sem prioridade)", dict(divisao="igual")),
        ("Sem reserva para a ponta", dict(reserva=False)),
        ("Estação convencional", dict(convencional=True)),
    )
    linhas = tabela_dia([(nome, simular(**kw)) for nome, kw in estrategias])

    # ---------- Teste 2: prioridade pela menor bateria ----------
    # Dois veiculos chegam e saem juntos, com SOC muito diferentes e energia limitada (noite)
    agenda = ((21 * 60 + 30, "conectar", "A", 20), (21 * 60 + 30, "conectar", "B", 60),
              (23 * 60 + 30, "desconectar", "A", None), (23 * 60 + 30, "desconectar", "B", None))
    comum = dict(eventos=agenda, inicio_h=21.5, fim_h=24, irradiancia=sem_sol, bat_inicial=20.0)
    prop = simular(**comum)
    igual = simular(divisao="igual", **comum)
    linhas += [
        "",
        "### Teste 2: prioridade pela menor bateria",
        "",
        "Dois veículos chegam juntos às 21h30 (A com 20%, B com 60%) e saem juntos às 23h30, "
        "com 10 kW disponíveis da rede e bateria estacionária vazia.",
        "",
        "| Divisão | SOC de A na saída | SOC de B na saída | Menor SOC na saída |",
        "|---|---|---|---|",
    ]
    for nome, m in (("Proporcional (SolarFlow)", prop), ("Igual", igual)):
        soc = {s[0]: s[2] for s in m["sessoes"]}
        linhas.append(f"| {nome} | {soc['A']:.0f}% | {soc['B']:.0f}% | {min(soc.values()):.0f}% |")

    # ---------- Teste 3: reserva da bateria para a ponta ----------
    # Um veiculo carrega a tarde; outro chega no inicio da ponta, ja sem sol
    agenda = ((15 * 60 + 30, "conectar", "A", 30), (17 * 60 + 30, "desconectar", "A", None),
              (17 * 60 + 30, "conectar", "B", 30), (20 * 60 + 30, "desconectar", "B", None))
    comum = dict(eventos=agenda, inicio_h=15, fim_h=20.5, bat_inicial=100.0)
    com = simular(**comum)
    sem = simular(reserva=False, **comum)
    linhas += [
        "",
        "### Teste 3: reserva da bateria para o horário de ponta",
        "",
        "Bateria cheia às 15h. O veículo A carrega das 15h30 às 17h30, e o veículo B chega às 17h30, "
        "início da ponta, e sai às 20h30.",
        "",
        "| Estratégia | Energia entregue a B na ponta (kWh) | SOC de B na saída | Rede na ponta (kWh) |",
        "|---|---|---|---|",
    ]
    for nome, m in (("Com reserva (SolarFlow)", com), ("Sem reserva", sem)):
        soc_b = [s[2] for s in m["sessoes"] if s[0] == "B"][0]
        linhas.append(f"| {nome} | {br(m['entregue_ponta'])} | {soc_b:.0f}% | {br(m['rede_ponta'])} |")

    texto = "\n".join(linhas)
    (Path(__file__).resolve().parent / "bancada.md").write_text(texto, encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()
