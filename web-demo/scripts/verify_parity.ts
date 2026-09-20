// Verifies the TS compare() port against the real Python-computed outcomes
// for every BL_COMPARISON email that reached a compare (status OK/MISMATCH)
// -- not the escalated ones, since those never ran compare() in Python either.
import { readFileSync } from "node:fs";
import { compare, type Field } from "../src/lib/compare.ts";

interface EmailRecord {
  id: string;
  category: string;
  status: string;
  defectFields: string[];
  si: { fields?: Record<string, string> } | null;
  bl: { fields?: Record<string, string> } | null;
}

const path = new URL("../public/data/emails.json", import.meta.url);
const data: EmailRecord[] = JSON.parse(readFileSync(path, "utf8"));

let checked = 0;
let mismatches = 0;

for (const e of data) {
  if (e.category !== "BL_COMPARISON") continue;
  if (e.status !== "OK" && e.status !== "MISMATCH") continue;
  if (!e.si?.fields || !e.bl?.fields) continue;
  checked++;
  const result = compare(e.si.fields as Partial<Record<Field, string>>, e.bl.fields as Partial<Record<Field, string>>);
  const wantDefects = [...e.defectFields].sort();
  const gotDefects = [...result.defectFields].sort();
  const same =
    result.status === e.status && JSON.stringify(wantDefects) === JSON.stringify(gotDefects);
  if (!same) {
    mismatches++;
    console.log(
      `DRIFT ${e.id}: python status=${e.status} defects=${wantDefects} | ts status=${result.status} defects=${gotDefects}`,
    );
  }
}

console.log(`checked ${checked} emails, ${mismatches} drifted from the Python original`);
process.exit(mismatches === 0 ? 0 : 1);
