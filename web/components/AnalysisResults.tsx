'use client';

import { useState } from 'react';

interface AnalysisFinding {
  issue: string;
  details: string;
  category: string;
  location: string;
  severity: 'critical' | 'warning' | 'informational';
  recommendation: string;
}

interface OverallRiskAssessment {
  risk_level: 'HIGH' | 'MEDIUM' | 'LOW';
  summary: string;
}

interface AnalysisData {
  overall_risk_assessment?: OverallRiskAssessment;
  summary: {
    critical: number;
    warning: number;
    informational: number;
    total_issues: number;
  };
  findings: AnalysisFinding[];
}

interface AnalysisResultsProps {
  analysisResults: {
    analysis: string;
    model: string;
    tokens_used: {
      input: number;
      output: number;
    };
  };
  compact?: boolean;
}

const riskLevelConfig: Record<string, {
  textColor: string;
  bgColor: string;
  borderColor: string;
  label: string;
}> = {
  HIGH: {
    textColor: 'text-red-700',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-400',
    label: 'HIGH RISK',
  },
  MEDIUM: {
    textColor: 'text-orange-700',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-400',
    label: 'MEDIUM RISK',
  },
  LOW: {
    textColor: 'text-green-700',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-400',
    label: 'LOW RISK',
  },
};

const severityOrder: Record<string, number> = {
  critical: 0,
  warning: 1,
  informational: 2,
};

const severityConfig: Record<string, {
  label: string;
  badgeBg: string;
  badgeText: string;
  borderColor: string;
  bgColor: string;
  icon: string;
}> = {
  critical: {
    label: 'Critical',
    badgeBg: 'bg-red-100',
    badgeText: 'text-red-800',
    borderColor: 'border-red-500',
    bgColor: 'bg-red-50',
    icon: '!',
  },
  warning: {
    label: 'Warning',
    badgeBg: 'bg-amber-100',
    badgeText: 'text-amber-800',
    borderColor: 'border-amber-500',
    bgColor: 'bg-amber-50',
    icon: '!',
  },
  informational: {
    label: 'Info',
    badgeBg: 'bg-blue-100',
    badgeText: 'text-blue-800',
    borderColor: 'border-blue-500',
    bgColor: 'bg-blue-50',
    icon: 'i',
  },
};

function parseAnalysis(analysisStr: string): AnalysisData | null {
  try {
    // Strip markdown code fences if the AI wrapped the JSON in them
    let cleaned = analysisStr.trim();
    if (cleaned.startsWith('```')) {
      cleaned = cleaned.replace(/^```(?:json)?\s*\n?/, '').replace(/\n?```\s*$/, '');
    }
    const parsed = JSON.parse(cleaned);
    if (parsed && parsed.findings && Array.isArray(parsed.findings)) {
      return parsed as AnalysisData;
    }
    return null;
  } catch {
    return null;
  }
}

function SeverityIcon({ severity }: { severity: string }) {
  const config = severityConfig[severity] || severityConfig.informational;

  if (severity === 'critical') {
    return (
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-red-100 flex items-center justify-center">
        <svg className="w-5 h-5 text-red-600" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
      </div>
    );
  }

  if (severity === 'warning') {
    return (
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center">
        <svg className="w-5 h-5 text-amber-600" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
      </div>
    );
  }

  return (
    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
      <svg className="w-5 h-5 text-blue-600" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
      </svg>
    </div>
  );
}

