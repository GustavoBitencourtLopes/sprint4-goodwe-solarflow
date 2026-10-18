# SolarFlow - Estacao Inteligente de Recarga GoodWe
# Loop principal: botoes ou cenario automatico, gestor de energia, algoritmo
# de divisao, maquina de estados, atuadores, display, alertas e telemetria.

import time
import micropython
import config
from sensores import SensorSolar, SensorSOC, Botao
from relogio import RelogioSimulado
from ponto_recarga import PontoRecarga, AGUARDANDO, DISPONIVEL
from energia import GestorEnergia
from algoritmo import dividir_proporcional
from atuadores import (SaidaPonto, IndicadorOrigem, Buzzer, piscar,
                       SOM_CONECTAR, SOM_DESCONECTAR, SOM_COMPLETO,
                       SOM_MODO, SOM_EMERGENCIA, SOM_RESET)
from display import Painel
import telemetria
import cenario

SOM_ALERTA = ((1500, 60), (0, 60), (1500, 60))

# Ctrl+C no Serial Monitor nao interrompe a estacao (permite copiar os dados com seguranca)
micropython.kbd_intr(-1)

# ================= Inicializacao =================
solar = SensorSolar(config.PIN_LDR)
sensor_soc = {"A": SensorSOC(config.PIN_POT_A), "B": SensorSOC(config.PIN_POT_B)}

btn_emergencia = Botao(config.PIN_BTN_EMERG)
btn_modo = Botao(config.PIN_BTN_MODO)
btn_ponto = {"A": Botao(config.PIN_BTN_A), "B": Botao(config.PIN_BTN_B)}

pontos = {"A": PontoRecarga("A"), "B": PontoRecarga("B")}
saidas = {
    "A": SaidaPonto(config.PIN_LED_A, config.PIN_RELE_A),
    "B": SaidaPonto(config.PIN_LED_B, config.PIN_RELE_B),
}
origem = IndicadorOrigem()
buzzer = Buzzer(config.PIN_BUZZER)
relogio = RelogioSimulado()
painel = Painel()
gestor = GestorEnergia()

modo_eco = False
emergencia = False
atualizar_agora = False      # forca o redesenho imediato apos um clique
fluxo = gestor.fluxo
tempo_sim_min = 0.0          # tempo simulado desde o inicio (para a telemetria)
solar_kw = 0.0

# Cenario automatico: relogio comeca no inicio do cenario e segue a agenda
automatico = config.CENARIO_AUTOMATICO
cenario_concluido = False
proximo_evento = 0
if automatico:
    relogio.ajustar(cenario.INICIO_H)
DURACAO_CENARIO_MIN = (cenario.FIM_H - cenario.INICIO_H) * 60

# Memoria dos alertas (para avisar so na mudanca, e nao a cada ciclo)
ponta_anterior = relogio.em_ponta()
alerta_bateria_limite = False
alerta_bateria_cheia = False
alerta_injetando = False


def log(mensagem):
    print("[{}] {}".format(relogio.texto(), mensagem))


def limites_do_momento(ponta):
    """Regras de operacao conforme o modo e o horario.

    Retorna (limite da rede em kW, SOC minimo permitido da bateria).
    - Eco:            sem rede; bateria pode ir ate o minimo de protecao
    - Normal, ponta:  rede limitada; bateria pode ir ate o minimo de protecao
    - Normal, fora:   rede liberada; bateria guarda reserva para a ponta
    """
    if modo_eco:
        return 0.0, config.BAT_SOC_MIN
    if ponta:
        return config.REDE_LIMITE_PONTA_KW, config.BAT_SOC_MIN
    return config.REDE_LIMITE_KW, config.BAT_RESERVA_FORA_PONTA


def definir_modo(eco):
    global modo_eco, atualizar_agora
    if eco == modo_eco:
        return
    modo_eco = eco
    atualizar_agora = True
    buzzer.tocar(*SOM_MODO)
    if modo_eco:
        log("Modo ECO - recarga somente com energia renovavel (sol + bateria)")
    else:
        log("Modo NORMAL - sol, bateria e rede")


