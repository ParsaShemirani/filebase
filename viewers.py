import argparse
import textwrap
from datetime import datetime
from zoneinfo import ZoneInfo

from tabulate import tabulate
from sqlalchemy import select


from models import File, Collection
from connection import Session

def wrap_text(text, width=40):
    if text is None:
        return ""
    return "\n".join(textwrap.wrap(str(text), width=width))

def print_current_time():
    california_time = datetime.now(ZoneInfo("America/Los_Angeles"))
    print("Time: ", california_time.strftime("%Y-%m-%d %H:%M:%S"))

def print_recent_files():
    with Session() as session:
        rows = session.scalars(select(File).order_by(File.id.desc()).limit(15)).all()

        data = []
        for row in rows:
            data.append([
                row.id,
                row.inserted_ts,
                wrap_text(row.sha256_hash),
                row.extension,
                row.created_ts,
                row.collection_id,
                wrap_text(row.description),
            ])

    table = tabulate(
        data,
        headers=[
            "ID",
            "Inserted TS",
            "SHA256 Hash",
            "Extension",
            "Created TS",
            "Collection ID",
            "Description",
        ]
    )
    print(10*"\n")
    print_current_time()
    print(table)


def print_recent_collections():
    with Session() as session:
        rows = session.scalars(select(Collection).order_by(Collection.id.desc()).limit(5)).all()

        data = []
        for row in rows:
            data.append([
                row.id,
                row.inserted_ts,
                wrap_text(row.description)
            ])

        table = tabulate(
            data,
            headers=[
                "ID",
                "Inserted TS",
                "Description"
            ]
        )

    print(10*"\n")
    print_current_time()
    print(table)




def main():
    parser = argparse.ArgumentParser(
        prog="Files / Collections displayer",
        description="Prints recent files or collections in archvive database",
        epilog="By: Parsa Shemirani"
    )
    parser.add_argument("-f", "--file", action="store_true")
    parser.add_argument("-c", "--collection", action="store_true")
    args = parser.parse_args()

    if args.file:
        print_recent_files()
    if args.collection:
        print_recent_collections()

if __name__ == "__main__":
    main()
