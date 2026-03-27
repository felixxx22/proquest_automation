#!/bin/bash

# Ensure the script exits on any error
set -e

# Activate the Python virtual environment
source env/Scripts/activate

# Define the search query and number of files to download
SEARCH_QUERY='title("FINANCIAL MARKETS") AND stype.exact("Newspapers") AND bdl(1007155)'
NUM_FILES=10

# Run the Python script with the specified arguments
python3 proquest_download.py "$SEARCH_QUERY" -n $NUM_FILES