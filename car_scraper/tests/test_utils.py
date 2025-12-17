from car_scraper.templates.utils import parse_mileage, parse_year, parse_price


def test_parse_mileage_simple():
    v, u = parse_mileage('12,000 miles')
    assert v == 12000 and u == 'mi'


def test_parse_mileage_k_shorthand():
    v, u = parse_mileage('18k')
    assert v == 18000 and u == 'mi'


def test_parse_mileage_k_km_conversion():
    v, u = parse_mileage('20k km')
    # 20000 km -> approx 12427 mi
    assert abs(v - 12427) <= 2


def test_parse_mileage_range():
    v, u = parse_mileage('12-15k')
    assert v == 12000 and u == 'mi'


def test_parse_year_4digit():
    assert parse_year('Year: 2018') == 2018


def test_parse_year_2digit():
    assert parse_year('18') == 2018
    assert parse_year('99') == 1999


def test_parse_price_examples():
    amt, cur = parse_price('£995')
    assert amt == 995 and cur == 'GBP'
    amt2, cur2 = parse_price('$4,995')
    assert amt2 == 4995 and cur2 == 'USD'
