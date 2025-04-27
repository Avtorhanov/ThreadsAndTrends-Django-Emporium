# import json
#
# def remove_status_field(data):
#     for item in data:
#         if item.get('model') == 'orderitem':
#             if 'fields' in item and 'status' in item['fields']:
#                 del item['fields']['status']
#
# # Чтение данных из файла
# with open('fixtures.json', 'r', encoding='utf-8') as file:
#     json_data = json.load(file)
#
# # Удаление поля "status" из объектов "orderitem"
# remove_status_field(json_data)
#
# # Запись обновленных данных обратно в файл
# with open('fixtures.json', 'w', encoding='utf-8') as file:
#     json.dump(json_data, file, ensure_ascii=False, indent=4)
#

# import chardet
#
# # Открываем файл для чтения в бинарном режиме
# with open('store/subcategory_detail.html', 'rb') as file:
#     # Читаем первые несколько байтов из файла для определения кодировки
#     raw_data = file.read(10000)
#
# # Определяем кодировку с помощью модуля chardet
# encoding_result = chardet.detect(raw_data)['encoding']
#
# # Печатаем результат
# print("Результат определения кодировки:", encoding_result)
#
# # Теперь открываем файл для чтения с определенной кодировкой
# with open('store/subcategory_detail.html', 'r', encoding=encoding_result) as file:
#     content = file.read()

# for num in range(1, 26):
#     if num % 2 != 0:  # если не кратно 2, то точно не кратно 4 и 8 тоже
#         continue  # поэтому эту итерацию пропускаем
#     print(f'\nЧисло {num}')
#     print('Кратно 2')
#
#     if num % 4 != 0:
#         continue
#     print('Кратно 4')
#
#     if num % 8 != 0:
#         continue
#     print('Кратно 8')

# У лукоморья дуб зеленый.

# Введите предложение
# s = input()
#
# p = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~№41'
# c = ''
# for i in s:
#     if i not in p:
#         c += i
#
# words = c.lower().split()
# for w in words:
#     print(w[::-1])


# s = 0
# f = False
# for i in range(11):
#     x = int(input())
#     if x <= 0:
#         s += x
#         f = True
# if not f:
#     print('NO')
#
# print(s)

# def common_prefix(words):
#     if not words:
#         return ""
#
#     prefix = words[0]  # Берем первое слово в качестве начального префикса
#
#     # Проходим по остальным словам
#     for word in words[1:]:
#         # Обрезаем префикс до длины общего префикса
#         while not word.startswith(prefix):
#             prefix = prefix[:-1]
#
#     return prefix
#
# # Пример использования
# words = ["flower", "flow", "flight"]
# print("Общий префикс:", common_prefix(words))  # Вывод: "fl"


# def romanToInt(s):
#     # Создаем словарь для соответствия римских цифр и их арабских значений
#     rom_value = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
#     # Инициализируем результат
#     result = 0
#     # Инициализируем предыдущее значение, начинаем с последнего символа
#     prev_value = rom_value[s[-1]]
#     # Проходимся по строке справа налево
#     for i in range(len(s) - 1, -1, -1):
#         # Получаем текущее значение из словаря
#         curr_value = rom_value[s[i]]
#         # Если текущее значение больше или равно предыдущему, добавляем его к результату
#         if curr_value >= prev_value:
#             result += curr_value
#         else:
#             # Иначе, вычитаем его
#             result -= curr_value
#         # Обновляем значение предыдущего символа для следующей итерации
#         prev_value = curr_value
#     # Возвращаем итоговый результат
#     return result
#
# # Пример использования
# print(romanToInt('III'))     # Вывод: 3
# print(romanToInt('IV'))      # Вывод: 4
# print(romanToInt('IX'))      # Вывод: 9
# print(romanToInt('LVIII'))   # Вывод: 58
# print(romanToInt('MCMXCIV')) # Вывод: 1994

# def initials(name):
#     first_n, last_n = name.split()
#     initials = first_n[0].upper() + '.' + last_n[0].upper()
#     print(initials)
#
# initials('Sam Harris')


