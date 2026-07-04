import type { MetricPayload, Point } from './metrics';

export interface Region {
  name_ru: string;
  name_ky: string;
  name_en: string;
  series: Point[];
}

export type NscPayload = MetricPayload & { regions?: Region[] };

const files = import.meta.glob<NscPayload>('../../data/*.json', {
  eager: true,
  import: 'default',
});

/** Все метрики из data/*.json, ключ — slug (имя файла). */
export const metrics: Record<string, NscPayload> = Object.fromEntries(
  Object.entries(files).map(([path, payload]) => [
    path.replace(/^.*\/(.+)\.json$/, '$1'),
    payload,
  ]),
);
