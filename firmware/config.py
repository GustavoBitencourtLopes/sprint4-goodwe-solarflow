# SolarFlow - Configuracao central
# Todos os pinos e parametros da simulacao ficam aqui.

# ================= PINOS (Raspberry Pi Pico W) =================
PIN_I2C_SDA = 8        # OLED (I2C0)
PIN_I2C_SCL = 9        # OLED (I2C0)

PIN_LED_A = 2          # Ponto A carregando
PIN_LED_B = 3          # Ponto B carregando
PIN_LED_SOL = 4        # Geracao solar ativa
PIN_LED_BAT = 5        # Bateria descarregando
PIN_LED_REDE = 6       # Importando energia da rede

PIN_BTN_EMERG = 12     # Parada de emergencia
PIN_BTN_MODO = 13      # Alterna Normal / Eco
PIN_BTN_A = 14         # Conectar/desconectar veiculo A
PIN_BTN_B = 15         # Conectar/desconectar veiculo B

PIN_BUZZER = 16        # PWM
PIN_RELE_A = 17        # Contator do ponto A
PIN_RELE_B = 18        # Contator do ponto B

PIN_LDR = 26           # ADC0 - luminosidade (convertida em irradiancia)
PIN_POT_A = 27         # ADC1 - SOC do veiculo A na conexao
PIN_POT_B = 28         # ADC2 - SOC do veiculo B na conexao

# ================= GERACAO SOLAR =================
PV_POTENCIA_KWP = 10.0         # Potencia de pico dos paineis (kW)
IRRADIANCIA_MAX = 1000.0       # W/m2 (condicao padrao de teste)
LUX_POR_WM2 = 100.0            # Aproximacao: sol pleno ~100.000 lux ~ 1000 W/m2

# Modelo do modulo fotoresistor do Wokwi (divisor de tensao)
LDR_VCC = 3.3                  # Tensao de alimentacao do modulo (V)
LDR_R_FIXO = 10000.0           # Resistor fixo do divisor (ohms)
LDR_GAMMA = 0.7                # Inclinacao da curva log(R) x log(lux)
LDR_RL10_KOHM = 50.0           # Resistencia do LDR a 10 lux (kohms)

# ================= BATERIA ESTACIONARIA =================
BAT_CAPACIDADE_KWH = 10.0
BAT_POTENCIA_MAX_KW = 5.0      # Limite de carga e de descarga
BAT_SOC_INICIAL = 60.0         # %
BAT_SOC_MIN = 20.0             # % - protecao contra descarga profunda
BAT_RESERVA_FORA_PONTA = 50.0  # % - modo Normal fora da ponta: guarda energia para a ponta
BAT_SOC_MAX = 100.0            # %

# ================= PONTOS DE RECARGA E VEICULOS =================
PONTO_POTENCIA_MAX_KW = 7.0    # Referencia: GoodWe HCA 7 kW
POTENCIA_MIN_RECARGA_KW = 0.1  # Abaixo disso a energia nao vai aos veiculos (aguardam)
VEICULO_CAPACIDADE_KWH = 50.0
VEICULO_SOC_ALVO = 80.0        # %

# ================= REDE ELETRICA =================
REDE_LIMITE_KW = 10.0          # Fora do horario de ponta
REDE_LIMITE_PONTA_KW = 3.0     # No horario de ponta
PONTA_INICIO_MIN = 17 * 60 + 30   # 17:30 - inicio do horario de ponta (Enel SP)
PONTA_FIM_MIN = 20 * 60 + 30      # 20:30 - fim do horario de ponta (Enel SP)

# ================= TEMPO =================
HORA_INICIAL = 16              # Hora em que o relogio simulado comeca
ESCALA_MIN_POR_S = 5           # 1 s real = 5 min simulados
CICLO_MS = 500                 # Periodo do loop principal (ms)
BOTAO_AMOSTRA_MS = 10          # Periodo da interrupcao de timer que le os botoes (ms)
DEBOUNCE_MS = 30               # Tempo que o botao precisa ficar estavel para valer (ms)

# ================= TELEMETRIA =================
TELEMETRIA_ATIVA = True        # Envia uma linha DADOS,... por ciclo pela serial

# ================= CENARIO AUTOMATICO =================
CENARIO_AUTOMATICO = True      # True: simula um dia completo sozinho (06h as 24h)
                               # False: modo manual (LDR, potenciometros e botoes)
