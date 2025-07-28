def wrap_user_function(user_code: str, func_name: str) -> str:
    """
    Оборачивает пользовательский код функции, добавляя запуск из stdin.
    В stdin приходит JSON с именованными аргументами.
    Выводит JSON результата.
    """
    return f"""
import sys
import json

{user_code.strip()}

if __name__ == "__main__":
    input_str = sys.stdin.read()
    args = json.loads(input_str)
    result = {func_name}(**args)
    print(json.dumps(result))
"""
