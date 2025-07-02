import networkx as nx
import matplotlib.pyplot as plt
import time
import random
import ipaddress

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



def same_subnet(ip1, ip2, mask="255.255.255.224"):
    try:
        if "N/A" in (ip1, ip2):
                return False
        # Função simples para checar se IPs estão na mesma subrede
        import ipaddress
        net1 = ipaddress.IPv4Network(f"{ip1}/{mask}", strict=False)
        net2 = ipaddress.IPv4Network(f"{ip2}/{mask}", strict=False)
        return net1.network_address == net2.network_address
    except Exception:
        return False

def find_path_same_subnet(G, origem, destino):
    # Retorna o caminho mais curto entre origem e destino considerando só hosts e switches (sem roteadores)
    subgraph_nodes = [n for n in G.nodes if G.nodes[n]['type'] in ('host','switch')]
    SG = G.subgraph(subgraph_nodes)
    try:
        return nx.shortest_path(SG, origem, destino)
    except:
        return None


def next_hop(router, destino_ip, routing_tables):
    table = routing_tables.get(router, {})
    for subnet, neighbor in table.items():
        if ipaddress.IPv4Address(destino_ip) in ipaddress.IPv4Network(subnet):
            return neighbor
    return None  # Default route (se quiser implementar depois)

def xping_routing_return(G, origem, destino, routing_tables, subnet_mask="255.255.255.224"):
    def caminho_mesma_subnet(G, start, end):
        """Retorna o caminho para hosts na mesma subnet navegando só pelos switches e hosts."""
        atual = start
        visitados = set()
        hops = []

        if G.nodes[atual]['type'] == "host":
            vizinhos = list(G.neighbors(atual))
            if not vizinhos:
                return None
            atual = vizinhos[0]
            hops.append((atual, G.nodes[atual].get('ip', 'N/A')))
            visitados.add(start)

        while atual != end:
            if atual in visitados:
                return None  # loop
            visitados.add(atual)

            # Se o destino é vizinho direto, caminho finaliza
            if end in G.neighbors(atual):
                hops.append((end, G.nodes[end].get('ip', 'N/A')))
                break

            # Avança para próximo switch
            avancou = False
            for viz in G.neighbors(atual):
                if viz not in visitados and G.nodes[viz]['type'] in ("switch", "host"):
                    atual = viz
                    hops.append((atual, G.nodes[atual].get('ip', 'N/A')))
                    avancou = True
                    break
            if not avancou:
                return None
        return hops

    def caminho_valido(G, start, end, routing_tables):
        destino_ip = G.nodes[end]['ip']
        atual = start
        visitados = set()
        hops = []

        # Se hosts na mesma subnet, use caminho_mesma_subnet
        ip_start = G.nodes[start]['ip']
        ip_end = G.nodes[end]['ip']
        if same_subnet(ip_start, ip_end, subnet_mask):
            return caminho_mesma_subnet(G, start, end)

        # Caso contrário, usa rota via roteadores
        if G.nodes[atual]['type'] == "host":
            vizinhos = list(G.neighbors(atual))
            if not vizinhos:
                return None
            atual = vizinhos[0]
            hops.append((atual, G.nodes[atual].get('ip', 'N/A')))
            visitados.add(start)

        while atual != end:
            if atual in visitados:
                return None  # Loop detectado
            visitados.add(atual)

            tipo_atual = G.nodes[atual]['type']

            if tipo_atual == "switch":
                if end in G.neighbors(atual):
                    hops.append((end, G.nodes[end].get('ip', 'N/A')))
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
                        return None

            elif tipo_atual == "router":
                nh = next_hop(atual, destino_ip, routing_tables)
                if not nh:
                    return None
                atual = nh
                hops.append((atual, G.nodes[atual].get('ip', 'N/A')))

            elif tipo_atual == "host":
                return None

        return hops

    # Caminho ida
    caminho_ida = caminho_valido(G, origem, destino, routing_tables)
    if caminho_ida is None:
        print(f"Ping de {origem} para {destino}: Falha no caminho de ida.")
        return

    # Caminho volta
    caminho_volta = caminho_valido(G, destino, origem, routing_tables)
    if caminho_volta is None:
        print(f"Ping de {origem} para {destino}: Falha no caminho de volta.")
        return

    # Sucesso
    print(f"Ping de {origem} ({G.nodes[origem]['ip']}) para {destino} ({G.nodes[destino]['ip']}) - Sucesso")
    print("Caminho (ida):")
    for hop, ip in caminho_ida:
        print(f" -> {hop} ({ip})")
    print("Caminho (volta):")
    for hop, ip in caminho_volta:
        print(f" -> {hop} ({ip})")
    print("Resposta de", destino, ": Sucesso\n")


