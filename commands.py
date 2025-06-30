import subprocess
import re

def run_analiz_script():
    subprocess.run(['python', 'ANALIZ.py'])

def generate_commands(result_file, commands_file):
    with open(commands_file, 'w') as commands:
        with open(result_file, 'r') as results:
            for line in results:
                match = re.search(r'Схожесть: (\d+\.\d+)%', line)
                if match:
                    similarity = float(match.group(1))
                    if similarity > 75:
                        command = "Корректировка маршрута не требуется"
                    elif similarity > 50:
                        command = "Рекомендована корректировка"
                    elif similarity > 30:
                        command = "Необходима корректировка маршрута"
                    else:
                        command = "Критическое схождение с маршрута. Необходима срочная корректировка"
                    commands.write(f"{command} - Схожесть {similarity:.2f}%\n")

if __name__ == "__main__":
    run_analiz_script()
    generate_commands('result.txt', 'commands.txt')
    print("Команды сгенерированы и сохранены в commands.txt.")
