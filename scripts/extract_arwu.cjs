// Extract the institution pool from ShanghaiRanking's public Nuxt payload.
// Usage: node scripts/extract_arwu.cjs PAYLOAD_FILE SOURCE_URL OUTPUT_DIRECTORY
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');

const [input, sourceUrl, output] = process.argv.slice(2);
if (!input || !sourceUrl || !output) {
  throw new Error('Expected PAYLOAD_FILE SOURCE_URL OUTPUT_DIRECTORY');
}
const raw = fs.readFileSync(input, 'utf8');
// No Node APIs or host functions are supplied to the payload context.
const context = Object.create(null);
vm.runInNewContext(
  'var result; function __NUXT_JSONP__(route, data) { result = data; }\n' + raw,
  context,
  { timeout: 1000, contextCodeGeneration: { strings: false, wasm: false } }
);
const data = JSON.parse(JSON.stringify(context.result)).data[0];
const institutions = data.univList;
if (data.year !== 2026 || !Array.isArray(institutions) || institutions.length !== 1000) {
  throw new Error('Expected exactly 1000 institutions from ARWU 2026');
}
const ids = new Set();
for (const row of institutions) {
  if (!row.univUp || !row.univNameEn || !row.ranking || ids.has(row.univUp)) {
    throw new Error('Missing or duplicate institution identity');
  }
  ids.add(row.univUp);
}
const quote = value => '"' + String(value).replaceAll('"', '""') + '"';
const columns = ['institution_id', 'university', 'country_or_region', 'arwu_rank_or_band', 'arwu_year', 'source_url'];
const source = 'https://www.shanghairanking.com/rankings/arwu/2026';
const rows = institutions.map(row => [row.univUp, row.univNameEn, row.region, row.ranking, data.year, source]);
fs.mkdirSync(output, { recursive: true });
fs.writeFileSync(path.join(output, 'arwu_2026_top1000.csv'),
  [columns, ...rows].map(row => row.map(quote).join(',')).join('\n') + '\n');
fs.writeFileSync(path.join(output, 'arwu_2026_source.json'), JSON.stringify({
  ranking_page: source,
  payload_url: sourceUrl,
  extraction_time_utc: new Date().toISOString(),
  payload_sha256: crypto.createHash('sha256').update(raw).digest('hex'),
  institution_count: institutions.length,
  purpose: 'Eligibility pool only. ARWU rank and score are not bibliometric ranking inputs.',
  publication_audit_status: 'Not started; pool extraction does not establish publication coverage.'
}, null, 2) + '\n');
console.log(`Saved ${institutions.length} unique institutions to ${output}`);
