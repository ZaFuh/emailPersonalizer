#!/usr/bin/env python3
"""
LinkedIn Profile Email Personalizer
Takes a text file with copy-pasted LinkedIn profile dumps.
Each profile starts with "<person_name, company_name>" on its own line,
followed by the profile content until the next profile marker.
Generates personalized emails using Groq API.
"""

import sys
import os
import re
from datetime import datetime

try:
    from groq import Groq
except ImportError:
    print("Error: groq library not installed.")
    print("Install it with: pip install groq")
    sys.exit(1)


# Email template
EMAIL_TEMPLATE = """Dear {name},

I hope you're doing well.

{praise}

I'm reaching out from Stream Advertising. Since 1999, we support clients across the UAE with branding, events and production solutions including signage, wayfinding, office and retail branding, exhibition stands, Fitouts, kiosks, custom fabrication, and large-format printing. Since we do our production in-house, we have complete quality control and have zero delays in deadlines. We always strive to go beyond client expectations.

With {company} {requirement}, I thought it would be worthwhile to see if there could be any upcoming opportunities where we might support your team as a reliable production partner.

I have attached our company profile. Please feel free to look through it. Look forward to hearing from you.

Have a wonderful week!"""

MODEL_NAME = "mixtral-8x7b-32768"


def parse_profiles(file_path):
    """
    Parse a text file with profile dumps.
    Expected format:
    <person_name, company_name>
    [profile content - headline, about, experience, posts, etc.]
    
    <another_person, another_company>
    [profile content]
    
    Returns list of dicts with name, company, and full profile text.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file '{file_path}': {str(e)}")
        sys.exit(1)

    profiles = []
    
    # Split by the profile marker pattern: <name, company>
    # This regex captures everything after < until we hit > and a newline
    pattern = r'<([^>]+)>\s*\n((?:(?!<[^>]+>\s*\n).)*)'
    
    matches = re.finditer(pattern, content, re.DOTALL)
    
    for match in matches:
        header = match.group(1).strip()
        profile_text = match.group(2).strip()
        
        # Parse header: "name, company"
        parts = [p.strip() for p in header.split(',', 1)]
        if len(parts) != 2:
            print(f"Warning: Skipping malformed header: <{header}>")
            continue
        
        name, company = parts
        
        if not name or not company or not profile_text:
            print(f"Warning: Skipping {name} - missing data")
            continue
        
        profiles.append({
            "name": name,
            "company": company,
            "profile_text": profile_text,
        })
    
    return profiles


def clean_greeting_name(full_name):
    """
    'Omar Hamouda, MBA' -> 'Omar Hamouda'
    Strips trailing credentials after comma for natural greeting.
    """
    return full_name.split(",")[0].strip()


def extract_json(text):
    """Pull a JSON object out of a model response, tolerating markdown fences."""
    import json
    text = text.strip()
    text = re.sub(r'^```(json)?', '', text).strip()
    text = re.sub(r'```$', '', text).strip()
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(text)


def generate_personalization(client, profile):
    """
    Use Groq to analyze the LinkedIn profile dump and generate:
    1. "praise": 2-3 sentences of genuine, specific compliment
    2. "requirement": a phrase describing business needs for the company
    
    Returns (result_dict, used_ai: bool)
    """
    name = profile.get("name", "there")
    company = profile.get("company", "their company")
    profile_text = profile.get("profile_text", "")
    
    analysis_prompt = f"""You are helping write a genuine, human-sounding cold outreach email from a
UAE branding/production company (Stream Advertising) to a marketing/brand contact.

Based on the LinkedIn profile text below, write:
1. "praise": 2-3 sentences that open the email. Should read as a genuine,
   specific compliment or observation tied to their actual role, experience,
   or company. Pick out real details from their profile (projects, skills,
   achievements, company scale) and comment on them naturally.
   Do NOT use generic flattery. Be warm but specific.
