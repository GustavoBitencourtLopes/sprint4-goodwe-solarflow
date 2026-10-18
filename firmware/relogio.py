# SolarFlow - Relogio simulado
# Acelera o tempo (ESCALA_MIN_POR_S) e informa o horario de ponta.

import time
import config

MINUTOS_DIA = 24 * 60


class RelogioSimulado:
    def __init__(self):
        self.minutos = config.HORA_INICIAL * 60.0
        self._ultimo_ms = time.ticks_ms()

    def avancar(self):
        """Avanca o relogio e devolve o intervalo simulado em HORAS (dt)."""
        agora = time.ticks_ms()
        dt_real_s = time.ticks_diff(agora, self._ultimo_ms) / 1000
        self._ultimo_ms = agora
        dt_min = dt_real_s * config.ESCALA_MIN_POR_S
        self.minutos = (self.minutos + dt_min) % MINUTOS_DIA
        return dt_min / 60

    def hora(self):
        return int(self.minutos // 60)

    def texto(self):
        return "{:02d}:{:02d}".format(int(self.minutos // 60), int(self.minutos % 60))

    def ajustar(self, hora):
        """Coloca o relogio em uma hora especifica (usado pelo cenario automatico)."""
        self.minutos = hora * 60.0
        self._ultimo_ms = time.ticks_ms()

    def em_ponta(self):
        return config.PONTA_INICIO_MIN <= self.minutos < config.PONTA_FIM_MIN
