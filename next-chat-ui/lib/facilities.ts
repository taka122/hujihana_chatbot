import { readFileSync } from "node:fs";
import path from "node:path";

export type Facility = {
  id: string;
  name: string;
  prefecture: string;
  city: string;
  serviceType: string;
  address: string;
  phone: string;
  businessHours: string;
  features: string[];
  lastUpdated: string;
  sourceUrl: string;
};

let facilityCache: Facility[] | null = null;

function parseCsvLine(line: string): string[] {
  const cells: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === "\"") {
      const next = line[i + 1];
      if (inQuotes && next === "\"") {
        current += "\"";
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (ch === "," && !inQuotes) {
      cells.push(current);
      current = "";
      continue;
    }

    current += ch;
  }

  cells.push(current);
  return cells.map((cell) => cell.trim());
}

export function loadFacilities(): Facility[] {
  if (facilityCache) {
    return facilityCache;
  }

  const csvPath = path.resolve(process.cwd(), "..", "data", "facilities_sample.csv");
  const raw = readFileSync(csvPath, "utf-8");
  const lines = raw
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  if (lines.length <= 1) {
    throw new Error(`施設データが空です: ${csvPath}`);
  }

  const headers = parseCsvLine(lines[0]);
  const indexOf = (name: string): number => {
    const idx = headers.indexOf(name);
    if (idx < 0) {
      throw new Error(`CSVヘッダーが不足しています: ${name}`);
    }
    return idx;
  };

  const idIdx = indexOf("id");
  const nameIdx = indexOf("name");
  const prefIdx = indexOf("prefecture");
  const cityIdx = indexOf("city");
  const serviceIdx = indexOf("service_type");
  const addressIdx = indexOf("address");
  const phoneIdx = indexOf("phone");
  const hoursIdx = indexOf("business_hours");
  const featuresIdx = indexOf("features");
  const updatedIdx = indexOf("last_updated");
  const sourceIdx = indexOf("source_url");

  const facilities: Facility[] = [];
  for (const line of lines.slice(1)) {
    const cells = parseCsvLine(line);
    facilities.push({
      id: cells[idIdx] ?? "",
      name: cells[nameIdx] ?? "",
      prefecture: cells[prefIdx] ?? "",
      city: cells[cityIdx] ?? "",
      serviceType: cells[serviceIdx] ?? "",
      address: cells[addressIdx] ?? "",
      phone: cells[phoneIdx] ?? "",
      businessHours: cells[hoursIdx] ?? "",
      features: (cells[featuresIdx] ?? "")
        .split("|")
        .map((item) => item.trim())
        .filter((item) => item.length > 0),
      lastUpdated: cells[updatedIdx] ?? "",
      sourceUrl: cells[sourceIdx] ?? ""
    });
  }

  facilityCache = facilities;
  return facilities;
}

