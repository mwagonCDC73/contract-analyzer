export interface StatusConfig {
  label: string;
  className: string;
}

const statusMap: Record<string, StatusConfig> = {
  draft: { label: 'Draft', className: 'bg-gray-100 text-gray-800' },
  processing: { label: 'Processing', className: 'bg-amber-100 text-amber-800' },
  submitted: { label: 'Awaiting Review', className: 'bg-blue-100 text-blue-800' },
  in_review: { label: 'Under Review', className: 'bg-purple-100 text-purple-800' },
  approved: { label: 'Approved', className: 'bg-green-100 text-green-800' },
  rejected: { label: 'Rejected', className: 'bg-red-100 text-red-800' },
};

export function getStatusConfig(status: string): StatusConfig {
  return statusMap[status] || { label: status, className: 'bg-gray-100 text-gray-800' };
}

export function getStatusBadge(status: string): { label: string; className: string } {
  return getStatusConfig(status);
}
