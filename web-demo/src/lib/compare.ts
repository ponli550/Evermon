/**
 * Hand-ported from dock/fields.py's value-comparison half (normalise_value,
 * values_match, is_blank) -- NOT the label-alias half. The 520 real emails
 * ship pre-aligned (dock/extract.py already resolved "Load Port" vs "Port
 * of Loading" to the same field, at build time, in Python -- see
 * web-demo/scripts/export_dataset.py). What runs here, in the browser, is
 * only the "do these two values mean the same thing" layer, so a visitor
 * can edit a value and see the real locode-stripping / weight-normalising
 * / container-parsing rules re-run live, without a second copy of the
 * label-alignment table drifting from the Python original.
 */

export const FIELDS = [
  "shipper",
  "consignee",
  "notify_party",
  "port_of_loading",
  "port_of_discharge",
  "container_count",
  "gross_weight_kg",
] as const;

export type Field = (typeof FIELDS)[number];

export const FIELD_LABELS: Record<Field, string> = {
  shipper: "Shipper",
  consignee: "Consignee",
  notify_party: "Notify Party",
  port_of_loading: "Port of Loading",
  port_of_discharge: "Port of Discharge",
  container_count: "Container Count",
  gross_weight_kg: "Gross Weight (kg)",
};

const LOCODE = /\s*\(\s*[A-Z]{2}[A-Z0-9]{3}\s*\)\s*$/;
const WS = /\s+/g;
const CONTAINERS = /^\s*([\d,]+)\s*(?:x|\*)\s*(.+?)\s*$/i;
const NUMBER = /-?[\d,]*\.?\d+/;
const NON_ALNUM = /[^a-z0-9]+/g;
const BLANK_MARKERS = /^(n\/?a|tba|tbc|tbd|nil|none|-+|_+|\.+)$/i;

/** True when a value is absent, or a human's placeholder for "not filled in". */
export function isBlank(value: string | null | undefined): boolean {
  if (value == null) return true;
  const text = value.replace(WS, " ").trim();
  if (!text) return true;
  if (/^[_\-.\s]+[A-Za-z]*$/.test(text)) return true;
  return BLANK_MARKERS.test(text);
}

function normText(value: string): string {
  return value.replace(WS, " ").trim().toUpperCase();
}

function normPort(value: string): string {
  return normText(value.trim().replace(LOCODE, ""));
}

function normWeight(value: string): number | null {
  const match = value.replace(/ /g, "").match(NUMBER);
  if (!match) return null;
  const n = Number.parseFloat(match[0].replace(/,/g, ""));
  return Number.isNaN(n) ? null : n;
}

function normContainers(value: string): [string, string] | null {
  const match = normText(value).match(CONTAINERS);
  if (!match) return null;
  return [match[1].replace(/,/g, ""), match[2].toLowerCase().replace(NON_ALNUM, "")];
}

/** The comparable form of a value -- what's rendered back to a reviewer. */
export function normaliseValue(field: Field, value: string): string {
  if (field === "port_of_loading" || field === "port_of_discharge") return normPort(value);
  if (field === "gross_weight_kg") {
    const w = normWeight(value);
    return w == null ? normText(value) : String(w);
  }
  if (field === "container_count") {
    const c = normContainers(value);
    return c == null ? normText(value) : `${c[0]} x ${c[1].toUpperCase()}`;
  }
  return normText(value);
}

/** True when the two values mean the same thing for this field. */
export function valuesMatch(field: Field, siValue: string, blValue: string): boolean {
  if (field === "gross_weight_kg") {
    const l = normWeight(siValue);
    const r = normWeight(blValue);
    if (l != null && r != null) return l === r;
  }
  if (field === "container_count") {
    const l = normContainers(siValue);
    const r = normContainers(blValue);
    if (l && r) return l[0] === r[0] && l[1] === r[1];
  }
  return normaliseValue(field, siValue) === normaliseValue(field, blValue);
}

export interface CompareResult {
  status: "OK" | "MISMATCH";
  defectFields: Field[];
  compared: Record<Field, [string, string]>;
}

/** Mirrors dock/compare.py's compare(): diff every field both sides have a value for. */
export function compare(
  si: Partial<Record<Field, string>>,
  bl: Partial<Record<Field, string>>,
): CompareResult {
  const defectFields: Field[] = [];
  const compared = {} as Record<Field, [string, string]>;
  for (const f of FIELDS) {
    const siValue = si[f];
    const blValue = bl[f];
    if (siValue == null || blValue == null || isBlank(siValue) || isBlank(blValue)) continue;
    compared[f] = [normaliseValue(f, siValue), normaliseValue(f, blValue)];
    if (!valuesMatch(f, siValue, blValue)) defectFields.push(f);
  }
  return {
    status: defectFields.length ? "MISMATCH" : "OK",
    defectFields,
    compared,
  };
}

export const NO_MISMATCH = "No mismatch detected";
