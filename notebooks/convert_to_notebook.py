#!/usr/bin/env python3
"""
Convert bee_processing_FIXED.py to Jupyter notebook
Run: python convert_to_notebook.py
"""

import json
import re

# Read the Python file
with open('bee_processing_FIXED.py', 'r') as f:
    content = f.read()

# Create notebook structure
notebook = {
    "nbformat": 4,
    "nbformat_minor": 0,
    "metadata": {
        "colab": {
            "provenance": [],
            "gpuType": "T4"
        },
        "kernelspec": {
            "name": "python3",
            "display_name": "Python 3"
        },
        "language_info": {
            "name": "python"
        },
        "accelerator": "GPU"
    },
    "cells": []
}

# Split by cell markers using regex
cell_pattern = r'# ={40,}\s*\n# CELL (\d+): (.+?)\s*\n# ={40,}\s*\n'
cell_splits = re.split(cell_pattern, content)

# First part is the header
header = cell_splits[0].strip()
if header:
    # Extract markdown from header
    lines = header.split('\n')
    markdown_lines = []
    for line in lines:
        if line.startswith('#'):
            markdown_lines.append(line.lstrip('#').strip())
        elif '"""' in line:
            continue
        elif line.strip():
            markdown_lines.append(line.strip())
    
    if markdown_lines:
        notebook['cells'].append({
            "cell_type": "markdown",
            "metadata": {"id": "header"},
            "source": markdown_lines
        })

# Process remaining cells (they come in groups of 3: cell_num, title, code)
for i in range(1, len(cell_splits), 3):
    if i + 2 >= len(cell_splits):
        break
    
    cell_num = cell_splits[i]
    title = cell_splits[i + 1]
    code = cell_splits[i + 2]
    
    # Clean up code - remove trailing empty lines and next cell marker
    code_lines = code.split('\n')
    
    # Remove empty lines at the end
    while code_lines and not code_lines[-1].strip():
        code_lines.pop()
    
    # Remove any trailing cell markers
    while code_lines and code_lines[-1].startswith('# ====='):
        code_lines.pop()
    
    if not code_lines:
        continue
    
    # Add markdown title
    notebook['cells'].append({
        "cell_type": "markdown",
        "metadata": {"id": f"title_{cell_num}"},
        "source": [f"## {title}"]
    })
    
    # Add code cell with proper line endings
    source_lines = []
    for j, line in enumerate(code_lines):
        if j < len(code_lines) - 1:
            source_lines.append(line + '\n')
        else:
            source_lines.append(line)  # Last line without \n
    
    notebook['cells'].append({
        "cell_type": "code",
        "metadata": {"id": f"code_{cell_num}"},
        "execution_count": None,
        "outputs": [],
        "source": source_lines
    })

# Write notebook
output_file = 'bee_processing_FIXED.ipynb'
with open(output_file, 'w') as f:
    json.dump(notebook, f, indent=2)

print(f"✅ Created {output_file}")
print(f"   Total cells: {len(notebook['cells'])}")
print(f"   Code cells: {sum(1 for c in notebook['cells'] if c['cell_type'] == 'code')}")
print(f"\n📤 Upload to Colab: File → Upload notebook → {output_file}")
