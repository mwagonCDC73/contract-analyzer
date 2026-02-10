interface StateBadgeProps {
  state: string;
  size?: 'sm' | 'md';
}

const STATE_COLORS: Record<string, string> = {
  CA: 'bg-sky-100 text-sky-800',
  NV: 'bg-amber-100 text-amber-800',
};

export default function StateBadge({ state, size = 'sm' }: StateBadgeProps) {
  const colorClass = STATE_COLORS[state] || 'bg-gray-100 text-gray-800';
  const sizeClass = size === 'md' ? 'px-2.5 py-1 text-sm' : 'px-2 py-0.5 text-xs';

  return (
    <span className={`inline-flex items-center font-semibold rounded-full ${colorClass} ${sizeClass}`}>
      {state}
    </span>
  );
}
