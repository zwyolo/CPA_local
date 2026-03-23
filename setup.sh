#!/bin/bash
set -e

echo "=== CPA Exam Availability Checker Setup ==="

conda create -n cpa python=3.11 -y
conda run -n cpa pip install -r requirements.txt

echo ""
echo "Setup complete! To run:"
echo "  conda activate cpa"
echo "  python search.py"
