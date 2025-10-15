#!/usr/bin/env python3
"""
Convert bee_processing_FIXED.py to Jupyter notebook
Run: python convert_to_notebook.py
"""

import json

# Read the Python file
with open('bee_processing_FIXED.py', 'r') as f:
    content = f.read()

# Split by cell markers
cells_raw = content.split('# ============================================\n# CELL ')

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

# Process first cell (header)
if cells_raw[0].strip():
    lines = cells_raw[0].strip().split('\n')
    markdown_lines = []
    for line in lines:
        if line.startswith('"""') or line.startswith('#'):
            markdown_lines.append(line.replace('"""', '').replace('# ', '').strip())
    
    if markdown_lines:
        notebook['cells'].append({
            "cell_type": "markdown",
            "metadata": {"id": "header"},
            "source": markdown_lines
        })

# Process remaining cells
for i, cell_content in enumerate(cells_raw[1:], 1):
    if not cell_content.strip():
        continue
    
    lines = cell_content.split('\n')
    
    # Extract cell title
    title_line = lines[0] if lines else f"Cell {i}"
    title = title_line.split(':')[-1].strip() if ':' in title_line else title_line
    
    # Get code (skip the separator lines)
    code_lines = []
    skip_next = False
    
    for line in lines[1:]:
        if line.startswith('# ======='):
            skip_next = True
            continue
        if skip_next:
            skip_next = False
            continue
        code_lines.append(line)
    
    # Remove trailing empty lines
    while code_lines and not code_lines[-1].strip():
        code_lines.pop()
    
    if code_lines:
        # Add markdown cell for title
        notebook['cells'].append({
            "cell_type": "markdown",
            "metadata": {"id": f"title_{i}"},
            "source": [f"## {title}"]
        })
        
        # Add code cell
        notebook['cells'].append({
            "cell_type": "code",
            "metadata": {"id": f"cell_{i}"},
            "execution_count": None,
            "outputs": [],
            "source": code_lines
        })

# Write notebook
output_file = 'bee_processing_FIXED.ipynb'
with open(output_file, 'w') as f:
    json.dump(notebook, f, indent=2)

print(f"✅ Created {output_file}")
print(f"   Total cells: {len(notebook['cells'])}")
print(f"\n📤 Upload to Colab: File → Upload notebook → {output_file}")
