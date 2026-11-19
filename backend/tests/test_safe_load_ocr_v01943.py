from unittest.mock import patch
from app.services.safe_load_images import _neural_lines


def test_neural_lines_keep_separate_name_rows():
    class FakeEngine:
        def __call__(self, array):
            return ([
                ([[10,10],[100,10],[100,25],[10,25]], '1 ALLEN', .98),
                ([[10,35],[100,35],[100,50],[10,50]], '2 THOM', .99),
            ], None)
    import numpy as np
    assert _neural_lines(FakeEngine(), np.zeros((80,120,3), dtype=np.uint8)) == '1 ALLEN\n2 THOM'
