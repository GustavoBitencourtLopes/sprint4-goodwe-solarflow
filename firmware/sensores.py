# SolarFlow - Leitura e conversao dos sensores
# Converte leituras brutas do ADC em grandezas fisicas
# e trata os botoes com interrupcao de timer + debounce.

from machine import ADC, Pin, Timer
import time
import config

ADC_MAX = 65535  # read_u16(): o ADC de 12 bits e escalado para 16 bits


def ler_media(adc, amostras=4):
    """Media de varias leituras: filtro simples contra ruido do ADC."""
    total = 0
    for _ in range(amostras):
        total += adc.read_u16()
    return total / amostras


class SensorSolar:
    """LDR -> tensao -> resistencia -> lux -> irradiancia (W/m2) -> geracao (kW)."""

    def __init__(self, pino):
        self.adc = ADC(pino)
        self.tensao = 0.0
        self.lux = 0.0
        self.irradiancia = 0.0
        self.potencia_kw = 0.0

    def ler(self):
        vcc = config.LDR_VCC
        tensao = ler_media(self.adc) * vcc / ADC_MAX
        # Evita divisao por zero nos extremos (escuro total ou luz maxima)
        tensao = min(max(tensao, 0.001), vcc - 0.001)

        # Divisor de tensao: V = Vcc * R_ldr / (R_ldr + R_fixo)  ->  isolando R_ldr
        resistencia = config.LDR_R_FIXO * tensao / (vcc - tensao)

        # Curva do LDR: R = RL10 * (10 / lux) ^ gamma  ->  isolando o lux
        rl10 = config.LDR_RL10_KOHM * 1000
        lux = (rl10 * 10 ** config.LDR_GAMMA / resistencia) ** (1 / config.LDR_GAMMA)

        self.tensao = tensao
        self.lux = lux
        self.irradiancia = min(lux / config.LUX_POR_WM2, config.IRRADIANCIA_MAX)
        self.potencia_kw = config.PV_POTENCIA_KWP * self.irradiancia / config.IRRADIANCIA_MAX
        return self.potencia_kw


class SensorSOC:
    """Potenciometro -> estado de carga (SOC) do veiculo no momento da conexao."""

    def __init__(self, pino):
        self.adc = ADC(pino)

    def ler(self):
        return round(ler_media(self.adc) * 100 / ADC_MAX, 1)


# ---------------- Botoes: debounce por interrupcao de timer ----------------
# Um timer periodico (interrupcao a cada BOTAO_AMOSTRA_MS) le todos os botoes.
# Uma mudanca so e aceita depois de AMOSTRAS_ESTAVEIS leituras iguais seguidas,
# o que descarta os repiques mecanicos ao apertar E ao soltar o botao.
# A rotina de interrupcao nao aloca memoria (requisito de ISR no MicroPython).

AMOSTRAS_ESTAVEIS = max(1, config.DEBOUNCE_MS // config.BOTAO_AMOSTRA_MS)

_botoes = []
_timer = None


def _isr_timer(timer):
    for i in range(len(_botoes)):
        _botoes[i].amostrar()


class Botao:
    """Botao com pull-up interno (solto = 1, apertado = 0)."""

    def __init__(self, pino):
        global _timer
        self.pin = Pin(pino, Pin.IN, Pin.PULL_UP)
        self._estavel = 1          # ultimo estado confirmado
        self._ultima_leitura = 1   # ultima leitura bruta
        self._contador = 0         # leituras iguais seguidas
        self._pendente = False     # clique aguardando o loop principal
        _botoes.append(self)
        if _timer is None:
            _timer = Timer(period=config.BOTAO_AMOSTRA_MS, mode=Timer.PERIODIC,
                           callback=_isr_timer)

    def amostrar(self):
        """Chamado pela interrupcao do timer."""
        leitura = self.pin.value()
        if leitura != self._ultima_leitura:
            self._ultima_leitura = leitura
            self._contador = 0
        elif self._contador < AMOSTRAS_ESTAVEIS:
            self._contador += 1
            if self._contador == AMOSTRAS_ESTAVEIS and leitura != self._estavel:
                self._estavel = leitura
                if leitura == 0:
                    self._pendente = True

    def foi_pressionado(self):
        """True uma unica vez por clique confirmado."""
        if self._pendente:
            self._pendente = False
            return True
        return False

    def esta_apertado(self):
        return self._estavel == 0
