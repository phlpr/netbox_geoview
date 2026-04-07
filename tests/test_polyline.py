import unittest

from netbox_geoview.polyline import decode_polyline


class DecodePolylineTests(unittest.TestCase):
    def test_empty_string_returns_empty_list(self):
        self.assertEqual(decode_polyline(""), [])

    def test_decodes_zero_coordinate(self):
        self.assertEqual(decode_polyline("??"), [[0.0, 0.0]])

    def test_decodes_small_positive_coordinate_precision_6(self):
        self.assertEqual(decode_polyline("AA"), [[0.000001, 0.000001]])

    def test_truncated_input_returns_decoded_prefix_only(self):
        self.assertEqual(decode_polyline("??A"), [[0.0, 0.0]])


if __name__ == "__main__":
    unittest.main()
