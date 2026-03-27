# Ensure the script exits on any error
$ErrorActionPreference = "Stop"

# Activate the Python virtual environment
& env\Scripts\Activate.ps1

# Define the search query and number of files to download
$SEARCH_QUERY = 'title(\"STOCK QUOTE\") AND stype.exact(\"Newspapers\") AND bdl(1007155) AND fulltext(\"complete transactions\")'
$NUM_FILES = 11
$OUTPUT_DIR = "./Stock Exchange"

# Run the Python script with the specified arguments
python proquest_download.py "$SEARCH_QUERY" -n $NUM_FILES -o $OUTPUT_DIR
