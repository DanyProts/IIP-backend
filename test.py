import os
import smtplib
from email.message import EmailMessage

def load_env_manual(path):
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, val = line.split('=', 1)
            os.environ[key] = val

def send_simple_email(to_email: str, env_path: str = 'C:/Users/Aushota/IIP-backend/.env'):
    # Загружаем переменные из .env вручную
    load_env_manual(env_path)

    EMAIL_ADDRESS = os.getenv('SMTP_EMAIL')
    EMAIL_PASSWORD = os.getenv('SMTP_PASSWORD')

    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        raise RuntimeError("Email configuration is not set")

    msg = EmailMessage()
    msg['Subject'] = "Тестовое письмо"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg.set_content("Hello world")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
    print("Письмо отправлено")

# Пример вызова функции:
if __name__ == "__main__":
    send_simple_email("rombritvin9@gmail.com")

