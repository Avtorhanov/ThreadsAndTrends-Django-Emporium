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
