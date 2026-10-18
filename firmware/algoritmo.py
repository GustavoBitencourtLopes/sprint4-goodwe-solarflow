# SolarFlow - Algoritmo de divisao proporcional com prioridade pela menor bateria
#
# A potencia disponivel e dividida de forma proporcional a ENERGIA QUE FALTA
# para cada veiculo chegar ao SOC alvo: quem tem menos bateria recebe mais.
# Se um ponto atingir seu limite, a sobra e redistribuida entre os demais.


def dividir_proporcional(potencia_kw, pedidos):
    """Divide potencia_kw entre os pontos.

    pedidos: dicionario {nome: (falta_kwh, limite_kw)}
      falta_kwh -> energia que falta para o SOC alvo (define o peso)
      limite_kw -> maximo que o ponto pode receber neste ciclo
    Retorna: dicionario {nome: potencia_kw}
    """
    alocacao = {}
    for nome in pedidos:
        alocacao[nome] = 0.0

    # So participam pontos que precisam de energia e podem receber
    restantes = [n for n in pedidos if pedidos[n][0] > 0 and pedidos[n][1] > 0]
    sobra = potencia_kw

    while restantes and sobra > 1e-6:
        soma_faltas = 0.0
        for n in restantes:
            soma_faltas += pedidos[n][0]

        saturados = []
        distribuido = 0.0
        for n in restantes:
            parte = sobra * pedidos[n][0] / soma_faltas       # fatia proporcional
            livre = pedidos[n][1] - alocacao[n]               # quanto ainda cabe
            if parte >= livre:
                alocacao[n] += livre                          # bateu no limite
                distribuido += livre
                saturados.append(n)
            else:
                alocacao[n] += parte
                distribuido += parte

        sobra -= distribuido
        if not saturados:
            break                                             # tudo distribuido
        restantes = [n for n in restantes if n not in saturados]  # redistribui a sobra

    return alocacao
