import requests


def get_nodes():
    url = "https://bitnodes.earn.com/api/v1/snapshots/latest/"
    response = requests.get(url)
    return response.json()["nodes"]


def nodes_to_address_tuples(nodes):
    address_strings = nodes.keys()
    address_tuples = []
    for address_string in address_strings:
        ip, port = address_string.rsplit(":", 1)

        # FIXME
        ip = ip.replace("[", "").replace("]", "")

        address_tuple = (ip, int(port))
        address_tuples.append(address_tuple)
    return address_tuples


def get_addresses():
    nodes = get_nodes()
    address_tuples = nodes_to_address_tuples(nodes)
    return address_tuples