def acionar_ponto(nome, soc):
    """Mesmo efeito do botao do ponto: conecta (se livre) ou desconecta."""
    global atualizar_agora
    atualizar_agora = True
    p = pontos[nome]
    evento = p.botao(soc)
    if evento == "conectado":
        buzzer.tocar(*SOM_CONECTAR)
        log("Ponto {}: veiculo conectado (SOC {:.0f}%)".format(nome, p.soc))
    elif evento == "ja_completo":
        buzzer.tocar(*SOM_COMPLETO)
        log("Ponto {}: veiculo ja esta acima do alvo (SOC {:.0f}%)".format(nome, p.soc))
    elif evento == "desconectado":
        buzzer.tocar(*SOM_DESCONECTAR)
        log("Ponto {}: veiculo desconectado ({:.2f} kWh entregues)".format(
            nome, p.energia_sessao_kwh))


def executar_agenda():
    """Executa os eventos do cenario automatico que ja chegaram na hora."""
    global proximo_evento
    agora_min = cenario.INICIO_H * 60 + tempo_sim_min
    while proximo_evento < len(cenario.EVENTOS) and agora_min >= cenario.EVENTOS[proximo_evento][0]:
        _, acao, nome, soc = cenario.EVENTOS[proximo_evento]
        proximo_evento += 1
        if emergencia:
            continue
        if acao == "conectar" and pontos[nome].estado == DISPONIVEL:
            acionar_ponto(nome, soc)
        elif acao == "desconectar" and pontos[nome].estado != DISPONIVEL:
            acionar_ponto(nome, 0)
        elif acao == "modo_eco":
            definir_modo(True)
        elif acao == "modo_normal":
            definir_modo(False)


if automatico:
    log("SolarFlow iniciado - CENARIO AUTOMATICO (dia completo, {:02d}h as {:02d}h)".format(
        cenario.INICIO_H, cenario.FIM_H))
else:
    log("SolarFlow iniciado - modo manual")
telemetria.cabecalho()
ultimo_ciclo = time.ticks_ms()

