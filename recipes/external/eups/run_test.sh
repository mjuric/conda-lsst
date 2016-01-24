#!/bin/bash

source eups-setups.sh

# Ensure we can import the EUPS Python module
python -c "import eups;"

# Ensure we can run EUPS
eups -h 2>/dev/null
