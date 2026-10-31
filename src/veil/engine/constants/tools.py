EDIT_FILE = "edit_file"
FINISH = "finish"
READ_FILE = "read_file"
SEARCH = "search"
LIST_DIR = "list_dir"

TOOL_DESCRIPTIONS = {
    READ_FILE: "Read a text file of the repository. Give a start line to read from there.",
    SEARCH: "Find the lines that match a regular expression in the files of the repository.",
    LIST_DIR: "List the files and the folders in a directory of the repository.",
    EDIT_FILE: "Replace the first match of an exact text in a file with a new text. You cannot make or delete files.",
    FINISH: "Call this when the fix is complete. Give a one-line commit message and a short explanation. Write both in ASD-STE100 Simplified Technical English.",
}
