const CHARSET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ";
const INDEX: Record<string, number> = Object.fromEntries([...CHARSET].map((c, i) => [c, i]));
const N = CHARSET.length;

function checksum(payload: string): string {
  let factor = 2;
  let total = 0;
  for (let i = payload.length - 1; i >= 0; i--) {
    let addend = factor * INDEX[payload[i]];
    addend = Math.floor(addend / N) + (addend % N);
    total += addend;
    factor = factor === 2 ? 1 : 2;
  }
  return CHARSET[(N - (total % N)) % N];
}

export function is_valid_judge_code(code: string): boolean {
  const c = code.toUpperCase().replace(/-/g, "");
  if (c.length !== 8) return false;
  if ([...c].some((ch) => !(ch in INDEX))) return false;
  return checksum(c.slice(0, 7)) === c[7];
}

export function format_judge_code(raw: string): string {
  const stripped = raw.replace(/-/g, "").slice(0, 8);
  if (stripped.length > 4) return `${stripped.slice(0, 4)}-${stripped.slice(4)}`;
  return stripped;
}
