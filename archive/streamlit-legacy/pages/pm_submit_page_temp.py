        return None

    # Remove null bytes and other control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]', '', text)

    # Normalize unicode characters
    text = text.encode('ascii', 'ignore').decode('ascii')

    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)

    # Replace multiple newlines with double newline
    text = re.sub(r'\n\n+', '\n\n', text)

    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    return text.strip()


def extract_text_from_pdf(file):
    """Extract text from PDF file using pdfplumber (better quality) with fallback to PyPDF2"""
    try:
        file_bytes = file.getvalue()

        # Try pdfplumber first (better extraction quality)
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"

                if text.strip():
                    cleaned_text = clean_extracted_text(text)
                    if cleaned_text and len(cleaned_text) > 100:
                        return cleaned_text
        except Exception as e:
            print(f"pdfplumber extraction failed, trying PyPDF2: {str(e)}")

        # Fallback to PyPDF2
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"

            if text.strip():
                cleaned_text = clean_extracted_text(text)
                if cleaned_text and len(cleaned_text) > 100:
                    return cleaned_text
        except Exception as e:
            print(f"PyPDF2 extraction also failed: {str(e)}")

        st.error("Failed to extract text from PDF. File may be scanned, encrypted, or corrupted.")
        return None

    except Exception as e:
        st.error(f"Error extracting PDF text: {str(e)}")
        return None


def analyze_contract_with_claude(contract_text, api_key, contract_type="single", comparison_text=None):
    """Analyze contract using Claude API

    Args:
        contract_text: Main contract text to analyze
        api_key: Anthropic API key
        contract_type: "single" for one contract, "comparison" for prime+sub analysis
        comparison_text: Second contract text (for comparison mode)
    """

    # DEBUG - Check API key
    st.write("🔍 **DEBUG - API Key Check:**")
    if api_key:
        st.write(f"   - Key starts with: `{api_key[:15]}...`")
        st.write(f"   - Key length: {len(api_key)} characters")
        st.write(f"   - Starts with 'sk-ant-': {api_key.startswith('sk-ant-')}")
    else:
        st.error("   - API Key is None or empty!")
        return None

    if contract_type == "comparison" and comparison_text:
        # Dual contract comparison analysis
        prompt = """You are an expert construction contract analyst specializing in wall and ceiling specialty subcontractor agreements for California Drywall Co.

You are analyzing BOTH a prime contract and a subcontract together to identify:
1. Red flags in each contract individually
2. Flow-down clause issues between prime and subcontract
3. Gaps or conflicts between the two agreements

PRIME CONTRACT:
{prime_text}

---

SUBCONTRACT:
{sub_text}

Provide comprehensive analysis covering:

**A. PRIME CONTRACT RED FLAGS:**
- Payment terms and cash flow
- Schedule and performance requirements
- Insurance and bonding requirements
- Scope definition gaps
- Risk allocation concerns
- Change order provisions
- Dispute resolution terms

**B. SUBCONTRACT RED FLAGS:**
- All of the above, from subcontractor perspective
- Pay-when-paid vs pay-if-paid clauses
- Retainage provisions
- Warranty requirements
- Indemnification scope

**C. FLOW-DOWN & COMPARISON ISSUES:**
- Are prime contract obligations properly flowed down to subcontract?
- Payment timing gaps (e.g., prime gets paid Net-30, but sub must wait Net-60)
- Insurance requirements gaps (sub required to carry more than prime)
- Schedule constraints not aligned
- Change order markup inconsistencies
- Liquidated damages passed through without caps
- Dispute resolution method conflicts
- Missing flow-down provisions that create liability gaps

Format response as JSON:
{{
  "summary": {{
    "total_issues": <number>,
    "critical": <number>,
    "warning": <number>,
    "informational": <number>,
    "comparison_issues": <number of flow-down/gap issues>
  }},
  "findings": [
    {{
      "contract": "<prime|subcontract|both>",
      "category": "<category>",
      "severity": "<critical|warning|informational>",
      "issue": "<brief title>",
      "details": "<detailed explanation>",
      "location": "<Article X, Section Y>",
      "recommendation": "<action to take>"
    }}
  ]
}}
"""
        prompt = prompt.format(prime_text=contract_text[:40000], sub_text=comparison_text[:40000])
    else:
        # Single contract analysis
        prompt = """You are an expert construction contract analyst specializing in wall and ceiling specialty subcontractor agreements for California Drywall Co.

Analyze the following construction contract and provide comprehensive red flag analysis focusing on:

1. **Critical Issues** - Must be resolved before signing (deal-breakers, missing critical terms, unacceptable risk allocation)
2. **Warnings** - Items requiring negotiation or clarification (unfavorable terms, ambiguous language, business risks)
3. **Informational** - Items to be aware of (standard clauses, best practices, recommendations)

**Key Risk Areas to Examine:**

**Payment & Cash Flow:**
- Payment timing (Net-30? Net-60? Pay-when-paid vs pay-if-paid?)
- Retainage percentage and release timing
- Stored materials payment provisions
- Payment for extra work/changes
- Administrative burden for payment applications

**Schedule & Performance:**
- Realistic timelines for wall/ceiling scope
- Shop drawing submittal time
- Liquidated damages (capped? reasonable?)
- "No damage for delay" clauses
- Substantial completion criteria

**Scope & Coordination:**
- Clear scope definition for wall/ceiling systems
- Division of work between trades (backing, blocking, framing for others)
- BIM/VDC coordination requirements
- Prefabrication provisions and site access
- Fire-rated assemblies and acoustic testing responsibility

**Insurance & Risk:**
- Insurance requirements (reasonable for subcontractor?)
- Indemnification scope (for GC's sole negligence?)
- Waiver of subrogation
- OCIP/CCIP provisions

**Change Orders:**
- Unilateral change directives
- Markup limitations
- Notice requirements
- Time extension provisions

**California-Specific:**
- Prompt payment compliance (Civil Code §8800)
- Stop notice rights preserved
- Mechanics lien rights
- Indemnity limitations (Civil Code §2782)
- OSHPD requirements (if applicable)
- Prevailing wage compliance

**Dispute Resolution:**
- Arbitration vs litigation
- Venue/jurisdiction
- Attorney's fees provisions
- Step dispute resolution process

Format response as JSON:
{{
  "summary": {{
    "total_issues": <number>,
    "critical": <number>,
    "warning": <number>,
    "informational": <number>
  }},
  "findings": [
    {{
      "category": "<category>",
      "severity": "<critical|warning|informational>",
      "issue": "<brief title>",
      "details": "<detailed explanation with California Drywall context>",
      "location": "<Article X, Section Y>",
      "recommendation": "<specific action to take>"
    }}
  ]
}}

CONTRACT TEXT:
{contract_text}
"""
        prompt = prompt.format(contract_text=contract_text[:50000])
    
    try:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        st.write(f"🔍 **DEBUG - Making API call to Anthropic...**")
        
        data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 8000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt  # Already formatted above
                }
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=120
        )
        
        st.write(f"🔍 **DEBUG - API Response Status:** {response.status_code}")
        
        if response.status_code != 200:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
        
        result = response.json()
        response_text = result['content'][0]['text']
        
        # Find JSON in response
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        
        return json.loads(response_text)
    
    except Exception as e:
        st.error(f"Error analyzing contract: {str(e)}")
        return None


