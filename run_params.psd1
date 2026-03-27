@{
    # Required: ProQuest search query passed as the first positional argument.
    SearchQuery = 'title("STOCK QUOTE") AND stype.exact("Newspapers") AND bdl(1007155) AND fulltext("complete transactions")'

    # Optional: defaults to 3 if omitted.
    NumFiles = 11

    # Optional: yyyy-mm-dd. Use $null to auto-detect from existing files.
    StartDate = $null

    # Optional: output directory for downloaded PDFs.
    OutputDir = './Stock Exchange'

    # Optional: leave blank to use values from .env file.
    ResearchEmail = ''
    ResearchPassword = ''

    # Optional: custom Python executable. Defaults to .\env\Scripts\python.exe when present.
    PythonExe = ''
}