2. "requirement": a short phrase (8-15 words) that will be inserted into:
   "With {company} <requirement>, I thought it would be worthwhile..."
   So it must:
   - NOT repeat "{company}" or start with "With"
   - NOT start with a capital letter (continues the sentence)
   - describe a real, plausible branding/events/production need relevant
     to their company and this person's role
   Example: "handling multiple large-scale developments that need retail branding and wayfinding"

LinkedIn Profile:
{profile_text}

Respond with ONLY a JSON object, no markdown, no preamble:
{{"praise": "...", "requirement": "..."}}"""
    
    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=400,
            messages=[
                {"role": "user", "content": analysis_prompt}
            ]
        )
        
        response_text = response.content[0].text
        result = extract_json(response_text)
        
        if "praise" not in result or "requirement" not in result:
            raise ValueError(f"Missing keys in response: {result}")
        
        return result, True
        
    except Exception as e:
        print(f"    ⚠ Groq API error for {name}: {e}")
        # Fallback: generic but still respectful
        praise = f"I came across your profile and was impressed by your work at {company}."
        requirement = "expanding its presence and capabilities in the UAE market"
        return {"praise": praise, "requirement": requirement}, False


def personalize_email(profile, personalization):
    """Fill the email template with personalized content."""
    greeting_name = clean_greeting_name(profile.get("name", "there"))
    return EMAIL_TEMPLATE.format(
        name=greeting_name,
        praise=personalization.get("praise", "").strip(),
        company=profile.get("company", "your company"),
        requirement=personalization.get("requirement", "").strip(),
    )


def main():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY environment variable not set.")
        print("Get a free API key from https://console.groq.com/keys")
        print("Then set it with: export GROQ_API_KEY='your-key-here'")
        sys.exit(1)
    
    client = Groq(api_key=api_key)
    
    input_file = sys.argv[1] if len(sys.argv) > 1 else "linkedin_profiles.txt"
    
    print(f"Parsing LinkedIn profile dumps from '{input_file}'...")
    profiles = parse_profiles(input_file)
    
    if not profiles:
        print("No valid profiles found. Check your file format.")
        print("Expected format:")
        print("<name, company>")
        print("[profile content here]")
        print("")
        print("<another_name, another_company>")
        print("[profile content here]")
        sys.exit(0)
    
    print(f"Found {len(profiles)} profiles.\n")
    
    emails = []
    ai_count = 0
    fallback_count = 0
    
    for i, profile in enumerate(profiles, 1):
        name = profile.get("name", "Unknown")
        print(f"[{i}/{len(profiles)}] {name}...", end=" ")
        
        personalization, used_ai = generate_personalization(client, profile)
        if used_ai:
            ai_count += 1
            print("✓")
        else:
            fallback_count += 1
            print("⚠ (fallback)")
        
        email = personalize_email(profile, personalization)
        
        emails.append({
            "name": name,
            "company": profile.get("company", "Unknown"),
            "email": email,
            "used_ai": used_ai,
        })
    
    output_file = "personalized_emails.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PERSONALIZED EMAIL OUTREACH\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total emails: {len(emails)}  (AI: {ai_count}, fallback: {fallback_count})\n")
        f.write("=" * 80 + "\n\n")
        
        for i, email_data in enumerate(emails, 1):
            f.write(f"\n{'='*80}\n")
            f.write(f"EMAIL #{i}\n")
            f.write(f"Recipient: {email_data['name']}\n")
            f.write(f"Company: {email_data['company']}\n")
            if not email_data['used_ai']:
                f.write("⚠ NOTE: Fallback text (API error) -- review before sending\n")
            f.write(f"{'='*80}\n\n")
            f.write(email_data['email'])
            f.write("\n\n")
    
    print(f"\n✓ Generated {len(emails)} personalized emails")
    if fallback_count > 0:
        print(f"  ({ai_count} AI, {fallback_count} fallback -- review fallback ones)")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()