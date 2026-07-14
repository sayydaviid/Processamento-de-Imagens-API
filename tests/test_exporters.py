import csv
import json

from github_repo_stats.exporters import CsvExporter, JsonExporter


def test_json_exporter_writes_utf8_json(tmp_path) -> None:
    path = tmp_path / "json" / "saida.json"

    JsonExporter().save(path, {"mensagem": "ação"})

    assert json.loads(path.read_text(encoding="utf-8")) == {"mensagem": "ação"}


def test_csv_exporter_writes_rows(tmp_path) -> None:
    path = tmp_path / "csv" / "saida.csv"

    CsvExporter().save(path, [{"nome": "teste", "valor": 1}])

    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows == [{"nome": "teste", "valor": "1"}]


def test_csv_exporter_handles_empty_rows_with_fieldnames(tmp_path) -> None:
    path = tmp_path / "csv" / "vazio.csv"

    CsvExporter().save(path, [], fieldnames=["nome", "valor"])

    assert path.read_text(encoding="utf-8").splitlines()[0] == "nome,valor"
