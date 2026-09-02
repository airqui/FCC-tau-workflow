import unittest

from fcc_tau_workflow.truthlink_ancestor_assignment import assign_selected_ancestor


class AncestorAssignmentTest(unittest.TestCase):
    def assert_assignment(self, result, status, index, depth):
        self.assertEqual(result.status, status)
        self.assertEqual(result.assigned_mc_index, index)
        self.assertEqual(result.ancestor_depth, depth)

    def test_direct_selected(self):
        result = assign_selected_ancestor("assigned", 0, [[], []], {0})
        self.assert_assignment(result, "same_direct_selected", 0, 0)

    def test_selected_parent(self):
        result = assign_selected_ancestor("assigned", 1, [[], [0]], {0})
        self.assert_assignment(result, "promoted_unique_ancestor", 0, 1)

    def test_selected_grandparent(self):
        result = assign_selected_ancestor("assigned", 2, [[], [0], [1]], {0})
        self.assert_assignment(result, "promoted_unique_ancestor", 0, 2)

    def test_two_selected_at_same_depth_are_ambiguous(self):
        result = assign_selected_ancestor("assigned", 2, [[], [], [0, 1]], {0, 1})
        self.assert_assignment(result, "ancestor_orphan_ambiguous", None, 1)
        self.assertEqual(result.n_selected_at_nearest_depth, 2)

    def test_nearer_selected_wins(self):
        result = assign_selected_ancestor("assigned", 2, [[], [0], [1]], {0, 1})
        self.assert_assignment(result, "promoted_unique_ancestor", 1, 1)

    def test_ancestor_no_selected_ancestor(self):
        result = assign_selected_ancestor("assigned", 1, [[], [0]], set())
        self.assert_assignment(result, "ancestor_no_selected_ancestor", None, None)

    def test_order_invariant(self):
        left = assign_selected_ancestor("assigned", 2, [[], [], [0, 1]], {0, 1})
        right = assign_selected_ancestor("assigned", 2, [[], [], [1, 0]], {0, 1})
        self.assertEqual(left, right)

    def test_loop_protection(self):
        with self.assertRaisesRegex(ValueError, "cycle"):
            assign_selected_ancestor("assigned", 0, [[1], [0]], set())


if __name__ == "__main__":
    unittest.main()
