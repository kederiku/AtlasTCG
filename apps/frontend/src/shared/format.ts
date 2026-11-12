export const date = (value: string, locale = "fr") =>
  new Date(value).toLocaleString(locale, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });

export const calendarDate = (value: string, locale: string) =>
  new Intl.DateTimeFormat(locale, {
    day: "2-digit",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));

export const count = (value: unknown, locale: string) =>
  typeof value === "number" ? value.toLocaleString(locale) : String(value);
