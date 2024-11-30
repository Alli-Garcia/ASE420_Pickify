from fastapi.templating import Jinja2Templates
from pathlib import Path

# Set up the templates directory
templates_path = Path(__file__).parent.parent / "templates"  # Adjust path accordingly to find templates folder
templates = Jinja2Templates(directory=str(templates_path))
