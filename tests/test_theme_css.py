import unittest
from pathlib import Path


CSS_PATH = (
    Path(__file__).parents[1]
    / "netbox_geoview"
    / "static"
    / "netbox_geoview"
    / "geoview.css"
)


class ThemeStylesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = CSS_PATH.read_text(encoding="utf-8")

    def test_uses_netbox_tabler_theme_variables(self):
        self.assertNotIn("var(--bs-", self.css)
        self.assertIn("var(--tblr-body-bg)", self.css)
        self.assertIn("var(--tblr-bg-surface)", self.css)

    def test_leaflet_popup_is_bound_to_netbox_theme(self):
        self.assertIn(".leaflet-popup-content-wrapper", self.css)
        self.assertIn(".leaflet-popup-tip", self.css)
        self.assertIn("color: var(--tblr-body-color);", self.css)


if __name__ == "__main__":
    unittest.main()
