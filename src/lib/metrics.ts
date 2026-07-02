/** Работа с data/<metric>.json на этапе сборки. */

export interface Point {
  date: string;
  value: number;
}

export interface MetricPayload {
  metric: string;
  unit: string;
  source_name: string;
  source_url: string;
  fetched_at: string;
  data_date: string;
  series: Point[];
}

/** Последнее значение и дельта к предыдущей точке серии. */
export function latestWithDelta(series: Point[]): {
  value: number;
  delta: number | null;
  date: string;
} {
  const last = series[series.length - 1];
  const prev = series.length > 1 ? series[series.length - 2] : null;
  return {
    value: last.value,
    delta: prev ? last.value - prev.value : null,
    date: last.date,
  };
}

/** Хвост серии за последние `days` дней от последней точки. */
export function tail(series: Point[], days: number): Point[] {
  const end = new Date(series[series.length - 1].date).getTime();
  const from = end - days * 86_400_000;
  return series.filter((p) => new Date(p.date).getTime() >= from);
}

/** Равномерное прореживание до maxPoints (последняя точка сохраняется). */
export function downsample(series: Point[], maxPoints: number): Point[] {
  if (series.length <= maxPoints) return series;
  const step = (series.length - 1) / (maxPoints - 1);
  return Array.from({ length: maxPoints }, (_, i) => series[Math.round(i * step)]);
}

/** Точки polyline для SVG-спарклайна (viewBox 0 0 w h), считается при сборке. */
export function sparklinePoints(rawSeries: Point[], w = 120, h = 32, pad = 2): string {
  const series = downsample(rawSeries, 180);
  const values = series.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1; // плоская серия → горизонтальная линия
  return series
    .map((p, i) => {
      const x = pad + (i / Math.max(series.length - 1, 1)) * (w - 2 * pad);
      const y = pad + (1 - (p.value - min) / span) * (h - 2 * pad);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
}

const nf = new Intl.NumberFormat('ru-RU', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
});

export function formatValue(v: number): string {
  return nf.format(v);
}

export function formatDelta(d: number): string {
  const sign = d > 0 ? '+' : d < 0 ? '−' : '±';
  return `${sign}${nf.format(Math.abs(d))}`;
}

export function formatDateRu(iso: string): string {
  return new Date(iso).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}
