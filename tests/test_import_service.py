from app.services.import_service import parse_products_csv


def test_parse_products_csv_success():
    data = "Хлеб; 12.5; свежий\nМолоко; 45\n".encode("utf-8")
    preview = parse_products_csv(data)
    assert not preview.errors
    assert len(preview.items) == 2
    assert preview.items[0].name == "Хлеб"
    assert preview.items[0].price == 12.5


def test_parse_products_csv_errors():
    data = ";;; \nСок; abc\nСок; 12\n".encode("utf-8")
    preview = parse_products_csv(data)
    assert preview.errors
    assert len(preview.items) == 1


def test_parse_products_csv_with_sku_columns():
    data = "Хлеб; 12.5; SKU-AAAABBBB\nМолоко; 45; свежее; SKU-CCCCDDDD\n".encode("utf-8")
    preview = parse_products_csv(data)
    assert not preview.errors
    assert len(preview.items) == 2
    assert preview.items[0].sku == "SKU-AAAABBBB"
    assert preview.items[0].description == ""
    assert preview.items[1].description == "свежее"
    assert preview.items[1].sku == "SKU-CCCCDDDD"
