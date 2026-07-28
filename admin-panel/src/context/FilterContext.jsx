import { createContext, useContext, useMemo, useState } from 'react';
import { resolvePreset } from '../lib/dateRanges';

const FilterContext = createContext(null);

export function FilterProvider({ children }) {
  const [preset, setPreset] = useState('last7');
  const [customStart, setCustomStart] = useState(null);
  const [customEnd, setCustomEnd] = useState(null);
  const [compareEnabled, setCompareEnabled] = useState(false);

  const range = useMemo(
    () => resolvePreset(preset, customStart, customEnd),
    [preset, customStart, customEnd]
  );

  const value = {
    preset,
    setPreset,
    customStart,
    setCustomStart,
    customEnd,
    setCustomEnd,
    compareEnabled,
    setCompareEnabled,
    range,
  };

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>;
}

export function useFilter() {
  return useContext(FilterContext);
}
