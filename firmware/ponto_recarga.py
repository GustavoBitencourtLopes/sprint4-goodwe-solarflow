# SolarFlow - Ponto de recarga (maquina de estados)
# Cada ponto controla um veiculo: conexao, recarga, SOC e energia entregue.

import config

# Estados da maquina de estados
DISPONIVEL = "DISPONIVEL"
CONECTADO = "CONECTADO"
CARREGANDO = "CARREGANDO"
AGUARDANDO = "AGUARDANDO"
COMPLETO = "COMPLETO"
EMERGENCIA = "EMERGENCIA"

# Rotulos curtos para o display (maximo 5 caracteres)
ROTULO = {
    DISPONIVEL: "LIVRE",
    CONECTADO: "CONEC",
    CARREGANDO: "CARR",
    AGUARDANDO: "AGUAR",
    COMPLETO: "CHEIO",
    EMERGENCIA: "EMERG",
}

# Estados em que o veiculo esta conectado e ainda precisa de energia
ATIVOS = (CONECTADO, CARREGANDO, AGUARDANDO)


class PontoRecarga:
    def __init__(self, nome):
        self.nome = nome
        self.estado = DISPONIVEL
        self.soc = 0.0                  # % da bateria do veiculo
        self.potencia_kw = 0.0          # potencia entregue no ultimo ciclo
        self.energia_sessao_kwh = 0.0   # energia entregue desde a conexao

    def quer_energia(self):
        return self.estado in ATIVOS

    def falta_kwh(self):
        """Energia que falta para o veiculo chegar ao SOC alvo."""
        falta = (config.VEICULO_SOC_ALVO - self.soc) / 100 * config.VEICULO_CAPACIDADE_KWH
        return max(0.0, falta)

    def demanda_kw(self, dt_h):
        """Potencia que o ponto pede neste ciclo.

        Limitada pela potencia do carregador e pela energia que falta,
        para nao passar do SOC alvo no ultimo ciclo.
        """
        if not self.quer_energia():
            return 0.0
        if dt_h <= 0:
            return config.PONTO_POTENCIA_MAX_KW
        return min(config.PONTO_POTENCIA_MAX_KW, self.falta_kwh() / dt_h)

    def botao(self, soc_lido):
        """Botao do ponto: conecta (se livre) ou desconecta (se ocupado).

        Retorna o evento: "conectado", "ja_completo", "desconectado" ou None.
        """
        if self.estado == EMERGENCIA:
            return None
        if self.estado == DISPONIVEL:
            self.soc = soc_lido
            self.energia_sessao_kwh = 0.0
            self.potencia_kw = 0.0
            if self.soc >= config.VEICULO_SOC_ALVO:
                self.estado = COMPLETO
                return "ja_completo"
            self.estado = CONECTADO
            return "conectado"
        self.estado = DISPONIVEL
        self.potencia_kw = 0.0
        return "desconectado"

    def atualizar(self, potencia_kw, dt_h):
        """Aplica a potencia alocada durante dt_h horas. Retorna "completo" ou None."""
        if self.estado not in ATIVOS:
            self.potencia_kw = 0.0
            return None

        # Tolerancia de arredondamento: falta menos de 1 Wh, considera completo
        if self.falta_kwh() < 0.001:
            self.soc = config.VEICULO_SOC_ALVO
            self.estado = COMPLETO
            self.potencia_kw = 0.0
            return "completo"

        potencia_kw = min(max(potencia_kw, 0.0), config.PONTO_POTENCIA_MAX_KW)
        if potencia_kw <= 0:
            self.estado = AGUARDANDO
            self.potencia_kw = 0.0
            return None

        self.estado = CARREGANDO
        self.potencia_kw = potencia_kw
        energia = potencia_kw * dt_h
        falta = self.falta_kwh()

        if energia >= falta:
            # Ultimo ciclo: entrega so o que falta e encerra a recarga
            self.energia_sessao_kwh += falta
            self.soc = config.VEICULO_SOC_ALVO
            self.estado = COMPLETO
            self.potencia_kw = 0.0
            return "completo"

        self.energia_sessao_kwh += energia
        # dSOC (%) = energia (kWh) / capacidade (kWh) * 100
        self.soc += energia / config.VEICULO_CAPACIDADE_KWH * 100
        return None

    def entrar_emergencia(self):
        self.estado = EMERGENCIA
        self.potencia_kw = 0.0

    def resetar(self):
        """Apos a emergencia: ponto livre, veiculo precisa ser reconectado."""
        self.estado = DISPONIVEL
        self.soc = 0.0
        self.potencia_kw = 0.0
        self.energia_sessao_kwh = 0.0