# ================= Loop principal =================
while True:
    # ---- 1. Botoes (verificados a cada 20 ms) ----
    if btn_emergencia.foi_pressionado():
        atualizar_agora = True
        emergencia = not emergencia
        if emergencia:
            for p in pontos.values():
                p.entrar_emergencia()
            buzzer.tocar(*SOM_EMERGENCIA)
            log("EMERGENCIA ACIONADA - recarga interrompida nos dois pontos")
        else:
            for p in pontos.values():
                p.resetar()
            buzzer.tocar(*SOM_RESET)
            log("Emergencia resetada - reconecte os veiculos")

    # No cenario automatico, MODO e os botoes dos pontos ficam com a agenda
    if btn_modo.foi_pressionado() and not emergencia and not automatico:
        definir_modo(not modo_eco)

    for nome, botao in btn_ponto.items():
        if botao.foi_pressionado() and not emergencia and not automatico:
            acionar_ponto(nome, sensor_soc[nome].ler())

    # ---- 2. Ciclo da simulacao (a cada CICLO_MS) ----
    agora = time.ticks_ms()
    if atualizar_agora or time.ticks_diff(agora, ultimo_ciclo) >= config.CICLO_MS:
        atualizar_agora = False
        ultimo_ciclo = agora
        dt_h = relogio.avancar()
        tempo_sim_min += dt_h * 60
        ponta = relogio.em_ponta()

        # Fonte da geracao solar: perfil do cenario ou sensor LDR
        if automatico:
            if not cenario_concluido:
                executar_agenda()
            irradiancia = cenario.irradiancia(cenario.INICIO_H * 60 + tempo_sim_min)
            solar_kw = config.PV_POTENCIA_KWP * irradiancia / config.IRRADIANCIA_MAX
        else:
            solar_kw = solar.ler()

        # Alerta: inicio e fim do horario de ponta
        if ponta != ponta_anterior:
            ponta_anterior = ponta
            buzzer.tocar(*SOM_ALERTA)
            if ponta:
                log("Inicio do horario de ponta - rede limitada a {:.0f} kW".format(
                    config.REDE_LIMITE_PONTA_KW))
            else:
                log("Fim do horario de ponta - rede liberada")

        # 2.1 Regras do momento e demanda de cada ponto
        rede_limite, bat_soc_min = limites_do_momento(ponta)
        demandas = {}
        for nome, p in pontos.items():
            demandas[nome] = p.demanda_kw(dt_h)
        demanda_total = sum(demandas.values())

        # 2.2 Gestor de energia: solar -> bateria -> rede (e excedente)
        fluxo = gestor.balancear(demanda_total, solar_kw, rede_limite, bat_soc_min, dt_h)

        # 2.3 Divisao proporcional com prioridade pela menor bateria
        pedidos = {}
        for nome, p in pontos.items():
            pedidos[nome] = (p.falta_kwh(), demandas[nome])
        alocacao = dividir_proporcional(fluxo["para_veiculos"], pedidos)

        # 2.4 Aplica a potencia em cada ponto
        for nome, p in pontos.items():
            estado_anterior = p.estado
            if p.atualizar(alocacao[nome], dt_h) == "completo":
                buzzer.tocar(*SOM_COMPLETO)
                log("Ponto {}: recarga completa (SOC {:.0f}%, {:.2f} kWh entregues)".format(
                    nome, p.soc, p.energia_sessao_kwh))
            elif p.estado == AGUARDANDO and estado_anterior != AGUARDANDO:
                log("Ponto {}: aguardando energia disponivel".format(nome))

        # 2.5 Alertas da bateria estacionaria
        bat = gestor.bateria
        no_limite = demanda_total > 0 and bat.soc <= bat_soc_min + 0.1
        if no_limite and not alerta_bateria_limite:
            if bat_soc_min == config.BAT_RESERVA_FORA_PONTA:
                log("Bateria em {:.0f}% - reserva guardada para o horario de ponta".format(bat_soc_min))
            else:
                log("Bateria em {:.0f}% - limite de protecao atingido".format(bat_soc_min))
        alerta_bateria_limite = no_limite

        cheia = bat.soc >= config.BAT_SOC_MAX - 0.1
        if cheia and not alerta_bateria_cheia:
            log("Bateria estacionaria cheia ({:.0f}%)".format(bat.soc))
        alerta_bateria_cheia = cheia

        injetando = fluxo["injetada"] > 0.01
        if injetando and not alerta_injetando:
            if cheia:
                motivo = "bateria cheia"
            else:
                motivo = "bateria no limite de carga de {:.0f} kW".format(config.BAT_POTENCIA_MAX_KW)
            log("Excedente solar injetado na rede ({})".format(motivo))
        alerta_injetando = injetando

        painel.desenhar(relogio.texto(), ponta, modo_eco, solar_kw,
                        bat.soc, pontos, fluxo, emergencia)

        # 2.6 Telemetria: uma linha de dados por ciclo (para os graficos)
        if not cenario_concluido:
            telemetria.linha(tempo_sim_min, dt_h * 60, relogio.texto(), modo_eco, ponta,
                             fluxo, bat.soc, pontos)

        # 2.7 Fim do cenario automatico: para a telemetria para facilitar a copia
        if automatico and not cenario_concluido and tempo_sim_min >= DURACAO_CENARIO_MIN:
            cenario_concluido = True
            buzzer.tocar(*SOM_COMPLETO)
            log("CENARIO CONCLUIDO - pause a simulacao e copie o Serial Monitor")

    # ---- 3. Saidas (a cada 20 ms, para os LEDs piscarem) ----
    for nome, saida in saidas.items():
        saida.aplicar(pontos[nome].estado)

    if emergencia:
        origem.aplicar(False, False, piscar(250))   # LED vermelho piscando
    else:
        # LEDs das fontes ativas: geracao solar, bateria descarregando, rede importando
        origem.aplicar(fluxo["solar"] > 0.01,
                       fluxo["bateria_veiculos"] > 0.01,
                       fluxo["rede_veiculos"] > 0.01)

    buzzer.atualizar()
    time.sleep_ms(20)
