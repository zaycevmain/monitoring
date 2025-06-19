#!/bin/bash
# Скрипт для установки зависимостей мониторинга
# Запускать с sudo: sudo bash install_monitoring.sh
set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Начало установки зависимостей для скрипта мониторинга ===${NC}"

# 1. Обновление списка пакетов
echo -e "\n${YELLOW}> Шаг 1: Обновление списка пакетов (apt update)...${NC}"
apt-get update -y

# 2. Установка системных утилит и Python-пакетов через apt
echo -e "\n${YELLOW}> Шаг 2: Установка всех необходимых пакетов через apt...${NC}"
apt-get install -y python3 lm-sensors python3-rich python3-psutil python3-requests python3-psycopg2

echo -e "\n${GREEN}=== Установка успешно завершена! ===${NC}"
echo -e "Скрипт мониторинга готов к запуску."
echo -e "Для корректного отображения температуры CPU может потребоваться первоначальная настройка сенсоров."
echo -e "Рекомендуется запустить команду: ${YELLOW}sudo sensors-detect${NC} и ответить на вопросы (обычно достаточно нажимать Enter)."
echo -e "\nЗапуск скрипта мониторинга: ${GREEN}python3 monitoring.py${NC}" 
