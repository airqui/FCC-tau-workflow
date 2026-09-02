import random
import unittest

from fcc_tau_workflow.truthlink_assignment import (
    ASSIGNED,
    ORPHAN_AMBIGUOUS,
    ORPHAN_NO_RELATION,
    TruthCandidate,
    assign_truth_to_pfo,
    decode_packed_weight,
)


def candidate(mc, *, t=0, c=0, charge=1.0, pdg=211):
    return TruthCandidate.from_packed(
        mc_index=mc,
        pdg=pdg,
        charge=charge,
        generator_status=1,
        created_in_simulation=False,
        raw_weight=10000 * c + t,
    )


class TruthlinkAssignmentTest(unittest.TestCase):
    def test_one_track_candidate(self):
        result = assign_truth_to_pfo([candidate(1, t=200, c=100)])
        self.assertEqual((result.status, result.candidate.mc_index), (ASSIGNED, 1))

    def test_track_beats_stronger_cluster_only_candidate(self):
        result = assign_truth_to_pfo([
            candidate(1, t=200, c=100),
            candidate(2, t=0, c=1000, charge=0),
        ])
        self.assertEqual(result.candidate.mc_index, 1)

    def test_different_track_components(self):
        result = assign_truth_to_pfo([candidate(1, t=200), candidate(2, t=300)])
        self.assertEqual(result.candidate.mc_index, 2)

    def test_track_tie_resolved_by_cluster(self):
        result = assign_truth_to_pfo([
            candidate(1, t=300, c=100), candidate(2, t=300, c=200)
        ])
        self.assertEqual(result.candidate.mc_index, 2)
        self.assertEqual(result.decision_branch, "track_maxT_then_maxC")

    def test_track_and_cluster_exact_tie_is_ambiguous(self):
        result = assign_truth_to_pfo([
            candidate(1, t=300, c=200), candidate(2, t=300, c=200)
        ])
        self.assertEqual(result.status, ORPHAN_AMBIGUOUS)

    def test_cluster_maximum(self):
        result = assign_truth_to_pfo([
            candidate(1, c=100, charge=1), candidate(2, c=200, charge=1)
        ])
        self.assertEqual(result.candidate.mc_index, 2)

    def test_cluster_tie_neutral_wins(self):
        result = assign_truth_to_pfo([
            candidate(1, c=500, charge=1), candidate(2, c=500, charge=0)
        ])
        self.assertEqual(result.candidate.mc_index, 2)
        self.assertTrue(result.neutral_tiebreak_used)

    def test_cluster_tie_two_neutrals_is_ambiguous(self):
        result = assign_truth_to_pfo([
            candidate(1, c=500, charge=0), candidate(2, c=500, charge=0)
        ])
        self.assertEqual(result.status, ORPHAN_AMBIGUOUS)

    def test_cluster_tie_two_charged_is_ambiguous(self):
        result = assign_truth_to_pfo([
            candidate(1, c=500, charge=1), candidate(2, c=500, charge=-1)
        ])
        self.assertEqual(result.status, ORPHAN_AMBIGUOUS)

    def test_no_relation(self):
        self.assertEqual(assign_truth_to_pfo([]).status, ORPHAN_NO_RELATION)

    def test_packed_zero_relation_is_still_a_relation(self):
        result = assign_truth_to_pfo([candidate(7, t=0, c=0, charge=0)])
        self.assertEqual((result.status, result.candidate.mc_index), (ASSIGNED, 7))
        self.assertEqual(decode_packed_weight(0), (0, 0, 0))

    def test_order_invariance(self):
        base = [
            candidate(1, t=200, c=100),
            candidate(2, t=300, c=100),
            candidate(3, t=300, c=900),
            candidate(4, t=0, c=1000, charge=0),
        ]
        expected = assign_truth_to_pfo(base)
        for seed in range(30):
            shuffled = list(base)
            random.Random(seed).shuffle(shuffled)
            self.assertEqual(assign_truth_to_pfo(shuffled), expected)

    def test_nonintegral_packed_weight_rejected(self):
        with self.assertRaises(ValueError):
            decode_packed_weight(1.25)

    def test_duplicate_mc_candidate_rejected(self):
        with self.assertRaises(ValueError):
            assign_truth_to_pfo([candidate(1, t=1), candidate(1, c=2)])


if __name__ == "__main__":
    unittest.main()
