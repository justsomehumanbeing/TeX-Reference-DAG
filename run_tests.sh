#!/bin/sh
python -m pytest -q
python test_environment_parsing.py
python test_full_document.py
python test_self_reference.py