# class MyClass:
#     def __init__(self, x):
#         self.x = x
#
#     def print_x(self):
#         print(self.x)
#
# obj = MyClass(5)
# obj.print_x()  # Вызывает метод print_x() с экземпляром obj как аргумент self

# import json
#
# # Создаем словарь для хранения данных
# data = {
#     "Россия": "Москва",
#     "США": "Вашингтон",
#     "Китай": "Пекин"
# }
#
# # Добавление данных
# data["Франция"] = "Париж"
#
# # Удаление данных
# del data["Китай"]
#
# # Поиск данных
# country = "Россия"
# capital = data.get(country)
# if capital:
#     print(f"Столица страны {country} - {capital}")
# else:
#     print(f"Данные о стране {country} не найдены")
#
# # Редактирование данных
# data["США"] = "Нью-Йорк"
#
# # Сохранение данных
# with open("data.json", "w") as f:
#     json.dump(data, f)
#
# # Загрузка данных
# with open("data.json", "r") as f:
#     data = json.load(f)
#     print(data)


# test.assert_equals(count_by(1, 5), [1, 2, 3, 4, 5])
#         test.assert_equals(count_by(2, 5), [2, 4, 6, 8, 10])
#         test.assert_equals(count_by(3, 5), [3, 6, 9, 12, 15])
#         test.assert_equals(count_by(50, 5), [50, 100, 150, 200, 250])
#         test.assert_equals(count_by(100, 5), [100, 200, 300, 400, 500])



# def double_char(s):
#     return ''.join(i * 2 for i in s)
#
# print(double_char('Hello world'))

# def correct(s):
#     return s.replace('0', 'O').replace('1', 'I').replace('5', 'S')
#
# print(correct('501'))

# def is_palindrome(s):
#     return True if s.capitalize() == s[::-1].capitalize() else False
#
# print(is_palindrome('a'))
# print(is_palindrome('aba'))
# print(is_palindrome('Abba'))
# print(is_palindrome('malam'))
# print(is_palindrome('walter'))
# print(is_palindrome('kodok'))

# def sum_numbers(s1, s2):
#     return lambda s1, s2: sum(map(int, s1.split())) if s1 and s2 else 0 if not s1 else sum(map(int, s1.split())) if not s2 else sum(map(int, s2.split()))

# def sum_numbers(s1, s2):
#         return str(sum(map(int, s1.split())) + sum(map(int, s2.split())))
# # Примеры использования:
# print(sum_numbers("1 2 3", "4 5 6"))  # Вывод: "21"
# print(sum_numbers("", "4 5 6"))       # Вывод: "15"
# print(sum_numbers("1 2 3", ""))       # Вывод: "6"
# print(sum_numbers("", ""))            # Вывод: "0"

# def add_binary(a,b):
#     return format(a + b, 'b')
#
# print(add_binary(1,4))

# num = 14
# g = format(num, 'b')
# print(g)

# def count_sheeps(sheeps):
#     count = 0
#     for sheep in (sheeps):
#         if sheep == True:
#             count += 1
#     return count
#
# print(count_sheeps([True,  True,  True,  False,
#   True,  True,  True,  True ,
#   True,  False, True,  False,
#   True,  False, False, True ,
#   True,  True,  True,  True ,
#   False, False, True,  True]))

# Задача с Амазон

# def find_pair(arr, k):
#     num_dict = {}
#     for i, num in enumerate(arr):
#         diff = k - num
#         if diff in num_dict:
#             return f'Первое число {arr[num_dict[diff]]} индекс - {num_dict[diff]} \nВторое число {num} индекс - {i}'
#
#         num_dict[num] = i
#     return 'Не найдено'
#
# print(find_pair([2,4,3,], 9))


