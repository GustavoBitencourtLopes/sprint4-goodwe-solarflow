# SolarFlow - Teste de hardware (Bloco 2.1)
# Testa todos os componentes do circuito, um por vez.
# No Wokwi, este codigo vai no main.py so durante esta etapa.

from machine import Pin, ADC, I2C, PWM
import time
import ssd1306

# ---------- Saidas ----------
leds = {
    "A": Pin(2, Pin.OUT),
    "B": Pin(3, Pin.OUT),
    "SOL": Pin(4, Pin.OUT),
    "BAT": Pin(5, Pin.OUT),
    "REDE": Pin(6, Pin.OUT),
}
reles = {"A": Pin(17, Pin.OUT), "B": Pin(18, Pin.OUT)}
buzzer = PWM(Pin(16))
buzzer.duty_u16(0)

# ---------- Entradas ----------
botoes = {
    "EMERG": Pin(12, Pin.IN, Pin.PULL_UP),
    "MODO": Pin(13, Pin.IN, Pin.PULL_UP),
    "A": Pin(14, Pin.IN, Pin.PULL_UP),
    "B": Pin(15, Pin.IN, Pin.PULL_UP),
}
adc_ldr = ADC(26)
adc_pot_a = ADC(27)
adc_pot_b = ADC(28)

# ---------- Display (I2C0 em GP8/GP9) ----------
i2c = I2C(0, sda=Pin(8), scl=Pin(9), freq=400000)
enderecos = i2c.scan()
print("[I2C] Dispositivos encontrados:", [hex(e) for e in enderecos])
oled = ssd1306.SSD1306_I2C(128, 64, i2c)


def bipe(freq=1000, duracao=0.15):
    buzzer.freq(freq)
    buzzer.duty_u16(32768)
    time.sleep(duracao)
    buzzer.duty_u16(0)


def porcentagem(adc):
    return adc.read_u16() * 100 / 65535


# ---------- Teste 1: display ----------
oled.fill(0)
oled.text("SolarFlow", 28, 0)
oled.text("Teste de", 32, 24)
oled.text("hardware", 32, 36)
oled.show()
print("[OLED] Mensagem exibida")
time.sleep(1)

# ---------- Teste 2: LEDs um por um ----------
for nome, led in leds.items():
    print("[LED] Acendendo", nome)
    led.on()
    time.sleep(0.4)
    led.off()

# ---------- Teste 3: reles ----------
for nome, rele in reles.items():
    print("[RELE] Ligando ponto", nome)
    rele.on()
    time.sleep(0.6)
    rele.off()

# ---------- Teste 4: buzzer ----------
print("[BUZZER] Tocando")
bipe(800)
bipe(1200)

print("[OK] Testes automaticos concluidos")
print("Agora mexa no LDR, nos potenciometros e aperte os botoes.")

# ---------- Teste 5: leitura continua ----------
while True:
    ldr = porcentagem(adc_ldr)
    pot_a = porcentagem(adc_pot_a)
    pot_b = porcentagem(adc_pot_b)
    apertados = [nome for nome, b in botoes.items() if b.value() == 0]

    # Botao A e B acendem o LED do respectivo ponto enquanto pressionados
    leds["A"].value(botoes["A"].value() == 0)
    leds["B"].value(botoes["B"].value() == 0)
    if botoes["EMERG"].value() == 0:
        bipe(2000, 0.05)

    print("LDR={:5.1f}%  POT_A={:5.1f}%  POT_B={:5.1f}%  BOTOES={}".format(
        ldr, pot_a, pot_b, apertados))

    oled.fill(0)
    oled.text("LDR:   {:5.1f}%".format(ldr), 0, 0)
    oled.text("POT A: {:5.1f}%".format(pot_a), 0, 16)
    oled.text("POT B: {:5.1f}%".format(pot_b), 0, 32)
    oled.text("BTN: " + (",".join(apertados) or "-"), 0, 48)
    oled.show()

    time.sleep(0.5)
