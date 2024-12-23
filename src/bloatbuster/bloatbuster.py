import os
import asyncio
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import yaml
from loguru import logger
from tqdm import tqdm
from typing import Dict, Tuple, List

# Ladda konfiguration från fil
def load_config(config_file: str) -> dict:
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

config_path = os.path.join(os.path.dirname(__file__), '../../config.yaml')
config = load_config(config_path)
EXCLUDE_FILE_EXTENSIONS = config.get('exclude_extensions', [])
LARGE_FILE_THRESHOLD = config.get('large_file_threshold', 52428800)  # Default 50 MB
MANY_FILES_THRESHOLD = config.get('many_files_threshold', 100)

logger.add("bloatbuster.log", rotation="500 MB")

def dynamic_adjustment():
    # Placeholder för framtida dynamisk justering
    pass

async def get_file_size(file_path: str) -> int:
    return os.path.getsize(file_path)

async def get_excludable_files_info(directory: str) -> Tuple[Dict[str, int], Dict[str, int]]:
    file_count_by_type = defaultdict(int)
    size_by_type = defaultdict(int)
    tasks = []

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        for root, dirs, files in os.walk(directory):
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in EXCLUDE_FILE_EXTENSIONS:
                    file_path = os.path.join(root, file)
                    tasks.append((ext, file_path, loop.run_in_executor(executor, get_file_size, file_path)))

    for ext, file_path, task in tqdm(tasks, desc="Bearbetar filer", unit="fil"):
        file_size = await task
        file_count_by_type[ext] += 1
        size_by_type[ext] += file_size

    return file_count_by_type, size_by_type

def print_summary(file_count_by_type: Dict[str, int], size_by_type: Dict[str, int]):
    total_files = 0
    total_size = 0
    summary = []

    for file_type in file_count_by_type:
        count = file_count_by_type[file_type]
        size = size_by_type[file_type]
        summary.append((file_type, count, size))
        total_files += count
        total_size += size

    summary = sorted(summary, key=lambda x: x[1], reverse=True)

    large_files = [file_type for file_type, count, size in summary if size > LARGE_FILE_THRESHOLD]
    many_files = [file_type for file_type, count, size in summary if count > MANY_FILES_THRESHOLD]

    print("Sammanfattning av exkluderbara filer efter filtyp:")
    print("{:<10} {:<15} {:<15}".format("Filtyp", "Antal filer", "Total storlek (MB)"))
    print("-" * 40)
    for file_type, count, size in summary:
        print("{:<10} {:<15} {:.2f}".format(file_type, count, size / 1024 / 1024))

    print("\nTotalt antal exkluderbara filer: {}".format(total_files))
    print("Total storlek på exkluderbara filer: {:.2f} MB".format(total_size / 1024 / 1024))

    print("\nPotentiellt tidskrävande filer att bearbeta:")
    if large_files:
        print("Stora filer (över 50 MB):", ", ".join(large_files))
    else:
        print("Inga stora filer (över 50 MB) identifierade.")

    if many_files:
        print("Många filer (över 100 filer):", ", ".join(many_files))
    else:
        print("Inga filtyper med över 100 filer identifierade.")

def save_summary_to_file(file_count_by_type: Dict[str, int], size_by_type: Dict[str, int], output_file: str):
    summary = {
        'total_files': sum(file_count_by_type.values()),
        'total_size': sum(size_by_type.values()),
        'details': [
            {'file_type': file_type, 'file_count': file_count_by_type[file_type], 'total_size': size_by_type[file_type]}
            for file_type in file_count_by_type
        ]
    }

    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=4)

    print("\nRapport sparad till {}".format(output_file))

# Användning
directory = '/root/termux_home/storage/downloads/sync/Projects'
output_file = 'exclude_files_report.json'

async def main():
    dynamic_adjustment()  # Kör dynamisk justering av tröskelvärden
    file_count_by_type, size_by_type = await get_excludable_files_info(directory)
    print_summary(file_count_by_type, size_by_type)
    save_summary_to_file(file_count_by_type, size_by_type, output_file)

if __name__ == '__main__':
    logger.info("Startar Bloatbuster...")
    asyncio.run(main())
    logger.info("Bloatbuster slutförd.")
