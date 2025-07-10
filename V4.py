import networkx as nx
import matplotlib.pyplot as plt
import time
import random
import ipaddress


def get_node_ip(G, node, vizinho=None, default_mask="255.255.255.224"):
    ip = G.nodes[node].get('ip', 'N/A')
    if ip != 'N/A':
        return ip
    
    interfaces = G.nodes[node].get('interfaces')
    if not isinstance(interfaces, dict):
        return 'N/A'

    if vizinho:
        ip_viz = G.nodes[vizinho].get('ip', 'N/A')
        if ip_viz == 'N/A':
            ip_viz = get_node_ip(G, vizinho)

        for ip_iface in interfaces.values():
            try:
                if same_subnet(ip_viz, ip_iface, mask=default_mask):
                    return ip_iface
            except:
                continue

    return next(iter(interfaces.values()), 'N/A')


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
        import ipaddress
        net1 = ipaddress.IPv4Network(f"{ip1}/{mask}", strict=False)
        net2 = ipaddress.IPv4Network(f"{ip2}/{mask}", strict=False)
        return net1.network_address == net2.network_address
    except Exception:
        return False
"""
def find_path_same_subnet(G, origem, destino):
    # Retorna o caminho mais curto entre origem e destino considerando só hosts e switches (sem roteadores)
    subgraph_nodes = [n for n in G.nodes if G.nodes[n]['type'] in ('host','switch')]
    SG = G.subgraph(subgraph_nodes)
    try:
        return nx.shortest_path(SG, origem, destino)
    except:
        return None
"""

def find_path_same_subnet(G, origem, destino):
    # Permite hosts, switches e roteadores no caminho
    subgraph_nodes = [n for n in G.nodes if G.nodes[n]['type'] in ('host','switch','router')]
    SG = G.subgraph(subgraph_nodes)
    try:
        return nx.shortest_path(SG, origem, destino)
    except:
        return None
"""
def next_hop(router, destino_ip, routing_tables):
    table = routing_tables.get(router, {})
    for subnet, neighbor in table.items():
        if ipaddress.IPv4Address(destino_ip) in ipaddress.IPv4Network(subnet):
            return neighbor
    return None  # Default route (se quiser implementar depois)
"""

def next_hop(router, destino_ip, routing_tables):
    table = routing_tables.get(router, {})
    for subnet, neighbor in table.items():
        try:
            net = ipaddress.IPv4Network(subnet)
            if ipaddress.IPv4Address(destino_ip) in net:
                return neighbor
        except Exception as e:
            print(f"[DEBUG] ⚠️ Erro analisando subnet {subnet}: {e}")
    print(f"[DEBUG] → Nenhuma rota encontrada para {destino_ip}")
    return None 


