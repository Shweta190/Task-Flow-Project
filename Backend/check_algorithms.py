"""Self-test script for algorithms.py  run: python check_algorithms.py"""

from algorithms import (
    insertion_sort,
    insertion_sort_count,
    binary_search,
    binary_search_count,
    linear_search,
    linear_search_count,
)


def run_tests():
    passed = 0
    failed = 0

    def check(condition, label, expected=None, got=None):
        nonlocal passed, failed
        if condition:
            print(f"PASS: {label}")
            passed += 1
        else:
            print(f"FAIL: {label} — expected {expected}, got {got}")
            failed += 1

    # Test 1: insertion_sort on empty list
    data = []
    insertion_sort(data, "val")
    check(data == [], "insertion_sort empty list", [], data)

    # Test 2: insertion_sort on 1 element
    data = [{"val": 5}]
    insertion_sort(data, "val")
    check(data == [{"val": 5}], "insertion_sort single element", [{"val": 5}], data)

    # Test 3: binary_search finds element at start
    data = [{"val": 1}, {"val": 3}, {"val": 5}, {"val": 7}, {"val": 9}]
    result = binary_search(data, 1, "val")
    check(result == 0, "binary_search at start", 0, result)

    # Test 4: binary_search finds element at end
    data = [{"val": 1}, {"val": 3}, {"val": 5}, {"val": 7}, {"val": 9}]
    result = binary_search(data, 9, "val")
    check(result == 4, "binary_search at end", 4, result)

    # Test 5: binary_search element not found
    data = [{"val": 1}, {"val": 3}, {"val": 5}, {"val": 7}, {"val": 9}]
    result = binary_search(data, 4, "val")
    check(result == -1, "binary_search not found", -1, result)

    # Test 6: insertion_sort_count returns int
    data = [{"val": 3}, {"val": 1}, {"val": 2}]
    count = insertion_sort_count(data, "val")
    check(isinstance(count, int), "insertion_sort_count returns int", "int", type(count).__name__)

    # Test 7: binary_search_count returns int
    data = [{"val": 1}, {"val": 3}, {"val": 5}, {"val": 7}, {"val": 9}]
    count = binary_search_count(data, 5, "val")
    check(isinstance(count, int), "binary_search_count returns int", "int", type(count).__name__)

    print(f"\n{passed} passed, {failed} failed out of {passed + failed} tests.")
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    raise SystemExit(0 if success else 1)
