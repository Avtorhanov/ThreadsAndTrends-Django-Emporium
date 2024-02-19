import json

def remove_status_field(data):
    for item in data:
        if item.get('model') == 'orderitem':
            if 'fields' in item and 'status' in item['fields']:
                del item['fields']['status']

# Чтение данных из файла
with open('fixtures.json', 'r', encoding='utf-8') as file:
    json_data = json.load(file)

# Удаление поля "status" из объектов "orderitem"
remove_status_field(json_data)

# Запись обновленных данных обратно в файл
with open('fixtures.json', 'w', encoding='utf-8') as file:
    json.dump(json_data, file, ensure_ascii=False, indent=4)
