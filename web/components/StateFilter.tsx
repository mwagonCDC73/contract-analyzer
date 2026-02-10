interface StateFilterProps {
  value: string;
  onChange: (value: string) => void;
  states?: { code: string; name: string }[];
}

const DEFAULT_STATES = [
  { code: 'CA', name: 'California' },
  { code: 'NV', name: 'Nevada' },
];

export default function StateFilter({ value, onChange, states = DEFAULT_STATES }: StateFilterProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="text-sm border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500"
    >
      <option value="">All States</option>
      {states.map((s) => (
        <option key={s.code} value={s.code}>
          {s.code} - {s.name}
        </option>
      ))}
    </select>
  );
}
