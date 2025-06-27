import networkx as nx
import matplotlib.pyplot as plt
import time
import random
import ipaddress

def next_hop(router, destino_ip, routing_tables):
    table = routing_tables.get(router, {})
    for subnet, neighbor in table.items():
        if ipaddress.IPv4Address(destino_ip) in ipaddress.IPv4Network(subnet):
            return neighbor
    return None  # Default route (se quiser implementar depois)

def xping_routing(G, origem, destino, routing_tables):
    try:
        if destino not in G.nodes or origem not in G.nodes:
            print(f"Nó inválido: {origem} ou {destino} não existe.")
            return

        destino_ip = G.nodes[destino]['ip']
        atual = origem
        visitados = set()
        hops = []

        print(f"Ping de {origem} ({G.nodes[origem]['ip']}) para {destino} ({destino_ip})")

        # Se for host, envia para o switch vizinho
        if G.nodes[atual]['type'] == "host":
            vizinhos = list(G.neighbors(atual))
            if not vizinhos:
                print(f"Host {atual} não tem vizinhos.")
                return
            atual = vizinhos[0]
            hops.append((atual, G.nodes[atual].get('ip', 'N/A')))
            visitados.add(origem)

        while atual != destino:
            if atual in visitados:
                print(f"⚠️ Loop detectado em {atual}. Encerrando.")
                return
            visitados.add(atual)

            tipo_atual = G.nodes[atual]['type']

            # SWITCH
            if tipo_atual == "switch":
                if destino in G.neighbors(atual):
                    hops.append((destino, G.nodes[destino].get('ip', 'N/A')))
                    break
                else:
                    encaminhado = False
                    for viz in G.neighbors(atual):
                        tipo_viz = G.nodes[viz]['type']
                        if tipo_viz in ("router", "switch") and viz not in visitados:
                            atual = viz
                            hops.append((atual, G.nodes[atual].get('ip', 'N/A')))
                            encaminhado = True
                            break
                    if not encaminhado:
                        print(f"Switch {atual} não conseguiu encaminhar para {destino}.")
                        return

            # ROTEADOR
            elif tipo_atual == "router":
                nh = next_hop(atual, destino_ip, routing_tables)
                if not nh:
                    print(f"Roteador {atual} não tem rota para {destino_ip}.")
                    return
                atual = nh
                hops.append((atual, G.nodes[atual].get('ip', 'N/A')))

            # HOST (incomum, mas previne erro)
            elif tipo_atual == "host":
                print(f"Host intermediário encontrado inesperadamente em {atual}.")
                return

        # Impressão final
        for hop, ip in hops:
            print(f" -> {hop} ({ip})")
        print(f"Resposta de {destino}: Sucesso\n")

    except Exception as e:
        print(f"Erro: {e}")


