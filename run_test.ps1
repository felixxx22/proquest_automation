# Ensure the script exits on any error
$ErrorActionPreference = "Stop"

# Activate the Python virtual environment
& env\Scripts\Activate.ps1

# Define the search query and number of files to download
$SEARCH_QUERY = 'title(\"FINANCIAL MARKETS\") AND stype.exact(\"Newspapers\") AND bdl(1007155)'
$SEARCH_QUERY = 'title(\"STOCK QUOTE\") AND stype.exact(\"Newspapers\") AND bdl(1007155) AND fulltext(\"BID AND ASKED QUOTATIONS\")' # title("STOCK QUOTE") AND stype.exact("Newspapers") AND bdl(1007155) AND fulltext("BID AND ASKED QUOTATIONS")
$NUM_FILES = 11
$START_DATE = "1900-01-01"  # Optional: Starting date in yyyy-mm-dd format

# Run the Python script with the specified arguments
python proquest_download.py "$SEARCH_QUERY" -n $NUM_FILES # -d $START_DATE