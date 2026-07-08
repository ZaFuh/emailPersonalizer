#!/usr/bin/env python3
"""
LinkedIn Profile Email Personalizer
Uses Groq API (free) to generate personalized outreach emails from a CSV
of leads (Name, Company, LinkedIn URL, Job Title, and optionally a Bio/About column).
"""

import json
import sys
import csv
import os
import re
import time
from datetime import datetime

try:
    from groq import Groq
except ImportError:
    print("Error: groq library not installed.")
    print("Install it with: pip install groq")
    sys.exit(1)


# Email template. Note: <requirement> must read naturally directly after
# "<company_name>" -- e.g. "With Modon having several large-scale developments
# underway, I thought..." -- so the LLM is instructed to never repeat the
# company name or start the phrase with "With".
EMAIL_TEMPLATE = """Dear {name},

I hope you're doing well.

{praise}

I'm reaching out from Stream Advertising. Since 1999, we support clients across the UAE with branding, events and production solutions including signage, wayfinding, office and retail branding, exhibition stands, Fitouts, kiosks, custom fabrication, and large-format printing. Since we do our production in-house, we have complete quality control and have zero delays in deadlines. We always strive to go beyond client expectations.

With {company} {requirement}, I thought it would be worthwhile to see if there could be any upcoming opportunities where we might support your team as a reliable production partner.

I have attached our company profile. Please feel free to look through it. Look forward to hearing from you.

Have a wonderful week!"""

# Model choice: Groq deprecated its Llama chat models in mid-2026.
# openai/gpt-oss-120b is the current recommended general-purpose free model.
# Check https://console.groq.com/docs/models if this stops working.
MODEL_NAME = "openai/gpt-oss-120b"


def clean_greeting_name(full_name):
    """
    'Omar Hamouda, MBA' -> 'Omar Hamouda'
    Strips trailing credentials (MBA, MCIM, etc.) after a comma so the
    greeting line reads naturally. Falls back to the full name if there's
    no comma.
    """
    return full_name.split(",")[0].strip()


def load_linkedin_profiles(file_path):
    """
    Load leads from a CSV file. Required columns (case-insensitive, flexible
    naming): Lead Name / Name, Company Name / Company, Linkedin.
    Optional columns used if present: Job (job title), Bio / About (manually
    pasted profile text -- greatly improves personalization quality).
    All other columns are ignored.
    """
    try:
        profiles = []
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            if reader.fieldnames is None:
                print(f"Error: CSV file '{file_path}' is empty.")
                sys.exit(1)

            fieldnames_lower = {field.lower().strip(): field for field in reader.fieldnames}

            name_col = None
            company_col = None
            linkedin_col = None
            job_col = None
            bio_col = None

            for lower_key, original_key in fieldnames_lower.items():
                if 'lead' in lower_key and 'name' in lower_key:
                    name_col = original_key
                elif 'company' in lower_key:
                    company_col = original_key
                elif 'linkedin' in lower_key:
                    linkedin_col = original_key
                elif lower_key == 'job' or 'job title' in lower_key or lower_key == 'title':
                    job_col = original_key
                elif lower_key in ('bio', 'about', 'summary', 'notes'):
                    bio_col = original_key

            if not name_col:
                for lower_key, original_key in fieldnames_lower.items():
                    if lower_key == 'name':
                        name_col = original_key
                        break

            if not name_col or not company_col or not linkedin_col:
                print("\nError: Missing required columns!")
                print(f"Found columns: {list(reader.fieldnames)}\n")
                if not name_col:
                    print("✗ Missing: 'Lead Name' or 'Name' column")
                if not company_col:
                    print("✗ Missing: 'Company Name' or 'Company' column")
                if not linkedin_col:
                    print("✗ Missing: 'Linkedin' or 'LinkedIn' column")
                sys.exit(1)

            print(f"Matched columns -> Name: '{name_col}', Company: '{company_col}', "
                  f"LinkedIn: '{linkedin_col}'"
                  + (f", Job: '{job_col}'" if job_col else "")
                  + (f", Bio: '{bio_col}'" if bio_col else ""))
            if not bio_col:
                print("Tip: add a 'Bio' or 'About' column with pasted profile text "
                      "for noticeably better, more specific personalization.\n")

            for row in reader:
                name = (row.get(name_col) or "").strip()
                company = (row.get(company_col) or "").strip()
                linkedin_url = (row.get(linkedin_col) or "").strip()
                job_title = (row.get(job_col) or "").strip() if job_col else ""
                bio = (row.get(bio_col) or "").strip() if bio_col else ""

                if not name or not company:
                    continue

                if not linkedin_url:
                    print(f"  ⚠ Skipping {name} - no LinkedIn URL")
                    continue

                profiles.append({
                    "name": name,
                    "company": company,
                    "profile_url": linkedin_url,
                    "job_title": job_title,
                    "bio": bio,
                })

        return profiles
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file '{file_path}': {str(e)}")
        sys.exit(1)


def extract_json(text):
    """Pull a JSON object out of a model response, tolerating markdown fences."""
    text = text.strip()
    text = re.sub(r'^```(json)?', '', text).strip()
    text = re.sub(r'```$', '', text).strip()
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(text)


