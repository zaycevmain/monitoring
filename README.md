# System & Application Monitoring Tool / Утилита для мониторинга системы и приложений

---

A terminal-based tool for comprehensive monitoring of system resources (CPU, Memory, Disk, Temperature) and specific services like PostgreSQL and web applications. Written in Python using the `rich` library.

---

Инструмент для комплексного мониторинга системных ресурсов (ЦП, ОЗУ, Диск, Температура) и служб, таких как PostgreSQL и веб-приложения, работающий в терминале. Написан на Python с использованием библиотеки `rich`.

---

## ⚠️ Requirements / Требования

Before using this script, make sure the following packages are installed on your system. The installation script will handle this automatically.

Перед использованием скрипта убедитесь, что в вашей системе установлены следующие пакеты. Скрипт установки сделает это автоматически.

**Required packages:**
- `git`
- `python3`
- `lm-sensors`
- `python3-rich`
- `python3-psutil`
- `python3-requests`
- `python3-psycopg2`

### How to install dependencies (Ubuntu/Debian):
The provided installation script handles everything.
```bash
sudo bash install_monitoring.sh
```

### Как установить зависимости (Ubuntu/Debian):
Входящий в состав репозитория скрипт установки сделает всё за вас.
```bash
sudo bash install_monitoring.sh
```

---

## 🇬🇧 Installation and Usage (English)

1.  **Go to a directory of your choice (e.g., your home directory):**
    ```bash
    cd ~
    ```
2.  **Clone the repository:**
    ```bash
    git clone https://github.com/zaycevmain/monitoring.git
    cd monitoring
    ```
3.  **Run the installation script with superuser privileges:**
    ```bash
    sudo bash install_monitoring.sh
    ```
4.  **Run the main script:**
    ```bash
    python3 monitoring.py
    ```

5.  **Follow the interactive menu:**
    -   **Run Monitoring**: Starts the main monitoring dashboard.
    -   **Configuration**: Allows you to interactively edit the `monitoring.conf` file. This is crucial for the first run.
    -   **View Logs**: Shows statistics and the last entries from the CSV log file.
    -   **Exit**: Closes the application.

---

## 🇷🇺 Установка и использование (Russian)

1.  **Перейдите в удобную для вас директорию (например, в домашнюю):**
    ```bash
    cd ~
    ```
2.  **Склонируйте репозиторий:**
    ```bash
    git clone https://github.com/zaycevmain/monitoring.git
    cd monitoring
    ```
3.  **Запустите скрипт установки с правами суперпользователя:**
    ```bash
    sudo bash install_monitoring.sh
    ```
4.  **Запустите основной скрипт:**
    ```bash
    python3 monitoring.py
    ```

5.  **Следуйте интерактивному меню:**
    -   **Запустить мониторинг**: Открывает основную панель мониторинга.
    -   **Настройка конфигурации**: Позволяет интерактивно редактировать файл `monitoring.conf`. Крайне важно выполнить при первом запуске.
    -   **Просмотр логов**: Показывает статистику и последние записи из лог-файла.
    -   **Выход**: Завершает работу программы.

---

## ⚙️ Configuration / Настройка (`monitoring.conf`)

The behavior of the script is controlled by the `monitoring.conf` file, which is created automatically on the first run. You can edit it via the "Configuration" menu item.

Поведение скрипта управляется файлом `monitoring.conf`, который создаётся при первом запуске. Вы можете редактировать его через пункт меню "Настройка конфигурации".

-   **`[monitoring]`**
    -   `update_interval`: Screen refresh rate in seconds. / Интервал обновления экрана в секундах.
    -   `history_length`: Number of data points to keep for history. / Количество точек данных для истории.
    -   `log_to_csv`: `true` or `false` to enable/disable CSV logging. / Включить/отключить логирование.

-   **`[postgresql]`**
    -   `host`, `port`, `database`, `user`, `password`: Connection details for your PostgreSQL database. / Параметры для подключения к вашей базе данных PostgreSQL.

-   **`[application]`**
    -   `service_name`: The name of the `systemd` service for your application (e.g., `my-app.service`). / Имя вашего `systemd`-сервиса (например, `my-app.service`).
    -   `url`: The HTTP(S) endpoint to check for a `200 OK` status. / Адрес (HTTP/HTTPS), который проверяется на получение статуса `200 OK`.

-   **`[alerts]`**
    -   `cpu_threshold`, `memory_threshold`, `disk_threshold`: Percentage threshold for triggering an alert. / Порог в процентах для срабатывания оповещения.
    -   `temp_threshold`: Temperature in Celsius for the CPU temperature alert. / Порог в градусах Цельсия для оповещения о температуре ЦП.
    -   `cpu_sustained_load_time`: Time in seconds the high CPU load must persist to trigger an alert. / Время в секундах, которое должна удерживаться высокая нагрузка на ЦП для срабатывания оповещения.

---

**If you have any questions or issues, please create an issue on GitHub.**

**Если возникли вопросы или проблемы — создайте issue на GitHub.** 
