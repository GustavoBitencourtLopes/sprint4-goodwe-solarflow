# SolarFlow - Telemetria em CSV pela serial (USB)
# A cada ciclo imprime uma linha "DADOS,..." com o estado completo da estacao.
# O script analise/graficos.py le essas linhas e gera os graficos.
# Papel equivalente ao do SEMS Portal no ecossistema GoodWe.

import config

COLUNAS = ("t_min,dt_min,hora,modo,ponta,solar_kw,solar_veic_kw,bat_veic_kw,"
           "rede_veic_kw,bat_carga_kw,injetada_kw,bat_soc,"
           "a_estado,a_soc,a_kw,b_estado,b_soc,b_kw")

_FORMATO = ("DADOS,{:.2f},{:.3f},{},{},{},{:.3f},{:.3f},{:.3f},{:.3f},{:.3f},{:.3f},"
            "{:.2f},{},{:.2f},{:.3f},{},{:.2f},{:.3f}")


def cabecalho():
    if config.TELEMETRIA_ATIVA:
        print("COLUNAS," + COLUNAS)


def linha(t_min, dt_min, hora, modo_eco, ponta, fluxo, bat_soc, pontos):
    if not config.TELEMETRIA_ATIVA:
        return
    a = pontos["A"]
    b = pontos["B"]
    print(_FORMATO.format(
        t_min, dt_min, hora, "ECO" if modo_eco else "NORMAL", 1 if ponta else 0,
        fluxo["solar"], fluxo["solar_veiculos"], fluxo["bateria_veiculos"],
        fluxo["rede_veiculos"], fluxo["bateria_carga"], fluxo["injetada"], bat_soc,
        a.estado, a.soc, a.potencia_kw, b.estado, b.soc, b.potencia_kw))
