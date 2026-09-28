const KNOWN = new Set(["PENDING", "CONFIRMED", "FAILED", "CANCELLED", "SUCCESS"]);

export default function StatusPill({ status }: { status: string }) {
  const key = status.toUpperCase();
  const modifier = KNOWN.has(key) ? key.toLowerCase() : "cancelled";
  return <span className={`pill pill-${modifier}`}>{key}</span>;
}
