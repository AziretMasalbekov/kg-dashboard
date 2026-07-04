import type { APIRoute } from 'astro';
import { metrics } from '../../lib/data';

export function getStaticPaths() {
  return Object.keys(metrics).map((slug) => ({ params: { slug } }));
}

function csvEscape(s: string): string {
  return /[",\n]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
}

export const GET: APIRoute = ({ params }) => {
  const data = metrics[params.slug!];
  const rows: string[] = [];

  if (data.regions?.length) {
    rows.push('name,date,value');
    for (const r of data.regions) {
      for (const p of r.series) {
        rows.push(`${csvEscape(r.name_ru)},${p.date},${p.value}`);
      }
    }
  } else {
    rows.push('date,value');
    for (const p of data.series) {
      rows.push(`${p.date},${p.value}`);
    }
  }
  // атрибуция источника — обязательна по условиям лицензии данных
  rows.push('');
  rows.push(`# ${data.source_name} — ${data.source_url}`);

  return new Response(rows.join('\n'), {
    headers: { 'Content-Type': 'text/csv; charset=utf-8' },
  });
};
