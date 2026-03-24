"""
bwt.py - BWT с поддержкой блоков
"""

def bwt_encode_simple(data: bytes) -> tuple:
    """
    Простое BWT кодирование
    Возвращает: (bwt_data, original_index)
    """
    if not data:
        return b'', 0

    n = len(data)

    # Создаем все циклические сдвиги
    rotations = []
    for i in range(n):
        rotation = data[i:] + data[:i]
        rotations.append(rotation)

    # Сортируем
    rotations.sort()

    # Берем последний столбец
    last_column = bytes(rot[-1] for rot in rotations)

    # Находим индекс оригинальной строки
    original = data
    for i, rot in enumerate(rotations):
        if rot == original:
            original_index = i
            break

    return last_column, original_index


def bwt_decode_efficient(last_column: bytes, original_index: int) -> bytes:
    """
    Эффективное BWT декодирование
    """
    if not last_column:
        return b''

    n = len(last_column)

    # Подсчет символов
    char_counts = [0] * 256
    for char in last_column:
        char_counts[char] += 1

    # Начальные позиции
    start_pos = [0] * 256
    total = 0
    for i in range(256):
        start_pos[i] = total
        total += char_counts[i]

    # Построение next_pos
    next_pos = [0] * n
    current_pos = start_pos[:]

    for i in range(n):
        char = last_column[i]
        next_pos[current_pos[char]] = i
        current_pos[char] += 1

    # Восстановление
    result = bytearray()
    pos = original_index

    for _ in range(n):
        pos = next_pos[pos]
        result.append(last_column[pos])

    return bytes(result)


def bwt_decode_simple(last_column: bytes, original_index: int) -> bytes:
    """
    Простое BWT декодирование (для понимания)
    """
    if not last_column:
        return b''

    n = len(last_column)
    table = [b''] * n

    for _ in range(n):
        for i in range(n):
            table[i] = bytes([last_column[i]]) + table[i]
        table.sort()

    return table[original_index]


# ==================== BWT С БЛОКАМИ ====================

def bwt_encode_blocks(data: bytes, block_size: int = None) -> tuple:
    """
    BWT с разбиением на блоки

    Args:
        data: исходные данные
        block_size: размер блока в байтах (None или 0 = без разбиения)

    Returns:
        bwt_data: объединенные BWT блоки
        indices: индексы для каждого блока
        block_sizes: реальные размеры блоков
        is_bwt: флаг, был ли применен BWT к блоку
    """
    if not data:
        return b'', [], [], []

    # Без разбиения
    if not block_size or block_size <= 0 or block_size >= len(data):
        bwt_block, idx = bwt_encode_simple(data)
        return bwt_block, [idx], [len(data)], [True]

    bwt_blocks = bytearray()
    indices = []
    block_sizes = []
    is_bwt = []

    for i in range(0, len(data), block_size):
        block = data[i:i + block_size]
        block_sizes.append(len(block))

        # Для маленького последнего блока (меньше 3 байт)
        if len(block) < 3:
            # Просто копируем без BWT
            bwt_blocks.extend(block)
            indices.append(0)
            is_bwt.append(False)
        else:
            bwt_block, idx = bwt_encode_simple(block)
            bwt_blocks.extend(bwt_block)
            indices.append(idx)
            is_bwt.append(True)

    return bytes(bwt_blocks), indices, block_sizes, is_bwt


def bwt_decode_blocks(bwt_data: bytes, indices: list, block_sizes: list, is_bwt: list, use_efficient: bool = True) -> bytes:
    """
    Обратное BWT с блоками

    Args:
        bwt_data: объединенные BWT блоки
        indices: индексы для каждого блока
        block_sizes: реальные размеры блоков
        is_bwt: флаг, был ли применен BWT к блоку
        use_efficient: использовать эффективное декодирование

    Returns:
        восстановленные данные
    """
    if not bwt_data or not indices:
        return b''

    result = bytearray()
    pos = 0

    decode_func = bwt_decode_efficient if use_efficient else bwt_decode_simple

    for i, (idx, block_size, bwt_flag) in enumerate(zip(indices, block_sizes, is_bwt)):
        if pos >= len(bwt_data):
            break

        block = bwt_data[pos:pos + block_size]

        if not bwt_flag:
            # Блок без BWT
            result.extend(block)
        else:
            # BWT блок
            if len(block) == block_size:
                decoded = decode_func(block, idx)
                result.extend(decoded)

        pos += block_size

    return bytes(result)


# ==================== ДЛЯ СОВМЕСТИМОСТИ ====================

# Псевдонимы для совместимости с другими файлами
bwt_encode = bwt_encode_simple
bwt_decode = bwt_decode_efficient


# ==================== ТЕСТИРОВАНИЕ ====================

