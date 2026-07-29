"""Per-domain cluster authority table (H1479: roadmap G-04 + L-03 wired in).

Pins the three properties the drafted tables were written for and the 3-case
shortcut could not express: a domain-matched school is boosted, a
methodologically mute one is *suppressed* below its base weight, and a school
the row does not name stays exactly neutral.
"""

import unittest
from pathlib import Path

from ruwritingstyles.config import CouncilArchetype, load_manifest
from ruwritingstyles.council import (
    DOMAIN_CLUSTER_WEIGHTS,
    domain_cluster_multiplier,
    get_cluster_weights,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


class DomainClusterWeightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load_manifest(REPO_ROOT)
        # The cluster-level passport for each cluster id (level: cluster in the
        # manifest sets cluster_id == style_id), used to read a base weight.
        self.by_cluster = {
            ref.cluster_id: ref
            for ref in self.manifest.passports
            if ref.cluster_id == ref.style_id
        }

    def _base(self, cluster_id: str) -> float:
        return self.by_cluster[cluster_id].weight

    def _weight_of(self, weights: dict[str, float], cluster_id: str) -> float:
        return weights[self.by_cluster[cluster_id].style_id]

    # --- the acceptance criterion, mechanically enforced --------------------

    def test_every_declared_cluster_domain_has_a_table_row(self) -> None:
        """Coverage is the point of H1479: no cluster may declare a `domains`
        value that falls through to the coarse generic boost."""
        declared = {
            (cluster.id, domain)
            for cluster in self.manifest.clusters
            for domain in cluster.domains
        }
        self.assertTrue(declared, "no cluster declares domains — fixture broke")
        missing = sorted(
            f"{cluster_id}:{domain}"
            for cluster_id, domain in declared
            if domain not in DOMAIN_CLUSTER_WEIGHTS
        )
        self.assertEqual(missing, [])

    def test_every_table_cluster_id_exists(self) -> None:
        known = {cluster.id for cluster in self.manifest.clusters}
        unknown = sorted(
            f"{domain}:{key}"
            for domain, row in DOMAIN_CLUSTER_WEIGHTS.items()
            for key in row
            if not key.endswith("*") and key not in known
        )
        self.assertEqual(unknown, [])

    # --- boost / suppress / neutral ----------------------------------------

    def test_domain_matched_cluster_is_boosted(self) -> None:
        weights = get_cluster_weights(self.manifest, "literary_poststructural")
        self.assertAlmostEqual(
            self._weight_of(weights, "lit_poststructural"),
            self._base("lit_poststructural") * 2.0,
        )

    def test_domain_mismatched_cluster_is_suppressed(self) -> None:
        """The normativist has almost no voice on poststructuralism (L-03: 0.1)."""
        weights = get_cluster_weights(self.manifest, "literary_poststructural")
        suppressed = self._weight_of(weights, "ling_nss")
        self.assertAlmostEqual(suppressed, self._base("ling_nss") * 0.1)
        self.assertLess(suppressed, self._base("ling_nss"))
        self.assertLess(suppressed, self._weight_of(weights, "lit_poststructural"))

    def test_cluster_absent_from_row_stays_neutral(self) -> None:
        weights = get_cluster_weights(self.manifest, "literary_poststructural")
        self.assertAlmostEqual(
            self._weight_of(weights, "ling_dss"), self._base("ling_dss")
        )

    def test_unknown_domain_leaves_every_weight_at_base(self) -> None:
        weights = get_cluster_weights(self.manifest, "unknown")
        for ref in self.manifest.passports:
            self.assertAlmostEqual(weights[ref.style_id], ref.weight, msg=ref.style_id)

    def test_undocumented_domain_leaves_every_weight_at_base(self) -> None:
        """`linguistics`/`lexicography` (used by the eval suite) are deliberately
        unrowed, and no cluster declares them — so nothing may shift."""
        for domain in ("linguistics", "lexicography"):
            self.assertNotIn(domain, DOMAIN_CLUSTER_WEIGHTS)
            weights = get_cluster_weights(self.manifest, domain)
            for ref in self.manifest.passports:
                self.assertAlmostEqual(
                    weights[ref.style_id], ref.weight, msg=f"{domain}/{ref.style_id}"
                )

    # --- composition with the mechanisms already in production -------------

    def test_table_row_is_authoritative_no_double_count(self) -> None:
        """ling_iesh declares `etymology`, so the generic x1.5 would also match;
        the row must win outright instead of compounding to x3.0."""
        weights = get_cluster_weights(self.manifest, "etymology")
        self.assertAlmostEqual(
            self._weight_of(weights, "ling_iesh"), self._base("ling_iesh") * 1.5
        )

    def test_etymology_authority_ratio_preserved(self) -> None:
        """Pre-table code gave iesh 3.0 vs nss 1.0; G-04 gives 1.5 vs 0.5. The
        absolute numbers drop, the 3x relative authority does not."""
        weights = get_cluster_weights(self.manifest, "etymology")
        ratio = self._weight_of(weights, "ling_iesh") / self._weight_of(weights, "ling_nss")
        self.assertAlmostEqual(ratio, 3.0)

    def test_semiotics_keeps_its_pre_table_multiplier(self) -> None:
        weights = get_cluster_weights(self.manifest, "semiotics")
        self.assertAlmostEqual(
            self._weight_of(weights, "ling_mts"), self._base("ling_mts") * 2.0
        )

    def test_literature_prefix_wildcard_still_covers_every_lit_cluster(self) -> None:
        weights = get_cluster_weights(self.manifest, "literature")
        lit_clusters = [c.id for c in self.manifest.clusters if c.id.startswith("lit_")]
        self.assertGreater(len(lit_clusters), 1)
        for cluster_id in lit_clusters:
            self.assertAlmostEqual(
                self._weight_of(weights, cluster_id),
                self._base(cluster_id) * 1.2,
                msg=cluster_id,
            )
        self.assertAlmostEqual(
            self._weight_of(weights, "ling_nss"), self._base("ling_nss")
        )

    def test_archetype_override_supplies_the_base_the_row_scales(self) -> None:
        archetype = CouncilArchetype(
            id="p", name="Poststructural", description="", instructions="",
            weights={"ling_nss": 3.0},
        )
        weights = get_cluster_weights(self.manifest, "literary_poststructural", archetype)
        self.assertAlmostEqual(self._weight_of(weights, "ling_nss"), 3.0 * 0.1)

    # --- the lookup helper --------------------------------------------------

    def test_multiplier_helper_precedence(self) -> None:
        self.assertEqual(domain_cluster_multiplier("etymology", "ling_iesh"), 1.5)
        self.assertEqual(domain_cluster_multiplier("etymology", "ling_dss"), 1.0)
        self.assertEqual(domain_cluster_multiplier("unknown", "ling_iesh"), 1.0)
        self.assertEqual(domain_cluster_multiplier("etymology", None), 1.0)
        # exact id beats the prefix wildcard in the same row
        self.assertEqual(domain_cluster_multiplier("literature", "lit_bakhtin"), 1.2)
        self.assertEqual(domain_cluster_multiplier("literature", "ling_iesh"), 1.0)

    def test_no_row_is_empty_and_all_multipliers_are_positive(self) -> None:
        for domain, row in DOMAIN_CLUSTER_WEIGHTS.items():
            self.assertTrue(row, msg=domain)
            for key, value in row.items():
                self.assertGreater(value, 0.0, msg=f"{domain}:{key}")


if __name__ == "__main__":
    unittest.main()
