# SolarFlow - Cenario automatico de demonstracao
# Simula um dia completo sem interacao: perfil solar, chegada e saida
# de veiculos e troca de modo. Torna os resultados reproduziveis.

import math

INICIO_H = 6        # o cenario comeca as 06:00
FIM_H = 24          # e termina a meia-noite

# Perfil solar: dia ensolarado (nascer 06h, por 18h) com nuvens entre 11h30 e 13h
IRRADIANCIA_PICO = 850.0     # W/m2 ao meio-dia
NUVEM_INICIO_H = 11.5
NUVEM_FIM_H = 13.0
FATOR_NUVEM = 0.3            # nuvens deixam passar 30% da irradiancia


def irradiancia(minutos):
    """Irradiancia solar (W/m2) em um minuto do dia."""
    h = minutos / 60
    if h <= 6 or h >= 18:
        return 0.0
    irr = IRRADIANCIA_PICO * math.sin(math.pi * (h - 6) / 12)
    if NUVEM_INICIO_H <= h < NUVEM_FIM_H:
        irr *= FATOR_NUVEM
    return irr


# Agenda do dia: (horario em minutos, acao, ponto, SOC de chegada em %)
EVENTOS = (
    (8 * 60,       "conectar",    "A", 25),    # chega ao trabalho com pouca carga
    (9 * 60 + 30,  "conectar",    "B", 45),
    (11 * 60,      "modo_eco",    None, None), # gestor ativa o modo Eco
    (13 * 60,      "modo_normal", None, None),
    (14 * 60,      "desconectar", "A", None),
    (15 * 60,      "desconectar", "B", None),
    (16 * 60 + 30, "conectar",    "A", 20),    # fim da tarde: novos veiculos
    (17 * 60 + 45, "conectar",    "B", 30),    # chega em pleno horario de ponta
    (21 * 60 + 30, "desconectar", "A", None),
    (22 * 60 + 30, "desconectar", "B", None),
)
