

def call_bitnodes_api(url):
    return requests.get(url).json()

def get_nodes(url):
    data = requests.get(url).json()
    return data['nodes']

