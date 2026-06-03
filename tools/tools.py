import os

os.environ.setdefault("CREWAI_TOOLS_ALLOW_UNSAFE_PATHS", "true")

from crewai_tools.tools.exa_tools.exa_search_tool import EXASearchTool
from crewai_tools.tools.file_read_tool.file_read_tool import FileReadTool
from dotenv import load_dotenv

load_dotenv()

# TOOL 1: FileReadTool
log_reader_tool = FileReadTool()

# TOOL 2: EXASearchTool
os.environ["EXA_API_KEY"] = os.getenv("EXA_API_KEY")

exa_search_tool = EXASearchTool()