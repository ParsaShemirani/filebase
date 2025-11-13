from pathlib import Path

import pandas as pd

from connection import engine

temp_output_dir = Path(__file__).parent / "temp_csv"
temp_output_dir.mkdir()

table_names = ["nodes", "edges", "files", "descriptions", "collections"]

with engine.connect() as conn:
    for tn in table_names:
        df = pd.read_sql_table(tn, conn)

        df.to_csv(temp_output_dir / f"{tn}.csv", index=False)