def xping_routing_return_routers(G, origem, destino, routing_tables, subnet_mask="255.255.255.224"):
    def caminho_mesma_subnet(G, start, end):
        atual = start
        visitados = set()
        hops = []

        if G.nodes[atual]['type'] == "host":
            vizinhos = list(G.neighbors(atual))
            if not vizinhos:
                return None
            anterior = atual
            atual = vizinhos[0]
            hops.append((atual, get_node_ip(G, atual, anterior)))
            visitados.add(start)
        else:
            anterior = None

        while atual != end:
            if atual in visitados:
                return None
            visitados.add(atual)

            if end in G.neighbors(atual):
                hops.append((end, get_node_ip(G, end, atual)))
                break

            avancou = False
            for viz in G.neighbors(atual):
                if viz not in visitados and G.nodes[viz]['type'] in ("switch", "host"):
                    anterior = atual
                    atual = viz
                    hops.append((atual, get_node_ip(G, atual, anterior)))
                    avancou = True
                    break
            if not avancou:
                return None
        return hops
    """
    def caminho_valido(G, start, end, routing_tables):
        destino_ip = get_node_ip(G, end)  # IP genérico do destino
        
        atual = start
        visitados = set()
        hops = []

        ip_start = get_node_ip(G, start)
        ip_end = destino_ip

        if same_subnet(ip_start, ip_end, subnet_mask):
            return caminho_mesma_subnet(G, start, end)

        if G.nodes[atual]['type'] == "host":
            vizinhos = list(G.neighbors(atual))
            if not vizinhos:
                return None
            anterior = atual
            atual = vizinhos[0]
            hops.append((atual, get_node_ip(G, atual, anterior)))
            visitados.add(start)
        else:
            anterior = None

        while atual != end:
            if atual in visitados:
                return None
            visitados.add(atual)

            tipo_atual = G.nodes[atual]['type']

            # Só considera vizinho direto se atual for switch ou host
            if tipo_atual in ("switch", "host") and end in G.neighbors(atual):
                hops.append((end, get_node_ip(G, end, atual)))
                break

            if tipo_atual == "switch":
                encaminhado = False
                for viz in G.neighbors(atual):
                    tipo_viz = G.nodes[viz]['type']
                    if tipo_viz in ("router", "switch") and viz not in visitados:
                        anterior = atual
                        atual = viz
                        hops.append((atual, get_node_ip(G, atual, anterior)))
                        encaminhado = True
                        break
                if not encaminhado:
                    return None

            elif tipo_atual == "router":
                if end in G.neighbors(atual):
                    # Destino é vizinho direto do roteador
                    hops.append((end, get_node_ip(G, end, atual)))
                    break
                nh = next_hop(atual, destino_ip, routing_tables)
                if not nh:
                    return None
                anterior = atual
                atual = nh
                hops.append((atual, get_node_ip(G, atual, anterior)))

            elif tipo_atual == "host":
                return None

        return hops
    """
    def caminho_valido(G, start, end, routing_tables):
        destino_ip = get_node_ip(G, end)
        ip_start = get_node_ip(G, start)

        visitados = set()
        stack = [(start, [], None)]  # (nó atual, caminho acumulado, nó anterior)

        while stack:
            atual, hops, anterior = stack.pop()

            if atual in visitados:
                continue
            visitados.add(atual)

            novo_hops = hops.copy()
            if anterior is not None:
                novo_hops.append((atual, get_node_ip(G, atual, anterior)))

            if atual == end:
                return novo_hops

            tipo_atual = G.nodes[atual]['type']

            # Destino vizinho direto (host/switch)
            if end in G.neighbors(atual):
                novo_hops.append((end, get_node_ip(G, end, atual)))
                return novo_hops

            if tipo_atual == "host":
                for viz in G.neighbors(atual):
                    if viz not in visitados:
                        stack.append((viz, novo_hops, atual))

            elif tipo_atual == "switch":
                for viz in G.neighbors(atual):
                    if viz not in visitados and G.nodes[viz]['type'] in ("switch", "router", "host"):
                        stack.append((viz, novo_hops, atual))

            elif tipo_atual == "router":
                nh = next_hop(atual, destino_ip, routing_tables)
                if nh and nh not in visitados:
                    stack.append((nh, novo_hops, atual))
                elif end in G.neighbors(atual):
                    novo_hops.append((end, get_node_ip(G, end, atual)))
                    return novo_hops
        print(f"[DEBUG] Caminho de {start} para {end} não encontrado.")
        return None


    caminho_ida = caminho_valido(G, origem, destino, routing_tables)
    if caminho_ida is None:
        print(f"Ping de {origem} para {destino}: Falha no caminho de ida.")
        return

    caminho_volta = caminho_valido(G, destino, origem, routing_tables)
    if caminho_volta is None:
        print(f"Ping de {origem} para {destino}: Falha no caminho de volta.")
        return
    
    if len(caminho_ida) >= 2:
        ip_destino = get_node_ip(G, destino, caminho_ida[-2][0])
    else:
        ip_destino = get_node_ip(G, destino)

    print(f"Ping de {origem} ({get_node_ip(G, origem)}) para {destino} ({ip_destino}) - Sucesso")
    print("Caminho (ida):")
    for hop, ip in caminho_ida:
        print(f" -> {hop} ({ip})")
    print("Caminho (volta):")
    for hop, ip in caminho_volta:
        print(f" -> {hop} ({ip})")
    print(f"Resposta de {destino}: Sucesso\n")