def xtraceroute_routing_probe(G, origem, destino, routing_tables):
    try:
        destino_ip = G.nodes[destino]['ip']
        origem_ip = G.nodes[origem]['ip']
        total_delay = 0
        hop_num = 1

        print(f"XTraceroute de {origem} ({G.nodes[origem]['ip']}) até {destino} ({destino_ip})")
        print("Saltos:")

        if same_subnet(origem_ip, destino_ip):
            path = find_path_same_subnet(G, origem, destino)
            if path is None:
                print(f"⚠️ Nenhum caminho direto na subrede entre {origem} e {destino}")
                return
            for hop in path[1:]:  # pular origem
                delay = random.randint(2, 6)
                total_delay += delay
                ip = G.nodes[hop].get('ip', 'N/A')
                print(f"{hop_num}: {hop} ({ip})   {total_delay} ms")
                hop_num += 1
            print("\nRota concluída com sucesso.\n")
            return


        atual = origem
        visitados = set()

        # Primeiro salto: se origem é host, avança para o switch e mostra
        if G.nodes[atual]['type'] == "host":
            vizinhos = list(G.neighbors(atual))
            proximo = vizinhos[0]  # Assume conexão direta
            
            probes = [total_delay + random.randint(2, 6) for _ in range(3)]
            print(f"{hop_num}: {proximo} ({G.nodes[proximo].get('ip', 'N/A')})   {'   '.join(str(p) + ' ms' for p in probes)}")
            total_delay = max(probes)
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
                    probes = [total_delay + random.randint(2, 6) for _ in range(3)]
                    print(f"{hop_num}: {destino} ({G.nodes[destino].get('ip', 'N/A')})   {'   '.join(str(p) + ' ms' for p in probes)}")
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
                                    probes = [total_delay + random.randint(2, 6) for _ in range(3)]
                                    total_delay = max(probes)
                                    ip = G.nodes[hop].get('ip', 'N/A')
                                    print(f"{hop_num}: {hop} ({ip})   {'   '.join(str(p) + ' ms' for p in probes)}")
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
                                    probes = [total_delay + random.randint(2, 6) for _ in range(3)]
                                    total_delay = max(probes)
                                    ip = G.nodes[hop].get('ip', 'N/A')
                                    print(f"{hop_num}: {hop} ({ip})   {'   '.join(str(p) + ' ms' for p in probes)}")
                                    hop_num += 1
                                    visitados.add(hop)

                            # Imprime o roteador alcançado
                            probes = [total_delay + random.randint(2, 6) for _ in range(3)]
                            total_delay = max(probes)
                            ip = G.nodes[vizinho].get('ip', 'N/A')
                            print(f"{hop_num}: {vizinho} ({ip})   {'   '.join(str(p) + ' ms' for p in probes)}")
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
                probes = [total_delay + random.randint(5, 15) for _ in range(3)]
                print(f"{hop_num}: {nh} ({G.nodes[nh].get('ip', 'N/A')})   {'   '.join(str(p) + ' ms' for p in probes)}")
                total_delay = max(probes)
                atual = nh
                hop_num += 1

        # Quando chega ao destino
        probes = [total_delay + random.randint(2, 5) for _ in range(3)]
        print(f"{hop_num}: {destino} ({destino_ip})   {'   '.join(str(p) + ' ms' for p in probes)}")
        print("\nRota concluída com sucesso.\n")

    except Exception as e:
        print(f"Erro durante o traceroute: {e}")





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

    # Hosts
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
        xping_routing_return(G, origem, destino, routing_tables)
        main()
    elif escolha == '2':
        print()
        origem = input("Digite o nó de origem (ex: h1, e1a, a1): ").strip()
        destino = input("Digite o nó de destino (ex: h2, e2a, a2): ").strip()
        xtraceroute_routing_probe(G, origem, destino, routing_tables)
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