# def find_pair(arr, K):
#     # Создаем пустой словарь для хранения индексов чисел из массива
#     num_dict = {}
#     # Проходим по каждому элементу и его индексу в массиве
#     for i, num in enumerate(arr):
#         # Вычисляем разность между целевым числом K и текущим числом num
#         diff = K - num
#         # Проверяем, есть ли разность в словаре (т.е. уже встречали число, которое дает нужную разность)
#         if diff in num_dict:
#             # Если нашли такую разность, возвращаем числа и их индексы
#             return f"Числа: {arr[num_dict[diff]]} (индекс {num_dict[diff]}) и {num} (индекс {i})"
#         # Если разность не найдена, сохраняем текущее число в словаре с его индексом
#         num_dict[num] = i
#     # Если не нашли пары чисел, которые в сумме дают K, возвращаем None
#     return None
# # Пример использования
# print(find_pair([1, 2, 3, 4, 5], 7))

# def bubble_sort(arr):
#     n = len(arr)
#     for i in range(n):
#         for j in range(0, n-i-1):
#             if arr[j] > arr[j+1]:
#                 arr[j], arr[j+1] = arr[j+1], arr[j]
#     return arr
#
# # Пример использования
# print(bubble_sort([64, 34, 25, 12, 22, 11, 90]))
#
#
# def count_elements(arr):
#     count_dict = {}
#     for element in arr:
#         if element in count_dict:
#             count_dict[element] += 1
#         else:
#             count_dict[element] = 1
#     return count_dict
#
# # Пример использования
# print(count_elements([1, 2, 1, 3, 2, 4, 1]))
#
# def max_subarray(arr):
#     max_sum = current_sum = arr[0]
#     for num in arr[1:]:
#         current_sum = max(num, current_sum + num)
#         max_sum = max(max_sum, current_sum)
#     return max_sum
#
# # Пример использования
# print(max_subarray([-2, 1, -3, 4, -1, 2, 1, -5, 4]))

# import psycopg2
# from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# try:
#     # Подключаемся к postgres (не к конкретной БД)
#     conn = psycopg2.connect(dbname='postgres', user='boss', password='1243', host='localhost', port='5432')
#     conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
#     cur = conn.cursor()

#     # Проверяем наличие базы
#     cur.execute("SELECT 1 FROM pg_database WHERE datname = 'db_shop'")
#     exists = cur.fetchone()

#     if not exists:
#         cur.execute('CREATE DATABASE db_shop')
#         print("База данных 'db_shop' успешно создана.")
#     else:
#         print("База данных 'db_shop' уже существует.")

#     cur.close()
#     conn.close()
# except Exception as e:
#     print("Ошибка при подключении или создании базы:", e)

import json

# Словарь для замены описаний (по названиям подкатегорий)
desc_map = {
    'часы': 'смотреть время',
    'очки': 'солнцезащитные',
    'витамины': 'для здоровья',
    'косметика': 'для красоты',
    'футболки': 'на выход',
    'зимние': 'теплые',
    'кроссовки': 'удобные',
    'сумки': 'строго для денег'
}

# Словарь соответствия ID и описаний (если subcategory уже числовой)
id_to_desc = {
    1: 'смотреть время',  # ID для 'часы'
    2: 'солнцезащитные',  # ID для 'очки'
    3: 'для здоровья',     # ID для 'витамины'
    4: 'для красоты',      # ID для 'косметика'
    5: 'на выход',         # ID для 'футболки'
    6: 'теплые',           # ID для 'зимние'
    7: 'удобные',          # ID для 'кроссовки'
    8: 'строго для денег'  # ID для 'сумки'
}

with open('fixtures/fixtures.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for obj in data:
    if obj['model'].endswith('product') and 'subcategory' in obj['fields']:
        subcat = obj['fields']['subcategory']
        
        # Если subcategory - строка (название)
        if isinstance(subcat, str):
            key = subcat.lower()
            
            # Обновляем описание по названию
            if key in desc_map:
                obj['fields']['description'] = desc_map[key]
                
        # Если subcategory - число (ID)
        elif isinstance(subcat, int):
            # Обновляем описание по ID
            if subcat in id_to_desc:
                obj['fields']['description'] = id_to_desc[subcat]

with open('fixtures/fixtures.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print('Готово! Описания обновлены по названиям и ID подкатегорий.')

