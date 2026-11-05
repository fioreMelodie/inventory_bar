from django.test import SimpleTestCase

from .algorithms import (binary_search, bubble_sort, greedy_change, insertion_sort,
                         knapsack_01, lexicographically_greatest, quick_sort)


class AcademicAlgorithmsTests(SimpleTestCase):
    def test_sorting_algorithms_sort_without_mutating_input(self):
        values = [{"value": 3}, {"value": 1}, {"value": 2}]
        for algorithm in (bubble_sort, insertion_sort, quick_sort):
            self.assertEqual([item["value"] for item in algorithm(values, lambda item: item["value"])], [1, 2, 3])
        self.assertEqual([item["value"] for item in values], [3, 1, 2])

    def test_binary_search_returns_position_or_not_found(self):
        values = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
        self.assertEqual(binary_search(values, "b", lambda item: item["name"]), 1)
        self.assertEqual(binary_search(values, "x", lambda item: item["name"]), -1)

    def test_greedy_change_and_lexicographic_greedy(self):
        breakdown, remaining = greedy_change(1750, (1000, 500, 200, 50))
        self.assertEqual(breakdown, [{"denomination": 1000, "count": 1}, {"denomination": 500, "count": 1}, {"denomination": 200, "count": 1}, {"denomination": 50, "count": 1}])
        self.assertEqual(remaining, 0)
        self.assertEqual(lexicographically_greatest("cab"), "cab")

    def test_knapsack_selects_best_feasible_items(self):
        selected, benefit = knapsack_01([
            {"name": "A", "weight": 2, "benefit": 3},
            {"name": "B", "weight": 3, "benefit": 4},
            {"name": "C", "weight": 4, "benefit": 5},
        ], 5)
        self.assertEqual([item["name"] for item in selected], ["A", "B"])
        self.assertEqual(benefit, 7)
