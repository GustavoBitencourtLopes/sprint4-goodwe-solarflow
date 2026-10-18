# SolarFlow - Painel de status no display OLED SSD1306 (128x64, I2C0)
# Fonte de 8x8 pixels: cabem 16 caracteres por linha.

from machine import I2C, Pin
import ssd1306
import config
from ponto_recarga import ROTULO, DISPONIVEL, EMERGENCIA


class Painel:
    def __init__(self):
        i2c = I2C(0, sda=Pin(config.PIN_I2C_SDA), scl=Pin(config.PIN_I2C_SCL), freq=400000)
        self.oled = ssd1306.SSD1306_I2C(128, 64, i2c)

    def desenhar(self, hora, ponta, modo_eco, solar_kw, bateria_soc, pontos, fluxo, emergencia):
        o = self.oled
        o.fill(0)

        # Linha 1: horario, modo e aviso de horario de ponta
        o.text("{} {} {}".format(hora, "ECO " if modo_eco else "NORM", "PONTA" if ponta else ""), 0, 0)

        # Linha 2: geracao solar (kW) e carga da bateria estacionaria (%)
        o.text("Sol{:5.1f} Bat{:3.0f}%".format(solar_kw, bateria_soc), 0, 11)
        o.hline(0, 21, 128, 1)

        # Linhas 3 e 4: um ponto de recarga por linha (estado, SOC e potencia)
        y = 25
        for nome in ("A", "B"):
            p = pontos[nome]
            if p.estado in (DISPONIVEL, EMERGENCIA):
                soc = " -- "
            else:
                soc = "{:3.0f}%".format(p.soc)
            o.text("{} {:<5}{} {:3.1f}".format(nome, ROTULO[p.estado], soc, p.potencia_kw), 0, y)
            y += 11
        o.hline(0, 47, 128, 1)

        # Linha 5: emergencia, energia vinda da rede ou excedente injetado
        if emergencia:
            o.text("!! EMERGENCIA !!", 0, 53)
        elif fluxo["injetada"] > 0.01:
            o.text("Injeta:{:5.2f} kW".format(fluxo["injetada"]), 0, 53)
        else:
            o.text("Rede:  {:5.2f} kW".format(fluxo["rede_veiculos"]), 0, 53)

        o.show()
