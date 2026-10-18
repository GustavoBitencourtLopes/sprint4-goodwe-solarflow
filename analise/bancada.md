### Teste 1: dia completo (cenário automático)

| Estratégia | Energia entregue (kWh) | Comprada da rede (kWh) | Rede na ponta (kWh) | Pico na ponta (kW) | Custo, tarifa convencional (R$) | CO₂ (kg) | SOC na saída (A, B, A, B) |
|---|---|---|---|---|---|---|---|
| SolarFlow completo | 81,23 | 33,53 | 8,53 | 3,0 | 19,92 | 1,29 | 80%, 80%, 56%, 66% |
| Divisão igual (sem prioridade) | 81,23 | 33,39 | 8,53 | 3,0 | 19,83 | 1,29 | 80%, 80%, 58%, 64% |
| Sem reserva para a ponta | 81,23 | 31,77 | 8,53 | 3,0 | 18,87 | 1,22 | 80%, 80%, 56%, 66% |
| Estação convencional | 100,00 | 100,00 | 40,25 | 14,0 | 59,40 | 3,85 | 80%, 80%, 80%, 80% |

### Teste 2: prioridade pela menor bateria

Dois veículos chegam juntos às 21h30 (A com 20%, B com 60%) e saem juntos às 23h30, com 10 kW disponíveis da rede e bateria estacionária vazia.

| Divisão | SOC de A na saída | SOC de B na saída | Menor SOC na saída |
|---|---|---|---|
| Proporcional (SolarFlow) | 47% | 72% | 47% |
| Igual | 40% | 80% | 40% |

### Teste 3: reserva da bateria para o horário de ponta

Bateria cheia às 15h. O veículo A carrega das 15h30 às 17h30, e o veículo B chega às 17h30, início da ponta, e sai às 20h30.

| Estratégia | Energia entregue a B na ponta (kWh) | SOC de B na saída | Rede na ponta (kWh) |
|---|---|---|---|
| Com reserva (SolarFlow) | 11,42 | 53% | 8,12 |
| Sem reserva | 9,73 | 49% | 8,75 |