export default function AnalysisResults({ analysisResults, compact = false }: AnalysisResultsProps) {
  const [expandedFindings, setExpandedFindings] = useState<Set<number>>(new Set());
  const [showAll, setShowAll] = useState(!compact);

  const data = parseAnalysis(analysisResults.analysis);

  // Fallback: if we can't parse structured data, render as formatted text
  if (!data) {
    return (
      <div className="space-y-4">
        <div className="bg-gray-50 rounded-lg p-4">
          <pre className="whitespace-pre-wrap text-sm text-gray-700 leading-relaxed">
            {analysisResults.analysis}
          </pre>
        </div>
      </div>
    );
  }

  const sortedFindings = [...data.findings].sort(
    (a, b) => (severityOrder[a.severity] ?? 99) - (severityOrder[b.severity] ?? 99)
  );

  const displayFindings = compact && !showAll
    ? sortedFindings.slice(0, 5)
    : sortedFindings;

  const toggleFinding = (index: number) => {
    setExpandedFindings((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const categories = [...new Set(data.findings.map((f) => f.category))];

  const riskAssessment = data.overall_risk_assessment;
  const riskConfig = riskAssessment
    ? riskLevelConfig[riskAssessment.risk_level] || riskLevelConfig.MEDIUM
    : null;

  return (
    <div className="space-y-6">
      {/* Overall Risk Assessment Banner */}
      {riskAssessment && riskConfig && (
        <div className={`${riskConfig.bgColor} ${riskConfig.borderColor} border-2 rounded-lg p-5`}>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
            Overall Risk Assessment
          </p>
          <div className="flex items-center gap-3 mb-2">
            <span className={`text-2xl font-extrabold ${riskConfig.textColor}`}>
              {riskConfig.label}
            </span>
          </div>
          <p className={`text-base font-semibold ${riskConfig.textColor}`}>
            {riskAssessment.summary}
          </p>
        </div>
      )}

      {/* Summary Bar */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-gray-900">
              {data.summary.total_issues} Issues Found
            </h3>
          </div>
          <div className="flex flex-wrap gap-3">
            {data.summary.critical > 0 && (
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
                <span className="text-sm font-medium text-red-800">
                  {data.summary.critical} Critical
                </span>
              </div>
            )}
            {data.summary.warning > 0 && (
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                <span className="text-sm font-medium text-amber-800">
                  {data.summary.warning} Warning
                </span>
              </div>
            )}
            {data.summary.informational > 0 && (
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-500"></span>
                <span className="text-sm font-medium text-blue-800">
                  {data.summary.informational} Informational
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Severity Progress Bar */}
        {data.summary.total_issues > 0 && (
          <div className="mt-3 flex rounded-full overflow-hidden h-2 bg-gray-100">
            {data.summary.critical > 0 && (
              <div
                className="bg-red-500"
                style={{ width: `${(data.summary.critical / data.summary.total_issues) * 100}%` }}
              />
            )}
            {data.summary.warning > 0 && (
              <div
                className="bg-amber-500"
                style={{ width: `${(data.summary.warning / data.summary.total_issues) * 100}%` }}
              />
            )}
            {data.summary.informational > 0 && (
              <div
                className="bg-blue-500"
                style={{ width: `${(data.summary.informational / data.summary.total_issues) * 100}%` }}
              />
            )}
          </div>
        )}

        {/* Category Tags */}
        <div className="mt-3 flex flex-wrap gap-1.5">
          {categories.map((cat) => (
            <span
              key={cat}
              className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600"
            >
              {cat}
            </span>
          ))}
        </div>
      </div>

      {/* Finding Cards */}
      <div className="space-y-3">
        {displayFindings.map((finding, idx) => {
          const config = severityConfig[finding.severity] || severityConfig.informational;
          const isExpanded = expandedFindings.has(idx);

          return (
            <div
              key={idx}
              className={`border-l-4 ${config.borderColor} rounded-r-lg bg-white border border-gray-200 overflow-hidden`}
            >
              {/* Header - always visible */}
              <button
                onClick={() => toggleFinding(idx)}
                className="w-full text-left px-4 py-3 flex items-start gap-3 hover:bg-gray-50 transition-colors"
              >
                <SeverityIcon severity={finding.severity} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="text-sm font-semibold text-gray-900">
                      {finding.issue}
                    </h4>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${config.badgeBg} ${config.badgeText}`}>
                      {config.label}
                    </span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                      {finding.category}
                    </span>
                  </div>
                  {!isExpanded && (
                    <p className="mt-1 text-sm text-gray-600 line-clamp-2">
                      {finding.details}
                    </p>
                  )}
                </div>
                <svg
                  className={`flex-shrink-0 w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>

              {/* Expanded Details */}
              {isExpanded && (
                <div className={`px-4 pb-4 pt-0 ml-11 space-y-3 border-t border-gray-100`}>
                  <div className="pt-3">
                    <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Details</h5>
                    <p className="text-sm text-gray-700 leading-relaxed">{finding.details}</p>
                  </div>
                  {finding.location && (
                    <div>
                      <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Location</h5>
                      <p className="text-sm text-gray-600">{finding.location}</p>
                    </div>
                  )}
                  {finding.recommendation && (
                    <div className={`${config.bgColor} rounded-md p-3`}>
                      <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Recommendation</h5>
                      <p className="text-sm text-gray-700 leading-relaxed">{finding.recommendation}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Show More / Show Less */}
      {compact && sortedFindings.length > 5 && (
        <div className="text-center">
          <button
            onClick={() => setShowAll(!showAll)}
            className="text-sm font-medium text-blue-600 hover:text-blue-800"
          >
            {showAll
              ? 'Show fewer findings'
              : `Show all ${sortedFindings.length} findings`}
          </button>
        </div>
      )}

    </div>
  );
}
