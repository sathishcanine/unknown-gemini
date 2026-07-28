const IST = 'Asia/Kolkata';

/** Parse API timestamps. Backend now returns IST with +05:30 offset. */
function parseTs(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatISTDateTime(iso) {
  const d = parseTs(iso);
  if (!d) return '\u2014';
  return d.toLocaleString('en-IN', {
    timeZone: IST,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }) + ' IST';
}

export function formatISTDate(iso) {
  const d = parseTs(iso);
  if (!d) return '\u2014';
  return d.toLocaleDateString('en-IN', {
    timeZone: IST,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

export function timeAgoIST(iso) {
  const d = parseTs(iso);
  if (!d) return 'Never';
  const diffMs = Date.now() - d.getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

/** Calendar "today" in IST as a local Date at midnight (for date-fns presets). */
export function todayInIST() {
  const ymd = new Intl.DateTimeFormat('en-CA', {
    timeZone: IST,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date());
  const [y, m, d] = ymd.split('-').map(Number);
  return new Date(y, m - 1, d);
}
