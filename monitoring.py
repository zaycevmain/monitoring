import time
import os
import sys
import psutil
import requests
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.progress import Progress, BarColumn, TextColumn
from rich.text import Text
from rich.layout import Layout
from rich.align import Align
from rich import box
from rich.rule import Rule
from rich.markdown import Markdown
from rich.traceback import install
from rich.style import Style
from rich.prompt import Prompt, Confirm
import subprocess
import configparser
from datetime import datetime
import json
import csv

try:
    import psycopg2
except ImportError:
    psycopg2 = None

install()

class ConfigManager:
    DEFAULT_CONFIG = {
        'monitoring': {
            'update_interval': '2',
            'history_length': '60',
            'enable_notifications': 'true',
            'log_to_csv': 'true'
        },
        'postgresql': {
            'host': 'localhost',
            'port': '5432',
            'database': 'postgres',
            'user': 'postgres',
            'password': ''
        },
        'application': {
            'service_name': 'platform5.service',
            'url': 'http://localhost:8081'
        },
        'alerts': {
            'cpu_threshold': '80',
            'memory_threshold': '80',
            'disk_threshold': '80',
            'temp_threshold': '75',
            'cpu_sustained_load_time': '60'
        }
    }

    def __init__(self, config_file='monitoring.conf'):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load()

    def load(self):
        try:
            if os.path.exists(self.config_file):
                self.config.read(self.config_file, encoding='utf-8')
            self._set_defaults()
        except Exception as e:
            console.print(f"[red]Ошибка при загрузке конфигурации: {str(e)}[/red]")
            self._set_defaults()

    def _set_defaults(self):
        try:
            for section, values in self.DEFAULT_CONFIG.items():
                if not self.config.has_section(section):
                    self.config.add_section(section)
                for key, value in values.items():
                    if not self.config.has_option(section, key):
                        self.config.set(section, key, value)
            self.save()
        except Exception as e:
            console.print(f"[red]Ошибка при установке значений по умолчанию: {str(e)}[/red]")

    def save(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
        except Exception as e:
            console.print(f"[red]Ошибка при сохранении конфигурации: {str(e)}[/red]")
            # Попробуем сохранить во временный файл
            temp_file = f"{self.config_file}.tmp"
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    self.config.write(f)
                os.replace(temp_file, self.config_file)
            except Exception as e2:
                console.print(f"[red]Не удалось сохранить даже во временный файл: {str(e2)}[/red]")

    def get(self, section, key, fallback=None):
        try:
            if not self.config.has_section(section):
                self._set_defaults()
            return self.config.get(section, key, fallback=fallback)
        except Exception as e:
            console.print(f"[red]Ошибка при получении значения {section}.{key}: {str(e)}[/red]")
            return fallback

    def set(self, section, key, value):
        try:
            if not self.config.has_section(section):
                self.config.add_section(section)
            # Убедимся, что значение является строкой и не содержит суррогатных пар
            safe_value = str(value).encode('utf-8', errors='ignore').decode('utf-8')
            self.config.set(section, key, safe_value)
            self.save()
        except Exception as e:
            console.print(f"[red]Ошибка при установке значения {section}.{key}: {str(e)}[/red]")

    def get_postgresql_config(self):
        return {
            'host': self.get('postgresql', 'host'),
            'port': self.get('postgresql', 'port'),
            'database': self.get('postgresql', 'database'),
            'user': self.get('postgresql', 'user'),
            'password': self.get('postgresql', 'password')
        }

    def get_application_config(self):
        return {
            'service_name': self.get('application', 'service_name'),
            'url': self.get('application', 'url')
        }

    def get_alerts_config(self):
        return {
            'cpu_threshold': float(self.get('alerts', 'cpu_threshold')),
            'memory_threshold': float(self.get('alerts', 'memory_threshold')),
            'disk_threshold': float(self.get('alerts', 'disk_threshold')),
            'temp_threshold': float(self.get('alerts', 'temp_threshold')),
            'cpu_sustained_load_time': int(self.get('alerts', 'cpu_sustained_load_time'))
        }

    def get_monitoring_config(self):
        return {
            'update_interval': float(self.get('monitoring', 'update_interval')),
            'history_length': int(self.get('monitoring', 'history_length')),
            'enable_notifications': self.get('monitoring', 'enable_notifications').lower() == 'true',
            'log_to_csv': self.get('monitoring', 'log_to_csv').lower() == 'true'
        }

    def edit_interactive(self):
        console.clear()
        console.print("[bold cyan]=== Настройка конфигурации ===\n")
        
        try:
            for section in self.config.sections():
                console.print(f"\n[bold yellow]{section.upper()}:")
                for key, value in self.config.items(section):
                    try:
                        new_value = Prompt.ask(
                            f"{key}",
                            default=value,
                            show_default=True
                        )
                        if new_value != value:
                            self.set(section, key, new_value)
                    except Exception as e:
                        console.print(f"[red]Ошибка при редактировании {section}.{key}: {str(e)}[/red]")
                        continue
            
            console.print("\n[green]Конфигурация сохранена![/green]")
            if Confirm.ask("Перезапустить мониторинг?"):
                return True
            return False
        except Exception as e:
            console.print(f"\n[red]Ошибка при сохранении конфигурации: {str(e)}[/red]")
            input("\nНажмите Enter для продолжения...")
            return False

# Удаляем старые функции конфигурации
# CONFIG_FILE = "monitoring.conf"
LOG_FILE = "monitoring_log.csv"

console = Console()

# График для истории
class History:
    def __init__(self, maxlen=60, default_value=0):
        self.maxlen = maxlen
        self.default_value = default_value
        self.data = [default_value]  # Инициализируем с одним значением по умолчанию
    
    def append(self, value):
        self.data.append(value)
        if len(self.data) > self.maxlen:
            self.data.pop(0)
    
    def get(self):
        return self.data

cpu_hist = History()
mem_hist = History()
disk_hist = History()
temp_hist = History()
pg_conn_hist = History()
pg_long_hist = History()
http_hist = History()

# PostgreSQL мониторинг
def pg_status(conf):
    if not psycopg2:
        return (False, 'psycopg2 не установлен', 0, 0, 'N/A')
    try:
        conn = psycopg2.connect(
            host=conf['host'], port=conf['port'], dbname=conf['database'], user=conf['user'], password=conf['password'],
            connect_timeout=2
        )
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM pg_stat_activity;")
        active_conn = int(cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM pg_stat_activity WHERE state='active' AND now()-query_start > interval '30 seconds';")
        long_queries = int(cur.fetchone()[0])
        cur.execute(f"SELECT pg_size_pretty(pg_database_size('{conf['database']}'));")
        db_size = cur.fetchone()[0]
        cur.close()
        conn.close()
        return (True, 'OK', active_conn, long_queries, db_size)
    except Exception as e:
        return (False, str(e), 0, 0, 'N/A')

# Статус systemd
def service_status(service):
    try:
        out = subprocess.check_output(['systemctl', 'is-active', service], stderr=subprocess.STDOUT).decode().strip()
        return out == 'active'
    except Exception:
        return False

# HTTP статус
def http_status(url):
    try:
        r = requests.get(url, timeout=2)
        return r.status_code
    except Exception:
        return None

# Температура CPU (lm-sensors)
def cpu_temp():
    try:
        out = subprocess.check_output(['sensors'], stderr=subprocess.STDOUT).decode()
        for line in out.splitlines():
            if 'Core 0' in line or 'Tctl' in line:
                parts = line.split()
                for p in parts:
                    if p.startswith('+') and p.endswith('°C'):
                        return float(p[1:-2])
        return None
    except Exception:
        return None

# График линии (ASCII)
def line_chart(data, width=50, height=8, color='cyan', alert_level=None):
    if not data:
        return ""
    min_v = min(data)
    max_v = max(data)
    rng = max_v - min_v if max_v != min_v else 1
    scaled = [int((v - min_v) / rng * (height - 1)) for v in data]
    chart = [''] * height
    for y in range(height-1, -1, -1):
        row = ''
        for x in range(-width, 0):
            idx = x + len(data)
            if 0 <= idx < len(data) and scaled[idx] == y:
                # Цвет по алерту
                if alert_level and data[idx] >= alert_level:
                    row += '[red]▄[/]'
                else:
                    row += f'[{color}]▄[/]'
            else:
                row += ' '
        chart[height-1-y] = row
    return '\n'.join(chart)

# Логирование
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w') as f:
        f.write('time,cpu,mem,disk,temp,pg_conn,pg_long,http\n')

def log_metrics(cpu, mem, disk, temp, pg_conn, pg_long, http, config_manager):
    if not config_manager.get_monitoring_config()['log_to_csv']:
        return
        
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            f.write('time,cpu,mem,disk,temp,pg_conn,pg_long,http\n')
            
    with open(LOG_FILE, 'a') as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')},{cpu},{mem},{disk},{temp},{pg_conn},{pg_long},{http}\n")

# Алерты
def get_alerts(cpu, mem, disk, temp, pg_ok, app_ok, http_code, alerts_config):
    alerts = []
    if cpu > alerts_config['cpu_threshold']:
        alerts.append("[red]CPU: высокая загрузка[/red]")
    if mem > alerts_config['memory_threshold']:
        alerts.append("[red]Memory: недостаточно свободной памяти[/red]")
    if disk > alerts_config['disk_threshold']:
        alerts.append("[red]Disk: критически мало места[/red]")
    if temp is not None and temp > alerts_config['temp_threshold']:
        alerts.append("[red]CPU Temperature: перегрев[/red]")
    if not pg_ok:
        alerts.append("[red]PostgreSQL: сервис недоступен[/red]")
    if not app_ok:
        alerts.append("[red]Application: сервис остановлен[/red]")
    if http_code != 200:
        status = 'недоступен' if http_code is None or http_code == 0 else str(http_code)
        alerts.append(f"[red]HTTP Status: {status}[/red]")
    return alerts

# Всплывающее уведомление
def notify(alerts, config_manager):
    if not config_manager.get_monitoring_config()['enable_notifications']:
        return
    
    for alert in alerts:
        console.bell()
        console.print(Panel(alert, style="bold red", title="ALERT!"))

def sparkline(data, width=30, height=1):
    """Создает спарклайн (мини-график) из данных"""
    if not data or len(data) == 0:
        return "─" * width
    
    blocks = "▁▂▃▄▅▆▇█"
    min_val = min(data)
    max_val = max(data)
    rng = max_val - min_val if max_val != min_val else 1
    
    # Ресемплируем данные до нужной ширины
    step = len(data) / width if len(data) > width else 1
    sampled_data = []
    for i in range(width):
        idx = min(int(i * step), len(data) - 1)
        sampled_data.append(data[idx])
    
    # Создаем спарклайн
    line = ""
    for val in sampled_data:
        height_idx = int(((val - min_val) / rng) * (len(blocks) - 1))
        line += blocks[height_idx]
    
    return line

def bar_chart(data, width=30, height=8, title="", color="blue", scale_to_max=False):
    """Создает столбчатую диаграмму с заголовком"""
    if not data or len(data) == 0:
        empty_chart = []
        if title:
            header = f"─── {title} "
            header += "─" * (width - len(title) - 4)
            empty_chart.append(header)
        empty_chart.extend([" " * width] * height)
        return Text("\n".join(empty_chart), style=color)
    
    chart = []
    max_val = max(data)
    min_val = min(data)
    
    # Если scale_to_max=False, используем фиксированный диапазон 0-100 для процентов
    if not scale_to_max and max_val <= 100:
        max_val = 100
        min_val = 0
    
    rng = max_val - min_val if max_val != min_val else 1
    
    # Ресемплируем данные до нужной ширины
    step = len(data) / width if len(data) > width else 1
    sampled_data = []
    for i in range(width):
        idx = min(int(i * step), len(data) - 1)
        sampled_data.append(data[idx])
    
    # Создаем столбцы
    for y in range(height - 1, -1, -1):
        row = ""
        for val in sampled_data:
            bar_height = int(((val - min_val) / rng) * (height - 1))
            if y <= bar_height:
                row += "▀"  # Используем более тонкий символ
            else:
                row += " "
        chart.append(row)
    
    # Добавляем заголовок
    if title:
        current = sampled_data[-1]
        header = f"─── {title} [{current:.1f}] "
        header += "─" * (width - len(title) - len(f" [{current:.1f}]") - 4)
        chart.insert(0, header)
    
    return Text("\n".join(chart), style=color)

def get_load_color(value, warning=70, critical=90):
    """Возвращает цвет в зависимости от нагрузки"""
    if value >= critical:
        return "red"
    elif value >= warning:
        return "yellow"
    return "green"

def get_load_style(value, warning=70, critical=90):
    """Возвращает стиль для отображения нагрузки"""
    return f"bold {get_load_color(value, warning, critical)}"

def get_resource_indicator(value, warning=70, critical=90):
    """Возвращает цветной индикатор ⬤ в зависимости от нагрузки."""
    if value >= critical:
        return Text("⬤", style="bold red")
    elif value >= warning:
        return Text("⬤", style="bold yellow")
    return Text("⬤", style="bold green")

def load_bar(value, width=50, warning=70, critical=90):
    """Создает индикатор нагрузки в стиле htop"""
    filled_width = int(value * width / 100)
    empty_width = width - filled_width
    
    # Создаем сегменты разных цветов
    segments = []
    if filled_width > 0:
        color = get_load_color(value, warning, critical)
        segments.append(Text("█" * filled_width, style=f"bold {color}"))
    if empty_width > 0:
        segments.append(Text("░" * empty_width, style="dim"))
    
    # Добавляем процент
    bar = Text().join(segments)
    return Group(
        bar,
        Text(f"{value:>5.1f}%", style=get_load_style(value, warning, critical))
    )

def metric_line(label, value, max_value=100, width=50, warning=70, critical=90, unit=""):
    """Создает строку с меткой и индикатором нагрузки"""
    value_pct = (value / max_value * 100) if max_value > 0 else 0
    return Group(
        Text(f"{label:<15}", style="bold blue"),
        load_bar(value_pct, width, warning, critical),
        Text(f" {value}{unit}", style="dim")
    )

def render(config_manager):
    term_width, term_height = console.size
    minimal = term_width < 120 or term_height < 35
    compact = term_width < 80 or term_height < 25

    monitoring_config = config_manager.get_monitoring_config()
    alerts_config = config_manager.get_alerts_config()
    
    # CPU
    cpu = psutil.cpu_percent(interval=None)
    cpu_hist.append(cpu)
    per_cpu = psutil.cpu_percent(percpu=True)
    
    # Memory
    mem = psutil.virtual_memory()
    mem_hist.append(mem.percent)
    
    # Disk
    disk = psutil.disk_usage('/')
    disk_hist.append(disk.percent)
    
    # Temperature
    temp = cpu_temp()
    if temp is not None:
        temp_hist.append(temp)
    
    # PostgreSQL
    pg_config = config_manager.get_postgresql_config()
    pg_ok, pg_status_text, pg_conn_count, pg_long_queries, pg_size = pg_status(pg_config)
    if pg_conn_count is not None:
        pg_conn_hist.append(pg_conn_count)
    if pg_long_queries is not None:
        pg_long_hist.append(pg_long_queries)
    
    # App status
    app_config = config_manager.get_application_config()
    app_ok = service_status(app_config['service_name'])
    http_code = http_status(app_config['url'])
    if http_code is not None:
        http_hist.append(http_code)
    else:
        http_hist.append(0)  # Используем 0 как индикатор ошибки

    # Layout
    layout = Layout()
    
    if compact:
        layout.split_column(
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        main_content = Group(
            metric_line("CPU", cpu, width=30),
            metric_line("Memory", mem.percent, width=30),
            metric_line("Disk", disk.percent, width=30),
            Text(f"CPU Temp: {temp}°C" if temp is not None else "CPU Temp: N/A", style="cyan"),
            Rule(),
            Panel(
                Group(
                    Text("PostgreSQL", style="bold blue", justify="center"),
                    Text("Status: " + ("OK" if pg_ok else pg_status_text), 
                         style="bold green" if pg_ok else "bold red",
                         justify="center")
                ),
                border_style="blue",
                padding=(0, 2)
            ),
            Text(f"Connections: {pg_conn_count if pg_conn_count is not None else 'N/A'}", style="bold blue"),
            Panel(
                Group(
                    Text("Application", style="bold green", justify="center"),
                    Text("Status: " + ("Running" if app_ok else "Stopped"),
                         style="bold green" if app_ok else "bold red",
                         justify="center")
                ),
                border_style="green",
                padding=(0, 2)
            ),
            Text(f"HTTP Status: {http_code if http_code is not None else 'N/A'}", style="bold green" if http_code == 200 else "bold red")
        )
        
        layout["main"].update(Panel(main_content, title="System Monitor"))
        
    else:
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )
        
        layout["header"].update(
            Align.center(Text("SYSTEM & APPLICATION MONITORING", style="bold cyan"))
        )
        
        # Sustained CPU load calculation
        num_samples = int(alerts_config['cpu_sustained_load_time'] / monitoring_config['update_interval'])
        if num_samples > len(cpu_hist.data):
            num_samples = len(cpu_hist.data) # Use all available history if not enough data
        
        recent_cpu_history = list(cpu_hist.data)[-num_samples:] if num_samples > 0 else []
        avg_cpu_sustained = sum(recent_cpu_history) / len(recent_cpu_history) if recent_cpu_history else 0
            
        # System metrics
        cpu_warn = alerts_config['cpu_threshold'] * 0.9
        cpu_crit = alerts_config['cpu_threshold']
        mem_warn = alerts_config['memory_threshold'] * 0.9
        mem_crit = alerts_config['memory_threshold']
        disk_warn = alerts_config['disk_threshold'] * 0.9
        disk_crit = alerts_config['disk_threshold']
        temp_warn = alerts_config['temp_threshold'] * 0.9
        temp_crit = alerts_config['temp_threshold']

        system_resources_table = Table.grid(expand=True, padding=(0, 1))
        system_resources_table.add_column(ratio=1)
        system_resources_table.add_column(width=3, justify="center")

        # CPU
        system_resources_table.add_row(
            metric_line("CPU Total", cpu, width=40, warning=cpu_warn, critical=cpu_crit),
            get_resource_indicator(avg_cpu_sustained, warning=cpu_warn, critical=cpu_crit)
        )
        for i, perc in enumerate(per_cpu):
            system_resources_table.add_row(
                metric_line(f"  CPU {i}", perc, width=38, warning=cpu_warn, critical=cpu_crit)
            )
        system_resources_table.add_row(Rule())

        # Memory
        system_resources_table.add_row(
            metric_line("Memory", mem.percent, width=40, warning=mem_warn, critical=mem_crit),
            get_resource_indicator(mem.percent, warning=mem_warn, critical=mem_crit)
        )
        system_resources_table.add_row(
            Text(f"  Used: {mem.used // (1024*1024)} MB / {mem.total // (1024*1024)} MB", style="dim")
        )
        system_resources_table.add_row(Rule())

        # Disk
        system_resources_table.add_row(
            metric_line("Disk", disk.percent, width=40, warning=disk_warn, critical=disk_crit),
            get_resource_indicator(disk.percent, warning=disk_warn, critical=disk_crit)
        )
        system_resources_table.add_row(
            Text(f"  Used: {disk.used // (1024*1024*1024)} GB / {disk.total // (1024*1024*1024)} GB", style="dim")
        )
        system_resources_table.add_row(Rule())

        # Temperature
        if temp is not None:
            system_resources_table.add_row(
                metric_line("CPU Temp", temp, max_value=100, width=40, unit="°C", warning=temp_warn, critical=temp_crit),
                get_resource_indicator(temp, warning=temp_warn, critical=temp_crit)
            )
        else:
            system_resources_table.add_row(Text("CPU Temp: N/A", style="cyan"))


        system_content = Group(
            Text("System Resources", style="bold cyan"),
            Rule(),
            system_resources_table
        )
            
        # Services status
        pg_status_table = Table.grid(expand=True)
        pg_status_table.add_column(justify="center")
        pg_status_table.add_row(Text("PostgreSQL", style="bold cyan", justify="center"))
        pg_status_table.add_row(Text("━━━━━━━━━", style="blue", justify="center"))
        pg_status_table.add_row("")

        pg_status_table.add_row(Text("Connection", style="dim", justify="center"))
        pg_status_table.add_row("")
        if pg_ok:
            pg_status_table.add_row(
                Text.assemble(Text("⬤  ", style="bold green"), Text("✓ OK ✓", style="bold green"))
            )
        else:
            pg_status_table.add_row(
                Text.assemble(
                    Text("⬤  ", style="bold red"),
                    Text(f"✗ {pg_status_text} ✗", style="bold red", overflow="fold")
                )
            )

        app_status_table = Table.grid(expand=True)
        app_status_table.add_column(justify="center")
        app_status_table.add_row(Text("Application", style="bold cyan", justify="center"))
        app_status_table.add_row(Text("━━━━━━━━━", style="green", justify="center"))
        app_status_table.add_row("")

        # Service status
        app_status_table.add_row(Text("Service (systemd)", style="dim", justify="center"))
        app_status_table.add_row("")
        if app_ok:
            app_status_table.add_row(
                Text.assemble(Text("⬤  ", style="bold green"), Text("✓ RUNNING ✓", style="bold green"))
            )
        else:
            app_status_table.add_row(
                Text.assemble(Text("⬤  ", style="bold red"), Text("✗ STOPPED ✗", style="bold red"))
            )
        
        app_status_table.add_row("") # Spacer
        app_status_table.add_row(Text("· · ·", style="dim green", justify="center"))
        app_status_table.add_row("") # Spacer

        # HTTP status
        app_status_table.add_row(Text("Endpoint (HTTP)", style="dim", justify="center"))
        app_status_table.add_row("")
        if http_code == 200:
            status_text = '200 OK'
            app_status_table.add_row(
                Text.assemble(
                    Text("⬤  ", style="bold green"), 
                    Text(f"✓ {status_text} ✓", style="bold green")
                )
            )
        else:
            status_text = 'N/A' if http_code is None or http_code == 0 else str(http_code)
            app_status_table.add_row(
                Text.assemble(
                    Text("⬤  ", style="bold red"), 
                    Text(f"✗ {status_text} ✗", style="bold red")
                )
            )

        services_content = Group(
            Text("Services Status", style="bold magenta"),
            Rule(style="magenta"),
            Panel(
                pg_status_table,
                border_style="blue",
                padding=(1, 4),
                width=50
            ),
            Text(""),  # Пустая строка для отступа
            Group(
                Text(f"Active Connections: {pg_conn_count if pg_conn_count is not None else 'N/A'}", style="bold blue"),
                Text(f"Long Queries: {pg_long_queries if pg_long_queries is not None else 'N/A'}", 
                     style="yellow" if pg_long_queries and pg_long_queries > 0 else "blue"),
                Text(f"DB Size: {pg_size}", style="dim")
            ),
            Rule(style="magenta"),
            Panel(
                app_status_table,
                border_style="green",
                padding=(1, 4),
                width=50
            )
        )

        layout["left"].update(Panel(system_content, border_style="cyan"))
        layout["right"].update(Panel(services_content, border_style="magenta"))
    
    # Footer
    active_alerts = get_footer_alerts(
        cpu, mem.percent, disk.percent, temp,
        pg_ok, app_ok, http_code,
        alerts_config, avg_cpu_sustained
    )

    if active_alerts:
        alert_texts = [Text(a, style="bold red") for a in active_alerts]
        separator = Text(" | ", style="bold red")
        footer_renderable = separator.join(alert_texts)
    else:
        footer_text = f"Ctrl+C для выхода. Обновление раз в {monitoring_config['update_interval']} сек."
        footer_renderable = Text(footer_text, style="bold cyan")

    layout["footer"].update(Align.center(footer_renderable))
    
    return layout

def get_footer_alerts(cpu, mem, disk, temp, pg_ok, app_ok, http_code, alerts_config, avg_cpu_sustained):
    """Возвращает список текущих проблем для футера."""
    alerts = []
    if avg_cpu_sustained > alerts_config['cpu_threshold']:
        alerts.append(f"ДЛИТЕЛЬНАЯ НАГРУЗКА CPU: {avg_cpu_sustained:.0f}%")
    if mem > alerts_config['memory_threshold']:
        alerts.append(f"MEM Высокая нагрузка: {mem:.0f}%")
    if disk > alerts_config['disk_threshold']:
        alerts.append(f"DISK Мало места: {disk:.0f}%")
    if temp is not None and temp > alerts_config['temp_threshold']:
        alerts.append(f"CPU Температура: {temp:.0f}°C")
    if not pg_ok:
        alerts.append("POSTGRESQL НЕДОСТУПЕН")
    if not app_ok:
        alerts.append("СЕРВИС ПРИЛОЖЕНИЯ ОСТАНОВЛЕН")
    if http_code != 200:
        alerts.append(f"ОШИБКА HTTP: {http_code or 'N/A'}")
    return alerts

# Главное меню
def main_menu():
    config_manager = ConfigManager()
    while True:
        console.clear()
        console.print("[bold cyan]=== Меню мониторинга ===\n")
        console.print("[1] Запустить мониторинг")
        console.print("[2] Настройка конфигурации")
        console.print("[3] Просмотр логов")
        console.print("[4] Выход\n")
        
        choice = Prompt.ask("Выберите действие", choices=["1", "2", "3", "4"])
        
        if choice == "1":
            start_monitoring(config_manager)
        elif choice == "2":
            if config_manager.edit_interactive():
                start_monitoring(config_manager)
        elif choice == "3":
            view_logs()
        else:
            sys.exit(0)

def start_monitoring(config_manager):
    try:
        monitoring_config = config_manager.get_monitoring_config()
        update_interval = monitoring_config['update_interval']
        
        with Live(
            render(config_manager),
            refresh_per_second=1/update_interval,
            screen=True
        ) as live:
            try:
                while True:
                    live.update(render(config_manager))
                    time.sleep(update_interval)
            except KeyboardInterrupt:
                return
    except Exception as e:
        console.print(f"\n[red]Ошибка при запуске мониторинга: {str(e)}[/red]")
        input("\nНажмите Enter для продолжения...")
        return

def view_logs():
    """Отображает статистику из файла логов."""
    try:
        if not os.path.exists(LOG_FILE):
            console.print("[red]Файл логов не найден![/red]")
            input("\nНажмите Enter для возврата в меню...")
            return
        
        try:
            with open(LOG_FILE, 'r') as f:
                reader = csv.reader(f)
                header = next(reader)
                data = list(reader)

            if not data:
                console.print("[yellow]Файл логов пуст.[/yellow]")
                input("\nНажмите Enter для возврата в меню...")
                return

            # Последние 10 записей
            console.print("\n[bold]Последние 10 записей:[/bold]")
            log_table = Table(box=box.ROUNDED)
            for col in header:
                log_table.add_column(col)
            
            for row in data[-10:]:
                styled_row = []
                for i, value in enumerate(row):
                    if i > 0: # Пропускаем время
                        try:
                            val = float(value)
                            if header[i] == 'cpu':
                                styled_row.append(f"[{get_load_color(val)}]"+value+f"[/[{get_load_color(val)}]]")
                            else:
                                 styled_row.append(value)
                        except (ValueError, TypeError):
                            styled_row.append(value)
                    else:
                        styled_row.append(value)
                log_table.add_row(*styled_row)
            
            console.print(log_table)

            # Статистика
            stats_table = Table(title="Статистика по метрикам", box=box.ROUNDED, show_header=True, header_style="bold magenta")
            stats_table.add_column("Метрика")
            stats_table.add_column("Среднее")
            stats_table.add_column("Максимум")
            stats_table.add_column("Минимум")

            for i, col in enumerate(header[1:], 1):  # Пропускаем колонку времени
                values = []
                for row in data:
                    try:
                        # Пытаемся преобразовать значение в число, пропуская некорректные
                        if len(row) > i and row[i] not in ('', 'None', 'N/A'):
                            values.append(float(row[i]))
                    except (ValueError, IndexError):
                        continue # Пропускаем строки с ошибками данных

                if values:
                    avg = sum(values) / len(values)
                    max_val = max(values)
                    min_val = min(values)
                    stats_table.add_row(col, f"{avg:.2f}", f"{max_val:.2f}", f"{min_val:.2f}")
                else:
                    stats_table.add_row(col, "N/A", "N/A", "N/A")

            console.print(stats_table)
            input("\nНажмите Enter для возврата в меню...")

        except Exception as e:
            console.print(f"[red]Ошибка чтения логов: {e}[/red]")
            input("\nНажмите Enter для возврата в меню...")
    except KeyboardInterrupt:
        console.print("\n[yellow]Возврат в главное меню...[/yellow]")
        return

if __name__ == "__main__":
    main_menu() 
