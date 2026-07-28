import {
  format,
  subDays,
  startOfMonth,
  endOfMonth,
  startOfYear,
  endOfYear,
  subMonths,
} from 'date-fns';
import { todayInIST } from './formatTime';

const fmt = (d) => format(d, 'yyyy-MM-dd');

/**
 * Returns { start, end, compareStart, compareEnd, label } for a given preset.
 * All calendar days are computed in IST (Asia/Kolkata).
 */
export function resolvePreset(preset, customStart, customEnd) {
  const today = todayInIST();

  switch (preset) {
    case 'today':
      return {
        start: fmt(today),
        end: fmt(today),
        compareStart: fmt(subDays(today, 1)),
        compareEnd: fmt(subDays(today, 1)),
        label: 'Today',
      };
    case 'yesterday': {
      const y = subDays(today, 1);
      return {
        start: fmt(y),
        end: fmt(y),
        compareStart: fmt(subDays(y, 1)),
        compareEnd: fmt(subDays(y, 1)),
        label: 'Yesterday',
      };
    }
    case 'last7': {
      const start = subDays(today, 6);
      return {
        start: fmt(start),
        end: fmt(today),
        compareStart: fmt(subDays(start, 7)),
        compareEnd: fmt(subDays(start, 1)),
        label: 'Last 7 Days',
      };
    }
    case 'last30': {
      const start = subDays(today, 29);
      return {
        start: fmt(start),
        end: fmt(today),
        compareStart: fmt(subDays(start, 30)),
        compareEnd: fmt(subDays(start, 1)),
        label: 'Last 30 Days',
      };
    }
    case 'thisMonth':
      return {
        start: fmt(startOfMonth(today)),
        end: fmt(today),
        compareStart: fmt(startOfMonth(subMonths(today, 1))),
        compareEnd: fmt(endOfMonth(subMonths(today, 1))),
        label: 'This Month',
      };
    case 'prevMonth': {
      const prev = subMonths(today, 1);
      return {
        start: fmt(startOfMonth(prev)),
        end: fmt(endOfMonth(prev)),
        compareStart: fmt(startOfMonth(subMonths(prev, 1))),
        compareEnd: fmt(endOfMonth(subMonths(prev, 1))),
        label: 'Previous Month',
      };
    }
    case 'thisYear':
      return {
        start: fmt(startOfYear(today)),
        end: fmt(today),
        compareStart: fmt(startOfYear(subMonths(today, 12))),
        compareEnd: fmt(endOfYear(subMonths(today, 12))),
        label: 'This Year',
      };
    case 'custom':
      return {
        start: customStart,
        end: customEnd,
        compareStart: null,
        compareEnd: null,
        label: `${customStart} \u2192 ${customEnd}`,
      };
    default:
      return resolvePreset('today');
  }
}

export const PRESETS = [
  { id: 'today', label: 'Today' },
  { id: 'yesterday', label: 'Yesterday' },
  { id: 'last7', label: 'Last 7 Days' },
  { id: 'last30', label: 'Last 30 Days' },
  { id: 'thisMonth', label: 'This Month' },
  { id: 'prevMonth', label: 'Previous Month' },
  { id: 'thisYear', label: 'This Year' },
  { id: 'custom', label: 'Custom Date' },
];

export function pctChange(current, previous) {
  if (previous === null || previous === undefined || previous === 0) {
    if (current > 0) return null;
    return 0;
  }
  return Math.round(((current - previous) / previous) * 1000) / 10;
}