def xtraceroute_routing_probe_updated(G, origem, destino, routing_tables):
    try:
        destino_ip = get_node_ip(G, destino)
        origem_ip = get_node_ip(G, origem)
        total_delay = 0
        hop_num = 1

        print(f"XTraceroute de {origem} ({origem_ip}) até {destino} ({destino_ip})")
        print("Saltos:")

        if same_subnet(origem_ip, destino_ip):
            path = find_path_same_subnet(G, origem, destino)
            if path is None:
                print(f"⚠️ Nenhum caminho direto na subrede entre {origem} e {destino}")
                return
            anterior = origem
            for hop in path[1:]:  # pula origem
                probes = [random.randint(2, 6) for _ in range(3)]
                total_delay = max(probes)
                ip = get_node_ip(G, hop, anterior)
                print(f"{hop_num}: {hop} ({ip})   {'   '.join(str(p) + ' ms' for p in probes)}")
                hop_num += 1
                anterior = hop
            print("\nRota concluída com sucesso.\n")
            return

        atual = origem
        visitados = set()
        anterior = None

        if G.nodes[atual]['type'] == "host":
            vizinhos = list(G.neighbors(atual))
            proximo = vizinhos[0]
            ip = get_node_ip(G, proximo, atual)
            probes = [random.randint(2, 6) for _ in range(3)]
            total_delay = max(probes)
            print(f"{hop_num}: {proximo} ({ip})   {'   '.join(str(p) + ' ms' for p in probes)}")
            hop_num += 1
            anterior = atual
            atual = proximo
            visitados.add(anterior)

        while atual != destino:
            if atual in visitados and G.nodes[atual]['type'] != "router":
                print(f"⚠️ Roteamento em loop detectado em {atual}. Encerrando.")
                return
            visitados.add(atual)

            tipo_atual = G.nodes[atual]['type']

            if tipo_atual == "switch":
                if destino in G.neighbors(atual):
                    ip = get_node_ip(G, destino, atual)
                    probes = [total_delay + random.randint(2, 6) for _ in range(3)]
                    print(f"{hop_num}: {destino} ({ip})   {'   '.join(str(p) + ' ms' for p in probes)}")
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
                            anterior = caminho[-1]
                            for hop in caminho[1:] + [vizinho]:
                                if hop not in visitados:
                                    ip = get_node_ip(G, hop, anterior)
                                    probes = [total_delay + random.randint(2, 6) for _ in range(3)]
                                    total_delay = max(probes)
                                    print(f"{hop_num}: {hop} ({ip})   {'   '.join(str(p) + ' ms' for p in probes)}")
                                    hop_num += 1
                                    visitados.add(hop)
                                    anterior = hop
                            print("\nRota concluída com sucesso.\n")
                            return

                        if tipo == "switch":
                            fila.append((vizinho, caminho + [vizinho]))

                        if tipo == "router" and vizinho not in visitados:
                            anterior = caminho[-1]
                            for hop in caminho[1:]:
                                if hop not in visitados:
                                    ip = get_node_ip(G, hop, anterior)
                                    probes = [total_delay + random.randint(2, 6) for _ in range(3)]
                                    total_delay = max(probes)
                                    print(f"{hop_num}: {hop} ({ip})   {'   '.join(str(p) + ' ms' for p in probes)}")
                                    hop_num += 1
                                    visitados.add(hop)
                                    anterior = hop

                            ip = get_node_ip(G, vizinho, anterior)
                            probes = [total_delay + random.randint(5, 15) for _ in range(3)]
                            total_delay = max(probes)
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

            elif tipo_atual == "router":
                nh = next_hop(atual, destino_ip, routing_tables)
                if not nh:
                    print(f"Sem rota de {atual} para {destino_ip}")
                    return
                ip = get_node_ip(G, nh, atual)
                probes = [total_delay + random.randint(5, 15) for _ in range(3)]
                total_delay = max(probes)
                print(f"{hop_num}: {nh} ({ip})   {'   '.join(str(p) + ' ms' for p in probes)}")
                atual = nh
                hop_num += 1
        if atual != destino:
            probes = [total_delay + random.randint(2, 5) for _ in range(3)]
            ip = get_node_ip(G, destino, atual)
            print(f"{hop_num}: {destino} ({ip})   {'   '.join(str(p) + ' ms' for p in probes)}")
            print("\nRota concluída com sucesso.\n")
        else:
            print("\nRota concluída com sucesso.\n")

    except Exception as e:
        print(f"Erro durante o traceroute: {e}")


