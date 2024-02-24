from bs4 import BeautifulSoup, Tag
import requests
import re
from pathlib import Path
import csv
import json
import logging


URL = "https://calorizator.ru/product"
HEADERS = {
    "User-Agent": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 YaBrowser/24.1.0.0 Safari/537.36",
}
WITHOUT_LAST_SECTION = 32

HTML_DIR = Path(__file__).parent / "html"
CSV_DIR = Path(__file__).parent / "csv"
DIRTY_JSON_DIR = Path(__file__).parent / "dirty_json"
JSON_DIR = Path(__file__).parent / "json"


def main():

    check_dirs(
        (
            HTML_DIR,
            DIRTY_JSON_DIR,
            JSON_DIR,
            CSV_DIR,
        )
    )

    file_path: Path = download_page(
        file_dir=HTML_DIR,
        file_name="index.html",
    )

    soup = read_html(file_path)

    categories: list = soup.find_all("li", class_=re.compile(r"prod\d\d"))[
        :WITHOUT_LAST_SECTION
    ]

    html_paths: list[Path] = download_category_pages(categories)

    dirty_json_paths: list[Path] = download_dirty_data(html_paths)

    json_paths: list[Path] = clear_json(dirty_json_paths)

    csv_paths: list[Path] = clear_csv(dirty_json_paths)


def clear_csv(dirty_json_paths: list[Path]) -> list[Path]:
    files: list[Path] = []

    for path in dirty_json_paths:
        with open(path, "r", encoding="utf-8") as file:
            data_json = json.load(file)

        cleared_heads = [clear_str(key) for key in data_json[0].keys()]
        cleared_data = [
            [clear_str(value) for key, value in data.items()] for data in data_json
        ]

        files.append(write_csv(cleared_heads, cleared_data, path.stem))
    return files


def clear_str(data_string: str) -> str:
    dirts = ("\n", ",")
    data_string = data_string.strip()
    for dirt in dirts:
        data_string = data_string.replace(dirt, "")
    data_string = data_string.replace(" ", "_")
    return data_string


def clear_json(dirty_json_paths: list[Path]) -> list[Path]:
    files: list[Path] = []

    for path in dirty_json_paths:
        with open(path, "r", encoding="utf-8") as file:
            data_json = json.load(file)

        cleared_data = [
            {clear_str(key): clear_str(value) for key, value in data.items()}
            for data in data_json
        ]

        files.append(write_json(cleared_data, path.stem))
    return files


def download_dirty_data(html_paths: list[Path]) -> list[Path]:
    files: list[Path] = []

    for path in html_paths:
        soup = read_html(path)

        table = soup.find("table")
        table_header: list = take_header(table)
        table_data: list[list] = [list(row) for row in zip(*take_data(table))]

        files.append(
            write_json(
                [dict(zip(table_header, i)) for i in table_data],
                path.stem,
                DIRTY_JSON_DIR,
            )
        )

    return files


def write_json(data: list[dict], file_name: str, file_dir=JSON_DIR) -> Path:
    file_path = f"{file_dir}/{file_name}.json"
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    return Path(file_path)


def write_csv(header: list, data: list[list], file_name: str) -> Path:
    file_path = f"{CSV_DIR}/{file_name}.csv"
    with open(file_path, "w", encoding="utf-8") as file:
        csv_out = csv.writer(file)
        csv_out.writerow(header)
        csv_out.writerows(data)

    return Path(file_path)


def take_header(table: Tag) -> list:
    return [t.text for t in table.find("thead").find_all("th")[1:]]


def take_data(table: Tag) -> tuple[list, list, list, list]:
    products = table.find_all("td", class_="views-field views-field-title active")
    products_names: list[str] = [product.find("a").text for product in products]

    products_protein = [
        i.text
        for i in table.find_all(
            "td", class_="views-field views-field-field-protein-value"
        )
    ]
    products_carbohydrate = [
        i.text
        for i in table.find_all(
            "td", class_="views-field views-field-field-carbohydrate-value"
        )
    ]
    products_fat = [
        i.text
        for i in table.find_all("td", class_="views-field views-field-field-fat-value")
    ]
    products_kcal = [
        i.text
        for i in table.find_all("td", class_="views-field views-field-field-kcal-value")
    ]

    return [
        products_names,
        products_protein,
        products_carbohydrate,
        products_fat,
        products_kcal,
    ]


def download_category_pages(categories: list) -> list[Path]:
    files: list[Path] = []

    for category in categories[:3]:
        href: str = category.find("a").get("href")
        category_name: str = href.split("/")[1]
        file_path: Path = download_page(
            file_dir=HTML_DIR,
            file_name=f"{category_name}.html",
            url=f"{URL}/{category_name}/",
        )
        files.append(file_path)
    return files


def download_page(file_dir: Path, file_name: str, url: str = URL) -> Path:

    req = requests.get(url=url, headers=HEADERS, timeout=10)

    file_path = f"{file_dir}/{file_name}"

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(req.text)

    return Path(file_path)


def read_html(file_path: Path) -> BeautifulSoup:
    with open(file_path, "r", encoding="utf-8") as file:
        html_txt: str = file.read()

    return BeautifulSoup(html_txt, "lxml")


def check_dirs(dirs: tuple[Path]):
    for dir in dirs:
        if not dir.exists():
            dir.mkdir()


if __name__ == "__main__":
    main()
