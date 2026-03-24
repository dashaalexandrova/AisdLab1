from collections import Counter


class ArithmeticCoder:
    def __init__(self):
        self.probabilities = None
        self.cumulative = None
        self.symbols_list = None

    def build_probabilities(self, data):
        freq = Counter(data)
        total = len(data)
        self.probabilities = {symbol: count / total for symbol, count in freq.items()}
        self.symbols_list = sorted(self.probabilities.keys())

        self.cumulative = {}
        cum = 0.0
        for symbol in self.symbols_list:
            self.cumulative[symbol] = cum
            cum += self.probabilities[symbol]

    def encode(self, data):
        if not data:
            return 0.0, 0.0, 0.0

        if self.probabilities is None:
            self.build_probabilities(data)

        low = 0.0
        high = 1.0

        for symbol in data:
            range_width = high - low
            symbol_low = self.cumulative[symbol]
            symbol_high = symbol_low + self.probabilities[symbol]

            high = low + range_width * symbol_high
            low = low + range_width * symbol_low

            if high == low or (high - low) < 1e-15:
                return None, low, high

        return (low + high) / 2, low, high

    def decode(self, encoded_value, length):
        if self.cumulative is None:
            raise ValueError("Модель не построена")

        intervals = []
        for symbol in self.symbols_list:
            intervals.append({
                'symbol': symbol,
                'low': self.cumulative[symbol],
                'high': self.cumulative[symbol] + self.probabilities[symbol]
            })

        result = bytearray()
        low = 0.0
        high = 1.0

        for _ in range(length):
            range_width = high - low
            value = (encoded_value - low) / range_width

            found = None
            for interval in intervals:
                if interval['low'] <= value < interval['high']:
                    found = interval['symbol']
                    break

            if found is None:
                return None

            result.append(found)

            symbol_low = self.cumulative[found]
            symbol_high = symbol_low + self.probabilities[found]
            high = low + range_width * symbol_high
            low = low + range_width * symbol_low

        return bytes(result)


def test_precision():
    """Эксперимент: при какой длине строки происходит потеря точности double"""
    print("=" * 100)
    print("ЭКСПЕРИМЕНТ: ПРЕДЕЛЫ ТОЧНОСТИ DOUBLE В АРИФМЕТИЧЕСКОМ КОДИРОВАНИИ")
    print("=" * 100)

    # Тестовая строка
    test_string = "abracadabra"
    test_data = test_string.encode('ascii')

    print(f"\nИсходная строка: '{test_string}'")
    print(f"Длина строки: {len(test_data)} символов")
    print(f"Уникальных символов: {len(set(test_data))}")
    print()

    print(f"{'Длина':<10} {'Исходная строка':<30} {'Закодированное число':<40} {'Результат декодирования'}")
    print("-" * 100)

    max_success = 0
    error_length = None

    for length in [5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 120, 140, 160, 180, 200]:
        # Берем строку нужной длины
        repeat_count = (length + len(test_string) - 1) // len(test_string)
        full_string = (test_string * repeat_count)[:length]
        test_data_slice = full_string.encode('ascii')

        coder = ArithmeticCoder()
        coder.build_probabilities(test_data_slice)
        result, low, high = coder.encode(test_data_slice)

        if result is None:
            print(f"{length:<10} {full_string:<30} {'ПОТЕРЯ ТОЧНОСТИ':<40} -")
            error_length = length
            break
        else:
            # Пробуем декодировать
            decoded = coder.decode(result, length)
            decoded_str = decoded.decode('ascii')

            if decoded == test_data_slice:
                print(f"{length:<10} {full_string:<30} {result:<40.20f} {decoded_str}")
            else:
                print(f"{length:<10} {full_string:<30} {result:<40.20f} {'ОШИБКА ДЕКОДИРОВАНИЯ'}")
                error_length = length
                break

            max_success = length




if __name__ == "__main__":
    test_precision()