def xtraceroute_routing(G, origem, destino, routing_tables):
    try:
        destino_ip = G.nodes[destino]['ip']
        atual = origem
        total_delay = 0
        hop_num = 1

        print(f"XTraceroute de {origem} ({G.nodes[origem]['ip']}) até {destino} ({destino_ip})")
        print("Saltos:")

        visitados = set()

        # Primeiro salto: se origem é host, avança para o switch e mostra
        if G.nodes[atual]['type'] == "host":
            vizinhos = list(G.neighbors(atual))
            proximo = vizinhos[0]  # Assume conexão direta
            delay = random.randint(2, 6)
            total_delay += delay
            print(f"{hop_num}: {proximo} ({G.nodes[proximo].get('ip', 'N/A')})   {total_delay} ms")
            hop_num += 1
            visitados.add(atual)
            atual = proximo

        while atual != destino:
            if atual in visitados and G.nodes[atual]['type'] != "router":
                print(f"⚠️ Roteamento em loop detectado em {atual}. Encerrando.")
                return
            visitados.add(atual)

            tipo_atual = G.nodes[atual]['type']

            # ---------- SWITCH ----------
            if tipo_atual == "switch":
                if destino in G.neighbors(atual):
                    delay = random.randint(2, 6)
                    total_delay += delay
                    print(f"{hop_num}: {destino} ({G.nodes[destino].get('ip', 'N/A')})   {total_delay} ms")
                    print("\nRota concluída com sucesso.\n")
                    return

                fila = [(atual, [atual])]
                visitados_switches = set()

                while fila:
                    nodo, caminho = fila.pop(0)
                    visitados_switches.add(nodo)

                    for vizinho in G.neighbors(nodo):
                        if vizinho in visitados_switches:
                            continue

                        tipo = G.nodes[vizinho]['type']

                        if vizinho == destino:
                            for hop in caminho[1:] + [vizinho]:
                                if hop not in visitados:
                                    delay = random.randint(2, 6)
                                    total_delay += delay
                                    ip = G.nodes[hop].get('ip', 'N/A')
                                    print(f"{hop_num}: {hop} ({ip})   {total_delay} ms")
                                    hop_num += 1
                                    visitados.add(hop)
                            print("\nRota concluída com sucesso.\n")
                            return

                        if tipo == "host":
                            continue

                        if tipo == "switch":
                            fila.append((vizinho, caminho + [vizinho]))

                        if tipo == "router" and vizinho not in visitados:
                            for hop in caminho[1:]:
                                if hop not in visitados:
                                    delay = random.randint(2, 6)
                                    total_delay += delay
                                    ip = G.nodes[hop].get('ip', 'N/A')
                                    print(f"{hop_num}: {hop} ({ip})   {total_delay} ms")
                                    hop_num += 1
                                    visitados.add(hop)

                            # ✅ Correção: imprimir roteador alcançado
                            delay = random.randint(2, 6)
                            total_delay += delay
                            ip = G.nodes[vizinho].get('ip', 'N/A')
                            print(f"{hop_num}: {vizinho} ({ip})   {total_delay} ms")
                            hop_num += 1
                            visitados.add(vizinho)

                            atual = vizinho
                            break
                    else:
                        continue
                    break
                else:
                    print(f"⚠️ Switch {atual} não encontrou rota para {destino}")
                    return
                continue

            # ---------- ROTEADOR ----------
            elif tipo_atual == "router":
                nh = next_hop(atual, destino_ip, routing_tables)
                if not nh:
                    print(f"Sem rota de {atual} para {destino_ip}")
                    return
                delay = random.randint(5, 15)
                total_delay += delay
                print(f"{hop_num}: {nh} ({G.nodes[nh].get('ip', 'N/A')})   {total_delay} ms")
                atual = nh
                hop_num += 1

        # Quando sai do loop e chegou ao destino (via roteadores)
        print(f"{hop_num}: {destino} ({destino_ip})   {total_delay + random.randint(2, 5)} ms")
        print("\nRota concluída com sucesso.\n")

    except Exception as e:
        print(f"Erro durante o traceroute: {e}")




def hierarchy_pos(G, root, width=1.0, vert_gap=0.2, vert_loc=0, xcenter=0.5, pos=None, parent=None):
    """Posiciona o grafo como uma árvore com raiz `root`."""
    if pos is None:
        pos = {root: (xcenter, vert_loc)}
    else:
        pos[root] = (xcenter, vert_loc)
    neighbors = list(G.neighbors(root))
    if parent is not None:
        neighbors.remove(parent)  # remove back edge to parent
    if len(neighbors) != 0:
        dx = width / len(neighbors)
        next_x = xcenter - width/2 - dx/2
        for neighbor in neighbors:
            next_x += dx
            pos = hierarchy_pos(G, neighbor, width=dx, vert_gap=vert_gap,
                                vert_loc=vert_loc - vert_gap, xcenter=next_x,
                                pos=pos, parent=root)
    return pos


