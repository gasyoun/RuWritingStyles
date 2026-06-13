"""get_cluster_weights de-regioning (prompt-fidelity review F5)."""

import unittest
from pathlib import Path

from ruwritingstyles.config import CouncilArchetype, load_manifest
from ruwritingstyles.council import get_cluster_weights

REPO_ROOT = Path(__file__).resolve().parents[1]


class DeRegionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load_manifest(REPO_ROOT)
        loc = {c.id: c.location for c in self.manifest.clusters}
        # A passport whose cluster is tagged exactly "Moscow" — the city that the
        # old location-string boost doubled under a Moscow archetype.
        self.target = next(
            p for p in self.manifest.passports if loc.get(p.cluster_id) == "Moscow"
        )

    def _moscow_archetype(self, weights=None) -> CouncilArchetype:
        return CouncilArchetype(
            id="m", name="Moscow School", description="", instructions="",
            weights=weights or {},
        )

    def test_location_no_longer_boosts_weight(self) -> None:
        # text_domain="unknown" -> no domain/method boost fires; with empty
        # archetype weights the result must equal the base weight (it was base*2.0
        # before de-region, from the Moscow-location boost).
        weights = get_cluster_weights(self.manifest, "unknown", self._moscow_archetype())
        self.assertEqual(weights[self.target.style_id], self.target.weight)

    def test_explicit_archetype_cluster_weight_still_applies(self) -> None:
        # Deliberate cluster boosting via archetype weights still works (and is no
        # longer silently doubled by geography).
        arch = self._moscow_archetype(weights={self.target.cluster_id: 3.0})
        weights = get_cluster_weights(self.manifest, "unknown", arch)
        self.assertEqual(weights[self.target.style_id], 3.0)


if __name__ == "__main__":
    unittest.main()
