def _extract_data() -> list[int]:
    return [1, 2, 3, 4]


def _store_data(processed_at: str, data_a: list[int], data_b: list[int]) -> None:
    print(f"Storing {len(data_a + data_b)} records at {processed_at}")
