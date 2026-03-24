"""
Преобразование Барроуза-Уиллера через суффиксный массив
Задания 3 и 4
"""

from typing import Tuple, List


def suffix_array_to_bwt(data: bytes, suffix_array: List[int]) -> bytes:
    """Задание 3: Преобразование суффиксного массива в BWT"""
    if not data or not suffix_array:
        return b''

    n = len(data)
    result = bytearray(n)

    for i, idx in enumerate(suffix_array):
        if idx == 0:
            result[i] = data[-1]
        else:
            result[i] = data[idx - 1]

    return bytes(result)


def build_suffix_array(data: bytes) -> List[int]:
    """
    Построение суффиксного массива (алгоритм Манбера-Майерса)
    Временная сложность: O(n log n)
    Пространственная сложность: O(n)
    """
    n = len(data)
    if n == 0:
        return []
    if n == 1:
        return [0]

    # Инициализация: суффиксный массив и ранги
    sa = list(range(n))
    rank = [data[i] for i in range(n)]
    tmp = [0] * n
    k = 1

    while True:
        # Сортировка по (rank[i], rank[i+k])
        sa.sort(key=lambda i: (rank[i], rank[i + k] if i + k < n else -1))

        # Пересчет рангов
        tmp[sa[0]] = 0
        for i in range(1, n):
            prev, cur = sa[i-1], sa[i]
            prev_key = (rank[prev], rank[prev + k] if prev + k < n else -1)
            cur_key = (rank[cur], rank[cur + k] if cur + k < n else -1)
            tmp[cur] = tmp[prev] + (prev_key != cur_key)

        rank, tmp = tmp, rank

        # Если все ранги уникальны, завершаем
        if rank[sa[-1]] == n - 1:
            break

        k *= 2

    return sa


def bwt_encode(data: bytes) -> Tuple[bytes, int]:
    """Прямое BWT через суффиксный массив"""
    if not data:
        return b'', 0

    suffix_array = build_suffix_array(data)
    bwt = suffix_array_to_bwt(data, suffix_array)
    original_index = suffix_array.index(0) if 0 in suffix_array else 0

    return bwt, original_index


def bwt_decode(bwt: bytes, idx: int) -> bytes:
    """Обратное BWT с сортировкой подсчетом"""
    if not bwt:
        return b''

    n = len(bwt)

    # Сортировка подсчетом
    counts = [0] * 256
    for c in bwt:
        counts[c] += 1

    start = [0] * 256
    total = 0
    for i in range(256):
        start[i] = total
        total += counts[i]

    next_pos = [0] * n
    cur = start[:]
    for i in range(n):
        c = bwt[i]
        next_pos[cur[c]] = i
        cur[c] += 1

    result = bytearray()
    pos = idx
    for _ in range(n):
        pos = next_pos[pos]
        result.append(bwt[pos])

    return bytes(result)


if __name__ == "__main__":
    # Тест из задания: 0x62 0x61 0x6e 0x61 0x6e 0x61 ("banana")
    test_data = bytes([0x62, 0x61, 0x6e, 0x61, 0x6e, 0x61])

    print(f"Исходные: {test_data}")

    bwt, idx = bwt_encode(test_data)
    print(f"BWT: {bwt}")
    print(f"Индекс: {idx}")

    decoded = bwt_decode(bwt, idx)
    print(f"Декодировано: {decoded}")

    if decoded == test_data:
        print("\nКорректно")
    else:
        print("\nОшибка")