def test_banana():
    """Тестирование на banana"""

    test_data = bytes([0x62, 0x61, 0x6e, 0x61, 0x6e, 0x61])

    print("="*60)
    print("ТЕСТ: banana")
    print("="*60)
    print(f"Исходные: {test_data} -> '{test_data.decode()}'")
    print()

    # Без блоков
    print("БЕЗ БЛОКОВ:")
    bwt_data, idx = bwt_encode_simple(test_data)
    print(f"  BWT: {bwt_data}")
    print(f"  Индекс: {idx}")
    decoded = bwt_decode_efficient(bwt_data, idx)
    print(f"  Декодировано: {decoded} -> '{decoded.decode()}'")
    print(f"  Результат: {'✓' if decoded == test_data else '✗'}")
    print()

    # С блоками
    for bs in [2, 3, 4, 5, 6]:
        print(f"БЛОК {bs}:")
        bwt_data, indices, block_sizes, is_bwt = bwt_encode_blocks(test_data, bs)
        print(f"  BWT: {bwt_data}")
        print(f"  Индексы: {indices}")
        print(f"  Размеры: {block_sizes}")
        print(f"  BWT применен: {is_bwt}")
        decoded = bwt_decode_blocks(bwt_data, indices, block_sizes, is_bwt)
        print(f"  Декодировано: {decoded} -> '{decoded.decode() if len(decoded) == len(test_data) else decoded}'")
        print(f"  Результат: {'✓' if decoded == test_data else '✗'}")
        print()


def test_repetitive():
    """Тестирование на повторяющихся данных"""

    test_data = b"abc" * 30 + b"def" * 30
    print("="*60)
    print("ТЕСТ: повторяющиеся данные")
    print("="*60)
    print(f"Размер: {len(test_data)} байт")
    print(f"Первые 30: {test_data[:30]}")
    print()

    for bs in [None, 32, 64, 128, 256]:
        if bs:
            bwt_data, indices, block_sizes, is_bwt = bwt_encode_blocks(test_data, bs)
            print(f"БЛОК {bs}:")
        else:
            bwt_data, indices, block_sizes, is_bwt = bwt_encode_blocks(test_data)
            print(f"БЕЗ БЛОКОВ:")

        decoded = bwt_decode_blocks(bwt_data, indices, block_sizes, is_bwt)

        ratio = len(bwt_data) / len(test_data)
        status = '✓' if decoded == test_data else '✗'

        print(f"  BWT размер: {len(bwt_data)} (коэфф={ratio:.4f})")
        print(f"  Количество блоков: {len(indices)}")
        print(f"  Статус: {status}")

        if decoded != test_data and len(decoded) == len(test_data):
            # Находим позицию первого отличия
            for i in range(len(test_data)):
                if decoded[i] != test_data[i]:
                    print(f"  Первое отличие на позиции {i}: {test_data[i]} vs {decoded[i]}")
                    break

        print()


def test_bwt_alone():
    """Тест только BWT без блоков"""

    test_cases = [
        (b"banana", "banana"),
        (b"abcabc", "abcabc"),
        (b"aaaaaa", "aaaaaa"),
        (b"abcde", "abcde"),
    ]

    print("="*60)
    print("ТЕСТ BWT (без блоков)")
    print("="*60)

    for data, name in test_cases:
        bwt_data, idx = bwt_encode_simple(data)
        decoded = bwt_decode_efficient(bwt_data, idx)

        print(f"{name}:")
        print(f"  Исходный: {data}")
        print(f"  BWT: {bwt_data}")
        print(f"  Индекс: {idx}")
        print(f"  Декод: {decoded}")
        print(f"  Статус: {'✓' if decoded == data else '✗'}")
        print()


# ==================== ТЕСТИРОВАНИЕ НА РУССКОМ ТЕКСТЕ ====================

def test_russian_text_blocks():
    """
    Тестирование BWT с блоками на русском тексте
    """
    import os

    base_path = r"C:\Users\Daria\OneDrive\Desktop\аисд"
    russian_file = os.path.join(base_path, "Русский текст.txt")

    if not os.path.exists(russian_file):
        print(f"❌ Файл не найден: {russian_file}")
        return

    with open(russian_file, 'rb') as f:
        data = f.read()

    print("=" * 80)
    print("ТЕСТИРОВАНИЕ BWT С БЛОКАМИ НА РУССКОМ ТЕКСТЕ")
    print("=" * 80)
    print(f"Размер файла: {len(data):,} байт")
    print()

    # Размеры блоков для тестирования
    block_sizes = [256, 512, 1024, 2048, 4096, 8192, 16384]

    # ========== ТЕСТ 1: BWT + RLE ==========
    print("-" * 80)
    print("ТЕСТ 1: BWT + RLE")
    print("-" * 80)
    print(f"{'Блок (байт)':<15} {'BWT размер':>15} {'BWT+RLE':>15} {'Коэфф.':>10} {'Статус':>8}")
    print("-" * 80)

    # Импортируем RLE
    try:
        from rle_compressor import RLE
        rle = RLE(Ms=8, Mc=8)
        has_rle = True
    except ImportError:
        print("RLE модуль не найден")
        has_rle = False

    for bs in block_sizes:
        if bs > len(data):
            continue

        # BWT с блоками
        bwt_data, indices, block_sizes_list, is_bwt = bwt_encode_blocks(data, bs)

        # Проверяем корректность
        decoded = bwt_decode_blocks(bwt_data, indices, block_sizes_list, is_bwt)
        status_bwt = '✓' if decoded == data else '✗'

        if not has_rle:
            print(f"{bs:<15} {len(bwt_data):>15,} {'N/A':>15} {len(bwt_data) / len(data):>10.4f} {status_bwt:>8}")
            continue

        # RLE
        rle_data = rle.encode(bwt_data)

        # Проверяем декодирование RLE
        decoded_bwt = rle.decode(rle_data)
        decoded_final = bwt_decode_blocks(decoded_bwt, indices, block_sizes_list, is_bwt)

        ratio = len(rle_data) / len(data)
        status = '✓' if decoded_final == data else '✗'

        print(f"{bs:<15} {len(bwt_data):>15,} {len(rle_data):>15,} {ratio:>10.4f} {status:>8}")

    print("-" * 80)

    # Повторяем для поиска оптимального
    best_bwt_rle = None
    best_ratio_rle = 1.0

    for bs in block_sizes:
        if bs > len(data):
            continue

        bwt_data, indices, block_sizes_list, is_bwt = bwt_encode_blocks(data, bs)

        if has_rle:
            rle_data = rle.encode(bwt_data)
            ratio_rle = len(rle_data) / len(data)
            if ratio_rle < best_ratio_rle:
                best_ratio_rle = ratio_rle
                best_bwt_rle = bs

    if best_bwt_rle:
        print(f"\n✅ Оптимальный размер блока для BWT+RLE: {best_bwt_rle} байт (коэффициент = {best_ratio_rle:.4f})")