def main():

    G = nx.Graph()
    # Hosts
    G.add_node("h1", type="host", ip="172.16.0.3")
    G.add_node("h2", type="host", ip="172.16.0.19")
    G.add_node("h3", type="host", ip="172.16.0.67")
    G.add_node("h4", type="host", ip="172.16.0.83")
    G.add_node("h5", type="host", ip="172.16.1.131")
    G.add_node("h6", type="host", ip="172.16.1.132")
    G.add_node("h7", type="host", ip="172.16.1.163")
    G.add_node("h8", type="host", ip="172.16.1.164")

    # Switches
    G.add_node("e1a", type="switch", ip="172.16.0.2")
    G.add_node("e1b", type="switch", ip="172.16.0.18")
    G.add_node("e2a", type="switch", ip="172.16.0.66")
    G.add_node("e2b", type="switch", ip="172.16.0.82")
    G.add_node("e3", type="switch", ip="172.16.1.130")
    G.add_node("e4", type="switch", ip="172.16.1.162")

    # Roteadores
    G.add_node("a1", type="router", ip="N/A", interfaces={ "a1-c1": "172.16.2.65", "a1-e1a": "172.16.0.1", "a1-e2a": "172.16.0.65"})  # interface para C1
    G.add_node("a2", type="router", ip="N/A", interfaces={ "a2-c1": "172.16.2.69", "a2-e3": "172.16.1.129", "a2-e4": "172.16.1.161"})  # interface para C1
    G.add_node("c1", type="router", ip="N/A", interfaces={ "c1-a1": "172.16.2.66", "c1-a2": "172.16.2.70"})  # tem duas interfaces: 172.16.2.66 e 172.16.2.70

    # Conexões entre roteadores
    G.add_edge("c1", "a1", type="serial", subnet="172.16.2.64/30")  # C1=66, A1=65
    G.add_edge("c1", "a2", type="serial", subnet="172.16.2.68/30")  # C1=70, A2=69

    # Conexões entre roteadores e switches
    G.add_edge("a1", "e1a", type="ethernet", subnet="172.16.0.0/26")  # e1a: 2, gw: 1
    G.add_edge("a1", "e2a", type="ethernet", subnet="172.16.0.64/26")  # e2a: 66, gw: 65
    G.add_edge("a2", "e3", type="ethernet", subnet="172.16.1.128/27")  # e3: 130, gw: 129
    G.add_edge("a2", "e4", type="ethernet", subnet="172.16.1.160/27")  # e4: 162, gw: 161

    # Conexões hosts e switches
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


    # Tabela de Roteamento

    routing_tables = {
    "a1": {
        "172.16.0.0/26": "e1a",
        "172.16.0.64/26": "e2a",
        "172.16.1.128/27": "c1",
        "172.16.1.160/27": "c1",
        "172.16.2.64/30": "c1",
        "172.16.2.68/30": "c1",  # <- adicione esta linha!
    },
    "a2": {
        "172.16.1.128/27": "e3",  # h5, h6
        "172.16.1.160/27": "e4",  # h7, h8
        "172.16.0.0/26": "c1",    # via C1 para A1
        "172.16.0.64/26": "c1",
        "172.16.2.68/30": "c1",
        "172.16.2.64/30": "c1",
    },
    "c1": {
        "172.16.0.0/26": "a1",
        "172.16.0.64/26": "a1",
        "172.16.1.128/27": "a2",
        "172.16.1.160/27": "a2",
        "172.16.2.64/30": "a1",
        "172.16.2.68/30": "a2",
        
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
        xping_routing_return_routers(G, origem, destino, routing_tables)
        main()
    elif escolha == '2':
        print()
        origem = input("Digite o nó de origem (ex: h1, e1a, a1): ").strip()
        destino = input("Digite o nó de destino (ex: h2, e2a, a2): ").strip()
        xtraceroute_routing_probe_updated(G, origem, destino, routing_tables)
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
    elif escolha == '5':
        print()
        run_all_possible_traceroutes(G, routing_tables)
        main()
    elif escolha == '6':
        print()
        run_all_possible_pings(G, routing_tables)
        main()
    else:
        print()
        print("Opção inválida. Por favor, escolha 1, 2, 3 ou 4.")

def run_all_possible_traceroutes(G, routing_tables):
    nodes = list(G.nodes)
    for origem in nodes:
        for destino in nodes:
            if origem != destino:
                print(f"\n--- Traceroute de {origem} para {destino} ---")
                xtraceroute_routing_probe_updated(G, origem, destino, routing_tables)
                input()

def run_all_possible_pings(G, routing_tables):
    nodes = list(G.nodes)
    for origem in nodes:
        for destino in nodes:
            if origem != destino:
                print(f"\n--- Ping de {origem} para {destino} ---")
                xping_routing_return_routers(G, origem, destino, routing_tables)
                input()


if __name__ == "__main__":
    main()