def main():
    G = nx.Graph()
    # Roteadores
    G.add_node("c1", type="router", ip="N/A")
    G.add_node("a1", type="router", ip="N/A")
    G.add_node("a2", type="router", ip="N/A")

    # Switches
    G.add_node("e1a", type="switch", ip="172.16.0.10")
    G.add_node("e2a", type="switch", ip="172.16.0.44")
    G.add_node("e1b", type="switch", ip="172.16.0.11")
    G.add_node("e2b", type="switch", ip="172.16.0.45")
    G.add_node("e3", type="switch", ip="172.16.0.74")
    G.add_node("e4", type="switch", ip="172.16.0.106")

    # Hosts (alguns como exemplo)
    G.add_node("h1", type="host", ip="172.16.0.2")
    G.add_node("h2", type="host", ip="172.16.0.3")
    G.add_node("h3", type="host", ip="172.16.0.34")
    G.add_node("h4", type="host", ip="172.16.0.35")
    G.add_node("h5", type="host", ip="172.16.0.66")
    G.add_node("h6", type="host", ip="172.16.0.67")
    G.add_node("h7", type="host", ip="172.16.0.98")
    G.add_node("h8", type="host", ip="172.16.0.99")

    G.add_edge("c1", "a1", type="serial", interface_c1="S0/3/0", interface_a1="S0/3/0", subnet="172.16.1.0/30")
    G.add_edge("c1", "a2", type="serial", interface_c1="S0/3/1", interface_a2="S0/3/0", subnet="172.16.1.4/30")

    G.add_edge("a1", "e1a", type="ethernet", subnet="172.16.0.0/27")
    G.add_edge("a1", "e2a", type="ethernet", subnet="172.16.0.32/27")
    G.add_edge("a2", "e3", type="ethernet", subnet="172.16.0.64/27")
    G.add_edge("a2", "e4", type="ethernet", subnet="172.16.0.96/27")

    G.add_edge("e1b", "h1", type="ethernet")

    G.add_edge("e1b", "e1a", type="ethernet")

    G.add_edge("e1a", "h2", type="ethernet")

    G.add_edge("e2a", "e2b", type="ethernet")

    G.add_edge("e2b", "h3", type="ethernet")
    G.add_edge("e2a", "h4", type="ethernet")
    G.add_edge("e3", "h5", type="ethernet")
    G.add_edge("e3", "h6", type="ethernet")
    G.add_edge("e4", "h7", type="ethernet")
    G.add_edge("e4", "h8", type="ethernet")

    routing_tables = {
        "a1": {
            "172.16.0.0/27": "e1a",  # Subrede h1, h2 via e1b -> e1a
            "172.16.0.32/27": "e2a",  # Subrede h3, h4 via e2b -> e2a
            "172.16.0.64/27": "c1",  # Encaminha para c1 (subrede de a2)
            "172.16.0.96/27": "c1",
        },
        "a2": {
            "172.16.0.64/27": "e3",   # h5, h6
            "172.16.0.96/27": "e4",   # h7, h8
            "172.16.0.0/27": "c1",    # Subredes de a1 via c1
            "172.16.0.32/27": "c1",
        },
        "c1": {
            "172.16.0.0/27": "a1",
            "172.16.0.32/27": "a1",
            "172.16.0.64/27": "a2",
            "172.16.0.96/27": "a2",
        }
    }

    node_colors = []
    for node in G.nodes:
        tipo = G.nodes[node].get("type", "")
        if tipo == "router":
            node_colors.append("lightcoral")
        elif tipo == "switch":
            node_colors.append("lightblue")
        elif tipo == "host":
            node_colors.append("wheat")
        else:
            node_colors.append("gray")

    print("Escolha o algoritmo de Emparelhamento:")
    print("1 - XPing")
    print("2 - XTraceroute")
    print("3 - Exibir Grafo")
    print("4 - Terminar Execução")
    escolha = input("Digite 1, 2, 3 ou 4: ").strip()

    if escolha == '1':
        print()
        origem = input("Digite o nó de origem (ex: h1, e1a, a1): ").strip()
        destino = input("Digite o nó de destino (ex: h2, e2a, a2): ").strip()
        xping_routing(G, origem, destino, routing_tables)
        main()
    elif escolha == '2':
        print()
        origem = input("Digite o nó de origem (ex: h1, e1a, a1): ").strip()
        destino = input("Digite o nó de destino (ex: h2, e2a, a2): ").strip()
        xtraceroute_routing(G, origem, destino, routing_tables)
        main()
    elif escolha == '3':
        print()
        print("Exibindo o grafo...")
        pos = hierarchy_pos(G, "c1")
        labels = {node: f"{node}\n{G.nodes[node]['ip']}" for node in G.nodes()}
        nx.draw(G, pos, with_labels=True, labels=labels,
        node_color=node_colors, node_size=2000, edge_color="gray",
        font_size=8, font_weight="bold")
        plt.show()
        print("Grafo exibido com sucesso.\n")
        main()
    elif escolha == '4':
        print()
        return
    else:
        print()
        print("Opção inválida. Por favor, escolha 1, 2, 3 ou 4.")


if __name__ == "__main__":
    main()