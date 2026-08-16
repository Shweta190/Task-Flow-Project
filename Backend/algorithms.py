

def _compare_vals(a, b) -> int:
    """Helper comparing two values.
    Returns 1 if a > b, -1 if a < b, 0 if equal.
    Handles None, strings (case-insensitive), and mixed types safely.
    """
    if a == b:
        return 0
    if a is None and b is None:
        return 0
    if a is None:
        return 1
    if b is None:
        return -1
    if isinstance(a, str) and isinstance(b, str):
        al, bl = a.lower(), b.lower()
        if al != bl:
            return 1 if al > bl else -1
        return 1 if a > b else (-1 if a < b else 0)
    if type(a) is type(b):
        return 1 if a > b else -1
    sa, sb = str(a).lower(), str(b).lower()
    if sa != sb:
        return 1 if sa > sb else -1
    return 1 if str(a) > str(b) else (-1 if str(a) < str(b) else 0)


def _less(a: dict, b: dict, key: str) -> bool:
    """Returns True if a[key] > b[key] (i.e. a should come after b in ascending sort)."""
    return _compare_vals(a.get(key), b.get(key)) > 0


def _lt(a, b) -> bool:
    """Returns True if a < b."""
    return _compare_vals(a, b) < 0


def _eq(a, b) -> bool:
    """Returns True if a equals b (case-insensitive for strings)."""
    return _compare_vals(a, b) == 0


def insertion_sort(records: list[dict], key: str):
    """Sorts records in place by the given key using insertion sort."""
    for i in range(1, len(records)):
        current = records[i]
        j = i - 1
        while j >= 0 and _less(records[j], current, key):
            records[j + 1] = records[j]
            j -= 1
        records[j + 1] = current


def insertion_sort_count(records: list[dict], key: str) -> int:
    """Sorts in place and returns the number of comparisons made."""
    comparisons = 0
    for i in range(1, len(records)):
        current = records[i]
        j = i - 1
        while j >= 0:
            comparisons += 1
            if _less(records[j], current, key):
                records[j + 1] = records[j]
                j -= 1
            else:
                break
        records[j + 1] = current
    return comparisons


def binary_search(sorted_records: list[dict], target_value, key: str) -> int:
    """Returns the index of target_value in sorted_records by key, or -1."""
    low = 0
    high = len(sorted_records) - 1
    while low <= high:
        mid = (low + high) // 2
        mid_val = sorted_records[mid].get(key)
        if _eq(mid_val, target_value):
            return mid
        elif _lt(mid_val, target_value):
            low = mid + 1
        else:
            high = mid - 1
    return -1


def binary_search_count(sorted_records: list[dict], target_value, key: str) -> int:
    """Returns the number of comparisons made during binary search."""
    comparisons = 0
    low = 0
    high = len(sorted_records) - 1
    while low <= high:
        mid = (low + high) // 2
        mid_val = sorted_records[mid].get(key)
        comparisons += 1
        if _eq(mid_val, target_value):
            return comparisons
        comparisons += 1
        if _lt(mid_val, target_value):
            low = mid + 1
        else:
            high = mid - 1
    return comparisons


def linear_search(records: list[dict], target_value, key: str) -> int:
    """Returns the index of target_value in records by key, or -1."""
    for i in range(len(records)):
        if _eq(records[i].get(key), target_value):
            return i
    return -1


def linear_search_count(records: list[dict], target_value, key: str) -> int:
    """Returns the number of comparisons made during linear search."""
    comparisons = 0
    for i in range(len(records)):
        comparisons += 1
        if _eq(records[i].get(key), target_value):
            return comparisons
    return comparisons