def generate_personalization(client, profile):
    """
    Use Groq to generate a genuine 2-3 sentence praise/hook and a short
    company-requirement phrase, grounded in whatever real signal we have
    (job title, and bio/about text if the user supplied it).

    Returns (result_dict, used_ai: bool)
    """
    name = profile.get("name", "there")
    company = profile.get("company", "their company")
    job_title = profile.get("job_title", "")
    bio = profile.get("bio", "")

    context_lines = [f"Name: {name}", f"Company: {company}"]
    if job_title:
        context_lines.append(f"Job title: {job_title}")
    if bio:
        context_lines.append(f"Profile bio/about: {bio}")
    if not job_title and not bio:
        context_lines.append(
            "(No job title or bio available -- keep the praise general but "
            "still warm and specific to the company/industry, not generic.)"
        )
    context = "\n".join(context_lines)

    analysis_prompt = f"""You are helping write a genuine, human-sounding cold outreach email from a
UAE branding/production company (Stream Advertising) to a marketing/brand contact.

Based on the profile info below, write:
1. "praise": 2-3 sentences that open the email. Should read as a genuine,
   specific compliment or observation tied to their actual role/company
   (e.g. what their role likely involves, the scale or nature of their
   company's projects). Avoid generic flattery like "impressive background."
   Do not invent specific facts, numbers, or achievements you weren't given.
2. "requirement": a short phrase (8-15 words) that will be inserted into this
   exact sentence: "With {company} <requirement>, I thought it would be
   worthwhile..." So it must:
   - NOT repeat "{company}" or start with "With"
   - NOT start with a capital letter (it continues the sentence)
   - describe a plausible branding/events/production need or growth signal
     relevant to their company and this person's role
   Example: "having multiple large-scale developments underway that will need retail branding and wayfinding"

Profile:
{context}

Respond with ONLY a JSON object, no markdown, no preamble:
{{"praise": "...", "requirement": "..."}}"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=400,
            temperature=0.8,
            response_format={"type": "json_object"},
            messages=[
                {"role": "user", "content": analysis_prompt}
            ]
        )

        response_text = response.choices[0].message.content
        result = extract_json(response_text)

        if "praise" not in result or "requirement" not in result:
            raise ValueError(f"Missing expected keys in model response: {result}")

        return result, True

    except Exception as e:
        print(f"    ⚠ Groq API error for {name}: {e}")
        # Fallback that still uses whatever real data we have, without
        # duplicating the company name (the old bug).
        if job_title:
            praise = f"I came across your role as {job_title} at {company} and wanted to reach out directly."
        else:
            praise = f"I came across your profile and {company}'s work and wanted to reach out directly."
        requirement = "expanding its presence across the UAE"
        return {"praise": praise, "requirement": requirement}, False


def personalize_email(profile, personalization):
    """Fill the email template. Returns the finished email text."""
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

    input_file = sys.argv[1] if len(sys.argv) > 1 else "linkedin_profiles.csv"

    print(f"Loading leads from '{input_file}'...")
    profiles = load_linkedin_profiles(input_file)
    print(f"Found {len(profiles)} leads with LinkedIn URLs.\n")

    if not profiles:
        print("No valid leads to process (need Name, Company, and LinkedIn URL). Exiting.")
        sys.exit(0)

    emails = []
    ai_count = 0
    fallback_count = 0

    for i, profile in enumerate(profiles, 1):
        name = profile.get("name", "Unknown")
        print(f"[{i}/{len(profiles)}] {name}...", end=" ")

        personalization, used_ai = generate_personalization(client, profile)
        if used_ai:
            ai_count += 1
            print("✓ AI personalized")
        else:
            fallback_count += 1
            print("⚠ used fallback (see error above)")

        email = personalize_email(profile, personalization)

        emails.append({
            "name": name,
            "company": profile.get("company", "Unknown"),
            "linkedin": profile.get("profile_url", ""),
            "email": email,
            "used_ai": used_ai,
        })

        # Stay comfortably under Groq's free-tier rate limit (~30 req/min).
        if i < len(profiles):
            time.sleep(2)

    output_file = "personalized_emails.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PERSONALIZED EMAIL OUTREACH\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total emails: {len(emails)}  (AI personalized: {ai_count}, fallback: {fallback_count})\n")
        f.write("=" * 80 + "\n\n")

        for i, email_data in enumerate(emails, 1):
            f.write(f"\n{'='*80}\n")
            f.write(f"EMAIL #{i}\n")
            f.write(f"Recipient: {email_data['name']}\n")
            f.write(f"Company: {email_data['company']}\n")
            f.write(f"LinkedIn: {email_data['linkedin']}\n")
            if not email_data['used_ai']:
                f.write("NOTE: AI personalization failed for this one -- review before sending.\n")
            f.write(f"{'='*80}\n\n")
            f.write(email_data['email'])
            f.write("\n\n")

    print(f"\n✓ Done: {ai_count} AI-personalized, {fallback_count} used fallback text.")
    if fallback_count > 0:
        print("  Review the ⚠ flagged emails in the output file before sending --")
        print("  they used generic fallback text because the API call failed.")
    print(f"Output saved to: {output_file}")


if __name__ == "__main__":
    main()