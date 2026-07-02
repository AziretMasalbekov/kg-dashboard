import sys
from pathlib import Path

# Парсеры лежат в scripts/ и импортируют друг друга как плоские модули
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

FIXTURES = Path(__file__).resolve().parent / "fixtures"
