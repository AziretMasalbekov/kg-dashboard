import ru from './ru.json';
import ky from './ky.json';

export type Locale = 'ru' | 'ky';
export type MessageKey = keyof typeof ru;

const messages: Record<Locale, Record<string, string>> = { ru, ky };

export const DEFAULT_LOCALE: Locale = 'ru';

/** Возвращает строку UI по ключу; ky-заглушки падают обратно на ru. */
export function t(key: MessageKey, locale: Locale = DEFAULT_LOCALE): string {
  const value = messages[locale][key];
  if (!value || value.startsWith('TODO(')) return messages.ru[key];
  return value;
}
