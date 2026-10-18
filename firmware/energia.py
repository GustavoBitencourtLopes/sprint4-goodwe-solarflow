# SolarFlow - Gestor de energia
# Bateria estacionaria + balanco de energia a cada ciclo:
#   para os veiculos: solar -> bateria -> rede
#   excedente solar:  bateria -> injecao na rede

import config


class Bateria:
    """Bateria estacionaria (equivalente: GoodWe Lynx Home)."""

    def __init__(self):
        self.soc = config.BAT_SOC_INICIAL   # %

    def _kwh(self, pontos_percentuais):
        return pontos_percentuais / 100 * config.BAT_CAPACIDADE_KWH

    def max_descarga_kw(self, soc_min, dt_h):
        """Potencia maxima que a bateria entrega sem passar de soc_min."""
        disponivel = self._kwh(max(0.0, self.soc - soc_min))
        if disponivel <= 0:
            return 0.0
        if dt_h <= 0:
            return config.BAT_POTENCIA_MAX_KW
        return min(config.BAT_POTENCIA_MAX_KW, disponivel / dt_h)

    def max_carga_kw(self, dt_h):
        """Potencia maxima que a bateria aceita sem passar de 100%."""
        espaco = self._kwh(max(0.0, config.BAT_SOC_MAX - self.soc))
        if espaco <= 0:
            return 0.0
        if dt_h <= 0:
            return config.BAT_POTENCIA_MAX_KW
        return min(config.BAT_POTENCIA_MAX_KW, espaco / dt_h)

    def aplicar(self, potencia_kw, dt_h):
        """Potencia positiva carrega, negativa descarrega."""
        self.soc += potencia_kw * dt_h / config.BAT_CAPACIDADE_KWH * 100
        self.soc = min(max(self.soc, 0.0), config.BAT_SOC_MAX)


class GestorEnergia:
    def __init__(self):
        self.bateria = Bateria()
        self.fluxo = {
            "solar": 0.0,             # geracao solar total (kW)
            "solar_veiculos": 0.0,    # solar entregue aos veiculos
            "bateria_veiculos": 0.0,  # bateria entregue aos veiculos
            "rede_veiculos": 0.0,     # rede entregue aos veiculos
            "bateria_carga": 0.0,     # excedente solar guardado na bateria
            "injetada": 0.0,          # excedente solar injetado na rede
            "para_veiculos": 0.0,     # total disponivel para os veiculos
        }
        # Energia acumulada desde o inicio (kWh) - usada nos resultados
        self.energia = {}
        for chave in self.fluxo:
            self.energia[chave] = 0.0

    def balancear(self, demanda_kw, solar_kw, rede_limite_kw, bat_soc_min, dt_h):
        bat = self.bateria

        # 1. Solar atende os veiculos primeiro
        solar_veiculos = min(solar_kw, demanda_kw)
        falta = demanda_kw - solar_veiculos

        # 2. Bateria completa o que falta (respeitando o SOC minimo do momento)
        bateria_veiculos = min(falta, bat.max_descarga_kw(bat_soc_min, dt_h))
        falta -= bateria_veiculos

        # 3. Rede completa o restante, ate o limite do momento (0 no modo Eco)
        rede_veiculos = min(falta, rede_limite_kw)

        # Energia insuficiente para recarregar: os veiculos aguardam
        # e o pouco que ha de sol vai para a bateria
        if solar_veiculos + bateria_veiculos + rede_veiculos < config.POTENCIA_MIN_RECARGA_KW:
            solar_veiculos = 0.0
            bateria_veiculos = 0.0
            rede_veiculos = 0.0

        # 4. Excedente solar: primeiro a bateria, depois injecao na rede
        sobra = solar_kw - solar_veiculos
        bateria_carga = min(sobra, bat.max_carga_kw(dt_h))
        injetada = sobra - bateria_carga

        bat.aplicar(bateria_carga - bateria_veiculos, dt_h)

        self.fluxo["solar"] = solar_kw
        self.fluxo["solar_veiculos"] = solar_veiculos
        self.fluxo["bateria_veiculos"] = bateria_veiculos
        self.fluxo["rede_veiculos"] = rede_veiculos
        self.fluxo["bateria_carga"] = bateria_carga
        self.fluxo["injetada"] = injetada
        self.fluxo["para_veiculos"] = solar_veiculos + bateria_veiculos + rede_veiculos

        for chave in self.fluxo:
            self.energia[chave] += self.fluxo[chave] * dt_h
        return self.fluxo
