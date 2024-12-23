import sys
import os
import pytest
from unittest.mock import patch, mock_open
import json
import asyncio

# Lägg till src-katalogen till sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from bloatbuster import bloatbuster

def test_load_config():
    config = bloatbuster.load_config("config.yaml")
    assert config["exclude_extensions"]
    assert config["large_file_threshold"] == 52428800
    assert config["many_files_threshold"] == 100

def test_get_file_size():
    # Skapa en tillfällig fil för testning
    test_file = "testfile.tmp"
    with open(test_file, "w") as f:
        f.write("test")

    size = os.path.getsize(test_file)
    assert size == 4  # "test" är 4 bytes

    os.remove(test_file)

@patch('bloatbuster.bloatbuster.os.path.getsize')
@patch('bloatbuster.bloatbuster.os.walk')
@patch('bloatbuster.bloatbuster.load_config')
def test_get_excludable_files_info(mock_load_config, mock_os_walk, mock_getsize):
    mock_load_config.return_value = {
        "exclude_extensions": [".tmp", ".log"],
        "large_file_threshold": 52428800,
        "many_files_threshold": 100
    }
    mock_os_walk.return_value = [
        ('/some/directory', ('subdir',), ('file1.tmp', 'file2.log', 'file3.txt')),
    ]
    mock_getsize.side_effect = [100, 200, 300]

    directory = "/some/directory"
    file_count_by_type, size_by_type = asyncio.run(bloatbuster.get_excludable_files_info(directory))

    assert file_count_by_type['.tmp'] == 1
    assert file_count_by_type['.log'] == 1
    assert file_count_by_type['.txt'] == 0
    assert size_by_type['.tmp'] == 100
    assert size_by_type['.log'] == 200
    assert size_by_type['.txt'] == 0

def test_print_summary():
    file_count_by_type = {'.tmp': 3, '.log': 2}
    size_by_type = {'.tmp': 30000000, '.log': 10000000}

    bloatbuster.LARGE_FILE_THRESHOLD = 50000000  # 50 MB
    bloatbuster.MANY_FILES_THRESHOLD = 2

    # Fånga utdata från funktionen
    with patch('builtins.print') as mocked_print:
        bloatbuster.print_summary(file_count_by_type, size_by_type)

    # Kontrollera att utskriften är korrekt
    mocked_print.assert_any_call("Sammanfattning av exkluderbara filer efter filtyp:")
    mocked_print.assert_any_call("{:<10} {:<15} {:<15}".format("Filtyp", "Antal filer", "Total storlek (MB)"))
    mocked_print.assert_any_call("-" * 40)
    mocked_print.assert_any_call("{:<10} {:<15} {:.2f}".format('.tmp', 3, 30000000 / 1024 / 1024))
    mocked_print.assert_any_call("{:<10} {:<15} {:.2f}".format('.log', 2, 10000000 / 1024 / 1024))
    mocked_print.assert_any_call("\nTotalt antal exkluderbara filer: {}".format(5))
    mocked_print.assert_any_call("Total storlek på exkluderbara filer: {:.2f} MB".format((30000000 + 10000000) / 1024 / 1024))

@patch('bloatbuster.bloatbuster.json.dump')
def test_save_summary_to_file(mock_json_dump):
    file_count_by_type = {'.tmp': 3, '.log': 2}
    size_by_type = {'.tmp': 30000000, '.log': 10000000}
    output_file = "exclude_files_report.json"

    bloatbuster.save_summary_to_file(file_count_by_type, size_by_type, output_file)

    summary = {
        'total_files': 5,
        'total_size': 40000000,
        'details': [
            {'file_type': '.tmp', 'file_count': 3, 'total_size': 30000000},
            {'file_type': '.log', 'file_count': 2, 'total_size': 10000000}
        ]
    }

    # Kontrollera att json.dump kallades med rätt argument
    mock_json_dump.assert_called_with(summary, mock_open().__enter__(), indent=4)
