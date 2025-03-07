from .. import loader, utils
import subprocess
import os

@loader.tds
class DanteSetupMod(loader.Module):
    """Автоматическая установка и настройка Dante SOCKS5-прокси"""

    strings = {"name": "DanteSetup"}

    async def client_ready(self, client, db):
        self._client = client

    async def dantecmd(self, message):
        """Устанавливает и настраивает SOCKS5-прокси (Dante) на 45.67.215.203:80"""
        await utils.answer(message, "🔧 Проверяю систему и устанавливаю Dante SOCKS5-прокси...")

        try:
            # Проверка, установлен ли Dante
            dante_installed = subprocess.run("dpkg -l | grep dante-server", shell=True, stdout=subprocess.PIPE).stdout.decode()
            if "dante-server" in dante_installed:
                await utils.answer(message, "✅ Dante уже установлен. Перенастраиваю...")
            else:
                # Установка Dante
                subprocess.run("sudo apt update && sudo apt install dante-server -y", shell=True, check=True)

            # Конфигурация Dante
            dante_config = """
logoutput: syslog
internal: 45.67.215.203 port = 80
external: 45.67.215.203
socksmethod: none

user.privileged: root
user.unprivileged: nobody

client pass {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    log: connect disconnect
}

socks pass {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    log: connect disconnect
}
"""
            # Запись конфига
            with open("/etc/danted.conf", "w") as conf_file:
                conf_file.write(dante_config)

            # Проверка и открытие порта в UFW, если он включен
            ufw_status = subprocess.run("sudo ufw status", shell=True, stdout=subprocess.PIPE).stdout.decode()
            if "active" in ufw_status:
                subprocess.run("sudo ufw allow 80/tcp", shell=True)

            # Перезапуск Dante
            subprocess.run("sudo systemctl restart danted", shell=True, check=True)

            # Проверка статуса сервиса
            dante_status = subprocess.run("sudo systemctl is-active danted", shell=True, stdout=subprocess.PIPE).stdout.decode().strip()
            if dante_status != "active":
                raise Exception("Dante не запустился. Проверь логи: `sudo journalctl -u danted --no-pager`")

            await utils.answer(message, f"✅ Прокси успешно настроен!\n\n"
                                        f"🔹 **Тип:** SOCKS5\n"
                                        f"🌍 **IP:** `45.67.215.203`\n"
                                        f"🔢 **Порт:** `80`\n\n"
                                        f"📌 Теперь можешь использовать его в Telegram!")

        except subprocess.CalledProcessError as e:
            await utils.answer(message, f"❌ Ошибка выполнения команды: {e}")
        except Exception as e:
            await utils.answer(message, f"❌ Ошибка: {e}")
