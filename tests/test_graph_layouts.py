import importlib.util
import os
import sys
import unittest

# load draw_graphs module
MODULE_PATH = os.path.join(os.path.dirname(__file__), os.pardir, 'draw_graphs.py')
spec = importlib.util.spec_from_file_location('draw_graphs', MODULE_PATH)
draw_graphs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(draw_graphs)
compute_coordinates = draw_graphs.compute_coordinates

import networkx as nx

class TestGraphLayouts(unittest.TestCase):
    def test_all_layouts(self):
        G = nx.DiGraph()
        G.add_edge('a', 'b')
        for layout in ['dot', 'neato', 'sfdp', 'spring', 'kamada_kawai']:
            coords = compute_coordinates(G, layout=layout, k=1.0)
            self.assertEqual(set(coords.keys()), set(G.nodes))

if __name__ == '__main__':
    unittest.main()
