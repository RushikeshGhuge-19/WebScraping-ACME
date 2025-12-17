"""Simple accuracy runner that applies available templates to sample HTML
and prints a CSV-like summary with confidence and key fields.
"""
from pathlib import Path
import csv
from car_scraper.engine import ScraperEngine
from pathlib import Path
import csv
import argparse
from car_scraper.engine import ScraperEngine


def compare_field(pred, actual, field):
    # normalize and compare depending on field type
    if actual is None or actual == '':
        return False
    if pred is None or pred == '':
        return False
    try:
        if field in ('price', 'mileage_value'):
            return float(pred) == float(actual)
        if field == 'year':
            return int(pred) == int(actual)
        # strings: case-insensitive equality
        return str(pred).strip().lower() == str(actual).strip().lower()
    except Exception:
        return str(pred).strip().lower() == str(actual).strip().lower()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ground-truth', '-g', help='CSV file with ground truth rows', default=None)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    samples = root / 'car_scraper' / 'samples'
    engine = ScraperEngine()
    results = engine.scrape_samples(samples)

    # map by sample name
    res_by_sample = {r['sample']: r for r in results}

    fields = ['name', 'brand', 'model', 'price', 'currency', 'mileage_value', 'year']

    if args.ground_truth:
        gt_path = Path(args.ground_truth)
    else:
        gt_path = root / 'scripts' / 'ground_truth.csv'

    if not gt_path.exists():
        print('No ground truth file found at', gt_path)
        # fallback: just print sample summary
        writer = csv.writer(__import__('sys').stdout)
        writer.writerow(['sample', 'template', 'confidence', 'name', 'brand', 'model', 'price', 'currency'])
        for r in results:
            tpl = r.get('template')
            car = r.get('car') or {}
            conf = car.get('confidence') if isinstance(car, dict) else None
            writer.writerow([
                r.get('sample'), tpl, conf, car.get('name') if car else None,
                car.get('brand') if car else None, car.get('model') if car else None,
                car.get('price') if car else None, car.get('currency') if car else None,
            ])
        return

    # read ground truth
    gt_rows = {}
    with gt_path.open(newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            # sample column required
            s = row.get('sample')
            if not s:
                continue
            gt_rows[s] = row

    # metrics
    metrics = {f: {'tp': 0, 'pred': 0, 'actual': 0} for f in fields}

    for sample, gt in gt_rows.items():
        r = res_by_sample.get(sample)
        car = (r.get('car') or {}) if r else {}
        for f in fields:
            pred = car.get(f) if car else None
            actual = gt.get(f)
            if actual not in (None, ''):
                metrics[f]['actual'] += 1
            if pred not in (None, ''):
                metrics[f]['pred'] += 1
            if compare_field(pred, actual, f):
                metrics[f]['tp'] += 1

    # print metrics
    print('field,precision,recall,f1,tp,pred,actual')
    for f in fields:
        tp = metrics[f]['tp']
        pred = metrics[f]['pred']
        actual = metrics[f]['actual']
        prec = tp / pred if pred else 0.0
        rec = tp / actual if actual else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
        print(f"{f},{prec:.3f},{rec:.3f},{f1:.3f},{tp},{pred},{actual}")


if __name__ == '__main__':
    main()
