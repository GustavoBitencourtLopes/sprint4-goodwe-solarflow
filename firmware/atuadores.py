# SolarFlow - Atuadores: reles (contatores), LEDs e buzzer

from machine import Pin, PWM
import time
import config
from ponto_recarga import CARREGANDO, AGUARDANDO, COMPLETO


def piscar(periodo_ms):
    """Alterna entre 1 e 0 a cada periodo_ms (usado nos LEDs piscantes)."""
    return (time.ticks_ms() // periodo_ms) % 2


class SaidaPonto:
    """LED de status e rele (contator) de um ponto de recarga.

    LED aceso       = carregando
    LED pisca rapido = aguardando energia
    LED pisca lento  = recarga completa
    LED apagado      = livre, conectado ou emergencia
    """

    def __init__(self, pino_led, pino_rele):
        self.led = Pin(pino_led, Pin.OUT, value=0)
        self.rele = Pin(pino_rele, Pin.OUT, value=0)

    def aplicar(self, estado):
        # O contator so fecha quando o ponto esta efetivamente carregando
        self.rele.value(1 if estado == CARREGANDO else 0)
        if estado == CARREGANDO:
            self.led.value(1)
        elif estado == AGUARDANDO:
            self.led.value(piscar(150))
        elif estado == COMPLETO:
            self.led.value(piscar(600))
        else:
            self.led.value(0)


class IndicadorOrigem:
    """LEDs que mostram de onde vem a energia: sol, bateria e rede."""

    def __init__(self):
        self.sol = Pin(config.PIN_LED_SOL, Pin.OUT, value=0)
        self.bateria = Pin(config.PIN_LED_BAT, Pin.OUT, value=0)
        self.rede = Pin(config.PIN_LED_REDE, Pin.OUT, value=0)

    def aplicar(self, sol, bateria, rede):
        self.sol.value(1 if sol else 0)
        self.bateria.value(1 if bateria else 0)
        self.rede.value(1 if rede else 0)


# Sons: sequencias de (frequencia em Hz, duracao em ms). Frequencia 0 = pausa.
SOM_CONECTAR = ((1000, 80),)
SOM_DESCONECTAR = ((600, 80),)
SOM_COMPLETO = ((1200, 100), (0, 60), (1600, 180))
SOM_MODO = ((900, 50),)
SOM_EMERGENCIA = ((2000, 250), (0, 100), (2000, 250), (0, 100), (2000, 250))
SOM_RESET = ((800, 100), (1200, 100))


class Buzzer:
    """Buzzer por PWM que toca sem travar o programa (nao bloqueante).

    tocar() so coloca as notas numa fila; atualizar(), chamado no loop,
    troca de nota quando o tempo da nota atual termina.
    """

    def __init__(self, pino):
        self.pwm = PWM(Pin(pino))
        self.pwm.duty_u16(0)
        self._fila = []
        self._fim_ms = 0
        self._tocando = False

    def tocar(self, *notas):
        self._fila.extend(notas)

    def atualizar(self):
        agora = time.ticks_ms()
        if self._tocando and time.ticks_diff(agora, self._fim_ms) < 0:
            return
        if self._fila:
            freq, duracao = self._fila.pop(0)
            if freq > 0:
                self.pwm.freq(freq)
                self.pwm.duty_u16(32768)
            else:
                self.pwm.duty_u16(0)
            self._fim_ms = time.ticks_add(agora, duracao)
            self._tocando = True
        else:
            self.pwm.duty_u16(0)
            self._tocando = False
