## Resultados quantitativos (cenário automático de um dia)

Período simulado: 06:02 a 22:32 (16,5 h), 396 registros de telemetria.

### Origem da energia entregue aos veículos

| Fonte | Energia (kWh) | Participação |
|---|---|---|
| Solar direto | 31,78 | 39,1% |
| Bateria (carregada pelo sol) | 16,00 | 19,7% |
| Rede elétrica | 33,52 | 41,2% |
| **Total** | **81,30** | **58,8% de energia renovável local** |

### Aproveitamento da geração solar

| Indicador | Valor |
|---|---|
| Geração solar total | 56,09 kWh |
| Usada nos veículos ou guardada na bateria | 43,78 kWh (78,0%) |
| Excedente injetado na rede | 12,32 kWh (22,0%) |

### Comparação com uma estação convencional (100% rede, mesma energia entregue)

| Estação | Energia comprada da rede (kWh) | Custo, tarifa convencional (R$) | Custo, tarifa branca (R$) | CO₂ (kg) |
|---|---|---|---|---|
| Convencional | 81,30 | 48,29 | 51,75 | 3,13 |
| SolarFlow | 33,52 | 19,91 | 24,24 | 1,29 |

| Ganho do SolarFlow | Valor |
|---|---|
| Redução da energia comprada da rede | 47,78 kWh (58,8%) |
| Economia no dia, tarifa convencional | R$ 28,38 (58,8%) |
| Economia no dia, tarifa branca | R$ 27,51 (53,2%) |
| Economia projetada no ano, tarifa convencional (250 dias úteis) | R$ 7.094,87 |
| CO₂ evitado no dia | 1,84 kg |
| CO₂ evitado projetado no ano (250 dias úteis) | 460 kg |
| Pico de demanda da rede no horário de ponta | 14,0 kW → 3,0 kW (79% menor) |
| Energia da rede consumida no horário de ponta | 12,05 kWh → 8,53 kWh |

Modalidade tarifária mais vantajosa para o SolarFlow neste perfil de uso: **tarifa convencional** (R$ 19,91 contra R$ 48,29 da melhor opção da estação convencional).

### Sessões de recarga

| Ponto | Chegada | SOC na chegada | Saída | SOC na saída | Energia (kWh) |
|---|---|---|---|---|---|
| A | 08:00 | 25% | 14:00 | 80% | 27,50 |
| B | 09:30 | 45% | 15:00 | 80% | 17,50 |
| A | 16:30 | 20% | 21:30 | 56% | 18,18 |
| B | 17:47 | 30% | 22:32 | 66% | 18,12 |

Premissas: tarifas de referência da Enel SP sem impostos (convencional R$ 0,594/kWh; tarifa branca R$ 1,115 na ponta, R$ 0,724 no intermediário e R$ 0,499 fora da ponta); horário de ponta da Enel SP das 17h30 às 20h30; fator médio de emissão do SIN de 0,0385 kg CO₂/kWh (MCTI, 2023); dia útil; a estação convencional entrega a mesma energia nos mesmos horários, comprando tudo da rede.