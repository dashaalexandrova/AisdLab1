import os


# ==================== LZ77 ====================
# (код есть, но не запускается)

def lz77_encode(data: bytes, window_size: int = 4096, lookahead_size: int = 16) -> bytes:
    # функция присутствует, но не вызывается
    pass


def lz77_decode(data: bytes) -> bytes:
    pass


# ==================== LZSS ====================
# (код есть, но не запускается)

def lzss_encode(data: bytes, window_size: int = 4096, lookahead_size: int = 16) -> bytes:
    pass


def lzss_decode(data: bytes) -> bytes:
    pass


# ==================== LZ78 ====================

class LZ78Coder:
    def __init__(self, max_dict_size: int = 4096):
        self.max_dict_size = max_dict_size

    def encode(self, data: bytes) -> bytes:
        if not data:
            return b''
        dictionary = {b'': 0}
        result = bytearray()
        current = b''
        for byte in data:
            current += bytes([byte])
            if current not in dictionary:
                if len(dictionary) < self.max_dict_size:
                    dictionary[current] = len(dictionary)
                prefix = current[:-1]
                idx = dictionary.get(prefix, 0)
                result.extend(idx.to_bytes(2, 'big'))
                result.append(byte)
                current = b''
        if current:
            idx = dictionary.get(current[:-1], 0) if current[:-1] in dictionary else 0
            result.extend(idx.to_bytes(2, 'big'))
            result.append(current[-1])
        return bytes(result)

    def decode(self, data: bytes) -> bytes:
        if not data:
            return b''
        dictionary = {0: b''}
        result = bytearray()
        i = 0
        n = len(data)
        while i + 3 <= n:
            idx = int.from_bytes(data[i:i + 2], 'big')
            char = data[i + 2]
            i += 3
            entry = dictionary.get(idx, b'') + bytes([char])
            if len(dictionary) < self.max_dict_size:
                dictionary[len(dictionary)] = entry
            result.extend(entry)
        return bytes(result)


# ==================== LZW ====================

class LZWCoder:
    def __init__(self, max_dict_size: int = 4096):
        self.max_dict_size = max_dict_size

    def encode(self, data: bytes) -> bytes:
        if not data:
            return b''
        dictionary = {bytes([i]): i for i in range(256)}
        result = bytearray()
        current = b''
        for byte in data:
            new_current = current + bytes([byte])
            if new_current in dictionary:
                current = new_current
            else:
                code = dictionary[current]
                result.extend(code.to_bytes(2, 'big'))
                if len(dictionary) < self.max_dict_size:
                    dictionary[new_current] = len(dictionary)
                current = bytes([byte])
        if current:
            code = dictionary[current]
            result.extend(code.to_bytes(2, 'big'))
        return bytes(result)

    def decode(self, data: bytes) -> bytes:
        if not data:
            return b''
        dictionary = {i: bytes([i]) for i in range(256)}
        result = bytearray()
        i = 0
        n = len(data)
        if n < 2:
            return b''
        prev_code = int.from_bytes(data[i:i + 2], 'big')
        i += 2
        result.extend(dictionary[prev_code])
        while i + 2 <= n:
            code = int.from_bytes(data[i:i + 2], 'big')
            i += 2
            if code in dictionary:
                entry = dictionary[code]
            elif code == len(dictionary):
                entry = dictionary[prev_code] + bytes([dictionary[prev_code][0]])
            else:
                break
            result.extend(entry)
            if len(dictionary) < self.max_dict_size:
                new_entry = dictionary[prev_code] + bytes([entry[0]])
                dictionary[len(dictionary)] = new_entry
            prev_code = code
        return bytes(result)


# ==================== ТЕСТИРОВАНИЕ ТОЛЬКО LZ78 И LZW ====================

if __name__ == "__main__":
    desktop_path = r"C:\Users\Daria\OneDrive\Desktop\аисд"

    files = [
        ('enwik7', os.path.join(desktop_path, 'enwik7')),
        ('russian_text', os.path.join(desktop_path, 'Русский текст.txt')),
        ('binary_file', os.path.join(desktop_path, 'Бинарный файл.exe')),
        ('bw_raw', os.path.join(desktop_path, 'чб', 'bw.raw')),
        ('gray_raw', os.path.join(desktop_path, 'серое', 'gray.raw')),
        ('color_raw', os.path.join(desktop_path, 'цветное', 'color.raw')),
    ]

    print("=" * 80)
    print("LZ78 (словарь 4096)")
    print("=" * 80)
    print(f"{'Файл':<20} {'Исходный':>12} {'Сжатый':>12} {'Коэффициент':>12} {'Статус':>10}")
    print("-" * 70)

    for name, path in files:
        if not os.path.exists(path):
            print(f"{name:<20} {'НЕ НАЙДЕН':<40}")
            continue
        with open(path, 'rb') as f:
            data = f.read()

        coder = LZ78Coder(4096)
        enc = coder.encode(data)
        dec = coder.decode(enc)
        ratio = len(enc) / len(data)
        status = "✓" if dec == data else "✗"
        print(f"{name:<20} {len(data):>12,} {len(enc):>12,} {ratio:>12.4f} {status:>10}")

    print("\n" + "=" * 80)
    print("LZW (исследование размера словаря)")
    print("=" * 80)

    dict_sizes = [256, 512, 1024, 2048, 4096, 8192]

    for name, path in files:
        if name not in ['enwik7', 'russian_text']:
            continue
        if not os.path.exists(path):
            continue
        with open(path, 'rb') as f:
            data = f.read()

        print(f"\n{name} (размер: {len(data):,} байт)")
        print(f"{'Словарь':<12} {'Сжатый':>15} {'Коэффициент':>12} {'Статус':>10}")
        print("-" * 55)

        for ds in dict_sizes:
            coder = LZWCoder(ds)
            enc = coder.encode(data)
            dec = coder.decode(enc)
            ratio = len(enc) / len(data)
            status = "✓" if dec == data else "✗"
            print(f"{ds:<12} {len(enc):>15,} {ratio:>12.4f} {status:>10}")

    print("\n✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")