# ==================== ТЕСТИРОВАНИЕ НА ENWIK7 ====================

def test_enwik7_blocks():
    """
    Тестирование BWT с блоками на enwik7
    """
    import os

    base_path = r"C:\Users\Daria\OneDrive\Desktop\аисд"
    enwik7_file = os.path.join(base_path, "enwik7")

    if not os.path.exists(enwik7_file):
        print(f"❌ Файл не найден: {enwik7_file}")
        return

    with open(enwik7_file, 'rb') as f:
        data = f.read()

    print("=" * 80)
    print("ТЕСТИРОВАНИЕ BWT С БЛОКАМИ НА ENWIK7")
    print("=" * 80)
    print(f"Размер файла: {len(data):,} байт")
    print()

    # Размеры блоков для тестирования
    block_sizes = [256, 512, 1024, 2048, 4096, 8192, 16384]

    # ========== ТЕСТ 1: BWT + RLE ==========
    print("-" * 80)
    print("ТЕСТ 1: BWT + RLE")
    print("-" * 80)
    print(f"{'Блок (байт)':<15} {'BWT размер':>15} {'BWT+RLE':>15} {'Коэфф.':>10} {'Статус':>8}")
    print("-" * 80)

    # Импортируем RLE
    try:
        from rle_compressor import RLE
        rle = RLE(Ms=8, Mc=8)
        has_rle = True
    except ImportError:
        print("RLE модуль не найден")
        has_rle = False

    for bs in block_sizes:
        if bs > len(data):
            continue

        # BWT с блоками
        bwt_data, indices, block_sizes_list, is_bwt = bwt_encode_blocks(data, bs)

        # Проверяем корректность
        decoded = bwt_decode_blocks(bwt_data, indices, block_sizes_list, is_bwt)
        status_bwt = '✓' if decoded == data else '✗'

        if not has_rle:
            print(f"{bs:<15} {len(bwt_data):>15,} {'N/A':>15} {len(bwt_data) / len(data):>10.4f} {status_bwt:>8}")
            continue

        # RLE
        rle_data = rle.encode(bwt_data)

        # Проверяем декодирование RLE
        decoded_bwt = rle.decode(rle_data)
        decoded_final = bwt_decode_blocks(decoded_bwt, indices, block_sizes_list, is_bwt)

        ratio = len(rle_data) / len(data)
        status = '✓' if decoded_final == data else '✗'

        print(f"{bs:<15} {len(bwt_data):>15,} {len(rle_data):>15,} {ratio:>10.4f} {status:>8}")

    print("-" * 80)

    # Повторяем для поиска оптимального
    best_bwt_rle = None
    best_ratio_rle = 1.0

    for bs in block_sizes:
        if bs > len(data):
            continue

        bwt_data, indices, block_sizes_list, is_bwt = bwt_encode_blocks(data, bs)

        if has_rle:
            rle_data = rle.encode(bwt_data)
            ratio_rle = len(rle_data) / len(data)
            if ratio_rle < best_ratio_rle:
                best_ratio_rle = ratio_rle
                best_bwt_rle = bs

    if best_bwt_rle:
        print(f"\n✅ Оптимальный размер блока для BWT+RLE: {best_bwt_rle} байт (коэффициент = {best_ratio_rle:.4f})")


# ==================== ОСНОВНОЙ ЗАПУСК ====================

if __name__ == "__main__":
    # Сначала тесты на banana и повторяющихся данных
    test_bwt_alone()
    print()
    #test_banana()
    #print()

    # Тесты на русском тексте
    test_russian_text_blocks()
    print()

    # Тесты на enwik7
    test_enwik7_blocks()